"""Creación del HUD de la escena de juego."""
import esper
import pygame

from src.create.prefab_text import create_interface_text
from src.ecs.components.c_lives_counter import CLivesCounter
from src.ecs.components.c_lives_icons import CLivesIcons
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_score_text import CScoreText, ScoreKind
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_ui import CTagUI


def create_score_hud(world: esper.World, hud_info: dict) -> None:
    """Crea los textos 1UP y HI-SCORE con sus valores, según el "hud" de score.json."""
    create_interface_text(world, hud_info["score_label"]["text"], hud_info["score_label"])
    create_interface_text(world, hud_info["hi_score_label"]["text"], hud_info["hi_score_label"])
    score = create_interface_text(world, "0", hud_info["score_value"])
    world.add_component(score, CScoreText(ScoreKind.SCORE))
    hi_score = create_interface_text(world, "0", hud_info["hi_score_value"])
    world.add_component(hi_score, CScoreText(ScoreKind.HI_SCORE))


def create_lives_hud(world: esper.World, lives_hud_info: dict) -> None:
    """Crea los íconos de las vidas y el contador, según "lives" > "hud" de score.json.

    Empiezan vacíos: system_lives_hud los dibuja con las vidas de GameStateService.
    """
    max_visible = lives_hud_info["max_visible"]
    icons_info = lives_hud_info["icons"]
    anchor = icons_info["anchor"]
    empty = pygame.Surface((0, 0), pygame.SRCALPHA)
    world.create_entity(CTransform(pygame.Vector2(anchor["x"], anchor["y"])), CSurface.from_surface(empty),
                        CLivesIcons(icons_info, max_visible), CTagUI())
    counter = create_interface_text(world, "", lives_hud_info["counter"])
    world.add_component(counter, CLivesCounter(max_visible))
