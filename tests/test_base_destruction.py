"""Pruebas de la destrucción de bases y su puntaje (#21). Ejecutar con: python -m unittest discover -s tests"""
import copy
import json
import os
import unittest
import warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import esper
import pygame

from src.create.prefab_base import create_base, rotate_offset
from src.create.prefab_bullet import create_turret_bullet
from src.create.prefab_obstacle import create_mine_blast
from src.create.prefab_player import create_player
from src.create.prefab_player_bullet import create_player_bullet
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_base import BaseOrientation, CBase
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_turret import CTurret, TurretState
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_base import CTagBase
from src.ecs.components.tags.c_tag_enemy_bullet import CTagEnemyBullet
from src.ecs.components.tags.c_tag_offscreen_despawn import CTagOffscreenDespawn
from src.ecs.systems.s_base_destruction import destroy_base, heading_hits_core, system_player_bullet_base
from src.ecs.systems.s_collision import hitbox_center, hitboxes_overlap
from src.ecs.systems.s_obstacles import system_mine_blast
from src.ecs.systems.s_player_death import system_player_death
from src.ecs.systems.s_turret import system_turret
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator

H = BaseOrientation.HORIZONTAL
V = BaseOrientation.VERTICAL
WORLD = pygame.Vector2(1024, 1536)
with open("assets/cfg/base.json", encoding="utf-8") as f:
    BASE_INFO = json.load(f)
with open("assets/cfg/player.json", encoding="utf-8") as f:
    PLAYER_INFO = json.load(f)
POINTS = BASE_INFO["points"]
CENTER = pygame.Vector2(300, 400)


def player_bullet_info():
    return PLAYER_INFO["weapon"]["bullet"]


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((1, 1))
        self.addCleanup(pygame.quit)
        score_config = ServiceLocator.constants_service.score_config
        ServiceLocator.game_state_service.load(ServiceLocator.configs_service.get(score_config))
        self.addCleanup(ServiceLocator.game_state_service.load,
                        ServiceLocator.configs_service.get(score_config))
        self.world = esper.World()
        self.bullet_info = player_bullet_info()

    # --- ayudas ---
    def reset(self):
        """Mundo y puntaje nuevos, para cada subTest."""
        self.world = esper.World()
        ServiceLocator.game_state_service.new_game()

    def base(self, orientation=H, center=CENTER, info=BASE_INFO):
        return create_base(self.world, info, pygame.Vector2(center), orientation)

    def parts(self, base):
        return self.world.component_for_entity(base, CBase)

    def center(self, entity):
        return hitbox_center(self.world.component_for_entity(entity, CTransform),
                             self.world.component_for_entity(entity, CHitBox))

    def bullet(self, center, direction):
        bullet = create_player_bullet(self.world, self.bullet_info, pygame.Vector2(center), pygame.Vector2(1, 0))
        self.world.component_for_entity(bullet, CVelocity).vel = pygame.Vector2(direction) * 150
        return bullet

    def step(self, points=POINTS, world_size=WORLD):
        system_player_bullet_base(self.world, points, world_size)
        self.world._clear_dead_entities()

    def score(self):
        return ServiceLocator.game_state_service.score

    def explosions(self):
        return len(self.world.get_component(CAnimation))

    def alive(self, entity):
        return self.world.entity_exists(entity)

    def shoot_turret(self, turret, direction=(1, 0)):
        bullet = self.bullet(self.center(turret), direction)
        self.step()
        return bullet

    def shoot_core(self, base, direction=None):
        c_base = self.parts(base)
        axis = pygame.Vector2(1, 0) if c_base.orientation == H else pygame.Vector2(0, 1)
        direction = axis if direction is None else pygame.Vector2(direction)
        # Justo antes del centro, sobre el eje: la bala ya solapa la hitbox del núcleo.
        bullet = self.bullet(self.center(c_base.core) - axis * 3, direction)
        self.step()
        return bullet


class TestTorretas(BaseTestCase):
    def test_torreta_destruida_suma_explota_y_borra_la_bala(self):
        base = self.base()
        turret = self.parts(base).turrets[2]
        bullet = self.shoot_turret(turret)
        self.assertEqual(self.score(), 200)
        self.assertFalse(self.alive(turret))
        self.assertFalse(self.alive(bullet))
        self.assertEqual(self.explosions(), 1)
        self.assertNotIn(turret, self.parts(base).turrets)
        self.assertEqual(len(self.parts(base).turrets), 5)
        self.assertTrue(self.alive(base))

    def test_seis_torretas_una_a_una_tumban_la_base(self):
        base = self.base()
        core = self.parts(base).core
        for index, turret in enumerate(list(self.parts(base).turrets)):
            self.assertTrue(self.alive(base))
            self.shoot_turret(turret)
            self.assertEqual(self.score(), 200 * (index + 1) + (1500 if index == 5 else 0))
        self.assertEqual(self.score(), 2700)
        self.assertFalse(self.alive(base))
        self.assertFalse(self.alive(core))
        # Seis torretas, el núcleo y el cuerpo.
        self.assertEqual(self.explosions(), 8)

    def test_torretas_abiertas_y_cerradas_se_destruyen_igual(self):
        base = self.base()
        opened, closed = self.parts(base).turrets[:2]
        self.world.component_for_entity(opened, CTurret).state = TurretState.OPEN
        self.shoot_turret(opened)
        self.shoot_turret(closed)
        self.assertEqual(self.score(), 400)
        self.assertFalse(self.alive(opened))
        self.assertFalse(self.alive(closed))

    def test_torreta_destruida_no_dispara_mas(self):
        base = self.base()
        turrets = list(self.parts(base).turrets)
        for turret in turrets:
            c_tu = self.world.component_for_entity(turret, CTurret)
            c_tu.time_to_fire = 0
        for turret in turrets[:5]:
            self.shoot_turret(turret)
        system_turret(self.world, 0.01, pygame.Vector2(CENTER), BASE_INFO["bullet"], WORLD)
        shooters = {self.world.component_for_entity(b, CTransform).pos.distance_to(self.center(turrets[5])) < 5
                    for b, _ in self.world.get_component(CTagEnemyBullet)}
        self.assertEqual(len(self.world.get_component(CTagEnemyBullet)), 1)
        self.assertEqual(shooters, {True})


class TestNucleo(BaseTestCase):
    def test_nucleo_con_base_intacta_vale_1500(self):
        for orientation in (H, V):
            with self.subTest(orientation=orientation):
                self.reset()
                base = self.base(orientation)
                parts = self.parts(base)
                pieces = [base, parts.core, *parts.turrets]
                before = self.explosions()
                bullet = self.shoot_core(base)
                self.assertEqual(self.score(), 1500)
                self.assertFalse(self.alive(bullet))
                self.assertFalse(any(self.alive(p) for p in pieces))
                self.assertEqual(self.explosions() - before, 8)

    def test_nucleo_tras_n_torretas(self):
        for n in range(6):
            with self.subTest(n=n):
                self.reset()
                base = self.base()
                for turret in list(self.parts(base).turrets[:n]):
                    self.shoot_turret(turret)
                self.shoot_core(base)
                self.assertEqual(self.score(), 200 * n + 1500)
                self.assertFalse(self.alive(base))

    def test_rumbo_al_nucleo(self):
        cases = [
            (H, (1, 0), True), (H, (-1, 0), True), (H, (1, 0.5), True),
            (H, (0, 1), False), (H, (0, -1), False), (H, (1, 1), False), (H, (0, 0), False),
            (V, (0, 1), True), (V, (0, -1), True), (V, (-0.5, -1), True),
            (V, (1, 0), False), (V, (-1, 0), False), (V, (-1, 1), False), (V, (0, 0), False),
        ]
        for orientation, direction, expected in cases:
            with self.subTest(orientation=orientation, direction=direction):
                self.assertEqual(heading_hits_core(pygame.Vector2(direction), orientation), expected)

    def test_rumbo_invalido_gasta_la_bala_sin_danar(self):
        for orientation, direction in ((H, (0, 1)), (H, (0, -1)), (H, (1, -1)), (H, (0, 0)),
                                       (V, (1, 0)), (V, (-1, 0)), (V, (1, 1)), (V, (0, 0))):
            with self.subTest(orientation=orientation, direction=direction):
                self.reset()
                base = self.base(orientation)
                core = self.parts(base).core
                bullet = self.bullet(self.center(core), direction)
                self.step()
                self.assertFalse(self.alive(bullet))
                self.assertTrue(self.alive(base))
                self.assertTrue(self.alive(core))
                self.assertEqual(len(self.parts(base).turrets), 6)
                self.assertEqual(self.score(), 0)

    def test_rumbo_valido_en_los_dos_sentidos(self):
        for orientation, direction in ((H, (1, 0)), (H, (-1, 0)), (V, (0, 1)), (V, (0, -1))):
            with self.subTest(orientation=orientation, direction=direction):
                self.reset()
                base = self.base(orientation)
                self.shoot_core(base, direction)
                self.assertFalse(self.alive(base))
                self.assertEqual(self.score(), 1500)


class TestGeometria(BaseTestCase):
    def test_corredor_libre_por_el_eje_hasta_el_nucleo(self):
        """Con los turret_offsets de base.json, una bala que avanza por el eje llega al
        núcleo sin tocar ninguna torreta, en las dos orientaciones y los dos sentidos."""
        bullet_size = pygame.Vector2(self.bullet_info["size"]["w"], self.bullet_info["size"]["h"])
        turret_hitbox = BASE_INFO["turret"]["hitbox"]["size"]
        core_hitbox = BASE_INFO["core"]["hitbox"]["size"]
        for orientation in (H, V):
            rotated = orientation == V
            t_size = pygame.Vector2(turret_hitbox["w"], turret_hitbox["h"])
            c_size = pygame.Vector2(core_hitbox["w"], core_hitbox["h"])
            if rotated:
                t_size, c_size = pygame.Vector2(t_size.y, t_size.x), pygame.Vector2(c_size.y, c_size.x)
            turrets = [rotate_offset(pygame.Vector2(o["x"], o["y"]), orientation)
                       for o in BASE_INFO["turret_offsets"]]
            axis = rotate_offset(pygame.Vector2(1, 0), orientation)
            for sense in (1, -1):
                with self.subTest(orientation=orientation, sense=sense):
                    reached = False
                    for step in range(80, -1, -1):
                        pos = axis * step * sense
                        if hitboxes_overlap(pos, bullet_size, pygame.Vector2(0, 0), c_size):
                            reached = True
                            break
                        for turret in turrets:
                            self.assertFalse(hitboxes_overlap(pos, bullet_size, turret, t_size),
                                             f"la bala toca la torreta {turret} en {pos}")
                    self.assertTrue(reached)

    def test_bala_por_el_eje_llega_al_nucleo_de_base_intacta(self):
        for orientation in (H, V):
            with self.subTest(orientation=orientation):
                self.reset()
                base = self.base(orientation)
                axis = rotate_offset(pygame.Vector2(1, 0), orientation)
                bullet = self.bullet(CENTER - axis * 60, axis)
                for _ in range(120):
                    if not self.alive(bullet):
                        break
                    c_t = self.world.component_for_entity(bullet, CTransform)
                    c_t.pos += axis
                    self.step()
                self.assertEqual(self.score(), 1500)
                self.assertFalse(self.alive(base))

    def test_las_piezas_conocen_su_base(self):
        base = self.base()
        parts = self.parts(base)
        for piece in [*parts.turrets, parts.core]:
            self.assertEqual(self.world.component_for_entity(piece, CBasePart).base, base)
        self.assertFalse(self.world.has_component(base, CBasePart))


def info_with_offsets(offsets):
    info = copy.deepcopy(BASE_INFO)
    info["turret_offsets"] = [{"x": x, "y": y} for x, y in offsets]
    return info


FAR = [(0, -30), (0, 30), (-30, -30), (30, 30)]


class TestPrioridad(BaseTestCase):
    def test_nucleo_valido_antes_que_torreta(self):
        # Una torreta pegada al núcleo: la bala solapa las dos.
        base = self.base(info=info_with_offsets([(7, 0), (-30, 0)] + FAR))
        bullet = self.bullet(CENTER + pygame.Vector2(4, 0), (1, 0))
        self.step()
        self.assertFalse(self.alive(bullet))
        self.assertFalse(self.alive(base))
        self.assertEqual(self.score(), 1500)

    def test_torreta_antes_que_nucleo_con_rumbo_invalido(self):
        base = self.base(info=info_with_offsets([(7, 0), (-30, 0)] + FAR))
        turret = self.parts(base).turrets[0]
        self.bullet(CENTER + pygame.Vector2(4, 0), (0, 1))
        self.step()
        self.assertFalse(self.alive(turret))
        self.assertTrue(self.alive(base))
        self.assertEqual(self.score(), 200)

    def test_torreta_mas_cercana_sin_importar_el_orden_de_creacion(self):
        for offsets in ([(20, 0), (28, 0)], [(28, 0), (20, 0)]):
            with self.subTest(offsets=offsets):
                self.reset()
                base = self.base(info=info_with_offsets(offsets + FAR))
                near = next(t for t in self.parts(base).turrets
                            if self.center(t) == CENTER + pygame.Vector2(20, 0))
                far = next(t for t in self.parts(base).turrets
                           if self.center(t) == CENTER + pygame.Vector2(28, 0))
                self.bullet(CENTER + pygame.Vector2(23, 0), (0, 1))
                self.step()
                self.assertFalse(self.alive(near))
                self.assertTrue(self.alive(far))
                self.assertEqual(self.score(), 200)

    def test_empate_entre_torretas_gana_la_de_menor_id(self):
        base = self.base(info=info_with_offsets([(28, 0), (20, 0)] + FAR))
        first, second = self.parts(base).turrets[:2]
        self.bullet(CENTER + pygame.Vector2(24, 0), (0, 1))
        self.step()
        self.assertFalse(self.alive(first))
        self.assertTrue(self.alive(second))
        self.assertEqual(self.score(), 200)


class TestVariasBasesYSimultaneos(BaseTestCase):
    def test_dos_bases_no_se_afectan(self):
        a = self.base(H, CENTER)
        b = self.base(V, CENTER + pygame.Vector2(200, 0))
        self.shoot_turret(self.parts(a).turrets[0])
        self.assertEqual(len(self.parts(b).turrets), 6)
        self.shoot_core(a)
        self.assertFalse(self.alive(a))
        self.assertTrue(self.alive(b))
        self.assertTrue(self.alive(self.parts(b).core))
        self.assertTrue(all(self.alive(t) for t in self.parts(b).turrets))
        self.assertEqual(self.score(), 1700)

    def test_dos_balas_sobre_la_misma_torreta(self):
        base = self.base()
        turret = self.parts(base).turrets[0]
        first = self.bullet(self.center(turret), (1, 0))
        second = self.bullet(self.center(turret), (1, 0))
        self.step()
        self.assertEqual(self.score(), 200)
        self.assertFalse(self.alive(first))
        self.assertTrue(self.alive(second))

    def test_dos_balas_sobre_el_nucleo(self):
        base = self.base()
        first = self.bullet(CENTER - pygame.Vector2(3, 0), (1, 0))
        second = self.bullet(CENTER + pygame.Vector2(3, 0), (-1, 0))
        self.step()
        self.assertEqual(self.score(), 1500)
        self.assertFalse(self.alive(base))
        self.assertFalse(self.alive(first))
        self.assertTrue(self.alive(second))
        self.assertEqual(self.explosions(), 8)

    def test_ultima_torreta_y_nucleo_en_el_mismo_paso(self):
        for core_first in (True, False):
            with self.subTest(core_first=core_first):
                self.reset()
                base = self.base()
                turrets = list(self.parts(base).turrets)
                for turret in turrets[:5]:
                    self.shoot_turret(turret)
                if core_first:
                    self.bullet(CENTER - pygame.Vector2(3, 0), (1, 0))
                    self.bullet(self.center(turrets[5]), (1, 0))
                else:
                    self.bullet(self.center(turrets[5]), (1, 0))
                    self.bullet(CENTER - pygame.Vector2(3, 0), (1, 0))
                self.step()
                self.assertFalse(self.alive(base))
                # Se procesa primero la bala de menor id. Si es la del núcleo, la de la torreta
                # ya no tiene pieza; si es la de la torreta, el núcleo cayó con la base. El premio
                # de la base se suma una sola vez.
                self.assertEqual(self.score(), 1000 + 1500 if core_first else 1000 + 200 + 1500)

    def test_destroy_base_es_idempotente(self):
        base = self.base()
        self.assertEqual(destroy_base(self.world, base, POINTS), 1500)
        explosions = self.explosions()
        self.assertEqual(destroy_base(self.world, base, POINTS), 0)
        self.assertEqual(self.explosions(), explosions)

    def test_cuerpo_deja_de_contar_como_base(self):
        base = self.base()
        self.shoot_core(base)
        self.assertEqual(self.world.get_component(CTagBase), [])


class TestBordesDelMundo(BaseTestCase):
    def test_base_partida_por_el_borde_horizontal(self):
        base = self.base(H, pygame.Vector2(0, 400))
        bullet = self.bullet(pygame.Vector2(WORLD.x - 3, 400), (1, 0))
        self.step()
        self.assertFalse(self.alive(bullet))
        self.assertFalse(self.alive(base))
        self.assertEqual(self.score(), 1500)

    def test_base_partida_por_el_borde_vertical(self):
        base = self.base(V, pygame.Vector2(300, WORLD.y))
        bullet = self.bullet(pygame.Vector2(300, 3), (0, -1))
        self.step()
        self.assertFalse(self.alive(bullet))
        self.assertFalse(self.alive(base))
        self.assertEqual(self.score(), 1500)

    def test_base_partida_por_una_esquina(self):
        base = self.base(H, pygame.Vector2(0, 0))
        turret = next(t for t in self.parts(base).turrets if self.center(t) == pygame.Vector2(-24, -12))
        bullet = self.bullet(pygame.Vector2(WORLD.x - 24, WORLD.y - 12), (0, 1))
        self.step()
        self.assertFalse(self.alive(bullet))
        self.assertFalse(self.alive(turret))
        self.assertEqual(self.score(), 200)


class TestConfiguracion(BaseTestCase):
    def test_puntajes_salen_de_la_configuracion(self):
        points = {"turret": 7, "base": 1000}
        base = self.base()
        self.bullet(self.center(self.parts(base).turrets[0]), (1, 0))
        self.step(points)
        self.assertEqual(self.score(), 7)
        self.bullet(CENTER - pygame.Vector2(3, 0), (1, 0))
        self.step(points)
        self.assertEqual(self.score(), 1007)

    def test_base_json_trae_los_puntajes(self):
        self.assertEqual(POINTS, {"turret": 200, "base": 1500})


class TestOtrasCausasNoDestruyenBases(BaseTestCase):
    def test_bala_de_torreta_no_destruye(self):
        base = self.base()
        core = self.parts(base).core
        create_turret_bullet(self.world, BASE_INFO["bullet"], self.center(core), pygame.Vector2(1, 0))
        create_turret_bullet(self.world, BASE_INFO["bullet"], self.center(self.parts(base).turrets[0]),
                             pygame.Vector2(1, 0))
        self.step()
        self.assertTrue(self.alive(base))
        self.assertEqual(len(self.parts(base).turrets), 6)
        self.assertEqual(self.score(), 0)

    def test_mina_no_destruye(self):
        base = self.base()
        obstacles = ServiceLocator.configs_service.get(ServiceLocator.constants_service.obstacles_config)
        create_mine_blast(self.world, obstacles["mine"]["blast"], pygame.Vector2(CENTER))
        system_mine_blast(self.world, WORLD, pygame.Vector2(-500, -500))
        self.step()
        self.assertTrue(self.alive(base))
        self.assertEqual(len(self.parts(base).turrets), 6)
        self.assertEqual(self.score(), 0)

    def test_choque_del_jugador_no_destruye(self):
        base = self.base()
        size = PLAYER_INFO["size"]
        create_player(self.world, PLAYER_INFO, CENTER - pygame.Vector2(size["w"], size["h"]) / 2)
        constants = ServiceLocator.constants_service
        system_player_death(self.world, PLAYER_INFO["respawn"],
                            ServiceLocator.configs_service.get(constants.obstacles_config), WORLD)
        self.step()
        self.assertTrue(self.alive(base))
        self.assertTrue(self.alive(self.parts(base).core))
        self.assertEqual(len(self.parts(base).turrets), 6)
        self.assertEqual(self.score(), 0)


class TestEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]

    def test_disparo_al_nucleo_destruye_la_base_en_la_escena(self):
        self.scene.start()
        self.scene.skip_blast_off()
        world = self.scene.ecs_world
        bases = sorted(entity for entity, _ in world.get_component(CBase))
        base = bases[0]
        c_base = world.component_for_entity(base, CBase)
        core_center = hitbox_center(world.component_for_entity(c_base.core, CTransform),
                                    world.component_for_entity(c_base.core, CHitBox))
        axis = pygame.Vector2(1, 0) if c_base.orientation == H else pygame.Vector2(0, 1)
        score = ServiceLocator.game_state_service.score
        bullet = create_player_bullet(world, player_bullet_info(), core_center - axis * 3, axis)
        # La bala avanza un poco en el paso, pero sigue sobre el núcleo.
        world.component_for_entity(bullet, CVelocity).vel = axis * 60
        # La base puede quedar fuera de la cámara: que la bala no se borre por eso.
        world.remove_component(bullet, CTagOffscreenDespawn)
        self.scene.simulate(1 / 60)
        self.assertFalse(world.entity_exists(base))
        self.assertEqual(ServiceLocator.game_state_service.score - score, 1500)
        self.assertEqual(len(world.get_component(CTagBase)), len(bases) - 1)
        self.scene.do_draw(self.engine.screen)


if __name__ == "__main__":
    unittest.main()
