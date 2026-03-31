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
    
    # Gebruik session_state om de tijd even vast te houden tijdens het invullen
    nu_nl = get_nederlandse_tijd()
    
    # We geven de widgets een unieke 'key' zodat Streamlit de waarde beter bewaart
    gekozen_datum = st.date_input("Datum", value=nu_nl.date(), key="input_datum")
    gekozen_tijd = st.time_input("Tijdstip", value=nu_nl.time(), key="input_tijd")
    
    submitted = st.form_submit_button("Opslaan")
    
    if submitted:
        # Belangrijk: We halen de waarde direct uit de widgets en maken de timestamp 'schoon'
        # De .replace(microsecond=0) voorkomt dat de huidige milliseconden meeliften
        dt_combi = datetime.datetime.combine(gekozen_datum, gekozen_tijd).replace(microsecond=0)
        
        new_data = {
            "timestamp": dt_combi.isoformat(),
            "datum": gekozen_datum.strftime("%Y-%m-%d"),
            "tijd": gekozen_tijd.strftime("%H:%M"),
            "score": int(score) # Forceer integer
        }
        
        # Opslaan in Firebase
        if col_ref:
            col_ref.add(new_data)
            st.success(f"Score {score} opgeslagen voor {gekozen_datum} om {new_data['tijd']}!")
            # Geef de database even een seconde voor de rerun zodat de data zichtbaar is
            time.sleep(0.5) 
            st.rerun()

# --- 5. VISUALISATIE ---
if not df.empty:
    # Forceer de timestamp naar een echt datetime object
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    st.subheader("Jouw verloop")
    
    # Sorteer de dagen zodat de nieuwste bovenaan staat in de selector
    dagen = sorted(df['datum'].unique(), reverse=True)
    geselecteerde_dag = st.selectbox("Bekijk dag:", dagen)
    
    # Filter de data voor de gekozen dag
    dag_data = df[df['datum'] == geselecteerde_dag].copy()
    
    # Sorteer de data van die dag op het exacte tijdstip
    dag_data = dag_data.sort_values("timestamp")
    
    # Verbeterde Grafiek Spec
    chart_spec = {
        "mark": {
            "type": "line", 
            "interpolate": "monotone", 
            "point": {"filled": True, "size": 100} # Maak de punten duidelijker
        },
        "encoding": {
            "x": {
                "field": "timestamp", 
                "type": "temporal",  # Veranderd van nominal naar temporal
                "title": "Tijdstip",
                "axis": {"format": "%H:%M"} # Toon alleen uren:minuten op de as
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
        st.dataframe(dag_data[["tijd", "score"]].sort_values("tijd"))
else:
    st.info("Nog geen scores gevonden. Voer je eerste score hierboven in!")
