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
2. Unter **Import** CSV-Dateien hochladen (ohne API-Keys) – siehe unten.
3. Unter **Schulden** Einträge für Klarna, PayPal, Hypothek etc. anlegen.
4. Optional: **Verbindungen** für GoCardless/WealthAPI (kostenpflichtig/reguliert).

## Ohne API-Keys: Workflow mit CSV-Exporten

Kein Scraping, keine WealthAPI-/GoCardless-Pflicht. Du exportierst periodisch aus dem Online-Banking bzw. Broker und importierst lokal.

| Was | Wo exportieren | In Konto-Kompass |
|-----|----------------|------------------|
| **Giro-Saldo** | Deutsche Bank / anderes HB: Umsätze/Konto oft als CSV; oder eine Zeile mit Kontostand | Tab **Import** → „Konto-CSV“ |
| **Depot / ETFs** | Trade Republic, viele Broker: Portfolio-CSV | Tab **Import** → „Depot-CSV“ |
| **Schulden** | — | Tab **Schulden** manuell |

**Beispiel Kontostand (`Konto,Saldo`):**

```csv
Konto,Saldo
Deutsche Bank Giro,4521.33
```

**Beispiel Depot (`Instrument,ISIN,Quantity,Market Value`):**

```csv
Instrument,ISIN,Quantity,Market Value
MSCI World,IE00BK5BQT80,10,980.50
```

Nach dem Import: Dashboard zeigt Nettovermögen; unter **Positionen** / **Konten** die Details. Einmal pro Woche re-importieren reicht für viele Nutzer.

**Hinweis:** Spaltennamen sind flexibel (deutsch/englisch). Passt dein Export nicht, CSV-Beispiel im Tab **Import** ansehen oder Spalten umbenennen.

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

## Fehlerbehebung (Deployment)

### Warnung `variable "..." is not set`

Docker Compose interpretiert `$` in der `.env` als Variablen-Start. Passwort `abc$xyz` wird zu `abc` + leerer Variable `xyz`.

**Lösung:** Passwort ohne `$` wählen, oder `$` als `$$` schreiben (`geheim$$pass` → `geheim$pass`).

### `Connection refused` zu PostgreSQL

Die API startete früher Alembic, bevor Postgres bereit war. Aktuell: DB-Healthcheck + Warte-Skript im API-Entrypoint. Nach `git pull`:

```bash
docker compose down
docker compose up -d --build
docker compose logs -f db
docker compose logs -f api
```

Falls die DB mit **leerem** Passwort initialisiert wurde (wegen `$`-Problem), Volume zurücksetzen:

```bash
docker compose down
docker volume rm konto-kompass_pgdata_konto_kompass   # Name: docker volume ls prüfen
# .env mit korrektem POSTGRES_PASSWORD
docker compose up -d --build
```

### Synchronisierung liefert keine Daten / Status `needs_reauth`

- **Go Cardless:** Feld **Externe Referenz** muss die **Account-UUID** sein, die die GoCardless-API nach der Bank-Verknüpfung zurückgibt (`GET /accounts/` …). Eine **Kontonummer** (z.B. nur Ziffern wie `4189935560`) funktioniert nicht.
- **WealthAPI:** Hier muss die **Depot-ID** aus dem WealthAPI-Portal/API stehen, nicht die Kontonummer der Bank (Worker nutzt `/depots/{id}/positions`).
- Logs: `docker compose logs worker --tail 80` — dort erscheinen die Fehlerursachen.
- Doppelte oder widersprüchliche Verbindungen (gleiche Bank zweimal) löschen bzw. bereinigen.

## Migrationen

```bash
cd api
DATABASE_URL=postgresql+psycopg://konto:pass@localhost:5432/konto_kompass alembic upgrade head
```
