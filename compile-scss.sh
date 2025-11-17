#!/bin/bash
# compile scss files to css

cd "$(dirname "$0")/ui/styles"

echo "Compiling SCSS files to CSS..."

sass base.scss:base.css \
     upload.scss:upload.css \
     loading.scss:loading.css \
     edit.scss:edit.css \
     deck-ui.scss:deck-ui.css \
     deck-slides.scss:deck-slides.css \
     --style expanded

echo "Compilation complete!"

