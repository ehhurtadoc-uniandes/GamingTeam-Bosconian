import esper

from src.ecs.components.c_text import CText
from src.ecs.components.tags.c_tag_score_text import CTagScoreText, ScoreKind
from src.engine.game_session import GameSession


def add_score(session: GameSession, points: int) -> None:
    """Suma puntos al jugador. Si supera el HI-SCORE, este se actualiza al mismo tiempo (LC-PUN-03)."""
    session.score += points
    session.hi_score = max(session.hi_score, session.score)


def system_score_hud(world: esper.World, session: GameSession) -> None:
    """Muestra en el HUD el puntaje y el HI-SCORE de la sesión."""
    components = world.get_components(CText, CTagScoreText)
    c_text: CText
    c_tag: CTagScoreText
    for _, (c_text, c_tag) in components:
        value = session.score if c_tag.kind == ScoreKind.SCORE else session.hi_score
        c_text.text = str(value)
