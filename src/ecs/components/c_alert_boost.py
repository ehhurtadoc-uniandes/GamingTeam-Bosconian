class CAlertBoost:
    """Marca de un enemigo que ya recibió el multiplicador de velocidad de la alerta ROJA (#29).

    Evita aplicarlo dos veces. factor es el multiplicador que se aplicó.
    """

    def __init__(self, factor: float) -> None:
        self.factor = factor
