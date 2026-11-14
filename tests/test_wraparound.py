"""Pruebas del mundo con wraparound (RF-06). Ejecutar con: python -m unittest discover -s tests"""
import unittest

import esper
import pygame

from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_wraparound import system_wraparound
from src.utils.wrap import wrap_position, wrapped_delta

WORLD = pygame.Vector2(100, 80)


class TestWrapFunctions(unittest.TestCase):
    def test_wrap_position_por_la_derecha_y_abajo(self):
        pos = pygame.Vector2(105, 85)
        wrap_position(pos, WORLD)
        self.assertEqual(pos, pygame.Vector2(5, 5))

    def test_wrap_position_por_la_izquierda_y_arriba(self):
        pos = pygame.Vector2(-3, -10)
        wrap_position(pos, WORLD)
        self.assertEqual(pos, pygame.Vector2(97, 70))

    def test_wrapped_delta_cruza_el_borde(self):
        delta = wrapped_delta(pygame.Vector2(95, 75), pygame.Vector2(5, 5), WORLD)
        self.assertEqual(delta, pygame.Vector2(10, 10))

    def test_wrapped_delta_sin_cruzar(self):
        delta = wrapped_delta(pygame.Vector2(10, 10), pygame.Vector2(30, 20), WORLD)
        self.assertEqual(delta, pygame.Vector2(20, 10))


class TestSystemWraparound(unittest.TestCase):
    def test_entidad_que_sale_aparece_del_otro_lado(self):
        world = esper.World()
        entity = world.create_entity(CTransform(pygame.Vector2(101, -2)), CVelocity(pygame.Vector2(10, -10)))
        system_wraparound(world, WORLD)
        self.assertEqual(world.component_for_entity(entity, CTransform).pos, pygame.Vector2(1, 78))

    def test_entidad_sin_velocidad_no_se_toca(self):
        world = esper.World()
        entity = world.create_entity(CTransform(pygame.Vector2(150, 10)))
        system_wraparound(world, WORLD)
        self.assertEqual(world.component_for_entity(entity, CTransform).pos, pygame.Vector2(150, 10))


if __name__ == "__main__":
    unittest.main()
