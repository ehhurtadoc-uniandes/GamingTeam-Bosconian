from typing import TYPE_CHECKING

import esper
import pygame

from src.ecs.systems.s_rendering import system_rendering

if TYPE_CHECKING:
    from src.engine.game_engine import GameEngine


class Scene:
    """Escena base (patrón Scene). Cada escena tiene su propio mundo ECS.

    Las escenas concretas sobrescriben los métodos do_*.
    """

    def __init__(self, game_engine: "GameEngine") -> None:
        self.ecs_world = esper.World()
        self._game_engine = game_engine
        self.screen_rect = game_engine.screen.get_rect()

    def start(self) -> None:
        self.do_create()

    def simulate(self, delta_time: float) -> None:
        self.do_update(delta_time)
        # Sin world.process(), las entidades borradas no se limpian solas.
        self.ecs_world._clear_dead_entities()

    def clean(self) -> None:
        self.do_clean()
        self.ecs_world.clear_database()

    def switch_scene(self, new_scene_name: str) -> None:
        self._game_engine.switch_scene(new_scene_name)

    def do_create(self) -> None:
        """Crea las entidades de la escena."""

    def do_update(self, delta_time: float) -> None:
        """Llama a los sistemas de la escena en cada paso fijo."""

    def do_draw(self, screen: pygame.Surface) -> None:
        system_rendering(self.ecs_world, screen)

    def do_process_events(self, event: pygame.event.Event) -> None:
        """Recibe cada evento de pygame."""

    def do_clean(self) -> None:
        """Libera lo que la escena haya creado fuera de su mundo ECS."""
