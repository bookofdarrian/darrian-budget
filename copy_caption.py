#!/usr/bin/env python3
"""Copy the right caption for each platform. Usage: python3 copy_caption.py [fb|tiktok|ig|youtube]"""
import subprocess, sys

CAPTIONS = {
    "fb": open("FB_POST.txt").read(),

    "tiktok": """my laptop built me a new feature while i was sleeping 😭

built 3 apps from a home server while working fulltime at Visa & finishing Georgia Tech. this is the tour.

📊 peachstatesavings.com — free personal finance OS
👟 getsoleops.com — sneaker resale suite (april launch)
🎓 collegeconfused.org — free AI college prep, always free

follow the build 👉 @bookofdarrian

#buildinpublic #techlife #softwareengineer #sideproject #ai #blacktech #solofounder""",

    "ig": """My server built me a new feature while I slept 🖥️

3 apps. 1 year. Built solo while working full-time at Visa + finishing Georgia Tech.

📊 peachstatesavings.com — 140-page personal finance OS. Free.
👟 getsoleops.com — sneaker resale suite. April launch.
🎓 collegeconfused.org — AI college prep for first-gen students. Always free.

Link in bio | @bookofdarrian

#buildinpublic #blacktech #sideproject #solofounder #ai #streamlit""",

    "youtube": """Full tour of everything I've built in one year:

📊 Peach State Savings — peachstatesavings.com (free)
👟 SoleOps — getsoleops.com (April launch)
🎓 College Confused — collegeconfused.org (always free)

Built solo while working as a TPM at Visa + finishing Georgia Tech.
Runs on a home server. AI builds features while I sleep.

Follow the build: @bookofdarrian

#buildinpublic #solofounder #python #ai #streamlit #shorts""",
}

URLS = {
    "fb":      "https://www.facebook.com",
    "tiktok":  "https://www.tiktok.com/upload",
    "ig":      "https://www.instagram.com/create/style/",
    "youtube": "https://studio.youtube.com",
}

platform = sys.argv[1].lower() if len(sys.argv) > 1 else "fb"
if platform not in CAPTIONS:
    print(f"Usage: python3 copy_caption.py [{'|'.join(CAPTIONS.keys())}]")
    sys.exit(1)

subprocess.run(['pbcopy'], input=CAPTIONS[platform].encode('utf-8'), check=True)
subprocess.run(['open', '-a', 'Google Chrome', URLS[platform]])
print(f"✅ {platform.upper()} caption in clipboard + tab opened!")
print(f"\n--- CAPTION ---\n{CAPTIONS[platform][:200]}...")
