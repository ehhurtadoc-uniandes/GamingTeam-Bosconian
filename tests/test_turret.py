"""Pruebas de las torretas que disparan y sus balas (#20). Ejecutar con: python -m unittest discover -s tests"""
import os
import random
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_base import create_base
from src.create.prefab_bullet import create_turret_bullet
from src.create.prefab_enemy import create_enemy
from src.ecs.components.c_base import BaseOrientation, CBase
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_turret import CTurret, TurretState
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_base import CTagBaseTurret
from src.ecs.components.tags.c_tag_enemy import CTagEnemy, CTagEnemyBullet, EnemyType
from src.ecs.systems.s_enemy_bullet_collision import system_enemy_bullet_collision
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_turret import system_turret
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.scenes.play_scene import BASE_CONFIG
from tests.test_base import BASE_INFO, center_of

BULLET_INFO = {"size": {"w": 2, "h": 2}, "color": {"r": 255, "g": 255, "b": 0}, "speed": 100, "lifetime": 1.0}
ENEMIES_INFO = {"I": {
    "size": {"w": 8, "h": 8}, "color": {"r": 255, "g": 0, "b": 0}, "points": 50, "initial_state": "CHASE",
    "steering": {"max_speed": 0, "max_force": 0},
    "states": {"CHASE": {"seek_weight": 0.0}},
}}


def add_turret(world, center, activation_distance=50.0, fire_interval=1.0, time_to_fire=0.0):
    """Torreta suelta de 4x4 con centro en center."""
    closed = pygame.Surface((4, 4))
    opened = pygame.Surface((4, 4))
    turret = world.create_entity()
    world.add_component(turret, CTransform(pygame.Vector2(center) - pygame.Vector2(2, 2)))
    world.add_component(turret, CSurface.from_surface(closed))
    world.add_component(turret, CTurret(activation_distance, fire_interval, time_to_fire, closed, opened))
    return turret


def bullets(world):
    return [e for e, _ in world.get_component(CTagEnemyBullet) if world.entity_exists(e)]


class TestSystemTurret(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()

    def step(self, player_center, delta_time=0.1, world_size=None):
        system_turret(self.world, delta_time, pygame.Vector2(player_center), BULLET_INFO, world_size)

    def state(self, turret):
        return self.world.component_for_entity(turret, CTurret).state

    def test_lejos_queda_cerrada_y_no_dispara(self):
        turret = add_turret(self.world, (0, 0))
        for _ in range(30):
            self.step((100, 0))
        self.assertEqual(self.state(turret), TurretState.CLOSED)
        self.assertEqual(bullets(self.world), [])

    def test_cerca_se_abre_cambia_de_aspecto_y_lejos_se_cierra(self):
        turret = add_turret(self.world, (0, 0), time_to_fire=10)
        c_tu = self.world.component_for_entity(turret, CTurret)
        c_s = self.world.component_for_entity(turret, CSurface)
        self.step((49, 0))
        self.assertEqual(self.state(turret), TurretState.OPEN)
        self.assertIs(c_s.surf, c_tu.open_surf)
        self.step((51, 0))
        self.assertEqual(self.state(turret), TurretState.CLOSED)
        self.assertIs(c_s.surf, c_tu.closed_surf)

    def test_distancia_cruzando_el_borde_del_mundo(self):
        world_size = pygame.Vector2(500, 400)
        turret = add_turret(self.world, (490, 200), time_to_fire=10)
        self.step((20, 200), world_size=world_size)  # 30 px cruzando el borde derecho
        self.assertEqual(self.state(turret), TurretState.OPEN)
        self.step((20, 200))  # sin wraparound está a 470 px
        self.assertEqual(self.state(turret), TurretState.CLOSED)

    def test_dispara_segun_su_intervalo(self):
        add_turret(self.world, (0, 0), fire_interval=1.0, time_to_fire=0.25)
        counts = []
        for _ in range(25):  # 2.5 s
            self.step((10, 0))
            counts.append(len(bullets(self.world)))
        # Disparos en t = 0.3, 1.3 y 2.3 (pasos de 0.1 s)
        self.assertEqual(counts[1], 0)
        self.assertEqual(counts[2], 1)
        self.assertEqual(counts[11], 1)
        self.assertEqual(counts[12], 2)
        self.assertEqual(counts[-1], 3)

    def test_cerrada_no_avanza_el_temporizador(self):
        turret = add_turret(self.world, (0, 0), time_to_fire=0.5)
        for _ in range(20):
            self.step((100, 0))
        self.assertAlmostEqual(self.world.component_for_entity(turret, CTurret).time_to_fire, 0.5)

    def test_bala_sale_del_centro_hacia_el_jugador(self):
        add_turret(self.world, (10, 10))
        self.step((34, 42), delta_time=0.01)
        [bullet] = bullets(self.world)
        self.assertEqual(center_of(self.world, bullet), (10, 10))
        vel = self.world.component_for_entity(bullet, CVelocity).vel
        self.assertAlmostEqual(vel.length(), BULLET_INFO["speed"])
        self.assertAlmostEqual(vel.normalize().x, 0.6)
        self.assertAlmostEqual(vel.normalize().y, 0.8)

    def test_bala_apunta_por_el_borde_con_wraparound(self):
        add_turret(self.world, (490, 200))
        self.step((20, 200), delta_time=0.01, world_size=pygame.Vector2(500, 400))
        [bullet] = bullets(self.world)
        self.assertGreater(self.world.component_for_entity(bullet, CVelocity).vel.x, 0)


class TestTorretasDeBase(unittest.TestCase):
    def test_torretas_de_una_base_tienen_ritmos_distintos(self):
        world = esper.World()
        base = create_base(world, BASE_INFO, pygame.Vector2(100, 100), BaseOrientation.HORIZONTAL,
                           random.Random(1))
        turrets = [world.component_for_entity(t, CTurret) for t in world.component_for_entity(base, CBase).turrets]
        intervals = [t.fire_interval for t in turrets]
        self.assertEqual(len(set(intervals)), 6)
        self.assertEqual(len({t.time_to_fire for t in turrets}), 6)
        for c_tu in turrets:
            self.assertEqual(c_tu.state, TurretState.CLOSED)
            self.assertTrue(1.0 <= c_tu.fire_interval <= 2.0)
            self.assertTrue(0 <= c_tu.time_to_fire <= c_tu.fire_interval)
            self.assertEqual(c_tu.activation_distance, 50)
            self.assertEqual(c_tu.open_surf.get_at((0, 0)), (255, 128, 0))
            self.assertEqual(c_tu.closed_surf.get_at((0, 0)), (255, 255, 255))

    def test_misma_semilla_mismo_ritmo(self):
        def intervals(seed):
            world = esper.World()
            create_base(world, BASE_INFO, pygame.Vector2(0, 0), BaseOrientation.HORIZONTAL, random.Random(seed))
            return [c.fire_interval for _, c in world.get_component(CTurret)]
        self.assertEqual(intervals(7), intervals(7))

    def test_aspecto_abierto_rota_con_la_base_vertical(self):
        world = esper.World()
        create_base(world, BASE_INFO, pygame.Vector2(0, 0), BaseOrientation.VERTICAL, random.Random(0))
        for _, c_tu in world.get_component(CTurret):
            self.assertEqual(c_tu.open_surf.get_size(), (6, 10))

    def test_no_disparan_todas_a_la_vez(self):
        world = esper.World()
        create_base(world, BASE_INFO, pygame.Vector2(100, 100), BaseOrientation.HORIZONTAL, random.Random(3))
        fired_per_step = []
        for _ in range(20):
            before = len(bullets(world))
            system_turret(world, 0.1, pygame.Vector2(110, 100), BULLET_INFO)
            fired_per_step.append(len(bullets(world)) - before)
        # Cada una dispara al menos una vez en 2 s (intervalo máximo), pero en pasos distintos.
        self.assertGreaterEqual(sum(fired_per_step), 6)
        self.assertLess(max(fired_per_step), 6)
        self.assertGreaterEqual(sum(1 for n in fired_per_step if n > 0), 3)

    def test_intervalo_invalido_da_error(self):
        turret_info = dict(BASE_INFO["turret"], fire_interval={"min": 2.0, "max": 1.0})
        with self.assertRaisesRegex(ValueError, "fire_interval"):
            create_base(esper.World(), dict(BASE_INFO, turret=turret_info), pygame.Vector2(0, 0),
                        BaseOrientation.HORIZONTAL)


class TestBalas(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()

    def simulate(self, delta_time, screen_rect=None):
        system_movement(self.world, delta_time)
        system_lifetime(self.world, delta_time, screen_rect)
        system_enemy_bullet_collision(self.world)
        self.world._clear_dead_entities()

    def test_bala_avanza_recto_y_muere_al_cumplir_su_vida(self):
        bullet = create_turret_bullet(self.world, BULLET_INFO, pygame.Vector2(0, 0), pygame.Vector2(1, 0))
        self.assertTrue(self.world.has_component(bullet, CLifetime))
        for _ in range(9):
            self.simulate(0.1)
        self.assertAlmostEqual(center_of(self.world, bullet).x, 90)
        self.assertAlmostEqual(center_of(self.world, bullet).y, 0)
        self.simulate(0.11)
        self.assertFalse(self.world.entity_exists(bullet))

    def test_bala_fuera_de_pantalla_se_borra(self):
        screen = pygame.Rect(0, 0, 50, 50)
        bullet = create_turret_bullet(self.world, BULLET_INFO, pygame.Vector2(45, 10), pygame.Vector2(1, 0))
        self.simulate(0.01, screen)
        self.assertTrue(self.world.entity_exists(bullet))
        self.simulate(0.1, screen)
        self.assertFalse(self.world.entity_exists(bullet))

    def test_enemigo_que_choca_con_una_bala_muere_con_ella(self):
        enemy = create_enemy(self.world, ENEMIES_INFO, pygame.Vector2(10, 0), EnemyType.I)
        other = create_enemy(self.world, ENEMIES_INFO, pygame.Vector2(100, 100), EnemyType.I)
        bullet = create_turret_bullet(self.world, BULLET_INFO, pygame.Vector2(5, 4), pygame.Vector2(1, 0))
        self.simulate(0.05)
        self.assertFalse(self.world.entity_exists(enemy))
        self.assertFalse(self.world.entity_exists(bullet))
        self.assertTrue(self.world.entity_exists(other))

    def test_una_bala_mata_a_un_solo_enemigo(self):
        a = create_enemy(self.world, ENEMIES_INFO, pygame.Vector2(0, 0), EnemyType.I)
        b = create_enemy(self.world, ENEMIES_INFO, pygame.Vector2(0, 0), EnemyType.I)
        create_turret_bullet(self.world, BULLET_INFO, pygame.Vector2(4, 4), pygame.Vector2(1, 0))
        self.simulate(0.0)
        self.assertEqual(len(self.world.get_component(CTagEnemy)), 1)
        self.assertNotEqual(self.world.entity_exists(a), self.world.entity_exists(b))

    def test_bala_vencida_ya_no_mata(self):
        enemy = create_enemy(self.world, ENEMIES_INFO, pygame.Vector2(0, 0), EnemyType.I)
        info = dict(BULLET_INFO, lifetime=0.01)
        create_turret_bullet(self.world, info, pygame.Vector2(4, 4), pygame.Vector2(1, 0))
        self.simulate(0.02)
        self.assertTrue(self.world.entity_exists(enemy))
        self.assertEqual(bullets(self.world), [])

    def test_balas_atraviesan_las_bases(self):
        base = create_base(self.world, BASE_INFO, pygame.Vector2(50, 50), BaseOrientation.HORIZONTAL)
        bullet = create_turret_bullet(self.world, BULLET_INFO, pygame.Vector2(50, 50), pygame.Vector2(1, 0))
        self.simulate(0.05)
        self.assertTrue(self.world.entity_exists(base))
        self.assertTrue(self.world.entity_exists(bullet))
        self.assertEqual(len(self.world.get_component(CTagBaseTurret)), 6)


class TestTorretasEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]

    def test_config_real_tiene_torreta_y_bala(self):
        base_info = ServiceLocator.configs_service.get(BASE_CONFIG)
        turret = base_info["turret"]
        self.assertGreater(turret["activation_distance"], 0)
        self.assertLessEqual(turret["fire_interval"]["min"], turret["fire_interval"]["max"])
        self.assertIn("open_color", turret)
        for key in ("size", "color", "speed", "lifetime"):
            self.assertIn(key, base_info["bullet"])

    def test_torretas_cercanas_al_jugador_disparan_en_la_escena(self):
        self.scene.start()
        world = self.scene.ecs_world
        player = self.scene._player_entity
        # Pone al jugador junto a la primera base y lo deja quieto.
        base_center = center_of(world, sorted(e for e, _ in world.get_component(CBase))[0])
        world.component_for_entity(player, CTransform).pos = pygame.Vector2(base_center) + pygame.Vector2(0, 30)
        world.remove_component(player, CVelocity)
        for _ in range(int(3 / self.engine.fixed_dt)):
            self.scene.simulate(self.engine.fixed_dt)
        self.assertTrue(any(c.state == TurretState.OPEN for _, c in world.get_component(CTurret)))
        self.assertGreater(len(world.get_component(CTagEnemyBullet)), 0)
        self.scene.do_draw(self.engine.screen)


if __name__ == "__main__":
    unittest.main()
