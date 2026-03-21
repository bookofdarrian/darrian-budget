#!/bin/zsh
# Open the actual dashboard and screenshot the Chrome window

open -a "Google Chrome" "https://peachstatesavings.com/app"
sleep 7

osascript -e 'tell application "Google Chrome" to activate'
sleep 1

screencapture -l $(osascript -e 'tell application "Google Chrome" to id of window 1') \
  /Users/darrianbelcher/Downloads/darrian-budget/static/app_window.png

echo "Done: $(ls -lh /Users/darrianbelcher/Downloads/darrian-budget/static/app_window.png)"
