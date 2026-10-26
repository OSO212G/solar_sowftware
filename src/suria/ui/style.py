"""Streamlit UI styles — HelioScope colour palette and compact sidebar."""

HELIOSCOPE_CSS = """
<style>
/* Hide Streamlit chrome */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display: none !important;}

/* Reduce padding globally */
.block-container {
    padding-top: 0rem !important;
    padding-bottom: 0rem !important;
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
    max-width: 100% !important;
}

/* Sidebar - exact 300px inner container */
section[data-testid="stSidebar"] > div:first-child {
    width: 300px !important;
    min-width: 300px !important;
    max-width: 300px !important;
    flex: none !important;
}
[data-testid="stSidebarResizer"] {
    display: none !important;
}

/* Sidebar theme */
section[data-testid="stSidebar"] {
    background-color: #e9ecef !important;
    color: #333 !important;
    border-right: 1px solid #d0d0d0 !important;
}
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label {
    color: #333 !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background-color: #fff !important;
    color: #333 !important;
    border: 1px solid #ccc !important;
    border-radius: 4px !important;
    font-size: 12px !important;
    padding: 4px 8px !important;
    min-height: 28px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #f0f0f0 !important;
    border-color: #bbb !important;
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background-color: #f1c40f !important;
    color: #1a1a2e !important;
    border: none !important;
    font-weight: 600 !important;
}

/* Yellow primary buttons */
.stButton > button[kind="primary"] {
    background-color: #f1c40f !important;
    color: #1a1a2e !important;
    border: none !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background-color: #d4ac0d !important;
}

/* Secondary buttons */
.stButton > button[kind="secondary"] {
    background-color: #6c757d !important;
    color: white !important;
    border: none !important;
}

/* Compact metric display inside sidebar */
section[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: #fff !important;
    padding: 6px !important;
    border-radius: 4px !important;
    border: 1px solid #ddd !important;
}
section[data-testid="stSidebar"] [data-testid="stMetric"] label {
    color: #666 !important;
    font-size: 11px !important;
}
section[data-testid="stSidebar"] [data-testid="stMetric"] div {
    color: #333 !important;
    font-size: 13px !important;
}

/* Section headers inside sidebar */
.heliosection {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #666 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    margin-top: 12px !important;
    margin-bottom: 6px !important;
    border-bottom: 1px solid #ddd !important;
    padding-bottom: 4px !important;
}

/* Compact number inputs in sidebar */
section[data-testid="stSidebar"] .stNumberInput input {
    font-size: 12px !important;
    padding: 4px 6px !important;
    min-height: 28px !important;
}
section[data-testid="stSidebar"] .stTextInput input {
    font-size: 12px !important;
    padding: 4px 6px !important;
    min-height: 28px !important;
}
section[data-testid="stSidebar"] .stSelectbox > div > div {
    font-size: 12px !important;
    min-height: 28px !important;
}

/* Radio segmented control */
.stRadio > div[role="radiogroup"] {
    background: #e9ecef !important;
    padding: 4px !important;
    border-radius: 6px !important;
}
.stRadio > div[role="radiogroup"] label {
    color: #333 !important;
}

/* Reduce map padding */
iframe {
    border: none !important;
}

/* Compact divider in sidebar */
section[data-testid="stSidebar"] hr {
    margin: 8px 0 !important;
    border-color: #ddd !important;
}
</style>
"""
