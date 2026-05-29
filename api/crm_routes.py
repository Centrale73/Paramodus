"""
api/crm_routes.py — CRM REST API routes for BonsaiChat.
Mounted at /api/crm in app.py.
"""

from flask import Blueprint, request, jsonify
from crm.db import get_urgent_events, add_event, log_contact

crm_bp = Blueprint('crm', __name__, url_prefix='/api/crm')


@crm_bp.route('/urgent', methods=['GET'])
def crm_urgent():
    """Return all events with urgency tags for the current month."""
    events = get_urgent_events()
    return jsonify({'events': events})


@crm_bp.route('/events', methods=['POST'])
def crm_add_event():
    """Add a new event/organisation to the CRM."""
    data = request.json or {}
    eid = add_event(
        event_name=data.get('event_name', ''),
        city=data.get('city', ''),
        event_type=data.get('event_type', ''),
        contact_month_start=data.get('contact_month_start'),
        contact_month_end=data.get('contact_month_end'),
        notes=data.get('notes', ''),
    )
    return jsonify({'id': eid}), 201


@crm_bp.route('/log', methods=['POST'])
def crm_log():
    """Log a contact interaction for an organisation."""
    data = request.json or {}
    lid = log_contact(
        org_id=data.get('org_id'),
        status=data.get('status', ''),
        summary=data.get('summary', ''),
        follow_up_date=data.get('follow_up_date', ''),
        method=data.get('method', 'UI'),
    )
    return jsonify({'id': lid}), 201
