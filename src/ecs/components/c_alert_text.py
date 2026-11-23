from src.ecs.components.c_alert import AlertState


class CAlertText:
    """Texto del HUD con el nombre de la condición de alerta (#29).

    states trae el texto y el color de cada estado (alerts.json > hud > states);
    system_alert_hud los copia al CText según el estado de la alerta.
    """

    def __init__(self, states: dict[AlertState, dict]) -> None:
        self.states = states
