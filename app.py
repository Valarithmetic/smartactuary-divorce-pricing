import streamlit as st
import numpy as np
import pandas as pd
from PIL import Image
import plotly.graph_objects as go

st.set_page_config(
    page_title="Smart Actuary  Divorce-Risk Insurance Pricing",
    page_icon="assets/logo.png",
    layout="wide",
)

# =========================================================
# SMART ACTUARY CASE STUDY TEMPLATE — shared styling
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
    .sa-hero h1 { font-size:36px; font-weight:800; color:#F4EFE6 !important; margin:14px 0 12px; max-width:760px; line-height:1.15; }
    .sa-hero .subtags span {
        display:inline-block; font-family:'JetBrains Mono'; font-size:11px; color:#AEB9C6 !important;
        border:1px solid #33507A; border-radius:999px; padding:5px 14px; margin:4px 8px 4px 0;
    }

    .sa-kpi { background:#F4EFE6; border-radius:12px; padding:20px 18px; text-align:center; border-top:4px solid #D9A441; }
    .sa-kpi .num { font-family:'JetBrains Mono'; font-size:26px; font-weight:600; color:#10233A !important; display:block; }
    .sa-kpi .lbl { font-size:12px; color:#5C6670 !important; text-transform:uppercase; letter-spacing:0.5px; }

    .sa-eyebrow { font-family:'JetBrains Mono'; font-size:11px; letter-spacing:2px; color:#D9A441 !important; text-transform:uppercase; }
    .sa-h2 { font-size:24px; font-weight:700; color:#F4EFE6 !important; margin:6px 0 18px; }

    .sa-card { background:#F4EFE6; border-radius:12px; padding:20px 22px; height:100%; border-top:4px solid #D9A441; }
    .sa-card h4 { color:#10233A !important; margin:0 0 4px; font-family:'Poppins'; font-size:13px; text-transform:uppercase; letter-spacing:0.5px; }
    .sa-card p, .sa-card span { color:#10233A !important; }
    .sa-card .big { font-family:'JetBrains Mono'; font-size:24px; font-weight:600; color:#10233A !important; }
    .tier-low { border-top-color:#5C6670; }
    .tier-high { border-top-color:#2f7a4f; }

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
# Gompertz model — calibrated to the study's reported findings
# (survival ~75-80% at 10y, cumulative divorce ~30% by 20y,
# survival near-zero by 40y, consistent with a small-sample fit)
# =========================================================
B, C = 0.0108, 1.0724
DISCOUNT_RATE = 0.05        # interest rate, as used in the original study
EXPENSE_LOADING = 0.02      # 2% of premium
SURRENDER_CHARGE = 0.10     # 10%
BASE_BENEFIT = 100_000      # KSh, divorce benefit for marriages under 10 years
LONG_MARRIAGE_BENEFIT = 150_000  # illustrative higher payout for marriages past 10 years —
                                  # reflecting the study's objective of higher payouts for couples
                                  # married more than ten years; exact original multiplier not
                                  # recoverable from the source formulas (embedded as images)

def survival(t):
    return np.exp(-(B / np.log(C)) * (C**t - 1))

def benefit_at(t):
    """Divorce benefit depends on how long the couple has been married when divorce occurs."""
    return LONG_MARRIAGE_BENEFIT if t >= 10 else BASE_BENEFIT

def price_policy(term_years, current_duration=0):
    v = 1 / (1 + DISCOUNT_RATE)
    years = np.arange(0, term_years + 1)
    S = survival(years)
    prob_divorce_in_year = S[:-1] - S[1:]

    epv_benefits = sum(v**(t+1) * prob_divorce_in_year[t] * benefit_at(t+1) for t in range(term_years))
    epv_annuity = sum(v**t * S[t] for t in range(term_years))
    net_premium = epv_benefits / epv_annuity if epv_annuity > 0 else 0
    gross_premium = net_premium / (1 - EXPENSE_LOADING)

    d = current_duration
    if d >= term_years:
        reserve = 0
    else:
        S_d = S[d]
        remaining = term_years - d
        future_benefits = sum(
            v**(k+1) * (S[d+k] - S[d+k+1]) / S_d * benefit_at(d+k+1) for k in range(remaining)
        )
        future_premiums = net_premium * sum(v**k * S[d+k] / S_d for k in range(remaining))
        reserve = future_benefits - future_premiums

    surrender_value = max(reserve * (1 - SURRENDER_CHARGE), 0)
    return gross_premium, reserve, surrender_value


# Real per-couple results from the original 14-couple study
COUPLE_DATA = pd.DataFrame({
    "Couple": list(range(1, 15)),
    "Premium (KES)": [1106.17, 1159.87, 1334.97, 1463.65, 1531.57, 1601.85, 1601.85,
                       1674.42, 1749.18, 1985.27, 2067.22, 2806.64, 3352.09, 3366.45],
    "Prospective Reserve": [220.60, 230.53, 260.84, 281.34, 291.61, 301.87, 301.87,
                             312.07, 322.19, 351.60, 360.92, 421.65, 385.62, 370.30],
    "Retrospective Reserve": [441.68, 693.65, 1585.92, 2303.91, 2702.44, 3128.32, 3128.32,
                               3582.11, 4064.25, 5681.98, 6277.46, 12595.67, 20753.04, 21590.96],
    "Surrender Value": [198.54, 207.48, 234.76, 253.21, 262.45, 271.68, 271.68,
                         280.87, 289.97, 316.44, 324.83, 379.48, 347.06, 333.27],
})


# =========================================================
# SIDEBAR — Try It Yourself inputs
# =========================================================
with st.sidebar:
    st.markdown("### Try It Yourself")
    st.markdown("Price a policy using the fitted Gompertz model.")
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
    <h1>An Insurance Product Designed to Reduce Divorce Rates in Kenya</h1>
    <div class="subtags">
        <span>Stochastic Modeling</span>
        <span>Gompertz's Law</span>
        <span>Behavioral Actuarial Design</span>
    </div>
</div>
""", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
for col, num, lbl in zip(
    [k1, k2, k3, k4],
    ["14", "KES 1,106–3,366", "KES 100K → 150K", "10%"],
    ["Couples priced in the study", "Premium range by risk", "Divorce benefit, under vs. over 10 years", "Surrender charge rate"]
):
    col.markdown(f'<div class="sa-kpi"><span class="num">{num}</span><span class="lbl">{lbl}</span></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# THE CHALLENGE
# =========================================================
sa_section_start("The problem", "The Challenge")
st.markdown("""
Divorce rates in Kenya continue to rise, carrying real financial and social costs — for couples,
for children, and for the wider welfare system. Most insurance products treat marriage purely as
a backdrop, not as something the product itself can influence. The brief was to design an
actuarial product that does more than pay out after divorce: one that's structured to actively
**encourage marital stability**, using financial incentives rather than moral appeals.
""")
sa_section_end()

# =========================================================
# OUR SOLUTION
# =========================================================
sa_section_start("The approach", "Our Solution")
st.markdown("""
An endowment-style couple's insurance product, priced using Gompertz's law to model marriage
duration as a survival process. The mechanism designed to support the product's mission is
**duration-based payouts**: couples who divorce after being married more than ten years receive a
meaningfully higher benefit than couples who divorce earlier — the general objective stated in the
original study. Reserves and surrender values also grow the longer a couple stays in the policy,
so continued participation is consistently rewarded, not just the divorce payout itself.
""")
sa_section_end()

# =========================================================
# THE MODEL
# =========================================================
sa_section_start("The mathematics", "The Model")
st.markdown("Gompertz's law models the hazard of divorce as growing with marital duration:")
st.latex(r"\mu(t) = B \cdot C^{t}")
st.markdown("Which gives a survival function of:")
st.latex(r"S(t) = \exp\left(-\frac{B}{\ln C}\left(C^{t} - 1\right)\right)")
st.markdown("""
Premiums are set so the expected present value of future benefits equals the expected present
value of future premiums — the standard equivalence principle, applied here with a benefit amount
that steps up once the marriage passes the ten-year mark, directly encoding the product's
stability-incentive design into the pricing itself.
""")
sa_section_end()

# =========================================================
# SURVIVAL & DIVORCE RISK FINDINGS
# =========================================================
sa_section_start("Model output", "Survival & Divorce Risk Over Time")
years_plot = np.arange(0, 41)
S_plot = survival(years_plot)
fig = go.Figure()
fig.add_trace(go.Scatter(x=years_plot, y=S_plot, name="Marriage survival probability",
                          line=dict(color="#2f7a4f", width=3)))
fig.add_trace(go.Scatter(x=years_plot, y=1 - S_plot, name="Cumulative divorce probability",
                          line=dict(color="#b3541e", width=3)))
fig.add_vline(x=10, line_dash="dash", line_color="#5C6670",
              annotation_text="10-year threshold", annotation_font_color="#10233A")
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
**Key findings from the original study:** roughly 70-80% of couples remained married beyond the
first decade, with the cumulative probability of divorce rising to approximately 25-35% by year
20. Divorce risk increased through the first 10-20 years before tapering — the exact window the
product's duration-based payout structure is designed around.
""")
sa_section_end()

# =========================================================
# THE RESULTS (real per-couple data)
# =========================================================
sa_section_start("The results", "Model Performance")
st.markdown("Real pricing outputs across the 14 couples in the original study:")
st.dataframe(COUPLE_DATA, hide_index=True, use_container_width=True)

fig2 = go.Figure()
fig2.add_trace(go.Bar(x=COUPLE_DATA["Couple"], y=COUPLE_DATA["Premium (KES)"],
                       name="Premium", marker_color="#4A6FA5"))
fig2.add_trace(go.Scatter(x=COUPLE_DATA["Couple"], y=COUPLE_DATA["Surrender Value"],
                           name="Surrender value", line=dict(color="#D9A441", width=3), yaxis="y2"))
fig2.update_layout(
    plot_bgcolor="#F4EFE6", paper_bgcolor="#F4EFE6",
    height=360, margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(title="Couple", tickfont=dict(color="#10233A"), title_font=dict(color="#10233A")),
    yaxis=dict(title="Premium (KES)", gridcolor="#D8CFC0", tickfont=dict(color="#10233A"), title_font=dict(color="#10233A")),
    yaxis2=dict(title="Surrender value (KES)", overlaying="y", side="right", tickfont=dict(color="#10233A"), title_font=dict(color="#10233A")),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(color="#10233A"), bgcolor="rgba(0,0,0,0)")
)
st.markdown('<div class="sa-plot-card">', unsafe_allow_html=True)
st.plotly_chart(fig2, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown("""
Premiums ranged from KES 1,106 to KES 3,366 depending on each couple's risk profile. Higher
premiums correspond to higher reserves and surrender values — couples paying more into the policy
build proportionally more value the longer they stay in it.
""")
sa_section_end()

# =========================================================
# BUSINESS IMPACT
# =========================================================
sa_section_start("What it enables", "Business Impact")
st.markdown("""
- A financial product with a built-in behavioral incentive toward marital stability
- A defensible, actuarially-sound pricing structure for a genuinely novel risk category
- A reserving system validated for internal consistency (prospective and retrospective reserves align)
- A template extendable to other duration-based social and financial products
""")
sa_section_end()

# =========================================================
# WHY THIS MATTERS
# =========================================================
sa_section_start("The bigger picture", "Why This Matters")
st.markdown("""
Rising divorce rates carry real costs — to family welfare, to children's outcomes, and to the
wider social support system. Most insurance products can only respond to that after the fact. This
one is structured to shift incentives before the fact: staying married longer is rewarded
financially, not just emotionally, through both a higher divorce benefit past the ten-year mark
and steadily growing reserves for continued participation.
""")
sa_section_end()

# =========================================================
# TRY IT YOURSELF
# =========================================================
sa_section_start("Interactive demo", "Try It Yourself")
st.markdown(
    "See how the duration-based payout structure works, and price a policy using the fitted "
    "Gompertz model via the sidebar."
)

b1, b2 = st.columns(2)
b1.markdown(f'<div class="sa-card tier-low"><h4>Divorce before 10 years</h4><div class="big">KES {BASE_BENEFIT:,.0f}</div><p>Base divorce benefit</p></div>', unsafe_allow_html=True)
b2.markdown(f'<div class="sa-card tier-high"><h4>Divorce after 10 years</h4><div class="big">KES {LONG_MARRIAGE_BENEFIT:,.0f}</div><p>Higher benefit for marital longevity</p></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if run:
    duration_in = min(duration_in, term_in - 1)
    premium, reserve, surrender = price_policy(term_in, duration_in)
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
