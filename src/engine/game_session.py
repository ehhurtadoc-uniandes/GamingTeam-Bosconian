class GameSession:
    """Datos de la partida que sobreviven al cambio de escena y de nivel.

    Cada escena vacía su mundo ECS al salir, así que el puntaje no puede vivir en una entidad.
    """

    def __init__(self, score_info: dict) -> None:
        self.hi_score: int = score_info["initial_hi_score"]
        self.score = 0

    def new_game(self) -> None:
        """Reinicia la partida; el HI-SCORE se conserva."""
        self.score = 0
