"""Pruebas del paso de nivel (#26) y del indicador de ronda (#32)."""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.ecs.components.c_hitbox import CHitBox, CollisionLayer
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_text import CText
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_base import CTagBase
from src.ecs.systems.s_base_destruction import destroy_base
from src.ecs.systems.s_collision import hitbox_center, hitboxes_overlap
from src.ecs.systems.s_player_death import kill_player
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.scenes.play_scene import PlayState
from tests.test_gamepad import axis

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
        score_info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.score_config)
        self.addCleanup(self.game_state.load, score_info)
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
        self.assertEqual(self.engine._scene_name_to_switch, "play")
        self.assertEqual(self.game_state.level_index, 1)

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


    def kill(self, lives):
        self.game_state.lives = lives
        kill_player(self.world, self.scene._player_entity, self.scene._respawn_info)

    def test_sin_vidas_la_ultima_base_lleva_a_la_derrota(self):
        # La bala que seguía en vuelo destruye la última base cuando la nave ya explotó.
        self.kill(lives=0)
        self.destroy_all_bases()
        for _ in range(round(self.scene._respawn_info["delay"] / DT) + 1):
            self.scene.simulate(DT)
        self.assertNotEqual(self.scene.state, PlayState.CLEARED)
        self.assertEqual(self.engine._scene_name_to_switch, "defeat")
        self.assertEqual(self.game_state.level_index, 0)

    def test_con_vidas_la_ultima_base_pasa_de_ronda_aunque_haya_muerto(self):
        self.kill(lives=2)
        self.destroy_all_bases()
        self.scene.simulate(DT)
        self.assertEqual(self.scene.state, PlayState.CLEARED)

    def pass_round(self):
        self.engine._current_scene = self.scene
        self.scene.next_level()
        self.engine._handle_switch_scene()
        self.world = self.scene.ecs_world
        self.scene.skip_blast_off()

    def direction(self):
        return self.world.component_for_entity(self.scene._player_entity, CPlayerMovement).direction

    def test_la_flecha_presionada_sigue_valiendo_en_la_ronda_nueva(self):
        self.scene.process_events(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        self.pass_round()
        self.assertEqual(self.direction(), pygame.Vector2(1, 0))
        self.scene.process_events(pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT))
        self.assertEqual(self.scene._held_direction_keys, set())

    def test_el_stick_sostenido_sigue_valiendo_y_se_suelta_en_la_ronda_nueva(self):
        self.scene.process_events(axis(0, 1.0))
        self.pass_round()
        self.assertEqual(self.direction(), pygame.Vector2(1, 0))
        self.scene.process_events(axis(0, 0.0))
        self.assertEqual(self.scene._held_direction_keys, set())

    def test_viniendo_de_otra_escena_no_quedan_flechas_presionadas(self):
        self.scene.process_events(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        self.scene.switch_scene("title")
        self.scene.clean()
        self.scene.start()
        self.assertEqual(self.scene._held_direction_keys, set())


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

    def test_ningun_obstaculo_empieza_encima_de_una_base(self):
        scene = self.engine._scenes["play"]
        base_layers = (CollisionLayer.BASE, CollisionLayer.BASE_TURRET, CollisionLayer.BASE_CORE)
        for index, path in enumerate(self.paths):
            with self.subTest(nivel=path):
                ServiceLocator.game_state_service.level_index = index
                scene.start()
                boxes = [(c_h.layer, hitbox_center(c_t, c_h), c_h.size)
                         for _, (c_t, c_h) in scene.ecs_world.get_components(CTransform, CHitBox)]
                obstacles = [(c, s) for layer, c, s in boxes if layer == CollisionLayer.OBSTACLE]
                parts = [(c, s) for layer, c, s in boxes if layer in base_layers]
                self.assertTrue(obstacles)
                for center, size in obstacles:
                    for part_center, part_size in parts:
                        self.assertFalse(hitboxes_overlap(center, size, part_center, part_size, scene.world_size))
                scene.clean()


if __name__ == "__main__":
    unittest.main()
