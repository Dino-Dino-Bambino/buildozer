[app]
title = Quiz App
package.name = quizapp
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1

requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 0

# (int) Target Android API, should be as high as possible.
android.api = 34

# (str) Android NDK version to use
android.ndk = 26b

# (int) minimum API your APK will support.
android.minapi = 21

# (str) The Android arch to build for
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
