import streamlit as st
import requests
import html
import random
import time

# ---------- page config ----------
st.set_page_config(page_title="Play – News Trivia", page_icon="▶️", layout="centered")

# ---------- CSS ----------
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
    div.stButton > button {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ---------- fallback questions ----------
FALLBACK_QUESTIONS = [
    {"category":"Science","difficulty":"medium","question":"What planet is known as the Red Planet?","correct_answer":"Mars","incorrect_answers":["Venus","Jupiter","Saturn"]},
    {"category":"History","difficulty":"easy","question":"In which year did the Titanic sink?","correct_answer":"1912","incorrect_answers":["1905","1918","1923"]},
    {"category":"Geography","difficulty":"easy","question":"What is the largest ocean on Earth?","correct_answer":"Pacific Ocean","incorrect_answers":["Atlantic Ocean","Indian Ocean","Arctic Ocean"]},
    {"category":"Science","difficulty":"hard","question":"What is the chemical symbol for Tungsten?","correct_answer":"W","incorrect_answers":["Tu","Tg","Wn"]},
    {"category":"Entertainment","difficulty":"medium","question":"Who directed the movie Inception?","correct_answer":"Christopher Nolan","incorrect_answers":["Steven Spielberg","James Cameron","Ridley Scott"]},
    {"category":"Science","difficulty":"easy","question":"How many bones are in the adult human body?","correct_answer":"206","incorrect_answers":["201","209","215"]},
    {"category":"History","difficulty":"medium","question":"Which empire was ruled by Genghis Khan?","correct_answer":"Mongol Empire","incorrect_answers":["Ottoman Empire","Roman Empire","Persian Empire"]},
    {"category":"Geography","difficulty":"easy","question":"What is the smallest country in the world?","correct_answer":"Vatican City","incorrect_answers":["Monaco","San Marino","Liechtenstein"]},
    {"category":"Science","difficulty":"medium","question":"What gas do plants absorb from the atmosphere?","correct_answer":"Carbon Dioxide","incorrect_answers":["Oxygen","Nitrogen","Hydrogen"]},
    {"category":"Entertainment","difficulty":"easy","question":"What band sang 'Bohemian Rhapsody'?","correct_answer":"Queen","incorrect_answers":["The Beatles","Led Zeppelin","Pink Floyd"]},
    {"category":"History","difficulty":"hard","question":"The Rosetta Stone was discovered in which year?","correct_answer":"1799","incorrect_answers":["1815","1762","1801"]},
    {"category":"Geography","difficulty":"medium","question":"What is the capital of Australia?","correct_answer":"Canberra","incorrect_answers":["Sydney","Melbourne","Brisbane"]},
    {"category":"Science","difficulty":"hard","question":"What is the half-life of Carbon-14 (approx.)?","correct_answer":"5,730 years","incorrect_answers":["3,200 years","8,400 years","12,000 years"]},
    {"category":"Entertainment","difficulty":"medium","question":"In The Matrix, what color pill does Neo take?","correct_answer":"Red","incorrect_answers":["Blue","Green","White"]},
    {"category":"History","difficulty":"easy","question":"Who was the first President of the United States?","correct_answer":"George Washington","incorrect_answers":["Thomas Jefferson","Abraham Lincoln","John Adams"]},
]

# ---------- category map for opentdb ----------
CATEGORY_MAP = {
    "Any Category": None,
    "General Knowledge": 9,
    "Science & Nature": 17,
    "History": 23,
    "Geography": 22,
    "Entertainment: Film": 11,
    "Entertainment: Music": 12,
    "Entertainment: Video Games": 15,
    "Sports": 21,
    "Art": 25,
    "Mythology": 20,
    "Computers": 18,
    "Animals": 27,
}

DIFFICULTY_EMOJI = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}

# ---------- fetch questions ----------
def fetch_questions(amount, category, difficulty):
    """Try opentdb API first, fall back to built-in set."""
    params = {"amount": amount, "type": "multiple"}
    if category:
        params["category"] = category
    if difficulty != "any":
        params["difficulty"] = difficulty
    try:
        resp = requests.get("https://opentdb.com/api.php", params=params, timeout=6)
        data = resp.json()
        if data.get("response_code") == 0:
            questions = []
            for q in data["results"]:
                questions.append({
                    "category": html.unescape(q["category"]),
                    "difficulty": q["difficulty"],
                    "question": html.unescape(q["question"]),
                    "correct_answer": html.unescape(q["correct_answer"]),
                    "incorrect_answers": [html.unescape(a) for a in q["incorrect_answers"]],
                })
            return questions, True
    except Exception:
        pass
    # fallback
    pool = FALLBACK_QUESTIONS[:]
    if difficulty != "any":
        filtered = [q for q in pool if q["difficulty"] == difficulty]
        if filtered:
            pool = filtered
    random.shuffle(pool)
    return pool[:amount], False

# ---------- session state defaults ----------
defaults = {
    "game_active": False,
    "questions": [],
    "current_idx": 0,
    "score": 0,
    "streak": 0,
    "answered": False,
    "selected_answer": None,
    "shuffled_options": [],
    "online": True,
    "total_played": 0,
    "total_correct": 0,
    "best_streak": 0,
    "round_results": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ===================================================================
#  SETUP PHASE
# ===================================================================
if not st.session_state.game_active:
    st.markdown('<p style="font-size:2rem;font-weight:700;text-align:center;color:#ffd200;">▶️ New Round</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        category_name = st.selectbox("Category", list(CATEGORY_MAP.keys()))
    with col2:
        difficulty = st.selectbox("Difficulty", ["any", "easy", "medium", "hard"])

    num_questions = st.slider("How many questions?", 5, 20, 10)

    if st.button("🚀 Start Round", use_container_width=True, type="primary"):
        cat_id = CATEGORY_MAP[category_name]
        qs, online = fetch_questions(num_questions, cat_id, difficulty)
        if not qs:
            st.error("Couldn't load questions. Try a different category or check your connection.")
        else:
            st.session_state.questions = qs
            st.session_state.game_active = True
            st.session_state.current_idx = 0
            st.session_state.score = 0
            st.session_state.streak = 0
            st.session_state.answered = False
            st.session_state.selected_answer = None
            st.session_state.online = online
            st.session_state.round_results = []
            # pre-shuffle first question
            q = qs[0]
            opts = q["incorrect_answers"] + [q["correct_answer"]]
            random.shuffle(opts)
            st.session_state.shuffled_options = opts
            st.rerun()

# ===================================================================
#  GAME PHASE
# ===================================================================
elif st.session_state.game_active and st.session_state.current_idx < len(st.session_state.questions):
    q = st.session_state.questions[st.session_state.current_idx]
    total = len(st.session_state.questions)
    idx = st.session_state.current_idx

    # source badge
    source = "🌐 Live" if st.session_state.online else "💾 Offline"
    st.caption(source)

    # progress bar
    st.progress((idx) / total)

    # score bar
    st.markdown(f"""
    <div class="score-bar">
        <div class="score-item"><div class="val">{idx+1}/{total}</div><div class="lbl">Question</div></div>
        <div class="score-item"><div class="val">{st.session_state.score}</div><div class="lbl">Score</div></div>
        <div class="score-item"><div class="val">🔥 {st.session_state.streak}</div><div class="lbl">Streak</div></div>
    </div>
    """, unsafe_allow_html=True)

    # question
    diff_em = DIFFICULTY_EMOJI.get(q["difficulty"], "⚪")
    st.markdown(f'<p class="q-header">{q["category"]} · {diff_em} {q["difficulty"].title()}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="q-text">{q["question"]}</p>', unsafe_allow_html=True)

    options = st.session_state.shuffled_options

    if not st.session_state.answered:
        # show answer buttons
        cols = st.columns(2)
        for i, opt in enumerate(options):
            with cols[i % 2]:
                if st.button(opt, key=f"opt_{idx}_{i}", use_container_width=True):
                    st.session_state.selected_answer = opt
                    st.session_state.answered = True
                    correct = (opt == q["correct_answer"])
                    st.session_state.round_results.append(correct)
                    st.session_state.total_played += 1
                    if correct:
                        st.session_state.score += 1
                        st.session_state.streak += 1
                        st.session_state.total_correct += 1
                        if st.session_state.streak > st.session_state.best_streak:
                            st.session_state.best_streak = st.session_state.streak
                    else:
                        st.session_state.streak = 0
                    st.rerun()
    else:
        # show feedback
        selected = st.session_state.selected_answer
        correct_ans = q["correct_answer"]
        if selected == correct_ans:
            st.markdown(f'<div class="feedback-correct">✅ Correct! Nice one.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="feedback-wrong">❌ Wrong — the answer was <b>{correct_ans}</b></div>', unsafe_allow_html=True)

        # show options with color coding
        cols = st.columns(2)
        for i, opt in enumerate(options):
            with cols[i % 2]:
                if opt == correct_ans:
                    st.success(f"✅ {opt}")
                elif opt == selected and opt != correct_ans:
                    st.error(f"❌ {opt}")
                else:
                    st.button(opt, key=f"dis_{idx}_{i}", disabled=True, use_container_width=True)

        # next button
        st.markdown("")
        if st.button("➡️ Next Question" if idx + 1 < total else "🏁 See Results", use_container_width=True, type="primary"):
            next_idx = st.session_state.current_idx + 1
            st.session_state.current_idx = next_idx
            st.session_state.answered = False
            st.session_state.selected_answer = None
            if next_idx < total:
                nq = st.session_state.questions[next_idx]
                opts = nq["incorrect_answers"] + [nq["correct_answer"]]
                random.shuffle(opts)
                st.session_state.shuffled_options = opts
            st.rerun()

# ===================================================================
#  RESULTS PHASE
# ===================================================================
else:
    total = len(st.session_state.questions)
    score = st.session_state.score
    pct = round(score / total * 100) if total else 0

    # choose a reaction
    if pct == 100:
        reaction = "🏆 PERFECT SCORE!"
        color = "#2ecc71"
    elif pct >= 80:
        reaction = "🔥 Impressive!"
        color = "#f39c12"
    elif pct >= 50:
        reaction = "👍 Not bad!"
        color = "#3498db"
    else:
        reaction = "💪 Keep practicing!"
        color = "#e74c3c"

    st.markdown(f"""
    <div style="text-align:center;padding:2rem 0;">
        <p style="font-size:3rem;margin-bottom:0;">{reaction}</p>
        <p style="font-size:5rem;font-weight:800;color:{color};margin:0.2rem 0;">{score}/{total}</p>
        <p style="font-size:1.2rem;color:#b8b8d0;">{pct}% accuracy · Best streak this session: 🔥 {st.session_state.best_streak}</p>
    </div>
    """, unsafe_allow_html=True)

    # show question recap
    with st.expander("📋 Round Recap", expanded=False):
        for i, q in enumerate(st.session_state.questions):
            result = st.session_state.round_results[i] if i < len(st.session_state.round_results) else False
            icon = "✅" if result else "❌"
            st.markdown(f"**{icon} Q{i+1}:** {q['question']}  \n*Answer: {q['correct_answer']}*")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Play Again", use_container_width=True, type="primary"):
            st.session_state.game_active = False
            st.session_state.questions = []
            st.session_state.current_idx = 0
            st.session_state.answered = False
            st.rerun()
    with col2:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.game_active = False
            st.switch_page("🏠_Home.py")
