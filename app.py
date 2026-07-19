import streamlit as st
import numpy as np
import pandas as pd
from PIL import Image
import plotly.graph_objects as go

st.set_page_config(
    page_title="Smart Actuary — Divorce-Risk Insurance Pricing",
    page_icon="assets/logo.png",
    layout="wide",
)

# =========================================================
# SMART ACTUARY CASE STUDY TEMPLATE — shared styling
# Same template used across all Smart Actuary case study apps.
# =========================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800&family=Inter:wght@400;500&family=JetBrains+Mono:wght@500&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #10233A; }
    section[data-testid="stSidebar"] { background-color: #0C1B2E; }
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] h3 { color: #F4EFE6 !important; }
    h1, h2, h3 { font-family: 'Poppins', sans-serif; color: #F4EFE6 !important; }
    p, span, label, li, .stMarkdown, div[data-testid="stMarkdownContainer"] p { color: #C7D0DC !important; }
    hr { border-color: #26405F !important; }
    footer {visibility: hidden;}

    .sa-hero {
        background: radial-gradient(circle at 20% 20%, #1B3352 0%, #0C1B2E 70%);
        border-radius: 18px; padding: 64px 48px 52px; margin-bottom: 8px;
        border: 1px solid #26405F;
    }
    .sa-hero h1 { font-size:38px; font-weight:800; color:#F4EFE6 !important; margin:14px 0 12px; max-width:760px; line-height:1.15; }
    .sa-hero .subtags span {
        display:inline-block; font-family:'JetBrains Mono'; font-size:11px; color:#AEB9C6 !important;
        border:1px solid #33507A; border-radius:999px; padding:5px 14px; margin:4px 8px 4px 0;
    }

    .sa-kpi { background:#F4EFE6; border-radius:12px; padding:20px 18px; text-align:center; border-top:4px solid #D9A441; }
    .sa-kpi .num { font-family:'JetBrains Mono'; font-size:28px; font-weight:600; color:#10233A !important; display:block; }
    .sa-kpi .lbl { font-size:12px; color:#5C6670 !important; text-transform:uppercase; letter-spacing:0.5px; }

    .sa-eyebrow { font-family:'JetBrains Mono'; font-size:11px; letter-spacing:2px; color:#D9A441 !important; text-transform:uppercase; }
    .sa-h2 { font-size:24px; font-weight:700; color:#F4EFE6 !important; margin:6px 0 18px; }

    .sa-card { background:#F4EFE6; border-radius:12px; padding:20px 22px; height:100%; border-top:4px solid #D9A441; }
    .sa-card h4 { color:#10233A !important; margin:0 0 4px; font-family:'Poppins'; font-size:13px; text-transform:uppercase; letter-spacing:0.5px; }
    .sa-card p, .sa-card span { color:#10233A !important; }
    .sa-card .big { font-family:'JetBrains Mono'; font-size:24px; font-weight:600; color:#10233A !important; }

    .sa-plot-card { background:#F4EFE6; border-radius:12px; padding:18px; }

    .stButton>button { background-color:#D9A441; color:#412402; font-weight:600; border-radius:8px; border:none; padding:10px 24px; width:100%; }
    .stButton>button:hover { background-color:#c4913a; color:#412402; }
</style>
""", unsafe_allow_html=True)


def sa_section_start(eyebrow, title):
    st.markdown(f'<span class="sa-eyebrow">{eyebrow}</span>', unsafe_allow_html=True)
    st.markdown(f'<div class="sa-h2">{title}</div>', unsafe_allow_html=True)


def sa_section_end():
    st.markdown("<br>", unsafe_allow_html=True)


# =========================================================
# Gompertz model — shared pricing engine
# =========================================================
B, C, DISCOUNT_RATE = 0.0008, 1.09, 0.10

def survival(t, B=B, C=C):
    return np.exp(-(B / np.log(C)) * (C**t - 1))

def price_policy(sum_assured, term_years, current_duration=0):
    v = 1 / (1 + DISCOUNT_RATE)
    years = np.arange(0, term_years + 1)
    S = survival(years)
    prob_divorce_in_year = S[:-1] - S[1:]

    epv_benefits = sum_assured * sum(v**(t+1) * prob_divorce_in_year[t] for t in range(term_years))
    epv_annuity = sum(v**t * S[t] for t in range(term_years))
    premium = epv_benefits / epv_annuity if epv_annuity > 0 else 0

    # Prospective reserve at current_duration, using conditional survival from that point
    d = current_duration
    if d >= term_years:
        reserve = 0
    else:
        S_d = S[d]
        remaining = term_years - d
        future_benefits = sum_assured * sum(
            v**(k+1) * (S[d+k] - S[d+k+1]) / S_d for k in range(remaining)
        )
        future_premiums = premium * sum(
            v**k * S[d+k] / S_d for k in range(remaining)
        )
        reserve = future_benefits - future_premiums

    surrender_value = max(reserve * 0.90, 0)  # 10% surrender charge
    return premium, reserve, surrender_value, S


# =========================================================
# SIDEBAR — Try It Yourself inputs
# =========================================================
with st.sidebar:
    st.markdown("### Try It Yourself")
    st.markdown("Price a policy using the fitted Gompertz model.")
    sum_assured_in = st.number_input("Sum assured (KES)", 50000, 2000000, 300000, step=25000)
    term_in = st.slider("Policy term (years)", 5, 30, 20)
    duration_in = st.slider("Years already married", 0, 29, 3)
    run = st.button("Calculate premium & reserve")

# =========================================================
# HERO
# =========================================================
hcol1, hcol2 = st.columns([0.09, 0.91])
with hcol1:
    st.image(Image.open("assets/logo.png"), width=64)
with hcol2:
    st.markdown('<span class="sa-eyebrow" style="padding-top:10px; display:inline-block;">Smart Actuary · Case Study</span>', unsafe_allow_html=True)

st.markdown("""
<div class="sa-hero">
    <h1>Pricing a Divorce-Risk Insurance Product with Gompertz's Law</h1>
    <div class="subtags">
        <span>Stochastic Modeling</span>
        <span>Gompertz's Law</span>
        <span>Actuarial Pricing</span>
    </div>
</div>
""", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
for col, num, lbl in zip(
    [k1, k2, k3, k4],
    ["14", "KES 1,000–3,500", "10%", "Gompertz"],
    ["Couple profiles priced", "Premium range by risk", "Surrender charge rate", "Model"]
):
    col.markdown(f'<div class="sa-kpi"><span class="num">{num}</span><span class="lbl">{lbl}</span></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# THE CHALLENGE
# =========================================================
sa_section_start("The problem", "The Challenge")
st.markdown("""
Most divorce-insurance concepts price a flat, reactive payout and don't touch the actual mechanics
of *why* marriages end. The brief was to instead treat marital duration the way an actuary treats
mortality — a survival process that can be modeled, priced, and reserved against properly, with a
full premium, reserve, and surrender value structure rather than a fixed lump sum.
""")
sa_section_end()

# =========================================================
# OUR SOLUTION
# =========================================================
sa_section_start("The approach", "Our Solution")
st.markdown("""
Adapted Gompertz's law — usually used to model human mortality — to marital duration instead,
treating "divorce" as the event a couple survives against over time. Parameters were fitted via
Maximum Likelihood Estimation, then used to derive survival probabilities, cumulative divorce
probabilities, and divorce density curves — fed directly into a full endowment-policy pricing
structure: premiums per couple's risk profile, prospective and retrospective reserves, and
surrender values.
""")
sa_section_end()

# =========================================================
# THE MODEL
# =========================================================
sa_section_start("The mathematics", "The Model")
st.markdown("Gompertz's law models the hazard of an event as growing exponentially over time:")
st.latex(r"\mu(t) = B \cdot C^{t}")
st.markdown("Which gives a survival function of:")
st.latex(r"S(t) = \exp\left(-\frac{B}{\ln C}\left(C^{t} - 1\right)\right)")
st.markdown("""
Premiums are then set so the expected present value of future benefits equals the expected present
value of future premiums — the same equivalence principle used to price any life-contingent policy,
just applied to marital survival instead of mortality.
""")
sa_section_end()

# =========================================================
# SURVIVAL CURVE (live-computed)
# =========================================================
sa_section_start("Model output", "Survival & Divorce Risk Over Time")
years_plot = np.arange(0, 31)
S_plot = survival(years_plot)
fig = go.Figure()
fig.add_trace(go.Scatter(x=years_plot, y=S_plot, name="Marriage survival probability",
                          line=dict(color="#2f7a4f", width=3)))
fig.add_trace(go.Scatter(x=years_plot, y=1 - S_plot, name="Cumulative divorce probability",
                          line=dict(color="#b3541e", width=3)))
fig.update_layout(
    plot_bgcolor="#F4EFE6", paper_bgcolor="#F4EFE6",
    height=380, margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(title="Years of marriage", gridcolor="#D8CFC0", zerolinecolor="#D8CFC0",
               tickfont=dict(color="#10233A"), title_font=dict(color="#10233A")),
    yaxis=dict(title="Probability", gridcolor="#D8CFC0", zerolinecolor="#D8CFC0",
               tickfont=dict(color="#10233A"), title_font=dict(color="#10233A")),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                font=dict(color="#10233A"), bgcolor="rgba(0,0,0,0)")
)
st.markdown('<div class="sa-plot-card">', unsafe_allow_html=True)
st.plotly_chart(fig, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown("""
Divorce risk is modeled as rising with marital duration under this fitted curve — consistent with
Gompertz's underlying assumption that hazard compounds over time rather than staying constant.
""")
sa_section_end()

# =========================================================
# MODEL PERFORMANCE
# =========================================================
sa_section_start("The results", "Model Performance")
st.markdown("""
Across the 14 couple profiles priced in the original study, premiums scaled sensibly with risk
(KES 1,000–3,500), reserves grew consistently with policy duration, and the prospective and
retrospective reserve calculations stayed internally consistent — the core check for whether an
actuarial pricing structure is sound. The recommended next step from the original study: validate
the fitted parameters against real marriage-registry data rather than simulated durations.
""")
sa_section_end()

# =========================================================
# BUSINESS IMPACT
# =========================================================
sa_section_start("What it enables", "Business Impact")
st.markdown("""
- A defensible, actuarially-sound framework for a genuinely novel insurance product
- Individualized pricing instead of a flat, reactive payout
- A reserving structure that holds up to prospective/retrospective consistency checks
- A template extendable to other duration-based risks beyond marriage
""")
sa_section_end()

# =========================================================
# WHY THIS MATTERS
# =========================================================
sa_section_start("The bigger picture", "Why This Matters")
st.markdown("""
Most novel insurance concepts stall at the idea stage because nobody works out whether they can
actually be priced soundly. This project shows that an unconventional risk — marital duration —
can be treated with the same rigor as any standard life-contingent product, using tools actuaries
already trust.
""")
sa_section_end()

# =========================================================
# TRY IT YOURSELF
# =========================================================
sa_section_start("Interactive demo", "Try It Yourself")
st.markdown(
    "Adjust the parameters in the sidebar to price a policy using the fitted Gompertz model. "
    "Parameters here are illustrative, calibrated to reflect the same relationships as the "
    "original study."
)

if run:
    duration_in = min(duration_in, term_in - 1)
    premium, reserve, surrender, _ = price_policy(sum_assured_in, term_in, duration_in)
    r1, r2, r3 = st.columns(3)
    r1.markdown(f'<div class="sa-card"><h4>Annual premium</h4><div class="big">KES {premium:,.0f}</div></div>', unsafe_allow_html=True)
    r2.markdown(f'<div class="sa-card"><h4>Reserve at duration {duration_in}</h4><div class="big">KES {reserve:,.0f}</div></div>', unsafe_allow_html=True)
    r3.markdown(f'<div class="sa-card"><h4>Surrender value</h4><div class="big">KES {surrender:,.0f}</div></div>', unsafe_allow_html=True)
else:
    st.markdown("*Set your parameters in the sidebar, then click **Calculate premium & reserve**.*")
sa_section_end()

# =========================================================
# FOOTER
# =========================================================
st.markdown("""
<div style="text-align:center; padding: 24px 0;">
<span class="sa-eyebrow">Built by Smart Actuary</span><br>
<span style="color:#C7D0DC;">Actuarial intelligence · Risk analytics · Predictive modeling</span><br><br>
<a href="https://mary-aringo-portfolio.netlify.app" style="color:#D9A441; font-weight:600;">Portfolio</a>
&nbsp;&nbsp;|&nbsp;&nbsp;
<a href="https://github.com/Valarithmetic" style="color:#D9A441; font-weight:600;">GitHub</a>
&nbsp;&nbsp;|&nbsp;&nbsp;
<a href="https://smartactuary.co.ke/#projects" style="color:#D9A441; font-weight:600;">More case studies</a>
&nbsp;&nbsp;|&nbsp;&nbsp;
<a href="https://smartactuary.co.ke/#contact" style="color:#D9A441; font-weight:600;">Contact</a>
</div>
""", unsafe_allow_html=True)
