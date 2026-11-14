import random

import pygame

from src.create.prefab_base import create_bases
from src.create.prefab_camera import create_camera
from src.create.prefab_enemy import create_enemy
from src.create.prefab_enemy_spawner import create_enemy_spawner
from src.create.prefab_hud import create_score_hud
from src.create.prefab_player import create_player
from src.create.prefab_stars import create_starfield
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_enemy import EnemyType
from src.ecs.systems.s_camera import get_camera, system_camera, view_top_left
from src.ecs.systems.s_debug_labels import system_enemy_labels
from src.ecs.systems.s_enemy_bullet_collision import system_enemy_bullet_collision
from src.ecs.systems.s_enemy_spawner import system_enemy_spawner
from src.ecs.systems.s_enemy_state import system_enemy_state
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_player_movement import system_player_acceleration, system_player_direction
from src.ecs.systems.s_score import system_score_hud
from src.ecs.systems.s_starfield import system_starfield
from src.ecs.systems.s_steering import system_steering
from src.ecs.systems.s_turret import system_turret
from src.ecs.systems.s_wraparound import system_wraparound
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator
from src.utils.wrap import wrap_position, world_size_from_config

PLAYER_CONFIG = "assets/cfg/player.json"
ENEMIES_CONFIG = "assets/cfg/enemies.json"
DEBUG_CONFIG = "assets/cfg/debug.json"
BASE_CONFIG = "assets/cfg/base.json"
LEVELS_CONFIG = "assets/cfg/levels.json"
WORLD_CONFIG = "assets/cfg/world.json"
STARS_CONFIG = "assets/cfg/stars.json"
SCORE_CONFIG = "assets/cfg/score.json"
SPAWNER_CONFIG = "assets/cfg/spawner.json"

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


# Con el modo de depuración, estas teclas crean enemigos a pedido, además de los del spawner (#28).
DEBUG_SPAWN_COMMANDS = {
    "DEBUG_SPAWN_I": EnemyType.I,
    "DEBUG_SPAWN_P": EnemyType.P,
    "DEBUG_SPAWN_E": EnemyType.E,
}


def random_edge_position(screen_rect: pygame.Rect, size: pygame.Vector2,
                         rng: random.Random | None = None) -> pygame.Vector2:
    """Posición al azar pegada a uno de los cuatro bordes de la pantalla, dentro de ella."""
    rng = rng or random
    max_x = screen_rect.width - size.x
    max_y = screen_rect.height - size.y
    side = rng.choice(("top", "bottom", "left", "right"))
    if side == "top":
        return pygame.Vector2(rng.uniform(0, max_x), 0)
    if side == "bottom":
        return pygame.Vector2(rng.uniform(0, max_x), max_y)
    if side == "left":
        return pygame.Vector2(0, rng.uniform(0, max_y))
    return pygame.Vector2(max_x, rng.uniform(0, max_y))


class PlayScene(Scene):
    """Escena de juego. Crea al jugador; cada área agrega aquí sus entidades y sistemas.

    Con debug.json "enabled", las teclas 1, 2 y 3 crean enemigos I, P y E y se dibuja
    su tipo y estado encima de cada uno.
    """

    def __init__(self, game_engine) -> None:
        super().__init__(game_engine)
        # Índice en levels.json del nivel que se juega. Pasar de nivel (#26) lo avanzará.
        self.level_index = 0
        # Se guardan teclas y no acciones: si una dirección tiene varias teclas, soltar una no la apaga.
        self._held_direction_keys: set[tuple[str, int]] = set()

    def do_create(self) -> None:
        self._held_direction_keys.clear()
        # Las estrellas se crean primero; igual system_rendering las dibuja siempre debajo (CTagBackground).
        world_info = ServiceLocator.configs_service.get(WORLD_CONFIG)
        self.world_size = world_size_from_config(world_info)
        self._create_level()
        player_info = ServiceLocator.configs_service.get(PLAYER_CONFIG)
        size = player_info["size"]
        pos = pygame.Vector2(self.screen_rect.center) - pygame.Vector2(size["w"], size["h"]) / 2
        self._player_entity = create_player(self.ecs_world, player_info, pos)
        player_center = pos + pygame.Vector2(size["w"], size["h"]) / 2
        create_camera(self.ecs_world, world_info["camera"], self.world_size, player_center)
        self._stars_info = ServiceLocator.configs_service.get(STARS_CONFIG)
        create_starfield(self.ecs_world, self._stars_info, get_camera(self.ecs_world).viewport)
        self._debug_info = ServiceLocator.configs_service.get(DEBUG_CONFIG)
        create_score_hud(self.ecs_world, ServiceLocator.configs_service.get(SCORE_CONFIG)["hud"])

    def _create_level(self) -> None:
        """Crea las entidades del nivel actual según su JSON: las bases y el spawner de enemigos."""
        level_path = ServiceLocator.configs_service.get(LEVELS_CONFIG)["levels"][self.level_index]
        level_info = ServiceLocator.configs_service.get(level_path)
        base_info = ServiceLocator.configs_service.get(BASE_CONFIG)
        self._bullet_info = base_info["bullet"]
        self._enemies_info = ServiceLocator.configs_service.get(ENEMIES_CONFIG)
        self._spawn_margin = ServiceLocator.configs_service.get(SPAWNER_CONFIG)["offscreen_margin"]
        try:
            create_bases(self.ecs_world, base_info, level_info)
            create_enemy_spawner(self.ecs_world, level_info)
        except (KeyError, ValueError) as error:
            raise ValueError(f"{level_path}: {error}") from error

    def do_update(self, delta_time: float) -> None:
        system_player_acceleration(self.ecs_world, delta_time)
        # Los enemigos persiguen la posición del jugador. El estado va antes que el
        # steering porque ajusta sus pesos. Con world_size persiguen cruzando los bordes.
        player_pos = self.ecs_world.component_for_entity(self._player_entity, CTransform).pos
        # Los enemigos nuevos salen fuera de lo que ve la cámara (aún en la posición del paso anterior).
        system_enemy_spawner(self.ecs_world, delta_time, get_camera(self.ecs_world),
                             self._enemies_info, self._spawn_margin)
        system_enemy_state(self.ecs_world, delta_time, player_pos, self.world_size)
        system_steering(self.ecs_world, delta_time, player_pos, self.world_size)
        # Las torretas disparan antes del movimiento para que la bala nueva avance en este frame.
        player_size = self.ecs_world.component_for_entity(self._player_entity, CSurface).area.size
        player_center = player_pos + pygame.Vector2(player_size) / 2
        system_turret(self.ecs_world, delta_time, player_center, self._bullet_info, self.world_size)
        system_movement(self.ecs_world, delta_time)
        # Justo después de mover: lo que salió por un borde vuelve por el opuesto.
        system_wraparound(self.ecs_world, self.world_size)
        # La cámara sigue al jugador ya movido, para que no se vea un frame atrasada.
        system_camera(self.ecs_world, player_pos + pygame.Vector2(player_size) / 2)
        system_starfield(self.ecs_world, delta_time, get_camera(self.ecs_world), self._stars_info["blink"])
        # "Salir de la pantalla" es salir de lo que ve la cámara.
        system_lifetime(self.ecs_world, delta_time, camera=get_camera(self.ecs_world))
        system_enemy_bullet_collision(self.ecs_world)
        # Al final, para que el HUD muestre los puntos sumados en este paso.
        system_score_hud(self.ecs_world, self.session)

    def do_draw(self, screen: pygame.Surface) -> None:
        super().do_draw(screen)
        if not self._debug_info["enabled"]:
            return
        font = ServiceLocator.fonts_service.get(self._debug_info["font"], self._debug_info["font_size"])
        c = self._debug_info["label_color"]
        color = pygame.Color(c["r"], c["g"], c["b"])
        system_enemy_labels(self.ecs_world, screen, font, color, get_camera(self.ecs_world))
        help_pos = self._debug_info["help_pos"]
        screen.blit(font.render(self._debug_info["help_text"], False, color), (help_pos["x"], help_pos["y"]))

    def do_action(self, action: CInputCommand) -> None:
        if action.name in DEBUG_SPAWN_COMMANDS:
            if action.phase == CommandPhase.START and self._debug_info["enabled"]:
                self._spawn_debug_enemy(DEBUG_SPAWN_COMMANDS[action.name])
        elif action.name in DIRECTION_COMMANDS:
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

    def _spawn_debug_enemy(self, enemy_type: EnemyType) -> int:
        enemies_info = ServiceLocator.configs_service.get(ENEMIES_CONFIG)
        size = enemies_info[enemy_type.value]["size"]
        camera = get_camera(self.ecs_world)
        view = pygame.Rect((0, 0), camera.viewport.size)
        # Borde de lo que se ve, pasado a coordenadas de mundo.
        pos = view_top_left(camera) + random_edge_position(view, pygame.Vector2(size["w"], size["h"]))
        wrap_position(pos, self.world_size)
        return create_enemy(self.ecs_world, enemies_info, pos, enemy_type)
