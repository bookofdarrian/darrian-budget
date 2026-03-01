"""
aura/jarvis.py
Jarvis — Darrian's personal AI assistant personality layer.
Wraps Claude claude-opus-4-5 with a Jarvis system prompt optimized for voice responses.
Keeps answers short (≤2 sentences) for TTS output.

Usage:
    from aura.jarvis import ask_jarvis
    response = ask_jarvis("What's my budget looking like this month?")
"""

import sys
import os

# Allow importing from project root when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

JARVIS_SYSTEM_PROMPT = """You are JARVIS, the personal AI assistant for Darrian Belcher — \
software engineer, homelab builder, content creator, and cat owner in Atlanta, GA.

Your personality:
- Direct, precise, occasionally witty — like Tony Stark's AI
- Never verbose. For voice output: 1-2 sentences max unless asked for detail
- Address him as "Darrian" on first mention, or occasionally "sir" for fun
- You know about his budget app (Peach State Savings), homelab (CT100, Proxmox, Tailscale), \
  content channels, and his cats
- When asked about finances, reference that you can pull data from the Peach State Savings app
- If asked to do something you can't do, say so in one sentence and suggest what he should do instead

Current context:
- App: peachstatesavings.com (Streamlit + PostgreSQL on home lab)
- Homelab: CT100 @ 100.95.125.112, Nginx → prod
- Audio: HomePod Mini (kitchen), Echo Dot (living room)
- Cats: fed at 7 AM and 6 PM
"""


def ask_jarvis(user_query: str, context: str = "", max_tokens: int = 200) -> str:
    """
    Ask Jarvis a question. Returns a short, voice-ready response string.

    Args:
        user_query: What the user said or typed
        context: Optional extra context (e.g. current page data, budget summary)
        max_tokens: Keep low for voice output (200), higher for detailed text (1000)

    Returns:
        Jarvis's response as a plain string
    """
    try:
        import anthropic
    except ImportError:
        return "Anthropic package not installed. Run: pip install anthropic"

    try:
        from utils.db import get_setting
        api_key = get_setting("anthropic_api_key", "")
    except Exception:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key:
        return "No API key found, Darrian. Add your Anthropic key in AI Insights settings."

    client = anthropic.Anthropic(api_key=api_key)

    messages = []
    if context:
        messages.append({"role": "user", "content": f"Context for this session:\n{context}"})
        messages.append({"role": "assistant", "content": "Got it. Ready."})

    messages.append({"role": "user", "content": user_query})

    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=max_tokens,
            system=JARVIS_SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"I ran into an issue, Darrian: {e}"


def ask_jarvis_detailed(user_query: str, context: str = "") -> str:
    """
    Ask Jarvis for a detailed response (notes, analysis, etc.) — not optimized for TTS.
    """
    return ask_jarvis(user_query, context, max_tokens=1000)


if __name__ == "__main__":
    # Quick test
    print("Testing Jarvis...")
    reply = ask_jarvis("What's today's vibe?")
    print(f"Jarvis: {reply}")
