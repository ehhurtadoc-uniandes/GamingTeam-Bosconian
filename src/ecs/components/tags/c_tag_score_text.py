from enum import Enum


class ScoreKind(Enum):
    SCORE = 0
    HI_SCORE = 1


class CTagScoreText:
    """Marca el texto del HUD que muestra el puntaje (1UP) o el HI-SCORE."""

    def __init__(self, kind: ScoreKind) -> None:
        self.kind = kind
