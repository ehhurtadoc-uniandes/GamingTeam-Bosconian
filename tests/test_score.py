"""Pruebas del puntaje. Ejecutar con: python -m unittest discover -s tests"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_hud import create_score_hud
from src.ecs.components.c_text import CText
from src.ecs.components.c_score_text import CScoreText, ScoreKind
from src.ecs.systems.s_score import system_score_hud
from src.engine.game_engine import GameEngine
from src.engine.services.game_state_service import GameStateService
from src.engine.service_locator import ServiceLocator

SCORE_CONFIG = ServiceLocator.constants_service.score_config


def score_texts(world):
    return {c_tag.kind: c_text.text for _, (c_text, c_tag) in world.get_components(CText, CScoreText)}


class TestScore(unittest.TestCase):
    def setUp(self):
        self.game_state = GameStateService()
        self.game_state.load(ServiceLocator.configs_service.get(SCORE_CONFIG))

    def test_hi_score_inicia_en_20000(self):
        self.assertEqual(self.game_state.hi_score, 20000)
        self.assertEqual(self.game_state.score, 0)

    def test_sumar_sin_superar_no_cambia_el_hi_score(self):
        self.game_state.add_score(1500)
        self.assertEqual(self.game_state.score, 1500)
        self.assertEqual(self.game_state.hi_score, 20000)

    def test_al_superar_el_hi_score_se_actualiza_al_mismo_tiempo(self):
        self.game_state.add_score(19990)
        self.game_state.add_score(60)
        self.assertEqual(self.game_state.hi_score, 20050)

    def test_nueva_partida_conserva_el_hi_score(self):
        self.game_state.add_score(25000)
        self.game_state.new_game()
        self.assertEqual(self.game_state.score, 0)
        self.assertEqual(self.game_state.hi_score, 25000)


class TestScoreHud(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        ServiceLocator.game_state_service.load(ServiceLocator.configs_service.get(SCORE_CONFIG))
        self.game_state = ServiceLocator.game_state_service
        self.world = esper.World()
        create_score_hud(self.world, ServiceLocator.configs_service.get(SCORE_CONFIG)["hud"])

    def test_hud_tiene_las_etiquetas(self):
        texts = {c_text.text for _, c_text in self.world.get_component(CText)}
        self.assertTrue({"1UP", "HI-SCORE"} <= texts)

    def test_hud_muestra_los_valores_de_la_sesion(self):
        self.game_state.add_score(70)
        system_score_hud(self.world)
        self.assertEqual(score_texts(self.world), {ScoreKind.SCORE: "70", ScoreKind.HI_SCORE: "20000"})


class TestPlaySceneScore(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)

    def test_el_puntaje_sobrevive_al_cambio_de_escena(self):
        scene = self.engine._scenes["play"]
        scene.start()
        ServiceLocator.game_state_service.add_score(200)
        scene.clean()
        scene.start()
        scene.simulate(1 / 60)
        self.assertEqual(score_texts(scene.ecs_world)[ScoreKind.SCORE], "200")


if __name__ == "__main__":
    unittest.main()
