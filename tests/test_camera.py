"""Pruebas de la cámara (#6). Ejecutar con: python -m unittest discover -s tests"""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_camera import is_visible, system_camera, view_top_left, world_to_screen
from src.ecs.systems.s_rendering import system_rendering

WORLD = pygame.Vector2(1000, 800)
VIEWPORT = pygame.Rect(0, 0, 200, 100)


def make_camera(center) -> CCamera:
    return CCamera(VIEWPORT, WORLD, pygame.Vector2(center))


class TestCamera(unittest.TestCase):
    def test_centro_de_la_camara_queda_en_el_centro_del_viewport(self):
        cam = make_camera((500, 400))
        self.assertEqual(world_to_screen(cam, pygame.Vector2(500, 400)), pygame.Vector2(100, 50))
        self.assertEqual(world_to_screen(cam, pygame.Vector2(510, 390)), pygame.Vector2(110, 40))

    def test_objeto_del_otro_lado_del_borde_se_ve_cerca(self):
        cam = make_camera((995, 400))
        # x=5 está a 10 px a la derecha cruzando el borde, no a 990 a la izquierda.
        self.assertEqual(world_to_screen(cam, pygame.Vector2(5, 400)), pygame.Vector2(110, 50))
        self.assertTrue(is_visible(cam, pygame.Vector2(5, 400), (8, 8)))

    def test_objeto_lejano_no_es_visible(self):
        cam = make_camera((500, 400))
        self.assertFalse(is_visible(cam, pygame.Vector2(800, 400), (8, 8)))

    def test_system_camera_sigue_al_objetivo_y_guarda_el_movimiento(self):
        world = esper.World()
        world.create_entity(make_camera((995, 400)))
        system_camera(world, pygame.Vector2(1003, 400))  # el jugador cruzó el borde
        cam = world.get_component(CCamera)[0][1]
        self.assertEqual(cam.center, pygame.Vector2(3, 400))
        self.assertEqual(cam.last_move, pygame.Vector2(8, 0))

    def test_view_top_left_da_la_vuelta(self):
        cam = make_camera((50, 20))
        self.assertEqual(view_top_left(cam), pygame.Vector2(950, 770))


class TestRenderingConCamara(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.screen = pygame.Surface((200, 100))
        self.world = esper.World()
        self.world.create_entity(make_camera((500, 400)))

    def tearDown(self):
        pygame.quit()

    def add_square(self, pos):
        surf = CSurface(pygame.Vector2(4, 4), pygame.Color(255, 0, 0))
        return self.world.create_entity(CTransform(pygame.Vector2(pos)), surf)

    def test_dibuja_relativo_a_la_camara(self):
        self.add_square((510, 390))
        system_rendering(self.world, self.screen)
        self.assertEqual(self.screen.get_at((111, 41))[:3], (255, 0, 0))

    def test_no_dibuja_lo_que_no_se_ve(self):
        self.add_square((900, 400))
        system_rendering(self.world, self.screen)
        self.assertEqual(pygame.mask.from_threshold(self.screen, (255, 0, 0), (1, 1, 1, 255)).count(), 0)


if __name__ == "__main__":
    unittest.main()
