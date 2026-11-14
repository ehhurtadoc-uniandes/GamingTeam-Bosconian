class GameStateService:
    """Datos de la partida que sobreviven al cambio de escena y de nivel (puntaje, HI-SCORE).

    Cada escena vacía su mundo ECS al salir, así que estos datos no pueden vivir en una entidad.
    Los JSON no se guardan aquí: ConfigsService ya los lee una sola vez y los conserva.
    """

    def __init__(self) -> None:
        self.hi_score = 0
        self.score = 0

    def load(self, score_info: dict) -> None:
        """Arranca el estado con los valores de score.json. Lo llama GameEngine al iniciar."""
        self.hi_score = score_info["initial_hi_score"]
        self.score = 0

    def new_game(self) -> None:
        """Reinicia la partida; el HI-SCORE se conserva."""
        self.score = 0

    def add_score(self, points: int) -> None:
        """Suma puntos al jugador. Si supera el HI-SCORE, este se actualiza al mismo tiempo (LC-PUN-03)."""
        self.score += points
        self.hi_score = max(self.hi_score, self.score)
