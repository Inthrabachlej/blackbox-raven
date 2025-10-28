blackbox-raven
==============

blackbox-raven = lokalny operator Claude 4.5 odpalany w terminalu Linux.

Rola:
- rozmawiasz z modelem z konsoli, bez przeglądarki
- dajesz mu kontekst plików / katalogów z wybranego workspace
- prosisz go o wygenerowanie pełnych plików kodu
- raven.py zapisuje te pliki fizycznie na dysk w tym workspace

Nie kopiujesz ręcznie kodu. Nie wklejasz do edytora. On pisze, plik powstaje.

Kluczowe komendy w raven.py:
- :use <name>        -> wybiera / tworzy workspace w workspaces/<name>
- :read_file <path>  -> ładuje plik albo cały katalog z workspace do kontekstu AI
- :write_file <path> -> AI generuje finalną zawartość pliku i raven.py zapisuje ten plik
- :ask               -> tryb promptu wielolinijkowego, kończysz wpisując :end
- :save / :load      -> zapis / przywrócenie historii czatu

Workflow, real case:
1. :use archon2
2. :read_file prompt_archon2.0.txt
3. :write_file api/main.py
4. :write_file core/state.py
5. :write_file core/planner.py

Ten flow wygenerował drugi projekt: "archon2".

archon2
-------

archon2 (public repo: github.com/Inthrabachlej/archon2) to FastAPI backend, który:
- ma endpointy /health i /build
- trzyma stan buildów projektów (projects/<name>/state)
- ma planner, który z opisu typu "blog API z auth i SQLite" robi strukturę modułów i zadań

archon2 został fizycznie wygenerowany przez blackbox-raven komendami :write_file. Prawie bez ręcznego pisania kodu.

Jak uruchomić blackbox-raven lokalnie:
1. python3 -m venv .venv
2. source .venv/bin/activate
3. pip install -r requirements.txt
4. echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env.local
5. source .env.local
6. ./raven.py

Bez przeglądarki. Bez wysyłania całego katalogu źródeł na zewnętrzny serwer. Ty decydujesz który workspace widzi model.

.gitignore blokuje:
- .env.local
- workspaces/
- sessions/
- venv/.venv
- __pycache__

To repo + archon2 pokazują stack:
- narzędzie operacyjne AI (blackbox-raven)
- backend orkiestrujący projekt i stan buildów (archon2)

To nie jest "hello world". To jest pipeline do generowania i składania backendu.
