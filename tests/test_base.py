"""Pruebas de las bases enemigas (#19). Ejecutar con: python -m unittest discover -s tests"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_base import create_base, create_bases, parse_orientation, rotate_offset
from src.ecs.components.c_base import BaseOrientation, CBase
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_base import CTagBase, CTagBaseCore, CTagBaseTurret
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.scenes.play_scene import BASE_CONFIG, LEVELS_CONFIG

BASE_INFO = {
    "body": {"size": {"w": 60, "h": 40}, "color": {"r": 0, "g": 255, "b": 0}},
    "core": {"size": {"w": 12, "h": 8}, "color": {"r": 255, "g": 0, "b": 0}, "offset": {"x": 0, "y": 0}},
    "turret": {"size": {"w": 10, "h": 6}, "color": {"r": 255, "g": 255, "b": 255}},
    "turret_offsets": [
        {"x": -20, "y": 0}, {"x": -10, "y": -10}, {"x": 10, "y": -10},
        {"x": 20, "y": 0}, {"x": 10, "y": 10}, {"x": -10, "y": 10},
    ],
}


def center_of(world, entity):
    pos = world.component_for_entity(entity, CTransform).pos
    size = world.component_for_entity(entity, CSurface).area.size
    return pos + pygame.Vector2(size) / 2


class TestPrefabBase(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()

    def test_base_tiene_seis_torretas_y_un_nucleo_como_entidades(self):
        base = create_base(self.world, BASE_INFO, pygame.Vector2(100, 100), BaseOrientation.HORIZONTAL)
        c_base = self.world.component_for_entity(base, CBase)
        self.assertEqual(len(c_base.turrets), 6)
        self.assertEqual(len(set(c_base.turrets) | {c_base.core, base}), 8)
        self.assertTrue(self.world.has_component(base, CTagBase))
        for turret in c_base.turrets:
            self.assertEqual(self.world.component_for_entity(turret, CTagBaseTurret).base, base)
        self.assertEqual(self.world.component_for_entity(c_base.core, CTagBaseCore).base, base)

    def test_piezas_horizontales_quedan_en_su_desplazamiento(self):
        center = pygame.Vector2(100, 80)
        base = create_base(self.world, BASE_INFO, center, BaseOrientation.HORIZONTAL)
        c_base = self.world.component_for_entity(base, CBase)
        self.assertEqual(center_of(self.world, base), center)
        self.assertEqual(center_of(self.world, c_base.core), center)
        for turret, offset in zip(c_base.turrets, BASE_INFO["turret_offsets"]):
            self.assertEqual(center_of(self.world, turret), center + pygame.Vector2(offset["x"], offset["y"]))
        self.assertEqual(self.world.component_for_entity(base, CSurface).area.size, (60, 40))

    def test_base_vertical_es_la_horizontal_rotada_90(self):
        center = pygame.Vector2(100, 80)
        base = create_base(self.world, BASE_INFO, center, BaseOrientation.VERTICAL)
        c_base = self.world.component_for_entity(base, CBase)
        self.assertEqual(c_base.orientation, BaseOrientation.VERTICAL)
        self.assertEqual(self.world.component_for_entity(base, CSurface).area.size, (40, 60))
        self.assertEqual(self.world.component_for_entity(c_base.core, CSurface).area.size, (8, 12))
        self.assertEqual(self.world.component_for_entity(c_base.turrets[0], CSurface).area.size, (6, 10))
        for turret, offset in zip(c_base.turrets, BASE_INFO["turret_offsets"]):
            self.assertEqual(center_of(self.world, turret), center + pygame.Vector2(-offset["y"], offset["x"]))

    def test_rotate_offset(self):
        self.assertEqual(rotate_offset(pygame.Vector2(3, 1), BaseOrientation.HORIZONTAL), (3, 1))
        self.assertEqual(rotate_offset(pygame.Vector2(3, 1), BaseOrientation.VERTICAL), (-1, 3))

    def test_piezas_no_tienen_velocidad(self):
        create_base(self.world, BASE_INFO, pygame.Vector2(50, 50), BaseOrientation.HORIZONTAL)
        self.assertEqual(len(self.world.get_component(CTransform)), 8)
        self.assertEqual(self.world.get_component(CVelocity), [])

    def test_cantidad_de_torretas_distinta_de_seis_es_error(self):
        info = dict(BASE_INFO, turret_offsets=BASE_INFO["turret_offsets"][:5])
        with self.assertRaisesRegex(ValueError, "turret_offsets"):
            create_base(self.world, info, pygame.Vector2(0, 0), BaseOrientation.HORIZONTAL)

    def test_create_bases_una_por_entrada_del_nivel(self):
        level = {"bases": [
            {"pos": {"x": 50, "y": 60}, "orientation": "horizontal"},
            {"pos": {"x": 150, "y": 160}, "orientation": "vertical"},
        ]}
        bases = create_bases(self.world, BASE_INFO, level)
        self.assertEqual(len(bases), 2)
        self.assertEqual(center_of(self.world, bases[0]), (50, 60))
        self.assertEqual(center_of(self.world, bases[1]), (150, 160))
        orientations = [self.world.component_for_entity(b, CBase).orientation for b in bases]
        self.assertEqual(orientations, [BaseOrientation.HORIZONTAL, BaseOrientation.VERTICAL])

    def test_nivel_sin_bases_no_crea_nada(self):
        self.assertEqual(create_bases(self.world, BASE_INFO, {}), [])

    def test_orientacion_invalida_da_error_claro(self):
        level = {"bases": [{"pos": {"x": 0, "y": 0}, "orientation": "diagonal"}]}
        with self.assertRaisesRegex(ValueError, r"base #0.*'diagonal'.*horizontal, vertical"):
            create_bases(self.world, BASE_INFO, level)
        with self.assertRaisesRegex(ValueError, "base #0"):
            create_bases(self.world, BASE_INFO, {"bases": [{"pos": {"x": 0, "y": 0}}]})

    def test_parse_orientation(self):
        self.assertEqual(parse_orientation("vertical"), BaseOrientation.VERTICAL)
        with self.assertRaises(ValueError):
            parse_orientation("Horizontal")


class TestBasesEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        # do_draw cachea la fuente de depuración; tras pygame.quit queda inválida.
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]

    def level_info(self):
        levels = ServiceLocator.configs_service.get(LEVELS_CONFIG)["levels"]
        return ServiceLocator.configs_service.get(levels[self.scene.level_index])

    def test_configs_reales_son_validas(self):
        base_info = ServiceLocator.configs_service.get(BASE_CONFIG)
        self.assertEqual(len(base_info["turret_offsets"]), 6)
        orientations = {b["orientation"] for b in self.level_info()["bases"]}
        self.assertEqual(orientations, {"horizontal", "vertical"})

    def test_escena_crea_las_bases_del_nivel_y_no_se_mueven(self):
        self.scene.start()
        world = self.scene.ecs_world
        expected = self.level_info()["bases"]
        bases = sorted(entity for entity, _ in world.get_component(CBase))
        self.assertEqual(len(bases), len(expected))
        for base, entry in zip(bases, expected):
            self.assertEqual(center_of(world, base), (entry["pos"]["x"], entry["pos"]["y"]))
        pieces = [CTagBase, CTagBaseTurret, CTagBaseCore]
        before = {e: pygame.Vector2(c.pos) for e, c in world.get_component(CTransform)
                  if any(world.has_component(e, tag) for tag in pieces)}
        self.assertEqual(len(before), 8 * len(expected))
        for _ in range(30):
            self.scene.simulate(self.engine.fixed_dt)
        for entity, pos in before.items():
            self.assertEqual(world.component_for_entity(entity, CTransform).pos, pos)
        self.scene.do_draw(self.engine.screen)


if __name__ == "__main__":
    unittest.main()
