import os
import unittest
import warnings
from unittest import mock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_bullet import create_turret_bullet
from src.create.prefab_enemy import create_enemy
from src.create.prefab_explosion import (build_frames, create_explosion, create_explosion_burst,
                                         create_explosion_for, destroy_with_explosion)
from src.create.prefab_player import create_player
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_enemy import CEnemy, EnemyType
from src.ecs.components.c_explosion_burst import CExplosionBurst
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_animation import system_animation
from src.ecs.systems.s_enemy_bullet_collision import system_enemy_bullet_collision
from src.ecs.systems.s_explosion_burst import system_explosion_burst
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_movement import system_movement
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from tests.test_input import key_event
from tests.test_player_fire import PLAYER_INFO
from tests.test_turret import BULLET_INFO, ENEMIES_INFO

V = pygame.Vector2

EXPLOSION_INFO = {
    "size": {"w": 10, "h": 10},
    "frame_duration": 0.1,
    "frames": [
        {"size": {"w": 2, "h": 2}, "color": {"r": 255, "g": 0, "b": 0}},
        {"size": {"w": 6, "h": 6}, "color": {"r": 0, "g": 255, "b": 0}},
        {"size": {"w": 10, "h": 10}, "color": {"r": 0, "g": 0, "b": 255}},
    ],
}
BURST_INFO = {"count": 5, "radius": 10, "time_spread": 0.5}


def explosions(world):
    return [e for e, _ in world.get_component(CAnimation) if world.entity_exists(e)]


def real_configs():
    return ServiceLocator.configs_service.get(ServiceLocator.constants_service.explosions_config)


class TestFrames(unittest.TestCase):
    def test_un_cuadro_por_entrada_con_el_tamano_configurado(self):
        frames = build_frames(EXPLOSION_INFO)
        self.assertEqual(len(frames), 3)
        for frame in frames:
            self.assertEqual(frame.get_size(), (10, 10))

    def test_cada_cuadro_se_dibuja_centrado(self):
        frame = build_frames(EXPLOSION_INFO)[0]
        self.assertEqual(frame.get_at((5, 5)), (255, 0, 0, 255))
        self.assertEqual(frame.get_at((0, 0)).a, 0)

    def test_hoja_de_sprites_se_corta_en_cuadros(self):
        sheet = pygame.Surface((30, 10))
        info = {"size": {"w": 10, "h": 10}, "image": "explosion.png"}
        with mock.patch.object(ServiceLocator.images_service, "get", return_value=sheet):
            self.assertEqual(len(build_frames(info)), 3)


class TestExplosionSimple(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()

    def test_queda_centrada_en_el_punto(self):
        explosion = create_explosion(self.world, EXPLOSION_INFO, V(50, 50), V(0, 0))
        self.assertEqual(self.world.component_for_entity(explosion, CTransform).pos, V(45, 45))

    def test_hereda_la_velocidad_y_se_mueve_con_ella(self):
        explosion = create_explosion(self.world, EXPLOSION_INFO, V(50, 50), V(40, -20))
        system_movement(self.world, 0.5)
        self.assertEqual(self.world.component_for_entity(explosion, CVelocity).vel, V(40, -20))
        self.assertEqual(self.world.component_for_entity(explosion, CTransform).pos, V(65, 35))

    def test_la_velocidad_es_una_copia(self):
        vel = V(10, 0)
        explosion = create_explosion(self.world, EXPLOSION_INFO, V(0, 0), vel)
        vel.x = 99
        self.assertEqual(self.world.component_for_entity(explosion, CVelocity).vel.x, 10)

    def test_la_animacion_avanza_por_cuadros(self):
        explosion = create_explosion(self.world, EXPLOSION_INFO, V(0, 0), V(0, 0))
        c_s = self.world.component_for_entity(explosion, CSurface)
        frames = self.world.component_for_entity(explosion, CAnimation).frames
        self.assertIs(c_s.surf, frames[0])
        system_animation(self.world, 0.11)
        self.assertIs(c_s.surf, frames[1])
        system_animation(self.world, 0.1)
        self.assertIs(c_s.surf, frames[2])

    def test_se_queda_en_el_ultimo_cuadro(self):
        explosion = create_explosion(self.world, EXPLOSION_INFO, V(0, 0), V(0, 0))
        system_animation(self.world, 10.0)
        c_s = self.world.component_for_entity(explosion, CSurface)
        self.assertIs(c_s.surf, self.world.component_for_entity(explosion, CAnimation).frames[-1])

    def test_desaparece_al_terminar_la_animacion(self):
        explosion = create_explosion(self.world, EXPLOSION_INFO, V(0, 0), V(0, 0))
        self.assertAlmostEqual(self.world.component_for_entity(explosion, CLifetime).remaining, 0.3)
        system_lifetime(self.world, 0.2)
        self.assertTrue(self.world.entity_exists(explosion))
        system_lifetime(self.world, 0.11)
        self.assertFalse(self.world.entity_exists(explosion))


class TestExplosionMultiple(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()

    def test_la_primera_sale_de_inmediato(self):
        create_explosion_burst(self.world, EXPLOSION_INFO, BURST_INFO, V(100, 100), V(0, 0))
        system_explosion_burst(self.world, 0.0)
        self.assertGreaterEqual(len(explosions(self.world)), 1)

    def test_salen_todas_las_explosiones_configuradas(self):
        create_explosion_burst(self.world, EXPLOSION_INFO, BURST_INFO, V(100, 100), V(0, 0))
        for _ in range(10):
            system_explosion_burst(self.world, 0.1)
        self.assertEqual(len(explosions(self.world)), 5)

    def test_el_burst_se_borra_al_terminar(self):
        burst = create_explosion_burst(self.world, EXPLOSION_INFO, BURST_INFO, V(100, 100), V(0, 0))
        for _ in range(10):
            system_explosion_burst(self.world, 0.1)
        self.assertFalse(self.world.entity_exists(burst))
        self.world._clear_dead_entities()
        self.assertEqual(len(self.world.get_component(CExplosionBurst)), 0)

    def test_no_salen_todas_a_la_vez(self):
        create_explosion_burst(self.world, EXPLOSION_INFO, dict(BURST_INFO, time_spread=1.0), V(0, 0), V(0, 0))
        system_explosion_burst(self.world, 0.0)
        self.assertEqual(len(explosions(self.world)), 1)

    def test_salen_cerca_del_centro(self):
        create_explosion_burst(self.world, EXPLOSION_INFO, BURST_INFO, V(100, 100), V(0, 0))
        for _ in range(10):
            system_explosion_burst(self.world, 0.1)
        for explosion in explosions(self.world):
            center = self.world.component_for_entity(explosion, CTransform).pos + V(5, 5)
            self.assertLessEqual((center - V(100, 100)).length(), BURST_INFO["radius"] + 0.001)

    def test_el_burst_se_mueve_y_las_explosiones_heredan_la_velocidad(self):
        create_explosion_burst(self.world, EXPLOSION_INFO, dict(BURST_INFO, radius=0, time_spread=0.5),
                               V(0, 0), V(100, 0))
        system_movement(self.world, 0.5)
        system_explosion_burst(self.world, 0.5)
        for explosion in explosions(self.world):
            self.assertEqual(self.world.component_for_entity(explosion, CVelocity).vel, V(100, 0))
            self.assertAlmostEqual(self.world.component_for_entity(explosion, CTransform).pos.x, 45)


class TestExplosionDeEntidades(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()

    def test_enemigo_genera_una_explosion_con_su_velocidad(self):
        enemy = create_enemy(self.world, ENEMIES_INFO, V(100, 100), EnemyType.I)
        self.world.component_for_entity(enemy, CVelocity).vel = V(30, 0)
        create_explosion_for(self.world, enemy)
        [explosion] = explosions(self.world)
        self.assertEqual(self.world.component_for_entity(explosion, CVelocity).vel, V(30, 0))
        center = self.world.component_for_entity(explosion, CTransform).pos + V(8, 8)
        self.assertEqual(center, V(104, 104))

    def test_jugador_genera_varias_explosiones(self):
        player = create_player(self.world, PLAYER_INFO, V(100, 100))
        create_explosion_for(self.world, player)
        self.assertEqual(len(self.world.get_component(CExplosionBurst)), 1)
        for _ in range(20):
            system_explosion_burst(self.world, 0.1)
        self.assertEqual(len(explosions(self.world)), real_configs()["player_burst"]["count"])

    def test_destruir_con_explosion_borra_la_entidad(self):
        enemy = create_enemy(self.world, ENEMIES_INFO, V(0, 0), EnemyType.I)
        destroy_with_explosion(self.world, enemy)
        self.assertFalse(self.world.entity_exists(enemy))
        self.assertEqual(len(explosions(self.world)), 1)

    def test_bala_enemiga_que_mata_a_un_enemigo_provoca_explosion(self):
        enemy = create_enemy(self.world, ENEMIES_INFO, V(0, 0), EnemyType.I)
        create_turret_bullet(self.world, BULLET_INFO, V(4, 4), V(1, 0))
        system_enemy_bullet_collision(self.world)
        self.assertFalse(self.world.entity_exists(enemy))
        self.assertEqual(len(explosions(self.world)), 1)

    def test_sin_colision_no_hay_explosion(self):
        create_enemy(self.world, ENEMIES_INFO, V(0, 0), EnemyType.I)
        create_turret_bullet(self.world, BULLET_INFO, V(100, 100), V(1, 0))
        system_enemy_bullet_collision(self.world)
        self.assertEqual(explosions(self.world), [])


class TestExplosionEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.scene.start()

    def test_config_real_es_valida(self):
        info = real_configs()
        self.assertGreater(info["explosion"]["frame_duration"], 0)
        self.assertGreater(len(build_frames(info["explosion"])), 1)
        self.assertGreaterEqual(info["player_burst"]["count"], 2)

    def test_k_hace_explotar_al_jugador_y_a_los_enemigos(self):
        world = self.scene.ecs_world
        enemy = create_enemy(world, ServiceLocator.configs_service.get(
            ServiceLocator.constants_service.enemies_config), V(0, 0), EnemyType.I)
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_k))
        self.assertFalse(world.entity_exists(enemy))
        self.assertEqual(len(world.get_component(CExplosionBurst)), 1)
        self.assertTrue(world.entity_exists(self.scene._player_entity))

    def test_las_explosiones_se_animan_se_dibujan_y_terminan(self):
        world = self.scene.ecs_world
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_k))
        for _ in range(3 * 60):
            self.scene.simulate(1 / 60)
            self.scene.do_draw(self.engine.screen)
        self.assertEqual(explosions(world), [])
        self.assertEqual(len(world.get_component(CExplosionBurst)), 0)

    def test_en_pausa_las_explosiones_no_avanzan(self):
        world = self.scene.ecs_world
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_k))
        self.scene.simulate(1 / 60)
        self.scene.toggle_pause()
        before = [world.component_for_entity(e, CAnimation).elapsed for e in explosions(world)]
        for _ in range(60):
            self.scene.simulate(1 / 60)
        after = [world.component_for_entity(e, CAnimation).elapsed for e in explosions(world)]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
