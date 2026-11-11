"""Pruebas del game loop y las escenas. Ejecutar con: python -m unittest discover -s tests"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.create.prefab_enemy import create_enemy
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_enemy import EnemyType
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.engine.game_engine import GameEngine
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator


class FakeScene(Scene):
    """Escena que registra qué métodos llamó el engine."""

    def __init__(self, game_engine):
        super().__init__(game_engine)
        self.calls = []

    def do_create(self):
        self.calls.append("create")

    def do_update(self, delta_time):
        self.calls.append(("update", delta_time))

    def do_clean(self):
        self.calls.append("clean")


class TestGameEngine(unittest.TestCase):
    def setUp(self):
        # El driver dummy no tiene renderer acelerado para pygame.SCALED; en una ventana real no aparece.
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene_a = FakeScene(self.engine)
        self.scene_b = FakeScene(self.engine)
        self.engine._scenes = {"a": self.scene_a, "b": self.scene_b}
        self.engine._current_scene = self.scene_a

    def test_ventana_usa_la_configuracion(self):
        self.assertEqual(self.engine.screen.get_size(), (256, 208))
        self.assertAlmostEqual(self.engine.fixed_dt, 1 / 60)

    def test_update_corre_solo_pasos_completos(self):
        self.engine._add_frame_time(self.engine.fixed_dt * 2.5)
        self.engine._update()
        self.assertEqual(self.scene_a.calls, [("update", self.engine.fixed_dt)] * 2)
        self.assertAlmostEqual(self.engine._accumulator, self.engine.fixed_dt * 0.5)

    def test_frame_largo_se_limita(self):
        self.engine._add_frame_time(10)
        self.assertEqual(self.engine._accumulator, self.engine.max_frame_time)

    def test_cambio_de_escena_es_diferido(self):
        self.engine.switch_scene("b")
        self.engine._add_frame_time(self.engine.fixed_dt)
        self.engine._update()
        self.assertEqual(self.scene_a.calls, [("update", self.engine.fixed_dt)])
        self.engine._handle_switch_scene()
        self.assertEqual(self.scene_a.calls[-1], "clean")
        self.assertEqual(self.scene_b.calls, ["create"])
        self.assertIs(self.engine._current_scene, self.scene_b)

    def test_sin_cambio_pendiente_sigue_la_misma_escena(self):
        self.engine._handle_switch_scene()
        self.assertIs(self.engine._current_scene, self.scene_a)
        self.assertEqual(self.scene_a.calls, [])


class TestScene(unittest.TestCase):
    def setUp(self):
        # El driver dummy no tiene renderer acelerado para pygame.SCALED; en una ventana real no aparece.
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)

    def test_simulate_borra_las_entidades_eliminadas(self):
        scene = Scene(self.engine)
        entity = scene.ecs_world.create_entity(CTransform(pygame.Vector2(0, 0)))
        scene.ecs_world.delete_entity(entity)
        scene.simulate(self.engine.fixed_dt)
        self.assertFalse(scene.ecs_world.entity_exists(entity))

    def test_clean_vacia_el_mundo(self):
        scene = Scene(self.engine)
        scene.ecs_world.create_entity(CTransform(pygame.Vector2(0, 0)))
        scene.clean()
        self.assertEqual(scene.ecs_world.get_component(CTransform), [])

    def test_escena_de_juego_crea_al_jugador(self):
        scene = self.engine._scenes["play"]
        scene.start()
        self.assertEqual(len(scene.ecs_world.get_component(CTagPlayer)), 1)
        scene.simulate(self.engine.fixed_dt)
        scene.do_draw(self.engine.screen)

    def test_escena_de_juego_mueve_enemigos_hacia_el_jugador_y_los_borra(self):
        scene = self.engine._scenes["play"]
        scene.start()
        player_pos = scene.ecs_world.component_for_entity(scene._player_entity, CTransform).pos
        enemies_info = ServiceLocator.configs_service.get("assets/cfg/enemies.json")
        enemy = create_enemy(scene.ecs_world, enemies_info, player_pos + pygame.Vector2(-60, 0), EnemyType.E)
        start = pygame.Vector2(scene.ecs_world.component_for_entity(enemy, CTransform).pos)

        scene.simulate(self.engine.fixed_dt)
        scene.simulate(self.engine.fixed_dt)
        pos = scene.ecs_world.component_for_entity(enemy, CTransform).pos
        self.assertGreater(pos.x, start.x)

        # E se elimina al agotar su tiempo; simulate limpia la entidad sin errores.
        duration = enemies_info["E"]["states"]["STRAIGHT"]["duration"]
        for _ in range(int(duration / self.engine.fixed_dt) + 2):
            scene.simulate(self.engine.fixed_dt)
        self.assertFalse(scene.ecs_world.entity_exists(enemy))
        self.assertTrue(scene.ecs_world.entity_exists(scene._player_entity))


if __name__ == "__main__":
    unittest.main()
