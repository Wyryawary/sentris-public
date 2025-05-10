// file: info.dart | purpose: typing up info from the database when the user choses the LEARN option in the Main Menu (main.dart) 
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'main.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'config.dart';
import 'package:flutter/gestures.dart';
import 'package:url_launcher/url_launcher.dart';

class InfoPage extends StatefulWidget {
  const InfoPage({super.key});

  @override
  InfoPageState createState() => InfoPageState();
}

class InfoPageState extends State<InfoPage> with TickerProviderStateMixin {
  String fullText = "";
  String displayedText = "";

  late AnimationController _controller;
  late Animation<int> _textAnimation;

  Color textColor = Colors.white;
  Color backgroundColor = Colors.black;
  Color frameColor = Colors.white;

  bool _typingFinished = false;

  @override
  void initState() {
    super.initState();
    _loadThemeSettings();
    _fetchInfoText();

    // Initialize Animation Controller
    _controller = AnimationController(
      vsync: this,
      duration:
          const Duration(milliseconds: 9999), // Adjust the speed as desired
    );

    // Once the animation completes, set _typingFinished = true so we don't intercept taps.
    _controller.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        setState(() {
          _typingFinished = true;
        });
      }
    });
  }

  Future<void> _fetchInfoText() async {
    try {
      final response = await http.get(Uri.parse(infoEndpoint));
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          fullText = data['info_text'];
          _startTypingEffect();
        });
      }
    } catch (e) {
      debugPrint("Error fetching info text: $e");
    }
  }

  Future<void> _loadThemeSettings() async {
    final prefs = await SharedPreferences.getInstance();
    int textIndex = prefs.getInt('textColorIndex') ?? 0;
    int frameIndex = prefs.getInt('frameColorIndex') ?? 0;
    int bgIndex = prefs.getInt('backgroundColorIndex') ?? 0;

    setState(() {
      textColor = availableColors[textIndex];
      frameColor = availableColors[frameIndex];
      backgroundColor = availableColors[bgIndex];
    });
  }

  TextSpan _buildMarkdownTextSpan(String text, TextStyle baseStyle) {
    final RegExp exp = RegExp(
      r'(\*\*\*[^*]+\*\*\*|\*\*[^*]+\*\*|_[^_]+_|(\[.+?\]\(.+?\))|[^\[*_]+)',
      dotAll: true,
    );

    final List<TextSpan> spans = [];
    final matches = exp.allMatches(text);

    for (final match in matches) {
      String segment = match.group(0)!;

      // Handle Bold + Italic
      if (segment.startsWith("***") && segment.endsWith("***")) {
        final inner = segment.substring(3, segment.length - 3);
        spans.add(TextSpan(
          text: inner,
          style: baseStyle.merge(const TextStyle(
            fontWeight: FontWeight.bold,
            fontStyle: FontStyle.italic,
          )),
        ));
      }
      // Bold
      else if (segment.startsWith("**") && segment.endsWith("**")) {
        final inner = segment.substring(2, segment.length - 2);
        spans.add(TextSpan(
          text: inner,
          style: baseStyle.merge(const TextStyle(fontWeight: FontWeight.bold)),
        ));
      }
      // Italic
      else if (segment.startsWith("_") && segment.endsWith("_")) {
        final inner = segment.substring(1, segment.length - 1);
        spans.add(TextSpan(
          text: inner,
          style: baseStyle.merge(const TextStyle(fontStyle: FontStyle.italic)),
        ));
      }
      // Markdown Link (Main improvement here)
      else if (segment.startsWith("[") && segment.contains("](")) {
        final int endOfText = segment.indexOf("](");
        final String linkText = segment.substring(1, endOfText);
        final String linkUrl =
            segment.substring(endOfText + 2, segment.length - 1);

        spans.add(TextSpan(
          text: linkText,
          style: baseStyle.merge(const TextStyle(
            color: Colors.blue,
            decoration: TextDecoration.underline,
          )),
          recognizer: TapGestureRecognizer()
            ..onTap = () async {
              final uri = Uri.parse(linkUrl);
              if (await canLaunchUrl(uri)) {
                await launchUrl(uri, webOnlyWindowName: '_blank');
              } else {
                debugPrint('Could not launch $linkUrl');
              }
            },
        ));
      }
      // Normal Text
      else {
        spans.add(TextSpan(
          text: segment,
          style: baseStyle,
        ));
      }
    }

    return TextSpan(children: spans, style: baseStyle);
  }

  void _startTypingEffect() {
    _textAnimation =
        IntTween(begin: 0, end: fullText.length).animate(_controller)
          ..addListener(() {
            setState(() {
              displayedText = fullText.substring(0, _textAnimation.value);
            });
          });

    _controller.forward();
  }

  void _skipTypingEffect() {
    _controller.stop();
    setState(() {
      displayedText = fullText;
      _typingFinished = true;
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final String fontFamily =
        FontSettingsProvider.of(context).currentFontFamily;
    final TextStyle baseStyle = TextStyle(
      fontSize: 18,
      color: textColor,
      fontFamily: fontFamily,
    );

    return Scaffold(
      backgroundColor: backgroundColor,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 20, bottom: 10),
              child: Text(
                'LEARN',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: textColor,
                  fontFamily: fontFamily,
                ),
              ),
            ),
            Expanded(
              // Only intercept taps while typing is in progress
              child: GestureDetector(
                behavior: _typingFinished
                    ? HitTestBehavior.deferToChild
                    : HitTestBehavior.opaque,
                onTap: _typingFinished ? null : _skipTypingEffect,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    child: RichText(
                      text: _buildMarkdownTextSpan(displayedText, baseStyle),
                    ),
                  ),
                ),
              ),
            ),
            Container(
              decoration: BoxDecoration(
                border: Border(
                  top: BorderSide(color: frameColor, width: 2),
                ),
              ),
              padding: const EdgeInsets.only(
                  left: 20.0, right: 20.0, top: 10.0, bottom: 10.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      side: BorderSide(color: frameColor, width: 2),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.zero,
                      ),
                      backgroundColor: Colors.transparent,
                    ),
                    onPressed: () {
                      Navigator.pop(context);
                    },
                    child: Text(
                      'BACK',
                      style: TextStyle(
                        fontSize: 20,
                        color: textColor,
                        fontFamily: fontFamily,
                      ),
                    ),
                  ),
                  Text(
                    'LEARN',
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: textColor,
                      fontFamily: fontFamily,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
