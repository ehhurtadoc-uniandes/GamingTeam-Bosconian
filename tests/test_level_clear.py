"""Pruebas del paso de nivel (#26) y del indicador de ronda (#32)."""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.ecs.components.c_text import CText
from src.ecs.components.tags.c_tag_base import CTagBase
from src.ecs.systems.s_base_destruction import destroy_base
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.scenes.play_scene import PlayState

DT = 1 / 60


class TestLevelClear(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.game_state = ServiceLocator.game_state_service
        self.game_state.level_index = 0
        self.addCleanup(setattr, self.game_state, "level_index", 0)
        self.scene = self.engine._scenes["play"]
        self.scene.start()
        self.scene.skip_blast_off()
        self.world = self.scene.ecs_world
        levels = ServiceLocator.configs_service.get(ServiceLocator.constants_service.levels_config)
        self.level_count = len(levels["levels"])
        self.clear_delay = levels["clear_delay"]

    def destroy_all_bases(self):
        for base, _ in self.world.get_component(CTagBase):
            destroy_base(self.world, base, {"base": 0})

    def texts(self):
        return [c_text.text for _, c_text in self.world.get_component(CText)]

    def test_muestra_la_ronda(self):
        self.assertIn("ROUND", self.texts())
        self.assertIn("1", self.texts())

    def test_con_bases_sigue_jugando(self):
        self.scene.simulate(DT)
        self.assertEqual(self.scene.state, PlayState.PLAYING)

    def test_sin_bases_espera_y_pasa_a_la_siguiente_ronda(self):
        self.destroy_all_bases()
        self.scene.simulate(DT)
        self.assertEqual(self.scene.state, PlayState.CLEARED)
        self.assertIsNone(self.engine._scene_name_to_switch)
        for _ in range(round(self.clear_delay / DT) + 1):
            self.scene.simulate(DT)
        if self.level_count > 1:
            self.assertEqual(self.engine._scene_name_to_switch, "play")
            self.assertEqual(self.game_state.level_index, 1)
        else:
            self.assertEqual(self.engine._scene_name_to_switch, "title")

    def test_despues_de_la_ultima_ronda_vuelve_al_titulo(self):
        self.game_state.level_index = self.level_count - 1
        self.scene.next_level()
        self.assertEqual(self.engine._scene_name_to_switch, "title")
        self.assertEqual(self.game_state.level_index, 0)

    def test_la_nueva_ronda_conserva_el_puntaje(self):
        self.game_state.score = 1234
        self.engine._current_scene = self.scene
        self.scene.next_level()
        self.engine._handle_switch_scene()
        self.assertEqual(self.game_state.score, 1234)



class TestLosDiezNiveles(unittest.TestCase):
    """Cada ronda de levels.json arranca con sus bases y obstáculos (LC-EG-03, #39)."""

    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.addCleanup(setattr, ServiceLocator.game_state_service, "level_index", 0)
        levels = ServiceLocator.configs_service.get(ServiceLocator.constants_service.levels_config)
        self.paths = levels["levels"]

    def test_hay_al_menos_diez_niveles(self):
        self.assertGreaterEqual(len(self.paths), 10)

    def test_cada_nivel_arranca_con_sus_bases(self):
        scene = self.engine._scenes["play"]
        for index, path in enumerate(self.paths):
            with self.subTest(nivel=path):
                ServiceLocator.game_state_service.level_index = index
                scene.start()
                expected = len(ServiceLocator.configs_service.get(path)["bases"])
                self.assertEqual(len(scene.ecs_world.get_component(CTagBase)), expected)
                self.assertIn(str(index + 1), [c.text for _, c in scene.ecs_world.get_component(CText)])
                scene.clean()


if __name__ == "__main__":
    unittest.main()
