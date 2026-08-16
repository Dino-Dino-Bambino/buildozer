[app]

# (str) Title of your application
title = Quiz App

# (str) Package name
package.name = quizapp

# (str) Package domain (needed for android packaging)
package.domain = org.test

# (str) Source code directory
source.dir = .

# (list) Source files to include (extensions)
source.include_exts = py,png,jpg,kv,atlas

# (str) Application versioning
version = 0.1

# (list) Application requirements
# Зафиксирована стабильная версия Kivy для предотвращения ошибок Cython
requirements = python3==3.11.11,kivy==2.3.0

# (str) Supported orientations
orientation = portrait

# (int) Fullscreen mode
fullscreen = 0

# ==========================================
# Настройки Android SDK / NDK для GitHub
# ==========================================

# (str) Жесткий путь к SDK на серверах GitHub Actions
android.sdk_path = /usr/local/lib/android/sdk

# (str) Жесткий путь к NDK на серверах GitHub Actions
android.ndk_path = /usr/local/lib/android/sdk/ndk/26.1.10909125

# (int) Target Android API (соответствует настройкам сервера)
android.api = 34

# (str) Android NDK version to use
android.ndk = 26b

# (int) Minimum API your APK will support
android.minapi = 21

# (str) Android architectures to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) Accept SDK license without operator input
android.accept_sdk_license = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug and error)
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
