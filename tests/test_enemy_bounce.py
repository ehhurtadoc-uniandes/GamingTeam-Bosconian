import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_base import create_base
from src.create.prefab_enemy import create_enemy
from src.create.prefab_player import create_player
from src.ecs.components.c_base import BaseOrientation, CBase
from src.ecs.components.c_enemy import EnemyType
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_collision import hitbox_center, hitboxes_overlap
from src.ecs.systems.s_enemy_bounce import contact_normal, reflect, system_enemy_bounce
from src.ecs.systems.s_movement import system_movement
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from tests.test_base import BASE_INFO
from tests.test_player_fire import PLAYER_INFO
from tests.test_turret import ENEMIES_INFO

V = pygame.Vector2


def make_enemy(world, pos, vel=(0, 0)):
    enemy = create_enemy(world, ENEMIES_INFO, V(pos), EnemyType.I)
    world.component_for_entity(enemy, CVelocity).vel = V(vel)
    return enemy


def vel(world, entity):
    return world.component_for_entity(entity, CVelocity).vel


def pos(world, entity):
    return world.component_for_entity(entity, CTransform).pos


def overlapping(world, a, b, world_size=None):
    return hitboxes_overlap(
        hitbox_center(world.component_for_entity(a, CTransform), world.component_for_entity(a, CHitBox)),
        world.component_for_entity(a, CHitBox).size,
        hitbox_center(world.component_for_entity(b, CTransform), world.component_for_entity(b, CHitBox)),
        world.component_for_entity(b, CHitBox).size, world_size)


class TestContactNormal(unittest.TestCase):
    def test_sin_solape_no_hay_contacto(self):
        self.assertIsNone(contact_normal(V(0, 0), V(10, 10), V(20, 0), V(10, 10)))

    def test_choque_lateral_usa_el_eje_x(self):
        normal, overlap = contact_normal(V(0, 0), V(10, 10), V(8, 1), V(10, 10))
        self.assertEqual(normal, V(1, 0))
        self.assertEqual(overlap, 2)

    def test_choque_vertical_usa_el_eje_y(self):
        normal, overlap = contact_normal(V(0, 0), V(10, 10), V(1, -8), V(10, 10))
        self.assertEqual(normal, V(0, -1))
        self.assertEqual(overlap, 2)

    def test_normal_apunta_de_la_primera_a_la_segunda(self):
        normal, _ = contact_normal(V(8, 0), V(10, 10), V(0, 0), V(10, 10))
        self.assertEqual(normal, V(-1, 0))

    def test_contacto_cruzando_el_borde(self):
        normal, overlap = contact_normal(V(98, 50), V(10, 10), V(3, 50), V(10, 10), V(100, 100))
        self.assertEqual(normal, V(1, 0))
        self.assertEqual(overlap, 5)


class TestReflect(unittest.TestCase):
    def test_refleja_si_se_acerca_al_obstaculo(self):
        self.assertEqual(reflect(V(5, 3), V(1, 0)), V(-5, 3))

    def test_no_cambia_si_se_aleja(self):
        self.assertEqual(reflect(V(-5, 3), V(1, 0)), V(-5, 3))

    def test_conserva_la_rapidez(self):
        self.assertAlmostEqual(reflect(V(4, 3), V(0, 1)).length(), 5.0)

    def test_no_modifica_el_vector_original(self):
        v = V(5, 3)
        reflect(v, V(1, 0))
        self.assertEqual(v, V(5, 3))


class TestReboteEntreEnemigos(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()

    def test_de_frente_rebotan_en_sentidos_contrarios(self):
        a = make_enemy(self.world, (0, 0), (50, 0))
        b = make_enemy(self.world, (5, 0), (-50, 0))
        system_enemy_bounce(self.world)
        self.assertEqual(vel(self.world, a), V(-50, 0))
        self.assertEqual(vel(self.world, b), V(50, 0))

    def test_quedan_separados(self):
        a = make_enemy(self.world, (0, 0), (50, 0))
        b = make_enemy(self.world, (5, 0), (-50, 0))
        system_enemy_bounce(self.world)
        self.assertFalse(overlapping(self.world, a, b))

    def test_conservan_su_rapidez_con_choque_en_diagonal(self):
        a = make_enemy(self.world, (0, 0), (30, 40))
        b = make_enemy(self.world, (5, 4), (0, 0))
        system_enemy_bounce(self.world)
        self.assertAlmostEqual(vel(self.world, a).length(), 50.0)

    def test_el_enemigo_quieto_no_gana_velocidad_si_no_se_acerca_a_el(self):
        a = make_enemy(self.world, (0, 0), (-50, 0))
        b = make_enemy(self.world, (5, 0), (0, 0))
        system_enemy_bounce(self.world)
        self.assertEqual(vel(self.world, a), V(-50, 0))
        self.assertEqual(vel(self.world, b), V(0, 0))

    def test_si_ya_se_alejan_solo_se_separan(self):
        a = make_enemy(self.world, (0, 0), (-50, 0))
        b = make_enemy(self.world, (5, 0), (50, 0))
        system_enemy_bounce(self.world)
        self.assertEqual(vel(self.world, a), V(-50, 0))
        self.assertEqual(vel(self.world, b), V(50, 0))
        self.assertFalse(overlapping(self.world, a, b))

    def test_choque_vertical(self):
        a = make_enemy(self.world, (0, 0), (0, 50))
        b = make_enemy(self.world, (0, 5), (0, -50))
        system_enemy_bounce(self.world)
        self.assertEqual(vel(self.world, a), V(0, -50))
        self.assertEqual(vel(self.world, b), V(0, 50))

    def test_no_mueren_ni_explotan(self):
        a = make_enemy(self.world, (0, 0), (50, 0))
        b = make_enemy(self.world, (5, 0), (-50, 0))
        system_enemy_bounce(self.world)
        self.world._clear_dead_entities()
        self.assertTrue(self.world.entity_exists(a) and self.world.entity_exists(b))
        self.assertEqual(len(self.world.get_component(CTransform)), 2)

    def test_enemigos_lejanos_no_se_tocan(self):
        a = make_enemy(self.world, (0, 0), (50, 0))
        make_enemy(self.world, (100, 0), (-50, 0))
        system_enemy_bounce(self.world)
        self.assertEqual(vel(self.world, a), V(50, 0))
        self.assertEqual(pos(self.world, a), V(0, 0))

    def test_rebotan_cruzando_el_borde_del_mundo(self):
        world_size = V(100, 100)
        a = make_enemy(self.world, (97, 50), (50, 0))
        b = make_enemy(self.world, (0, 50), (-50, 0))
        system_enemy_bounce(self.world, world_size)
        self.assertEqual(vel(self.world, a), V(-50, 0))
        self.assertEqual(vel(self.world, b), V(50, 0))
        self.assertFalse(overlapping(self.world, a, b, world_size))

    def test_varios_enemigos_que_convergen_no_se_atraviesan(self):
        enemies = [make_enemy(self.world, (i * 14, 0), (40 - 27 * i, 0)) for i in range(4)]
        for _ in range(300):
            system_movement(self.world, 1 / 60)
            system_enemy_bounce(self.world)
        xs = [pos(self.world, e).x for e in enemies]
        self.assertEqual(xs, sorted(xs))


class TestReboteContraBases(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()
        self.base = create_base(self.world, BASE_INFO, V(100, 100), BaseOrientation.HORIZONTAL)

    def test_rebota_contra_el_cuerpo_de_la_base(self):
        enemy = make_enemy(self.world, (65, 95), (50, 0))
        system_enemy_bounce(self.world)
        self.assertEqual(vel(self.world, enemy), V(-50, 0))

    def test_queda_fuera_de_la_base(self):
        enemy = make_enemy(self.world, (65, 95), (50, 0))
        system_enemy_bounce(self.world)
        self.assertFalse(overlapping(self.world, enemy, self.base))

    def test_la_base_no_se_mueve(self):
        before = V(pos(self.world, self.base))
        make_enemy(self.world, (65, 95), (50, 0))
        system_enemy_bounce(self.world)
        self.assertEqual(pos(self.world, self.base), before)

    def test_rebota_por_arriba_de_la_base(self):
        enemy = make_enemy(self.world, (95, 75), (0, 50))
        system_enemy_bounce(self.world)
        self.assertEqual(vel(self.world, enemy), V(0, -50))

    def test_la_base_vertical_tambien_rebota(self):
        world = esper.World()
        base = create_base(world, BASE_INFO, V(100, 100), BaseOrientation.VERTICAL)
        enemy = make_enemy(world, (75, 95), (50, 0))
        system_enemy_bounce(world)
        self.assertEqual(vel(world, enemy), V(-50, 0))
        self.assertFalse(overlapping(world, enemy, base))

    def test_enemigo_que_avanza_hacia_la_base_nunca_la_atraviesa(self):
        enemy = make_enemy(self.world, (20, 95), (80, 0))
        for _ in range(240):
            system_movement(self.world, 1 / 60)
            system_enemy_bounce(self.world)
            self.assertFalse(overlapping(self.world, enemy, self.base))

    def test_rebota_cruzando_el_borde_del_mundo(self):
        world_size = V(200, 200)
        world = esper.World()
        base = create_base(world, BASE_INFO, V(5, 100), BaseOrientation.HORIZONTAL)
        enemy = make_enemy(world, (172, 95), (50, 0))
        system_enemy_bounce(world, world_size)
        self.assertEqual(vel(world, enemy), V(-50, 0))
        self.assertFalse(overlapping(world, enemy, base, world_size))

    def test_el_empujon_de_otro_enemigo_no_lo_deja_dentro_de_la_base(self):
        # El cuerpo de la base empieza en x=70. b no la toca, pero al separarse de a
        # queda solapándola: la segunda pasada lo saca en el mismo paso.
        make_enemy(self.world, (55, 95), (50, 0))
        b = make_enemy(self.world, (61.5, 95))
        self.assertFalse(overlapping(self.world, b, self.base))
        system_enemy_bounce(self.world)
        self.assertFalse(overlapping(self.world, b, self.base))

    def test_con_una_sola_pasada_el_empujon_lo_deja_dentro(self):
        # Documenta por qué hacen falta varias pasadas.
        make_enemy(self.world, (55, 95), (50, 0))
        b = make_enemy(self.world, (61.5, 95))
        system_enemy_bounce(self.world, max_passes=1)
        self.assertTrue(overlapping(self.world, b, self.base))

    def test_torretas_y_nucleo_no_se_mueven(self):
        c_base = self.world.component_for_entity(self.base, CBase)
        before = [V(pos(self.world, e)) for e in (*c_base.turrets, c_base.core)]
        make_enemy(self.world, (65, 95), (50, 0))
        system_enemy_bounce(self.world)
        after = [V(pos(self.world, e)) for e in (*c_base.turrets, c_base.core)]
        self.assertEqual(before, after)


class TestElJugadorNoRebota(unittest.TestCase):
    def test_el_sistema_no_toca_al_jugador(self):
        world = esper.World()
        player = create_player(world, PLAYER_INFO, V(100, 100))
        enemy = make_enemy(world, (100, 100), (50, 0))
        system_enemy_bounce(world)
        self.assertEqual(pos(world, player), V(100, 100))
        self.assertEqual(vel(world, enemy), V(50, 0))


class TestReboteEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.scene.start()
        self.scene.skip_blast_off()
        self.world = self.scene.ecs_world
        self.world.component_for_entity(self.scene._player_entity, CTransform).pos = V(600, 600)

    def test_dos_enemigos_encimados_se_separan_en_la_escena(self):
        a = create_enemy(self.world, ENEMIES_INFO, V(400, 400), EnemyType.I)
        b = create_enemy(self.world, ENEMIES_INFO, V(402, 400), EnemyType.I)
        self.scene.simulate(1 / 60)
        self.assertFalse(overlapping(self.world, a, b, self.scene.world_size))

    def test_enemigo_que_cruza_una_base_real_rebota_en_la_escena(self):
        base = sorted(e for e, _ in self.world.get_component(CBase))[0]
        center = hitbox_center(self.world.component_for_entity(base, CTransform),
                               self.world.component_for_entity(base, CHitBox))
        enemy = create_enemy(self.world, ENEMIES_INFO, center, EnemyType.I)
        self.world.component_for_entity(enemy, CVelocity).vel = V(0, 0)
        self.scene.simulate(1 / 60)
        self.assertFalse(overlapping(self.world, enemy, base, self.scene.world_size))
        self.scene.do_draw(self.engine.screen)


if __name__ == "__main__":
    unittest.main()
