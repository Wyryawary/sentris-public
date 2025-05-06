# <!-- file: ai.py | purpose: AI endpoints | scope: ai | updated: 2025-04-21 -->

from fastapi import FastAPI, HTTPException, Request
from fastapi import APIRouter
from pydantic import BaseModel, Field, validator
import openai
import os
import random
import re
import logging
from typing import List, Optional
import json
import string
from collections import defaultdict
from db import database
from fastapi.responses import JSONResponse
from fastapi import BackgroundTasks

from db import (
    get_predefined_custom_topics,
    get_predefined_sentence_types,
    get_blacklist_topics,
    get_common_short_phrases,
    save_new_topics,
    record_token_usage,
    record_freshSentence,
    record_firstFiller,
    background_record_fillBlock,
    record_validated_sentence,
)

# Init
# logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
router = APIRouter()
timeout_str = os.getenv("OPENAI_API_TIMEOUT", "10")
DEFAULT_OPENAI_TIMEOUT = float(timeout_str) if timeout_str.isdigit() else 10.0

# Helper function to call OpenAI API with timeout and centralized error handling
async def call_openai_api(**kwargs):
    try:
        response = await openai.ChatCompletion.acreate(
            timeout=DEFAULT_OPENAI_TIMEOUT, 
            **kwargs
        )
        return response
    except openai.error.Timeout:
        logger.error("OpenAI API request timed out.")
        raise HTTPException(status_code=550, detail="External API request timed out.")
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(status_code=502, detail="External API request failed.")
    except Exception as e:
        logger.error(f"Unexpected error during OpenAI API call: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error.")

#----------------------
# AI endpoints

# ========== /get fresh sentence endpoint ==========
class GetFreshSentenceRequest(BaseModel):
    block_count: int = Field(..., ge=4, le=7)
    custom_topics: Optional[List[str]] = None
    model: Optional[str] = Field("gpt-4o-mini")
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    active_user_session: Optional[str] = None

class GetFreshSentenceResponse(BaseModel):
    sentence: str

@router.post("/get_fresh_sentence", response_model=GetFreshSentenceResponse)
async def get_fresh_sentence(request: GetFreshSentenceRequest, background_tasks: BackgroundTasks):
    print("\n------------ FRESH SENTENCE -------------")
    spelled_block_count = spell_int(request.block_count)

    if request.custom_topics and len(request.custom_topics) > 0:
        topic = random.choice(request.custom_topics)
    else:
        all_db_topics = await get_predefined_custom_topics()
        if not all_db_topics:
            raise HTTPException(status_code=500, detail="No topics available.")
        topic = random.choice(all_db_topics)

    sentence_types = ["statement", "question", "statement"]
    if not sentence_types:
        sentence_types = ["general"]

    chosen_sentence_type = random.choice(sentence_types)
        
    prompt = (
        f"\nProduce exactly one coherent sentence for a puzzle game using a total of {spelled_block_count} words, short phrases or texts, arranged into blocks separated by '^'.\n\n"
        "Each block MUST contain only one or two words and be at most ten characters each. Do not put an entire esntence into a single block! "
        f"Do not exceed {spelled_block_count} blocks or merge them. Make sure that one sentence is generated, made of the blocks. NOT one sentence per block! \n"
        "For example, the sentence 'I like to play chess' should be formatted as 'I^like^to^play^chess'.\n\n"
        f"Generate the sentence using the sentence type: '{chosen_sentence_type}'. \n"
        f"For the sentence, focus on the topic of '{topic}' or a similar topic.\n\n"
        "List the complete sentence on a new line without extra content."
    )   
    print("\n -----FRESH prompt:\n", prompt)

    try:
        response = await call_openai_api(
            model=request.model,
            temperature=0.3,
            max_tokens=25,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            messages=[
                {"role": "system", "content": (
                    "You are a strict puzzle generator. If your draft violates any requirement, "
                    "correct yourself immediately in the same response."
                )},
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        #print("\n -----fresh sentence response:", response)

        usage_info = response.get("usage")
        if usage_info:
            async with database.pool.acquire() as conn:
                async with conn.transaction():
                    await record_token_usage(
                        user_id=request.user_id,
                        endpoint_name="get_fresh_sentence",
                        model_name=request.model,
                        prompt_tokens=usage_info.get("prompt_tokens", 0),
                        completion_tokens=usage_info.get("completion_tokens", 0),
                        total_tokens=usage_info.get("total_tokens", 0),
                        session_id=request.session_id,
                        active_user_session=request.active_user_session
                    )

        raw_text = response.choices[0].message["content"].strip()
        print("\n -----FRESH raw: \n", raw_text)

    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(status_code=502, detail="Failed to generate sentences.")
    except Exception as e:
        logger.error(f"Error in /get fresh sentence: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error.")
    
    background_tasks.add_task(record_freshSentence, raw_text, request.block_count)
    
    return GetFreshSentenceResponse(sentence=raw_text)


# ========== /first filler Endpoint ==========

class FirstFillerRequest(BaseModel):
    block_count: int = Field(..., ge=4, le=7)
    sentence: str = Field(..., description="Partially filled sentence with ^|^ as block separators and #|# as placeholders.")
    #num_sentences: int = Field(..., ge=1)
    use_model: str = Field("gpt-4o-mini")
    user_id: Optional[str] = None
    active_user_session: Optional[str] = None

class FirstFillerResponse(BaseModel):
    sentences: List[str] = Field(
        ...,
        description="A list"
    )


@router.post("/first_filler", response_model=FirstFillerResponse)
async def first_filler(
    request: FirstFillerRequest, background_tasks: BackgroundTasks):
    print("\n------------ FIRST FILLER -------------")
    spelled_block_count = spell_int(request.block_count)

    prompt = (
        f"\nProduce two sensible, valid sentences formatted into {spelled_block_count} blocks of words, short phrases or texts delimited by '^|^'. "
        "The sentence to start with already includes one pre-existing block that has to be kept in its place, in the output. While the missing blocks are marked as '#|#'."
        f"\nSentence: '{request.sentence}' \n "
        "For every '#|#' placeholder, generate a replacement of up to twelve characters. \n"
        "When appropriate, feel free to generate creative variations that naturally fit the context of the sentence. "
        "List each complete sentence on a new line without extra content."
    )
    print("\n -----FIRST prompt:\n", prompt)
    
    try:
        response = await call_openai_api(
            model=request.use_model,
            temperature=0.8,
            max_tokens=64,
            top_p=1,
            frequency_penalty=0.1,  
            presence_penalty=0,
            messages=[
                {
                    "role": "system",
                    "content": "You produce short puzzle sentences in a minimal text format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        usage_info = response.get("usage")
        if usage_info:
            async with database.pool.acquire() as conn:
                async with conn.transaction():
                    await record_token_usage(
                        user_id=request.user_id,
                        endpoint_name="first_filler",
                        model_name=request.use_model,
                        prompt_tokens=usage_info.get("prompt_tokens", 0),
                        completion_tokens=usage_info.get("completion_tokens", 0),
                        total_tokens=usage_info.get("total_tokens", 0),
                        session_id=None,  # or your logic to set session_id
                        active_user_session=request.active_user_session
                    )

        #print("\n -----first filler response:", response)
        raw_text = response.choices[0].message["content"].strip()
        print("\n -----FIRST raw:", raw_text)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error calling FIRST FILLER: {str(e)}"
        )

    # Extract lines that match the block constraints.
    sents = [line.strip() for line in raw_text.splitlines() if line.strip()]
    print("\n -----FIRST completed:\n", sents)
    
    background_tasks.add_task(background_record_firstFiller, sents, request.block_count, request.sentence)

    return FirstFillerResponse(sentences=sents)


# ========== /fill block endpoint ==========

class FillBlockRequest(BaseModel):
    block_count: int = Field(
        ...,
        title="Block Count",
        description="Number of texts in the generated sentences.",
        ge=4,
        le=7
    )
    sentence: str = Field(
        ...,
        title="Sentence",
        description=(
            "A formatted sentence with missing parts."
        )
    )
    num_candidates: int = Field(
        3,
        title="Number of Candidates",
        description="The number of candidate textual contents to generate for each missing part.",
        ge=1,
        le=10
    )
    model: Optional[str] = Field(
        "gpt-4o-mini",
        title="GPT Model",
        description="The GPT model to use."
    )
    custom_topics: Optional[List[str]] = Field(
        None,
        title="Custom Topics",
        description="Optional custom topics to influence the candidate generation."
    )
    user_id: Optional[str] = Field(
        None,
        title="User ID",
        description="Unique identifier of the player (UUID) for token usage tracking."
    )   
    session_id: Optional[str] = Field(
        None,
        title="Session ID",
        description="Unique identifier for the current game session."
    )
    active_user_session: Optional[str] = None

class FillBlockResponse(BaseModel):
    sentences: List[str] = Field(
        ...,
        title="Sentences",
        description="A list of complete sentences formatted with blocks delimited by '^|^'."
    )
    

@router.post("/fill_block", response_model=FillBlockResponse)
async def fill_block(request: FillBlockRequest, background_tasks: BackgroundTasks):
    
    preprocessSentence = preprocess_sentence(request.sentence)
    print("\n------------  FILL BLOCK -------------")
    print("\n -----FILL Original sentence: ", request.sentence)
    print("\n -----FILL preprocessed sentence: \n", preprocessSentence)

    if '_' not in request.sentence: 
        raise HTTPException(
            status_code=400,
            detail="Sentence must contain at least one '_' indicating a missing part."
        )

    base_prompt = (
        "\nThe puzzle sentence below is partially complete with blocks of words and short texts delimited by '^|^'. "
        f"Puzzle sentence: \n{preprocessSentence}. \n\n "
        "Create a single valid sentence in a separate line by replacing the missing blocks indicated by '#|#'. \n"
        "Make sure that every '#|#' is cleared and replaced by some generated content. \n"
        "Make sure that each block of text is fifteen characters or fewer. \n"
        "Separate the blocks in the completed puzzle sentence with the '^|^' delimiter in between the blocks. \n"
    )

    if request.custom_topics:
        blacklist_topics_db = await get_blacklist_topics()
        filtered_topics = [topic for topic in request.custom_topics if topic not in blacklist_topics_db]
        if not filtered_topics:
            raise HTTPException(status_code=400, detail="All provided custom topics are blacklisted.")
        sel_topic = random.choice(filtered_topics)
        base_prompt += (
            f"The sentence should relate to a topic similar to: {sel_topic}\n"
            "Apply these part-of-speech topic relevance rules:\n"
            "  • Nouns or Verbs → MUST strongly relate to the topic(s)\n"
            "  • Adjectives → SHOULD relate if possible\n"
            "  • Adverbs → may optionally relate\n"
            "  • Prepositions, Conjunctions, Pronouns, Determiners, or common short phrases → no topic relevance required\n\n"
            "You must strictly follow these rules only if the missing block is of that part of speech.\n\n"
        )

    print("\n -----FILL BLOCK prompt: \n", base_prompt)

    try:
        response = await call_openai_api(
            model=request.model,
            temperature=0.7,
            max_tokens=25,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a language puzzle solver. "
                    )
                },
                {"role": "user", "content": f"{base_prompt}"}
            ]
        )
        # print("\n -----FILL BLOCK resp: ", response)

        # Token usage logging
        usage_info = response.get("usage")
        if usage_info:
            async with database.pool.acquire() as conn:
                async with conn.transaction():
                    await record_token_usage(
                        user_id=request.user_id,
                        endpoint_name="fill_block",
                        model_name=request.model,
                        prompt_tokens=usage_info.get("prompt_tokens", 0),
                        completion_tokens=usage_info.get("completion_tokens", 0),
                        total_tokens=usage_info.get("total_tokens", 0),
                        session_id=request.session_id,
                        active_user_session=request.active_user_session
                    )

        generated_text = response.choices[0].message['content'].strip()
        print("\n -----FILL gen:\n", generated_text)
        sents = [line.strip() for line in generated_text.splitlines() if line.strip()]
        
        if sents:
        # No parsing happens here — we defer everything to the background
            background_tasks.add_task(
                background_record_fillBlock_full,  # new function below
                sents[0],                          # single sentence to store
                request.block_count,
                request.sentence                   # raw partial sentence
            )
        
        return FillBlockResponse(sentences=sents)
        
        
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error in FILL: {e}")
        raise HTTPException(
            status_code=503,
            detail="FILL Failed to generate candidate textual contents."
        )
    except Exception as e:
        logger.error(f"Error in FB: {e}")
        raise HTTPException(
            status_code=504,
            detail="FILL Internal Server Error."
        )


# ========== /final filler Endpoint ==========

class FinalFillerRequest(BaseModel):
    sentence: str = Field(
        ...,
        title="Sentence",
        description="A formatted sentence with exactly one missing part indicated by '_' (which will be sanitized)."
    )
    model: Optional[str] = Field(
        "gpt-4o-mini",
        title="GPT Model",
        description="The GPT model to use for generating candidate sentence parts."
    )
    custom_topics: Optional[List[str]] = Field(
        None,
        title="Custom Topics",
        description="Optional custom topics to influence candidate generation."
    )
    user_id: Optional[str] = Field(
        None,
        title="User ID",
        description="Unique identifier of the player (UUID) for token usage tracking."
    )   
    session_id: Optional[str] = Field(
        None,
        title="Session ID",
        description="Unique identifier for the current game session."
    )
    active_user_session: Optional[str] = None

class FinalFillerResponse(BaseModel):
    candidates: List[str] = Field(
        ...,
        title="Candidates",
        description="A list of exactly 3 candidate sentence parts."
    )

@router.post("/final_filler", response_model=FinalFillerResponse)
async def final_filler(request: FinalFillerRequest):
    print("\n---------- FINAL FILLER ----------\n")

    prompt = (
        f"\nFill in the single missing block indicated by the ' #|# ' delimiter in the sentence: \"{request.sentence}\". "
        f"\nGenerate exactly five candidate completions.\n\n"
    )

    print("\nFINAL Prompt:\n", prompt)

    try:
        response = await call_openai_api(
            model=request.model,
            temperature=0.7,
            max_tokens=75,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a language puzzle expert that generates concise sentence parts to fill in a missing part in a sentence. "
                        "Put up your best effort in trying to find an ideal candidate that makes the sentence contextually appropriate and grammatically correct. "
                        "Sometimes it is as simple as a single short word, but it can also be a short phrase. "
                        "If a perfect candidate does not exist due to ambiguous context, provide a creative alternative. "
                        "Always respond in valid JSON format with a single key 'candidates' mapping to a list of sentence parts."
                    )
                },
                {"role": "user", "content": prompt}
            ]
        )

        usage_info = response.get("usage")
        if usage_info:
            async with database.pool.acquire() as conn:
                async with conn.transaction():
                    await record_token_usage(
                        user_id=request.user_id,
                        endpoint_name="final_filler",
                        model_name=request.model,
                        prompt_tokens=usage_info.get("prompt_tokens", 0),
                        completion_tokens=usage_info.get("completion_tokens", 0),
                        total_tokens=usage_info.get("total_tokens", 0),
                        session_id=request.session_id,
                        active_user_session=request.active_user_session
                    )

        generated_text = response.choices[0].message['content'].strip()
        #print(f"Recording token usage: session_id={request.session_id}, active_user_session={request.active_user_session}")
        print("--- FINAL Generated text (Raw):", generated_text.encode('utf-8', errors='replace'))
        #print("--- FINAL Generated text (UTF-8 Decoded):", generated_text)
        print("\n--- FINAL Generated text:\n", generated_text)

        try:
            json_str = extract_json_content(generated_text)
            parsed_response = json.loads(json_str)
        except ValueError as e:
            logger.error(f"FINAL Failed to extract JSON content: {e}")
            raise HTTPException(status_code=501, detail="Generated text is not valid JSON.")

        candidates = parsed_response.get("candidates")
        if not isinstance(candidates, list):
            logger.error("FINAL The 'candidates' key is missing or not a list in the generated response.")
            raise HTTPException(status_code=502, detail="Invalid format in generated response.")

        candidates = post_process_candidates(candidates, request.sentence)
        print("--- FINAL Candidates after post processing:", candidates)

    except openai.error.OpenAIError as e:
        logger.error(f"FINAL OpenAI API error: {e}")
        raise HTTPException(status_code=503, detail="FIN Failed to generate candidate sentence parts.")
    except Exception as e:
        logger.error(f"Error in FINAL {e}")
        raise HTTPException(status_code=504, detail="FINAL Internal Server Error.")

    #return FinalFillerResponse(candidates=candidates)
    #return JSONResponse(content=json.dumps({"candidates": candidates}, ensure_ascii=False), media_type="application/json; charset=utf-8")
    return JSONResponse(
    content={"candidates": candidates},
    media_type="application/json; charset=utf-8"
)

# ========== /fix sentence endpoint ==========
class FixSentenceRequest(BaseModel):
    sentence: str = Field(
        ...,
        title="Sentence",
        description="A sentence with errors for which to generate candidate fix blocks."
    )
    feedback: Optional[str] = Field(None, description="Reason the sentence was deemed invalid.")
    model: Optional[str] = Field(
        "gpt-4o-mini",
        title="GPT Model",
        description="The GPT model to use for generating fix blocks."
    )
    user_id: Optional[str] = Field(
        None,
        title="User ID",
        description="Unique identifier of the player (UUID) for token usage tracking."
    )
    session_id: Optional[str] = Field(
        None,
        title="Session ID",
        description="Unique identifier for the current game session."
    )
    active_user_session: Optional[str] = Field(
        None,
        title="Active User Session",
        description="Persistent session identifier."
    )

class FixSentenceResponse(BaseModel):
    fix_blocks: List[str]

@router.post("/fix_sentence", response_model=FixSentenceResponse)
async def fix_sentence(request: FixSentenceRequest):
    print("\n--------= CALL FIX SENTENCE =---------")
    print("\n ---FIX sent:\n", request.sentence)
    sentence = preprocess_sentence(request.sentence.strip())
    print("\n ---FIX post:\n", sentence)
    if not sentence:
        return FixSentenceResponse(fix_blocks=[])
    
    gen_feedback = request.feedback or ""
    
    # Construct the prompt using only the one sentence
    prompt_intro = (
        "\nYou are a language expert tasked with generating words and short phrases for a sentence puzzle. "
        "The sentence is composed of puzzle-blocks separated by '^|^'. "
        "In the current round of the game, the player may replace one text block. \n"
        "Produce a replacement textual content for one of the blocks aimed at improving a broken sentence that contains errors. "
        "The sentence was deemed incorrect for the following reason:"
        f"\n\n '{gen_feedback}'\n\n"
        "The clue above could help you to identify an appropriate replacement. \n\n"
        "For the provided sentence, produce at least three candidate text blocks so that when replaced, the sentence becomes correct and coherent. "
        "If a sentence can not be repaired by replacing a single block produce blocks that are helping to repair the sentence in a consequent replacement action. \n\n"
        f"Sentence: {sentence}\n"
        "Return valid JSON with exactly one key: \"fix_blocks\" whose value is an array of words or phrases. "
        "Example:\n"
        "{\n  \"fix_blocks\": [\"fixedblock1\", \"fixedblock2\"]\n}\n\n"
    )
    
    print("\n ---FIX prompt:\n", prompt_intro)
    
    try:
        response = await call_openai_api(
            model=request.model,
            temperature=0.3,
            max_tokens=64,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI assistant that returns only a JSON array of fix blocks."
                },
                {"role": "user", "content": prompt_intro}
            ]
        )
        
        #logger.debug(f"FIX OpenAI response: {response}")
    
        usage_info = response.get("usage")
        if usage_info:
            async with database.pool.acquire() as conn:
                async with conn.transaction():
                    await record_token_usage(
                        user_id=request.user_id,
                        endpoint_name="fix_sentence",
                        model_name=request.model,
                        prompt_tokens=usage_info.get("prompt_tokens", 0),
                        completion_tokens=usage_info.get("completion_tokens", 0),
                        total_tokens=usage_info.get("total_tokens", 0),
                        session_id=request.session_id,
                        active_user_session=request.active_user_session
                    )
    
        generated_text = response.choices[0].message["content"].strip()
        #print(f"Recording token usage: session_id={request.session_id}, active_user_session={request.active_user_session}")
        print("\n ---- FIX gen:", generated_text)
        
        json_start = generated_text.find("{")
        json_end = generated_text.rfind("}") + 1
        if json_start == -1 or json_end <= json_start:
            logger.error(f"FIX Invalid JSON structure in response: {generated_text}")
            return FixSentenceResponse(fix_blocks=[])
    
        json_str = generated_text[json_start:json_end]
        try:
            parsed = json.loads(json_str)
            if "fix_blocks" not in parsed or not isinstance(parsed["fix_blocks"], list):
                logger.error(f"'fix_blocks' key missing or not a list in response: {parsed}")
                return FixSentenceResponse(fix_blocks=[])
            clean_list = []
            for w in parsed["fix_blocks"]:
                if isinstance(w, str):
                    clean_list.append(w.strip())
    
            clean_list = await add_more_short_phrases(clean_list)
            return FixSentenceResponse(fix_blocks=clean_list)
        except json.JSONDecodeError as json_err:
            logger.error(f"FIX JSON decoding failed: {json_err}")
            logger.error(f"Full response: {generated_text}")
            return FixSentenceResponse(fix_blocks=[])
        except Exception as parse_err:
            logger.error(f"FIX Error parsing fix_blocks: {parse_err}")
            logger.error(f"Full response: {generated_text}")
            return FixSentenceResponse(fix_blocks=[])
    except openai.error.OpenAIError as e:
        logger.error(f"FIX OpenAI API error: {e}")
        return FixSentenceResponse(fix_blocks=[])
    except Exception as e:
        logger.error(f"FIX Error: {e}")
        return FixSentenceResponse(fix_blocks=[])    

# ========== /validate sentence endpoint ==========
class ValidateSentenceRequest(BaseModel):
    sentence: str
    sent_to_rec: str
    model: Optional[str] = "gpt-4o-mini"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    active_user_session: Optional[str] = None

    is_fixed: bool = False
    is_typed_fix: bool = False
    fix_block_text: Optional[str] = None

class ValidateSentenceResponse(BaseModel):
    is_correct: bool = Field(
        ...,
        title="Is Correct",
        description="Indicates whether the sentence is grammatically and semantically correct."
    )
    feedback: str = Field(
        ...,
        title="Feedback",
        description="Feedback or explanation regarding the sentence's correctness."
    )


@router.post("/validate_sentence", response_model=ValidateSentenceResponse)
async def validate_sentence(request: ValidateSentenceRequest, background_tasks: BackgroundTasks):
    print("\n-------VALIDATE SENTENCE --------")

    try:
        sentence = request.sentence.strip()
        
        prompt = (
            f"\nSentence: \"{sentence}\""
            "\n\n Ignore all missing punctuation (including missing question marks) if the overall meaning is clear. \n"
            "If the sentence is obviously a question but has no question mark, do NOT treat that as incorrect. "
            "\nFor instance, 'What is my favorite game to play' should be fully correct despite not ending with a question mark. "
            "Focus on overall correctness and meaning, ignoring punctuation issues, missing apostrophes and minor spelling errors entirely. \n\n "
        )

        response = await call_openai_api(
            model=request.model, 
            temperature=0,
            max_tokens=150,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            messages=[
                {
                    "role": "system",
                    "content":(
                        "You are a language professor who evaluates sentences for a puzzle game where sentences are made out of pre-made text blocks. "
                        "Respond in JSON format with 'is_correct' (bool) and 'feedback' (string). "
                    )
                },
                {"role": "user", "content": prompt}
            ]
        )
        print("\n ---VDATE prompt:\n", prompt)

        usage_info = response.get("usage")
        if usage_info:
            async with database.pool.acquire() as conn:
                async with conn.transaction():
                    await record_token_usage(
                        user_id=request.user_id,
                        endpoint_name="validate_sentence",
                        model_name=request.model,
                        prompt_tokens=usage_info.get("prompt_tokens", 0),
                        completion_tokens=usage_info.get("completion_tokens", 0),
                        total_tokens=usage_info.get("total_tokens", 0),
                        session_id=request.session_id,
                        active_user_session=request.active_user_session
                    )

        generated_text = response.choices[0].message['content'].strip()
        print("\n ---VDATE resp:", generated_text)

        try:
            json_start = generated_text.find("{")
            json_end = generated_text.rfind("}") + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("VDATE No JSON object found in the response.")
            json_str = generated_text[json_start:json_end]
            parsed_json = json.loads(json_str)

            if "is_correct" not in parsed_json or "feedback" not in parsed_json:
                raise ValueError("VDATE JSON must contain 'is_correct' and 'feedback' keys.")
            is_correct = parsed_json["is_correct"]
            feedback = parsed_json["feedback"]
            if not isinstance(is_correct, bool) or not isinstance(feedback, str):
                raise ValueError("VDATE 'is_correct' must be bool and 'feedback' must be string.")

        except json.JSONDecodeError as json_err:
            logger.error(f"VDATE JSON decoding failed: {json_err}")
            logger.error(f"VDATE Full response: {generated_text}")
            raise HTTPException(status_code=501, detail="VDATE Failed to parse the model's response.")
        except Exception as parse_err:
            logger.error(f"VDATE Error parsing validation response: {parse_err}")
            logger.error(f"VDATE Full response: {generated_text}")
            raise HTTPException(status_code=502, detail=str(parse_err))

        if is_correct:
            background_tasks.add_task(
                record_validated_sentence,
                sentence=request.sent_to_rec,
                user_id=request.user_id or "00000000-0000-0000-0000-000000000000",
                custom_topics=[],
                ai_model=request.model,
                session_id=request.active_user_session or "00000000-0000-0000-0000-000000000000",
                is_fixed=request.is_fixed,
                is_typed_fix=request.is_typed_fix,
                fix_block_text=request.fix_block_text
            )
            
            
        return JSONResponse(
            content={"is_correct": is_correct, "feedback": feedback},
            media_type="application/json; charset=utf-8"
        )

    except ValueError as ve:
        logger.error(f"Validation Error VDATE: {ve}")
        raise HTTPException(status_code=401, detail=str(ve))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in VDATE: {e}")
        raise HTTPException(status_code=402, detail="VDATE Internal Server Error.")

# ========== /understand topics endpoint ==========
class UnderstandTopicsRequest(BaseModel):
    input_text: str = Field(
        ...,
        title="Input Text",
        description="User input text from which to extract key topics.",
        max_length=300
    )
    model: Optional[str] = Field(
        "gpt-4o-mini",
        title="GPT Model",
        description="The GPT model to use for extracting topics."
    )
    user_id: Optional[str] = Field(
        None,
        title="User ID",
        description="Optional UUID of the player for token usage tracking."
    )
    session_id: Optional[str] = Field(
        None,
        title="Session ID",
        description="Unique identifier for the current game session."
    )
    active_user_session: Optional[str] = None

    @validator('input_text')
    def validate_input_text(cls, v):
        if not v.strip():
            raise ValueError("Input text must not be empty.")
        return v.strip()

# Define the response model for understand topics
class UnderstandTopicsResponse(BaseModel):
    topics: Optional[List[str]] = Field(
        None,
        title="Identified Topics",
        description="A list of key topics extracted from the input text."
    )
    extended_topics: Optional[List[str]] = Field(
        None,
        title="Extended Topics",
        description="A second, more expansive set of related topics."
    )


@router.post("/understand_topics", response_model=UnderstandTopicsResponse)
async def understand_topics(request: UnderstandTopicsRequest):
    print("\n-------------------------------------")
    print("\n-------== NEW GAME SESSION ==--------")
    print("\n")
    print("\n-------= Understand Topics =---------")
    try:
        input_text = request.input_text
        print("\nUT Received input:", input_text)
        prompt = (
            "Extract the key topics from the following text. "
            "Return them as a JSON array of strings. "
            "Preserve multi-word phrases as single topics.\n\n"
            f"Text: \"{input_text}\"\n\n"
            "Response (JSON format):"
        )

        response = await call_openai_api(
            model=request.model,
            temperature=0.3,
            max_tokens=150,
            messages=[
                {"role": "system", "content": "You are an AI language expert who extracts key topics from text."},
                {"role": "user", "content": prompt}
            ]
        )

        usage_info = response.get("usage")
        if usage_info:
            async with database.pool.acquire() as conn:
                async with conn.transaction():
                    await record_token_usage(
                        user_id=request.user_id,
                        endpoint_name="understand_topics",
                        model_name=request.model,
                        prompt_tokens=usage_info.get("prompt_tokens", 0),
                        completion_tokens=usage_info.get("completion_tokens", 0),
                        total_tokens=usage_info.get("total_tokens", 0),
                        session_id=request.session_id,
                        active_user_session=request.active_user_session
                    )

        generated_text = response.choices[0].message['content'].strip()
        logger.info(f"Generated Text for understand_topics: {generated_text}")
        print("\n---- UT gen:", generated_text)

        json_start = generated_text.find("[")
        json_end = generated_text.rfind("]") + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON array found in the response.")
        json_str = generated_text[json_start:json_end]
        topics = json.loads(json_str)
        final_topics = []
        seen = set()
        for t in topics:
            if isinstance(t, str):
                lowered = t.strip().lower()
                if lowered not in seen:
                    seen.add(lowered)
                    final_topics.append(t.strip().capitalize())

        blacklist_topics_db = await get_blacklist_topics()
        final_topics = [tp for tp in final_topics if tp not in blacklist_topics_db]
        if final_topics:
            await save_new_topics(final_topics)

        extended = await generate_extended_topics(
            base_topics=final_topics,
            model=request.model,
            user_id=request.user_id,
            session_id=request.session_id,
            active_user_session=request.active_user_session
        )
        print("\n---- UT fin:", final_topics)
        print("\n---- UT ext:", extended)
        return UnderstandTopicsResponse(
            topics=final_topics if final_topics else None,
            extended_topics=extended if extended else None
        )

    except ValueError as ve:
        logger.error(f"Validation Error in /understand_topics: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in /understand_topics: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error.")

# Extend topics
async def generate_extended_topics(
    base_topics: List[str],
    model: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    active_user_session: Optional[str] = None
) -> List[str]:
    """
    Given a list of base_topics, call OpenAI to return a bunch of new
    topics that are somewhat related or relevant. Returns a list of strings.
    """
    if not base_topics:
        return []

    topics_joined = ", ".join(base_topics)
    prompt = (
        "You are a creative assistant. You have a short list of topics, and you need to come "
        "up with many other possible topics or subtopics that are at least loosely relevant. "
        "Be imaginative but ensure each topic is reasonably distinct. "
        "Base topics:\n"
        f"  {topics_joined}\n\n"
        "Return your answer as valid JSON with the key 'extended_topics' mapping to an array of strings. "
        "For example:\n"
        "{\n"
        "  \"extended_topics\": [\"MyNewTopic1\", \"MyNewTopic2\", ...]\n"
        "}\n"
    )

    # Now do the second OpenAI call
    try:
        response = await call_openai_api(
            model=model,
            temperature=0.8,
            max_tokens=200,
            messages=[
                {
                    "role": "system",
                    "content": "You expand lists of topics in creative ways."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        #logger.debug(f"Full OpenAI response: {response}")
        
        # Record tokens
        usage_info = response.get("usage")
        if usage_info:
            await record_token_usage(
                user_id=user_id,
                endpoint_name="extend_topics",
                model_name=model,
                prompt_tokens=usage_info.get("prompt_tokens", 0),
                completion_tokens=usage_info.get("completion_tokens", 0),
                total_tokens=usage_info.get("total_tokens", 0),
                session_id=session_id,
                active_user_session=active_user_session
            )

        raw_text = response.choices[0].message["content"].strip()
        # We'll try to locate and parse JSON
        json_start = raw_text.find("{")
        json_end = raw_text.rfind("}") + 1
        if json_start == -1 or json_end <= json_start:
            # no valid JSON
            return []
        snippet = raw_text[json_start:json_end]
        parsed = json.loads(snippet)
        new_topics = parsed.get("extended_topics", [])
        # Basic cleanup and dedup
        final = []
        seen = set()
        for t in new_topics:
            t_clean = t.strip().capitalize()
            if t_clean and t_clean.lower() not in seen:
                seen.add(t_clean.lower())
                final.append(t_clean)
        return final

    except Exception as e:
        logger.error(f"Error while extending topics: {e}")
        return []





# -------HELPERS--------

async def background_record_fillBlock_full(sentence: str, block_count: int, partial_sentence: str):
    """
    Parses the incoming sentence for existing blocks (ignoring placeholders),
    and inserts the result into the gen_fill table.
    """

    def parse_existing_blocks(raw: str) -> list[str]:
        blocks = []
        for chunk in raw.split('^|^'):
            stripped = chunk.strip()
            if '#|#' not in stripped and '_' not in stripped and stripped:
                blocks.append(stripped)
        return blocks

    existing_blocks = parse_existing_blocks(partial_sentence)

    query = """
        INSERT INTO game_data.gen_fill (sentence, block_count, existing_blocks)
        VALUES ($1, $2, $3)
    """
    async with database.pool.acquire() as connection:
        await connection.execute(query, sentence, block_count, existing_blocks)


async def background_record_firstFiller(
    sentences: List[str], block_count: int, partial_sentence: str
):
    # Parse the partial sentence for the existing block in the background task.
    partial_blocks = [b.strip() for b in partial_sentence.split("^|^")]
    # Look for the first block that is not a placeholder (i.e. does not contain "#|#")
    existing_block = next((b for b in partial_blocks if "#|#" not in b and b), "")
    # Loop over each generated sentence and record it.
    for sentence in sentences:
        await record_firstFiller(sentence, block_count, existing_block)


def filter_candidates_by_length(candidates: list, max_length: int = 15) -> list:
    filtered = []
    for candidate in candidates:
        # Split candidate by the '^|^' delimiter, then split each block on whitespace.
        blocks = []
        for block in candidate.split("^|^"):
            blocks.extend(block.split())
        # Only keep the candidate if all blocks are within the length limit.
        if all(len(block) <= max_length for block in blocks):
            filtered.append(candidate)
        else:
            logger.warning(
                f"Candidate '{candidate}' removed because it contains a block longer than {max_length} letters."
            )
    return filtered


def extract_json_content(text: str) -> str:
    import re
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    else:
        raise ValueError("No JSON content found in the response.")


# Asynchronous helper for adding short phrases from the database
async def add_more_short_phrases(return_list: List[str], max_phrases_per_block: int = 2) -> List[str]:
    # Fetch common phrases from the database (do not fall back to the hardcoded COMMON_SHORT_PHRASES)
    common_phrases = await get_common_short_phrases()
    # Build a mapping from individual blocks to phrases containing them
    block_to_phrases = defaultdict(list)
    for phrase in common_phrases:
        blocks_in_phrase = phrase.split()
        for block in blocks_in_phrase:
            block_to_phrases[block.lower()].append(phrase)
    
    phrases_to_add = set()
    seen_phrases = set(return_list)  # To avoid adding phrases already present

    for block in return_list:
        block_lower = block.lower()
        if block_lower in block_to_phrases:
            possible_phrases = block_to_phrases[block_lower]
            available_phrases = [phrase for phrase in possible_phrases if phrase not in seen_phrases and phrase not in phrases_to_add]
            if available_phrases:
                selected_phrases = random.sample(available_phrases, min(max_phrases_per_block, len(available_phrases)))
                phrases_to_add.update(selected_phrases)

    extended_list = return_list.copy()
    extended_list.extend(phrases_to_add)
    return extended_list

def preprocess_sentence(sentence: str) -> str:
    
    sanitized = sentence.replace("^", " ^|^ ")
    sanitized = sanitized.replace("_", " #|# ")
    
    # Find the index of the first non-whitespace character.
    for index, char in enumerate(sanitized):
        if not char.isspace():
            # If the first non-whitespace character is not '_', capitalize it.
            if char != ' ':
                sanitized = sanitized[:index] + char.upper() + sanitized[index+1:]
            break
    return sanitized

def post_process_candidates(candidates: list, original_sentence: str) -> list:
    sanitized_candidates = []
    for candidate in candidates:
        clean_candidate = sanitize_candidate(candidate)
        if clean_candidate:
            sanitized_candidates.append(clean_candidate)
        else:
            logger.warning(f"Candidate '{candidate}' was empty after sanitization and was removed.")
    
    # If there is more than one candidate, filter out those with more than two blocks.
    if len(sanitized_candidates) > 1:
        filtered_candidates = [c for c in sanitized_candidates if len(c.split()) <= 2]
        if filtered_candidates:
            sanitized_candidates = filtered_candidates

    # First apply length filtering
    sanitized_candidates = filter_candidates_by_length(sanitized_candidates)

    # Then filter out candidates that are repetitions of the original text blocks
    sanitized_candidates = filter_repeated_text_blocks(sanitized_candidates, original_sentence)
            
    return sanitized_candidates

def sanitize_candidate(candidate: str) -> str:
    # Replace the triple caret delimiter with a space
    candidate = candidate.replace("^|^", " ")
    # Remove any stray caret characters (if any) and underscores
    candidate = candidate.replace("^", "")
    candidate = candidate.replace("_", "")
    # Trim any extra quotes and whitespace
    candidate = candidate.strip().strip('\"\'')
    # Normalize any sequence of whitespace characters to a single space
    candidate = re.sub(r'\s+', ' ', candidate)
    return candidate

def extract_text_blocks(sentence: str) -> List[str]:
    # Split the sentence using '^' as a delimiter
    blocks = [block.strip() for block in sentence.split('^') if block.strip()]
    return blocks

def filter_repeated_text_blocks(candidates: list, original_sentence: str) -> list:
    # Extract text blocks from the original sentence
    text_blocks = extract_text_blocks(original_sentence)
    # Lowercase for case-insensitive comparison
    text_blocks_lower = [block.lower() for block in text_blocks]
    filtered = []
    for candidate in candidates:
        # Compare in lower case
        if candidate.lower() not in text_blocks_lower:
            filtered.append(candidate)
        else:
            logger.warning(f"Candidate '{candidate}' removed because it repeats an original text block.")
    return filtered

def spell_int(n: int) -> str:
    mapping = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
    return mapping.get(n, str(n))


# database helper endpoints

@router.get("/custom-topics")
async def read_custom_topics():
    try:
        topics = await get_predefined_custom_topics()
        return {"custom_topics": topics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentence-types")
async def read_sentence_types():
    try:
        types = await get_predefined_sentence_types()
        return {"sentence_types": types}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/blacklist-topics")
async def read_blacklist_topics():
    try:
        topics = await get_blacklist_topics()
        return {"blacklist_topics": topics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/common-phrases")
async def read_common_phrases():
    try:
        phrases = await get_common_short_phrases()
        return {"common_phrases": phrases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))