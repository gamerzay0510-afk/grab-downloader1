[app]

title = GRAB Downloader
package.name = grabdownloader
package.domain = org.grab
version = 4.0

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.archs = arm64-v8a,armeabi-v7a
android.api = 31
android.minapi = 21
android.accept_sdk_license = True

[buildozer]
log_level = 2