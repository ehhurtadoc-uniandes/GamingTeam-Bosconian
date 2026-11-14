import json
import unittest
from pathlib import Path

import esper
import pygame

from src.create.prefab_player import create_player
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_player_movement import (snap_to_eight_directions, system_player_acceleration,
                                               system_player_direction)

PLAYER_CFG = Path(__file__).resolve().parent.parent / "assets" / "cfg" / "player.json"
PLAYER_INFO: dict = {}


def setUpModule():
    with open(PLAYER_CFG, encoding="utf-8") as f:
        PLAYER_INFO.update(json.load(f))


def make_player():
    world = esper.World()
    entity = create_player(world, PLAYER_INFO, pygame.Vector2(100, 100))
    return world, entity


class TestPlayerMovement(unittest.TestCase):
    def test_arranca_quieto(self):
        world, entity = make_player()
        self.assertEqual(world.component_for_entity(entity, CVelocity).vel, pygame.Vector2(0, 0))

    def test_acelera_gradualmente(self):
        world, entity = make_player()
        c_pm = world.component_for_entity(entity, CPlayerMovement)
        system_player_acceleration(world, 1.0)
        first = c_pm.speed
        system_player_acceleration(world, 1.0)
        self.assertGreater(first, 0)
        self.assertGreater(c_pm.speed, first)
        self.assertLess(first, c_pm.max_speed)

    def test_no_supera_velocidad_maxima(self):
        world, entity = make_player()
        c_pm = world.component_for_entity(entity, CPlayerMovement)
        system_player_acceleration(world, 1000.0)
        self.assertEqual(c_pm.speed, c_pm.max_speed)
        self.assertAlmostEqual(world.component_for_entity(entity, CVelocity).vel.length(), c_pm.max_speed)

    def test_se_mueve_en_direccion_inicial(self):
        world, entity = make_player()
        system_player_acceleration(world, 1.0)
        system_movement(world, 1.0)
        pos = world.component_for_entity(entity, CTransform).pos
        self.assertEqual(pos.x, 100)
        self.assertLess(pos.y, 100)

    def test_cambia_a_las_ocho_direcciones(self):
        world, entity = make_player()
        c_pm = world.component_for_entity(entity, CPlayerMovement)
        for x in (-1, 0, 1):
            for y in (-1, 0, 1):
                if x == 0 and y == 0:
                    continue
                system_player_direction(world, pygame.Vector2(x, y))
                self.assertAlmostEqual(c_pm.direction.length(), 1.0)
                self.assertAlmostEqual(c_pm.direction.x, pygame.Vector2(x, y).normalize().x)
                self.assertAlmostEqual(c_pm.direction.y, pygame.Vector2(x, y).normalize().y)

    def test_sin_input_mantiene_direccion(self):
        world, entity = make_player()
        c_pm = world.component_for_entity(entity, CPlayerMovement)
        system_player_direction(world, pygame.Vector2(1, 0))
        system_player_direction(world, pygame.Vector2(0, 0))
        self.assertEqual(c_pm.direction, pygame.Vector2(1, 0))

    def test_cambio_de_direccion_conserva_velocidad(self):
        world, entity = make_player()
        c_pm = world.component_for_entity(entity, CPlayerMovement)
        system_player_acceleration(world, 2.0)
        speed = c_pm.speed
        system_player_direction(world, pygame.Vector2(1, 1))
        system_player_acceleration(world, 0.0)
        self.assertAlmostEqual(c_pm.speed, speed)
        self.assertAlmostEqual(world.component_for_entity(entity, CVelocity).vel.length(), speed)

    def test_input_analogico_se_ajusta_a_ocho_direcciones(self):
        world, entity = make_player()
        c_pm = world.component_for_entity(entity, CPlayerMovement)
        system_player_direction(world, pygame.Vector2(0.3, 0.95))
        self.assertEqual(c_pm.direction, pygame.Vector2(1, 1).normalize())
        system_player_direction(world, pygame.Vector2(0.1, -0.9))
        self.assertEqual(c_pm.direction, pygame.Vector2(0, -1))

    def test_drift_de_joystick_no_cambia_direccion(self):
        world, entity = make_player()
        c_pm = world.component_for_entity(entity, CPlayerMovement)
        system_player_direction(world, pygame.Vector2(0.02, 0))
        self.assertEqual(c_pm.direction, pygame.Vector2(0, -1))
        self.assertEqual(snap_to_eight_directions(pygame.Vector2(0.05, -0.1)), pygame.Vector2(0, 0))

    def test_solo_afecta_entidades_con_tag_player(self):
        world, _ = make_player()
        other = world.create_entity()
        world.add_component(other, CPlayerMovement(PLAYER_INFO["movement"]))
        system_player_direction(world, pygame.Vector2(1, 0))
        self.assertEqual(world.component_for_entity(other, CPlayerMovement).direction, pygame.Vector2(0, -1))


class TestCPlayerMovementConfig(unittest.TestCase):
    def test_direccion_inicial_cero_usa_valor_por_defecto(self):
        c_pm = CPlayerMovement({"max_speed": 60, "start_direction": {"x": 0, "y": 0}})
        self.assertEqual(c_pm.direction, pygame.Vector2(0, -1))

    def test_claves_opcionales_tienen_valor_por_defecto(self):
        c_pm = CPlayerMovement({"max_speed": 60})
        self.assertEqual(c_pm.speed, 0)
        self.assertEqual(c_pm.acceleration, 0)
        self.assertEqual(c_pm.direction, pygame.Vector2(0, -1))

    def test_velocidad_inicial_se_limita_a_la_maxima(self):
        c_pm = CPlayerMovement({"max_speed": 60, "initial_speed": 100})
        self.assertEqual(c_pm.speed, 60)


if __name__ == "__main__":
    unittest.main()
