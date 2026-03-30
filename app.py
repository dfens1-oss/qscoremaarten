import streamlit as st
import pandas as pd
import datetime
import os

# Bestandsnaam voor opslag
DATA_FILE = "scores.csv"

st.title("Dagelijkse Kwaliteitsscore")

# 1. Data laden of aanmaken
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
else:
    df = pd.DataFrame(columns=["timestamp", "datum", "tijd", "score"])

# 2. Invoer gedeelte
with st.form("score_form", clear_on_submit=True):
    score = st.slider("Wat is de score van dit moment?", 1, 10, 5)
    submitted = st.form_submit_button("Opslaan")
    
    if submitted:
        nu = datetime.datetime.now()
        new_data = {
            "timestamp": nu,
            "datum": nu.strftime("%Y-%m-%d"),
            "tijd": nu.strftime("%H:%M"),
            "score": score
        }
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.success(f"Score {score} opgeslagen!")

# 3. Visualisatie
if not df.empty:
    st.subheader("Jouw verloop")
    
    # Filteren op dag (optioneel, hier tonen we alles)
    dagen = df['datum'].unique()
    geselecteerde_dag = st.selectbox("Bekijk dag:", dagen[::-1]) # Nieuwste bovenaan
    
    dag_data = df[df['datum'] == geselecteerde_dag].sort_values("timestamp")
    
    # Grafiek tekenen
    st.line_chart(data=dag_data, x="tijd", y="score")
    
    # Tabelweergave voor details
    if st.checkbox("Toon ruwe data"):
        st.write(dag_data)
else:
    st.info("Nog geen scores ingevoerd. Begin hierboven!")
