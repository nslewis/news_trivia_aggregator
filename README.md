# News Trivia Aggregator

A Streamlit trivia app that turns real-world diplomatic news into quiz questions — with an AI pipeline that generates fresh questions from current events.

## Quick Start

```bash
git clone https://github.com/nslewis/news_trivia_aggregator.git
cd news_trivia_aggregator
bash start.sh
```

`start.sh` creates a virtual environment, installs dependencies, and launches the app at `http://localhost:8501`.

## What's Inside

**The App** — a multi-page Streamlit game with two modes:
- **General Trivia** — live questions from [Open Trivia Database](https://opentdb.com), pick category/difficulty/count
- **Diplomacy Quiz** — 539+ curated questions across 15 categories (UN votes, NATO, sanctions, espionage, cyber diplomacy, etc.), with Normal and Hard modes

**The Pipeline** (`auto_refresh.py`) — a CLI tool that:
1. Pulls headlines from BBC, Al Jazeera, The Guardian, Reuters, and AP via RSS
2. Sends news summaries to Claude API to generate trivia questions
3. Validates schema and deduplicates against the existing question bank
4. Appends new questions with sequential IDs

```bash
export ANTHROPIC_API_KEY=your-key-here

python auto_refresh.py --count 20             # generate 20 new questions
python auto_refresh.py --count 10 --dry-run   # preview without writing
python auto_refresh.py --count 20 --review    # stage for manual review
python auto_refresh.py --approve              # merge reviewed questions
```

## Project Structure

```
🏠_Home.py                  # dashboard + stats
pages/1_▶️_Play.py           # general trivia (OpenTDB)
pages/2_🌍_Diplomacy.py      # diplomacy quiz
diplomacy_questions.json     # 539+ questions (the data)
auto_refresh.py              # news → trivia pipeline
start.sh                     # one-click launcher
requirements.txt             # dependencies
```

## Requirements

- Python 3.8+
- Internet connection (for general trivia + RSS feeds)
- `ANTHROPIC_API_KEY` env var (only needed for the auto-refresh pipeline)
