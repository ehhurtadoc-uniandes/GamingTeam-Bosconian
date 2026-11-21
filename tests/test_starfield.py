"""Pruebas del fondo de estrellas. Ejecutar con: python -m unittest discover -s tests"""
import unittest

import esper
import pygame

from src.create.prefab_stars import create_starfield
from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_star import CStar
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_background import CTagBackground
from src.ecs.systems.s_starfield import system_starfield

VIEWPORT = pygame.Rect(0, 20, 200, 100)
BLINK = {"speed": 100}


def make_star(world, pos, parallax=0.5, alpha=100.0, rising=True):
    surf = CSurface(pygame.Vector2(1, 1), pygame.Color(255, 255, 255))
    return world.create_entity(CTransform(pygame.Vector2(pos)), surf, CStar(parallax, alpha, rising))


class TestStarfield(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()
        self.camera = CCamera(VIEWPORT, pygame.Vector2(1000, 1000), pygame.Vector2(0, 0))

    def pos(self, entity):
        return self.world.component_for_entity(entity, CTransform).pos

    def test_parallax_se_mueve_una_fraccion_y_al_reves(self):
        star = make_star(self.world, (100, 50), parallax=0.5)
        self.camera.last_move = pygame.Vector2(10, -4)
        system_starfield(self.world, 0.016, self.camera, BLINK)
        self.assertEqual(self.pos(star), pygame.Vector2(95, 52))

    def test_capas_con_distinto_parallax_se_mueven_distinto(self):
        lejos = make_star(self.world, (100, 50), parallax=0.25)
        cerca = make_star(self.world, (100, 50), parallax=0.5)
        self.camera.last_move = pygame.Vector2(8, 0)
        system_starfield(self.world, 0.016, self.camera, BLINK)
        self.assertEqual(self.pos(lejos).x, 98)
        self.assertEqual(self.pos(cerca).x, 96)

    def test_estrella_que_sale_entra_por_el_lado_opuesto(self):
        star = make_star(self.world, (1, 21), parallax=1.0)
        self.camera.last_move = pygame.Vector2(3, 3)
        system_starfield(self.world, 0.016, self.camera, BLINK)
        self.assertEqual(self.pos(star), pygame.Vector2(198, 118))

    def test_brillo_sube_lento_a_velocidad_fija(self):
        star = make_star(self.world, (100, 50), alpha=100.0, rising=True)
        system_starfield(self.world, 0.5, self.camera, BLINK)
        c_s = self.world.component_for_entity(star, CSurface)
        self.assertEqual(self.world.component_for_entity(star, CStar).alpha, 150)
        self.assertEqual(c_s.surf.get_alpha(), 150)

    def test_brillo_rebota_en_255_y_en_0(self):
        arriba = make_star(self.world, (100, 50), alpha=250.0, rising=True)
        abajo = make_star(self.world, (100, 50), alpha=5.0, rising=False)
        system_starfield(self.world, 0.1, self.camera, BLINK)
        self.assertEqual(self.world.component_for_entity(arriba, CStar).alpha, 255)
        self.assertFalse(self.world.component_for_entity(arriba, CStar).rising)
        self.assertEqual(self.world.component_for_entity(abajo, CStar).alpha, 0)
        self.assertTrue(self.world.component_for_entity(abajo, CStar).rising)

    def test_create_starfield_dentro_del_viewport_y_de_fondo(self):
        info = {"count": 30, "size": 1, "layers": [{"parallax": 0.25, "weight": 1}],
                "colors": [{"r": 255, "g": 0, "b": 0}], "blink": BLINK}
        stars = create_starfield(self.world, info, VIEWPORT)
        self.assertEqual(len(stars), 30)
        for star in stars:
            self.assertTrue(VIEWPORT.collidepoint(self.pos(star)))
            self.assertTrue(self.world.has_component(star, CTagBackground))


if __name__ == "__main__":
    unittest.main()
