import os
import requests
import streamlit as st

API = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.title("Konto Kompass")

tenants = requests.get(f"{API}/tenants").json()
if not tenants:
    st.info("Noch kein Tenant. Erstelle einen via POST /tenants?name=...")
    st.stop()

tenant = st.selectbox("Tenant", tenants, format_func=lambda x: f'{x["id"]}: {x["name"]}')
tenant_id = tenant["id"]

snap = requests.get(f"{API}/tenants/{tenant_id}/snapshots/latest").json()

if not snap:
    st.warning("Noch kein Snapshot vorhanden. Warte auf den täglichen Job oder triggere sync_tenant manuell.")
else:
    st.metric("Total (EUR)", snap["total_eur"])
    st.metric("EOS (EUR)", snap["eos_eur"])
    st.metric("Stocks (EUR)", snap["stocks_eur"])
    st.metric("Cash (EUR)", snap["cash_eur"])
    st.write("Threshold:", snap["threshold_total_eur"], "Hit:", snap["threshold_hit"])
