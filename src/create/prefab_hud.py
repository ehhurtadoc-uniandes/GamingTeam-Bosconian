"""Creación del HUD de la escena de juego."""
import esper
import pygame

from src.create.prefab_text import create_text
from src.ecs.components.c_text import TextAlignment
from src.ecs.components.tags.c_tag_score_text import CTagScoreText, ScoreKind
from src.engine.service_locator import ServiceLocator

INTERFACE_CONFIG = "assets/cfg/interface.json"


def _create_hud_text(world: esper.World, text: str, text_info: dict) -> int:
    interface = ServiceLocator.configs_service.get(INTERFACE_CONFIG)
    font = ServiceLocator.fonts_service.get(interface["font"], interface["font_size"])
    color = text_info["color"]
    anchor = text_info["anchor"]
    return create_text(world, text, font, pygame.Color(color["r"], color["g"], color["b"]),
                       pygame.Vector2(anchor["x"], anchor["y"]), TextAlignment[text_info["alignment"]])


def create_score_hud(world: esper.World, hud_info: dict) -> None:
    """Crea los textos 1UP y HI-SCORE con sus valores, según el "hud" de score.json."""
    _create_hud_text(world, hud_info["score_label"]["text"], hud_info["score_label"])
    _create_hud_text(world, hud_info["hi_score_label"]["text"], hud_info["hi_score_label"])
    score = _create_hud_text(world, "0", hud_info["score_value"])
    world.add_component(score, CTagScoreText(ScoreKind.SCORE))
    hi_score = _create_hud_text(world, "0", hud_info["hi_score_value"])
    world.add_component(hi_score, CTagScoreText(ScoreKind.HI_SCORE))
