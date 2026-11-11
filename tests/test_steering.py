"""Pruebas de los steering behaviours. Ejecutar con: python -m unittest discover -s tests"""
import random
import unittest

import esper
import pygame

from src.ecs.components.c_steering import CSteering
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_steering import seek, steering_force, system_steering, truncate, wrapped_delta

STEERING = {"max_speed": 70, "max_force": 120, "seek_weight": 1.0,
            "wander_strength": 0.0, "wander_rate": 0.0}


class TestSteeringMath(unittest.TestCase):
    def test_truncate_limita_longitud(self):
        self.assertAlmostEqual(truncate(pygame.Vector2(30, 40), 10).length(), 10)
        self.assertEqual(truncate(pygame.Vector2(3, 4), 10), pygame.Vector2(3, 4))

    def test_seek_desde_reposo_apunta_al_objetivo(self):
        force = seek(pygame.Vector2(10, 0), pygame.Vector2(0, 0), 70)
        self.assertEqual(force, pygame.Vector2(70, 0))

    def test_seek_en_el_objetivo_no_aplica_fuerza(self):
        self.assertEqual(seek(pygame.Vector2(0, 0), pygame.Vector2(5, 5), 70), pygame.Vector2(0, 0))

    def test_wrapped_delta_sin_mundo_es_resta_directa(self):
        self.assertEqual(wrapped_delta(pygame.Vector2(10, 10), pygame.Vector2(250, 10)), pygame.Vector2(240, 0))

    def test_wrapped_delta_cruza_el_borde_si_es_mas_corto(self):
        world = pygame.Vector2(256, 208)
        self.assertEqual(wrapped_delta(pygame.Vector2(10, 10), pygame.Vector2(250, 200), world),
                         pygame.Vector2(-16, -18))

    def test_fuerza_limitada_a_max_force(self):
        c_st = CSteering(STEERING)
        force = steering_force(c_st, pygame.Vector2(0, 0), pygame.Vector2(-70, 0), pygame.Vector2(100, 0))
        self.assertAlmostEqual(force.length(), 120)


class TestSystemSteering(unittest.TestCase):
    def _enemy(self, world, pos, vel=(0, 0), info=None):
        entity = world.create_entity()
        world.add_component(entity, CTransform(pygame.Vector2(pos)))
        world.add_component(entity, CVelocity(pygame.Vector2(vel)))
        world.add_component(entity, CSteering(info or STEERING))
        return entity

    def test_acelera_hacia_el_objetivo_sin_superar_max_speed(self):
        world = esper.World()
        enemy = self._enemy(world, (0, 0))
        for _ in range(120):
            system_steering(world, 1 / 60, pygame.Vector2(1000, 0))
        vel = world.component_for_entity(enemy, CVelocity).vel
        self.assertGreater(vel.x, 0)
        self.assertLessEqual(vel.length(), 70 + 1e-6)

    def test_gira_progresivamente_no_de_golpe(self):
        world = esper.World()
        enemy = self._enemy(world, (0, 0), vel=(-70, 0))
        system_steering(world, 1 / 60, pygame.Vector2(1000, 0))
        self.assertLess(world.component_for_entity(enemy, CVelocity).vel.x, 0)

    def test_constant_speed_gira_aunque_el_objetivo_este_justo_detras(self):
        info = dict(STEERING, constant_speed=True)
        world = esper.World()
        enemy = self._enemy(world, (0, 0), vel=(-70, 0), info=info)
        for _ in range(60):  # 1 s
            system_steering(world, 1 / 60, pygame.Vector2(1000, 0))
        vel = world.component_for_entity(enemy, CVelocity).vel
        # Tasa de giro = 120 / 70 ≈ 1.71 rad/s ≈ 98°/s: tras 1 s ya giró más de 90°.
        self.assertGreater(vel.x, 0)

    def test_constant_speed_mas_fuerza_gira_mas_rapido(self):
        def angle_after(max_force):
            info = dict(STEERING, constant_speed=True, max_force=max_force)
            world = esper.World()
            enemy = self._enemy(world, (0, 0), vel=(0, -70), info=info)
            for _ in range(10):
                system_steering(world, 1 / 60, pygame.Vector2(1000, 0))
            return abs(pygame.Vector2(0, -70).angle_to(world.component_for_entity(enemy, CVelocity).vel))
        self.assertGreater(angle_after(300), angle_after(120))

    def test_constant_speed_mantiene_max_speed_al_girar(self):
        info = dict(STEERING, constant_speed=True)
        world = esper.World()
        enemy = self._enemy(world, (0, 0), vel=(-70, 0), info=info)
        for _ in range(60):
            system_steering(world, 1 / 60, pygame.Vector2(1000, 0))
            self.assertAlmostEqual(world.component_for_entity(enemy, CVelocity).vel.length(), 70)

    def test_wander_es_reproducible_con_semilla(self):
        info = dict(STEERING, wander_strength=0.5, wander_rate=3.0)
        results = []
        for _ in range(2):
            world = esper.World()
            enemy = self._enemy(world, (0, 0), vel=(70, 0), info=info)
            rng = random.Random(7)
            for _ in range(30):
                system_steering(world, 1 / 60, pygame.Vector2(1000, 0), rng=rng)
            results.append(pygame.Vector2(world.component_for_entity(enemy, CVelocity).vel))
        self.assertEqual(results[0], results[1])


if __name__ == "__main__":
    unittest.main()
