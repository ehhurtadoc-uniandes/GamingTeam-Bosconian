"""Pruebas de las vidas y su HUD. Ejecutar con: python -m unittest discover -s tests"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_hud import create_lives_hud
from src.ecs.components.c_lives_counter import CLivesCounter
from src.ecs.components.c_lives_icons import CLivesIcons
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_text import CText
from src.ecs.systems.s_lives_hud import system_lives_hud
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.engine.services.game_state_service import GameStateService, next_extra_life_after

SCORE_CONFIG = ServiceLocator.constants_service.score_config


def score_info():
    return ServiceLocator.configs_service.get(SCORE_CONFIG)


class TestLives(unittest.TestCase):
    def setUp(self):
        self.game_state = GameStateService()
        self.game_state.load(score_info())

    def test_umbrales_de_vida_extra(self):
        self.assertEqual(next_extra_life_after(50000, 100000), 100000)
        self.assertEqual(next_extra_life_after(100000, 100000), 200000)
        self.assertEqual(next_extra_life_after(200000, 100000), 300000)

    def test_arranca_con_tres_de_reserva(self):
        self.assertEqual(self.game_state.lives, 3)
        self.assertEqual(self.game_state.next_extra_life, 50000)

    def test_vida_extra_a_los_50000_100000_y_cada_100000(self):
        self.game_state.add_score(49990)
        self.assertEqual(self.game_state.lives, 3)
        self.game_state.add_score(10)
        self.assertEqual(self.game_state.lives, 4)
        self.game_state.add_score(50000)
        self.assertEqual(self.game_state.lives, 5)
        self.game_state.add_score(100000)
        self.assertEqual(self.game_state.lives, 6)
        self.assertEqual(self.game_state.next_extra_life, 300000)

    def test_cruzar_varios_umbrales_de_una_vez_da_una_vida_por_cada_uno(self):
        self.game_state.add_score(250000)
        self.assertEqual(self.game_state.lives, 6)
        self.assertEqual(self.game_state.next_extra_life, 300000)

    def test_perder_una_vida_con_reserva_permite_seguir(self):
        self.assertTrue(self.game_state.lose_life())
        self.assertEqual(self.game_state.lives, 2)

    def test_morir_sin_reserva_termina_la_partida(self):
        self.game_state.lives = 0
        self.assertFalse(self.game_state.lose_life())
        self.assertEqual(self.game_state.lives, 0)

    def test_nueva_partida_reinicia_vidas_y_umbral(self):
        self.game_state.add_score(120000)
        self.game_state.lose_life()
        self.game_state.new_game()
        self.assertEqual(self.game_state.lives, 3)
        self.assertEqual(self.game_state.next_extra_life, 50000)


class TestLivesHud(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        ServiceLocator.game_state_service.load(score_info())
        self.addCleanup(ServiceLocator.game_state_service.load, score_info())
        self.world = esper.World()
        create_lives_hud(self.world, score_info()["lives"]["hud"])

    def icons(self):
        return self.world.get_components(CLivesIcons, CSurface)[0][1]

    def counter_text(self):
        return self.world.get_components(CLivesCounter, CText)[0][1][1].text

    def test_con_tres_vidas_hay_tres_iconos_y_sin_numero(self):
        system_lives_hud(self.world)
        c_icons, c_s = self.icons()
        expected_width = 3 * c_icons.icon_size.x + 2 * c_icons.spacing
        self.assertEqual(c_s.area.size, (expected_width, c_icons.icon_size.y))
        self.assertEqual(self.counter_text(), "")

    def test_con_mas_de_cuatro_se_ven_cuatro_iconos_y_el_total(self):
        ServiceLocator.game_state_service.lives = 6
        system_lives_hud(self.world)
        c_icons, c_s = self.icons()
        self.assertEqual(c_icons.shown, 4)
        self.assertEqual(c_s.area.width, 4 * c_icons.icon_size.x + 3 * c_icons.spacing)
        self.assertEqual(self.counter_text(), "6")

    def test_sin_reserva_no_hay_iconos(self):
        ServiceLocator.game_state_service.lives = 0
        system_lives_hud(self.world)
        self.assertEqual(self.icons()[1].area.width, 0)

    def test_sin_cambios_no_se_redibujan_los_iconos(self):
        system_lives_hud(self.world)
        before = self.icons()[1].surf
        system_lives_hud(self.world)
        self.assertIs(self.icons()[1].surf, before)


class TestPlaySceneLives(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)

    def test_la_escena_de_juego_muestra_las_vidas(self):
        scene = self.engine._scenes["play"]
        scene.start()
        scene.simulate(1 / 60)
        c_icons = scene.ecs_world.get_component(CLivesIcons)[0][1]
        self.assertEqual(c_icons.shown, 3)


if __name__ == "__main__":
    unittest.main()
