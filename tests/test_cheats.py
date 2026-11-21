"""Pruebas del modo trampa (#40). Ejecutar con: python -m unittest discover -s tests"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.ecs.components.c_special_shot import CSpecialShot
from src.ecs.components.c_text import CText
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.ecs.systems.s_player_death import is_vulnerable, kill_player
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.engine.services.cheats_service import CheatsService

DT = 1 / 60


def key_event(event_type, key):
    return pygame.event.Event(event_type, key=key)


def cheats_info():
    return ServiceLocator.configs_service.get(ServiceLocator.constants_service.cheats_config)


def score_info():
    return ServiceLocator.configs_service.get(ServiceLocator.constants_service.score_config)


class TestCheatsService(unittest.TestCase):
    def setUp(self):
        self.cheats = CheatsService()
        self.cheats.load({"enabled": True})

    def test_toggle_activa_y_apaga(self):
        self.assertTrue(self.cheats.toggle("INVINCIBLE"))
        self.assertTrue(self.cheats.is_active("INVINCIBLE"))
        self.assertFalse(self.cheats.toggle("INVINCIBLE"))
        self.assertFalse(self.cheats.is_active("INVINCIBLE"))

    def test_con_el_modo_apagado_ninguna_trampa_cuenta(self):
        self.cheats.toggle("INVINCIBLE")
        self.cheats.enabled = False
        self.assertFalse(self.cheats.is_active("INVINCIBLE"))

    def test_load_arranca_sin_trampas(self):
        self.cheats.toggle("INVINCIBLE")
        self.cheats.load({"enabled": True})
        self.assertFalse(self.cheats.is_active("INVINCIBLE"))

    def test_cada_comando_de_trampa_existe_en_input_json(self):
        input_info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.input_config)
        for command in ServiceLocator.constants_service.cheat_commands:
            self.assertIn(command, input_info)


class TestCheatsEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.addCleanup(ServiceLocator.cheats_service.load, cheats_info())
        game_state = ServiceLocator.game_state_service
        self.addCleanup(game_state.load, score_info())
        self.addCleanup(setattr, game_state, "level_index", game_state.level_index)
        ServiceLocator.cheats_service.enabled = True
        self.scene = self.engine._scenes["play"]
        self.scene.start()
        self.scene.skip_blast_off()
        self.world = self.scene.ecs_world
        self.player = self.world.get_component(CTagPlayer)[0][0]

    def press(self, key):
        self.scene.process_events(key_event(pygame.KEYDOWN, key))
        self.scene.process_events(key_event(pygame.KEYUP, key))

    def texts(self):
        return {c.text for _, c in self.world.get_component(CText)}

    def level_without_special_shot(self):
        """Simula un nivel que no da el disparo especial (level_test.json sí lo da)."""
        self.scene._has_special_shot = False
        if self.world.has_component(self.player, CSpecialShot):
            self.world.remove_component(self.player, CSpecialShot)

    def test_i_hace_invencible_al_jugador_y_avisa(self):
        self.assertTrue(is_vulnerable(self.world, self.player))
        self.press(pygame.K_i)
        self.assertFalse(is_vulnerable(self.world, self.player))
        self.assertIn("INVENCIBLE: SI", self.texts())
        self.press(pygame.K_i)
        self.assertTrue(is_vulnerable(self.world, self.player))

    def test_invencible_la_tecla_de_muerte_no_lo_mata(self):
        self.press(pygame.K_i)
        lives = ServiceLocator.game_state_service.lives
        self.press(pygame.K_l)
        self.assertEqual(ServiceLocator.game_state_service.lives, lives)

    def test_quitar_la_trampa_no_quita_el_disparo_que_da_el_nivel(self):
        self.scene._has_special_shot = True
        self.press(pygame.K_o)
        self.press(pygame.K_o)
        self.assertTrue(self.world.has_component(self.player, CSpecialShot))

    def test_o_da_y_quita_el_disparo_especial(self):
        self.level_without_special_shot()
        self.assertFalse(self.world.has_component(self.player, CSpecialShot))
        self.press(pygame.K_o)
        self.assertTrue(self.world.has_component(self.player, CSpecialShot))
        self.assertIn("DISPARO ESPECIAL: SI", self.texts())
        self.press(pygame.K_o)
        self.assertFalse(self.world.has_component(self.player, CSpecialShot))

    def test_el_disparo_especial_de_la_trampa_sigue_en_el_siguiente_nivel(self):
        self.level_without_special_shot()
        self.press(pygame.K_o)
        self.scene.clean()
        self.scene.start()
        player = self.scene.ecs_world.get_component(CTagPlayer)[0][0]
        self.assertTrue(self.scene.ecs_world.has_component(player, CSpecialShot))

    def test_j_suma_puntos(self):
        before = ServiceLocator.game_state_service.score
        self.press(pygame.K_j)
        self.assertEqual(ServiceLocator.game_state_service.score, before + cheats_info()["score_points"])
        self.assertIn(f"+{cheats_info()['score_points']} PUNTOS", self.texts())

    def test_n_pasa_a_la_siguiente_ronda_y_da_la_vuelta(self):
        levels = ServiceLocator.configs_service.get(ServiceLocator.constants_service.levels_config)["levels"]
        self.press(pygame.K_n)
        self.assertEqual(self.engine._scene_name_to_switch, "play")
        self.assertEqual(ServiceLocator.game_state_service.level_index, 1 % len(levels))

    def test_n_avisa_la_ronda_en_la_escena_nueva(self):
        levels = ServiceLocator.configs_service.get(ServiceLocator.constants_service.levels_config)["levels"]
        self.engine._current_scene = self.scene
        self.press(pygame.K_n)
        self.engine._handle_switch_scene()
        self.world = self.scene.ecs_world
        self.assertIn(f"RONDA {1 % len(levels) + 1}", self.texts())

    def test_n_no_salta_de_ronda_con_el_jugador_muerto(self):
        level_index = ServiceLocator.game_state_service.level_index
        kill_player(self.world, self.player, self.scene._respawn_info)
        self.press(pygame.K_n)
        self.assertIsNone(self.engine._scene_name_to_switch)
        self.assertEqual(ServiceLocator.game_state_service.level_index, level_index)

    def test_solo_se_ve_un_aviso_a_la_vez(self):
        self.press(pygame.K_i)
        self.press(pygame.K_i)
        self.assertNotIn("INVENCIBLE: SI", self.texts())
        self.assertIn("INVENCIBLE: NO", self.texts())
        self.press(pygame.K_j)
        self.assertNotIn("INVENCIBLE: NO", self.texts())

    def test_el_mensaje_desaparece_con_el_tiempo(self):
        self.press(pygame.K_i)
        for _ in range(round((cheats_info()["message_duration"] + 0.2) / DT)):
            self.scene.simulate(DT)
        self.assertNotIn("INVENCIBLE: SI", self.texts())

    def test_con_el_modo_trampa_apagado_las_teclas_no_hacen_nada(self):
        self.level_without_special_shot()
        ServiceLocator.cheats_service.enabled = False
        score = ServiceLocator.game_state_service.score
        self.press(pygame.K_j)
        self.press(pygame.K_o)
        self.assertEqual(ServiceLocator.game_state_service.score, score)
        self.assertFalse(self.world.has_component(self.player, CSpecialShot))

    def test_en_pausa_las_trampas_no_funcionan(self):
        self.press(pygame.K_p)
        score = ServiceLocator.game_state_service.score
        self.press(pygame.K_j)
        self.assertEqual(ServiceLocator.game_state_service.score, score)


if __name__ == "__main__":
    unittest.main()
