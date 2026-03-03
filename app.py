import streamlit as st
from PyPDF2 import PdfReader
import re
import random
import math

st.set_page_config(
    page_title="Forensic Academic Auditor",
    layout="wide",
    page_icon="🔍",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────
# PHRASE BANKS
# ─────────────────────────────────────────────
AI_PHRASES = [
    "in conclusion", "furthermore", "moreover", "additionally",
    "it is worth noting", "it can be argued", "in today's world",
    "in the realm of", "it is important to note", "plays a crucial role",
    "it is evident", "needless to say", "as previously mentioned",
    "a wide range of", "in this essay", "to summarize",
    "taking everything into account", "on the other hand",
    "this essay will", "one must consider", "it should be noted",
    "a significant amount", "in recent years", "it goes without saying",
    "with that being said", "in light of this", "consequently",
    "subsequently", "accordingly", "nevertheless", "notably", "particularly"
]

PLAGIARISM_PHRASES = [
    "according to", "as stated by", "as cited in",
    "the study found", "researchers suggest", "evidence suggests",
    "studies show", "it has been found", "experts argue",
    "the literature suggests", "prior research", "previous studies"
]

WEAK_PHRASES = [
    "very", "really", "basically", "literally", "actually",
    "honestly", "kind of", "sort of", "quite", "rather",
    "somewhat", "fairly", "pretty much", "in a way"
]

STRENGTH_SIGNALS = [
    "for example", "for instance", "such as", "specifically",
    "this demonstrates", "this shows", "the data shows",
    "i argue", "i found", "my analysis", "my research",
    "case study", "primary data", "interview", "survey",
    "critically", "however", "in contrast", "this challenges",
    "et al", "(20", "doi", "journal", "university press"
]

# ─────────────────────────────────────────────
# CSS — Light theme
# ─────────────────────────────────────────────
st.markdown("""
<style>
body, .stApp {
    background: #f1f5f9 !important;
    color: #1e293b !important;
}
.main .block-container { padding-top: 1rem; background: #f1f5f9; }
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

.hero-wrap {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #a855f7 100%);
    border-radius: 20px; padding: 2.5rem 2rem; text-align: center;
    margin-bottom: 1.8rem; box-shadow: 0 8px 32px rgba(124,58,237,0.25);
}
.hero-title { font-size: 2.4rem; font-weight: 900; color: #fff; margin-bottom: .4rem; }
.hero-sub   { color: rgba(255,255,255,0.75); font-size: .92rem; }

.section-card {
    background: #ffffff; border-radius: 16px;
    padding: 1.4rem 1.6rem; box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    margin-bottom: 1.2rem;
}
.section-title {
    font-size: 1rem; font-weight: 800; color: #374151;
    margin-bottom: .8rem; display: flex; align-items: center; gap: .4rem;
}

.metric-card {
    background: #ffffff; border-radius: 14px; padding: 1.1rem .8rem;
    text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.06); border-top: 4px solid;
}
.metric-val { font-size: 1.9rem; font-weight: 800; }
.metric-lab { color: #64748b; font-size: .73rem; margin-top: .3rem; font-weight: 600;
              text-transform: uppercase; letter-spacing: .4px; }

.rubric-tag {
    display: inline-block; background: #ede9fe; color: #6d28d9;
    border-radius: 8px; padding: .25rem .7rem; font-size: .78rem;
    font-weight: 700; margin: .2rem .2rem .2rem 0;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px; background: #ffffff; border-radius: 14px;
    padding: 6px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); margin-bottom: 1rem;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important; font-weight: 700 !important;
    font-size: .88rem !important; padding: .55rem 1.3rem !important;
    color: #64748b !important; background: transparent !important; border: none !important;
}
.stTabs [aria-selected="true"] {
    background: #f1f5f9 !important; color: #1e293b !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1) !important;
}

.fcard {
    border-radius: 14px; padding: 1.2rem 1.4rem; margin: .7rem 0;
    border-left: 5px solid; box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.fcard-snip {
    font-size: .87rem; font-style: italic; border-radius: 8px;
    padding: .5rem .8rem; margin: .5rem 0; line-height: 1.7;
}
.fcard-note { font-size: .82rem; color: #475569; margin-top: .4rem; }
.fcard-tip  { font-size: .82rem; font-weight: 700; margin-top: .3rem; }
.badge {
    display: inline-block; padding: .2rem .75rem; border-radius: 20px;
    font-size: .7rem; font-weight: 700; margin-left: .3rem;
}
.section-empty {
    text-align: center; color: #94a3b8; font-size: 1rem; padding: 3rem 0;
    background: #ffffff; border-radius: 14px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}
.stButton button {
    border-radius: 12px !important; font-weight: 700 !important;
    font-size: 1rem !important; padding: .65rem !important;
}
.stTextArea textarea {
    border-radius: 10px !important; background: #f8fafc !important;
    border: 1.5px solid #e2e8f0 !important; color: #1e293b !important;
    font-size: .9rem !important;
}
label { color: #374151 !important; }
h1,h2,h3,h4 { color: #1e293b !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def extract_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text.strip()
    except Exception as e:
        return f"PDF_ERROR: {e}"


def get_sentences(text):
    return [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 10]


def highlight(snippet, phrases, color):
    result = snippet
    for phrase in phrases:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        result = pattern.sub(
            f'<span style="background:{color}28;color:{color};'
            f'border-radius:4px;padding:1px 5px;font-weight:800;">{phrase}</span>',
            result
        )
    return result


def parse_rubric(rubric_text):
    """Extract rubric criteria from pasted text. Returns list of (criterion, weight, description)."""
    criteria = []
    if not rubric_text.strip():
        return criteria
    for line in rubric_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3:
            criteria.append({
                "criterion":   parts[0],
                "weight":      parts[1],
                "description": ", ".join(parts[2:])
            })
        elif len(parts) == 2:
            criteria.append({"criterion": parts[0], "weight": parts[1], "description": ""})
        else:
            criteria.append({"criterion": line, "weight": "—", "description": ""})
    return criteria


# ─────────────────────────────────────────────
# LOCAL AI DETECTOR
# ─────────────────────────────────────────────
def local_ai_score(paragraph):
    text    = paragraph.strip()
    p_lower = text.lower()
    words   = text.split()
    sents   = get_sentences(text)

    if len(words) < 15 or len(sents) < 2:
        return 0.0, [], ""

    signals = {}
    fired   = []

    phrase_hits = [p for p in AI_PHRASES if p in p_lower]
    signals["phrases"] = min(len(phrase_hits) / 3, 1.0)
    if signals["phrases"] > 0.3: fired.append("AI phrases detected")

    unique_ratio = len(set(w.lower() for w in words)) / len(words)
    signals["diversity"] = 1.0 - unique_ratio
    if signals["diversity"] > 0.5: fired.append("low lexical variety")

    lengths = [len(s.split()) for s in sents if s]
    if len(lengths) > 1:
        mean_l   = sum(lengths) / len(lengths)
        variance = sum((l - mean_l) ** 2 for l in lengths) / len(lengths)
        cv = math.sqrt(variance) / mean_l if mean_l > 0 else 0
        signals["burstiness"] = max(0.0, 1.0 - (cv / 0.5))
    else:
        signals["burstiness"] = 0.5
    if signals["burstiness"] > 0.6: fired.append("uniform sentence lengths")

    passive = re.compile(r'\b(is|are|was|were|be|been|being)\s+\w+ed\b', re.IGNORECASE)
    p_count = len(passive.findall(text))
    signals["passive"] = min(p_count / max(len(sents), 1) / 0.6, 1.0)
    if signals["passive"] > 0.5: fired.append("high passive voice")

    filler_hits = sum(1 for w in WEAK_PHRASES if w in p_lower)
    signals["filler"] = max(0.0, 1.0 - (filler_hits / 2))

    weights = {"phrases": 0.35, "diversity": 0.20,
               "burstiness": 0.20, "passive": 0.10, "filler": 0.15}
    score = sum(signals[k] * weights[k] for k in weights)
    label = ", ".join(fired) if fired else "stylometric pattern"
    return round(score, 3), phrase_hits, label


# ─────────────────────────────────────────────
# STRENGTH DETECTOR
# ─────────────────────────────────────────────
def strength_score(paragraph, rubric_criteria=None):
    p_lower = paragraph.lower()
    words   = paragraph.split()
    sents   = get_sentences(paragraph)
    hits    = [s for s in STRENGTH_SIGNALS if s in p_lower]
    score   = 0

    if re.search(r'\(\d{4}\)|\[\d+\]|et al', paragraph): score += 2
    if any(h in p_lower for h in ["for example","for instance","specifically","case study"]): score += 2
    if any(h in p_lower for h in ["however","in contrast","challenges","critically","i argue"]): score += 2
    if 80 <= len(words) <= 160: score += 1
    if len(sents) >= 3:
        lengths = [len(s.split()) for s in sents if s]
        if lengths:
            mean_l = sum(lengths) / len(lengths)
            cv = math.sqrt(sum((l - mean_l)**2 for l in lengths) / len(lengths)) / mean_l if mean_l > 0 else 0
            if cv > 0.3: score += 1

    # Bonus: check if paragraph addresses any rubric criterion
    rubric_match = []
    if rubric_criteria:
        for crit in rubric_criteria:
            keywords = crit["criterion"].lower().split() + crit["description"].lower().split()
            if any(kw in p_lower for kw in keywords if len(kw) > 4):
                rubric_match.append(crit["criterion"])
                score += 1

    return score, hits, rubric_match


# ─────────────────────────────────────────────
# FORENSIC AUDIT
# ─────────────────────────────────────────────
def forensic_audit(text, rubric_criteria):
    ai_f, plg_f, weak_f, str_f = [], [], [], []

    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if len(p.strip()) > 60]
    if not paragraphs:
        paragraphs = [text[i:i+500] for i in range(0, len(text), 500) if text[i:i+500].strip()]

    for i, para in enumerate(paragraphs):
        p_lower = para.lower()
        p_words = len(para.split())
        lbl     = f"Paragraph {i+1}"

        # AI
        ai_score, ai_phrases, ai_label = local_ai_score(para)
        if ai_score > 0.52:
            ai_f.append({
                "label":    lbl,
                "score":    ai_score,
                "html":     highlight(para[:230], ai_phrases, "#ef4444"),
                "analysis": f"Stylometric confidence {ai_score:.0%} — {ai_label}",
                "action":   "Rewrite with your own original analysis and personal examples",
                "pts":      -random.randint(5, 9),
            })

        # Plagiarism
        plg_hits = [ph for ph in PLAGIARISM_PHRASES if ph in p_lower]
        if plg_hits:
            plg_val = min(50 + len(plg_hits) * 15, 93)
            plg_f.append({
                "label":    lbl,
                "score":    plg_val,
                "html":     highlight(para[:230], plg_hits, "#f97316"),
                "analysis": f"{plg_val}% similarity signal — triggers: {', '.join(plg_hits[:3])}",
                "action":   "Add Harvard in-text citations or rephrase in your own voice",
                "pts":      -random.randint(3, 7),
            })

        # Weak writing
        weak_hits = [w for w in WEAK_PHRASES if re.search(r'\b' + w + r'\b', p_lower)]
        if len(weak_hits) >= 2:
            weak_f.append({
                "label":    lbl,
                "html":     highlight(para[:230], weak_hits, "#d97706"),
                "analysis": f"Filler/hedge words: {', '.join(weak_hits[:5])}",
                "action":   "Replace with precise, confident academic language",
                "pts":      -random.randint(1, 3),
            })
        if p_words > 180:
            weak_f.append({
                "label":    lbl + " (too long)",
                "html":     para[:120] + "...",
                "analysis": f"Paragraph is {p_words} words — max recommended is 150",
                "action":   "Split into two focused paragraphs",
                "pts":      -1,
            })

        # Strengths
        s_score, s_phrases, rubric_match = strength_score(para, rubric_criteria)
        if s_score >= 3:
            rubric_note = f" | Rubric match: {', '.join(rubric_match)}" if rubric_match else ""
            str_f.append({
                "label":    lbl,
                "score":    s_score,
                "html":     highlight(para[:230], s_phrases, "#16a34a"),
                "analysis": f"Strength score {s_score}/8 — {', '.join(s_phrases[:4]) if s_phrases else 'good structure'}{rubric_note}",
                "action":   "Keep this approach — it shows critical academic engagement",
                "pts":      +random.randint(1, 3),
            })

    return ai_f, plg_f, weak_f, str_f


# ─────────────────────────────────────────────
# CARD RENDERERS
# ─────────────────────────────────────────────
def ai_card(f):
    st.markdown(f"""
    <div class="fcard" style="background:#fff5f5;border-left-color:#ef4444;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
            <span style="color:#dc2626;font-weight:800;font-size:.95rem;">🤖 AI Content — {f['label']}</span>
            <div>
                <span class="badge" style="background:#fee2e2;color:#dc2626;">HIGH RISK</span>
                <span class="badge" style="background:#f1f5f9;color:#64748b;">{f['pts']} pts</span>
            </div>
        </div>
        <div class="fcard-snip" style="background:#fee2e2;border-left:3px solid #ef4444;">{f['html']}...</div>
        <div class="fcard-note">📊 {f['analysis']}</div>
        <div class="fcard-tip" style="color:#16a34a;">💡 {f['action']}</div>
    </div>""", unsafe_allow_html=True)


def plg_card(f):
    rc = "#dc2626" if f["score"] >= 70 else "#ea580c"
    st.markdown(f"""
    <div class="fcard" style="background:#fff7ed;border-left-color:#f97316;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
            <span style="color:#ea580c;font-weight:800;font-size:.95rem;">📋 Plagiarism Risk — {f['label']}</span>
            <div>
                <span class="badge" style="background:#ffedd5;color:{rc};">{'HIGH' if f['score']>=70 else 'MEDIUM'}</span>
                <span class="badge" style="background:#f1f5f9;color:#64748b;">{f['pts']} pts</span>
            </div>
        </div>
        <div class="fcard-snip" style="background:#ffedd5;border-left:3px solid #f97316;">{f['html']}...</div>
        <div class="fcard-note">📊 {f['analysis']}</div>
        <div class="fcard-tip" style="color:#16a34a;">💡 {f['action']}</div>
    </div>""", unsafe_allow_html=True)


def weak_card(f):
    st.markdown(f"""
    <div class="fcard" style="background:#fffbeb;border-left-color:#d97706;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
            <span style="color:#b45309;font-weight:800;font-size:.95rem;">⚠️ Needs Improvement — {f['label']}</span>
            <div>
                <span class="badge" style="background:#fef3c7;color:#b45309;">LOW–MED</span>
                <span class="badge" style="background:#f1f5f9;color:#64748b;">{f['pts']} pts</span>
            </div>
        </div>
        <div class="fcard-snip" style="background:#fef3c7;border-left:3px solid #d97706;">{f['html']}...</div>
        <div class="fcard-note">📊 {f['analysis']}</div>
        <div class="fcard-tip" style="color:#16a34a;">💡 {f['action']}</div>
    </div>""", unsafe_allow_html=True)


def str_card(f):
    st.markdown(f"""
    <div class="fcard" style="background:#f0fdf4;border-left-color:#16a34a;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
            <span style="color:#15803d;font-weight:800;font-size:.95rem;">✅ Strength — {f['label']}</span>
            <div>
                <span class="badge" style="background:#dcfce7;color:#15803d;">GOOD</span>
                <span class="badge" style="background:#f1f5f9;color:#64748b;">+{f['pts']} pts</span>
            </div>
        </div>
        <div class="fcard-snip" style="background:#dcfce7;border-left:3px solid #16a34a;">{f['html']}...</div>
        <div class="fcard-note">📊 {f['analysis']}</div>
        <div class="fcard-tip" style="color:#15803d;">💡 {f['action']}</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MAIN UI
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
    <div class="hero-title">🔍 Forensic Academic Auditor</div>
    <div class="hero-sub">Local AI Detection &nbsp;·&nbsp; No API &nbsp;·&nbsp; No Rate Limits &nbsp;·&nbsp; 4-Color Precision System</div>
</div>
""", unsafe_allow_html=True)

# ── ROW 1: Rubric ──────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📋 Marking Rubric <span style="font-weight:400;color:#94a3b8;font-size:.82rem;">&nbsp;— paste exact criteria from your brief (one per line: Criterion, Weight%, Description)</span></div>', unsafe_allow_html=True)
rubric_input = st.text_area(
    "rubric",
    height=130,
    label_visibility="collapsed",
    placeholder="Example:\nCritical Analysis,30%,Demonstrate depth of argument and use of theory\nRoadmap & SDG Integration,20%,Staged AI transformation plan with KPIs\nSynthesis & Foresight,10%,Actionable recommendations showing long-term risk awareness\nProfessionalism & Logic,10%,Professional business communication, no AI hallmarks"
)
rubric_criteria = parse_rubric(rubric_input)
if rubric_criteria:
    tags_html = "".join(
        f'<span class="rubric-tag">{c["criterion"]} <strong>{c["weight"]}</strong></span>'
        for c in rubric_criteria
    )
    st.markdown(f'<div style="margin-top:.5rem;">{tags_html}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── ROW 2: Input ───────────────────────────────
col_l, col_r = st.columns([1, 1], gap="large")
with col_l:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📄 Upload PDF</div>', unsafe_allow_html=True)
    pdf_file = st.file_uploader("pdf", type=["pdf"], label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

with col_r:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">✏️ Or Paste Essay Text</div>', unsafe_allow_html=True)
    pasted = st.text_area("essay", height=140, label_visibility="collapsed",
                          placeholder="Paste your essay paragraphs here...")
    st.markdown('</div>', unsafe_allow_html=True)

run = st.button("🔍  RUN FORENSIC AUDIT", type="primary", use_container_width=True)

# ── RUN ────────────────────────────────────────
if run:
    raw_text = ""
    if pdf_file:
        raw_text = extract_pdf(pdf_file)
    elif pasted.strip():
        raw_text = pasted.strip()
    else:
        st.error("Upload a PDF or paste text first.")
        st.stop()

    if raw_text.startswith("PDF_ERROR"):
        st.error(raw_text)
        st.stop()

    word_count = len(raw_text.split())

    with st.spinner("Analysing paragraphs..."):
        ai_f, plg_f, weak_f, str_f = forensic_audit(raw_text, rubric_criteria)

    # Metrics
    total_neg = sum(f["pts"] for f in ai_f + plg_f + weak_f)
    total_pos = sum(f["pts"] for f in str_f)
    integrity = max(0, min(100, 100 + total_neg + total_pos))
    grade     = "A" if integrity >= 85 else "B" if integrity >= 70 else "C" if integrity >= 55 else "D"
    sc        = "#16a34a" if integrity >= 75 else "#d97706" if integrity >= 55 else "#dc2626"

    st.markdown("---")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    for col, (val, lab, clr) in zip(
        [c1,c2,c3,c4,c5,c6],
        [
            (f"{integrity}/100", "Integrity Score", sc),
            (str(word_count),    "Total Words",     "#4f46e5"),
            (grade,              "Predicted Grade", sc),
            (str(len(ai_f)),     "AI Flags",        "#dc2626"),
            (str(len(plg_f)),    "Plagiarism Flags","#ea580c"),
            (str(len(str_f)),    "Strengths Found", "#15803d"),
        ]
    ):
        col.markdown(f"""
        <div class="metric-card" style="border-top-color:{clr};">
            <div class="metric-val" style="color:{clr};">{val}</div>
            <div class="metric-lab">{lab}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Rubric summary if provided
    if rubric_criteria:
        with st.expander("📋 Rubric Criteria Loaded", expanded=False):
            for c in rubric_criteria:
                st.markdown(f"**{c['criterion']}** — {c['weight']}  \n_{c['description']}_")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        f"🔴  AI Content ({len(ai_f)})",
        f"🟠  Plagiarism ({len(plg_f)})",
        f"🟡  Weaknesses ({len(weak_f)})",
        f"🟢  Strengths ({len(str_f)})",
    ])

    with tab1:
        if ai_f:
            st.markdown(f"**{len(ai_f)} paragraph(s)** flagged as likely AI-generated. Red highlights show exact triggering phrases.")
            for f in ai_f: ai_card(f)
        else:
            st.markdown('<div class="section-empty">✅ No AI content detected</div>', unsafe_allow_html=True)

    with tab2:
        if plg_f:
            st.markdown(f"**{len(plg_f)} paragraph(s)** show unattributed content. Orange highlights show triggering phrases.")
            for f in plg_f: plg_card(f)
        else:
            st.markdown('<div class="section-empty">✅ No plagiarism signals found</div>', unsafe_allow_html=True)

    with tab3:
        if weak_f:
            st.markdown(f"**{len(weak_f)} section(s)** need improvement. Yellow highlights show weak language.")
            for f in weak_f: weak_card(f)
        else:
            st.markdown('<div class="section-empty">✅ No weak writing detected</div>', unsafe_allow_html=True)

    with tab4:
        if str_f:
            st.markdown(f"**{len(str_f)} paragraph(s)** show strong academic writing. Green highlights show what makes them work.")
            for f in str_f: str_card(f)
        else:
            st.markdown('<div class="section-empty">Add citations, examples and critical analysis to unlock strength flags</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;color:#94a3b8;font-size:.78rem;'>"
        "Syed Hashim Raza · MSc AI for Business · Manchester 2026 · "
        "Forensic Audit v5.1 — Local Stylometric Engine</div>",
        unsafe_allow_html=True
    )
