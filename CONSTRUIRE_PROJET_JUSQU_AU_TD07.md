# Construire SLRResearchAI jusqu'au TD07

## Continuité du projet

```text
TD01–TD02  questions de recherche et plan de recherche
TD03       recherche d'articles et artefact bibliographique
TD04       screening déterministe, LLM et arbitrage humain
TD05       RAG classique et preuves retrouvées
TD06       RAG agentique et mémoire de travail
TD07       planification, exécution contrôlée et replanning
```

Le TD07 ne recommence pas les étapes précédentes. Il consomme
`artifacts/td06_evidence.json`, qui représente le contrat de transmission du
TD06. Cet artefact contient trois questions de recherche, quatre études et six
unités de preuve traçables.

## Limite volontaire

Le corpus est petit afin de rendre les décisions du planificateur observables
en classe. Le livrable est donc une **note de synthèse pédagogique**, et non une
SLR publiable. Une véritable SLR exigerait notamment une recherche exhaustive,
la déduplication, un protocole, plusieurs évaluateurs, un diagramme PRISMA et
une évaluation du risque de biais.

## Ce que le TD07 ajoute

Le TD06 répondait surtout à la question « quelles preuves retrouver ? ».
Le TD07 répond à « dans quel ordre les exploiter, comment contrôler le plan
et que faire lorsqu'une précondition manque ? ».

La sortie de ce TD pourra être remplacée dans le projet personnel par un
artefact plus riche sans changer les principes : contrat Pydantic, plan validé,
exécution bornée, observation et replanning.
