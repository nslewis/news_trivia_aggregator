#!/usr/bin/env python3
"""
BrainBurst Auto-Refresh Pipeline
=================================
Fetches diplomatic news via RSS, generates trivia questions with Claude API,
validates, deduplicates, and appends to diplomacy_questions.json.

Usage:
    python auto_refresh.py --count 20            # Generate 20 new questions
    python auto_refresh.py --count 20 --review   # Stage for review (pending_questions.json)
    python auto_refresh.py --approve              # Merge pending into main
    python auto_refresh.py --count 10 --dry-run   # Preview without writing

Requires: ANTHROPIC_API_KEY environment variable
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

try:
    import feedparser
except ImportError:
    sys.exit("Missing dependency: pip install feedparser>=6.0")

try:
    import anthropic
except ImportError:
    sys.exit("Missing dependency: pip install anthropic>=0.40.0")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
QUESTIONS_FILE = SCRIPT_DIR / "diplomacy_questions.json"
PENDING_FILE = SCRIPT_DIR / "pending_questions.json"

RSS_FEEDS = {
    "Reuters World": "https://feeds.reuters.com/Reuters/worldNews",
    "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "The Guardian World": "https://www.theguardian.com/world/rss",
    "AP News World": "https://rsshub.app/apnews/topics/world-news",
}

VALID_CATEGORIES = [
    "Foreign Policy Disagreements",
    "UN & Multilateral Diplomacy",
    "EU & NATO Affairs",
    "Asia-Pacific Geopolitics",
    "Middle East Diplomacy",
    "Africa & Global South Diplomacy",
    "Bilateral Tensions & Alliances",
    "Economic Diplomacy & Sanctions",
    "International Law & Treaties",
    "US Foreign Policy",
    "Truth vs Narrative",
    "Diplomatic Language & Spin",
    "Historical Diplomatic Milestones",
    "Intelligence & Espionage in Diplomacy",
    "Cyber Diplomacy & Tech Geopolitics",
]

VALID_DIFFICULTIES = ["easy", "medium", "hard"]

REQUIRED_FIELDS = [
    "category",
    "difficulty",
    "question",
    "correct_answer",
    "incorrect_answers",
    "source",
]

DEDUP_THRESHOLD = 0.85  # similarity ratio above which = duplicate

LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(message)s"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
log = logging.getLogger("auto_refresh")

# ---------------------------------------------------------------------------
# RSS Fetching
# ---------------------------------------------------------------------------


def fetch_news(max_per_feed: int = 10) -> list[dict]:
    """Pull headlines + summaries from diplomatic RSS feeds."""
    items = []
    for name, url in RSS_FEEDS.items():
        log.info("Fetching RSS: %s", name)
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                log.warning("  Feed error for %s: %s", name, feed.bozo_exception)
                continue
            for entry in feed.entries[:max_per_feed]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                # Strip HTML tags from summary
                summary = re.sub(r"<[^>]+>", "", summary).strip()
                if title:
                    items.append(
                        {
                            "title": title,
                            "summary": summary[:500] if summary else title,
                            "source": name,
                            "link": entry.get("link", ""),
                        }
                    )
            log.info("  Got %d items from %s", min(len(feed.entries), max_per_feed), name)
        except Exception as e:
            log.warning("  Failed to fetch %s: %s", name, e)
    log.info("Total news items fetched: %d", len(items))
    return items


# ---------------------------------------------------------------------------
# Question Generation (Claude API)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert trivia question generator specializing in diplomacy, geopolitics, and international relations.

You create challenging, educational multiple-choice trivia questions based on real news events. Your questions should:
- Be factually accurate and based on the provided news items
- Have exactly ONE correct answer and exactly THREE plausible but incorrect answers
- Cover a range of difficulties (easy, medium, hard)
- Be assigned to one of the existing categories when possible

Target difficulty distribution: ~30% easy, ~35% medium, ~35% hard

Available categories:
""" + "\n".join(f"- {c}" for c in VALID_CATEGORIES) + """

If a question doesn't fit any existing category, use the closest match.

IMPORTANT: Return ONLY valid JSON — no markdown fences, no commentary."""

USER_PROMPT_TEMPLATE = """Based on these recent diplomatic/geopolitical news items, generate exactly {count} trivia questions.

NEWS ITEMS:
{news_block}

Return a JSON array of objects with this EXACT schema:
[
  {{
    "category": "one of the listed categories",
    "difficulty": "easy" | "medium" | "hard",
    "question": "the trivia question text",
    "correct_answer": "the correct answer",
    "incorrect_answers": ["wrong1", "wrong2", "wrong3"],
    "source": "brief citation of the news event / source"
  }}
]

Requirements:
- Exactly {count} questions
- Exactly 3 incorrect_answers per question
- Each question must cite which news event it's based on in the source field
- Mix difficulties: ~30% easy, ~35% medium, ~35% hard
- Questions should test knowledge of the EVENT, not just reading comprehension
- Make incorrect answers plausible — avoid obviously silly options

Return ONLY the JSON array, nothing else."""


def generate_questions(news_items: list[dict], count: int) -> list[dict]:
    """Send news to Claude API and get back trivia questions."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY environment variable is not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Build news block — use up to 15 items for context
    selected_news = news_items[:15]
    news_block = "\n\n".join(
        f"[{i+1}] {item['title']} ({item['source']})\n{item['summary']}"
        for i, item in enumerate(selected_news)
    )

    if not news_block.strip():
        log.error("No news items available to generate questions from")
        return []

    user_prompt = USER_PROMPT_TEMPLATE.format(count=count, news_block=news_block)

    log.info("Sending %d news items to Claude API (requesting %d questions)...", len(selected_news), count)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as e:
        log.error("Claude API error: %s", e)
        return []

    # Extract text from response
    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)

    try:
        questions = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("Failed to parse Claude response as JSON: %s", e)
        log.debug("Raw response:\n%s", raw[:1000])
        return []

    if not isinstance(questions, list):
        log.error("Expected JSON array, got %s", type(questions).__name__)
        return []

    log.info("Claude returned %d questions", len(questions))
    return questions


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_questions(questions: list[dict]) -> tuple[list[dict], list[dict]]:
    """Validate questions against required schema. Returns (valid, invalid)."""
    valid = []
    invalid = []

    for i, q in enumerate(questions):
        errors = []

        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in q or not q[field]:
                errors.append(f"missing or empty field: {field}")

        if not errors:
            # Check incorrect_answers is a list of exactly 3
            if not isinstance(q["incorrect_answers"], list):
                errors.append("incorrect_answers must be a list")
            elif len(q["incorrect_answers"]) != 3:
                errors.append(f"need exactly 3 incorrect_answers, got {len(q['incorrect_answers'])}")

            # Check difficulty
            if q.get("difficulty") not in VALID_DIFFICULTIES:
                errors.append(f"invalid difficulty: {q.get('difficulty')}")

            # Check category — warn but don't reject if it's a new one
            if q.get("category") not in VALID_CATEGORIES:
                log.warning(
                    "  Q%d: category '%s' not in standard list (keeping it)",
                    i + 1,
                    q.get("category"),
                )

            # Check for empty strings in answers
            if not q.get("correct_answer", "").strip():
                errors.append("correct_answer is empty")
            for j, ans in enumerate(q.get("incorrect_answers", [])):
                if not ans.strip():
                    errors.append(f"incorrect_answers[{j}] is empty")

        if errors:
            log.warning("  Q%d INVALID: %s", i + 1, "; ".join(errors))
            invalid.append({"question": q, "errors": errors})
        else:
            valid.append(q)

    log.info("Validation: %d valid, %d invalid", len(valid), len(invalid))
    return valid, invalid


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def similarity(a: str, b: str) -> float:
    """Fuzzy string similarity ratio."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate(new_qs: list[dict], existing_qs: list[dict]) -> tuple[list[dict], list[dict]]:
    """Remove questions that are too similar to existing ones."""
    existing_texts = [q["question"] for q in existing_qs]
    unique = []
    dupes = []

    for q in new_qs:
        is_dupe = False
        q_text = q["question"]

        for existing_text in existing_texts:
            sim = similarity(q_text, existing_text)
            if sim >= DEDUP_THRESHOLD:
                log.info("  DUPE (%.0f%%): %s", sim * 100, q_text[:80])
                dupes.append(q)
                is_dupe = True
                break

        if not is_dupe:
            # Also check against other new questions in this batch
            for already_added in unique:
                sim = similarity(q_text, already_added["question"])
                if sim >= DEDUP_THRESHOLD:
                    log.info("  BATCH DUPE (%.0f%%): %s", sim * 100, q_text[:80])
                    dupes.append(q)
                    is_dupe = True
                    break

        if not is_dupe:
            unique.append(q)

    log.info("Deduplication: %d unique, %d duplicates removed", len(unique), len(dupes))
    return unique, dupes


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


def load_questions(path: Path) -> list[dict]:
    """Load questions from a JSON file."""
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def save_questions(questions: list[dict], path: Path) -> None:
    """Write questions to a JSON file."""
    with open(path, "w") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    log.info("Saved %d questions to %s", len(questions), path.name)


def get_next_id(existing: list[dict]) -> int:
    """Get the next sequential ID number."""
    if not existing:
        return 0
    max_id = 0
    for q in existing:
        qid = q.get("id", "diplo_000")
        try:
            num = int(qid.split("_")[1])
            max_id = max(max_id, num)
        except (IndexError, ValueError):
            pass
    return max_id + 1


def append_questions(new_qs: list[dict]) -> int:
    """Assign sequential IDs and append to diplomacy_questions.json. Returns count added."""
    existing = load_questions(QUESTIONS_FILE)
    next_id = get_next_id(existing)

    for i, q in enumerate(new_qs):
        q["id"] = f"diplo_{next_id + i:03d}"

    existing.extend(new_qs)
    save_questions(existing, QUESTIONS_FILE)
    return len(new_qs)


# ---------------------------------------------------------------------------
# Review mode
# ---------------------------------------------------------------------------


def stage_for_review(questions: list[dict]) -> None:
    """Write questions to pending_questions.json for manual review."""
    pending = load_questions(PENDING_FILE)
    # Give them temporary IDs
    next_temp = len(pending)
    for i, q in enumerate(questions):
        q["id"] = f"pending_{next_temp + i:03d}"
        q["staged_at"] = datetime.now(timezone.utc).isoformat()
    pending.extend(questions)
    save_questions(pending, PENDING_FILE)
    log.info("Staged %d questions for review in %s", len(questions), PENDING_FILE.name)


def approve_pending() -> int:
    """Merge all pending questions into the main file."""
    pending = load_questions(PENDING_FILE)
    if not pending:
        log.info("No pending questions to approve.")
        return 0

    # Strip temporary fields
    for q in pending:
        q.pop("staged_at", None)
        q.pop("id", None)  # Will be re-assigned

    count = append_questions(pending)

    # Clear pending file
    PENDING_FILE.unlink(missing_ok=True)
    log.info("Approved and merged %d questions. Pending file cleared.", count)
    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="BrainBurst Auto-Refresh: generate diplomacy trivia from current news",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python auto_refresh.py --count 20              Generate 20 new questions
  python auto_refresh.py --count 20 --review     Stage for review first
  python auto_refresh.py --approve                Merge pending into main
  python auto_refresh.py --count 10 --dry-run     Preview without writing
        """,
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of questions to generate (default: 10)",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Stage questions in pending_questions.json for manual review",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Approve and merge all pending questions into main file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing to disk",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # --- Approve mode ---
    if args.approve:
        count = approve_pending()
        if count:
            total = len(load_questions(QUESTIONS_FILE))
            print(f"\n✅ Approved {count} questions. Total now: {total}")
        else:
            print("\n📭 No pending questions to approve.")
        return

    # --- Generate mode ---
    print(f"\n🧠 BrainBurst Auto-Refresh Pipeline")
    print(f"{'=' * 40}")

    # Step 1: Fetch news
    print("\n📡 Step 1: Fetching diplomatic news...")
    news = fetch_news()
    if not news:
        print("❌ No news items fetched. Check your internet connection.")
        sys.exit(1)
    print(f"   ✅ {len(news)} news items from {len(RSS_FEEDS)} feeds")

    # Step 2: Generate questions
    print(f"\n🤖 Step 2: Generating {args.count} questions via Claude API...")
    raw_questions = generate_questions(news, args.count)
    if not raw_questions:
        print("❌ No questions generated. Check API key and try again.")
        sys.exit(1)
    print(f"   ✅ {len(raw_questions)} raw questions generated")

    # Step 3: Validate
    print("\n✅ Step 3: Validating questions...")
    valid, invalid = validate_questions(raw_questions)
    if invalid:
        print(f"   ⚠️  {len(invalid)} questions failed validation")
    print(f"   ✅ {len(valid)} questions passed validation")

    if not valid:
        print("❌ No valid questions after validation. Try again.")
        sys.exit(1)

    # Step 4: Deduplicate
    print("\n🔍 Step 4: Deduplicating against existing questions...")
    existing = load_questions(QUESTIONS_FILE)
    unique, dupes = deduplicate(valid, existing)
    if dupes:
        print(f"   ⚠️  {len(dupes)} duplicates removed")
    print(f"   ✅ {len(unique)} unique new questions")

    if not unique:
        print("❌ All questions were duplicates. Try again for fresh content.")
        sys.exit(1)

    # Step 5: Output
    if args.dry_run:
        print(f"\n🔍 DRY RUN — Would add {len(unique)} questions:")
        print("-" * 60)
        for i, q in enumerate(unique):
            print(f"\n  [{i+1}] ({q['difficulty']}) {q['category']}")
            print(f"      Q: {q['question']}")
            print(f"      A: {q['correct_answer']}")
            print(f"      Wrong: {', '.join(q['incorrect_answers'])}")
            print(f"      Source: {q['source']}")
        print(f"\n📊 Difficulty mix: "
              f"easy={sum(1 for q in unique if q['difficulty']=='easy')}, "
              f"medium={sum(1 for q in unique if q['difficulty']=='medium')}, "
              f"hard={sum(1 for q in unique if q['difficulty']=='hard')}")
        print("\n✅ Dry run complete. No files were modified.")
        return

    if args.review:
        stage_for_review(unique)
        pending_total = len(load_questions(PENDING_FILE))
        print(f"\n📋 Staged {len(unique)} questions for review.")
        print(f"   Total pending: {pending_total}")
        print(f"   Review: {PENDING_FILE}")
        print(f"   Approve: python auto_refresh.py --approve")
    else:
        count = append_questions(unique)
        total = len(load_questions(QUESTIONS_FILE))
        print(f"\n✅ Added {count} new questions to diplomacy_questions.json")
        print(f"   Total questions: {total}")

    # Summary
    print(f"\n{'=' * 40}")
    print("🎉 Pipeline complete!")


if __name__ == "__main__":
    main()
