package com.deepedu.tv;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.view.KeyEvent;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;

import java.util.ArrayList;

/**
 * DeepEdu TV — 全屏 WebView 包装 deepedu.school/tv.html。
 *
 * 特性：
 * - 默认加载 https://deepedu.school/tv.html（可通过 strings.xml 配置）
 * - Android SpeechRecognizer 语音控制（"退出"/"返回"/"关闭"）
 * - 双击返回键退出应用（防误触）
 * - 适配 Android TV 遥控器（D-Pad / 返回键）
 * - 禁止缩放，桌面 UA 避免移动端重定向
 */
public class MainActivity extends Activity {

    private WebView webView;
    private SpeechRecognizer speechRecognizer;
    private Intent speechIntent;
    private boolean isListening = false;

    // 双击返回相关
    private long lastBackPressTime = 0;
    private static final long BACK_PRESS_INTERVAL = 2000; // 2 秒内双击退出

    // 可配置的默认 URL
    private String targetUrl;

    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 读取可配置 URL（优先从 strings.xml，其次硬编码兜底）
        targetUrl = getString(R.string.default_url);
        if (targetUrl.isEmpty()) {
            targetUrl = "https://deepedu.school/tv.html";
        }

        // 全屏 WebView
        webView = new WebView(this);
        webView.setLayoutParams(new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));
        setContentView(webView);

        configureWebView();
        webView.loadUrl(targetUrl);

        initSpeechRecognition();
    }

    // ---------- WebView 配置 ----------

    private void configureWebView() {
        WebSettings settings = webView.getSettings();

        // JavaScript & DOM Storage
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);

        // 禁用缩放（电视上无触摸，缩放无意义）
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);

        // 桌面版 User-Agent，避免 mobile 重定向
        settings.setUserAgentString(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        + "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36");

        // 适配 TV 屏幕
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);

        // 允许混合内容（http/https）
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        // WebViewClient — 页面在 WebView 内打开，不跳系统浏览器
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                view.loadUrl(request.getUrl().toString());
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
            }
        });

        // WebChromeClient — 支持全屏视频等
        webView.setWebChromeClient(new WebChromeClient());
    }

    // ---------- 语音识别 ----------

    private void initSpeechRecognition() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            return; // 设备不支持语音识别
        }

        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
        speechIntent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        speechIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        speechIntent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "zh-CN");
        speechIntent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        speechIntent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);

        speechRecognizer.setRecognitionListener(new RecognitionListener() {
            @Override
            public void onReadyForSpeech(Bundle params) {}

            @Override
            public void onBeginningOfSpeech() {}

            @Override
            public void onRmsChanged(float rmsdB) {}

            @Override
            public void onBufferReceived(byte[] buffer) {}

            @Override
            public void onEndOfSpeech() {}

            @Override
            public void onError(int error) {
                // 出错后自动重启监听
                if (isListening) {
                    restartListening();
                }
            }

            @Override
            public void onResults(Bundle results) {
                processSpeechResults(results);
                if (isListening) {
                    restartListening();
                }
            }

            @Override
            public void onPartialResults(Bundle partialResults) {
                processSpeechResults(partialResults);
            }

            @Override
            public void onEvent(int eventType, Bundle params) {}
        });
    }

    private void processSpeechResults(Bundle results) {
        ArrayList<String> matches = results.getStringArrayList(
                SpeechRecognizer.RESULTS_RECOGNITION);
        if (matches == null || matches.isEmpty()) return;

        for (String text : matches) {
            String t = text.trim();
            if (t.contains("退出") || t.contains("返回") || t.contains("关闭")) {
                mainHandler.post(() -> {
                    // 模拟 WebView 内的 ESC 键，让 tv.html 的 fullscreen 逻辑处理
                    // 同时也可以通过 JS 直接控制
                    webView.evaluateJavascript(
                        "if(document.fullscreenElement)document.exitFullscreen();", null);
                    Toast.makeText(MainActivity.this,
                        "语音指令: " + t, Toast.LENGTH_SHORT).show();
                });
                return;
            }
        }
    }

    private void startListening() {
        if (speechRecognizer == null || isListening) return;
        isListening = true;
        try {
            speechRecognizer.startListening(speechIntent);
        } catch (Exception ignored) {
            isListening = false;
        }
    }

    private void stopListening() {
        if (speechRecognizer == null) return;
        isListening = false;
        try {
            speechRecognizer.stopListening();
        } catch (Exception ignored) {}
    }

    private void restartListening() {
        mainHandler.postDelayed(() -> {
            if (isListening && speechRecognizer != null) {
                try {
                    speechRecognizer.startListening(speechIntent);
                } catch (Exception ignored) {}
            }
        }, 300);
    }

    // ---------- 遥控器按键处理 ----------

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            // 优先 WebView 内部回退
            if (webView.canGoBack()) {
                webView.goBack();
                return true;
            }
            // 双击返回退出应用
            long now = System.currentTimeMillis();
            if (now - lastBackPressTime < BACK_PRESS_INTERVAL) {
                finish();
                return true;
            } else {
                lastBackPressTime = now;
                Toast.makeText(this, "再按一次返回键退出", Toast.LENGTH_SHORT).show();
                return true;
            }
        }
        return super.onKeyDown(keyCode, event);
    }

    // ---------- 生命周期 ----------

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
        startListening();
    }

    @Override
    protected void onPause() {
        super.onPause();
        webView.onPause();
        stopListening();
    }

    @Override
    protected void onDestroy() {
        stopListening();
        if (speechRecognizer != null) {
            speechRecognizer.cancel();
            speechRecognizer.destroy();
            speechRecognizer = null;
        }
        if (webView != null) {
            webView.loadUrl("about:blank");
            webView.clearHistory();
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
