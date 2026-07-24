# ProGuard rules for DeepEdu TV

# Keep WebView
-keep class android.webkit.** { *; }
-dontwarn android.webkit.**

# Keep JavaScript interfaces (if any added later)
-keepattributes JavascriptInterface
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# Keep SpeechRecognizer
-keep class android.speech.** { *; }
-dontwarn android.speech.**
