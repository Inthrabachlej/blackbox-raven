# blackbox-raven — Runbook

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Uzupełnij ANTHROPIC_API_KEY (lub OPENAI_API_KEY)
```

## Uruchomienie

```bash
source .venv/bin/activate
python raven.py
```

## Tryb :ask

```
:ask
Twoje pytanie w kilku liniach...
:end
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| API 401 | sprawdź klucz w `.env.local` |
| `.env.local` brakuje | `cp .env.example .env.local` |
