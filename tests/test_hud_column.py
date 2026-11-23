"""La columna de la derecha (puntaje, condición, minimapa, vidas, ronda) no se sale hacia la zona de juego.

Ejecutar con: python -m unittest discover -s tests
"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_ui import CTagUI
from src.ecs.systems.s_camera import get_camera
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator


class TestHudColumn(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.scene.start()
        self.scene.skip_blast_off()
        self.scene.simulate(1 / 60)

    def test_el_hud_de_la_columna_queda_dentro_de_ella(self):
        column_x = get_camera(self.scene.ecs_world).viewport.right
        screen_w = self.engine.screen.get_width()
        for _, (c_t, c_s, _) in self.scene.ecs_world.get_components(CTransform, CSurface, CTagUI):
            right = c_t.pos.x + c_s.area.width
            if right > column_x and c_s.area.width > 0:
                self.assertGreaterEqual(c_t.pos.x, column_x - 0.5, f"se sale a la izquierda: {c_t.pos}")
                self.assertLessEqual(right, screen_w + 0.5, f"se sale a la derecha: {c_t.pos}")


if __name__ == "__main__":
    unittest.main()
