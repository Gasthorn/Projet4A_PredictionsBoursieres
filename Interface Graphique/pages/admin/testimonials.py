import dash
from dash import html, dcc, Input, Output, callback
from services.tracking_service import get_pending_testimonials, approve_testimonial, reject_testimonial

dash.register_page(__name__, path="/admin/testimonials", name="Gestion Témoignages")

layout = html.Div(className="admin-testimonials", children=[
    html.H1("Gestion des témoignages", className="admin-title"),
    html.Div(id="pending-testimonials-list"),
    dcc.Interval(id="testimonials-refresh", interval=5000, n_intervals=0)
])

@callback(
    Output("pending-testimonials-list", "children"),
    Input("testimonials-refresh", "n_intervals")
)
def refresh_pending(n):
    testimonials = get_pending_testimonials()
    
    if not testimonials:
        return html.Div("Aucun témoignage en attente", className="empty-state")
    
    cards = []
    for t in testimonials:
        t_id, email, name, content, rating, investment, gain, period, date = t
        
        card = html.Div(className="testimonial-card", children=[
            html.Div(className="testimonial-header", children=[
                html.H3(name),
                html.Span(f"Note: {'★'*rating}", className="rating"),
            ]),
            html.P(content),
            html.Div(className="testimonial-meta", children=[
                html.Span(f"Email: {email}"),
                html.Span(f"Invest: {investment}€" if investment else ""),
                html.Span(f"Gain: +{gain}€" if gain else ""),
            ]),
            html.Div(className="testimonial-actions", children=[
                html.Button("✅ Approuver", id=f"approve-{t_id}", className="approve-btn"),
                html.Button("❌ Rejeter", id=f"reject-{t_id}", className="reject-btn"),
            ]),
        ])
        cards.append(card)
    
    return cards

@callback(
    Output("pending-testimonials-list", "children", allow_duplicate=True),
    Input({"type": "approve-btn", "index": dash.dependencies.ALL}, "n_clicks"),
    Input({"type": "reject-btn", "index": dash.dependencies.ALL}, "n_clicks"),
    prevent_initial_call=True
)
def handle_testimonial_action(approve_clicks, reject_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if "approve" in button_id:
        testimonial_id = button_id.split("-")[1]
        approve_testimonial(testimonial_id)
    elif "reject" in button_id:
        testimonial_id = button_id.split("-")[1]
        reject_testimonial(testimonial_id)
    
    # Rafraîchir la liste
    return refresh_pending(None)