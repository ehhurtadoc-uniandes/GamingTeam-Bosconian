"""Pruebas del modo de depuración de enemigos. Ejecutar con: python -m unittest discover -s tests"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.ecs.components.c_enemy_state import CEnemyState, EnemyState
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_enemy import CEnemy, EnemyType
from src.ecs.systems.s_debug_labels import enemy_label
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.scenes.play_scene import random_edge_position


def key_event(event_type, key):
    return pygame.event.Event(event_type, key=key)


class TestDebugEnemies(unittest.TestCase):
    def setUp(self):
        # El driver dummy no tiene renderer acelerado para pygame.SCALED; en una ventana real no aparece.
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.scene.start()

    def enemy_types(self):
        return [c_tag.enemy_type for _, c_tag in self.scene.ecs_world.get_component(CEnemy)]

    def test_teclas_1_2_3_crean_enemigos_i_p_e(self):
        for key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self.scene.process_events(key_event(pygame.KEYDOWN, key))
            self.scene.process_events(key_event(pygame.KEYUP, key))
        self.assertEqual(self.enemy_types(), [EnemyType.I, EnemyType.P, EnemyType.E])

    def test_enemigo_creado_aparece_en_un_borde_y_se_mueve(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_1))
        entity, _ = self.scene.ecs_world.get_component(CEnemy)[0]
        pos = pygame.Vector2(self.scene.ecs_world.component_for_entity(entity, CTransform).pos)
        rect = self.scene.screen_rect
        self.assertTrue(pos.x in (0, rect.width - 8) or pos.y in (0, rect.height - 8))
        self.scene.simulate(1 / 60)
        self.scene.simulate(1 / 60)
        self.assertNotEqual(self.scene.ecs_world.component_for_entity(entity, CTransform).pos, pos)
        self.scene.do_draw(self.engine.screen)

    def test_posicion_en_borde_queda_dentro_de_la_pantalla(self):
        rect = pygame.Rect(0, 0, 256, 208)
        size = pygame.Vector2(8, 8)
        for _ in range(100):
            pos = random_edge_position(rect, size)
            self.assertTrue(0 <= pos.x <= rect.width - size.x and 0 <= pos.y <= rect.height - size.y)
            self.assertTrue(pos.x in (0, rect.width - size.x) or pos.y in (0, rect.height - size.y))

    def test_etiqueta_muestra_tipo_y_estado(self):
        c_es = CEnemyState(EnemyState.LEAVE, {}, {})
        self.assertEqual(enemy_label(CEnemy(EnemyType.I, 50), c_es), "I LEAVE")


if __name__ == "__main__":
    unittest.main()
