from pathlib import Path
import streamlit as st
from slrresearch.config import Settings, build_model
from slrresearch.plan_and_execute import build_llm_planner, compare_planning_strategies, run_classic, run_with_replanning
from slrresearch.td07_runtime import build_report_markdown, controlled_planner, controlled_replanner, load_td06_handoff

st.set_page_config(page_title="TD07 Plan-and-Execute", page_icon=":material/account_tree:", layout="wide")
ROOT=Path(__file__).parent; OBJECTIVE="Produire une note pédagogique couvrant RQ1, RQ2 et RQ3."

@st.cache_data
def load_inputs(): return load_td06_handoff(ROOT/"artifacts"/"td06_evidence.json")

def trace_rows(execution):
    labels={"continue":"Continuer","retry":"Réessayer","replan":"Replanifier","finish":"Terminer","abstain":"S'abstenir"}
    return [{"Étape":e.step_id,"Décision":labels[e.decision],"Raison":e.reason,"Information manquante":", ".join(e.missing_facets) or "—"} for e in execution.trace]

def plan_diagnostics(plan,evidence):
    evidence_by_id={item.id:item for item in evidence}; used_ids={identifier for step in plan.steps for identifier in step.evidence_ids}; unsupported=0
    for step in plan.steps:
        available={facet for identifier in step.evidence_ids if identifier in evidence_by_id for facet in evidence_by_id[identifier].facets}
        unsupported+=len(set(step.required_facets)-available)
    signatures={}
    for step in plan.steps: signatures.setdefault((step.rq_id,tuple(sorted(step.evidence_ids))),[]).append(step.id)
    duplicate_groups=[ids for ids in signatures.values() if len(ids)>1]
    return {"Preuves utilisées":f"{len(used_ids)}/{len(evidence_by_id)}","Dépendances":sum(len(step.depends_on) for step in plan.steps),"Exigences non supportées":unsupported,"Étapes de limitation":sum(step.mode=="limitation" for step in plan.steps),"Redondance potentielle":" ; ".join(", ".join(group) for group in duplicate_groups) or "Aucune"}

def duplicate_step_groups(plan):
    signatures={}
    for step in plan.steps: signatures.setdefault((step.rq_id,tuple(sorted(step.evidence_ids))),[]).append(step.id)
    return [ids for ids in signatures.values() if len(ids)>1]

evidence,required_rqs=load_inputs()
st.session_state.setdefault("phase1_result",None); st.session_state.setdefault("phase2_result",None)
st.title("TD07 — Plan-and-Execute")
st.warning("Ce mini-corpus sert à comprendre l'architecture agentique. La note produite n'est pas une revue systématique publiable.")
st.write("Nous étudions d'abord **l'effet de la stratégie de planification**, puis **l'effet du replanning pendant l'exécution**.")
with st.container(border=True):
    st.markdown("### Corpus de synthèse hérité du TD06")
    with st.container(horizontal=True):
        st.metric("Études primaires",len({item.paper_id for item in evidence})); st.metric("Unités de preuve",len(evidence)); st.metric("Questions de recherche",len(required_rqs))
    questions={item.rq_id:item.research_question for item in evidence}
    for rq_id in sorted(questions): st.markdown(f"**{rq_id} — {questions[rq_id]}**")
    st.caption("Une SLR compare plusieurs études, leurs résultats, leurs contextes et leurs limites.")
    st.info("E7 et E8 sont des extractions comparatives : elles réutilisent des études déjà présentes pour rendre visibles les compromis et les limites de domaine.")
with st.expander("Voir la matrice d'extraction multi-études",expanded=True):
    st.dataframe([{"Preuve":i.id,"RQ":i.rq_id,"Étude":i.paper_title,"Design":i.study_design,"Échantillon":i.sample,"Modèles":", ".join(i.models),"Résultat extrait":i.finding,"Limite":i.limitation} for i in evidence],hide_index=True)

st.header("Expérience 1 — Quel est l'effet de Direct, CoT et ToT ?")
st.info("Seule la stratégie de construction du plan change. L'exécuteur fixe et toutes les entrées restent identiques.")
st.caption("Dans ce TD, un plan est une suite ordonnée d'étapes. Chaque étape indique une RQ, un objectif, des preuves et les étapes dont elle dépend.")
with st.form("phase1_form",border=True):
    planner_mode=st.segmented_control("Planificateur",["Mode contrôlé","LLM réel"],default="Mode contrôlé")
    phase1_budget=st.slider("Budget identique pour chaque plan",3,9,6)
    run_phase1=st.form_submit_button("1 — Comparer les trois plans et leurs notes",type="primary",icon=":material/compare_arrows:")
if run_phase1:
    try:
        planner=controlled_planner if planner_mode=="Mode contrôlé" else build_llm_planner(build_model(Settings()))
        comparisons=compare_planning_strategies(planner,OBJECTIVE,evidence,required_rqs)
        executions={x["strategy"]:run_classic(x["plan"],evidence,required_rqs,max_retries=0,max_actions=phase1_budget) for x in comparisons}
        st.session_state.phase1_result={"mode":planner_mode,"comparisons":comparisons,"executions":executions}; st.session_state.phase2_result=None
    except Exception as exc: st.error(f"Expérience 1 impossible : {exc}")

phase1=st.session_state.phase1_result
if phase1:
    st.subheader("1A. Les trois plans initiaux : quelles étapes exécuter ?")
    explanations={"direct":"Plan immédiat et linéaire.","cot":"Organisation justifiée étape par étape.","tot":"Plusieurs organisations comparées avant le choix final."}
    columns=st.columns(3)
    for column,item in zip(columns,phase1["comparisons"]):
        plan=item["plan"]
        with column:
            with st.container(border=True,height="stretch"):
                st.markdown(f"### {plan.strategy.upper()}"); st.write(explanations[plan.strategy])
                if phase1["mode"] == "LLM réel":
                    st.caption(f"Appels LLM : {plan.llm_calls} — Direct : 1, CoT : 2, ToT : 3 selon le protocole pédagogique.")
                    st.caption("Implémentation réelle : Direct = 1 appel, CoT = analyse + plan (2 appels), ToT = 3 candidats évalués (3 appels). L'adaptateur harmonise l'ordre et les dépendances.")
                if plan.explored_alternatives: st.caption("Alternatives : "+" · ".join(plan.explored_alternatives))
                for index,step in enumerate(plan.steps,1):
                    st.markdown(f"**Étape {index} — {step.rq_id} (`{step.id}`)**"); st.write(step.objective)
                    st.caption(f"Preuves : {', '.join(step.evidence_ids)} · Dépend de : {', '.join(step.depends_on) if step.depends_on else 'aucune étape'}")
    st.subheader("1B. Effet observable sur les notes")
    effects={"direct":"Synthétise RQ1 et RQ2, puis s'abstient face à une validation prospective absente en RQ3.","cot":"Commence par les mécanismes de contrôle, puis relie performance et compromis dans une note complète.","tot":"Commence par le compromis décisionnel, compare les performances, puis conclut sur le déploiement."}
    summary=[]
    for item in phase1["comparisons"]:
        strategy=item["strategy"]; plan=item["plan"]; metrics=item["metrics"]; execution=phase1["executions"][strategy]; step_to_rq={s.id:s.rq_id for s in plan.steps}
        summary.append({"Stratégie":strategy.upper(),"Ordre des étapes":" → ".join(f"Étape {i} : {s.rq_id}" for i,s in enumerate(plan.steps,1)),"Nombre d'étapes":len(plan.steps),"Plan valide":"Oui" if metrics.valid else "Non","Couverture RQ":f"{metrics.rq_coverage:.0%}","Complétude étapes":f"{metrics.section_coverage:.0%}","Cohérence dépendances":f"{metrics.consistency:.0%}",**plan_diagnostics(plan,evidence),"Appels LLM":plan.llm_calls if phase1["mode"]=="LLM réel" else 0,"Actions":execution.tool_calls,"Statut":"Complet" if execution.status=="completed" else "Incomplet","Sections produites":" → ".join(step_to_rq[s.step_id] for s in execution.sections) or "Aucune"})
    st.dataframe(summary,hide_index=True)
    with st.expander("Contrôles réalisés avant l'exécution"):
        st.markdown("""Pour chaque plan, le validateur contrôle :

- l'unicité des identifiants d'étapes ;
- une seule section principale par question de recherche ;
- l'autorisation de chaque preuve ;
- l'ordre des dépendances et l'absence d'auto-dépendance ;
- la couverture de toutes les questions de recherche.

Un plan peut donc être bien formé tout en restant scientifiquement incomplet
si une facette demandée n'est pas présente dans les preuves.""")
    duplicate_rows=[]
    for item in phase1["comparisons"]:
        groups=duplicate_step_groups(item["plan"])
        duplicate_rows.append({"Stratégie":item["strategy"].upper(),"Étapes concernées":" ; ".join(", ".join(group) for group in groups) or "Aucune redondance détectée","Interprétation":"Vérifier les objectifs et fusionner si aucun apport distinct." if groups else "Les signatures RQ + preuves sont distinctes."})
    with st.expander("Contrôle pédagogique des sections dupliquées"):
        st.dataframe(duplicate_rows,hide_index=True)
        st.caption("Une alerte compare la même RQ et les mêmes preuves. Elle signale une redondance potentielle ; il faut encore lire les objectifs et le contenu.")
        for row in duplicate_rows:
            if row["Étapes concernées"]!="Aucune redondance détectée": st.warning(f"{row['Stratégie']} : {row['Étapes concernées']} utilisent la même RQ et les mêmes preuves.")
    with st.expander("Comment interpréter ces métriques ?"):
        st.markdown("""- **Couverture RQ** : questions présentes dans le plan.
- **Complétude des étapes** : objectif, preuves et facettes renseignés.
- **Cohérence des dépendances** : les étapes requises existent et ont déjà été exécutées.
- **Preuves utilisées** : diversité mobilisée ; davantage n'est pas automatiquement meilleur.
- **Exigences non supportées** : facettes absentes des preuves ; moins est préférable.
- **Étapes de limitation** : limites rendues explicites.
- **Appels LLM / actions** : coût à mettre en regard du bénéfice obtenu.""")
    st.warning("CoT et ToT n'inventent pas de validation prospective : cette lacune reste visible dans les limites. Le plan Direct en fait une précondition bloquante.")
    report_choice=st.segmented_control("Lire la note produite par",["DIRECT","COT","TOT"],default="DIRECT",key="phase1_report_choice")
    report=build_report_markdown(phase1["executions"][report_choice.lower()],evidence)
    with st.container(border=True): st.markdown(report)
    st.download_button("Télécharger cette note",report,file_name=f"note_{report_choice.lower()}.md",mime="text/markdown",icon=":material/download:",key="phase1_download")

    st.divider(); st.header("Expérience 2 — Plan fixe ou replanning ?")
    st.info("Seule la politique d'exécution change. Les deux variantes reçoivent le même plan DIRECT initial.")
    with st.form("phase2_form",border=True):
        with st.container(horizontal=True):
            retries=st.slider("Réessais du plan fixe",0,2,1); revisions=st.slider("Révisions autorisées",0,2,1); phase2_budget=st.slider("Budget d'actions",3,9,6)
        run_phase2=st.form_submit_button("2 — Comparer plan fixe et replanning",type="primary",icon=":material/account_tree:")
    if run_phase2:
        direct=next(x["plan"] for x in phase1["comparisons"] if x["strategy"]=="direct")
        st.session_state.phase2_result={"classic":run_classic(direct,evidence,required_rqs,max_retries=retries,max_actions=phase2_budget),"adaptive":run_with_replanning(direct,evidence,required_rqs,controlled_replanner,max_revisions=revisions,max_actions=phase2_budget)}

phase2=st.session_state.phase2_result
if phase1 and phase2:
    st.subheader("2A. Même plan Direct, deux politiques d'exécution")
    left,right=st.columns(2)
    for column,title,execution in [(left,"Plan-and-Execute classique",phase2["classic"]),(right,"Avec replanning",phase2["adaptive"])]:
        with column:
            with st.container(border=True,height="stretch"):
                st.markdown(f"### {title}")
                st.success("Note complète") if execution.status=="completed" else st.error("Note incomplète")
                st.dataframe(trace_rows(execution),hide_index=True); st.caption(f"{execution.tool_calls} actions · {execution.revisions} révision(s) · {len(execution.sections)} section(s)")
    st.subheader("2B. Effet du replanning sur la note Direct")
    report_version=st.segmented_control("Note à lire",["Plan fixe","Avec replanning"],default="Avec replanning",key="phase2_report_choice")
    chosen=phase2["classic"] if report_version=="Plan fixe" else phase2["adaptive"]
    with st.container(border=True): st.markdown(build_report_markdown(chosen,evidence))
elif not phase1:
    st.caption("Commencez par l'expérience 1. L'expérience 2 apparaîtra ensuite.")
