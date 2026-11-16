import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_player import create_player
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_player_weapon import CPlayerWeapon
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_player_bullet import CTagPlayerBullet
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_offscreen_despawn import system_offscreen_despawn
from src.ecs.systems.s_player_fire import system_player_fire, system_player_weapon_cooldown
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from tests.test_input import key_event

PLAYER_INFO = {
    "size": {"w": 10, "h": 10},
    "color": {"r": 0, "g": 0, "b": 255},
    "movement": {"initial_speed": 0, "max_speed": 60, "acceleration": 15, "start_direction": {"x": 1, "y": 0}},
    "weapon": {
        "fire_cooldown": 0.5,
        "bullet": {"size": {"w": 2, "h": 2}, "color": {"r": 255, "g": 255, "b": 255}, "speed": 100},
    },
}


def bullets(world):
    return [(e, world.component_for_entity(e, CVelocity).vel, world.component_for_entity(e, CTransform).pos)
            for e, _ in world.get_component(CTagPlayerBullet) if world.entity_exists(e)]


class TestSystemPlayerFire(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()
        self.player = create_player(self.world, PLAYER_INFO, pygame.Vector2(100, 100))

    def test_dispara_dos_balas(self):
        system_player_fire(self.world)
        self.assertEqual(len(bullets(self.world)), 2)

    def test_una_va_al_frente_y_otra_atras(self):
        system_player_fire(self.world)
        velocities = sorted((tuple(v) for _, v, _ in bullets(self.world)))
        self.assertEqual(velocities, [(-100.0, 0.0), (100.0, 0.0)])

    def test_sigue_la_direccion_actual_del_jugador(self):
        self.world.component_for_entity(self.player, CPlayerMovement).direction = pygame.Vector2(0, -1)
        system_player_fire(self.world)
        velocities = sorted((tuple(v) for _, v, _ in bullets(self.world)))
        self.assertEqual(velocities, [(0.0, -100.0), (0.0, 100.0)])

    def test_las_balas_salen_del_centro_del_jugador(self):
        system_player_fire(self.world)
        for _, _, pos in bullets(self.world):
            self.assertEqual(pos + pygame.Vector2(1, 1), pygame.Vector2(105, 105))

    def test_cooldown_impide_disparar_de_inmediato(self):
        system_player_fire(self.world)
        system_player_fire(self.world)
        self.assertEqual(len(bullets(self.world)), 2)

    def test_dispara_de_nuevo_al_terminar_el_cooldown(self):
        system_player_fire(self.world)
        system_player_weapon_cooldown(self.world, 0.3)
        system_player_fire(self.world)
        self.assertEqual(len(bullets(self.world)), 2)
        system_player_weapon_cooldown(self.world, 0.3)
        system_player_fire(self.world)
        self.assertEqual(len(bullets(self.world)), 4)

    def test_cooldown_no_baja_de_cero(self):
        system_player_weapon_cooldown(self.world, 10.0)
        self.assertEqual(self.world.component_for_entity(self.player, CPlayerWeapon).time_left, 0.0)

    def test_las_balas_se_mueven(self):
        system_player_fire(self.world)
        system_movement(self.world, 0.1)
        xs = sorted(pos.x for _, _, pos in bullets(self.world))
        self.assertAlmostEqual(xs[0], 104 - 10)
        self.assertAlmostEqual(xs[1], 104 + 10)

    def test_las_balas_desaparecen_al_salir_de_la_pantalla(self):
        screen = pygame.Rect(0, 0, 200, 200)
        system_player_fire(self.world)
        system_offscreen_despawn(self.world, screen_rect=screen)
        self.world._clear_dead_entities()
        self.assertEqual(len(bullets(self.world)), 2)
        for _ in range(30):
            system_movement(self.world, 0.1)
        system_offscreen_despawn(self.world, screen_rect=screen)
        self.world._clear_dead_entities()
        self.assertEqual(len(bullets(self.world)), 0)


class TestDisparoEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.scene.start()

    def test_config_real_tiene_arma(self):
        info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.player_config)
        self.assertGreater(info["weapon"]["fire_cooldown"], 0)
        for key in ("size", "color", "speed"):
            self.assertIn(key, info["weapon"]["bullet"])

    def test_z_dispara_dos_balas(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_z))
        self.assertEqual(len(bullets(self.scene.ecs_world)), 2)

    def test_en_pausa_no_dispara(self):
        self.scene.toggle_pause()
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_z))
        self.assertEqual(len(bullets(self.scene.ecs_world)), 0)

    def test_las_balas_se_borran_al_salir_del_area_de_juego(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_z))
        for _ in range(6 * 60):
            self.scene.simulate(1 / 60)
        self.assertEqual(len(bullets(self.scene.ecs_world)), 0)


if __name__ == "__main__":
    unittest.main()
