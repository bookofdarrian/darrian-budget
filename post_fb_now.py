#!/usr/bin/env python3
"""Post to Facebook using real Chrome + AppleScript + clipboard."""
import subprocess, time

POST = open("FB_POST.txt").read()

# Step 1: copy to clipboard
subprocess.run(['pbcopy'], input=POST.encode('utf-8'), check=True)
print("✅ Copied to clipboard")

# Step 2: Open/focus Facebook tab in Chrome
subprocess.run(['osascript', '-e', '''
tell application "Google Chrome"
    activate
    set found to false
    repeat with w in every window
        repeat with t in every tab of w
            if URL of t contains "facebook.com" then
                set current tab of w to t
                set index of w to 1
                set found to true
                exit repeat
            end if
        end repeat
        if found then exit repeat
    end repeat
    if not found then
        tell front window to make new tab with properties {URL:"https://www.facebook.com"}
        delay 4
    end if
end tell
'''])
print("✅ Facebook tab focused")
time.sleep(3)

# Step 3: Click compose box via JS (simple version, separate call)
js = "var el=document.querySelector('[aria-label*=\"mind\"]')||document.querySelector('[placeholder]'); if(el){el.click();'ok';}else{var s=Array.from(document.querySelectorAll('span')).find(s=>s.textContent&&s.textContent.includes('mind'));if(s){s.click();'ok2';}else{'notfound';}}"

osa_click = f'''
tell application "Google Chrome"
    execute front window's active tab javascript "{js}"
end tell
'''
r = subprocess.run(['osascript', '-e', osa_click], capture_output=True, text=True)
print(f"Compose click: {r.stdout.strip() or r.stderr.strip()}")
time.sleep(3)

# Step 4: Paste with Cmd+V
subprocess.run(['osascript', '-e', '''
tell application "Google Chrome" to activate
delay 0.5
tell application "System Events"
    key code 9 using command down
end tell
'''])
print("✅ Pasted")
time.sleep(3)

# Step 5: Click Post button
js_post = "var b=Array.from(document.querySelectorAll('div[role=button]')).find(b=>b.innerText.trim()==='Post'&&b.offsetParent);if(b){b.click();'posted';}else{'not found'}"
osa_post = f'''
tell application "Google Chrome"
    execute front window's active tab javascript "{js_post}"
end tell
'''
r = subprocess.run(['osascript', '-e', osa_post], capture_output=True, text=True)
print(f"Post button: {r.stdout.strip() or r.stderr.strip()}")
time.sleep(4)
print("✅ Check Facebook — post should be live!")
