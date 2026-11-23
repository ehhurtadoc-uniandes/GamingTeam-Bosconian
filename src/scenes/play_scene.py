import random
from enum import Enum

import pygame

from src.create.prefab_alert import create_alert, create_alert_hud, load_alert_hud
from src.create.prefab_base import create_bases
from src.create.prefab_camera import create_camera
from src.create.prefab_enemy import create_enemy
from src.create.prefab_enemy_spawner import create_enemy_spawner
from src.create.prefab_hud import create_ability_hud, create_lives_hud, create_score_hud
from src.create.prefab_menu import create_menu, create_text_lines
from src.create.prefab_minimap import create_minimap
from src.create.prefab_obstacle import create_obstacles
from src.create.prefab_pickup import create_pickup_spawner
from src.create.prefab_player import create_player
from src.create.prefab_round import create_round_hud
from src.create.prefab_special_message import create_special_shot_message
from src.create.prefab_stars import create_starfield
from src.create.prefab_text import create_interface_text
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_menu_item import CMenuItem
from src.ecs.components.c_player_dead import CPlayerDead
from src.ecs.components.c_special_shot import CSpecialShot
from src.ecs.components.tags.c_tag_hide_on_pause import CTagHideOnPause
from src.ecs.components.tags.c_tag_pause_overlay import CTagPauseOverlay
from src.create.prefab_explosion import create_explosion_for, destroy_with_explosion
from src.ecs.components.c_enemy import CEnemy, EnemyType
from src.ecs.systems.s_alert import (alert_allows_launch, alert_rate_multiplier, get_alert, system_alert,
                                    system_alert_hud, system_alert_speed)
from src.ecs.systems.s_animation import system_animation
from src.ecs.systems.s_base_core import system_base_core
from src.ecs.systems.s_base_destruction import system_player_bullet_base
from src.ecs.systems.s_camera import get_camera, system_camera, view_top_left
from src.ecs.systems.s_debug_hitboxes import system_debug_hitboxes
from src.ecs.systems.s_debug_labels import system_enemy_labels
from src.ecs.systems.s_input import reset_gamepad_commands
from src.ecs.systems.s_enemy_bullet_collision import system_enemy_bullet_collision
from src.ecs.systems.s_enemy_bounce import system_enemy_bounce
from src.ecs.systems.s_enemy_spawner import system_enemy_spawner
from src.ecs.systems.s_enemy_state import system_enemy_state
from src.ecs.systems.s_explosion_burst import system_explosion_burst
from src.ecs.systems.s_level import level_cleared
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_lives_hud import system_lives_hud
from src.ecs.systems.s_minimap import system_minimap
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_obstacles import (system_enemy_obstacle, system_mine_blast, system_obstacle_bounce,
                                        system_player_bullet_obstacle)
from src.ecs.systems.s_offscreen_despawn import system_offscreen_despawn
from src.ecs.systems.s_pause import system_pause_visibility
from src.ecs.systems.s_menu import get_menu, move_menu_selection, selected_action, system_menu_highlight
from src.ecs.systems.s_player_death import (is_vulnerable, kill_player, system_player_death,
                                           system_player_invulnerability, system_player_respawn)
from src.ecs.systems.s_player_ability import (system_ability_hud, system_pickup_collection,
                                             system_pickup_spawner, system_player_ability,
                                             system_player_ability_activate)
from src.ecs.systems.s_player_bullet_enemy import system_player_bullet_enemy
from src.ecs.systems.s_player_fire import system_player_fire, system_player_weapon_cooldown
from src.ecs.systems.s_player_sprite import system_player_sprite
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
    """Estado de la escena de juego (patrón State).

    - STARTING: inicio del nivel (LC-ESC-04.2). Se ve "BLAST OFF!", suena su sonido y nada se mueve.
    - PLAYING: el juego corre.
    - PAUSED: todo se congela menos el parpadeo de las estrellas y se ve el menú de pausa.
    - PAUSED_INFO: sigue en pausa, mostrando las instrucciones o los créditos (LC-ESC-04.3.5).
    - CLEARED: ya no quedan bases (LC-ESC-04.4). Se dejan terminar las explosiones y se pasa de nivel.
    """
    PLAYING = 0
    PAUSED = 1
    PAUSED_INFO = 2
    STARTING = 3
    CLEARED = 4


class PlayScene(Scene):
    """Escena de juego. Crea al jugador; cada área agrega aquí sus entidades y sistemas.

    Con debug.json "enabled", las teclas 1, 2 y 3 crean enemigos I, P y E. La tecla H
    muestra las hitboxes, la ayuda de las teclas y el tipo y estado de cada enemigo;
    sin H el juego se ve como el original.
    """

    def __init__(self, game_engine) -> None:
        super().__init__(game_engine)
        # Índice en levels.json del nivel que se juega; se toma de GameStateService al crear la escena.
        self.level_index = 0
        # Se guardan teclas y no acciones: si una dirección tiene varias teclas, soltar una no la apaga.
        self._held_direction_keys: set[tuple[str, int]] = set()
        self.state = PlayState.PLAYING
        self._pause_info: dict = {}
        self._blast_off_info: dict = {}
        self._cheats_info: dict = {}
        # Aviso de trampa en pantalla (uno a la vez) y el que se muestra al empezar la ronda
        # siguiente, para la trampa que cambia de ronda: (trampa, valores del texto).
        self._cheat_message: int | None = None
        self._pending_cheat_message: tuple[str, dict] | None = None
        # Modo trampa (#40): nombre de la trampa (ConstantsService.cheat_commands) -> qué hace.
        self._cheat_actions = {
            "NEXT_LEVEL": self._cheat_next_level,
            "INVINCIBLE": self._cheat_invincible,
            "SPECIAL_SHOT": self._cheat_special_shot,
            "SCORE": self._cheat_score,
        }
        self._blast_off_time = 0.0
        self._blast_off_text: int | None = None
        # Opción del menú de pausa a la que se vuelve desde las instrucciones o los créditos.
        self._pause_selected = 0
        # El evento actual ya cambió la pausa. Escape es PAUSE y MENU_BACK, y Z (o el botón A) es
        # disparo y MENU_ACCEPT: sin esto, un mismo toque haría dos cosas (p. ej. reanudar y disparar).
        # Se marca el evento y no la tecla porque en el gamepad cada comando tiene su propia clave.
        self._event_consumed = False
        self._show_hitboxes = False
        self._has_special_shot = False
        self._ability_info: dict | None = None
        self._respawn_info: dict = {}
        self._player_spawn_pos = pygame.Vector2(0, 0)
        self._alert_hud_info: dict = {}
        self._clear_time = 0.0
        # Escena pedida en el último switch_scene: al volver a crear la escena de juego (paso de
        # ronda o trampa N) se conservan las direcciones presionadas; viniendo de otra escena, no.
        self._switching_to: str | None = None

    def switch_scene(self, new_scene_name: str) -> None:
        self._switching_to = new_scene_name
        super().switch_scene(new_scene_name)

    def do_create(self) -> None:
        constants = ServiceLocator.constants_service
        keep_directions = self._switching_to == constants.play_scene
        self._switching_to = None
        if not keep_directions:
            self._held_direction_keys.clear()
        self.level_index = ServiceLocator.game_state_service.level_index
        self.state = PlayState.PLAYING
        # Cada ronda con su música (#38): se turnan las pistas de level_music.
        ServiceLocator.sounds_service.play_music(ServiceLocator.sounds_service.level_music(self.level_index))
        self._blast_off_info = ServiceLocator.configs_service.get(constants.blast_off_config)
        self._cheats_info = ServiceLocator.configs_service.get(constants.cheats_config)
        self._show_hitboxes = False
        self._pause_selected = 0
        self._event_consumed = False
        self._pause_info = ServiceLocator.configs_service.get(constants.pause_config)
        world_info = ServiceLocator.configs_service.get(constants.world_config)
        self.world_size = world_size_from_config(world_info)
        self._create_level()
        player_info = ServiceLocator.configs_service.get(constants.player_config)
        self._respawn_info = player_info["respawn"]
        self._ability_info = player_info.get("ability")
        size = player_info["size"]
        pos = self._player_start - pygame.Vector2(size["w"], size["h"]) / 2
        self._player_spawn_pos = pygame.Vector2(pos)
        # El disparo especial lo da el nivel o la trampa (#40); el mensaje solo sale si lo da el nivel.
        special_cheat = ServiceLocator.cheats_service.is_active(constants.cheat_special_shot)
        self._player_entity = create_player(self.ecs_world, player_info, pos,
                                            self._has_special_shot or special_cheat)
        if self._has_special_shot:
            create_special_shot_message(self.ecs_world, player_info["special_shot"])
        if keep_directions:
            self._restore_held_directions()
        player_center = pos + pygame.Vector2(size["w"], size["h"]) / 2
        create_camera(self.ecs_world, world_info["camera"], self.world_size, player_center)
        self._stars_info = ServiceLocator.configs_service.get(constants.stars_config)
        create_starfield(self.ecs_world, self._stars_info, get_camera(self.ecs_world).viewport)
        self._debug_info = ServiceLocator.configs_service.get(constants.debug_config)
        score_info = ServiceLocator.configs_service.get(constants.score_config)
        create_score_hud(self.ecs_world, score_info["hud"])
        create_lives_hud(self.ecs_world, score_info["lives"]["hud"])
        if self._ability_info is not None:
            create_ability_hud(self.ecs_world, self._ability_info["hud"])
        create_minimap(self.ecs_world, ServiceLocator.configs_service.get(constants.minimap_config))
        create_alert_hud(self.ecs_world, self._alert_hud_info)
        self._levels_info = ServiceLocator.configs_service.get(constants.levels_config)
        # La ronda se muestra desde 1; level_index empieza en 0.
        create_round_hud(self.ecs_world, self._levels_info["round_hud"], self.level_index + 1)
        self._start_blast_off()
        self._cheat_message = None
        if self._pending_cheat_message is not None:
            cheat, values = self._pending_cheat_message
            self._pending_cheat_message = None
            self._show_cheat_message(cheat, **values)

    def _restore_held_directions(self) -> None:
        """Las flechas que seguían presionadas al cambiar de ronda mueven a la nave de la ronda nueva.

        Los comandos del mundo nuevo empiezan sin presionar: se marcan en START para que el
        KEYUP (o el regreso del stick al centro) que llegue después los suelte.
        """
        c_input: CInputCommand
        for _, c_input in self.ecs_world.get_component(CInputCommand):
            if (c_input.name, c_input.key) in self._held_direction_keys:
                c_input.phase = CommandPhase.START
        self._update_player_direction()

    def _create_level(self) -> None:
        """Crea las entidades del nivel actual según su JSON: bases, spawner de enemigos y obstáculos.

        El formato del JSON de nivel está en docs/formato-niveles.md.
        """
        constants = ServiceLocator.constants_service
        level_path = ServiceLocator.configs_service.get(constants.levels_config)["levels"][self.level_index]
        level_info = ServiceLocator.configs_service.get(level_path)
        self._has_special_shot = level_info.get("special", False)
        base_info = ServiceLocator.configs_service.get(constants.base_config)
        self._bullet_info = base_info["bullet"]
        self._base_points = base_info["points"]
        self._enemies_info = ServiceLocator.configs_service.get(constants.enemies_config)
        self._spawn_margin = ServiceLocator.configs_service.get(constants.spawner_config)["offscreen_margin"]
        # Sin player_start en el nivel, el jugador empieza en el centro de la pantalla.
        start = level_info.get("player_start")
        self._player_start = (pygame.Vector2(start["x"], start["y"]) if start
                              else pygame.Vector2(self.screen_rect.center))
        try:
            bases = create_bases(self.ecs_world, base_info, level_info)
            create_enemy_spawner(self.ecs_world, level_info)
            create_pickup_spawner(self.ecs_world, level_info)
        except (KeyError, ValueError) as error:
            raise ValueError(f"{level_path}: {error}") from error
        # La alerta empieza en VERDE con el tiempo en cero cada vez que se crea el nivel (#29).
        # Sus errores ya nombran el archivo: alerts.json o el bloque "alert" del nivel.
        alerts_info = ServiceLocator.configs_service.get(constants.alerts_config)
        self._alert_hud_info = load_alert_hud(alerts_info, constants.alerts_config)
        create_alert(self.ecs_world, alerts_info, constants.alerts_config, level_info, level_path)
        # Los obstáculos no aparecen encima de las bases ni del jugador. Las bases cuentan por su cuerpo.
        bases_areas = [(self._center_of(base),
                        pygame.Vector2(self.ecs_world.component_for_entity(base, CSurface).area.size))
                       for base in bases]
        self._obstacles_info = ServiceLocator.configs_service.get(constants.obstacles_config)
        create_obstacles(self.ecs_world, self._obstacles_info, level_info, self.world_size,
                         [self._player_start], bases_areas)

    def _center_of(self, entity: int) -> pygame.Vector2:
        c_t = self.ecs_world.component_for_entity(entity, CTransform)
        c_s = self.ecs_world.component_for_entity(entity, CSurface)
        return c_t.pos + pygame.Vector2(c_s.area.size) / 2

    def do_update(self, delta_time: float) -> None:
        if self.state == PlayState.STARTING:
            self._update_blast_off(delta_time)
            return
        if self.state == PlayState.CLEARED:
            self._update_level_clear(delta_time)
            return
        if self.state != PlayState.PLAYING:
            # En pausa nada se mueve; las estrellas siguen brillando quietas (LC-ESC-04.3.2).
            system_star_blink(self.ecs_world, delta_time, self._stars_info["blink"])
            if self.state == PlayState.PAUSED:
                system_menu_highlight(self.ecs_world)
            return
        constants = ServiceLocator.constants_service
        # Al principio: si reaparece en el inicio, los enemigos ya lo persiguen ahí en este paso.
        if system_player_respawn(self.ecs_world, delta_time, self._respawn_info, self._player_spawn_pos):
            self.switch_scene(constants.defeat_scene)
        system_player_acceleration(self.ecs_world, delta_time)
        system_player_weapon_cooldown(self.ecs_world, delta_time)
        system_player_sprite(self.ecs_world)
        # Los enemigos persiguen la posición del jugador. El estado va antes que el
        # steering porque ajusta sus pesos. Con world_size persiguen cruzando los bordes.
        player_pos = self.ecs_world.component_for_entity(self._player_entity, CTransform).pos
        player_size = self.ecs_world.component_for_entity(self._player_entity, CSurface).area.size
        # La cámara ya está centrada en el jugador, salvo que acabe de reaparecer en el inicio:
        # se centra antes del spawner para que los enemigos nuevos no salgan dentro de la pantalla.
        system_camera(self.ecs_world, player_pos + pygame.Vector2(player_size) / 2)
        # La alerta va antes del spawner y de los núcleos: sus cambios ya rigen en este paso.
        # Una base destruida en el paso anterior la pone aquí en VERDE.
        system_alert(self.ecs_world, delta_time)
        # Los enemigos nuevos salen fuera de lo que ve la cámara (centrada en el jugador antes de moverse).
        system_enemy_spawner(self.ecs_world, delta_time, get_camera(self.ecs_world),
                             self._enemies_info, self._spawn_margin)
        # Los núcleos lanzan sus E antes del estado, para que el E nuevo apunte (AIM) en este paso.
        alert = get_alert(self.ecs_world)
        system_base_core(self.ecs_world, delta_time, self._enemies_info,
                         alert_allows_launch(alert), alert_rate_multiplier(alert))
        # En ROJA, los enemigos vivos y los recién creados van más rápido antes de decidir su estado.
        system_alert_speed(self.ecs_world)
        system_enemy_state(self.ecs_world, delta_time, player_pos, self.world_size)
        system_steering(self.ecs_world, delta_time, player_pos, self.world_size)
        # Las torretas disparan antes del movimiento para que la bala nueva avance en este frame.
        player_center = player_pos + pygame.Vector2(player_size) / 2
        system_turret(self.ecs_world, delta_time, player_center, self._bullet_info, self.world_size)
        system_movement(self.ecs_world, delta_time)
        system_enemy_bounce(self.ecs_world, self.world_size)
        system_obstacle_bounce(self.ecs_world, self.world_size)
        # Justo después de mover: lo que salió por un borde vuelve por el opuesto.
        system_wraparound(self.ecs_world, self.world_size)
        if self._ability_info is not None:
            system_player_ability(self.ecs_world, delta_time, self._ability_info)
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
        system_enemy_obstacle(self.ecs_world, self._obstacles_info, self.world_size)
        # Después de las balas de torreta (un enemigo que ya mató una torreta no da puntos) y de los
        # obstáculos. Antes de la muerte del jugador: si la bala mata al enemigo que lo tocaba, sobrevive.
        system_player_bullet_enemy(self.ecs_world, self.world_size)
        # Después de los obstáculos y los enemigos: una bala que ya se gastó en uno no daña la base.
        system_player_bullet_base(self.ecs_world, self._base_points, self.world_size)
        if self._ability_info is not None:
            system_pickup_spawner(self.ecs_world, delta_time, self._ability_info["pickup"], self.world_size,
                                  player_center)
            system_pickup_collection(self.ecs_world, self.world_size)
        system_animation(self.ecs_world, delta_time)
        # Después de la animación, para que la explosión se borre justo al terminar.
        # Devuelve True si la explosión alcanzó al jugador: su muerte la maneja el área del jugador.
        player_hit_by_blast = system_mine_blast(self.ecs_world, self.world_size, player_center)
        system_player_death(self.ecs_world, self._respawn_info, self._obstacles_info, self.world_size)
        if player_hit_by_blast and is_vulnerable(self.ecs_world, self._player_entity):
            kill_player(self.ecs_world, self._player_entity, self._respawn_info)
        system_player_invulnerability(self.ecs_world, delta_time, self._respawn_info)
        # Al final, para que el HUD muestre los puntos sumados en este paso.
        system_score_hud(self.ecs_world)
        system_lives_hud(self.ecs_world)
        if self._ability_info is not None:
            system_ability_hud(self.ecs_world, self._ability_info["hud"])
        system_alert_hud(self.ecs_world)
        system_minimap(self.ecs_world, delta_time, self.world_size)
        # Si el jugador murió sin vidas, la partida terminó aunque haya caído la última base
        # (p. ej. con una bala que seguía en vuelo): se va a la derrota, no a la siguiente ronda.
        if level_cleared(self.ecs_world) and not self._game_over_pending():
            self.state = PlayState.CLEARED
            self._clear_time = self._levels_info["clear_delay"]
            ServiceLocator.sounds_service.play_effect("LEVEL_CLEAR")

    def _game_over_pending(self) -> bool:
        c_dead: CPlayerDead
        return any(c_dead.game_over for _, c_dead in self.ecs_world.get_component(CPlayerDead))

    def _update_level_clear(self, delta_time: float) -> None:
        """Sin bases: las explosiones terminan de animarse y, pasado clear_delay, se pasa de nivel."""
        system_star_blink(self.ecs_world, delta_time, self._stars_info["blink"])
        system_explosion_burst(self.ecs_world, delta_time)
        system_animation(self.ecs_world, delta_time)
        system_lifetime(self.ecs_world, delta_time)
        system_score_hud(self.ecs_world)
        system_minimap(self.ecs_world, delta_time, self.world_size)
        self._clear_time -= delta_time
        if self._clear_time <= 0:
            self.next_level()

    def next_level(self) -> None:
        """Pasa a la siguiente ronda (#26). El puntaje y las vidas siguen en GameStateService.

        Después de la última ronda va a la escena de victoria (#36) y la próxima partida
        vuelve a empezar desde la primera ronda.
        """
        constants = ServiceLocator.constants_service
        game_state = ServiceLocator.game_state_service
        game_state.level_index += 1
        if game_state.level_index < len(self._levels_info["levels"]):
            self.switch_scene(constants.play_scene)
        else:
            game_state.reset_round()
            self.switch_scene(constants.victory_scene)

    def do_draw(self, screen: pygame.Surface) -> None:
        super().do_draw(screen)
        # En pausa los enemigos no se ven, así que tampoco sus etiquetas.
        if not self._debug_info["enabled"] or self.state != PlayState.PLAYING or not self._show_hitboxes:
            return
        font = ServiceLocator.fonts_service.get(self._debug_info["font"], self._debug_info["font_size"])
        c = self._debug_info["label_color"]
        color = pygame.Color(c["r"], c["g"], c["b"])
        system_enemy_labels(self.ecs_world, screen, font, color, get_camera(self.ecs_world))
        h = self._debug_info["hitbox_color"]
        system_debug_hitboxes(self.ecs_world, screen, pygame.Color(h["r"], h["g"], h["b"]),
                              get_camera(self.ecs_world))
        help_pos = self._debug_info["help_pos"]
        for i, line in enumerate(self._debug_info["help_lines"]):
            help_text = ServiceLocator.texts_service.get(font, line, color)
            screen.blit(help_text, (help_pos["x"], help_pos["y"] + i * self._debug_info["help_line_height"]))

    def do_action(self, action: CInputCommand) -> None:
        constants = ServiceLocator.constants_service
        if action.name in constants.direction_commands:
            # También en pausa: así, al reanudar, la dirección es la de las flechas que siguen presionadas.
            held = (action.name, action.key)
            if action.phase == CommandPhase.START:
                self._held_direction_keys.add(held)
            else:
                self._held_direction_keys.discard(held)
            self._update_player_direction()
        elif action.phase == CommandPhase.START and self._event_consumed:
            # Esta misma pulsación ya cambió la pausa con otro comando.
            return
        elif self.state in (PlayState.STARTING, PlayState.CLEARED):
            # Durante el BLAST OFF y al pasar de nivel no se dispara ni se pausa; las flechas sí se registran (arriba)
            # para que la nave salga en la dirección que se mantiene presionada.
            return
        elif self.state == PlayState.PAUSED:
            self._pause_menu_action(action)
        elif self.state == PlayState.PAUSED_INFO:
            self._pause_info_action(action)
        elif action.name == constants.pause_command:
            if action.phase == CommandPhase.START:
                self._event_consumed = True
                self.toggle_pause()
        elif action.name in constants.cheat_commands:
            if action.phase == CommandPhase.START and ServiceLocator.cheats_service.enabled:
                self._cheat_actions[constants.cheat_commands[action.name]]()
        elif action.name == constants.fire_command:
            if action.phase == CommandPhase.START:
                system_player_fire(self.ecs_world)
        elif action.name == constants.ability_command:
            if action.phase == CommandPhase.START and self._ability_info is not None:
                system_player_ability_activate(self.ecs_world, self._ability_info)
        elif action.name == constants.debug_hitboxes_command:
            if action.phase == CommandPhase.START and self._debug_info["enabled"]:
                self._show_hitboxes = not self._show_hitboxes
        elif action.name == constants.debug_explode_command:
            if action.phase == CommandPhase.START and self._debug_info["enabled"]:
                create_explosion_for(self.ecs_world, self._player_entity)
                for enemy, _ in self.ecs_world.get_component(CEnemy):
                    destroy_with_explosion(self.ecs_world, enemy)
        elif action.name == constants.debug_kill_command:
            if action.phase == CommandPhase.START and self._debug_info["enabled"]:
                if is_vulnerable(self.ecs_world, self._player_entity):
                    kill_player(self.ecs_world, self._player_entity, self._respawn_info)
        elif action.name in constants.debug_spawn_commands:
            if action.phase == CommandPhase.START and self._debug_info["enabled"]:
                self._spawn_debug_enemy(EnemyType(constants.debug_spawn_commands[action.name]))

    def _update_player_direction(self) -> None:
        active = {name for name, _ in self._held_direction_keys}
        system_player_direction(self.ecs_world, direction_from_commands(active))

    def _start_blast_off(self) -> None:
        """Empieza el nivel con "BLAST OFF!" y su sonido; el juego arranca al terminar duration."""
        self.state = PlayState.STARTING
        self._blast_off_time = self._blast_off_info["duration"]
        text_info = self._blast_off_info["text"]
        self._blast_off_text = create_interface_text(self.ecs_world, text_info["text"], text_info)
        if self._blast_off_info.get("sound"):
            ServiceLocator.sounds_service.play(self._blast_off_info["sound"])

    def skip_blast_off(self) -> None:
        """Termina el BLAST OFF de inmediato. Lo usan las pruebas y sirve para el modo trampa (#40)."""
        if self.state == PlayState.STARTING:
            self._update_blast_off(self._blast_off_time)

    def _update_blast_off(self, delta_time: float) -> None:
        """Mientras dura el BLAST OFF solo brillan las estrellas y se dibujan el HUD y el minimapa."""
        system_star_blink(self.ecs_world, delta_time, self._stars_info["blink"])
        system_score_hud(self.ecs_world)
        system_lives_hud(self.ecs_world)
        if self._ability_info is not None:
            system_ability_hud(self.ecs_world, self._ability_info["hud"])
        system_alert_hud(self.ecs_world)
        system_minimap(self.ecs_world, delta_time, self.world_size)
        self._blast_off_time -= delta_time
        if self._blast_off_time <= 0:
            self.ecs_world.delete_entity(self._blast_off_text, immediate=True)
            self._blast_off_text = None
            self.state = PlayState.PLAYING

    def _cheat_next_level(self) -> None:
        """Trampa: pasa a la siguiente ronda; desde la última va a la escena de victoria (#36).

        Con el jugador muerto no hace nada: si no le quedaban vidas, saltar de ronda evitaría la derrota.
        El aviso se muestra en la ronda nueva, porque el cambio de escena borra el mundo actual.
        """
        if self.ecs_world.has_component(self._player_entity, CPlayerDead):
            return
        levels = ServiceLocator.configs_service.get(ServiceLocator.constants_service.levels_config)["levels"]
        if ServiceLocator.game_state_service.level_index + 1 < len(levels):
            # La ronda se muestra desde 1, como en el título.
            self._pending_cheat_message = ("NEXT_LEVEL", {"level": ServiceLocator.game_state_service.level_index + 2})
        self.next_level()

    def _cheat_invincible(self) -> None:
        """Trampa: nada mata al jugador (ver is_vulnerable)."""
        active = ServiceLocator.cheats_service.toggle(ServiceLocator.constants_service.cheat_invincible)
        self._show_cheat_message("INVINCIBLE", state=self._on_off(active))

    def _cheat_special_shot(self) -> None:
        """Trampa: da o quita el disparo especial, aunque el nivel no lo dé."""
        constants = ServiceLocator.constants_service
        active = ServiceLocator.cheats_service.toggle(constants.cheat_special_shot)
        if active and not self.ecs_world.has_component(self._player_entity, CSpecialShot):
            special_info = ServiceLocator.configs_service.get(constants.player_config)["special_shot"]
            self.ecs_world.add_component(self._player_entity, CSpecialShot(special_info))
        elif not active and not self._has_special_shot:
            if self.ecs_world.has_component(self._player_entity, CSpecialShot):
                self.ecs_world.remove_component(self._player_entity, CSpecialShot)
        self._show_cheat_message("SPECIAL_SHOT", state=self._on_off(active))

    def _cheat_score(self) -> None:
        """Trampa: suma puntos, para ver las vidas extra y el HI-SCORE."""
        points = self._cheats_info["score_points"]
        ServiceLocator.game_state_service.add_score(points)
        self._show_cheat_message("SCORE", points=points)

    def _on_off(self, active: bool) -> str:
        return self._cheats_info["on_text"] if active else self._cheats_info["off_text"]

    def _show_cheat_message(self, cheat: str, **values) -> None:
        """Muestra unos segundos qué trampa se usó, con el texto de cheats.json.

        Reemplaza el aviso anterior: si no, al presionar dos trampas seguidas se verían encimados.
        """
        if self._cheat_message is not None and self.ecs_world.entity_exists(self._cheat_message):
            self.ecs_world.delete_entity(self._cheat_message, immediate=True)
        text = self._cheats_info["messages"][cheat].format(**values)
        message = create_interface_text(self.ecs_world, text, self._cheats_info["message"])
        self.ecs_world.add_component(message, CLifetime(self._cheats_info["message_duration"]))
        self.ecs_world.add_component(message, CTagHideOnPause())
        self._cheat_message = message

    def toggle_pause(self) -> None:
        """Pausa o reanuda (LC-ESC-04.3): esconde el mundo y el minimapa y muestra el menú de pausa."""
        sounds = ServiceLocator.sounds_service
        sounds.play_effect("PAUSE")
        if self.state == PlayState.PLAYING:
            system_pause_visibility(self.ecs_world, paused=True)
            self._show_pause_menu(0)
            sounds.pause_music()
        else:
            self._clear_pause_overlay()
            self.state = PlayState.PLAYING
            system_pause_visibility(self.ecs_world, paused=False)
            sounds.resume_music()

    def _pause_menu_action(self, action: CInputCommand) -> None:
        """Menú de pausa: elegir con arriba y abajo y aceptar; pausa o volver reanudan."""
        if action.phase != CommandPhase.START:
            return
        constants = ServiceLocator.constants_service
        if action.name in constants.menu_move_commands:
            move_menu_selection(self.ecs_world, constants.menu_move_commands[action.name])
            return
        if action.name in (constants.pause_command, constants.menu_back_command):
            choice = "RESUME"
        elif action.name == constants.menu_accept_command:
            choice = selected_action(self.ecs_world)
        else:
            return
        self._event_consumed = True
        self._pause_selected = get_menu(self.ecs_world).selected
        if choice != "RESUME":
            ServiceLocator.sounds_service.play_effect("MENU_ACCEPT")
        if choice == "RESUME":
            self.toggle_pause()
        elif choice == "INSTRUCTIONS":
            self._show_pause_info(constants.instructions_config)
        elif choice == "CREDITS":
            self._show_pause_info(constants.credits_config)
        elif choice == "QUIT":
            # Salir desde la pausa termina la partida: el título vuelve a la ronda 1 (LC-RON-01).
            ServiceLocator.game_state_service.reset_round()
            self.switch_scene(constants.title_scene)

    def _pause_info_action(self, action: CInputCommand) -> None:
        """Instrucciones o créditos en pausa: aceptar, volver o pausa regresan al menú de pausa."""
        constants = ServiceLocator.constants_service
        if action.phase == CommandPhase.START and action.name in (
                constants.menu_accept_command, constants.menu_back_command, constants.pause_command):
            self._event_consumed = True
            self._show_pause_menu(self._pause_selected)

    def _show_pause_menu(self, selected: int) -> None:
        """Muestra "JUEGO PAUSADO" y el menú de pausa, con el mismo estilo de menú que el título."""
        self._clear_pause_overlay()
        self.state = PlayState.PAUSED
        text_info = self._pause_info["text"]
        overlay = [create_interface_text(self.ecs_world, text_info["text"], text_info),
                   create_menu(self.ecs_world, self._pause_info["menu"])]
        overlay += [entity for entity, _ in self.ecs_world.get_component(CMenuItem)]
        get_menu(self.ecs_world).selected = selected
        system_menu_highlight(self.ecs_world)
        self._tag_pause_overlay(overlay)

    def _show_pause_info(self, config_path: str) -> None:
        """Muestra las líneas de las instrucciones o los créditos sin salir de la partida."""
        self._clear_pause_overlay()
        self.state = PlayState.PAUSED_INFO
        config = ServiceLocator.configs_service.get(config_path)
        hint_info = self._pause_info["info_hint"]
        overlay = create_text_lines(self.ecs_world, config["lines"])
        overlay.append(create_interface_text(self.ecs_world, hint_info["text"], hint_info))
        self._tag_pause_overlay(overlay)

    def _tag_pause_overlay(self, entities: list[int]) -> None:
        for entity in entities:
            self.ecs_world.add_component(entity, CTagPauseOverlay())

    def _clear_pause_overlay(self) -> None:
        for entity, _ in self.ecs_world.get_component(CTagPauseOverlay):
            self.ecs_world.delete_entity(entity, immediate=True)

    def do_process_events(self, event: pygame.event.Event) -> None:
        # system_input ya repartió este evento a todos sus comandos; el siguiente empieza de cero.
        self._event_consumed = False
        if event.type == pygame.JOYDEVICEREMOVED:
            # Solo se sueltan las direcciones del mando (claves negativas); las flechas que siguen
            # presionadas en el teclado se conservan.
            self._held_direction_keys = {held for held in self._held_direction_keys if held[1] >= 0}
            reset_gamepad_commands(self.ecs_world)
            self._update_player_direction()
        # Al perder el foco pygame puede no enviar el KEYUP; sin esto una flecha quedaría "pegada".
        if event.type == pygame.WINDOWFOCUSLOST:
            self._held_direction_keys.clear()
            reset_gamepad_commands(self.ecs_world)
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
