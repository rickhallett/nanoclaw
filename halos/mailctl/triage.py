"""triage — inbox triage rules for mailctl.

Each rule is a function that takes a message dict and returns a TriageResult.
Rules run in priority order; first match wins.

Message dict shape (from himalaya JSON):
    {
        "id": "8299",
        "flags": ["Seen"],
        "subject": "...",
        "from": {"name": "...", "addr": "..."},
        "to": {"name": "...", "addr": "..."},
        "date": "2026-01-26 14:36+00:00",
        "has_attachment": false
    }
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class Action(Enum):
    SURFACE = "surface"       # show in briefing, keep unread
    ARCHIVE = "archive"       # mark read, move to folder
    LABEL = "label"           # move to folder, keep unread
    SKIP = "skip"             # no action, next rule


@dataclass
class TriageResult:
    action: Action
    reason: str
    label: Optional[str] = None   # destination folder for ARCHIVE / LABEL


# ─── Helpers ──────────────────────────────────────────────────────

def _sender(msg: dict) -> str:
    return msg.get("from", {}).get("addr", "").lower()


def _sender_name(msg: dict) -> str:
    return msg.get("from", {}).get("name", "").lower()


def _subject(msg: dict) -> str:
    return msg.get("subject", "").lower()


def _to_addr(msg: dict) -> str:
    return msg.get("to", {}).get("addr", "").lower()


def _account_for(msg: dict) -> str:
    """Infer account from 'to' address."""
    to = _to_addr(msg)
    if "oceanheart" in to or "kai@" in to:
        return "gmail"
    return "icloud"


# ─── Rule 1: VIP senders — always surface ────────────────────────

# People whose emails should always stay in inbox, unread
VIPS = {
    # Personal
    "jools",           # Jools Bennett — BZR
    "ben hallett",     # Brother
    "andrew younger",  # Cafcass
    "muds",
    "jon hallett",
    "aureliana",       # Aureliana Enache — Dao teacher
    "daizan",          # Zen teacher
    "zenways",
    # Active recruiter leads (update as needed)
    "cathal lyons",
}

# VIP by email address (exact match fragments)
VIP_ADDRS = {
    "jools",
    "benhallett",
    "andrew.younger",
    "aureliana",
}


def _rule_vip(msg: dict) -> Optional[TriageResult]:
    """Surface messages from VIP senders."""
    addr = _sender(msg)
    name = _sender_name(msg)

    for vip in VIPS:
        if vip in name:
            return TriageResult(Action.SURFACE, f"VIP: {vip}")

    for pattern in VIP_ADDRS:
        if pattern in addr:
            return TriageResult(Action.SURFACE, f"VIP addr: {pattern}")

    return None


# ─── Rule 2: Phishing / spam — nuke on sight ─────────────────────

PHISH_PATTERNS = [
    "docsign",         # Docusign phishing variants
    "docusign",        # Even legit ones are suspect
    "nigerian",
    "lottery",
    "inheritanc",
]


def _rule_phishing(msg: dict) -> Optional[TriageResult]:
    """Junk obvious phishing."""
    subj = _subject(msg)
    name = _sender_name(msg)
    for pattern in PHISH_PATTERNS:
        if pattern in subj or pattern in name:
            return TriageResult(Action.ARCHIVE, f"Phish: {pattern}", label="Junk")
    return None


# ─── Rule 3: Bot / automated noise — archive to folders ──────────

# (sender_pattern, destination_folder)
BOT_RULES: list[tuple[str, str]] = [
    # GitHub / CI bots
    ("coderabbitai", "github-bots"),
    ("github.com", "github-bots"),
    ("noreply@github", "github-bots"),
    # Leave Me Alone (the irony)
    ("leavemealone", "_lma-shield/screened"),
    ("leave me alone", "_lma-shield/screened"),
    # npm
    ("npm", "infra"),
    # Infrastructure alerts
    ("railway.app", "infra"),
    ("sentry.io", "infra"),
    ("linear.app", "infra"),
    ("fly.io", "infra"),
    ("render.com", "infra"),
    ("firecrawl", "infra"),
    ("vercel.com", "infra"),
    ("circleci", "infra"),
    ("depot.dev", "infra"),
    ("supabase", "infra"),
    ("aikido", "infra"),
    ("brave", "infra"),
    ("hostinger", "infra"),
    # Cloud / billing
    ("anthropic.com", "infra"),
    ("openai.com", "infra"),
    ("xai.com", "infra"),
    ("vultr.com", "infra"),
    ("stripe.com", "infra"),
    ("neon.tech", "infra"),
    ("docker.com", "infra"),
    ("firebase", "infra"),
    # Slack
    ("slack.com", "noise"),
    ("slackbot", "noise"),
    # Zoom
    ("zoom.us", "noise"),
    ("zoom.com", "noise"),
    # Wellfound
    ("wellfound", "jobs"),
    # Indeed
    ("indeed.com", "jobs"),
    # Crossing Hurdles
    ("crossinghurdles", "jobs"),
    # Job boards
    ("80000hours", "jobs"),
    ("braintrust", "jobs"),
    ("greenhouse-mail", "jobs"),
    ("ashbyhq.com", "jobs"),
    ("upwork.com", "jobs"),
]


def _rule_bot(msg: dict) -> Optional[TriageResult]:
    """Archive known bot / automated senders."""
    addr = _sender(msg)
    name = _sender_name(msg)
    combined = f"{addr} {name}"

    for pattern, folder in BOT_RULES:
        if pattern in combined:
            return TriageResult(Action.ARCHIVE, f"Bot: {pattern}", label=folder)
    return None


# ─── Rule 4: Newsletters / marketing — batch to folder ───────────

NEWSLETTER_PATTERNS = [
    ("hackernoon", "newsletters"),
    ("substack.com", "newsletters"),
    ("beehiiv", "newsletters"),
    ("mailchimp", "newsletters"),
    ("readwise", "newsletters"),
    ("tryhackme", "newsletters"),
    ("codecrafters", "newsletters"),
    ("daily.dev", "newsletters"),
    ("posthog", "newsletters"),
    ("mermaid", "newsletters"),
    ("notebooklm", "newsletters"),
    ("otter.ai", "newsletters"),
    ("granola", "newsletters"),
    ("forwardfuture", "newsletters"),
    ("matthew berman", "newsletters"),
    ("limited edition", "newsletters"),
    ("clickup", "newsletters"),
    ("execute program", "newsletters"),
    ("neetcode", "newsletters"),
    ("mem.ai", "newsletters"),
    ("humanlayer", "newsletters"),
    ("ecstatic dance", "newsletters"),
    ("sideguide", "newsletters"),
    ("kernel tech", "newsletters"),
    ("apple developer", "newsletters"),
    ("patreon", "newsletters"),
    ("arc.net", "newsletters"),
    ("neo4j", "newsletters"),
    ("simply always awake", "newsletters"),
    ("vipassana", "newsletters"),
    ("medicine festival", "newsletters"),
    ("buddhafield", "newsletters"),
    ("throssel", "newsletters"),
]


def _rule_newsletter(msg: dict) -> Optional[TriageResult]:
    """Route newsletters to the newsletters folder."""
    addr = _sender(msg)
    name = _sender_name(msg)
    combined = f"{addr} {name}"

    for pattern, folder in NEWSLETTER_PATTERNS:
        if pattern in combined:
            return TriageResult(Action.ARCHIVE, f"Newsletter: {pattern}", label=folder)
    return None


# ─── Rule 5: Commerce / receipts — archive to folder ─────────────

COMMERCE_PATTERNS = [
    ("amazon.", "commerce"),
    ("paypal", "commerce"),
    ("trainline", "commerce"),
    ("tesco", "commerce"),
    ("evri", "commerce"),
    ("boots.com", "commerce"),
    ("eflorist", "commerce"),
    ("playstation", "commerce"),
    ("revolut.com", "commerce"),
    ("moneybox", "commerce"),
    ("barclays", "commerce"),
    ("mbna", "commerce"),
    ("virgin money", "commerce"),
    ("experian", "commerce"),
    ("coinbase", "commerce"),
    ("trezor", "commerce"),
    ("namecheap", "commerce"),
    ("ovhcloud", "commerce"),
    ("123-reg", "commerce"),
    ("godaddy", "commerce"),
    ("capital on tap", "commerce"),
    ("capitalontap", "commerce"),
    ("iwoca", "commerce"),
    ("universal credit", "commerce"),
    ("companies house", "commerce"),
    ("worldpay", "commerce"),
    ("steroids-uk", "commerce"),
    ("sarms", "commerce"),
    ("blood.co.uk", "commerce"),
    ("swan.bitcoin", "commerce"),
    ("setapp", "commerce"),
    ("paddle.com", "commerce"),
    ("lemon squeezy", "commerce"),
    ("wix.com", "commerce"),
]

# iCloud-specific commerce
ICLOUD_COMMERCE = [
    ("amazon", "receipts"),
    ("paypal", "receipts"),
    ("boots", "receipts"),
    ("revolut", "receipts"),
    ("virgin money", "receipts"),
    ("barclays", "receipts"),
    ("mbna", "receipts"),
    ("moneybox", "receipts"),
    ("experian", "receipts"),
    ("steroids", "receipts"),
    ("setapp", "receipts"),
    ("paddle", "receipts"),
    ("swan", "receipts"),
    ("coinbase", "receipts"),
    ("trezor", "receipts"),
]


def _rule_commerce(msg: dict) -> Optional[TriageResult]:
    """Route commerce/receipts to the appropriate folder."""
    addr = _sender(msg)
    name = _sender_name(msg)
    combined = f"{addr} {name}"
    account = _account_for(msg)

    # iCloud gets its own receipts folder
    if account == "icloud":
        for pattern, folder in ICLOUD_COMMERCE:
            if pattern in combined:
                return TriageResult(
                    Action.ARCHIVE, f"Receipt: {pattern}", label=folder
                )

    for pattern, folder in COMMERCE_PATTERNS:
        if pattern in combined:
            return TriageResult(
                Action.ARCHIVE, f"Commerce: {pattern}", label=folder
            )
    return None


# ─── Rule 6: Verification codes / OTP — noise ────────────────────

OTP_PATTERNS = [
    r"verification code",
    r"login code",
    r"security code",
    r"magic link",
    r"one-time",
    r"your code is",
    r"\b\d{6}\b.*code",
]


def _rule_otp(msg: dict) -> Optional[TriageResult]:
    """Archive OTP / verification code emails."""
    subj = _subject(msg)
    for pattern in OTP_PATTERNS:
        if re.search(pattern, subj):
            return TriageResult(Action.ARCHIVE, f"OTP: {pattern}", label="noise")
    return None


# ─── Rule 7: Job application confirmations — auto-archive ────────

JOB_CONFIRM_SUBJECTS = [
    "thank you for applying",
    "thanks for applying",
    "we've received your application",
    "we have received your application",
    "thank you for your interest",
    "thank you for your recent application",
    "application received",
    "your application to",
    "one last step for your application",
    "complete your.*application",
]


def _rule_job_confirmation(msg: dict) -> Optional[TriageResult]:
    """Archive generic job application confirmations."""
    subj = _subject(msg)
    for pattern in JOB_CONFIRM_SUBJECTS:
        if re.search(pattern, subj):
            return TriageResult(
                Action.ARCHIVE, f"Job confirm: {pattern}", label="jobs"
            )
    return None


# ─── Rule 8: Self-sends — noise ──────────────────────────────────

def _rule_self_send(msg: dict) -> Optional[TriageResult]:
    """Archive emails sent to yourself."""
    addr = _sender(msg)
    to = _to_addr(msg)
    if addr == to:
        return TriageResult(Action.ARCHIVE, "Self-send", label="noise")
    # Also catch Rick → Kai and vice versa
    own_addrs = {"kai@oceanheart.ai", "rickhallett@icloud.com"}
    if addr in own_addrs and to in own_addrs:
        return TriageResult(Action.ARCHIVE, "Self-send (cross-account)", label="noise")
    return None


# ─── Rule Registry ────────────────────────────────────────────────
# Order matters: first match wins.
# VIPs checked first to prevent false-positive archival.

RULES = [
    _rule_vip,           # 1. Always surface VIPs
    _rule_phishing,      # 2. Nuke phishing
    _rule_self_send,     # 3. Self-sends → noise
    _rule_otp,           # 4. OTP codes → noise
    _rule_bot,           # 5. Bots → labeled folders
    _rule_job_confirmation,  # 6. Job confirms → jobs/
    _rule_newsletter,    # 7. Newsletters → newsletters/
    _rule_commerce,      # 8. Commerce → commerce/ or receipts/
]


# ─── Execution ────────────────────────────────────────────────────

def triage(msg: dict) -> TriageResult:
    """Run triage rules against a message. Default: SURFACE."""
    for rule in RULES:
        result = rule(msg)
        if result is not None and result.action != Action.SKIP:
            return result
    return TriageResult(Action.SURFACE, "no rule matched — default surface")


def run_triage(
    messages: list[dict],
    dry_run: bool = True,
    account: str = "gmail",
) -> list[dict]:
    """Triage a batch of messages.

    When dry_run=False, actually moves/archives messages via engine.
    Returns list of {message_id, from, subject, action, reason, label} dicts.
    """
    from . import engine

    results = []
    moved = 0
    for msg in messages:
        result = triage(msg)
        entry = {
            "message_id": msg.get("id"),
            "from": msg.get("from", {}).get("addr", "unknown"),
            "subject": msg.get("subject", "(no subject)"),
            "action": result.action.value,
            "reason": result.reason,
            "label": result.label,
        }
        results.append(entry)

        if not dry_run and result.action == Action.ARCHIVE and result.label:
            try:
                engine.move(str(msg["id"]), result.label, account=account)
                engine.flag(str(msg["id"]), "seen", folder=result.label, account=account)
                moved += 1
            except Exception as e:
                log.warning(f"Failed to move {msg['id']} on {account}: {e}")

        if not dry_run and result.action == Action.LABEL and result.label:
            try:
                engine.move(str(msg["id"]), result.label, account=account)
                moved += 1
            except Exception as e:
                log.warning(f"Failed to label {msg['id']} on {account}: {e}")

    if not dry_run:
        log.info(f"[{account}] Moved {moved}/{len(messages)} messages")
        # Publish triage results to Halostream
        from halos.eventsource.publish import fire_event
        for entry in results:
            fire_event("mail.triage.executed", {
                "sender": entry["from"],
                "subject": entry["subject"],
                "action": entry["action"],
                "reason": entry["reason"],
                "label": entry.get("label"),
            })

    return results
