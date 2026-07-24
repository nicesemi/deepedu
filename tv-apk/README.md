# DeepEdu TV — Android TV APK

全屏 WebView 包装 [deepedu.school/tv.html](https://deepedu.school/tv.html)，适配 Android TV 遥控器交互，支持语音控制与双击返回退出。

## 功能

- 全屏加载 deepedu.school TV 版教育界面
- Android SpeechRecognizer 语音控制（说"退出"/"返回"/"关闭"退出全屏）
- 双击返回键退出应用，防止误触
- 桌面版 User-Agent，兼容 TV 大屏
- 禁止缩放，支持 JavaScript 与 DOM Storage

## 构建要求

| 工具 | 版本 |
|---|---|
| Android Studio | Hedgehog (2023.1) 或更高 |
| Gradle | 8.4+ |
| Android Gradle Plugin | 8.2.0 |
| compileSdk / targetSdk | 34 |
| minSdk | 21 (Android 5.0) |

## 构建步骤

### 方式一：Android Studio

1. 用 Android Studio 打开 `tv-apk/` 目录
2. 等待 Gradle Sync 完成
3. `Build > Build Bundle(s) / APK(s) > Build APK(s)`
4. APK 输出在 `app/build/outputs/apk/debug/app-debug.apk`

### 方式二：命令行

```bash
cd tv-apk

# macOS / Linux
./gradlew assembleDebug

# Windows
gradlew.bat assembleDebug
```

APK 输出位置：`app/build/outputs/apk/debug/app-debug.apk`

### 生成 Release APK

```bash
./gradlew assembleRelease
```

## 配置

默认加载的 URL 定义在 `app/src/main/res/values/strings.xml`：

```xml
<string name="default_url">https://deepedu.school/tv.html</string>
```

修改此值即可切换目标页面，无需改动 Java 代码。

## 安装到 TV

```bash
# 通过 ADB 安装
adb install app/build/outputs/apk/debug/app-debug.apk

# 或通过 U 盘拷贝 APK 到 TV 后使用文件管理器安装
```

## 权限说明

| 权限 | 用途 |
|---|---|
| INTERNET | 加载 Web 页面 |
| ACCESS_NETWORK_STATE | 检测网络状态 |
| RECORD_AUDIO | 语音识别控制（可选，无麦克风设备不影响使用） |

## 项目结构

```
tv-apk/
├── build.gradle              # 根构建文件（AGP 8.2.0）
├── settings.gradle            # 项目设置
├── gradle.properties          # Gradle 属性
├── gradle/wrapper/
│   └── gradle-wrapper.properties  # Gradle 8.4 wrapper 配置
├── README.md
└── app/
    ├── build.gradle           # 应用构建文件
    ├── proguard-rules.pro     # ProGuard 混淆规则
    └── src/main/
        ├── AndroidManifest.xml
        ├── java/com/deepedu/tv/
        │   └── MainActivity.java
        ├── res/
        │   ├── drawable/      # 图标与横幅
        │   ├── mipmap-anydpi-v26/  # 自适应图标
        │   └── values/
        │       └── strings.xml
