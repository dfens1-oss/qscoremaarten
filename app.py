import streamlit as st
import pandas as pd
import datetime
import pytz
import time
from google.cloud import firestore
from google.oauth2 import service_account
import json

# --- 1. FIREBASE SETUP ---
# Zorg dat je 'firebase_service_account' in je Streamlit Secrets hebt staan
def get_db():
    if "db" not in st.session_state:
        key_dict = json.loads(st.secrets["firebase_secrets"])
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
    
    nu_nl = get_nederlandse_tijd()

    # OPTIE: Handmatig typen van datum en tijd
    # We gebruiken text_input zodat je gewoon '2026-03-30' kunt typen
    datum_str = st.text_input("Datum (JJJJ-MM-DD)", value=nu_nl.strftime("%Y-%m-%d"))
    tijd_str = st.text_input("Tijdstip (UU:MM)", value=nu_nl.strftime("%H:%M"))
    
    submitted = st.form_submit_button("Opslaan")
    
    if submitted:
        try:
            # Converteer je getypte tekst naar echte tijd-objecten
            schone_datum = datetime.datetime.strptime(datum_str, "%Y-%m-%d").date()
            schone_tijd = datetime.datetime.strptime(tijd_str, "%H:%M").time()
            
            dt_combi = datetime.datetime.combine(schone_datum, schone_tijd)
            
            new_data = {
                "timestamp": dt_combi.isoformat(),
                "datum": schone_datum.strftime("%Y-%m-%d"),
                "tijd": schone_tijd.strftime("%H:%M"),
                "score": int(score)
            }
            
            if col_ref:
                col_ref.add(new_data)
                st.success(f"✅ Opgeslagen: {score} op {datum_str} om {tijd_str}")
                time.sleep(0.5) 
                st.rerun()
        except ValueError:
            st.error("Foutformaat! Gebruik JJJJ-MM-DD voor datum en UU:MM voor tijd.")

# --- 5. VISUALISATIE ---
if not df.empty:
    # 1. Zorg dat de timestamp écht een datetime object is
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    st.subheader("Jouw verloop")
    
    # 2. Sorteer de dagen voor de selector
    dagen = sorted(df['datum'].unique(), reverse=True)
    geselecteerde_dag = st.selectbox("Bekijk dag:", dagen)
    
    # 3. Filter en sorteer de data expliciet op timestamp
    # We voegen .reset_index(drop=True) toe om eventuele oude index-volgorde te vergeten
    dag_data = df[df['datum'] == geselecteerde_dag].sort_values("timestamp").reset_index(drop=True)
    
    # 4. Grafiek Spec met expliciete sortering
    chart_spec = {
        "mark": {
            "type": "line", 
            "interpolate": "monotone", 
            "point": {"filled": True, "size": 100}
        },
        "encoding": {
            "x": {
                "field": "timestamp", 
                "type": "temporal",
                "title": "Tijdstip",
                "axis": {"format": "%H:%M", "grid": True},
                "sort": "ascending"  # <--- FORCEER CHRONOLOGISCHE VOLGORDE
            },
            "y": {
                "field": "score", 
                "type": "quantitative", 
                "scale": {"domain": [1, 10]}, 
                "title": "Kwaliteitsscore"
            },
            "color": {"value": "#ff4b4b"},
            "tooltip": [
                {"field": "tijd", "title": "Tijd"},
                {"field": "score", "title": "Score"}
            ]
        },
        "config": {"view": {"stroke": "transparent"}}
    }
    
    st.vega_lite_chart(dag_data, chart_spec, use_container_width=True)
    
    if st.checkbox("Toon tabel van vandaag"):
        # Ook hier sorteren we de tabel voor de zekerheid
        st.dataframe(dag_data[["tijd", "score"]].sort_values("tijd"))
else:
    st.info("Nog geen scores gevonden. Voer je eerste score hierboven in!")
