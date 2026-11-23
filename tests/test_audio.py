"""Pruebas de los sonidos y la música (#38). Ejecutar con: python -m unittest discover -s tests"""
import os
import re
import unittest
import warnings
from unittest import mock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.ecs.components.c_base import CBase
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.ecs.systems.s_base_destruction import destroy_base
from src.ecs.systems.s_player_death import kill_player
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.engine.services.sounds_service import SoundsService

DT = 1 / 60


def config(attr):
    return ServiceLocator.configs_service.get(getattr(ServiceLocator.constants_service, attr))


def key_event(event_type, key):
    return pygame.event.Event(event_type, key=key)


class TestSoundsConfig(unittest.TestCase):
    def setUp(self):
        self.sounds_info = config("sounds_config")

    def test_cada_archivo_de_sonido_y_musica_existe_y_es_ogg(self):
        for path in [*self.sounds_info["effects"].values(), *self.sounds_info["music"].values()]:
            self.assertTrue(os.path.isfile(path), path)
            self.assertTrue(path.endswith(".ogg"), path)

    def test_cada_efecto_que_usa_el_codigo_esta_en_sounds_json(self):
        used = set()
        for folder, _, files in os.walk("src"):
            for name in files:
                if name.endswith(".py"):
                    with open(os.path.join(folder, name), encoding="utf-8") as file:
                        text = file.read()
                    used |= set(re.findall(r'play_effect\("([A-Z_]+)"\)', text))
        self.assertTrue(used)
        self.assertLessEqual(used, set(self.sounds_info["effects"]))

    def test_la_musica_de_cada_escena_y_ronda_esta_en_sounds_json(self):
        music = set(self.sounds_info["music"])
        for attr in ("title_config", "instructions_config", "credits_config", "victory_config", "defeat_config"):
            self.assertIn(config(attr)["music"], music, attr)
        self.assertLessEqual(set(self.sounds_info["level_music"]), music)


class TestSoundsService(unittest.TestCase):
    def setUp(self):
        self.sounds = SoundsService()
        self.sounds.load(config("sounds_config"))

    def test_las_rondas_turnan_las_pistas(self):
        level_music = config("sounds_config")["level_music"]
        self.assertEqual(self.sounds.level_music(0), level_music[0])
        self.assertNotEqual(self.sounds.level_music(0), self.sounds.level_music(1))
        self.assertEqual(self.sounds.level_music(len(level_music)), level_music[0])

    def test_la_misma_pista_no_vuelve_a_empezar(self):
        with mock.patch("pygame.mixer.get_init", return_value=(22050, -16, 2)), \
                mock.patch("pygame.mixer.music") as music:
            self.sounds.play_music("TITLE")
            self.sounds.play_music("TITLE")
            self.assertEqual(music.load.call_count, 1)
            self.assertEqual(music.play.call_count, 1)
            self.sounds.play_music("VICTORY")
            self.assertEqual(music.load.call_count, 2)
        self.assertEqual(self.sounds.current_music, "VICTORY")

    def test_sin_dispositivo_de_audio_no_falla(self):
        with mock.patch("pygame.mixer.get_init", return_value=None):
            self.sounds.play_effect("PLAYER_FIRE")
            self.sounds.play_music("TITLE")
            self.sounds.pause_music()
            self.sounds.resume_music()
        self.assertEqual(self.sounds.current_music, "TITLE")

    def test_un_efecto_que_no_existe_falla(self):
        with self.assertRaises(KeyError):
            self.sounds.play_effect("NO_EXISTE")


class TestAudioEnLasEscenas(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        game_state = ServiceLocator.game_state_service
        self.addCleanup(game_state.load, config("score_config"))
        self.addCleanup(setattr, game_state, "level_index", game_state.level_index)
        self.sounds = ServiceLocator.sounds_service
        patcher = mock.patch.object(self.sounds, "play_effect")
        self.play_effect = patcher.start()
        self.addCleanup(patcher.stop)

    def go_to(self, name):
        self.engine.switch_scene(name)
        self.engine._handle_switch_scene()
        return self.engine._current_scene

    def effects(self):
        return [call.args[0] for call in self.play_effect.call_args_list]

    def start_play(self):
        scene = self.engine._scenes["play"]
        self.engine._current_scene = scene
        scene.start()
        scene.skip_blast_off()
        return scene

    def test_cada_escena_cambia_la_musica(self):
        self.engine._current_scene = self.engine._scenes["title"]
        self.engine._current_scene.start()
        self.assertEqual(self.sounds.current_music, "TITLE")
        self.go_to("instructions")
        self.assertEqual(self.sounds.current_music, "TITLE")
        self.go_to("victory")
        self.assertEqual(self.sounds.current_music, "VICTORY")
        self.go_to("defeat")
        self.assertEqual(self.sounds.current_music, "DEFEAT")

    def test_cada_ronda_tiene_su_musica(self):
        ServiceLocator.game_state_service.level_index = 0
        scene = self.start_play()
        first = self.sounds.current_music
        self.assertEqual(first, self.sounds.level_music(0))
        scene.next_level()
        self.engine._handle_switch_scene()
        self.assertEqual(self.sounds.current_music, self.sounds.level_music(1))
        self.assertNotEqual(self.sounds.current_music, first)

    def test_la_pausa_suena_y_detiene_la_musica(self):
        scene = self.start_play()
        with mock.patch.object(self.sounds, "pause_music") as pause_music, \
                mock.patch.object(self.sounds, "resume_music") as resume_music:
            scene.process_events(key_event(pygame.KEYDOWN, pygame.K_p))
            pause_music.assert_called_once()
            scene.process_events(key_event(pygame.KEYUP, pygame.K_p))
            scene.process_events(key_event(pygame.KEYDOWN, pygame.K_p))
            resume_music.assert_called_once()
        self.assertEqual(self.effects().count("PAUSE"), 2)

    def test_el_disparo_suena(self):
        scene = self.start_play()
        scene.process_events(key_event(pygame.KEYDOWN, pygame.K_z))
        scene.simulate(DT)
        self.assertIn("PLAYER_FIRE", self.effects())

    def test_destruir_una_base_suena_con_sus_explosiones(self):
        scene = self.start_play()
        base = scene.ecs_world.get_component(CBase)[0][0]
        destroy_base(scene.ecs_world, base, scene._base_points)
        self.assertIn("EXPLOSION", self.effects())
        self.assertEqual(self.effects().count("BASE_DESTROYED"), 1)

    def test_la_nave_explota_con_su_propio_sonido(self):
        scene = self.start_play()
        player = scene.ecs_world.get_component(CTagPlayer)[0][0]
        kill_player(scene.ecs_world, player, scene._respawn_info)
        self.assertIn("PLAYER_EXPLOSION", self.effects())

    def test_la_vida_extra_suena_una_vez(self):
        game_state = ServiceLocator.game_state_service
        game_state.new_game()
        game_state.add_score(game_state.next_extra_life - 1)
        self.assertNotIn("EXTRA_LIFE", self.effects())
        game_state.add_score(10 ** 6)
        self.assertEqual(self.effects().count("EXTRA_LIFE"), 1)

    def test_los_menus_suenan_al_moverse_y_al_aceptar(self):
        title = self.engine._scenes["title"]
        self.engine._current_scene = title
        title.start()
        title.process_events(key_event(pygame.KEYDOWN, pygame.K_DOWN))
        title.process_events(key_event(pygame.KEYDOWN, pygame.K_z))
        self.assertEqual(self.effects(), ["MENU_MOVE", "MENU_ACCEPT"])


if __name__ == "__main__":
    unittest.main()
