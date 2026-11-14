"""Pruebas de los enemigos I, P y E. Ejecutar con: python -m unittest discover -s tests"""
import copy
import json
from pathlib import Path
import random
import unittest

import esper
import pygame

from src.create.prefab_enemy import create_enemy
from src.ecs.components.c_enemy_state import CEnemyState, EnemyState
from src.ecs.components.c_steering import CSteering
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_enemy import CEnemy, EnemyType
from src.ecs.systems.s_enemy_state import change_state, system_enemy_state
from src.ecs.systems.s_steering import flee, system_steering, wrapped_delta

ROOT = Path(__file__).resolve().parents[1]
WORLD_SIZE = pygame.Vector2(256, 208)


class TestEnemyState(unittest.TestCase):
    def setUp(self):
        with (ROOT / "assets" / "cfg" / "enemies.json").open(encoding="utf-8") as file:
            self.enemies_info = json.load(file)
        self.world = esper.World()
        self.target = pygame.Vector2(80, 40)

    def _enemy(self, enemy_type, pos=(40, 40), wander_scale=1.0):
        return create_enemy(self.world, self.enemies_info, pygame.Vector2(pos),
                            enemy_type, wander_scale=wander_scale)

    def _state(self, entity):
        return self.world.component_for_entity(entity, CEnemyState)

    def _steering(self, entity):
        return self.world.component_for_entity(entity, CSteering)

    def _velocity(self, entity):
        return self.world.component_for_entity(entity, CVelocity)

    def _update(self, delta_time):
        system_enemy_state(self.world, delta_time, self.target, WORLD_SIZE)

    def test_i_persigue_hasta_el_limite_y_luego_se_va(self):
        enemy = self._enemy(EnemyType.I)
        duration = self.enemies_info["I"]["states"]["CHASE"]["duration"]
        self._update(duration - 0.01)
        self.assertEqual(self._state(enemy).state, EnemyState.CHASE)
        system_steering(self.world, 0.1, self.target, WORLD_SIZE)
        self.assertGreater(self._velocity(enemy).vel.x, 0)
        self._update(0.02)
        self.assertEqual(self._state(enemy).state, EnemyState.LEAVE)
        self.assertEqual(self._state(enemy).time_in_state, 0)
        self.assertTrue(self.world.entity_exists(enemy))
        self._update(self.enemies_info["I"]["states"]["LEAVE"]["duration"])
        self.assertFalse(self.world.entity_exists(enemy))

    def test_p_pasa_pronto_de_perseguir_a_vagar_y_permanece(self):
        enemy = self._enemy(EnemyType.P)
        duration = self.enemies_info["P"]["states"]["CHASE"]["duration"]
        self.assertLess(duration, self.enemies_info["I"]["states"]["CHASE"]["duration"])
        self._update(duration - 0.01)
        self.assertEqual(self._state(enemy).state, EnemyState.CHASE)
        self._update(0.02)
        self.assertEqual(self._state(enemy).state, EnemyState.WANDER)
        self.assertEqual(self._state(enemy).time_in_state, 0)
        self._update(60)
        self.assertTrue(self.world.entity_exists(enemy))
        self.assertEqual(self._state(enemy).state, EnemyState.WANDER)

    def test_p_en_wander_no_depende_de_la_posicion_del_jugador(self):
        results = []
        for target in (pygame.Vector2(80, 40), pygame.Vector2(0, 100)):
            self.world = esper.World()
            enemy = self._enemy(EnemyType.P)
            self._update(self.enemies_info["P"]["states"]["CHASE"]["duration"])
            self._velocity(enemy).vel = pygame.Vector2(50, 10)
            random.seed(7)  # el mismo azar para los dos objetivos
            for _ in range(30):
                system_enemy_state(self.world, 1 / 60, target, WORLD_SIZE)
                system_steering(self.world, 1 / 60, target, WORLD_SIZE)
            results.append(pygame.Vector2(self._velocity(enemy).vel))
            self.assertNotEqual(results[-1], pygame.Vector2(50, 10))
        self.assertEqual(results[0], results[1])

    def test_p_en_wander_desde_reposo_empieza_a_moverse_al_azar(self):
        enemy = self._enemy(EnemyType.P)
        self._update(self.enemies_info["P"]["states"]["CHASE"]["duration"])
        for _ in range(60):
            system_steering(self.world, 1 / 60, self.target, WORLD_SIZE)
        self.assertGreater(self._velocity(enemy).vel.length(), 0)

    def test_e_apunta_una_vez_y_sigue_recto_aunque_el_jugador_se_mueva(self):
        enemy = self._enemy(EnemyType.E, pos=(10, 40))
        self.target = pygame.Vector2(250, 50)
        self.assertEqual(self._state(enemy).state, EnemyState.AIM)
        self._update(0)
        self.assertEqual(self._state(enemy).state, EnemyState.STRAIGHT)
        expected = wrapped_delta(pygame.Vector2(10, 40), self.target, WORLD_SIZE).normalize()
        expected *= self.enemies_info["E"]["steering"]["max_speed"]
        self.assertLess(expected.x, 0)  # Apunta por el borde más cercano.
        self.assertLess((self._velocity(enemy).vel - expected).length(), 1e-6)
        self.target = pygame.Vector2(50, 70)
        for _ in range(30):
            self._update(1 / 60)
            system_steering(self.world, 1 / 60, self.target, WORLD_SIZE)
            self.assertLess((self._velocity(enemy).vel - expected).length(), 1e-6)
            transform = self.world.component_for_entity(enemy, CTransform)
            transform.pos += self._velocity(enemy).vel / 60
            transform.pos.x %= WORLD_SIZE.x
            transform.pos.y %= WORLD_SIZE.y
        self.assertTrue(self.world.entity_exists(enemy))

    def test_e_sobre_el_jugador_espera_en_aim_hasta_tener_direccion(self):
        enemy = self._enemy(EnemyType.E, pos=(80, 40))
        self._update(1 / 60)
        self.assertEqual(self._state(enemy).state, EnemyState.AIM)
        self.assertEqual(self._velocity(enemy).vel.length(), 0)
        self.target = pygame.Vector2(120, 40)
        self._update(1 / 60)
        self.assertEqual(self._state(enemy).state, EnemyState.STRAIGHT)
        self.assertAlmostEqual(self._velocity(enemy).vel.length(),
                               self.enemies_info["E"]["steering"]["max_speed"])
        self.assertGreater(self._velocity(enemy).vel.x, 0)

    def test_e_se_elimina_al_agotar_su_tiempo_recto(self):
        enemy = self._enemy(EnemyType.E)
        self._update(0)
        self._update(self.enemies_info["E"]["states"]["STRAIGHT"]["duration"])
        self.assertFalse(self.world.entity_exists(enemy))

    def test_entrar_a_cada_estado_aplica_pesos_y_limpia_los_anteriores(self):
        cases = ((EnemyType.I, EnemyState.CHASE, (1, 0, 0.3, 120)),
                 (EnemyType.I, EnemyState.LEAVE, (0, 1, 0, 120)),
                 (EnemyType.P, EnemyState.CHASE, (1, 0, 0.3, 120)),
                 (EnemyType.P, EnemyState.WANDER, (0, 0, 1, 120)),
                 (EnemyType.E, EnemyState.AIM, (0, 0, 0, 0)),
                 (EnemyType.E, EnemyState.STRAIGHT, (0, 0, 0, 0)))
        for enemy_type, state, expected in cases:
            with self.subTest(tipo=enemy_type, estado=state):
                enemy = self._enemy(enemy_type)
                c_st = self._steering(enemy)
                c_es = self._state(enemy)
                c_st.seek_weight = c_st.flee_weight = c_st.wander_strength = 9
                c_st.max_force = 999
                c_es.time_in_state = 3
                change_state(c_es, c_st, state)
                self.assertEqual(c_es.state, state)
                self.assertEqual(c_es.time_in_state, 0)
                self.assertEqual((c_st.seek_weight, c_st.flee_weight,
                                  c_st.wander_strength, c_st.max_force), expected)

    def test_eliminar_por_alejarse_no_deja_entidad_en_los_sistemas(self):
        for enemy_type, state in ((EnemyType.I, EnemyState.LEAVE),
                                  (EnemyType.E, EnemyState.STRAIGHT)):
            with self.subTest(tipo=enemy_type):
                self.world = esper.World()
                enemy = self._enemy(enemy_type, pos=(0, 40))
                change_state(self._state(enemy), self._steering(enemy), state)
                self.target = pygame.Vector2(110, 40)
                self._velocity(enemy).vel = pygame.Vector2(-70, 0)
                self._update(0)
                self.assertFalse(self.world.entity_exists(enemy))
                # El borrado es diferido (como en el curso): el motor vacía las
                # entidades muertas al final de cada frame.
                self.world._clear_dead_entities()
                self.assertNotIn(enemy, [entity for entity, _ in self.world.get_components(
                    CTransform, CVelocity, CSteering, CEnemyState)])

    def test_wraparound_no_elimina_un_enemigo_cercano_al_otro_borde(self):
        for enemy_type, state in ((EnemyType.I, EnemyState.LEAVE),
                                  (EnemyType.E, EnemyState.STRAIGHT)):
            with self.subTest(tipo=enemy_type):
                enemy = self._enemy(enemy_type, pos=(10, 40))
                change_state(self._state(enemy), self._steering(enemy), state)
                self.target = pygame.Vector2(250, 40)
                self._velocity(enemy).vel = pygame.Vector2(70, 0)
                self._update(0)
                self.assertTrue(self.world.entity_exists(enemy))

    def test_no_elimina_por_distancia_si_aun_se_acerca(self):
        enemy = self._enemy(EnemyType.E, pos=(0, 40))
        self.target = pygame.Vector2(110, 40)
        self._update(0)
        self._update(0.1)
        self.assertTrue(self.world.entity_exists(enemy))

    def test_leave_aplica_huida_en_el_sistema_de_steering_con_wraparound(self):
        enemy = self._enemy(EnemyType.I, pos=(10, 40))
        self.target = pygame.Vector2(250, 40)
        self._update(self.enemies_info["I"]["states"]["CHASE"]["duration"])
        system_steering(self.world, 0.1, self.target, WORLD_SIZE)
        to_target = wrapped_delta(pygame.Vector2(10, 40), self.target, WORLD_SIZE)
        self.assertLess(self._velocity(enemy).vel.dot(to_target), 0)

    def test_wander_scale_no_modifica_config_y_se_aplica_en_cada_estado(self):
        original = copy.deepcopy(self.enemies_info)
        enemy = self._enemy(EnemyType.P, wander_scale=2)
        self._update(0)
        self.assertAlmostEqual(self._steering(enemy).wander_strength, 0.6)
        self._update(self.enemies_info["P"]["states"]["CHASE"]["duration"])
        self.assertAlmostEqual(self._steering(enemy).wander_strength, 2)
        other = self._enemy(EnemyType.P)
        self._update(0)
        self.assertAlmostEqual(self._steering(other).wander_strength, 0.3)
        self.assertEqual(self.enemies_info, original)

    def test_config_velocidades_superan_jugador_y_puntos_por_tipo(self):
        for enemy_type, points in ((EnemyType.I, 50), (EnemyType.P, 60), (EnemyType.E, 70)):
            with self.subTest(tipo=enemy_type):
                info = self.enemies_info[enemy_type.value]
                self.assertGreater(info["steering"]["max_speed"], 60)
                enemy = self._enemy(enemy_type)
                self.assertEqual(self._steering(enemy).max_speed, info["steering"]["max_speed"])
                self.assertEqual(self.world.component_for_entity(enemy, CEnemy).points, points)
        self.assertGreater(self.enemies_info["E"]["steering"]["max_speed"],
                           self.enemies_info["I"]["steering"]["max_speed"])


class TestFlee(unittest.TestCase):
    def test_flee_desde_reposo_aleja_del_objetivo(self):
        to_target = pygame.Vector2(30, 40)
        force = flee(to_target, pygame.Vector2(0, 0), 70)
        self.assertLess(force.dot(to_target), 0)
        self.assertAlmostEqual(force.length(), 70)

    def test_flee_frena_si_se_mueve_hacia_el_objetivo(self):
        self.assertEqual(flee(pygame.Vector2(10, 0), pygame.Vector2(20, 0), 70),
                         pygame.Vector2(-90, 0))

    def test_flee_sin_direccion_no_genera_fuerza_invalida(self):
        self.assertEqual(flee(pygame.Vector2(0, 0), pygame.Vector2(5, 5), 70),
                         pygame.Vector2(0, 0))


if __name__ == "__main__":
    unittest.main()
