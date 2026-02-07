# BrainBurst Trivia

A local trivia quiz game built with Streamlit — featuring 539+ hand-crafted diplomacy questions and an AI-powered auto-refresh pipeline.

## Quick Start

```bash
git clone https://github.com/nslewis/brainburst.git
cd brainburst
bash start.sh
```

`start.sh` handles everything: creates a virtual environment, installs dependencies, and launches the app. Your browser opens to `http://localhost:8501`.

## Features

- **539+ Diplomacy Questions** — 15 categories covering UN votes, NATO, BRICS, sanctions, espionage, cyber diplomacy, and more
- **General Trivia** — live questions from [Open Trivia Database](https://opentdb.com) across 12+ categories
- **Two Difficulty Modes** — Normal (easy + medium) or Hard mode for diplomacy
- **No-Repeat Rounds** — tracks seen questions so you don't get repeats until you've exhausted the pool
- **Score Tracking** — accuracy, streak counter, category breakdowns, round recaps
- **Perception Lens** — each diplomacy category includes context on how different nations frame events

## Auto-Refresh Pipeline

Generate new diplomacy questions from current news using Claude API:

```bash
# Set your API key
export ANTHROPIC_API_KEY=your-key-here

# Generate 20 new questions from current news
python auto_refresh.py --count 20

# Preview without writing (dry run)
python auto_refresh.py --count 10 --dry-run

# Stage for manual review first
python auto_refresh.py --count 20 --review

# Approve reviewed questions
python auto_refresh.py --approve
```

The pipeline:
1. Fetches headlines from BBC, Al Jazeera, The Guardian, Reuters, and AP
2. Sends news summaries to Claude to generate trivia questions
3. Validates schema (correct fields, 3 wrong answers, valid difficulty)
4. Deduplicates against existing questions (fuzzy matching)
5. Appends to `diplomacy_questions.json` with sequential IDs

## Requirements

- Python 3.8+
- Internet connection (for general trivia + RSS feeds)
- `ANTHROPIC_API_KEY` environment variable (only for auto-refresh pipeline)
