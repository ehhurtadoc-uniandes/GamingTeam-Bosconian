import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_base import create_base
from src.create.prefab_bullet import create_turret_bullet
from src.create.prefab_enemy import create_enemy
from src.create.prefab_hitbox import add_hitbox
from src.create.prefab_player import create_player
from src.create.prefab_player_bullet import create_player_bullet
from src.ecs.components.c_base import BaseOrientation, CBase
from src.ecs.components.c_enemy import EnemyType
from src.ecs.components.c_hitbox import CHitBox, CollisionLayer
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_collision import hitbox_center, hitboxes_overlap, system_collision
from src.ecs.systems.s_debug_hitboxes import system_debug_hitboxes
from src.ecs.systems.s_enemy_bullet_collision import system_enemy_bullet_collision
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from tests.test_base import BASE_INFO
from tests.test_input import key_event
from tests.test_player_fire import PLAYER_INFO
from tests.test_turret import BULLET_INFO, ENEMIES_INFO

L = CollisionLayer
V = pygame.Vector2


def add_box(world, pos, size, layer, offset=(0, 0)):
    entity = world.create_entity()
    world.add_component(entity, CTransform(V(pos)))
    world.add_component(entity, CHitBox(V(size), V(offset), layer))
    return entity


class TestOverlap(unittest.TestCase):
    def test_cajas_que_se_solapan(self):
        self.assertTrue(hitboxes_overlap(V(0, 0), V(10, 10), V(9, 0), V(10, 10)))

    def test_cajas_que_solo_se_tocan_no_chocan(self):
        self.assertFalse(hitboxes_overlap(V(0, 0), V(10, 10), V(10, 0), V(10, 10)))

    def test_cajas_separadas_en_un_solo_eje_no_chocan(self):
        self.assertFalse(hitboxes_overlap(V(0, 0), V(10, 10), V(5, 20), V(10, 10)))

    def test_choca_cruzando_el_borde_del_mundo(self):
        world_size = V(100, 100)
        self.assertFalse(hitboxes_overlap(V(2, 50), V(10, 10), V(98, 50), V(10, 10)))
        self.assertTrue(hitboxes_overlap(V(2, 50), V(10, 10), V(98, 50), V(10, 10), world_size))
        self.assertTrue(hitboxes_overlap(V(50, 2), V(10, 10), V(50, 98), V(10, 10), world_size))


class TestSystemCollision(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()
        self.pair = (L.PLAYER_BULLET, L.ENEMY)

    def test_detecta_el_par_de_capas(self):
        bullet = add_box(self.world, (0, 0), (4, 4), L.PLAYER_BULLET)
        enemy = add_box(self.world, (2, 2), (8, 8), L.ENEMY)
        self.assertEqual(system_collision(self.world, [self.pair])[self.pair], [(bullet, enemy)])

    def test_sin_solape_no_hay_colision(self):
        add_box(self.world, (0, 0), (4, 4), L.PLAYER_BULLET)
        add_box(self.world, (50, 50), (8, 8), L.ENEMY)
        self.assertEqual(system_collision(self.world, [self.pair])[self.pair], [])

    def test_capas_que_no_estan_en_los_pares_se_ignoran(self):
        add_box(self.world, (0, 0), (4, 4), L.PLAYER_BULLET)
        add_box(self.world, (0, 0), (8, 8), L.BASE)
        self.assertEqual(system_collision(self.world, [self.pair])[self.pair], [])

    def test_el_orden_del_par_importa(self):
        bullet = add_box(self.world, (0, 0), (4, 4), L.PLAYER_BULLET)
        enemy = add_box(self.world, (0, 0), (8, 8), L.ENEMY)
        result = system_collision(self.world, [(L.ENEMY, L.PLAYER_BULLET)])
        self.assertEqual(result[(L.ENEMY, L.PLAYER_BULLET)], [(enemy, bullet)])

    def test_misma_capa_no_se_choca_consigo_ni_repite_pares(self):
        a = add_box(self.world, (0, 0), (8, 8), L.ENEMY)
        b = add_box(self.world, (4, 0), (8, 8), L.ENEMY)
        c = add_box(self.world, (200, 0), (8, 8), L.ENEMY)
        pair = (L.ENEMY, L.ENEMY)
        self.assertEqual(system_collision(self.world, [pair])[pair], [(a, b)])
        self.assertNotIn(c, [e for found in system_collision(self.world, [pair])[pair] for e in found])

    def test_varios_pares_en_una_llamada(self):
        add_box(self.world, (0, 0), (4, 4), L.PLAYER_BULLET)
        add_box(self.world, (0, 0), (8, 8), L.ENEMY)
        add_box(self.world, (0, 0), (8, 8), L.PLAYER)
        pairs = [self.pair, (L.ENEMY, L.PLAYER)]
        result = system_collision(self.world, pairs)
        self.assertEqual(len(result[pairs[0]]), 1)
        self.assertEqual(len(result[pairs[1]]), 1)

    def test_entidad_borrada_no_choca(self):
        add_box(self.world, (0, 0), (4, 4), L.PLAYER_BULLET)
        enemy = add_box(self.world, (0, 0), (8, 8), L.ENEMY)
        self.world.delete_entity(enemy)
        self.assertEqual(system_collision(self.world, [self.pair])[self.pair], [])

    def test_wraparound_en_el_sistema(self):
        add_box(self.world, (98, 50), (4, 4), L.PLAYER_BULLET)
        add_box(self.world, (0, 50), (8, 8), L.ENEMY)
        self.assertEqual(system_collision(self.world, [self.pair])[self.pair], [])
        self.assertEqual(len(system_collision(self.world, [self.pair], V(100, 100))[self.pair]), 1)

    def test_offset_mueve_la_caja_respecto_al_sprite(self):
        entity = add_box(self.world, (10, 10), (4, 4), L.ENEMY, offset=(3, 1))
        c_t = self.world.component_for_entity(entity, CTransform)
        c_h = self.world.component_for_entity(entity, CHitBox)
        self.assertEqual(hitbox_center(c_t, c_h), V(15, 13))


class TestAddHitbox(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()

    def make(self, info, rotated=False):
        entity = self.world.create_entity(CSurface(V(16, 8), pygame.Color(0, 0, 0)))
        add_hitbox(self.world, entity, info, L.ENEMY, rotated)
        return self.world.component_for_entity(entity, CHitBox)

    def test_sin_hitbox_en_config_usa_el_tamano_del_sprite(self):
        c_h = self.make({})
        self.assertEqual(c_h.size, V(16, 8))
        self.assertEqual(c_h.offset, V(0, 0))

    def test_hitbox_configurada_queda_centrada_en_el_sprite(self):
        c_h = self.make({"hitbox": {"size": {"w": 8, "h": 4}}})
        self.assertEqual(c_h.size, V(8, 4))
        self.assertEqual(c_h.offset, V(4, 2))

    def test_offset_configurado_desplaza_el_centro(self):
        c_h = self.make({"hitbox": {"size": {"w": 8, "h": 4}, "offset": {"x": 2, "y": 0}}})
        self.assertEqual(c_h.offset, V(6, 2))

    def test_rotada_intercambia_ancho_y_alto(self):
        c_h = self.make({"hitbox": {"size": {"w": 8, "h": 4}}}, rotated=True)
        self.assertEqual(c_h.size, V(4, 8))

    def test_la_capa_queda_en_el_componente(self):
        self.assertEqual(self.make({}).layer, L.ENEMY)


class TestHitboxEnPrefabs(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()

    def hitbox(self, entity):
        return self.world.component_for_entity(entity, CHitBox)

    def test_jugador(self):
        player = create_player(self.world, PLAYER_INFO, V(0, 0))
        self.assertEqual(self.hitbox(player).layer, L.PLAYER)

    def test_hitbox_del_jugador_es_independiente_del_sprite(self):
        info = dict(PLAYER_INFO, hitbox={"size": {"w": 4, "h": 4}})
        player = create_player(self.world, info, V(100, 100))
        enemy = add_box(self.world, (112, 100), (4, 4), L.ENEMY)
        self.assertEqual(system_collision(self.world, [(L.PLAYER, L.ENEMY)])[(L.PLAYER, L.ENEMY)], [])
        self.assertTrue(self.world.entity_exists(player) and self.world.entity_exists(enemy))

    def test_enemigo(self):
        enemy = create_enemy(self.world, ENEMIES_INFO, V(0, 0), EnemyType.I)
        self.assertEqual(self.hitbox(enemy).layer, L.ENEMY)

    def test_balas(self):
        mine = create_player_bullet(self.world, PLAYER_INFO["weapon"]["bullet"], V(0, 0), V(1, 0))
        theirs = create_turret_bullet(self.world, BULLET_INFO, V(0, 0), V(1, 0))
        self.assertEqual(self.hitbox(mine).layer, L.PLAYER_BULLET)
        self.assertEqual(self.hitbox(theirs).layer, L.ENEMY_BULLET)

    def test_piezas_de_la_base(self):
        base = create_base(self.world, BASE_INFO, V(100, 100), BaseOrientation.HORIZONTAL)
        c_base = self.world.component_for_entity(base, CBase)
        self.assertEqual(self.hitbox(base).layer, L.BASE)
        self.assertEqual(self.hitbox(c_base.core).layer, L.BASE_CORE)
        for turret in c_base.turrets:
            self.assertEqual(self.hitbox(turret).layer, L.BASE_TURRET)

    def test_hitbox_de_la_base_vertical_sigue_a_la_pieza_rotada(self):
        info = dict(BASE_INFO, core=dict(BASE_INFO["core"], hitbox={"size": {"w": 10, "h": 4}}))
        base = create_base(self.world, info, V(100, 100), BaseOrientation.VERTICAL)
        core = self.world.component_for_entity(base, CBase).core
        self.assertEqual(self.hitbox(core).size, V(4, 10))

    def test_bala_de_jugador_choca_con_torreta_y_no_con_el_cuerpo(self):
        base = create_base(self.world, BASE_INFO, V(100, 100), BaseOrientation.HORIZONTAL)
        turret = self.world.component_for_entity(base, CBase).turrets[0]
        c_t = self.world.component_for_entity(turret, CTransform)
        create_player_bullet(self.world, PLAYER_INFO["weapon"]["bullet"], c_t.pos + V(3, 3), V(1, 0))
        pair = (L.PLAYER_BULLET, L.BASE_TURRET)
        self.assertEqual(len(system_collision(self.world, [pair])[pair]), 1)


class TestHitboxEnLaMuerteDeEnemigos(unittest.TestCase):
    def test_bala_enemiga_no_mata_si_solo_toca_el_sprite(self):
        world = esper.World()
        info = {"I": dict(ENEMIES_INFO["I"], size={"w": 20, "h": 20}, hitbox={"size": {"w": 4, "h": 4}})}
        enemy = create_enemy(world, info, V(0, 0), EnemyType.I)
        create_turret_bullet(world, BULLET_INFO, V(1, 1), V(1, 0))
        system_enemy_bullet_collision(world)
        self.assertTrue(world.entity_exists(enemy))

    def test_bala_enemiga_mata_al_chocar_con_la_hitbox(self):
        world = esper.World()
        enemy = create_enemy(world, ENEMIES_INFO, V(0, 0), EnemyType.I)
        create_turret_bullet(world, BULLET_INFO, V(4, 4), V(1, 0))
        system_enemy_bullet_collision(world)
        self.assertFalse(world.entity_exists(enemy))

    def test_bala_enemiga_mata_cruzando_el_borde_del_mundo(self):
        world = esper.World()
        enemy = create_enemy(world, ENEMIES_INFO, V(0, 50), EnemyType.I)
        create_turret_bullet(world, BULLET_INFO, V(99.5, 54), V(1, 0))
        system_enemy_bullet_collision(world)
        self.assertTrue(world.entity_exists(enemy))
        system_enemy_bullet_collision(world, V(100, 100))
        self.assertFalse(world.entity_exists(enemy))


class TestHitboxEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.scene.start()

    def test_configs_reales_tienen_hitbox_no_mayor_que_el_sprite(self):
        constants = ServiceLocator.constants_service
        configs = ServiceLocator.configs_service
        base = configs.get(constants.base_config)
        enemies = configs.get(constants.enemies_config)
        infos = [configs.get(constants.player_config), base["turret"], base["core"], *enemies.values()]
        for info in infos:
            self.assertLessEqual(info["hitbox"]["size"]["w"], info["size"]["w"])
            self.assertLessEqual(info["hitbox"]["size"]["h"], info["size"]["h"])

    def test_todo_lo_del_juego_tiene_hitbox(self):
        world = self.scene.ecs_world
        layers = {c_h.layer for _, c_h in world.get_component(CHitBox)}
        self.assertTrue({L.PLAYER, L.BASE, L.BASE_TURRET, L.BASE_CORE} <= layers)

    def test_h_muestra_y_oculta_las_hitbox(self):
        self.assertFalse(self.scene._show_hitboxes)
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_h))
        self.assertTrue(self.scene._show_hitboxes)
        self.scene.do_draw(self.engine.screen)
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_h))
        self.assertFalse(self.scene._show_hitboxes)

    def test_dibujo_de_hitbox_se_recorta_al_area_de_juego(self):
        screen = pygame.Surface((256, 208))
        world = esper.World()
        add_box(world, (-50, -50), (20, 20), L.ENEMY)
        system_debug_hitboxes(world, screen, pygame.Color(255, 255, 255))
        self.assertEqual(screen.get_at((0, 0)), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
