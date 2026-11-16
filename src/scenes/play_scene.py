import random
from enum import Enum

import pygame

from src.create.prefab_base import create_bases
from src.create.prefab_camera import create_camera
from src.create.prefab_enemy import create_enemy
from src.create.prefab_enemy_spawner import create_enemy_spawner
from src.create.prefab_hud import create_lives_hud, create_score_hud
from src.create.prefab_minimap import create_minimap
from src.create.prefab_obstacle import create_obstacles
from src.create.prefab_player import create_player
from src.create.prefab_stars import create_starfield
from src.create.prefab_text import create_interface_text
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.create.prefab_explosion import create_explosion_for, destroy_with_explosion
from src.ecs.components.c_enemy import CEnemy, EnemyType
from src.ecs.systems.s_animation import system_animation
from src.ecs.systems.s_camera import get_camera, system_camera, view_top_left
from src.ecs.systems.s_debug_hitboxes import system_debug_hitboxes
from src.ecs.systems.s_debug_labels import system_enemy_labels
from src.ecs.systems.s_enemy_bullet_collision import system_enemy_bullet_collision
from src.ecs.systems.s_enemy_spawner import system_enemy_spawner
from src.ecs.systems.s_enemy_state import system_enemy_state
from src.ecs.systems.s_explosion_burst import system_explosion_burst
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_lives_hud import system_lives_hud
from src.ecs.systems.s_minimap import system_minimap
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_obstacles import system_mine_blast, system_player_bullet_obstacle
from src.ecs.systems.s_offscreen_despawn import system_offscreen_despawn
from src.ecs.systems.s_pause import system_pause_visibility
from src.ecs.systems.s_player_fire import system_player_fire, system_player_weapon_cooldown
from src.ecs.systems.s_player_movement import system_player_acceleration, system_player_direction
from src.ecs.systems.s_score import system_score_hud
from src.ecs.systems.s_starfield import system_star_blink, system_starfield
from src.ecs.systems.s_steering import system_steering
from src.ecs.systems.s_turret import system_turret
from src.ecs.systems.s_wraparound import system_wraparound
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator
from src.utils.wrap import wrap_position, world_size_from_config


def direction_from_commands(active_commands: set[str]) -> pygame.Vector2:
    """Suma las direcciones de los comandos presionados; dos opuestas se anulan."""
    direction_commands = ServiceLocator.constants_service.direction_commands
    direction = pygame.Vector2(0, 0)
    for name in active_commands:
        direction += direction_commands[name]
    return direction


def random_edge_position(screen_rect: pygame.Rect, size: pygame.Vector2) -> pygame.Vector2:
    """Posición al azar pegada a uno de los cuatro bordes de la pantalla, dentro de ella."""
    max_x = screen_rect.width - size.x
    max_y = screen_rect.height - size.y
    side = random.choice(("top", "bottom", "left", "right"))
    if side == "top":
        return pygame.Vector2(random.uniform(0, max_x), 0)
    if side == "bottom":
        return pygame.Vector2(random.uniform(0, max_x), max_y)
    if side == "left":
        return pygame.Vector2(0, random.uniform(0, max_y))
    return pygame.Vector2(max_x, random.uniform(0, max_y))


class PlayState(Enum):
    """Estado de la escena de juego (patrón State). PAUSED congela todo menos el parpadeo de las estrellas."""
    PLAYING = 0
    PAUSED = 1


class PlayScene(Scene):
    """Escena de juego. Crea al jugador; cada área agrega aquí sus entidades y sistemas.

    Con debug.json "enabled", las teclas 1, 2 y 3 crean enemigos I, P y E y se dibuja
    su tipo y estado encima de cada uno.
    """

    def __init__(self, game_engine) -> None:
        super().__init__(game_engine)
        # Índice en levels.json del nivel que se juega; se toma de GameStateService al crear la escena.
        self.level_index = 0
        # Se guardan teclas y no acciones: si una dirección tiene varias teclas, soltar una no la apaga.
        self._held_direction_keys: set[tuple[str, int]] = set()
        self.state = PlayState.PLAYING
        self._pause_text: int | None = None
        self._pause_info: dict = {}
        self._show_hitboxes = False

    def do_create(self) -> None:
        constants = ServiceLocator.constants_service
        self._held_direction_keys.clear()
        self.level_index = ServiceLocator.game_state_service.level_index
        self.state = PlayState.PLAYING
        self._show_hitboxes = False
        self._pause_text = None
        self._pause_info = ServiceLocator.configs_service.get(constants.pause_config)
        world_info = ServiceLocator.configs_service.get(constants.world_config)
        self.world_size = world_size_from_config(world_info)
        self._create_level()
        player_info = ServiceLocator.configs_service.get(constants.player_config)
        size = player_info["size"]
        pos = self._player_start - pygame.Vector2(size["w"], size["h"]) / 2
        self._player_entity = create_player(self.ecs_world, player_info, pos)
        player_center = pos + pygame.Vector2(size["w"], size["h"]) / 2
        create_camera(self.ecs_world, world_info["camera"], self.world_size, player_center)
        self._stars_info = ServiceLocator.configs_service.get(constants.stars_config)
        create_starfield(self.ecs_world, self._stars_info, get_camera(self.ecs_world).viewport)
        self._debug_info = ServiceLocator.configs_service.get(constants.debug_config)
        score_info = ServiceLocator.configs_service.get(constants.score_config)
        create_score_hud(self.ecs_world, score_info["hud"])
        create_lives_hud(self.ecs_world, score_info["lives"]["hud"])
        create_minimap(self.ecs_world, ServiceLocator.configs_service.get(constants.minimap_config))

    def _create_level(self) -> None:
        """Crea las entidades del nivel actual según su JSON: bases, spawner de enemigos y obstáculos.

        El formato del JSON de nivel está en docs/formato-niveles.md.
        """
        constants = ServiceLocator.constants_service
        level_path = ServiceLocator.configs_service.get(constants.levels_config)["levels"][self.level_index]
        level_info = ServiceLocator.configs_service.get(level_path)
        base_info = ServiceLocator.configs_service.get(constants.base_config)
        self._bullet_info = base_info["bullet"]
        self._enemies_info = ServiceLocator.configs_service.get(constants.enemies_config)
        self._spawn_margin = ServiceLocator.configs_service.get(constants.spawner_config)["offscreen_margin"]
        # Sin player_start en el nivel, el jugador empieza en el centro de la pantalla.
        start = level_info.get("player_start")
        self._player_start = (pygame.Vector2(start["x"], start["y"]) if start
                              else pygame.Vector2(self.screen_rect.center))
        try:
            bases = create_bases(self.ecs_world, base_info, level_info)
            create_enemy_spawner(self.ecs_world, level_info)
        except (KeyError, ValueError) as error:
            raise ValueError(f"{level_path}: {error}") from error
        # Los obstáculos no aparecen encima de las bases ni del jugador.
        avoid = [self._player_start] + [self._center_of(base) for base in bases]
        self._obstacles_info = ServiceLocator.configs_service.get(constants.obstacles_config)
        create_obstacles(self.ecs_world, self._obstacles_info, level_info, self.world_size, avoid)

    def _center_of(self, entity: int) -> pygame.Vector2:
        c_t = self.ecs_world.component_for_entity(entity, CTransform)
        c_s = self.ecs_world.component_for_entity(entity, CSurface)
        return c_t.pos + pygame.Vector2(c_s.area.size) / 2

    def do_update(self, delta_time: float) -> None:
        if self.state == PlayState.PAUSED:
            # En pausa nada se mueve; las estrellas siguen brillando quietas (LC-ESC-04.3.2).
            system_star_blink(self.ecs_world, delta_time, self._stars_info["blink"])
            return
        system_player_acceleration(self.ecs_world, delta_time)
        system_player_weapon_cooldown(self.ecs_world, delta_time)
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
        # player_pos ya cambió con el movimiento: se recalcula el centro para la cámara y las explosiones.
        player_center = player_pos + pygame.Vector2(player_size) / 2
        system_camera(self.ecs_world, player_center)
        system_starfield(self.ecs_world, delta_time, get_camera(self.ecs_world), self._stars_info["blink"])
        system_explosion_burst(self.ecs_world, delta_time)
        system_lifetime(self.ecs_world, delta_time)
        # "Salir de la pantalla" es salir de lo que ve la cámara (el área de juego), no de la ventana.
        system_offscreen_despawn(self.ecs_world, camera=get_camera(self.ecs_world))
        system_enemy_bullet_collision(self.ecs_world, self.world_size)
        system_player_bullet_obstacle(self.ecs_world, self._obstacles_info, self.world_size)
        system_animation(self.ecs_world, delta_time)
        # Después de la animación, para que la explosión se borre justo al terminar.
        # Devuelve True si la explosión alcanzó al jugador: su muerte la maneja el área del jugador.
        system_mine_blast(self.ecs_world, self.world_size, player_center)
        # Al final, para que el HUD muestre los puntos sumados en este paso.
        system_score_hud(self.ecs_world)
        system_lives_hud(self.ecs_world)
        system_minimap(self.ecs_world, delta_time, self.world_size)

    def do_draw(self, screen: pygame.Surface) -> None:
        super().do_draw(screen)
        # En pausa los enemigos no se ven, así que tampoco sus etiquetas.
        if not self._debug_info["enabled"] or self.state == PlayState.PAUSED:
            return
        font = ServiceLocator.fonts_service.get(self._debug_info["font"], self._debug_info["font_size"])
        c = self._debug_info["label_color"]
        color = pygame.Color(c["r"], c["g"], c["b"])
        system_enemy_labels(self.ecs_world, screen, font, color, get_camera(self.ecs_world))
        if self._show_hitboxes:
            h = self._debug_info["hitbox_color"]
            system_debug_hitboxes(self.ecs_world, screen, pygame.Color(h["r"], h["g"], h["b"]),
                                  get_camera(self.ecs_world))
        help_pos = self._debug_info["help_pos"]
        help_text = ServiceLocator.texts_service.get(font, self._debug_info["help_text"], color)
        screen.blit(help_text, (help_pos["x"], help_pos["y"]))

    def do_action(self, action: CInputCommand) -> None:
        constants = ServiceLocator.constants_service
        if action.name == constants.pause_command:
            if action.phase == CommandPhase.START:
                self.toggle_pause()
        elif action.name in constants.direction_commands:
            # También en pausa: así, al reanudar, la dirección es la de las flechas que siguen presionadas.
            held = (action.name, action.key)
            if action.phase == CommandPhase.START:
                self._held_direction_keys.add(held)
            else:
                self._held_direction_keys.discard(held)
            active = {name for name, _ in self._held_direction_keys}
            system_player_direction(self.ecs_world, direction_from_commands(active))
        elif self.state == PlayState.PAUSED:
            # En pausa se ignora todo lo demás (disparo, depuración).
            return
        elif action.name == constants.fire_command:
            if action.phase == CommandPhase.START:
                system_player_fire(self.ecs_world)
        elif action.name == constants.debug_hitboxes_command:
            if action.phase == CommandPhase.START and self._debug_info["enabled"]:
                self._show_hitboxes = not self._show_hitboxes
        elif action.name == constants.debug_explode_command:
            if action.phase == CommandPhase.START and self._debug_info["enabled"]:
                create_explosion_for(self.ecs_world, self._player_entity)
                for enemy, _ in self.ecs_world.get_component(CEnemy):
                    destroy_with_explosion(self.ecs_world, enemy)
        elif action.name in constants.debug_spawn_commands:
            if action.phase == CommandPhase.START and self._debug_info["enabled"]:
                self._spawn_debug_enemy(EnemyType(constants.debug_spawn_commands[action.name]))

    def toggle_pause(self) -> None:
        """Pausa o reanuda (LC-ESC-04.3): esconde el mundo y el minimapa y muestra "JUEGO PAUSADO"."""
        if self.state == PlayState.PLAYING:
            self.state = PlayState.PAUSED
            system_pause_visibility(self.ecs_world, paused=True)
            text_info = self._pause_info["text"]
            self._pause_text = create_interface_text(self.ecs_world, text_info["text"], text_info)
        else:
            self.state = PlayState.PLAYING
            system_pause_visibility(self.ecs_world, paused=False)
            self.ecs_world.delete_entity(self._pause_text, immediate=True)
            self._pause_text = None

    def do_process_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.JOYDEVICEREMOVED:
            self._held_direction_keys.clear()
        # Al perder el foco pygame puede no enviar el KEYUP; sin esto una flecha quedaría "pegada".
        if event.type == pygame.WINDOWFOCUSLOST:
            self._held_direction_keys.clear()
            # Si el jugador se va a otra ventana, el juego no sigue sin él.
            if self.state == PlayState.PLAYING:
                self.toggle_pause()

    def _spawn_debug_enemy(self, enemy_type: EnemyType) -> int:
        enemies_info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.enemies_config)
        size = enemies_info[enemy_type.value]["size"]
        camera = get_camera(self.ecs_world)
        view = pygame.Rect((0, 0), camera.viewport.size)
        # Borde de lo que se ve, pasado a coordenadas de mundo.
        pos = view_top_left(camera) + random_edge_position(view, pygame.Vector2(size["w"], size["h"]))
        wrap_position(pos, self.world_size)
        return create_enemy(self.ecs_world, enemies_info, pos, enemy_type)
