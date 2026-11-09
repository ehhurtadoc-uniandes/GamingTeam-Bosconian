"""Pruebas del sistema de movimiento. Ejecutar con: python -m unittest discover -s tests"""
import unittest

import esper
import pygame

from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_movement import system_movement


class TestSystemMovement(unittest.TestCase):
    def test_mueve_segun_velocidad_y_delta(self):
        world = esper.World()
        entity = world.create_entity(CTransform(pygame.Vector2(10, 20)), CVelocity(pygame.Vector2(60, -30)))
        system_movement(world, 0.5)
        self.assertEqual(world.component_for_entity(entity, CTransform).pos, pygame.Vector2(40, 5))

    def test_sin_velocidad_no_se_mueve(self):
        world = esper.World()
        entity = world.create_entity(CTransform(pygame.Vector2(10, 20)))
        system_movement(world, 0.5)
        self.assertEqual(world.component_for_entity(entity, CTransform).pos, pygame.Vector2(10, 20))


if __name__ == "__main__":
    unittest.main()
