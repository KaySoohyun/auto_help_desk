"""Categorías disponibles para tickets.

Lista compartida entre backend y frontend para mantener consistencia.
"""

TICKET_CATEGORIES = [
    {"value": "billing", "label": "Facturación"},
    {"value": "technical", "label": "Soporte técnico"},
    {"value": "account", "label": "Cuenta"},
    {"value": "general", "label": "Consulta general"},
    {"value": "urgent", "label": "Urgente"},
    {"value": "feedback", "label": "Feedback"},
    {"value": "other", "label": "Otro"},
]
