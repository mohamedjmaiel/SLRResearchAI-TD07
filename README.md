# SLRResearchAI — TD07 étudiant

Cette version conserve les acquis du TD06 et ajoute six TODO principaux, avec
des sous-parties 1a–1c, 2a–2f, 3a–3b, 4a–4d, 5a–5b et 6a–6c, dans :

```text
slrresearch/plan_and_execute.py
```

Le TD compare trois implémentations de construction d'un plan — Direct, CoT et ToT
— puis deux variantes d'exécution du même plan Direct : classique et avec
replanning.

## Démarrage

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
pytest -v
```

Après les TODO :

```bash
python3 main.py
python3 -m streamlit run streamlit_app.py
```

Consultez [ENONCE_TD07.md](ENONCE_TD07.md) avant de modifier le code.
