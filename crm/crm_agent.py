"""
crm/crm_agent.py — Dedicated Agno CRM agent using the same small LLM.
Handles CRM queries conversationally, separate from the main Bonsai agent.
"""

from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.tools import tool
from crm.db import (
    get_urgent_events, get_seasonal_targets, get_followups_due,
    pipeline_summary, log_contact, add_event, find_organisations,
    find_events,
)
from datetime import date


# ─── Tools ────────────────────────────────────────────────────────────────────

@tool
def crm_urgent_contacts() -> str:
    """Return events that should be contacted now (green), soon (yellow), or are overdue (red)."""
    events = get_urgent_events()
    if not events:
        return "Aucun événement urgent pour ce mois-ci."
    lines = []
    for e in events:
        emoji = {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}.get(e['urgency'], '⚪')
        lines.append(f"{emoji} {e['city']} — {e['event_name']} (contacter: {e['best_contact']})")
    return "\n".join(lines)


@tool
def crm_followups() -> str:
    """Return all overdue follow-ups."""
    items = get_followups_due()
    if not items:
        return "Aucun suivi en retard."
    return "\n".join([
        f"• {i['org_name']} ({i['city']}) — statut: {i['status']} — prévu: {i['follow_up_date']}"
        for i in items
    ])


@tool
def crm_pipeline() -> str:
    """Return pipeline summary with counts and total value in CAD."""
    summary = pipeline_summary()
    lines = [f"Total organisations: {summary['total_orgs_contacted']}",
             f"Valeur pipeline: ${summary['total_pipeline_value_cad']:,.0f} CAD", ""]
    for s in summary['by_status']:
        lines.append(f"• {s['status']}: {s['count']} ({s['total_value']:,.0f}$)")
    return "\n".join(lines)


@tool
def crm_log_contact_tool(org_name: str, status: str, summary: str, follow_up_date: str = "") -> str:
    """Log a contact interaction. Find org by name, log status and summary."""
    orgs = find_organisations(query=org_name)
    if not orgs:
        return f"Organisation '{org_name}' introuvable dans le CRM."
    org = orgs[0]
    log_contact(
        org_id=org['id'],
        status=status,
        summary=summary,
        follow_up_date=follow_up_date,
        method='agent',
    )
    return f"✅ Contact enregistré pour {org['name']} — statut: {status}"


@tool
def crm_search_events(city: str = "", query: str = "") -> str:
    """Search events by city or keyword."""
    events = find_events(city=city, query=query)
    if not events:
        return "Aucun événement trouvé."
    return "\n".join([
        f"• {e['city']} — {e['event_name']} ({e['event_type']}) | Contacter: {e['best_contact']}"
        for e in events[:15]
    ])


@tool
def crm_seasonal_targets_tool(month: int = 0) -> str:
    """Return organisations to contact this month based on seasonal windows."""
    m = month if month else date.today().month
    orgs = get_seasonal_targets(m)
    if not orgs:
        return f"Aucune cible saisonnière pour le mois {m}."
    return "\n".join([f"• {o['name']} ({o['city']}) — {o['org_type']}" for o in orgs])


# ─── Agent ────────────────────────────────────────────────────────────────────

def build_crm_agent(model_url: str, model_name: str, api_key: str = "local") -> Agent:
    """Build and return the CRM Agno agent."""
    model = OpenAILike(
        id=model_name,
        base_url=model_url,
        api_key=api_key,
    )
    return Agent(
        model=model,
        tools=[
            crm_urgent_contacts,
            crm_followups,
            crm_pipeline,
            crm_log_contact_tool,
            crm_search_events,
            crm_seasonal_targets_tool,
        ],
        instructions="""Tu es l'agent CRM de Nic Idées / Cirkanime.
Tu aides à gérer les contacts, événements et suivis commerciaux.
Réponds toujours en français. Sois concis et orienté action.
Quand on te demande qui contacter, utilise crm_urgent_contacts.
Quand on te demande les suivis en retard, utilise crm_followups.
Quand on te demande d'enregistrer un contact, utilise crm_log_contact_tool.""",
        markdown=True,
    )
