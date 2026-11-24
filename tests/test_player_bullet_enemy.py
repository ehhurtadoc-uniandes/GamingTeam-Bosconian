"""Pruebas de las balas del jugador contra enemigos y su puntaje (#96, LC-TEN-01/02/03).

Ejecutar con: python -m unittest discover -s tests
"""
import json
import os
import unittest
import warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import esper
import pygame

from src.create.prefab_base import create_base
from src.create.prefab_bullet import create_turret_bullet
from src.create.prefab_enemy import create_enemy
from src.create.prefab_obstacle import create_mine_blast
from src.create.prefab_player_bullet import create_player_bullet
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_base import BaseOrientation, CBase
from src.ecs.components.c_enemy import EnemyType
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_base_destruction import system_player_bullet_base
from src.ecs.systems.s_collision import hitbox_center
from src.ecs.systems.s_enemy_bullet_collision import system_enemy_bullet_collision
from src.ecs.systems.s_obstacles import system_mine_blast
from src.ecs.systems.s_player_bullet_enemy import system_player_bullet_enemy
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator

V = pygame.Vector2
with open("assets/cfg/enemies.json", encoding="utf-8") as f:
    ENEMIES_INFO = json.load(f)
with open("assets/cfg/player.json", encoding="utf-8") as f:
    BULLET_INFO = json.load(f)["weapon"]["bullet"]
with open("assets/cfg/obstacles.json", encoding="utf-8") as f:
    BLAST_INFO = json.load(f)["mine"]["blast"]
TURRET_BULLET_INFO = {"size": {"w": 2, "h": 2}, "color": {"r": 255, "g": 255, "b": 0}, "speed": 100,
                      "lifetime": 1.0}


def explosions(world):
    return [e for e, _ in world.get_components(CAnimation, CLifetime) if world.entity_exists(e)]


class PlayerBulletEnemyTestCase(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((1, 1))
        self.addCleanup(pygame.quit)
        score_config = ServiceLocator.configs_service.get(ServiceLocator.constants_service.score_config)
        ServiceLocator.game_state_service.load(score_config)
        self.addCleanup(ServiceLocator.game_state_service.load, score_config)
        self.world = esper.World()

    def score(self):
        return ServiceLocator.game_state_service.score

    def enemy(self, pos=V(100, 100), enemy_type=EnemyType.I):
        return create_enemy(self.world, ENEMIES_INFO, V(pos), enemy_type)

    def center(self, entity):
        return hitbox_center(self.world.component_for_entity(entity, CTransform),
                             self.world.component_for_entity(entity, CHitBox))

    def bullet_on(self, entity, offset=V(0, 0)):
        return create_player_bullet(self.world, BULLET_INFO, self.center(entity) + offset, V(1, 0))


class TestBalaDelJugadorContraEnemigos(PlayerBulletEnemyTestCase):
    def test_cada_tipo_muere_con_explosion_y_suma_sus_puntos(self):
        for enemy_type, points in ((EnemyType.I, 50), (EnemyType.P, 60), (EnemyType.E, 70)):
            with self.subTest(enemy_type=enemy_type):
                self.world = esper.World()
                ServiceLocator.game_state_service.new_game()
                enemy = self.enemy(enemy_type=enemy_type)
                bullet = self.bullet_on(enemy)
                system_player_bullet_enemy(self.world)
                self.assertFalse(self.world.entity_exists(enemy))
                self.assertFalse(self.world.entity_exists(bullet))
                self.assertEqual(len(explosions(self.world)), 1)
                self.assertEqual(self.score(), points)
                self.assertEqual(ENEMIES_INFO[enemy_type.value]["points"], points)

    def test_sin_choque_no_pasa_nada(self):
        enemy = self.enemy()
        bullet = self.bullet_on(enemy, V(30, 0))
        system_player_bullet_enemy(self.world)
        self.assertTrue(self.world.entity_exists(enemy))
        self.assertTrue(self.world.entity_exists(bullet))
        self.assertEqual(explosions(self.world), [])
        self.assertEqual(self.score(), 0)

    def test_la_explosion_conserva_la_velocidad_del_enemigo(self):
        enemy = self.enemy()
        self.world.component_for_entity(enemy, CVelocity).vel = V(30, -10)
        self.bullet_on(enemy)
        system_player_bullet_enemy(self.world)
        [explosion] = explosions(self.world)
        self.assertEqual(self.world.component_for_entity(explosion, CVelocity).vel, V(30, -10))

    def test_el_hi_score_se_actualiza_al_superarlo(self):
        game_state = ServiceLocator.game_state_service
        game_state.hi_score = 30
        self.bullet_on(self.enemy())
        system_player_bullet_enemy(self.world)
        self.assertEqual(game_state.hi_score, 50)

    def test_el_hi_score_no_baja(self):
        game_state = ServiceLocator.game_state_service
        game_state.hi_score = 10000
        self.bullet_on(self.enemy())
        system_player_bullet_enemy(self.world)
        self.assertEqual(game_state.hi_score, 10000)

    def test_una_bala_mata_a_un_solo_enemigo(self):
        a = self.enemy(V(100, 100))
        b = self.enemy(V(101, 100))
        self.bullet_on(a, V(0.5, 0))
        system_player_bullet_enemy(self.world)
        alive = [e for e in (a, b) if self.world.entity_exists(e)]
        self.assertEqual(len(alive), 1)
        self.assertEqual(self.score(), 50)

    def test_un_enemigo_da_puntos_una_sola_vez(self):
        enemy = self.enemy()
        first = self.bullet_on(enemy)
        second = self.bullet_on(enemy, V(1, 0))
        system_player_bullet_enemy(self.world)
        self.assertEqual(self.score(), 50)
        # La segunda bala no se gastó en un enemigo que ya estaba muerto.
        self.assertEqual(sum(self.world.entity_exists(b) for b in (first, second)), 1)

    def test_solo_toca_la_hitbox_no_el_sprite(self):
        info = {"I": dict(ENEMIES_INFO["I"], size={"w": 20, "h": 20}, hitbox={"size": {"w": 4, "h": 4}})}
        enemy = create_enemy(self.world, info, V(0, 0), EnemyType.I)
        create_player_bullet(self.world, BULLET_INFO, V(1, 1), V(1, 0))
        system_player_bullet_enemy(self.world)
        self.assertTrue(self.world.entity_exists(enemy))

    def test_mata_cruzando_el_borde_del_mundo(self):
        world_size = V(100, 100)
        enemy = self.enemy(V(-6, 44))
        create_player_bullet(self.world, BULLET_INFO, V(99.8, 54), V(1, 0))
        system_player_bullet_enemy(self.world)
        self.assertTrue(self.world.entity_exists(enemy))
        system_player_bullet_enemy(self.world, world_size)
        self.assertFalse(self.world.entity_exists(enemy))
        self.assertEqual(self.score(), 50)


class TestOrdenConLasBases(PlayerBulletEnemyTestCase):
    def test_bala_sobre_enemigo_y_torreta_solo_mata_al_enemigo(self):
        with open("assets/cfg/base.json", encoding="utf-8") as f:
            base_info = json.load(f)
        base = create_base(self.world, base_info, V(300, 400), BaseOrientation.HORIZONTAL)
        turret = self.world.component_for_entity(base, CBase).turrets[0]
        turret_center = self.center(turret)
        enemy = self.enemy(turret_center - V(10, 10))
        create_player_bullet(self.world, BULLET_INFO, turret_center, V(1, 0))
        # El mismo orden que en PlayScene: primero los enemigos, después las bases.
        system_player_bullet_enemy(self.world)
        system_player_bullet_base(self.world, base_info["points"])
        self.assertFalse(self.world.entity_exists(enemy))
        self.assertTrue(self.world.entity_exists(turret))
        self.assertEqual(self.score(), 50)


class TestMuertesQueNoDanPuntos(PlayerBulletEnemyTestCase):
    def test_enemigo_muerto_por_una_torreta_no_da_puntos(self):
        enemy = self.enemy()
        create_turret_bullet(self.world, TURRET_BULLET_INFO, self.center(enemy), V(1, 0))
        player_bullet = self.bullet_on(enemy)
        # El mismo orden que en PlayScene: primero las balas de torreta.
        system_enemy_bullet_collision(self.world)
        system_player_bullet_enemy(self.world)
        self.assertFalse(self.world.entity_exists(enemy))
        self.assertTrue(self.world.entity_exists(player_bullet))
        self.assertEqual(self.score(), 0)

    def test_enemigo_muerto_por_una_mina_no_da_puntos(self):
        enemy = self.enemy()
        create_mine_blast(self.world, BLAST_INFO, self.center(enemy))
        system_mine_blast(self.world, V(1024, 1536), V(-1000, -1000))
        self.assertFalse(self.world.entity_exists(enemy))
        self.assertEqual(self.score(), 0)


class TestBalaContraEnemigoEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.scene.start()
        self.scene.skip_blast_off()

    def test_la_escena_suma_los_puntos_del_enemigo(self):
        world = self.scene.ecs_world
        player = self.scene._player_entity
        player_center = hitbox_center(world.component_for_entity(player, CTransform),
                                      world.component_for_entity(player, CHitBox))
        enemy = create_enemy(world, ENEMIES_INFO, player_center + V(30, 0), EnemyType.P)
        enemy_center = hitbox_center(world.component_for_entity(enemy, CTransform),
                                     world.component_for_entity(enemy, CHitBox))
        bullet = create_player_bullet(world, BULLET_INFO, enemy_center, V(1, 0))
        # Quieta, para que el enemigo no se le escape en este paso.
        world.component_for_entity(bullet, CVelocity).vel = V(0, 0)
        before = ServiceLocator.game_state_service.score
        self.scene.simulate(1 / 60)
        self.assertFalse(world.entity_exists(enemy))
        self.assertFalse(world.entity_exists(bullet))
        self.assertEqual(ServiceLocator.game_state_service.score, before + 60)


if __name__ == "__main__":
    unittest.main()
