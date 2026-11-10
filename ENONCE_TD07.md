# TD07 — Plan-and-Execute sur un mini-corpus pédagogique

## 1. Positionnement

Ce TD **ne produit pas une revue systématique publiable**. Il utilise quatre
études réelles et huit unités de preuve déjà extraites afin d'isoler les
concepts de Plan-and-Execute.

Une vraie SLR demanderait notamment : protocole enregistré, stratégie de
recherche exhaustive, déduplication, double screening, diagramme PRISMA,
évaluation du risque de biais et méthode de synthèse justifiée.

Le livrable du TD est donc une **note de synthèse pédagogique**.

## 2. Continuité avec le TD06

```text
TD06 : retrouver et vérifier des passages
                         ↓
TD07 : organiser les preuves → exécuter un plan → produire une note
```

L'artefact `artifacts/td06_evidence.json` contient :

- 4 études primaires ;
- 8 unités de preuve, dont deux extractions comparatives réutilisant des études déjà présentes ;
- 3 questions de recherche ;
- résultats, contextes et limites déjà extraits.

## 3. Objectifs

À la fin du TD, vous saurez :

1. distinguer planification Direct, CoT structurée et ToT ;
2. valider un plan avant son exécution ;
3. exécuter uniquement les preuves autorisées ;
4. constater qu'un plan fixe peut échouer ;
5. réviser puis revalider le plan restant.

Les métriques du plan et la fonction d'observation sont fournies. Les six TODO
portent uniquement sur ces concepts centraux, mais plusieurs sont décomposés
en sous-parties : vous allez coder le protocole de planification, le contrôle
du graphe, l'exécution bornée et la révision de l'état.

## 4. Fichier à modifier

Tous les TODO se trouvent dans :

```text
slrresearch/plan_and_execute.py
```

Les autres fichiers sont à consulter, mais pas à modifier :

- `slrresearch/planning_models.py` : contrats Pydantic ;
- `slrresearch/td07_runtime.py` : plans contrôlés et replanner ;
- `artifacts/td06_evidence.json` : mini-corpus ;
- `tests/test_td07.py` : comportement attendu.

## 5. Exécution

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
pytest -v
```

Tester un TODO isolément :

```bash
pytest -v -k "todo_1"
```

Après les six TODO :

```bash
python3 main.py
python3 -m streamlit run streamlit_app.py
```

## 6. TODO 1 — Implémenter Direct, CoT et ToT

Fichiers concernés : `build_planning_prompt()` et `build_llm_planner()` dans
`slrresearch/plan_and_execute.py`.

### TODO 1a — Construire les consignes des trois stratégies

Complétez d'abord le dictionnaire `instructions`. Cette étape ne lance aucun
appel LLM : elle prépare le guidage textuel propre à chaque stratégie.

Remplacez les trois `None` de `instructions` par :

- Direct : Produis directement un plan candidat sans justification intermédiaire ;
- CoT structuré : Fournis des justifications structurées sur les dépendances, puis le plan ;
- ToT : Explore plusieurs organisations, évalue-les, puis propose le meilleur plan.

### TODO 1b — Implémenter les appels Direct, CoT et ToT

En mode LLM réel, Direct effectue un appel, CoT produit une analyse structurée
puis le plan (deux appels), et ToT produit trois candidats puis sélectionne le
meilleur selon les métriques de validation. L'adaptateur harmonise ensuite
l'ordre et les dépendances pour la comparaison.

### Pourquoi ce nombre d'appels ?

Il s'agit d'un protocole pédagogique explicite, et non d'une règle universelle.
Direct utilise un seul appel parce que le modèle reçoit directement l'objectif
et doit produire le plan final. CoT sépare volontairement deux opérations : un
premier appel structure l'analyse (ordre, justification, risques), puis un
second appel transforme cette analyse en `PlanCandidate`. Cette séparation rend
visible l'intermédiaire et permet de le valider.

ToT utilise trois appels indépendants parce qu'il doit explorer trois
organisations candidates. L'application valide ensuite chaque candidat et
sélectionne le meilleur selon la couverture, la cohérence et la complétude.
Dans une application réelle, le nombre de branches pourrait être dynamique,
parallélisé ou remplacé par une recherche guidée par un score plus riche.
L'objectif du TD est de rendre le mécanisme observable, pas de prétendre que
tous les systèmes ToT utilisent exactement trois appels.

### TODO 1c — Valider et sélectionner un candidat ToT

Pour chaque candidat ToT, appelez `validate_plan()` avant de le noter. Ignorez
un candidat invalide au lieu de l'exécuter. Pour un candidat valide, utilisez
`evaluate_plan()` et comparez au minimum `rq_coverage`, `consistency`, puis
`section_coverage`. Conservez le candidat ayant le meilleur triplet dans cet
ordre de priorité.

Le reste du prompt doit rester identique. Ensuite, dans la même fonction
`build_llm_planner()`, complétez les trois branches déjà préparées dans le
code :

```python
if strategy == "direct":
    # un seul invoke vers PlanCandidate
elif strategy == "cot":
    # invoke PlanningAnalysis, puis invoke PlanCandidate avec cette analyse
else:
    # trois invoke PlanCandidate, validation de chaque candidat,
    # puis sélection du meilleur score
```

`Direct` ne doit appeler le modèle qu'une fois. `CoT` doit effectuer deux
appels distincts : le premier produit un objet `PlanningAnalysis`, le second
construit le plan à partir de cette analyse. `ToT` doit effectuer trois appels
indépendants, conserver les candidats valides et choisir celui qui maximise
successivement la couverture des RQ, la cohérence des dépendances puis la
complétude des étapes. Ne remplacez pas ces appels par un simple changement de
texte dans le prompt.

Avant de coder, repérez dans `planning_models.py` les deux contrats utilisés :
`PlanningAnalysis` pour l'analyse CoT et `PlanCandidate` pour le plan final.
Pour convertir une réponse dictionnaire en objet validé, utilisez :

```python
analysis = PlanningAnalysis.model_validate(result)
plan = PlanCandidate.model_validate(result)
```

Le test ciblé vérifie le nombre d'appels :

```bash
pytest -v -k "todo_1_implementations"
```

## 7. TODO 2 — Valider avant d'exécuter

Fonction : `validate_plan()`

Complétez les six contrôles `TODO 2a` à `TODO 2f` :

```python
len(step_ids) != len(set(step_ids))
not set(step.evidence_ids) <= allowed_evidence_ids
not set(step.depends_on) <= known_steps
not required_rqs <= planned_rqs
```

Ces règles contrôlent respectivement :

1. l'unicité des étapes ;
2. une seule étape principale par RQ ;
3. les permissions sur les preuves ;
4. l'ordre des dépendances ;
5. l'interdiction de dépendre de soi-même ;
6. la couverture des RQ.

Indice : `A <= B` signifie que tous les éléments de `A` sont présents dans
`B`. Pour contrôler l'unicité des identifiants, comparez `len(step_ids)` et
`len(set(step_ids))`.

## 8. TODO 3 — Comparer les trois plans

Fonction : `compare_planning_strategies()`

Complétez la liste parcourue (`TODO 3a`) puis conservez dans chaque résultat
le triplet stratégie/plan/métriques (`TODO 3b`) :

```python
for strategy in [ ... ]:
```

Les valeurs attendues sont `direct`, `cot` et `tot`. Le planner doit
recevoir exactement le même objectif et les mêmes preuves trois fois.

Ne reconstruisez pas les preuves dans la boucle. Une itération doit appeler
`planner`, calculer `evaluate_plan`, puis ajouter le résultat à `comparisons`.
Les trois stratégies reçoivent exactement les mêmes entrées ; seul leur
protocole de construction change.

## 9. TODO 4 — Exécuter une étape autorisée

Fonction : `execute_step()`

Complétez les quatre expressions `TODO 4a` à `TODO 4d` :

```python
completed_steps
set(evidence_by_id)
covered
"synthesis"
```

L'ordre des contrôles est important :

1. dépendances terminées ;
2. preuves autorisées ;
3. facettes couvertes et manquantes ;
4. abstention si une synthèse exige une facette absente.

Pour calculer les facettes disponibles, parcourez les preuves sélectionnées et
rassemblez leurs listes `facets`. Les facettes manquantes sont la différence
entre les facettes exigées et les facettes disponibles. Une étape bloquée doit
rester observable ; elle ne doit jamais être transformée en succès.

## 10. TODO 5 — Plan fixe et retry

Fonction : `run_classic()`

Deux expressions sont à compléter :

```python
observation["citation_validity"]
max_retries
```

Avant d'accepter une étape, contrôlez à la fois `step_success` et
`citation_validity`. Un retry répète la même étape avec le même plan et les
mêmes preuves. Il ne corrige donc pas une exigence impossible.

Le retry ne modifie jamais `plan`. Il augmente seulement la tentative et ajoute
un événement `retry` dans la trace.

## 11. TODO 6 — Replanning contrôlé

Fonction : `run_with_replanning()`

Le code contient deux emplacements distincts à compléter :

```python
can_replan = None       # TODO 6a
current_plan = replanner(current_plan, step, set(result.covered_facets))
```

Pour `TODO 6a`, remplacez `None` par la condition qui autorise une nouvelle
révision : le nombre de révisions déjà effectuées doit être strictement
inférieur à `max_revisions`. La condition doit ensuite vérifier que le budget
d'actions n'est pas épuisé.

Avant l'appel au replanner, mémorisez les identifiants des étapes déjà
terminées. Après l'appel (`TODO 6b`), `TODO 6c` doit vérifier que ces
identifiants existent toujours dans le plan révisé.

Pour `TODO 6b`, appelez `replanner` avec exactement trois arguments : le plan
courant, l'étape qui vient d'échouer et l'ensemble des facettes couvertes.

Le plan révisé est ensuite obligatoirement repassé à `validate_plan()`.
Replanifier ne signifie ni ignorer une contrainte ni inventer une preuve : on
répare seulement la partie restante du plan et on conserve les résultats déjà
produits.

## 12. Démonstration Streamlit

L'interface sépare deux expériences :

### Expérience 1

Même exécuteur fixe, mais trois plans initiaux. On observe l'effet de l'ordre et
des exigences du plan sur la note produite.

### Expérience 2

Même plan Direct initial, mais deux politiques : retry sans modification ou
replanning suivi d'une revalidation.

## 13. Résultat conceptuel attendu

```text
PLAN → VALIDATE → EXECUTE → OBSERVE → DECIDE
                               ├── CONTINUE
                               ├── RETRY
                               ├── REPLAN + VALIDATE
                               ├── FINISH
                               └── ABSTAIN
```

La leçon principale n'est pas « l'IA produit une SLR ». Elle est : **un agent
autonome doit séparer proposition, contrôle, exécution et révision**.
