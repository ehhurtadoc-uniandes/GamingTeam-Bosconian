"""Pruebas del núcleo animado que lanza enemigos E (#27). Ejecutar con: python -m unittest discover -s tests"""
import copy
import json
import os
import unittest
import warnings
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_base import create_base, create_bases, parse_core_mode
from src.create.prefab_enemy_spawner import create_enemy_spawner
from src.ecs.components.c_alert import AlertState
from src.ecs.components.c_base import BaseOrientation, CBase
from src.ecs.components.c_base_core import CBaseCore, CoreMode, CoreState
from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_enemy import CEnemy, EnemyType
from src.ecs.components.c_enemy_spawner import CEnemySpawner
from src.ecs.components.c_enemy_state import CEnemyState, EnemyState
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_leaving_base import CLeavingBase
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.create.prefab_enemy import create_enemy
from src.ecs.systems.s_alert import get_alert
from src.ecs.systems.s_base_core import system_base_core
from src.ecs.systems.s_enemy_bounce import system_enemy_bounce
from src.ecs.systems.s_enemy_spawner import system_enemy_spawner
from src.ecs.systems.s_enemy_state import system_enemy_state
from src.ecs.systems.s_movement import system_movement
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from tests.test_base import BASE_INFO, center_of

ROOT = Path(__file__).resolve().parents[1]
WORLD_SIZE = pygame.Vector2(256, 208)

DURATIONS = {"closed": 2.0, "opening": 0.5, "open": 1.0, "closing": 0.5}
CYCLE = sum(DURATIONS.values())
CORE_INFO = dict(BASE_INFO["core"], durations=DURATIONS, states={
    "closed": {"size": {"w": 4, "h": 2}, "color": {"r": 10, "g": 10, "b": 10}},
    "opening": {"size": {"w": 8, "h": 6}, "color": {"r": 20, "g": 20, "b": 20}},
    "open": {"color": {"r": 30, "g": 30, "b": 30}},
    "closing": {"size": {"w": 6, "h": 4}, "color": {"r": 40, "g": 40, "b": 40}},
})
CORE_BASE_INFO = dict(BASE_INFO, core=CORE_INFO)
STATE_COLORS = {CoreState(name): (look["color"]["r"],) * 3 for name, look in CORE_INFO["states"].items()}
STATE_SIZES = {CoreState.CLOSED: (4, 2), CoreState.OPENING: (8, 6), CoreState.OPEN: (12, 8),
               CoreState.CLOSING: (6, 4)}


def load_enemies_info():
    with (ROOT / "assets" / "cfg" / "enemies.json").open(encoding="utf-8") as file:
        return json.load(file)


class CoreTestCase(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()
        self.enemies_info = load_enemies_info()

    def make_base(self, mode=CoreMode.CYCLING, orientation=BaseOrientation.HORIZONTAL,
                  center=(100, 80), wander_scale=1.0):
        base = create_base(self.world, CORE_BASE_INFO, pygame.Vector2(center), orientation,
                           mode, wander_scale)
        return base, self.world.component_for_entity(base, CBase).core

    def core_state(self, core):
        return self.world.component_for_entity(core, CBaseCore)

    def step(self, delta_time):
        created = system_base_core(self.world, delta_time, self.enemies_info)
        self.world._clear_dead_entities()
        return created

    def enemies(self):
        return [e for e, _ in self.world.get_component(CEnemy)]


class TestModoDelNivel(CoreTestCase):
    def test_sin_bloque_core_es_static(self):
        self.assertEqual(parse_core_mode({}), CoreMode.STATIC)
        self.assertEqual(parse_core_mode({"core": {}}), CoreMode.STATIC)
        self.assertEqual(parse_core_mode({"core": {"mode": "cycling"}}), CoreMode.CYCLING)

    def test_nivel_sin_core_y_static_quedan_abiertos_y_no_lanzan(self):
        for level in ({}, {"core": {"mode": "static"}}):
            with self.subTest(level=level):
                self.world = esper.World()
                level = dict(level, bases=[{"pos": {"x": 50, "y": 50}, "orientation": "horizontal"}])
                base = create_bases(self.world, CORE_BASE_INFO, level)[0]
                core = self.world.component_for_entity(base, CBase).core
                self.assertEqual(self.core_state(core).mode, CoreMode.STATIC)
                self.assertEqual(self.core_state(core).state, CoreState.OPEN)
                surf = self.world.component_for_entity(core, CSurface).surf
                self.assertEqual(surf.get_at((0, 0))[:3], STATE_COLORS[CoreState.OPEN])
                for _ in range(100):
                    self.assertEqual(self.step(0.5), [])
                self.assertEqual(self.core_state(core).state, CoreState.OPEN)
                self.assertEqual(self.enemies(), [])

    def test_create_base_sin_modo_es_static_y_acepta_base_json_viejo(self):
        base = create_base(self.world, BASE_INFO, pygame.Vector2(50, 50), BaseOrientation.HORIZONTAL)
        core = self.world.component_for_entity(base, CBase).core
        self.assertEqual(self.core_state(core).mode, CoreMode.STATIC)
        self.assertEqual(self.step(100.0), [])

    def test_cycling_desde_el_nivel_con_wander_scale_del_spawner(self):
        level = {"core": {"mode": "cycling"}, "spawner": {"wander_scale": 0.5},
                 "bases": [{"pos": {"x": 50, "y": 50}, "orientation": "vertical"}]}
        base = create_bases(self.world, CORE_BASE_INFO, level)[0]
        c_core = self.core_state(self.world.component_for_entity(base, CBase).core)
        self.assertEqual((c_core.mode, c_core.state, c_core.wander_scale),
                         (CoreMode.CYCLING, CoreState.CLOSED, 0.5))
        del level["spawner"]
        base = create_bases(self.world, CORE_BASE_INFO, level)[0]
        self.assertEqual(self.core_state(self.world.component_for_entity(base, CBase).core).wander_scale, 1.0)


class TestCiclo(CoreTestCase):
    def test_empieza_cerrado_y_recorre_los_estados_con_sus_duraciones(self):
        _, core = self.make_base()
        c_core = self.core_state(core)
        self.assertEqual(c_core.state, CoreState.CLOSED)
        expected = [(1.999, CoreState.CLOSED), (0.001, CoreState.OPENING), (0.499, CoreState.OPENING),
                    (0.001, CoreState.OPEN), (0.999, CoreState.OPEN), (0.001, CoreState.CLOSING),
                    (0.499, CoreState.CLOSING), (0.001, CoreState.CLOSED)]
        for delta, state in expected:
            self.step(delta)
            self.assertEqual(c_core.state, state)
        self.assertAlmostEqual(c_core.time_in_state, 0.0, places=6)

    def test_un_e_por_apertura_y_ninguno_mientras_sigue_abierto(self):
        _, core = self.make_base()
        self.assertEqual(self.step(2.25), [])
        created = self.step(0.25)
        self.assertEqual(len(created), 1)
        for _ in range(7):
            self.assertEqual(self.step(0.125), [])
        self.assertEqual(self.core_state(core).state, CoreState.OPEN)
        self.assertEqual(len(self.enemies()), 1)

    def test_un_paso_largo_atraviesa_varias_transiciones_sin_perder_ni_duplicar(self):
        _, core = self.make_base()
        c_core = self.core_state(core)
        # Dos ciclos completos y 2.7 s más: tres aperturas, y queda 0.2 s dentro de OPEN.
        created = self.step(2 * CYCLE + 2.7)
        self.assertEqual(len(created), 3)
        self.assertEqual(c_core.state, CoreState.OPEN)
        self.assertAlmostEqual(c_core.time_in_state, 0.2, places=6)
        self.assertEqual(len(self.step(CYCLE)), 1)

    def test_conserva_el_tiempo_sobrante(self):
        _, core = self.make_base()
        c_core = self.core_state(core)
        self.step(2.3)
        self.assertEqual(c_core.state, CoreState.OPENING)
        self.assertAlmostEqual(c_core.time_in_state, 0.3, places=6)

    def test_e_nace_centrado_en_el_nucleo_y_es_tipo_e(self):
        for orientation in BaseOrientation:
            with self.subTest(orientation=orientation):
                self.world = esper.World()
                _, core = self.make_base(orientation=orientation, wander_scale=0.0)
                created = self.step(2.5)
                self.assertEqual(len(created), 1)
                enemy = created[0]
                self.assertEqual(self.world.component_for_entity(enemy, CEnemy).enemy_type, EnemyType.E)
                self.assertEqual(center_of(self.world, enemy), center_of(self.world, core))
                self.assertEqual(center_of(self.world, core), (100, 80))
                self.assertEqual(self.world.component_for_entity(enemy, CEnemyState).state, EnemyState.AIM)


class TestAspecto(CoreTestCase):
    def test_cada_estado_tiene_su_aspecto_y_mantiene_el_centro_y_la_hitbox(self):
        for orientation in BaseOrientation:
            with self.subTest(orientation=orientation):
                self.world = esper.World()
                center = pygame.Vector2(100, 80)
                _, core = self.make_base(orientation=orientation, center=center)
                hitbox = self.world.component_for_entity(core, CHitBox)
                transform = self.world.component_for_entity(core, CTransform)
                hitbox_center = transform.pos + hitbox.offset + hitbox.size / 2
                for delta, state in [(0, CoreState.CLOSED), (2.0, CoreState.OPENING), (0.5, CoreState.OPEN),
                                     (1.0, CoreState.CLOSING), (0.5, CoreState.CLOSED)]:
                    self.step(delta)
                    self.assertEqual(self.core_state(core).state, state)
                    c_s = self.world.component_for_entity(core, CSurface)
                    w, h = STATE_SIZES[state]
                    expected = (w, h) if orientation == BaseOrientation.HORIZONTAL else (h, w)
                    self.assertEqual(c_s.area.size, expected)
                    self.assertEqual(c_s.surf.get_at((0, 0))[:3], STATE_COLORS[state])
                    self.assertEqual(center_of(self.world, core), center)
                    self.assertEqual(transform.pos + hitbox.offset + hitbox.size / 2, hitbox_center)


class TestBaseInvalida(CoreTestCase):
    def test_base_eliminada_detiene_el_nucleo(self):
        base, core = self.make_base()
        self.world.delete_entity(base, immediate=True)
        self.assertEqual(self.step(10.0), [])
        self.assertEqual(self.core_state(core).state, CoreState.CLOSED)

    def test_base_que_ya_no_apunta_al_nucleo_lo_detiene(self):
        base, core = self.make_base()
        self.world.component_for_entity(base, CBase).core = -1
        self.assertEqual(self.step(10.0), [])
        self.assertEqual(self.core_state(core).time_in_state, 0.0)


class TestIndependenciaDelSpawner(CoreTestCase):
    def camera(self):
        return CCamera(pygame.Rect(0, 0, 256, 208), WORLD_SIZE, pygame.Vector2(128, 104))

    def test_lanza_sin_spawner_inactivo_o_con_el_cupo_lleno(self):
        cases = [None, {"active": False}, {"max_alive": 0}]
        for case in cases:
            with self.subTest(case=case):
                self.world = esper.World()
                self.make_base()
                if case is not None:
                    spawner = create_enemy_spawner(self.world, {"spawner": {
                        "interval": 0.1, "initial_delay": 0.0, "max_alive": case.get("max_alive", 10),
                        "weights": {"I": 1}}})
                    self.world.component_for_entity(spawner, CEnemySpawner).active = case.get("active", True)
                for _ in range(25):
                    system_enemy_spawner(self.world, 0.1, self.camera(), self.enemies_info, 8)
                    self.step(0.1)
                types = [c.enemy_type for _, c in self.world.get_component(CEnemy)]
                self.assertEqual(types.count(EnemyType.E), 1)
                self.assertEqual(types.count(EnemyType.I), 0)

    def test_los_e_del_nucleo_cuentan_para_max_alive_del_spawner(self):
        self.make_base()
        self.step(2.5)
        spawner = create_enemy_spawner(self.world, {"spawner": {
            "interval": 0.1, "initial_delay": 0.0, "max_alive": 1, "weights": {"I": 1}}})
        self.assertEqual(system_enemy_spawner(self.world, 0.1, self.camera(), self.enemies_info, 8), [])
        self.world.component_for_entity(spawner, CEnemySpawner).max_alive = 2
        self.assertEqual(len(system_enemy_spawner(self.world, 0.1, self.camera(), self.enemies_info, 8)), 1)


class TestAimDelE(CoreTestCase):
    def launch(self, center=(100, 80)):
        self.make_base(center=center)
        return self.step(2.5)[0]

    def test_apunta_al_jugador_en_el_mismo_paso_y_mantiene_el_rumbo(self):
        enemy = self.launch()
        # system_enemy_state compara esquinas: la del E está en (96, 76).
        system_enemy_state(self.world, 0.0, pygame.Vector2(196, 76), WORLD_SIZE)
        self.assertEqual(self.world.component_for_entity(enemy, CEnemyState).state, EnemyState.STRAIGHT)
        vel = self.world.component_for_entity(enemy, CVelocity).vel
        self.assertGreater(vel.x, 0)
        self.assertAlmostEqual(vel.y, 0)
        system_enemy_state(self.world, 0.1, pygame.Vector2(100, 0), WORLD_SIZE)
        self.assertEqual(self.world.component_for_entity(enemy, CVelocity).vel, vel)

    def test_con_direccion_cero_sigue_en_aim(self):
        enemy = self.launch()
        pos = pygame.Vector2(self.world.component_for_entity(enemy, CTransform).pos)
        system_enemy_state(self.world, 0.1, pos, WORLD_SIZE)
        self.assertEqual(self.world.component_for_entity(enemy, CEnemyState).state, EnemyState.AIM)

    def test_usa_wraparound_para_apuntar(self):
        # Con el jugador a la derecha pero más cerca cruzando el borde izquierdo, va hacia la izquierda.
        enemy = self.launch(center=(10, 80))
        system_enemy_state(self.world, 0.0, pygame.Vector2(240, 76), WORLD_SIZE)
        self.assertLess(self.world.component_for_entity(enemy, CVelocity).vel.x, 0)


class TestSalidaDeLaBase(CoreTestCase):
    """El E nace dentro del cuerpo de su base: debe salir hacia el jugador sin rebotar en ella."""

    def run_steps(self, target, steps):
        for _ in range(steps):
            system_enemy_state(self.world, 1 / 60, pygame.Vector2(target))
            system_movement(self.world, 1 / 60)
            system_enemy_bounce(self.world)
            self.world._clear_dead_entities()

    def test_sale_hacia_el_jugador_sin_saltar_al_borde_ni_invertir_el_rumbo(self):
        # La E está en (96, 76) al nacer (centro del núcleo en (100, 80)).
        for target, direction in [((96, 200), (0, 1)), ((96, -100), (0, -1)), ((250, 76), (1, 0))]:
            with self.subTest(target=target):
                self.world = esper.World()
                self.make_base()
                enemy = self.step(2.5)[0]
                start = pygame.Vector2(self.world.component_for_entity(enemy, CTransform).pos)
                self.run_steps(target, 1)
                moved = self.world.component_for_entity(enemy, CTransform).pos - start
                speed = self.world.component_for_entity(enemy, CVelocity).vel.length()
                # Un paso de movimiento normal, sin empujones de system_enemy_bounce.
                self.assertAlmostEqual(moved.length(), speed / 60, places=4)
                self.assertGreater(moved.dot(pygame.Vector2(direction)), 0)
                self.run_steps(target, 40)
                self.assertGreater(self.world.component_for_entity(enemy, CVelocity).vel
                                   .dot(pygame.Vector2(direction)), 0)
                self.assertFalse(self.world.has_component(enemy, CLeavingBase))

    def test_al_salir_vuelve_a_rebotar_contra_la_base(self):
        self.make_base()
        enemy = self.step(2.5)[0]
        self.assertTrue(self.world.has_component(enemy, CLeavingBase))
        self.run_steps((96, 200), 40)
        self.assertFalse(self.world.has_component(enemy, CLeavingBase))
        # Si se le hace volver hacia la base, rebota como cualquier enemigo.
        self.world.component_for_entity(enemy, CVelocity).vel = pygame.Vector2(0, -100)
        for _ in range(60):
            system_movement(self.world, 1 / 60)
            system_enemy_bounce(self.world)
        self.assertGreater(self.world.component_for_entity(enemy, CVelocity).vel.y, 0)

    def test_otro_enemigo_dentro_de_la_base_sigue_rebotando(self):
        self.make_base()
        other = create_enemy(self.world, self.enemies_info, pygame.Vector2(96, 76), EnemyType.E)
        system_enemy_bounce(self.world)
        self.assertNotEqual(self.world.component_for_entity(other, CTransform).pos, (96, 76))


class TestErroresDeConfiguracion(CoreTestCase):
    LEVEL = {"core": {"mode": "cycling"}, "bases": [{"pos": {"x": 0, "y": 0}, "orientation": "horizontal"}]}

    def test_modo_desconocido(self):
        with self.assertRaisesRegex(ValueError, r"core.mode inválido 'animated'.*static, cycling"):
            create_bases(self.world, CORE_BASE_INFO, {"core": {"mode": "animated"}})
        with self.assertRaisesRegex(ValueError, "core debe ser un objeto"):
            create_bases(self.world, CORE_BASE_INFO, {"core": "cycling"})

    def test_duracion_no_positiva_o_faltante(self):
        for value in (0, -1, None, "1", True):
            with self.subTest(value=value):
                info = copy.deepcopy(CORE_BASE_INFO)
                if value is None:
                    del info["core"]["durations"]["open"]
                else:
                    info["core"]["durations"]["open"] = value
                with self.assertRaisesRegex(ValueError, r"base.json: core.durations.open"):
                    create_bases(self.world, info, self.LEVEL)
        info = copy.deepcopy(CORE_BASE_INFO)
        del info["core"]["durations"]
        with self.assertRaisesRegex(ValueError, r"base.json: core.durations"):
            create_bases(self.world, info, self.LEVEL)

    def test_aspecto_incompleto(self):
        info = copy.deepcopy(CORE_BASE_INFO)
        del info["core"]["states"]["closing"]
        with self.assertRaisesRegex(ValueError, r"base.json: core.states.closing"):
            create_bases(self.world, info, {})
        info = copy.deepcopy(CORE_BASE_INFO)
        info["core"]["states"]["opening"] = {"size": {"w": 2, "h": 2}}
        with self.assertRaisesRegex(ValueError, r"core.states.opening.*image.*color"):
            create_bases(self.world, info, self.LEVEL)
        info = copy.deepcopy(CORE_BASE_INFO)
        info["core"]["states"]["open"]["color"] = {"r": 1}
        with self.assertRaisesRegex(ValueError, r"core.states.open.color"):
            create_bases(self.world, info, self.LEVEL)

    def test_no_se_crea_ninguna_base_si_la_config_es_invalida(self):
        with self.assertRaises(ValueError):
            create_bases(self.world, CORE_BASE_INFO, dict(self.LEVEL, core={"mode": "x"}))
        self.assertEqual(self.world.get_component(CBase), [])


TEST_LEVELS = ("assets/cfg/levels/level_test.json", "assets/cfg/levels/level_test_cycling.json")


class TestModoDeLasRondas(unittest.TestCase):
    """Las 10 rondas de levels.json eligen su modo de núcleo, y hay de los dos."""

    def test_cada_ronda_declara_un_modo_valido_y_hay_de_los_dos(self):
        levels = json.loads((ROOT / "assets/cfg/levels.json").read_text(encoding="utf-8"))["levels"]
        modes = []
        for path in levels:
            info = json.loads((ROOT / path).read_text(encoding="utf-8"))
            self.assertIn("core", info, path)
            modes.append(parse_core_mode(info))
        self.assertEqual(set(modes), {CoreMode.STATIC, CoreMode.CYCLING})
        # La dificultad sube: una vez que el núcleo empieza a ciclar, sigue ciclando en las rondas siguientes.
        first_cycling = modes.index(CoreMode.CYCLING)
        self.assertTrue(all(m == CoreMode.CYCLING for m in modes[first_cycling:]))


class TestNucleoEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.addCleanup(setattr, ServiceLocator.game_state_service, "level_index", 0)
        self.scene = self.engine._scenes["play"]
        # Las pruebas juegan los dos niveles de prueba (static y cycling), que no son rondas del juego:
        # se ponen como rondas 1 y 2 en la configuración cargada y se devuelve la lista real al terminar.
        levels_info = ServiceLocator.configs_service.get(ServiceLocator.constants_service.levels_config)
        self.addCleanup(levels_info.__setitem__, "levels", levels_info["levels"])
        levels_info["levels"] = list(TEST_LEVELS)

    def start_level(self, index):
        ServiceLocator.game_state_service.level_index = index
        self.scene.start()
        self.scene.skip_blast_off()
        world = self.scene.ecs_world
        return world, [c for _, c in world.get_component(CBaseCore)]

    def level_info(self, index):
        levels = ServiceLocator.configs_service.get(ServiceLocator.constants_service.levels_config)["levels"]
        return ServiceLocator.configs_service.get(levels[index])

    def test_niveles_de_prueba_tienen_un_modo_cada_uno_y_ambas_orientaciones(self):
        modes = {parse_core_mode(self.level_info(i)) for i in (0, 1)}
        self.assertEqual(modes, {CoreMode.STATIC, CoreMode.CYCLING})
        for index in (0, 1):
            orientations = {b["orientation"] for b in self.level_info(index)["bases"]}
            self.assertEqual(orientations, {"horizontal", "vertical"})

    def test_nivel_cycling_lanza_e_desde_los_nucleos(self):
        index = next(i for i in (0, 1) if parse_core_mode(self.level_info(i)) == CoreMode.CYCLING)
        world, cores = self.start_level(index)
        self.assertTrue(cores)
        self.assertTrue(all(c.state == CoreState.CLOSED for c in cores))
        # Se quita el spawner para contar solo los E de los núcleos, y la alerta pasa a AMARILLA
        # (en VERDE los núcleos no lanzan, #29).
        for spawner, _ in world.get_component(CEnemySpawner):
            world.delete_entity(spawner, immediate=True)
        get_alert(world).state = AlertState.YELLOW
        durations = cores[0].durations
        steps = int((durations[CoreState.CLOSED] + durations[CoreState.OPENING]) * 60) + 2
        for _ in range(steps):
            self.scene.simulate(1 / 60)
        types = [c.enemy_type for _, c in world.get_component(CEnemy)]
        self.assertEqual(types, [EnemyType.E] * len(cores))
        self.scene.do_draw(self.engine.screen)

    def test_nivel_static_no_lanza(self):
        index = next(i for i in (0, 1) if parse_core_mode(self.level_info(i)) == CoreMode.STATIC)
        world, cores = self.start_level(index)
        self.assertTrue(all(c.state == CoreState.OPEN for c in cores))
        for spawner, _ in world.get_component(CEnemySpawner):
            world.delete_entity(spawner, immediate=True)
        get_alert(world).state = AlertState.YELLOW
        for _ in range(300):
            self.scene.simulate(1 / 60)
        self.assertEqual(world.get_component(CEnemy), [])

    def test_error_de_nucleo_nombra_el_archivo_del_nivel(self):
        index = next(i for i in (0, 1) if parse_core_mode(self.level_info(i)) == CoreMode.CYCLING)
        info = self.level_info(index)
        original = info["core"]
        self.addCleanup(info.__setitem__, "core", original)
        info["core"] = {"mode": "otro"}
        ServiceLocator.game_state_service.level_index = index
        with self.assertRaisesRegex(ValueError, r"level_test_cycling.json.*core.mode"):
            self.scene.start()


if __name__ == "__main__":
    unittest.main()
