import streamlit as st
import json
import random
import os
from pathlib import Path

# ---------- page config ----------
st.set_page_config(page_title="Diplomacy – BrainBurst", page_icon="🌍", layout="centered")

# ---------- CSS (matches main app) ----------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    }
    section[data-testid="stSidebar"] {
        background: rgba(15, 12, 41, 0.95);
    }
    .q-header {
        color: #ffd200;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    .q-text {
        font-size: 1.35rem;
        color: #eee;
        line-height: 1.6;
        margin: 0.6rem 0 1.4rem 0;
    }
    .score-bar {
        display: flex;
        gap: 1.5rem;
        justify-content: center;
        margin-bottom: 1.5rem;
    }
    .score-item {
        background: rgba(255,255,255,0.07);
        border-radius: 10px;
        padding: 0.6rem 1.4rem;
        text-align: center;
    }
    .score-item .val { font-size: 1.4rem; font-weight: 700; color: #ffd200; }
    .score-item .lbl { font-size: 0.75rem; color: #999; }
    .feedback-correct {
        background: rgba(46, 204, 113, 0.15);
        border-left: 4px solid #2ecc71;
        padding: 1rem;
        border-radius: 8px;
        color: #2ecc71;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .feedback-wrong {
        background: rgba(231, 76, 60, 0.15);
        border-left: 4px solid #e74c3c;
        padding: 1rem;
        border-radius: 8px;
        color: #e74c3c;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .source-box {
        background: rgba(255,210,0,0.08);
        border-left: 4px solid #ffd200;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        color: #b8b8d0;
        font-size: 0.85rem;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
    }
    .perception-box {
        background: rgba(155,89,182,0.12);
        border-left: 4px solid #9b59b6;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        color: #c9a5e0;
        font-size: 0.9rem;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
    }
    .category-tag {
        display: inline-block;
        background: rgba(255,210,0,0.15);
        color: #ffd200;
        padding: 0.2rem 0.7rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    div.stButton > button {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

DIFFICULTY_EMOJI = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}

# Perception notes for categories that deal with how nations frame events
PERCEPTION_NOTES = {
    "Truth vs Narrative": "Nations frame the same events through vastly different lenses — what one calls 'liberation', another calls 'occupation'.",
    "Diplomatic Language & Spin": "Diplomatic language is designed to obscure as much as it reveals. The words chosen carry political weight.",
    "Foreign Policy Disagreements": "Disagreements at the UN reveal how countries weigh sovereignty, human rights, and alliances differently.",
    "Bilateral Tensions & Alliances": "Alliances shift based on strategic interests — today's partner may be tomorrow's rival.",
    "US Foreign Policy": "US foreign policy decisions ripple globally — allies and adversaries perceive the same action in opposite ways.",
    "UN & Multilateral Diplomacy": "Multilateral bodies are arenas where competing national narratives collide and sometimes compromise.",
    "EU & NATO Affairs": "European unity is tested when member states have divergent threat perceptions and economic interests.",
    "Asia-Pacific Geopolitics": "The Indo-Pacific is shaped by overlapping territorial claims, tech competition, and shifting alliance networks.",
    "Africa & Global South Diplomacy": "The Global South increasingly challenges Western-led frameworks, demanding a seat at the table.",
    "International Law & Treaties": "International law creates rules everyone agrees to — until enforcement threatens national interest.",
    "Historical Diplomatic Milestones": "History's treaties redrew maps and shifted power — understanding them reveals patterns that repeat today.",
    "Middle East Diplomacy": "The Middle East is where oil, religion, colonial borders, and great-power rivalry collide — every peace deal has a counter-narrative.",
    "Economic Diplomacy & Sanctions": "Sanctions are war by other means — they reshape economies, but who they actually hurt is always contested.",
    "Intelligence & Espionage in Diplomacy": "Behind every diplomatic handshake, intelligence agencies are reading the other side's cards.",
    "Cyber Diplomacy & Tech Geopolitics": "The digital battlefield has no borders — semiconductors, data, and code are the new instruments of power.",
}

# ---------- load questions ----------
@st.cache_data
def load_questions():
    # Try local copy first, then /tmp fallback
    paths = [
        Path(__file__).parent.parent / "diplomacy_questions.json",
        Path("/tmp/brainburst_all_questions.json"),
    ]
    for p in paths:
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return []

ALL_QUESTIONS = load_questions()

# ---------- session state defaults ----------
diplo_defaults = {
    "diplo_active": False,
    "diplo_questions": [],
    "diplo_idx": 0,
    "diplo_score": 0,
    "diplo_streak": 0,
    "diplo_answered": False,
    "diplo_selected": None,
    "diplo_options": [],
    "diplo_results": [],
    "diplo_mode": "normal",
    "diplo_seen_ids": set(),   # track seen question IDs across rounds
    "diplo_pool_reset": False, # flag when pool was exhausted and reset
}
for k, v in diplo_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Also init shared stats from the main game
for k in ("total_played", "total_correct", "best_streak"):
    if k not in st.session_state:
        st.session_state[k] = 0


def select_questions(mode, count=10):
    """Pick *unseen* questions based on difficulty mode.

    Tracks seen question IDs in session_state so no question repeats
    until the eligible pool is exhausted.  When that happens the seen
    set is cleared and the user is notified via a flag.
    Thread-safe: session_state is per-session in Streamlit.
    Memory-safe: only a set of short string IDs is stored.
    """
    seen: set = st.session_state.diplo_seen_ids
    st.session_state.diplo_pool_reset = False

    def _unseen(qs):
        return [q for q in qs if q.get("id") not in seen]

    if mode == "hard":
        hard = _unseen([q for q in ALL_QUESTIONS if q.get("difficulty") == "hard"])
        medium = _unseen([q for q in ALL_QUESTIONS if q.get("difficulty") == "medium"])
        eligible = hard + medium
    else:
        easy = _unseen([q for q in ALL_QUESTIONS if q.get("difficulty") == "easy"])
        medium = _unseen([q for q in ALL_QUESTIONS if q.get("difficulty") == "medium"])
        eligible = easy + medium

    # If not enough unseen questions, reset the pool
    if len(eligible) < count:
        st.session_state.diplo_seen_ids = set()
        seen = st.session_state.diplo_seen_ids
        st.session_state.diplo_pool_reset = True
        # Rebuild eligible after reset
        if mode == "hard":
            hard = [q for q in ALL_QUESTIONS if q.get("difficulty") == "hard"]
            medium = [q for q in ALL_QUESTIONS if q.get("difficulty") == "medium"]
            eligible = hard + medium
        else:
            easy = [q for q in ALL_QUESTIONS if q.get("difficulty") == "easy"]
            medium = [q for q in ALL_QUESTIONS if q.get("difficulty") == "medium"]
            eligible = easy + medium

    random.shuffle(eligible)
    selected = eligible[:count]

    # Mark selected questions as seen
    for q in selected:
        st.session_state.diplo_seen_ids.add(q.get("id"))

    return selected


# ===================================================================
#  SETUP PHASE
# ===================================================================
if not st.session_state.diplo_active:
    st.markdown(
        '<p style="font-size:2.4rem;font-weight:800;text-align:center;'
        'background:linear-gradient(90deg,#f7971e,#ffd200);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent;">'
        '🌍 Diplomatic Trivia</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:center;color:#b8b8d0;font-size:1.05rem;margin-bottom:2rem;">'
        'Test your knowledge of how nations navigate power, truth, and perception.'
        '</p>',
        unsafe_allow_html=True,
    )

    # Category breakdown
    categories = sorted(set(q.get("category", "Unknown") for q in ALL_QUESTIONS))
    cat_counts = {}
    for q in ALL_QUESTIONS:
        c = q.get("category", "Unknown")
        cat_counts[c] = cat_counts.get(c, 0) + 1

    st.markdown(
        '<p style="color:#ffd200;font-weight:700;font-size:1rem;margin-bottom:0.5rem;">'
        'Question Pool: {} questions across {} categories</p>'.format(
            len(ALL_QUESTIONS), len(categories)
        ),
        unsafe_allow_html=True,
    )

    # Show categories as tags
    tags = " ".join(
        f'<span class="category-tag">{c} ({cat_counts[c]})</span>' for c in categories
    )
    st.markdown(f'<div style="margin-bottom:1.5rem;">{tags}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Difficulty mode selection
    col1, col2 = st.columns(2)
    with col1:
        mode = st.radio(
            "Difficulty",
            ["normal", "hard"],
            format_func=lambda x: {"normal": "🟡 Normal (Easy + Medium)", "hard": "🔴 Hard"}[x],
            horizontal=True,
        )
    with col2:
        num_q = st.slider("Questions", 5, 20, 10)

    st.markdown("")

    # What to expect
    if mode == "hard":
        st.info(
            "**Hard mode:** Deep-cut diplomatic events, specific dates, institutional details, "
            "and questions where nations' competing narratives make the 'right' answer debatable."
        )
    else:
        st.info(
            "**Normal mode:** Headline-level diplomacy — NATO expansion, BRICS, major UN votes, "
            "and key bilateral moments. You follow the news? You'll do fine."
        )

    # Show how many unseen questions remain
    if st.session_state.diplo_seen_ids:
        if mode == "hard":
            mode_pool = [q for q in ALL_QUESTIONS if q.get("difficulty") in ("hard", "medium")]
        else:
            mode_pool = [q for q in ALL_QUESTIONS if q.get("difficulty") in ("easy", "medium")]
        remaining = len([q for q in mode_pool if q.get("id") not in st.session_state.diplo_seen_ids])
        st.caption(f"🧠 {remaining} unseen questions remaining in this mode ({len(st.session_state.diplo_seen_ids)} seen so far)")

    if st.button("🚀 Start Round", use_container_width=True, type="primary"):
        qs = select_questions(mode, num_q)
        if st.session_state.diplo_pool_reset:
            st.toast("🔄 You've seen all questions! Pool refreshed — some may repeat this round.", icon="🔄")
        if not qs:
            st.error("No questions available. Check that diplomacy_questions.json exists.")
        else:
            st.session_state.diplo_questions = qs
            st.session_state.diplo_active = True
            st.session_state.diplo_idx = 0
            st.session_state.diplo_score = 0
            st.session_state.diplo_streak = 0
            st.session_state.diplo_answered = False
            st.session_state.diplo_selected = None
            st.session_state.diplo_results = []
            st.session_state.diplo_mode = mode
            # Shuffle first question options
            q = qs[0]
            opts = q["incorrect_answers"] + [q["correct_answer"]]
            random.shuffle(opts)
            st.session_state.diplo_options = opts
            st.rerun()

# ===================================================================
#  GAME PHASE
# ===================================================================
elif st.session_state.diplo_active and st.session_state.diplo_idx < len(st.session_state.diplo_questions):
    q = st.session_state.diplo_questions[st.session_state.diplo_idx]
    total = len(st.session_state.diplo_questions)
    idx = st.session_state.diplo_idx
    cat = q.get("category", "Unknown")

    # Mode badge
    mode_label = "🔴 Hard Mode" if st.session_state.diplo_mode == "hard" else "🟡 Normal Mode"
    st.caption(f"🌍 Diplomatic Trivia · {mode_label}")

    # Progress bar
    st.progress(idx / total)

    # Score bar
    st.markdown(f"""
    <div class="score-bar">
        <div class="score-item"><div class="val">{idx+1}/{total}</div><div class="lbl">Question</div></div>
        <div class="score-item"><div class="val">{st.session_state.diplo_score}</div><div class="lbl">Score</div></div>
        <div class="score-item"><div class="val">🔥 {st.session_state.diplo_streak}</div><div class="lbl">Streak</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Category and difficulty
    diff = q.get("difficulty", "medium")
    diff_em = DIFFICULTY_EMOJI.get(diff, "⚪")
    st.markdown(f'<p class="q-header">{cat} · {diff_em} {diff.title()}</p>', unsafe_allow_html=True)

    # Question text
    st.markdown(f'<p class="q-text">{q["question"]}</p>', unsafe_allow_html=True)

    options = st.session_state.diplo_options

    if not st.session_state.diplo_answered:
        # Answer buttons
        cols = st.columns(2)
        for i, opt in enumerate(options):
            with cols[i % 2]:
                if st.button(opt, key=f"dopt_{idx}_{i}", use_container_width=True):
                    st.session_state.diplo_selected = opt
                    st.session_state.diplo_answered = True
                    correct = (opt == q["correct_answer"])
                    st.session_state.diplo_results.append({
                        "correct": correct,
                        "chosen": opt,
                        "answer": q["correct_answer"],
                        "category": cat,
                    })
                    st.session_state.total_played += 1
                    if correct:
                        st.session_state.diplo_score += 1
                        st.session_state.diplo_streak += 1
                        st.session_state.total_correct += 1
                        if st.session_state.diplo_streak > st.session_state.best_streak:
                            st.session_state.best_streak = st.session_state.diplo_streak
                    else:
                        st.session_state.diplo_streak = 0
                    st.rerun()
    else:
        # Show feedback
        selected = st.session_state.diplo_selected
        correct_ans = q["correct_answer"]
        if selected == correct_ans:
            st.markdown('<div class="feedback-correct">✅ Correct!</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="feedback-wrong">❌ Wrong — the answer was <b>{correct_ans}</b></div>',
                unsafe_allow_html=True,
            )

        # Show options with color coding
        cols = st.columns(2)
        for i, opt in enumerate(options):
            with cols[i % 2]:
                if opt == correct_ans:
                    st.success(f"✅ {opt}")
                elif opt == selected and opt != correct_ans:
                    st.error(f"❌ {opt}")
                else:
                    st.button(opt, key=f"ddis_{idx}_{i}", disabled=True, use_container_width=True)

        # Source citation
        source = q.get("source", "")
        if source:
            st.markdown(f'<div class="source-box">📄 <b>Source:</b> {source}</div>', unsafe_allow_html=True)

        # Perception note for relevant categories
        note = PERCEPTION_NOTES.get(cat, "")
        if note:
            st.markdown(f'<div class="perception-box">🔍 <b>Perception lens:</b> {note}</div>', unsafe_allow_html=True)

        # Next button
        st.markdown("")
        btn_label = "➡️ Next Question" if idx + 1 < total else "🏁 See Results"
        if st.button(btn_label, use_container_width=True, type="primary"):
            next_idx = st.session_state.diplo_idx + 1
            st.session_state.diplo_idx = next_idx
            st.session_state.diplo_answered = False
            st.session_state.diplo_selected = None
            if next_idx < total:
                nq = st.session_state.diplo_questions[next_idx]
                opts = nq["incorrect_answers"] + [nq["correct_answer"]]
                random.shuffle(opts)
                st.session_state.diplo_options = opts
            st.rerun()

# ===================================================================
#  RESULTS PHASE
# ===================================================================
else:
    total = len(st.session_state.diplo_questions)
    score = st.session_state.diplo_score
    pct = round(score / total * 100) if total else 0

    # Reaction
    if pct == 100:
        reaction, color = "🏆 Ambassador-Level!", "#2ecc71"
    elif pct >= 80:
        reaction, color = "🔥 Policy Wonk!", "#f39c12"
    elif pct >= 60:
        reaction, color = "📰 News Junkie!", "#3498db"
    elif pct >= 40:
        reaction, color = "🤔 Headline Skimmer", "#9b59b6"
    else:
        reaction, color = "😴 Diplomatically Disengaged", "#e74c3c"

    mode_label = "Hard" if st.session_state.diplo_mode == "hard" else "Normal"

    st.markdown(f"""
    <div style="text-align:center;padding:2rem 0;">
        <p style="font-size:3rem;margin-bottom:0;">{reaction}</p>
        <p style="font-size:5rem;font-weight:800;color:{color};margin:0.2rem 0;">{score}/{total}</p>
        <p style="font-size:1.2rem;color:#b8b8d0;">
            {pct}% accuracy · {mode_label} mode · Best streak: 🔥 {st.session_state.best_streak}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Category breakdown
    results = st.session_state.diplo_results
    cat_scores = {}
    for r in results:
        c = r["category"]
        if c not in cat_scores:
            cat_scores[c] = {"correct": 0, "total": 0}
        cat_scores[c]["total"] += 1
        if r["correct"]:
            cat_scores[c]["correct"] += 1

    st.markdown("### Your Strengths & Gaps")
    for cat, s in sorted(cat_scores.items(), key=lambda x: x[1]["correct"] / max(x[1]["total"], 1), reverse=True):
        cat_pct = round(s["correct"] / s["total"] * 100) if s["total"] else 0
        if cat_pct >= 80:
            bar_color = "#2ecc71"
        elif cat_pct >= 50:
            bar_color = "#f39c12"
        else:
            bar_color = "#e74c3c"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.5rem;">'
            f'<span style="color:#ccc;min-width:260px;font-size:0.9rem;">{cat}</span>'
            f'<div style="flex:1;background:rgba(255,255,255,0.07);border-radius:8px;height:24px;overflow:hidden;">'
            f'<div style="width:{cat_pct}%;height:100%;background:{bar_color};border-radius:8px;'
            f'display:flex;align-items:center;justify-content:center;font-size:0.75rem;font-weight:700;color:#fff;">'
            f'{s["correct"]}/{s["total"]}</div></div></div>',
            unsafe_allow_html=True,
        )

    # Round recap
    with st.expander("📋 Round Recap", expanded=False):
        for i, q in enumerate(st.session_state.diplo_questions):
            r = results[i] if i < len(results) else {"correct": False}
            icon = "✅" if r["correct"] else "❌"
            st.markdown(f"**{icon} Q{i+1}** ({q.get('category','')}) — {q['question']}")
            if not r["correct"]:
                st.markdown(f"  *Your answer: {r.get('chosen','')}* → Correct: **{q['correct_answer']}**")
            source = q.get("source", "")
            if source:
                st.caption(f"Source: {source}")

    # Perception insight
    st.markdown("---")
    st.markdown(
        '<div class="perception-box">'
        '🌍 <b>Remember:</b> In diplomacy, "truth" is often a matter of perspective. '
        "The same event — a military intervention, a trade restriction, a UN vote — "
        "is framed as liberation or aggression, protection or protectionism, justice or "
        "overreach, depending on which capital you're standing in. "
        "The questions you just answered reflect facts, but the narratives around them "
        "are where the real diplomacy happens."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Play Again", use_container_width=True, type="primary"):
            st.session_state.diplo_active = False
            st.session_state.diplo_questions = []
            st.session_state.diplo_idx = 0
            st.session_state.diplo_answered = False
            st.rerun()
    with col2:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.diplo_active = False
            st.switch_page("🏠_Home.py")
