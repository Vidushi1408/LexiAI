#!/bin/sh
# Renders every posters/poster*.html to an A3 PDF in posters/pdf/ using headless Google Chrome.
# Edit a poster's HTML (text, team roles) or drop team photos into posters/photos/ — named
# vidushi.jpg, parth.jpg, aryama.jpg, ashi.jpg, simran.jpg — then run:  sh posters/build.sh
set -e
cd "$(dirname "$0")"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
mkdir -p pdf
for f in poster*.html; do
  name="${f%.html}"
  "$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
    --virtual-time-budget=4000 --print-to-pdf="pdf/$name.pdf" "file://$PWD/$f" >/dev/null 2>&1
  echo "built pdf/$name.pdf"
done
