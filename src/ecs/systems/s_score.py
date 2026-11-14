import esper

from src.ecs.components.c_score_text import CScoreText, ScoreKind
from src.ecs.components.c_text import CText
from src.engine.service_locator import ServiceLocator


def system_score_hud(world: esper.World) -> None:
    """Muestra en el HUD el puntaje y el HI-SCORE de GameStateService."""
    game_state = ServiceLocator.game_state_service
    components = world.get_components(CText, CScoreText)
    c_text: CText
    c_score: CScoreText
    for _, (c_text, c_score) in components:
        value = game_state.score if c_score.kind == ScoreKind.SCORE else game_state.hi_score
        c_text.text = str(value)
