"""Pruebas del spawner de enemigos (#28). Ejecutar con: python -m unittest discover -s tests"""
import json
import os
import random
import unittest
import warnings
from collections import Counter
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_enemy_spawner import create_enemy_spawner
from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_enemy_spawner import CEnemySpawner
from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_enemy import CTagEnemy, EnemyType
from src.ecs.systems.s_camera import is_visible
from src.ecs.systems.s_enemy_spawner import offscreen_offset, pick_enemy_type, system_enemy_spawner
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator

ROOT = Path(__file__).resolve().parent.parent
ENEMIES = json.loads((ROOT / "assets/cfg/enemies.json").read_text(encoding="utf-8"))
WORLD = pygame.Vector2(1024, 1024)
VIEW = pygame.Rect(0, 0, 256, 208)
DT = 1 / 60

SPAWNER = {"initial_delay": 1.0, "interval": 2.0, "max_alive": 100,
           "weights": {"I": 3, "P": 2, "E": 1}, "wander_scale": 1.0}


def make_camera(center=(500, 500)):
    return CCamera(VIEW, WORLD, pygame.Vector2(center))


def make_world(info=None):
    world = esper.World()
    world.add_component(world.create_entity(), CEnemySpawner(dict(SPAWNER, **(info or {}))))
    return world


def run(world, seconds, camera=None, rng=None):
    camera = camera or make_camera()
    rng = rng or random.Random(3)
    created = []
    for _ in range(round(seconds / DT)):
        created += system_enemy_spawner(world, DT, camera, ENEMIES, 4, rng)
    return created


def spawner_of(world):
    return world.get_component(CEnemySpawner)[0][1]


class TestSpawnerHelpers(unittest.TestCase):
    def test_tipo_con_peso_cero_nunca_sale(self):
        spawner = CEnemySpawner(dict(SPAWNER, weights={"I": 1, "P": 0, "E": 1}))
        rng = random.Random(1)
        picked = {pick_enemy_type(spawner.weights, rng) for _ in range(300)}
        self.assertEqual(picked, {EnemyType.I, EnemyType.E})

    def test_tipos_salen_segun_su_peso(self):
        weights = {EnemyType.I: 3, EnemyType.P: 1}
        rng = random.Random(2)
        counts = Counter(pick_enemy_type(weights, rng) for _ in range(4000))
        self.assertAlmostEqual(counts[EnemyType.I] / 4000, 0.75, delta=0.03)

    def test_posicion_queda_fuera_de_la_vista_y_pegada_al_borde(self):
        size = pygame.Vector2(8, 8)
        view_size = pygame.Vector2(VIEW.size)
        rng = random.Random(4)
        sides = set()
        for _ in range(400):
            off = offscreen_offset(view_size, size, 4, rng)
            rect = pygame.Rect(off, size)
            self.assertFalse(VIEW.colliderect(rect), off)
            # A 4 px del borde: al crecer 10 px ya toca la vista, así que entra enseguida.
            self.assertTrue(VIEW.inflate(2 * (4 + 1), 2 * (4 + 1)).colliderect(rect), off)
            sides.add(("left" if off.x < 0 else "right" if off.x >= view_size.x else "")
                      + ("top" if off.y < 0 else "bottom" if off.y >= view_size.y else ""))
        self.assertTrue({"left", "right", "top", "bottom"} <= {s for s in sides if s in
                                                               ("left", "right", "top", "bottom")})


class TestCEnemySpawner(unittest.TestCase):
    def test_intervalo_cero_es_error(self):
        with self.assertRaises(ValueError):
            CEnemySpawner(dict(SPAWNER, interval=0))

    def test_sin_tipos_con_peso_es_error(self):
        with self.assertRaises(ValueError):
            CEnemySpawner(dict(SPAWNER, weights={"I": 0}))

    def test_tipo_desconocido_es_error(self):
        with self.assertRaises(ValueError):
            CEnemySpawner(dict(SPAWNER, weights={"X": 1}))

    def test_nivel_sin_bloque_spawner_no_crea_spawner(self):
        world = esper.World()
        self.assertIsNone(create_enemy_spawner(world, {"bases": []}))
        self.assertEqual(world.get_component(CEnemySpawner), [])


class TestSystemEnemySpawner(unittest.TestCase):
    def test_no_sale_nada_antes_del_retraso_inicial(self):
        world = make_world()
        self.assertEqual(run(world, 0.9), [])
        self.assertEqual(len(run(world, 0.2)), 1)

    def test_sale_uno_por_intervalo(self):
        world = make_world()
        # 1 s de retraso + 4 intervalos de 2 s = 9 s -> 5 enemigos (en t = 1, 3, 5, 7, 9).
        self.assertEqual(len(run(world, 9.01)), 5)

    def test_respeta_el_maximo_de_enemigos_vivos(self):
        world = make_world({"max_alive": 3})
        run(world, 30)
        self.assertEqual(len(world.get_component(CTagEnemy)), 3)

    def test_vuelve_a_salir_cuando_muere_uno(self):
        world = make_world({"max_alive": 2})
        created = run(world, 4)
        self.assertEqual(len(created), 2)
        world.delete_entity(created[0], immediate=True)
        self.assertEqual(len(run(world, 2.01)), 1)

    def test_inactivo_no_crea_enemigos(self):
        world = make_world()
        spawner_of(world).active = False
        self.assertEqual(run(world, 10), [])

    def test_multiplicador_dos_duplica_el_ritmo(self):
        normal, red = make_world({"initial_delay": 0.0}), make_world({"initial_delay": 0.0})
        spawner_of(red).rate_multiplier = 2.0
        # 9.5 s para no caer justo en un múltiplo del intervalo: normal sale en t = 0, 2, 4, 6, 8 (5)
        # y al doble en t = 0, 1, ..., 9 (10).
        self.assertEqual(len(run(normal, 9.5)), 5)
        self.assertEqual(len(run(red, 9.5)), 10)

    def test_enemigo_nuevo_esta_fuera_de_la_vista_y_dentro_del_mundo(self):
        world = make_world({"initial_delay": 0.0, "interval": 0.1})
        camera = make_camera(center=(5, 1020))  # cerca de dos bordes: la posición debe dar la vuelta
        for entity in run(world, 5, camera):
            pos = world.component_for_entity(entity, CTransform).pos
            self.assertFalse(is_visible(camera, pos, (8, 8)))
            self.assertTrue(0 <= pos.x < WORLD.x and 0 <= pos.y < WORLD.y)

    def test_usa_el_desvio_del_nivel(self):
        world = make_world({"initial_delay": 0.0, "wander_scale": 0.5, "weights": {"I": 1}})
        entity = run(world, DT)[0]
        c_es = world.component_for_entity(entity, CEnemyState)
        expected = ENEMIES["I"]["states"]["CHASE"]["wander_strength"] * 0.5
        self.assertAlmostEqual(c_es.states_info["CHASE"]["wander_strength"], expected)
        self.assertEqual(world.component_for_entity(entity, CTagEnemy).enemy_type, EnemyType.I)


class TestSpawnerEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.scene.start()

    def test_el_nivel_de_prueba_hace_aparecer_enemigos_con_el_tiempo(self):
        self.assertEqual(self.scene.ecs_world.get_component(CTagEnemy), [])
        for _ in range(round(6 / self.engine.fixed_dt)):
            self.scene.simulate(self.engine.fixed_dt)
        self.assertGreater(len(self.scene.ecs_world.get_component(CTagEnemy)), 0)
        self.scene.do_draw(self.engine.screen)


if __name__ == "__main__":
    unittest.main()
