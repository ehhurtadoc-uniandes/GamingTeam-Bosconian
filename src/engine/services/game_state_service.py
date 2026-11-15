def next_extra_life_after(threshold: int, every: int) -> int:
    """Siguiente puntaje que da vida extra después de threshold: 50.000 -> 100.000 -> 200.000 -> ..."""
    return (threshold // every + 1) * every


class GameStateService:
    """Datos de la partida que sobreviven al cambio de escena y de nivel (puntaje, HI-SCORE, vidas).

    Cada escena vacía su mundo ECS al salir, así que estos datos no pueden vivir en una entidad.
    Los JSON no se guardan aquí: ConfigsService ya los lee una sola vez y los conserva.

    lives son las vidas de reserva: con 0 el jugador sigue jugando su última nave (LC-VID-01,
    "cero vidas se considera una vida"), y la partida termina si muere así.
    """

    def __init__(self) -> None:
        self.hi_score = 0
        self.score = 0
        self.lives = 0
        self.next_extra_life = 0
        self._lives_info: dict = {}

    def load(self, score_info: dict) -> None:
        """Arranca el estado con los valores de score.json. Lo llama GameEngine al iniciar."""
        self.hi_score = score_info["initial_hi_score"]
        self._lives_info = score_info["lives"]
        self.new_game()

    def new_game(self) -> None:
        """Reinicia la partida; el HI-SCORE se conserva."""
        self.score = 0
        self.lives = self._lives_info["initial"]
        self.next_extra_life = self._lives_info["extra_life"]["first"]

    def add_score(self, points: int) -> None:
        """Suma puntos al jugador. Si supera el HI-SCORE, este se actualiza al mismo tiempo (LC-PUN-03).

        Cada umbral de vida extra que se cruce da una vida (LC-VID-02), aunque se crucen varios a la vez.
        """
        self.score += points
        self.hi_score = max(self.hi_score, self.score)
        every = self._lives_info["extra_life"]["every"]
        while self.score >= self.next_extra_life:
            self.lives += 1
            self.next_extra_life = next_extra_life_after(self.next_extra_life, every)

    def lose_life(self) -> bool:
        """Descuenta una vida al morir. Devuelve False si no quedaba reserva: la partida terminó."""
        if self.lives == 0:
            return False
        self.lives -= 1
        return True
