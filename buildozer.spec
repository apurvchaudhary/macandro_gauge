[app]

title = macGauge

package.name = macGauge

# (str) Package domain (needed for android/ios packaging)
package.domain = apurvchaudhary.com

# (str) Source code where the main.py live
source.dir = .

source.include_exts = py,png,jpg,kv,atlas

# (list) List of inclusions using pattern matching
#source.include_patterns = assets/*,images/*.png

# (list) Source files to exclude (let empty to not exclude anything)
#source.exclude_exts = spec

source.exclude_dirs = tests, bin, venv

version = 1.0

requirements = python3,kivy,requests,tzdata,plyer,python-dateutil,git+https://github.com/kivymd/KivyMD.git@master

icon.filename = logo.png
presplash.filename = logo.png
presplash.color = #000000


android.allow_cleartext_traffic = True
android.permissions = INTERNET

[buildozer]
log_level = 2
env.LDFLAGS = -L/opt/homebrew/opt/openssl@3/lib
env.CFLAGS = -I/opt/homebrew/opt/openssl@3/include
