import pygame

from src.create.prefab_player import create_player
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_player_movement import system_player_acceleration
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator

PLAYER_CONFIG = "assets/cfg/player.json"


class PlayScene(Scene):
    """Escena de juego. Por ahora solo crea al jugador; cada área agrega aquí sus entidades y sistemas."""

    def do_create(self) -> None:
        player_info = ServiceLocator.configs_service.get(PLAYER_CONFIG)
        size = player_info["size"]
        pos = pygame.Vector2(self.screen_rect.center) - pygame.Vector2(size["w"], size["h"]) / 2
        create_player(self.ecs_world, player_info, pos)

    def do_update(self, delta_time: float) -> None:
        system_player_acceleration(self.ecs_world, delta_time)
        system_movement(self.ecs_world, delta_time)
