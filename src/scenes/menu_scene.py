import pygame

from src.create.prefab_stars import create_starfield
from src.create.prefab_text import create_interface_text
from src.ecs.systems.s_starfield import system_starfield_fall
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator


class MenuScene(Scene):
    """Base de las escenas fuera del juego (título, instrucciones, créditos).

    Pone el fondo de estrellas, que en los menús bajan (LC-EST-04), y los textos
    "title", "subtitle" y "hint" de su JSON si los trae.
    """

    def __init__(self, game_engine, config_path: str) -> None:
        super().__init__(game_engine)
        self._config_path = config_path

    def do_create(self) -> None:
        self._config = ServiceLocator.configs_service.get(self._config_path)
        self._stars_info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.stars_config)
        create_starfield(self.ecs_world, self._stars_info, self.screen_rect)
        for key in ("title", "subtitle", "hint"):
            if key in self._config:
                create_interface_text(self.ecs_world, self._config[key]["text"], self._config[key])
        self.do_create_menu()

    def do_create_menu(self) -> None:
        """Crea lo propio de cada menú."""

    def do_update(self, delta_time: float) -> None:
        system_starfield_fall(self.ecs_world, delta_time, self._stars_info["menu_fall_speed"],
                              pygame.Rect(self.screen_rect), self._stars_info["blink"])
