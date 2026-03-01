"""
Gmail Client — Personal Assistant Integration
=============================================
Handles all Gmail API interactions for the Personal Assistant feature.

Capabilities:
  - OAuth2 authentication (credentials stored in DB, token stored in DB)
  - Fetch recent emails by label/query
  - Parse purchase/receipt emails into structured data
  - Detect notification/alert emails for smart filtering
  - Extract tasks and action items from emails

Setup — DB-first approach (works in Docker / production):
  1. Go to console.cloud.google.com → New Project → "Peach Savings Assistant"
  2. Enable Gmail API
  3. OAuth consent screen → External → add your Gmail as test user
  4. Credentials → OAuth 2.0 Client ID → Desktop App → download JSON
  5. In the Personal Assistant page, paste/upload credentials.json content →
     saved to DB under "google_credentials" key (survives container restarts,
     never committed to git)
  6. First run: click the auth link, approve, token saved to DB automatically

File fallback:
  If "google_credentials" is not in the DB, the code falls back to reading
  CREDENTIALS_FILE (env: GMAIL_CREDENTIALS_FILE, default: credentials.json).

Environment variables (optional overrides):
  GMAIL_CREDENTIALS_FILE  — path to credentials.json (default: ./credentials.json)
  GMAIL_TOKEN_FILE        — path to token.json fallback (default: ./token.json)
"""

import os
import json
import base64
import re
import logging
from datetime import datetime, timezone
from typing import Optional
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
CREDENTIALS_FILE = os.environ.get("GMAIL_CREDENTIALS_FILE", "credentials.json")
TOKEN_FILE       = os.environ.get("GMAIL_TOKEN_FILE", "token.json")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",   # needed to mark as read / apply labels
]

# ── Purchase/receipt detection patterns ──────────────────────────────────────
PURCHASE_SENDERS = [
    "amazon", "ebay", "paypal", "venmo", "cashapp", "zelle",
    "apple", "google", "netflix", "spotify", "hulu", "disney",
    "doordash", "ubereats", "grubhub", "instacart", "shipt",
    "walmart", "target", "bestbuy", "costco", "samsclub",
    "chevron", "shell", "bp", "exxon", "wawa",
    "chase", "bankofamerica", "wellsfargo", "nfcu", "navyfederal",
    "stripe", "square", "shopify", "etsy",
    "stockx", "goat", "flightclub", "kickscrew",
    "delta", "united", "southwest", "american airlines", "spirit",
    "uber", "lyft", "airbnb", "vrbo",
    "noreply@", "no-reply@", "receipts@", "orders@", "billing@",
]

PURCHASE_SUBJECT_PATTERNS = [
    r"order\s+(confirmed|received|shipped|delivered)",
    r"your\s+(receipt|invoice|purchase|payment|charge)",
    r"payment\s+(received|confirmed|processed|successful)",
    r"transaction\s+(confirmed|receipt|notification)",
    r"you\s+paid",
    r"charge\s+of\s+\$",
    r"amount\s+(charged|billed|due)",
    r"subscription\s+(renewed|charged|billed)",
    r"refund\s+(processed|issued|approved)",
    r"shipment\s+(confirmed|shipped|out for delivery)",
    r"delivery\s+(confirmed|scheduled|attempted)",
]

AMOUNT_PATTERNS = [
    r"\$\s*(\d{1,6}(?:,\d{3})*(?:\.\d{2})?)",
    r"(?:total|amount|charged|paid|billed)[:\s]+\$?\s*(\d{1,6}(?:,\d{3})*(?:\.\d{2})?)",
    r"(\d{1,6}(?:,\d{3})*\.\d{2})\s*(?:USD|usd)",
]

# ── Notification/alert detection ─────────────────────────────────────────────
NOTIFICATION_PATTERNS = [
    r"(unsubscribe|opt.out|manage\s+preferences|email\s+preferences)",
    r"(newsletter|weekly\s+digest|daily\s+digest|roundup)",
    r"(promotional|sale|deal|offer|discount|coupon|promo\s+code)",
    r"(new\s+message|someone\s+commented|liked\s+your|mentioned\s+you)",
    r"(security\s+alert|sign.in\s+attempt|new\s+device|unusual\s+activity)",
    r"(verify\s+your|confirm\s+your\s+email|activate\s+your)",
    r"(reminder|don.t\s+forget|last\s+chance|expires\s+soon)",
]

# ── Task/action item detection ────────────────────────────────────────────────
TASK_PATTERNS = [
    r"(?:please|kindly)?\s*(review|sign|complete|fill\s+out|submit|respond|reply|confirm|approve|schedule|call|contact|follow\s+up)",
    r"(action\s+required|action\s+needed|response\s+required|your\s+attention)",
    r"(deadline|due\s+(?:date|by)|expires?\s+(?:on|by)|by\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))",
    r"(meeting\s+(?:request|invite|scheduled)|calendar\s+invite|appointment)",
    r"(todo|to.do|task\s+assigned|assigned\s+to\s+you)",
]


# ── Credentials helper ────────────────────────────────────────────────────────

def _load_credentials_config(credentials_json_str: Optional[str] = None) -> dict:
    """
    Return the parsed credentials config dict.

    Priority:
      1. credentials_json_str  — JSON string passed in (from DB setting)
      2. CREDENTIALS_FILE      — file on disk (local dev fallback)

    Raises FileNotFoundError if neither source is available.
    """
    # 1. From DB / passed-in string
    if credentials_json_str:
        try:
            return json.loads(credentials_json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid credentials JSON: {e}")

    # 2. From file on disk
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE) as f:
            return json.load(f)

    raise FileNotFoundError(
        f"Google credentials not found. "
        f"Upload your credentials.json via the setup section, "
        f"or place the file at '{CREDENTIALS_FILE}'."
    )


# ── Gmail service factory ─────────────────────────────────────────────────────

def get_gmail_service(
    token_json: Optional[str] = None,
    credentials_json: Optional[str] = None,
):
    """
    Build and return an authenticated Gmail API service object.

    Args:
        token_json:       JSON string of the stored OAuth token (from DB).
                          If None, falls back to TOKEN_FILE on disk.
        credentials_json: JSON string of the OAuth client credentials (from DB).
                          Falls back to credentials.json on disk if not provided.

    Returns:
        (service, token_json_str) — token_json_str may be refreshed; save it back to DB.

    Raises:
        FileNotFoundError  — credentials not found anywhere
        RuntimeError       — auth flow needed (first-time setup)
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "Google API libraries not installed. Run:\n"
            "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
        )

    creds = None

    # 1. Try token from DB (passed in as JSON string)
    if token_json:
        try:
            creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
        except Exception as e:
            logger.warning(f"Could not load token from DB: {e}")
            creds = None

    # 2. Fallback: try token.json on disk
    if not creds and os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None

    # 3. Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.warning(f"Token refresh failed: {e}")
            creds = None

    # 4. If still no valid creds, we need the auth flow
    if not creds or not creds.valid:
        # Validate credentials are available (raises FileNotFoundError if not)
        _load_credentials_config(credentials_json)
        raise RuntimeError("AUTH_REQUIRED")

    # Serialize token back (may have been refreshed)
    token_str = creds.to_json()

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return service, token_str


def get_auth_url(
    state: str = "",
    credentials_json: Optional[str] = None,
) -> tuple:
    """
    Generate the OAuth2 authorization URL for first-time setup.

    Args:
        state:            Optional OAuth state string.
        credentials_json: JSON string of the OAuth client credentials (from DB).
                          Falls back to credentials.json on disk if not provided.

    Returns:
        (auth_url, flow) — store flow in session_state to exchange code later.
    """
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        raise ImportError("Run: pip install google-auth-oauthlib")

    config = _load_credentials_config(credentials_json)  # raises if not found

    flow = Flow.from_client_config(
        config,
        scopes=SCOPES,
        redirect_uri="urn:ietf:wg:oauth:2.0:oob",  # Desktop/OOB flow — user copies code
    )
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return auth_url, flow


def exchange_code_for_token(flow, code: str) -> str:
    """
    Exchange the authorization code for a token.
    Returns the token as a JSON string to store in the DB.
    """
    flow.fetch_token(code=code)
    creds = flow.credentials
    token_str = creds.to_json()
    # Also save to disk as fallback
    try:
        with open(TOKEN_FILE, "w") as f:
            f.write(token_str)
    except Exception as e:
        logger.warning(f"Could not save token.json to disk: {e}")
    return token_str


# ── Email fetching ────────────────────────────────────────────────────────────

def fetch_emails(
    service,
    query: str = "",
    max_results: int = 50,
    label_ids: Optional[list] = None,
) -> list:
    """
    Fetch emails matching a Gmail search query.
    Returns list of parsed email dicts.

    query examples:
        "is:unread newer_than:7d"
        "from:amazon.com newer_than:30d"
        "subject:receipt newer_than:30d"
        "category:purchases newer_than:30d"
    """
    try:
        params = {
            "userId": "me",
            "maxResults": max_results,
        }
        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids

        result = service.users().messages().list(**params).execute()
        messages = result.get("messages", [])

        emails = []
        for msg_ref in messages:
            try:
                msg = service.users().messages().get(
                    userId="me",
                    id=msg_ref["id"],
                    format="full",
                ).execute()
                parsed = _parse_message(msg)
                if parsed:
                    emails.append(parsed)
            except Exception as e:
                logger.warning(f"Failed to fetch message {msg_ref['id']}: {e}")
                continue

        return emails

    except Exception as e:
        logger.error(f"Gmail fetch failed: {e}")
        return []


def _parse_message(msg: dict) -> Optional[dict]:
    """Parse a raw Gmail message into a clean dict."""
    try:
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}

        # Parse date
        date_str = headers.get("date", "")
        try:
            date_obj = parsedate_to_datetime(date_str)
            date_iso = date_obj.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            date_display = date_obj.strftime("%Y-%m-%d")
        except Exception:
            date_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            date_display = datetime.utcnow().strftime("%Y-%m-%d")

        subject = headers.get("subject", "(no subject)")
        sender  = headers.get("from", "")
        to      = headers.get("to", "")

        # Extract body text
        body = _extract_body(msg["payload"])

        # Snippet (Gmail's auto-preview)
        snippet = msg.get("snippet", "")

        return {
            "id":           msg["id"],
            "thread_id":    msg.get("threadId", ""),
            "date":         date_display,
            "date_iso":     date_iso,
            "subject":      subject,
            "sender":       sender,
            "to":           to,
            "snippet":      snippet,
            "body":         body[:5000],  # cap at 5k chars for LLM
            "label_ids":    msg.get("labelIds", []),
            "is_unread":    "UNREAD" in msg.get("labelIds", []),
        }
    except Exception as e:
        logger.warning(f"Message parse error: {e}")
        return None


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text body from a Gmail message payload."""
    body_text = ""

    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            body_text = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    elif mime_type == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            html = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            # Strip HTML tags for plain text
            body_text = re.sub(r"<[^>]+>", " ", html)
            body_text = re.sub(r"\s+", " ", body_text).strip()

    elif "parts" in payload:
        # Prefer text/plain, fall back to text/html
        plain_parts = [p for p in payload["parts"] if p.get("mimeType") == "text/plain"]
        html_parts  = [p for p in payload["parts"] if p.get("mimeType") == "text/html"]
        multi_parts = [p for p in payload["parts"] if "parts" in p]

        if plain_parts:
            body_text = _extract_body(plain_parts[0])
        elif html_parts:
            body_text = _extract_body(html_parts[0])
        elif multi_parts:
            for part in multi_parts:
                body_text = _extract_body(part)
                if body_text:
                    break

    return body_text.strip()


# ── Email classification (rule-based, no LLM needed) ─────────────────────────

def classify_email(email: dict) -> dict:
    """
    Rule-based classification of an email.
    Returns classification dict with type, confidence, and extracted data.

    Types: 'purchase', 'notification', 'task', 'newsletter', 'personal', 'unknown'
    """
    subject_lower = email["subject"].lower()
    sender_lower  = email["sender"].lower()
    body_lower    = (email["body"] + " " + email["snippet"]).lower()
    combined      = f"{subject_lower} {sender_lower} {body_lower}"

    result = {
        "type":               "unknown",
        "confidence":         0.0,
        "extracted_amount":   None,
        "extracted_merchant": None,
        "is_purchase":        False,
        "is_notification":    False,
        "is_task":            False,
        "is_newsletter":      False,
        "suggested_category": None,
        "priority":           "normal",
    }

    scores = {"purchase": 0, "notification": 0, "task": 0, "newsletter": 0}

    # ── Purchase detection ────────────────────────────────────────────────────
    for sender_kw in PURCHASE_SENDERS:
        if sender_kw in sender_lower:
            scores["purchase"] += 3
            break

    for pattern in PURCHASE_SUBJECT_PATTERNS:
        if re.search(pattern, subject_lower):
            scores["purchase"] += 2

    # Extract dollar amount
    for pattern in AMOUNT_PATTERNS:
        m = re.search(pattern, combined)
        if m:
            try:
                amount_str = m.group(1).replace(",", "")
                result["extracted_amount"] = float(amount_str)
                scores["purchase"] += 1
            except Exception:
                pass
            break

    # ── Notification detection ────────────────────────────────────────────────
    for pattern in NOTIFICATION_PATTERNS:
        if re.search(pattern, combined):
            scores["notification"] += 2

    if "unsubscribe" in body_lower:
        scores["notification"] += 3
        scores["newsletter"] += 2

    # ── Task detection ────────────────────────────────────────────────────────
    for pattern in TASK_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            scores["task"] += 2

    # ── Newsletter detection ──────────────────────────────────────────────────
    newsletter_kws = ["newsletter", "digest", "weekly update", "monthly update", "roundup"]
    for kw in newsletter_kws:
        if kw in combined:
            scores["newsletter"] += 3

    # ── Determine winner ──────────────────────────────────────────────────────
    max_score = max(scores.values())
    if max_score == 0:
        result["type"] = "personal"
        result["confidence"] = 0.5
    else:
        winner = max(scores, key=scores.get)
        result["type"] = winner
        result["confidence"] = min(max_score / 8.0, 1.0)

    result["is_purchase"]     = scores["purchase"] >= 3
    result["is_notification"] = scores["notification"] >= 3
    result["is_task"]         = scores["task"] >= 2
    result["is_newsletter"]   = scores["newsletter"] >= 3

    # ── Extract merchant from sender ──────────────────────────────────────────
    sender_name_match = re.match(r'^"?([^"<]+)"?\s*<', email["sender"])
    if sender_name_match:
        result["extracted_merchant"] = sender_name_match.group(1).strip()
    else:
        # Use domain
        domain_match = re.search(r'@([\w.-]+)', email["sender"])
        if domain_match:
            domain = domain_match.group(1)
            # Clean up: remove TLD, capitalize
            parts = domain.split(".")
            result["extracted_merchant"] = parts[0].title() if parts else domain

    # ── Suggest expense category ──────────────────────────────────────────────
    if result["is_purchase"]:
        result["suggested_category"] = _suggest_category(sender_lower, subject_lower, body_lower)

    # ── Priority ──────────────────────────────────────────────────────────────
    if result["is_task"]:
        result["priority"] = "high"
    elif result["is_purchase"]:
        result["priority"] = "normal"
    elif result["is_newsletter"]:
        result["priority"] = "low"

    return result


def _suggest_category(sender: str, subject: str, body: str) -> str:
    """Map email content to a budget expense category."""
    combined = f"{sender} {subject} {body}"

    category_map = {
        "Food": ["doordash", "ubereats", "grubhub", "instacart", "shipt", "postmates",
                 "chipotle", "mcdonald", "starbucks", "dunkin", "chick-fil-a", "subway",
                 "domino", "pizza", "restaurant", "dining", "food delivery", "grocery",
                 "publix", "kroger", "whole foods", "trader joe", "aldi", "walmart grocery"],
        "Transportation": ["uber", "lyft", "delta", "united", "southwest", "american airlines",
                           "spirit", "frontier", "jetblue", "amtrak", "greyhound",
                           "chevron", "shell", "bp", "exxon", "gas station", "fuel",
                           "parking", "toll", "zipcar", "enterprise", "hertz", "avis"],
        "Entertainment": ["netflix", "spotify", "hulu", "disney", "hbo", "apple tv",
                          "amazon prime", "youtube premium", "twitch", "steam", "playstation",
                          "xbox", "nintendo", "ticketmaster", "eventbrite", "stubhub",
                          "concert", "movie", "theater", "subscription"],
        "Housing": ["rent", "mortgage", "electric", "gas bill", "water", "internet",
                    "comcast", "xfinity", "att", "verizon", "t-mobile", "spectrum",
                    "waste management", "hoa", "maintenance", "repair"],
        "Personal Care": ["cvs", "walgreens", "rite aid", "pharmacy", "prescription",
                          "doctor", "dentist", "vision", "medical", "health", "gym",
                          "planet fitness", "la fitness", "equinox", "salon", "barber",
                          "spa", "massage"],
        "Savings / Investments": ["fidelity", "vanguard", "schwab", "robinhood", "coinbase",
                                   "acorns", "betterment", "wealthfront", "transfer", "deposit"],
        "Business": ["ebay", "stockx", "goat", "flight club", "kicks crew", "mercari",
                     "poshmark", "depop", "shopify", "etsy", "paypal business",
                     "shipping", "usps", "fedex", "ups", "dhl"],
        "Shopping": ["amazon", "target", "walmart", "best buy", "costco", "sams club",
                     "apple store", "nike", "adidas", "foot locker", "finish line",
                     "nordstrom", "macy", "gap", "h&m", "zara", "shein"],
    }

    for category, keywords in category_map.items():
        for kw in keywords:
            if kw in combined:
                return category

    return "Shopping"  # default


# ── Amount extraction helper ──────────────────────────────────────────────────

def extract_amounts_from_body(body: str) -> list:
    """Extract all dollar amounts from email body text."""
    amounts = []
    for pattern in AMOUNT_PATTERNS:
        for m in re.finditer(pattern, body, re.IGNORECASE):
            try:
                val = float(m.group(1).replace(",", ""))
                if 0.01 <= val <= 99999:  # sanity range
                    amounts.append(val)
            except Exception:
                pass
    return sorted(set(amounts))


# ── LLM-powered parsing ───────────────────────────────────────────────────────

def parse_purchase_with_llm(email: dict, api_key: str, use_ollama: bool = False,
                              ollama_url: str = "") -> dict:
    """
    Use Claude or Ollama to extract structured purchase data from an email.

    Returns dict with:
        merchant, amount, date, category, subcategory, description, confidence
    """
    prompt = f"""Extract purchase information from this email. Return ONLY valid JSON, no other text.

Email Subject: {email['subject']}
From: {email['sender']}
Date: {email['date']}
Body (first 2000 chars):
{email['body'][:2000]}

Return this exact JSON structure:
{{
  "merchant": "store or company name",
  "amount": 0.00,
  "date": "YYYY-MM-DD",
  "category": "one of: Food, Transportation, Entertainment, Housing, Personal Care, Shopping, Business, Savings / Investments, Other",
  "subcategory": "specific subcategory like Groceries, Dining Out, Fuel, Subscriptions, etc.",
  "description": "brief one-line description of what was purchased",
  "is_refund": false,
  "confidence": 0.9
}}

If you cannot find a specific field, use null. Amount must be a number, not a string."""

    if use_ollama and ollama_url:
        try:
            import requests
            r = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": False},
                timeout=30,
            )
            if r.status_code == 200:
                raw = r.json().get("response", "")
                return _parse_llm_json_response(raw)
        except Exception as e:
            logger.warning(f"Ollama parse failed: {e}")

    # Fall back to Claude
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
        return _parse_llm_json_response(raw)
    except Exception as e:
        logger.error(f"Claude parse failed: {e}")
        return {}


def _parse_llm_json_response(raw: str) -> dict:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    # Strip markdown code fences
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()
    raw = raw.rstrip("`").strip()

    # Find JSON object
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def parse_task_with_llm(email: dict, api_key: str, use_ollama: bool = False,
                         ollama_url: str = "") -> dict:
    """
    Use LLM to extract task/action items from an email.

    Returns dict with:
        task_title, due_date, priority, notes
    """
    prompt = f"""Extract the action item or task from this email. Return ONLY valid JSON.

Email Subject: {email['subject']}
From: {email['sender']}
Date: {email['date']}
Body (first 1500 chars):
{email['body'][:1500]}

Return this exact JSON structure:
{{
  "task_title": "clear, actionable task description (start with a verb)",
  "due_date": "YYYY-MM-DD or null if no deadline mentioned",
  "priority": "high, normal, or low",
  "notes": "any relevant context or details",
  "source_email_subject": "{email['subject'][:80]}"
}}"""

    if use_ollama and ollama_url:
        try:
            import requests
            r = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": False},
                timeout=30,
            )
            if r.status_code == 200:
                raw = r.json().get("response", "")
                return _parse_llm_json_response(raw)
        except Exception as e:
            logger.warning(f"Ollama task parse failed: {e}")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
        return _parse_llm_json_response(raw)
    except Exception as e:
        logger.error(f"Claude task parse failed: {e}")
        return {}


# ── Batch processing ──────────────────────────────────────────────────────────

def process_emails_batch(
    emails: list,
    api_key: str = "",
    use_llm: bool = True,
    use_ollama: bool = False,
    ollama_url: str = "",
    max_llm_calls: int = 20,
) -> list:
    """
    Process a batch of emails: classify, extract data, optionally use LLM.

    Returns list of enriched email dicts ready for DB insertion.
    """
    results = []
    llm_calls = 0

    for email in emails:
        classification = classify_email(email)
        enriched = {**email, **classification}

        # Use LLM for purchase emails if we have budget
        if (use_llm and api_key and
                classification["is_purchase"] and
                llm_calls < max_llm_calls):
            llm_data = parse_purchase_with_llm(
                email, api_key, use_ollama, ollama_url
            )
            if llm_data:
                # LLM data overrides rule-based where available
                if llm_data.get("merchant"):
                    enriched["extracted_merchant"] = llm_data["merchant"]
                if llm_data.get("amount"):
                    enriched["extracted_amount"] = llm_data["amount"]
                if llm_data.get("category"):
                    enriched["suggested_category"] = llm_data["category"]
                if llm_data.get("subcategory"):
                    enriched["suggested_subcategory"] = llm_data.get("subcategory")
                if llm_data.get("description"):
                    enriched["purchase_description"] = llm_data["description"]
                if llm_data.get("is_refund"):
                    enriched["is_refund"] = llm_data["is_refund"]
                enriched["llm_parsed"] = True
            llm_calls += 1

        results.append(enriched)

    return results
