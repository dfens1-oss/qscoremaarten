import streamlit as st
import pandas as pd
import datetime
import pytz
from google.cloud import firestore
from google.oauth2 import service_account
import json

# --- 1. FIREBASE SETUP ---
# Zorg dat je 'firebase_service_account' in je Streamlit Secrets hebt staan
def get_db():
    if "db" not in st.session_state:
        key_dict = json.loads(st.secrets["textkey"]) # Of hoe je je secret noemt
        creds = service_account.Credentials.from_service_account_info(key_dict)
        st.session_state.db = firestore.Client(credentials=creds)
    return st.session_state.db

db = get_db()
col_ref = db.collection("kwaliteitsscores")

# --- 2. HELPERS ---
def get_nederlandse_tijd():
    tz = pytz.timezone('Europe/Amsterdam')
    return datetime.datetime.now(tz)

st.title("Dagelijkse Kwaliteitsscore")

# --- 3. DATA LADEN (Uit Firebase) ---
def load_data():
    docs = col_ref.stream()
    data = []
    for doc in docs:
        data.append(doc.to_dict())
    return pd.DataFrame(data)

df = load_data()

# --- 4. INVOER GEDEELTE ---
with st.form("score_form", clear_on_submit=True):
    score = st.slider("Wat is de score?", 1, 10, 5)
    
    # Handmatige datum en tijd (standaard op NU in NL tijd)
    nu_nl = get_nederlandse_tijd()
    gekozen_datum = st.date_input("Datum", nu_nl.date())
    gekozen_tijd = st.time_input("Tijdstip", nu_nl.time())
    
    submitted = st.form_submit_button("Opslaan")
    
    if submitted:
        # Combineer datum en tijd tot één timestamp
        dt_combi = datetime.datetime.combine(gekozen_datum, gekozen_tijd)
        
        new_data = {
            "timestamp": dt_combi.isoformat(),
            "datum": gekozen_datum.strftime("%Y-%m-%d"),
            "tijd": gekozen_tijd.strftime("%H:%M"),
            "score": score
        }
        
        # Opslaan in Firebase
        col_ref.add(new_data)
        st.success(f"Score {score} opgeslagen voor {gekozen_datum}!")
        st.rerun()

# --- 5. VISUALISATIE ---
if not df.empty:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    st.subheader("Jouw verloop")
    
    dagen = sorted(df['datum'].unique(), reverse=True)
    geselecteerde_dag = st.selectbox("Bekijk dag:", dagen)
    
    dag_data = df[df['datum'] == geselecteerde_dag].sort_values("timestamp")
    
    # Gebogen lijn grafiek via Vega-Lite
    chart_spec = {
        "mark": {"type": "line", "interpolate": "monotone", "point": True},
        "encoding": {
            "x": {"field": "tijd", "type": "nominal", "title": "Tijdstip"},
            "y": {"field": "score", "type": "quantitative", "scale": {"domain": [1, 10]}, "title": "Score"},
            "color": {"value": "#ff4b4b"}
        },
        "config": {"view": {"stroke": "transparent"}}
    }
    
    st.vega_lite_chart(dag_data, chart_spec, use_container_width=True)
    
    if st.checkbox("Toon alle geschiedenis"):
        st.write(df.sort_values("timestamp", ascending=False))
else:
    st.info("Nog geen scores aanwezig in Firebase.")
