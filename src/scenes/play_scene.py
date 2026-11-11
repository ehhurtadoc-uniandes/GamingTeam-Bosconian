import pygame

from src.create.prefab_player import create_player
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_enemy_state import system_enemy_state
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_player_movement import system_player_acceleration, system_player_direction
from src.ecs.systems.s_steering import system_steering
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

    def __init__(self, game_engine) -> None:
        super().__init__(game_engine)
        # Se guardan teclas y no acciones: si una dirección tiene varias teclas, soltar una no la apaga.
        self._held_direction_keys: set[tuple[str, int]] = set()

    def do_create(self) -> None:
        self._held_direction_keys.clear()
        player_info = ServiceLocator.configs_service.get(PLAYER_CONFIG)
        size = player_info["size"]
        pos = pygame.Vector2(self.screen_rect.center) - pygame.Vector2(size["w"], size["h"]) / 2
        self._player_entity = create_player(self.ecs_world, player_info, pos)

    def do_update(self, delta_time: float) -> None:
        system_player_acceleration(self.ecs_world, delta_time)
        # Los enemigos persiguen la posición del jugador. El estado va antes que el
        # steering porque ajusta sus pesos; world_size queda en None hasta el wraparound (#7).
        player_pos = self.ecs_world.component_for_entity(self._player_entity, CTransform).pos
        system_enemy_state(self.ecs_world, delta_time, player_pos)
        system_steering(self.ecs_world, delta_time, player_pos)
        system_movement(self.ecs_world, delta_time)

    def do_action(self, action: CInputCommand) -> None:
        if action.name in DIRECTION_COMMANDS:
            held = (action.name, action.key)
            if action.phase == CommandPhase.START:
                self._held_direction_keys.add(held)
            else:
                self._held_direction_keys.discard(held)
            active = {name for name, _ in self._held_direction_keys}
            system_player_direction(self.ecs_world, direction_from_commands(active))

    def do_process_events(self, event: pygame.event.Event) -> None:
        # Al perder el foco pygame puede no enviar el KEYUP; sin esto una flecha quedaría "pegada".
        if event.type == pygame.WINDOWFOCUSLOST:
            self._held_direction_keys.clear()
