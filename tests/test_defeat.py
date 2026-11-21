"""Pruebas de la escena de derrota con opción de continuar (#37).

Ejecutar con: python -m unittest discover -s tests
"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.ecs.components.c_text import CText
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.engine.services.game_state_service import GameStateService
from src.scenes.defeat_scene import seconds_left

DT = 1 / 60


def key_event(event_type, key):
    return pygame.event.Event(event_type, key=key)


def score_info():
    return ServiceLocator.configs_service.get(ServiceLocator.constants_service.score_config)


class TestContinueGame(unittest.TestCase):
    def setUp(self):
        self.game_state = GameStateService()
        self.game_state.load(score_info())

    def test_continuar_recupera_vidas_y_pierde_el_puntaje(self):
        self.game_state.add_score(12000)
        self.game_state.lives = 0
        self.game_state.level_index = 3
        self.game_state.continue_game()
        self.assertEqual(self.game_state.score, 0)
        self.assertEqual(self.game_state.lives, score_info()["lives"]["initial"])
        self.assertEqual(self.game_state.level_index, 3)
        self.assertEqual(self.game_state.continues_used, 1)

    def test_continuar_conserva_el_hi_score_y_reinicia_la_vida_extra(self):
        self.game_state.add_score(60000)
        hi_score = self.game_state.hi_score
        self.game_state.continue_game()
        self.assertEqual(self.game_state.hi_score, hi_score)
        self.assertEqual(self.game_state.next_extra_life, score_info()["lives"]["extra_life"]["first"])

    def test_se_cuentan_las_naves_perdidas_aunque_sea_la_ultima(self):
        self.game_state.lives = 1
        self.game_state.lose_life()
        self.game_state.lose_life()
        self.assertEqual(self.game_state.lives_lost, 2)

    def test_las_cuentas_sobreviven_a_continuar_y_se_reinician_con_partida_nueva(self):
        self.game_state.lose_life()
        self.game_state.continue_game()
        self.game_state.continue_game()
        self.assertEqual((self.game_state.continues_used, self.game_state.lives_lost), (2, 1))
        self.game_state.new_game()
        self.assertEqual((self.game_state.continues_used, self.game_state.lives_lost), (0, 0))


class TestSecondsLeft(unittest.TestCase):
    def test_redondea_hacia_arriba_y_no_baja_de_cero(self):
        self.assertEqual(seconds_left(5.0), 5)
        self.assertEqual(seconds_left(4.2), 5)
        self.assertEqual(seconds_left(0.01), 1)
        self.assertEqual(seconds_left(-0.5), 0)


class TestDefeatScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        game_state = ServiceLocator.game_state_service
        self.addCleanup(game_state.load, score_info())
        game_state.add_score(3000)
        game_state.lives = 0
        self.scene = self.engine._scenes["defeat"]
        self.scene.start()
        defeat_info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.defeat_config)
        self.continue_time = defeat_info["continue_time"]
        self.input_delay = defeat_info["input_delay"]

    def press(self, key):
        self.scene.process_events(key_event(pygame.KEYDOWN, key))
        self.scene.process_events(key_event(pygame.KEYUP, key))

    def texts(self):
        return {c.text for _, c in self.scene.ecs_world.get_component(CText)}

    def run_for(self, seconds):
        for _ in range(round(seconds / DT)):
            self.scene.simulate(DT)

    def test_muestra_fin_del_juego_la_cuenta_y_las_opciones(self):
        self.scene.simulate(DT)
        self.scene.do_draw(self.engine.screen)
        self.assertTrue({"FIN DEL JUEGO", f"CONTINUAR? {self.continue_time}", "SI", "NO"} <= self.texts())

    def test_la_cuenta_baja_cada_segundo(self):
        self.run_for(1.5)
        self.assertIn(f"CONTINUAR? {self.continue_time - 1}", self.texts())

    def wait_input_delay(self):
        self.run_for(self.input_delay + DT)

    def test_aceptar_si_continua_en_el_mismo_nivel_con_vidas_y_sin_puntaje(self):
        self.wait_input_delay()
        self.press(pygame.K_z)
        game_state = ServiceLocator.game_state_service
        self.assertEqual(self.engine._scene_name_to_switch, "play")
        self.assertEqual(game_state.score, 0)
        self.assertEqual(game_state.lives, score_info()["lives"]["initial"])
        self.assertEqual(game_state.continues_used, 1)

    def test_elegir_no_vuelve_al_titulo_sin_continuar(self):
        self.wait_input_delay()
        self.press(pygame.K_DOWN)
        self.press(pygame.K_z)
        self.assertEqual(self.engine._scene_name_to_switch, "title")
        self.assertEqual(ServiceLocator.game_state_service.continues_used, 0)

    def test_si_no_se_acepta_en_5_segundos_vuelve_al_titulo(self):
        self.run_for(self.continue_time - 0.5)
        self.assertIsNone(self.engine._scene_name_to_switch)
        self.run_for(1.0)
        self.assertEqual(self.engine._scene_name_to_switch, "title")
        self.assertEqual(ServiceLocator.game_state_service.continues_used, 0)

    def test_la_cuenta_vuelve_a_empezar_en_cada_derrota(self):
        self.run_for(3)
        self.scene.clean()
        self.scene.start()
        self.assertEqual(self.scene.time_left, self.continue_time)

    def test_al_entrar_no_se_acepta_hasta_pasado_input_delay(self):
        # Quien seguía disparando con Z al morir no continúa sin ver la pregunta.
        self.press(pygame.K_z)
        self.press(pygame.K_ESCAPE)
        self.assertIsNone(self.engine._scene_name_to_switch)
        self.assertEqual(ServiceLocator.game_state_service.continues_used, 0)
        self.wait_input_delay()
        self.press(pygame.K_z)
        self.assertEqual(self.engine._scene_name_to_switch, "play")

    def test_durante_input_delay_si_se_puede_mover_la_seleccion(self):
        self.press(pygame.K_DOWN)
        self.wait_input_delay()
        self.press(pygame.K_z)
        self.assertEqual(self.engine._scene_name_to_switch, "title")

    def test_aceptar_si_en_el_frame_en_que_vence_la_cuenta_continua(self):
        # El motor procesa los eventos antes del update: la cuenta no debe pisar el SI con el título.
        self.wait_input_delay()
        self.scene.time_left = DT / 2
        self.press(pygame.K_z)
        self.scene.simulate(DT)
        self.assertEqual(self.engine._scene_name_to_switch, "play")
        self.assertEqual(ServiceLocator.game_state_service.continues_used, 1)

    def test_dos_aceptar_en_un_frame_continuan_una_sola_vez(self):
        self.wait_input_delay()
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_z))
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_RETURN))
        self.assertEqual(ServiceLocator.game_state_service.continues_used, 1)
