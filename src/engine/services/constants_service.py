import pygame

from src.ecs.components.c_hitbox import CollisionLayer


class ConstantsService:
    """Constantes del juego en un solo lugar: rutas de los JSON y valores fijos del código.

    Lo que se pueda ajustar sin tocar código va en los JSON; aquí solo queda lo que
    el código necesita para leerlos o validarlos.
    """

    def __init__(self) -> None:
        self.window_config = "assets/cfg/window.json"
        self.input_config = "assets/cfg/input.json"
        self.gamepad_config = "assets/cfg/gamepad.json"
        self.interface_config = "assets/cfg/interface.json"
        self.score_config = "assets/cfg/score.json"
        self.player_config = "assets/cfg/player.json"
        self.enemies_config = "assets/cfg/enemies.json"
        self.debug_config = "assets/cfg/debug.json"
        self.base_config = "assets/cfg/base.json"
        self.levels_config = "assets/cfg/levels.json"
        self.world_config = "assets/cfg/world.json"
        self.stars_config = "assets/cfg/stars.json"
        self.spawner_config = "assets/cfg/spawner.json"
        self.title_config = "assets/cfg/title.json"
        self.instructions_config = "assets/cfg/instructions.json"
        self.credits_config = "assets/cfg/credits.json"
        self.blast_off_config = "assets/cfg/blast_off.json"
        self.cheats_config = "assets/cfg/cheats.json"
        self.victory_config = "assets/cfg/victory.json"
        self.sounds_config = "assets/cfg/sounds.json"
        self.pause_config = "assets/cfg/pause.json"
        self.explosions_config = "assets/cfg/explosions.json"
        self.defeat_config = "assets/cfg/defeat.json"
        self.obstacles_config = "assets/cfg/obstacles.json"
        self.minimap_config = "assets/cfg/minimap.json"
        self.alerts_config = "assets/cfg/alerts.json"

        # Delta máximo de un frame, en segundos: dos frames a 60 FPS. Ver GameEngine._calculate_time.
        # Con más, una bala y un enemigo que van de frente (~100 px/s cada uno) podrían cruzarse
        # en un solo paso sin que sus rectángulos (3 y 8 px) lleguen a tocarse.
        self.max_delta_time = 1 / 30

        # Dirección del jugador si player.json no trae start_direction (o trae cero): hacia arriba.
        self.player_default_direction = pygame.Vector2(0, -1)
        # Ejes de input con magnitud menor a esto se ignoran (drift de joystick, LC-JUG-02).
        self.player_dead_zone = 0.3

        # Intentos para ubicar un obstáculo lejos de lo que ya está en el mundo antes de rendirse.
        self.obstacle_place_tries = 200

        # Una base de Bosconian siempre tiene seis torretas; base.json debe traer un offset para cada una.
        self.turrets_per_base = 6

        self.player_death_layers = (CollisionLayer.ENEMY, CollisionLayer.ENEMY_BULLET, CollisionLayer.OBSTACLE)
        self.player_kills_layers = (CollisionLayer.ENEMY, CollisionLayer.ENEMY_BULLET)
        self.defeat_scene = "defeat"
        self.title_scene = "title"
        self.play_scene = "play"
        self.victory_scene = "victory"

        # Dirección de cada comando de movimiento del jugador.
        self.direction_commands = {
            "PLAYER_UP": pygame.Vector2(0, -1),
            "PLAYER_DOWN": pygame.Vector2(0, 1),
            "PLAYER_LEFT": pygame.Vector2(-1, 0),
            "PLAYER_RIGHT": pygame.Vector2(1, 0),
        }
        # Comandos de los menús (#33): mover la selección, cambiar un valor, aceptar y volver.
        self.menu_move_commands = {"MENU_UP": -1, "MENU_DOWN": 1}
        self.menu_change_commands = {"MENU_LEFT": -1, "MENU_RIGHT": 1}
        self.menu_accept_command = "MENU_ACCEPT"
        self.menu_back_command = "MENU_BACK"
        # Comando que pausa y reanuda la escena de juego (#35).
        self.pause_command = "PAUSE"
        self.fire_command = "PLAYER_FIRE"
        self.debug_hitboxes_command = "DEBUG_HITBOXES"
        self.debug_explode_command = "DEBUG_EXPLODE"
        self.debug_kill_command = "DEBUG_KILL"
        # Modo trampa (#40): comando de input.json -> nombre de la trampa. Cada área agrega aquí
        # el comando de su trampa y su acción en PlayScene._cheat_actions.
        self.cheat_commands = {
            "CHEAT_NEXT_LEVEL": "NEXT_LEVEL",
            "CHEAT_INVINCIBLE": "INVINCIBLE",
            "CHEAT_SPECIAL_SHOT": "SPECIAL_SHOT",
            "CHEAT_SCORE": "SCORE",
        }
        self.cheat_invincible = "INVINCIBLE"
        self.cheat_special_shot = "SPECIAL_SHOT"
        # Con el modo de depuración, estas teclas crean enemigos (valor de EnemyType) a pedido,
        # además de los del spawner (#28).
        self.debug_spawn_commands = {
            "DEBUG_SPAWN_I": "I",
            "DEBUG_SPAWN_P": "P",
            "DEBUG_SPAWN_E": "E",
        }
