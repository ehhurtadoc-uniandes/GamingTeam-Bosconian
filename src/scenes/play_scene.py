import pygame

from src.create.prefab_player import create_player
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_player_movement import system_player_acceleration, system_player_direction
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator

PLAYER_CONFIG = "assets/cfg/player.json"

DIRECTION_COMMANDS = {
    "PLAYER_UP": pygame.Vector2(0, -1),
    "PLAYER_DOWN": pygame.Vector2(0, 1),
    "PLAYER_LEFT": pygame.Vector2(-1, 0),
    "PLAYER_RIGHT": pygame.Vector2(1, 0),
}


def direction_from_commands(active_commands: set[str]) -> pygame.Vector2:
    """Suma las direcciones de los comandos presionados; dos opuestas se anulan."""
    direction = pygame.Vector2(0, 0)
    for name in active_commands:
        direction += DIRECTION_COMMANDS[name]
    return direction


class PlayScene(Scene):
    """Escena de juego. Por ahora solo crea al jugador; cada área agrega aquí sus entidades y sistemas."""

    def do_create(self) -> None:
        self._active_directions: set[str] = set()
        player_info = ServiceLocator.configs_service.get(PLAYER_CONFIG)
        size = player_info["size"]
        pos = pygame.Vector2(self.screen_rect.center) - pygame.Vector2(size["w"], size["h"]) / 2
        create_player(self.ecs_world, player_info, pos)

    def do_update(self, delta_time: float) -> None:
        system_player_acceleration(self.ecs_world, delta_time)
        system_movement(self.ecs_world, delta_time)

    def do_action(self, action: CInputCommand) -> None:
        if action.name in DIRECTION_COMMANDS:
            if action.phase == CommandPhase.START:
                self._active_directions.add(action.name)
            else:
                self._active_directions.discard(action.name)
            system_player_direction(self.ecs_world, direction_from_commands(self._active_directions))
