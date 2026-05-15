# Konto-Kompass

Persönliche Vermögensübersicht (GetQuin-ähnlich) mit Bereichen für **Guthaben**, **Investments** und **Schulden**. Unterstützt manuelle Erfassung, Trade-Republic-CSV-Import sowie Anbindung von Banken (GoCardless) und Brokern (WealthAPI).

## Architektur

- **api** – FastAPI REST API mit JWT-Auth
- **worker** – Celery-Sync (täglich 06:00 Europe/Berlin)
- **ui** – Streamlit-Dashboard
- **packages/konto_models** – gemeinsame SQLAlchemy-Modelle
- **packages/konto_connectors** – Parser und Connector-Datentypen

## Schnellstart

```bash
cp .env.example .env
# APP_SECRET und POSTGRES_PASSWORD anpassen

docker compose up --build
```

- UI: http://localhost:8501
- API-Docs: http://localhost:8000/docs

Beim ersten Start führt die API automatisch Alembic-Migrationen aus.

## Registrierung & Nutzung

1. In der UI unter **Registrieren** ein Konto anlegen (legt automatisch ein persönliches Profil/Tenant an).
2. Unter **Konten** Girokonten anlegen und Kontostände erfassen.
3. Unter **Positionen** Aktien/ETFs manuell pflegen oder Trade-Republic-CSV importieren.
4. Unter **Schulden** Einträge für Klarna, PayPal, Hypothek etc. anlegen.
5. **Verbindungen** für GoCardless/WealthAPI konfigurieren und Sync starten.

## API-Beispiele

```bash
# Registrieren
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"du@example.com","password":"geheim123"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"du@example.com","password":"geheim123"}' | jq -r .access_token)

# Übersicht
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/tenants/1/overview
```

## Externe Anbieter

| Provider | Zweck | Env-Variablen |
|----------|--------|----------------|
| GoCardless | Bank-Guthaben (PSD2) | `GOCARDLESS_SECRET_ID`, `GOCARDLESS_SECRET_KEY` |
| WealthAPI | Depot-Positionen | `WEALTHAPI_KEY` |
| CSV | Trade Republic Export | UI-Import, kein API-Key nötig |

## Sicherheit: `token_blob`

OAuth-Tokens und CSV-Inhalte in `connections.token_blob` werden mit **Fernet** verschlüsselt. Der Schlüssel wird aus `APP_SECRET` abgeleitet (SHA-256 → Base64). In Produktion:

- `APP_SECRET` als langer Zufallswert (min. 32 Zeichen)
- HTTPS vor der API
- Secrets nicht committen (`.env` ist in `.gitignore`)

## Tests

```bash
pip install -e packages/konto_models -e packages/konto_connectors -e api -e worker
pip install pytest
pytest
```

## Migrationen

```bash
cd api
DATABASE_URL=postgresql+psycopg://konto:pass@localhost:5432/konto_kompass alembic upgrade head
```
