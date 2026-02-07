import streamlit as st

st.set_page_config(
    page_title="News Trivia Aggregator",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------- custom CSS ----------
st.markdown("""
<style>
    /* overall vibe */
    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    }
    section[data-testid="stSidebar"] {
        background: rgba(15, 12, 41, 0.95);
    }
    .hero-title {
        font-size: 3.2rem;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(90deg, #f7971e, #ffd200);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .hero-sub {
        text-align: center;
        color: #b8b8d0;
        font-size: 1.15rem;
        margin-top: 0.2rem;
        margin-bottom: 2rem;
    }
    .card {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 1.2rem;
        transition: transform 0.2s;
    }
    .card:hover {
        transform: translateY(-3px);
        border-color: rgba(247,151,30,0.4);
    }
    .card h3 {
        color: #ffd200;
        margin-top: 0;
    }
    .card p {
        color: #ccc;
    }
    .stat-row {
        display: flex;
        gap: 1rem;
        justify-content: center;
        flex-wrap: wrap;
        margin: 1.5rem 0;
    }
    .stat-box {
        background: rgba(255,255,255,0.07);
        border-radius: 12px;
        padding: 1rem 1.8rem;
        text-align: center;
        min-width: 130px;
    }
    .stat-box .num {
        font-size: 2rem;
        font-weight: 700;
        color: #ffd200;
    }
    .stat-box .label {
        font-size: 0.85rem;
        color: #999;
    }
</style>
""", unsafe_allow_html=True)

# ---------- session state defaults ----------
if "total_played" not in st.session_state:
    st.session_state.total_played = 0
if "total_correct" not in st.session_state:
    st.session_state.total_correct = 0
if "best_streak" not in st.session_state:
    st.session_state.best_streak = 0

# ---------- hero ----------
st.markdown('<p class="hero-title">News Trivia Aggregator</p>', unsafe_allow_html=True)
st.markdown('<p class="hero-sub">Test what you know against what actually happened.</p>', unsafe_allow_html=True)

# ---------- lifetime stats ----------
played = st.session_state.total_played
correct = st.session_state.total_correct
accuracy = round(correct / played * 100) if played else 0
streak = st.session_state.best_streak

st.markdown(f"""
<div class="stat-row">
    <div class="stat-box"><div class="num">{played}</div><div class="label">Questions Faced</div></div>
    <div class="stat-box"><div class="num">{correct}</div><div class="label">Correct</div></div>
    <div class="stat-box"><div class="num">{accuracy}%</div><div class="label">Accuracy</div></div>
    <div class="stat-box"><div class="num">🔥 {streak}</div><div class="label">Best Streak</div></div>
</div>
""", unsafe_allow_html=True)

# ---------- info cards ----------
st.markdown("""
<div class="card">
    <h3>🎮 Quick Play</h3>
    <p>Jump into a round of trivia — pick your category, difficulty, and number of questions.
    Head to <b>▶️ Play</b> in the sidebar to start!</p>
</div>
<div class="card">
    <h3>🌍 Diplomacy Quiz</h3>
    <p>539+ questions on global diplomacy — UN votes, NATO, BRICS, sanctions, espionage,
    and the ways different institutions describe the same events in different words.
    Pick <b>Normal</b> or <b>Hard</b> mode under <b>🌍 Diplomacy</b>.</p>
</div>
<div class="card">
    <h3>📡 Sources & Method</h3>
    <p>General trivia is fetched live from Open Trivia DB. Diplomatic questions are drawn
    from UN records, NATO communiqués, State Department cables, Reuters, BBC, Al Jazeera,
    and other primary sources — then cross-referenced for factual accuracy.</p>
</div>
<div class="card">
    <h3>📊 Track Your Progress</h3>
    <p>Accuracy, streaks, and category breakdowns update in real-time across both modes.</p>
</div>
""", unsafe_allow_html=True)

# ---------- philosophical note ----------
st.markdown("""
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px; padding: 1.8rem; margin-top: 1rem;">
    <p style="color: #b8b8d0; font-size: 0.95rem; line-height: 1.75; margin: 0;">
        The premise of this project is simple: events happen, and then institutions describe them.
        Governments, international bodies, news agencies, and NGOs all report on the same
        incident — yet the language, emphasis, and framing can differ so widely that you'd
        think they were talking about different realities. Sometimes the most unlikely sources
        agree on the raw facts while those you'd expect to align diverge completely.
        <br><br>
        This is an attempt to get closer to what actually occurred by stripping away the
        editorializing and asking: <i>what do the primary documents say? What did the
        resolution actually state? Who voted which way, and what did they say on the record?</i>
        The hope is that trivia — of all things — can be a method for cutting through noise.
        Not by telling you what to think, but by testing whether you know what happened
        before the interpretations took over.
    </p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.caption("Questions from [opentdb.com](https://opentdb.com) & primary diplomatic sources")
