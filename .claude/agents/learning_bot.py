#!/usr/bin/env python3
"""
Learning Bot — Agentic Engineering Learning Assistant
Runs as part of Darrian's overnight agent orchestration
Generates learning challenges from PSS backlog + code reviews

Usage:
  python learning_bot.py --mode challenge --phase 1
  python learning_bot.py --mode review --commit HEAD~5
  python learning_bot.py --mode status
"""

import argparse
import json
import os
from datetime import datetime
from anthropic import Anthropic
import subprocess
from pathlib import Path


def get_git_diff(commit_range="HEAD~5..HEAD"):
    """Get recent commits and diffs for code review."""
    try:
        # Get commit log
        log_result = subprocess.run(
            ["git", "log", "--oneline", commit_range],
            capture_output=True, text=True, cwd=os.getcwd()
        )
        
        # Get diff summary
        diff_result = subprocess.run(
            ["git", "diff", "--stat", commit_range],
            capture_output=True, text=True, cwd=os.getcwd()
        )
        
        return {
            "commits": log_result.stdout,
            "diff_stat": diff_result.stdout,
            "success": True
        }
    except Exception as e:
        return {"error": str(e), "success": False}


def load_learning_progress():
    """Load user's learning progress from JSON."""
    progress_file = Path(".claude") / "learning_progress.json"
    if progress_file.exists():
        with open(progress_file) as f:
            return json.load(f)
    return {
        "phase": 1,
        "completed_checkpoints": [],
        "learning_notes": [],
        "last_review": None
    }


def save_learning_progress(progress):
    """Save learning progress to JSON."""
    progress_file = Path(".claude") / "learning_progress.json"
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    with open(progress_file, "w") as f:
        json.dump(progress, f, indent=2)


def generate_challenge(phase, context=""):
    """Use Claude to generate a learning challenge for the current phase."""
    client = Anthropic()
    
    phase_descriptions = {
        1: "Code Clarity & Foundations: Reading, testing, and refactoring existing code",
        2: "Systems & Architecture: Data flow, schema design, API design",
        3: "Version Control & Collaboration: Git workflow, documentation",
        4: "Security & Privacy: Vulnerability checking, secrets management, data minimization",
        5: "Deployment & Containerization: Docker, monitoring, zero-downtime deploys",
    }
    
    prompt = f"""You are Tina, the experienced engineer from "How to Learn Coding in 2026".
You're helping Darrian Belcher learn to code through building Peach State Savings (PSS),
an AI-powered personal finance app running on a homelab with PostgreSQL + Streamlit.

Darrian is currently in Phase {phase}: {phase_descriptions.get(phase, "Unknown")}

PSS Context: {context if context else "88+ page Streamlit app managing college finances, resale inventory, budgeting, and more"}

Generate ONE specific, actionable learning challenge for today that:
1. Takes 45-90 minutes to complete
2. Uses actual PSS code (not toy exercises)
3. Teaches the specific skill from this phase
4. Results in something useful (either improved code or a test)

Format:
CHALLENGE: [one-line challenge title]
TIME: [estimated minutes]
WHAT YOU'LL LEARN: [one sentence]
STEPS:
1. [first step]
2. [second step]
3. [etc.]
WHY THIS MATTERS: [connect to Darrian's values: ownership, serving users, transparency]
REFLECTION QUESTION: [question to deepen understanding]

Be specific. Use file paths from PSS. Make it real."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return message.content[0].text


def generate_code_review(git_diff, context=""):
    """Use Claude to review recent code and suggest learning opportunities."""
    client = Anthropic()
    
    prompt = f"""You are a senior code reviewer helping Darrian learn agentic engineering.
Darrian recently made these commits (shown below). Review them from a LEARNING perspective:
- What patterns can Darrian learn from?
- What could be improved for clarity/architecture/security?
- What future mistake is this code protecting against?

RECENT COMMITS:
{git_diff['commits']}

FILES CHANGED:
{git_diff['diff_stat']}

Format your response as:
LEARNING WINS: [2-3 things Darrian did well, specifically]
IMPROVEMENT OPPORTUNITIES: [2-3 concrete suggestions, with file/line if possible]
PATTERN TO LEARN: [one software pattern this reveals - e.g. "Authentication flow", "Database caching"]
SECURITY SCAN: [any security concerns? Or "clean"?]
NEXT STEP: [one thing to practice next based on this review]

Be encouraging. Darrian is learning. Point out the good parts first."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return message.content[0].text


def run_interactive_session():
    """Run an interactive learning conversation with Claude."""
    client = Anthropic()
    conversation_history = []
    
    system_prompt = """You are Tina, an experienced software engineer helping Darrian learn to code in 2026.
    
Darrian is building Peach State Savings (PSS), an AI-powered personal finance app. He's learning through real project work.

Your role:
- Answer specific code questions clearly
- Explain patterns and architecture decisions
- Challenge assumptions ("why did you choose that?")
- Connect learning to Darrian's values: ownership, serving users, transparency in code
- When Darrian is stuck, ask clarifying questions first

Style:
- Be direct. No fluff.
- Use examples from PSS when possible
- Explain the WHY, not just WHAT
- If you don't know, say so—then help them figure it out together

Darrian's learning phase: Based on the conversation, determine which phase they're in and guide accordingly."""

    print("\n🤖 Learning Bot — Interactive Session")
    print("Type 'exit' to quit, 'status' for progress, 'challenge' for daily challenge")
    print("-" * 60)
    
    while True:
        user_input = input("\n💭 You: ").strip()
        
        if user_input.lower() == 'exit':
            print("\n✅ Session saved. Keep building—you've got this.")
            break
        
        if user_input.lower() == 'status':
            progress = load_learning_progress()
            print(f"📊 Phase {progress['phase']}/5")
            print(f"✅ Completed checkpoints: {len(progress['completed_checkpoints'])}")
            print(f"📝 Learning notes: {len(progress['learning_notes'])}")
            continue
        
        if user_input.lower() == 'challenge':
            progress = load_learning_progress()
            print(f"\n🎯 Generating Phase {progress['phase']} challenge...")
            challenge = generate_challenge(progress['phase'])
            print(challenge)
            # Save to learning notes
            progress['learning_notes'].append({
                "timestamp": datetime.now().isoformat(),
                "type": "challenge",
                "content": challenge
            })
            save_learning_progress(progress)
            continue
        
        if not user_input:
            continue
        
        # Add to conversation
        conversation_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Get Claude's response
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=conversation_history
        )
        
        assistant_message = response.content[0].text
        conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        print(f"\n🎓 Tina: {assistant_message}")
        
        # Save conversation
        progress = load_learning_progress()
        progress['learning_notes'].append({
            "timestamp": datetime.now().isoformat(),
            "type": "conversation",
            "user": user_input,
            "assistant": assistant_message
        })
        save_learning_progress(progress)


def main():
    parser = argparse.ArgumentParser(
        description="Learning Bot — Agentic Engineering Learning Assistant"
    )
    parser.add_argument(
        "--mode",
        choices=["challenge", "review", "status", "interactive"],
        default="interactive",
        help="Mode: generate challenge, review code, show status, or interactive"
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Learning phase (for challenge mode)"
    )
    parser.add_argument(
        "--commit",
        default="HEAD~5",
        help="Commit range for review (e.g., 'HEAD~10..HEAD')"
    )
    
    args = parser.parse_args()
    
    if args.mode == "challenge":
        progress = load_learning_progress()
        phase = args.phase or progress['phase']
        print(f"\n🎯 Challenge for Phase {phase}\n")
        challenge = generate_challenge(phase)
        print(challenge)
        
        # Offer to mark as learned
        if input("\nCompleted? (y/n) ").lower() == 'y':
            progress['completed_checkpoints'].append({
                "phase": phase,
                "timestamp": datetime.now().isoformat()
            })
            save_learning_progress(progress)
            print("✅ Checkpoint marked complete!")
    
    elif args.mode == "review":
        print(f"\n📝 Reviewing commits: {args.commit}\n")
        git_diff = get_git_diff(args.commit)
        
        if not git_diff['success']:
            print(f"❌ Error: {git_diff['error']}")
            return
        
        review = generate_code_review(git_diff)
        print(review)
        
        # Save review
        progress = load_learning_progress()
        progress['learning_notes'].append({
            "timestamp": datetime.now().isoformat(),
            "type": "code_review",
            "commit_range": args.commit,
            "content": review
        })
        progress['last_review'] = datetime.now().isoformat()
        save_learning_progress(progress)
    
    elif args.mode == "status":
        progress = load_learning_progress()
        print(f"""
📊 Your Learning Progress
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase:                 {progress['phase']}/5
Total Checkpoints:     {len(progress['completed_checkpoints'])}
Learning Notes:        {len(progress['learning_notes'])}
Last Code Review:      {progress['last_review'] or 'Never'}

Recent Learning Activities:
""")
        for note in progress['learning_notes'][-5:]:
            print(f"  • {note['timestamp']}: {note['type']}")
    
    elif args.mode == "interactive":
        run_interactive_session()


if __name__ == "__main__":
    main()
