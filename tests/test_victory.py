"""Pruebas de la escena de victoria (#36). Ejecutar con: python -m unittest discover -s tests"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.ecs.components.c_text import CText
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator

DT = 1 / 60


def key_event(event_type, key):
    return pygame.event.Event(event_type, key=key)


def config(attr):
    return ServiceLocator.configs_service.get(getattr(ServiceLocator.constants_service, attr))


class TestVictoryScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        game_state = ServiceLocator.game_state_service
        self.addCleanup(game_state.load, config("score_config"))
        game_state.score = 87650
        game_state.lives_lost = 5
        game_state.continues_used = 2
        self.scene = self.engine._scenes["victory"]
        self.scene.start()
        self.accept_delay = config("victory_config")["accept_delay"]

    def press(self, key):
        self.scene.process_events(key_event(pygame.KEYDOWN, key))
        self.scene.process_events(key_event(pygame.KEYUP, key))

    def texts(self):
        return {c.text for _, c in self.scene.ecs_world.get_component(CText)}

    def run_for(self, seconds):
        for _ in range(round(seconds / DT)):
            self.scene.simulate(DT)

    def test_muestra_puntaje_vidas_y_continuaciones(self):
        self.scene.simulate(DT)
        self.scene.do_draw(self.engine.screen)
        self.assertTrue({"MISION CUMPLIDA", "PUNTAJE: 87650", "VIDAS USADAS: 5", "CONTINUACIONES: 2"}
                        <= self.texts())

    def test_al_principio_ignora_las_teclas(self):
        self.press(pygame.K_z)
        self.assertIsNone(self.engine._scene_name_to_switch)

    def test_despues_de_la_espera_z_vuelve_al_titulo(self):
        self.run_for(self.accept_delay + 0.1)
        self.press(pygame.K_z)
        self.assertEqual(self.engine._scene_name_to_switch, "title")

    def test_escape_tambien_vuelve_al_titulo(self):
        self.run_for(self.accept_delay + 0.1)
        self.press(pygame.K_ESCAPE)
        self.assertEqual(self.engine._scene_name_to_switch, "title")


class TestVictoryDesdeElJuego(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.addCleanup(ServiceLocator.cheats_service.load, config("cheats_config"))
        game_state = ServiceLocator.game_state_service
        self.addCleanup(game_state.load, config("score_config"))
        self.addCleanup(setattr, game_state, "level_index", game_state.level_index)
        self.level_count = len(config("levels_config")["levels"])
        game_state.level_index = self.level_count - 1
        self.scene = self.engine._scenes["play"]
        self.engine._current_scene = self.scene
        self.scene.start()
        self.scene.skip_blast_off()

    def test_terminar_la_ultima_ronda_lleva_a_la_victoria_con_los_datos(self):
        game_state = ServiceLocator.game_state_service
        game_state.add_score(4321)
        self.scene.next_level()
        self.engine._handle_switch_scene()
        victory = self.engine._current_scene
        self.assertIs(victory, self.engine._scenes["victory"])
        texts = {c.text for _, c in victory.ecs_world.get_component(CText)}
        self.assertIn(f"PUNTAJE: {game_state.score}", texts)
        self.assertEqual(game_state.level_index, 0)

    def test_la_trampa_n_en_la_ultima_ronda_lleva_a_la_victoria(self):
        ServiceLocator.cheats_service.enabled = True
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_n))
        self.assertEqual(self.engine._scene_name_to_switch, "victory")


if __name__ == "__main__":
    unittest.main()
