from dash import html, register_page

register_page(__name__, path="/actions_page", name="Actions")

layout = html.Div(
    html.Iframe(
        src="/assets/marche_chart.html",
        style={"width": "100%", "height": "100%", "border": "none", "display": "block"},
    ),
    className="chart-page-outer",
)
