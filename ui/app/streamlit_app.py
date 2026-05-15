import os

import pandas as pd
import requests
import streamlit as st

API = os.environ.get("API_BASE_URL", "http://localhost:8000")


def api_headers():
    token = st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def api_request(method: str, path: str, **kwargs):
    url = f"{API}{path}"
    resp = requests.request(method, url, headers=api_headers(), timeout=30, **kwargs)
    if resp.status_code == 401:
        st.session_state.pop("token", None)
        st.rerun()
    resp.raise_for_status()
    if resp.status_code == 204:
        return None
    return resp.json() if resp.content else None


def login_page():
    st.title("Konto Kompass")
    st.subheader("Anmelden")
    tab_login, tab_register = st.tabs(["Login", "Registrieren"])

    with tab_login:
        with st.form("login"):
            email = st.text_input("E-Mail")
            password = st.text_input("Passwort", type="password")
            if st.form_submit_button("Einloggen"):
                r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
                if r.status_code != 200:
                    try:
                        detail = r.json().get("detail", r.text)
                    except Exception:
                        detail = r.text
                    st.error(detail if isinstance(detail, str) else str(detail))
                else:
                    st.session_state["token"] = r.json()["access_token"]
                    st.rerun()

    with tab_register:
        with st.form("register"):
            email = st.text_input("E-Mail", key="reg_email")
            password = st.text_input("Passwort", type="password", key="reg_pw")
            tenant_name = st.text_input("Profilname (optional)")
            if st.form_submit_button("Registrieren"):
                payload = {"email": email, "password": password}
                if tenant_name:
                    payload["tenant_name"] = tenant_name
                r = requests.post(f"{API}/auth/register", json=payload, timeout=30)
                if r.status_code != 200:
                    try:
                        detail = r.json().get("detail", r.text)
                    except Exception:
                        detail = r.text
                    st.error(detail if isinstance(detail, str) else str(detail))
                else:
                    st.session_state["token"] = r.json()["access_token"]
                    st.rerun()


def sidebar_tenant():
    tenants = api_request("GET", "/tenants")
    if not tenants:
        st.warning("Kein Profil gefunden.")
        st.stop()
    tenant = st.sidebar.selectbox("Profil", tenants, format_func=lambda x: f'{x["name"]} ({x["role"]})')
    return tenant["id"]


def dashboard(tenant_id: int):
    overview = api_request("GET", f"/tenants/{tenant_id}/overview")
    st.header("Vermögensübersicht")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nettovermögen", f"€ {overview['net_worth_eur']:,.2f}")
    c2.metric("Guthaben", f"€ {overview['assets_liquidity_eur']:,.2f}")
    c3.metric("Investments", f"€ {overview['assets_investments_eur']:,.2f}")
    c4.metric("Schulden", f"€ {overview['liabilities_total_eur']:,.2f}")

    snaps = api_request("GET", f"/tenants/{tenant_id}/snapshots?limit=60")
    if snaps:
        df = pd.DataFrame(snaps)
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.sort_values("ts")
        st.subheader("Nettovermögen (Verlauf)")
        st.line_chart(df.set_index("ts")["net_worth_eur"])


def tab_accounts(tenant_id: int):
    areas = {a["slug"]: a for a in api_request("GET", f"/tenants/{tenant_id}/areas")}
    accounts = api_request("GET", f"/tenants/{tenant_id}/accounts")
    st.dataframe(accounts if accounts else [], use_container_width=True)

    with st.expander("Konto hinzufügen"):
        with st.form("new_account"):
            name = st.text_input("Name")
            area_slug = st.selectbox("Bereich", list(areas.keys()))
            provider = st.text_input("Anbieter", value="manual")
            if st.form_submit_button("Speichern"):
                api_request(
                    "POST",
                    f"/tenants/{tenant_id}/accounts",
                    json={"name": name, "area_id": areas[area_slug]["id"], "provider": provider},
                )
                st.success("Konto angelegt")
                st.rerun()

    with st.expander("Kontostand erfassen"):
        if not accounts:
            st.info("Zuerst ein Konto anlegen.")
            return
        with st.form("new_balance"):
            account_id = st.selectbox("Konto", accounts, format_func=lambda a: a["name"])["id"]
            amount = st.number_input("Betrag EUR", min_value=0.0, format="%.2f")
            if st.form_submit_button("Stand speichern"):
                api_request("POST", f"/tenants/{tenant_id}/balances", json={"account_id": account_id, "amount_eur": amount})
                st.success("Stand gespeichert")
                st.rerun()


def tab_holdings(tenant_id: int):
    holdings = api_request("GET", f"/tenants/{tenant_id}/holdings")
    st.dataframe(holdings if holdings else [], use_container_width=True)

    accounts = api_request("GET", f"/tenants/{tenant_id}/accounts")
    with st.expander("Position hinzufügen"):
        if not accounts:
            st.info("Zuerst ein Depot-Konto anlegen.")
            return
        with st.form("new_holding"):
            account_id = st.selectbox("Konto", accounts, format_func=lambda a: a["name"])["id"]
            symbol = st.text_input("Symbol/Name")
            isin = st.text_input("ISIN", value="")
            asset_type = st.selectbox("Typ", ["stock", "etf", "fund", "eos", "crypto", "other"])
            quantity = st.number_input("Stück", min_value=0.0, format="%.4f")
            value = st.number_input("Marktwert EUR", min_value=0.0, format="%.2f")
            if st.form_submit_button("Speichern"):
                api_request(
                    "POST",
                    f"/tenants/{tenant_id}/holdings",
                    json={
                        "account_id": account_id,
                        "symbol": symbol,
                        "isin": isin or None,
                        "asset_type": asset_type,
                        "quantity": quantity,
                        "market_value_eur": value,
                    },
                )
                st.success("Position gespeichert")
                st.rerun()


def tab_liabilities(tenant_id: int):
    items = api_request("GET", f"/tenants/{tenant_id}/liabilities")
    st.dataframe(items if items else [], use_container_width=True)

    with st.expander("Schuld hinzufügen (z.B. Klarna, PayPal, Hypothek)"):
        with st.form("new_liability"):
            label = st.text_input("Bezeichnung")
            provider = st.text_input("Anbieter", value="klarna")
            liability_type = st.selectbox("Typ", ["consumer_credit", "mortgage", "other"])
            principal = st.number_input("Ursprungsbetrag EUR", min_value=0.0, format="%.2f")
            remaining = st.number_input("Restschuld EUR", min_value=0.0, format="%.2f")
            monthly = st.number_input("Monatliche Rate EUR (optional)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Speichern"):
                payload = {
                    "label": label,
                    "provider": provider,
                    "liability_type": liability_type,
                    "principal_eur": principal,
                    "remaining_eur": remaining,
                }
                if monthly > 0:
                    payload["monthly_payment_eur"] = monthly
                api_request("POST", f"/tenants/{tenant_id}/liabilities", json=payload)
                st.success("Schuld gespeichert")
                st.rerun()


def tab_connections(tenant_id: int):
    conns = api_request("GET", f"/tenants/{tenant_id}/connections")
    st.dataframe(conns if conns else [], use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Gesamten Sync starten"):
            api_request("POST", f"/tenants/{tenant_id}/sync")
            st.success("Sync in Warteschlange")

    with col2:
        st.caption("Bank: GoCardless | Broker: WealthAPI")

    with st.expander("Verbindung hinzufügen"):
        with st.form("new_connection"):
            provider = st.selectbox("Provider", ["gocardless", "wealthapi", "manual", "csv_trade_republic"])
            label = st.text_input("Bezeichnung")
            external_ref = st.text_input("Externe Referenz (Konto-/Depot-ID)")
            if st.form_submit_button("Anlegen"):
                api_request(
                    "POST",
                    f"/tenants/{tenant_id}/connections",
                    json={"provider": provider, "label": label, "external_ref": external_ref or None},
                )
                st.success("Verbindung angelegt")
                st.rerun()

    with st.expander("Trade Republic CSV importieren"):
        csv_content = st.text_area("CSV-Inhalt einfügen")
        account_name = st.text_input("Depotname", value="Trade Republic")
        if st.button("CSV importieren"):
            api_request(
                "POST",
                f"/tenants/{tenant_id}/import/trade-republic-csv",
                json={"csv_content": csv_content, "account_name": account_name},
            )
            st.success("CSV importiert und Sync gestartet")


def main():
    if "token" not in st.session_state:
        login_page()
        return

    st.sidebar.title("Konto Kompass")
    if st.sidebar.button("Abmelden"):
        st.session_state.pop("token", None)
        st.rerun()

    try:
        me = api_request("GET", "/auth/me")
        st.sidebar.caption(me["email"])
        tenant_id = sidebar_tenant()
    except requests.HTTPError as exc:
        st.error(f"API-Fehler: {exc}")
        return

    tabs = st.tabs(["Dashboard", "Konten", "Positionen", "Schulden", "Verbindungen"])
    with tabs[0]:
        dashboard(tenant_id)
    with tabs[1]:
        tab_accounts(tenant_id)
    with tabs[2]:
        tab_holdings(tenant_id)
    with tabs[3]:
        tab_liabilities(tenant_id)
    with tabs[4]:
        tab_connections(tenant_id)


if __name__ == "__main__":
    main()
