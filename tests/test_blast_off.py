"""Pruebas del inicio de nivel con "BLAST OFF!" (#34). Ejecutar con: python -m unittest discover -s tests"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.ecs.components.c_enemy import CEnemy
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_text import CText
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.ecs.components.tags.c_tag_player_bullet import CTagPlayerBullet
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.scenes.play_scene import PlayState

DT = 1 / 60


def key_event(event_type, key):
    return pygame.event.Event(event_type, key=key)


class TestBlastOff(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.scene.start()
        self.world = self.scene.ecs_world
        self.player = self.world.get_component(CTagPlayer)[0][0]
        info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.blast_off_config)
        self.duration = info["duration"]
        self.text = info["text"]["text"]

    def press(self, key):
        self.scene.process_events(key_event(pygame.KEYDOWN, key))
        self.scene.process_events(key_event(pygame.KEYUP, key))

    def texts(self):
        return {c.text for _, c in self.world.get_component(CText)}

    def player_pos(self):
        return pygame.Vector2(self.world.component_for_entity(self.player, CTransform).pos)

    def run_for(self, seconds):
        for _ in range(round(seconds / DT)):
            self.scene.simulate(DT)

    def test_el_nivel_empieza_con_blast_off(self):
        self.assertEqual(self.scene.state, PlayState.STARTING)
        self.assertIn(self.text, self.texts())
        self.scene.simulate(DT)
        self.scene.do_draw(self.engine.screen)

    def test_durante_el_blast_off_el_jugador_no_se_mueve(self):
        before = self.player_pos()
        self.run_for(self.duration - 0.2)
        self.assertEqual(self.player_pos(), before)
        self.assertEqual(self.world.get_component(CEnemy), [])

    def test_al_terminar_desaparece_el_texto_y_el_juego_arranca(self):
        before = self.player_pos()
        self.run_for(self.duration + 0.1)
        self.assertEqual(self.scene.state, PlayState.PLAYING)
        self.assertNotIn(self.text, self.texts())
        self.run_for(0.1)
        self.assertNotEqual(self.player_pos(), before)

    def test_durante_el_blast_off_no_se_dispara_ni_se_pausa(self):
        self.press(pygame.K_z)
        self.press(pygame.K_p)
        self.assertEqual(self.world.get_component(CTagPlayerBullet), [])
        self.assertEqual(self.scene.state, PlayState.STARTING)

    def test_la_flecha_presionada_durante_el_blast_off_cuenta_al_arrancar(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_RIGHT))
        self.run_for(self.duration + 0.1)
        direction = self.world.component_for_entity(self.player, CPlayerMovement).direction
        self.assertEqual(direction, pygame.Vector2(1, 0))

    def test_el_hud_muestra_el_hi_score_desde_el_principio(self):
        self.scene.simulate(DT)
        self.assertIn(str(ServiceLocator.game_state_service.hi_score), self.texts())

    def test_skip_blast_off_arranca_de_inmediato(self):
        self.scene.skip_blast_off()
        self.assertEqual(self.scene.state, PlayState.PLAYING)
        self.assertNotIn(self.text, self.texts())
        self.scene.skip_blast_off()
        self.assertEqual(self.scene.state, PlayState.PLAYING)


class TestSoundsService(unittest.TestCase):
    def test_sin_mixer_no_falla(self):
        pygame.mixer.quit()
        ServiceLocator.sounds_service.play("assets/snd/blast_off.ogg")

    def test_el_sonido_del_blast_off_existe(self):
        info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.blast_off_config)
        self.assertTrue(os.path.isfile(info["sound"]))
        self.assertTrue(info["sound"].endswith(".ogg"))


if __name__ == "__main__":
    unittest.main()
