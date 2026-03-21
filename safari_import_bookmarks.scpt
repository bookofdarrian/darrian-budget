tell application "Safari"
	activate
end tell

delay 1

tell application "System Events"
	tell process "Safari"
		set frontmost to true
		delay 0.5
		click menu bar item "File" of menu bar 1
		delay 0.4
		tell menu 1 of menu bar item "File" of menu bar 1
			click menu item "Import From"
			delay 0.4
			tell menu 1 of menu item "Import From"
				click menu item "Bookmarks HTML File…"
			end tell
		end tell
		delay 1.5
		keystroke "g" using {command down, shift down}
		delay 0.8
		keystroke "/Users/darrianbelcher/Downloads/darrian-budget/PEACH_STATE_BOOKMARKS.html"
		delay 0.5
		key code 36
		delay 0.8
		key code 36
		delay 0.5
	end tell
end tell
