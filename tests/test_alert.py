"""Pruebas de la condición de alerta VERDE, AMARILLA y ROJA (#29). Ejecutar con: python -m unittest discover -s tests"""
import copy
import json
import os
import unittest
import warnings
from pathlib import Path
from unittest import mock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_alert import create_alert, load_alert_hud, load_alert_settings, load_alert_sounds
from src.create.prefab_base import create_base
from src.create.prefab_enemy import create_enemy
from src.ecs.components.c_alert import AlertState, CAlert
from src.ecs.components.c_alert_boost import CAlertBoost
from src.ecs.components.c_alert_text import CAlertText
from src.ecs.components.c_base import BaseOrientation, CBase
from src.ecs.components.c_base_core import CBaseCore, CoreMode, CoreState
from src.ecs.components.c_camera import CCamera
from src.ecs.components.c_enemy import CEnemy, EnemyType
from src.ecs.components.c_enemy_spawner import CEnemySpawner
from src.ecs.components.c_enemy_state import CEnemyState, EnemyState
from src.ecs.components.c_steering import CSteering
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_text import CText
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.tags.c_tag_ui import CTagUI
from src.ecs.systems.s_alert import (alert_allows_launch, alert_rate_multiplier, get_alert,
                                     record_base_destroyed, system_alert, system_alert_speed)
from src.ecs.systems.s_base_core import system_base_core
from src.ecs.systems.s_base_destruction import destroy_base, hit_turret
from src.ecs.systems.s_enemy_spawner import system_enemy_spawner
from src.ecs.systems.s_enemy_state import system_enemy_state
from src.ecs.systems.s_player_death import kill_player
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.scenes.play_scene import PlayState
from tests.test_base import BASE_INFO

ROOT = Path(__file__).resolve().parents[1]
ALERTS_PATH = "assets/cfg/alerts.json"
LEVEL_PATH = "assets/cfg/levels/nivel.json"
POINTS = {"turret": 200, "base": 1500}
DT = 1 / 60
CORE_DURATIONS = {"closed": 2.0, "opening": 0.5, "open": 1.0, "closing": 0.5}
CORE_BASE_INFO = dict(BASE_INFO, core=dict(BASE_INFO["core"], durations=CORE_DURATIONS))


def load_json(relative):
    with (ROOT / relative).open(encoding="utf-8") as file:
        return json.load(file)


def alerts_info(**changes):
    info = copy.deepcopy(load_json(ALERTS_PATH))
    info.update(changes)
    return info


def settings_info(green=5.0, base_green=5.0, red_after=120.0, speed=2.0, rate=2.0):
    return alerts_info(green_duration=green, base_destroyed_green_duration=base_green,
                       red_after=red_after, red_speed_multiplier=speed, red_rate_multiplier=rate)


class AlertTestCase(unittest.TestCase):
    """Mundo con una alerta y un registro de los sonidos que pide."""

    def setUp(self):
        self.world = esper.World()
        self.enemies_info = load_json("assets/cfg/enemies.json")
        patcher = mock.patch.object(ServiceLocator.sounds_service, "play")
        self.play = patcher.start()
        self.addCleanup(patcher.stop)

    def make_alert(self, level_info=None, **settings):
        create_alert(self.world, settings_info(**settings), ALERTS_PATH, level_info or {}, LEVEL_PATH)
        return get_alert(self.world)

    def sounds(self):
        return [call.args[0] for call in self.play.call_args_list]

    def sound_of(self, state):
        return load_json(ALERTS_PATH)["sounds"][state.value]

    def make_spawner(self, **changes):
        info = {"initial_delay": 1.0, "interval": 1.0, "max_alive": 100, "weights": {"I": 1}}
        info.update(changes)
        entity = self.world.create_entity(CEnemySpawner(info))
        return self.world.component_for_entity(entity, CEnemySpawner)

    def camera(self):
        return CCamera(pygame.Rect(0, 0, 192, 208), pygame.Vector2(1024, 1536), pygame.Vector2(512, 768))


class TestTransiciones(AlertTestCase):
    def test_empieza_en_verde_sin_sonido(self):
        c_alert = self.make_alert()
        self.assertEqual(c_alert.state, AlertState.GREEN)
        self.assertEqual(c_alert.total_time, 0.0)
        self.play.assert_not_called()

    def test_pasa_a_amarilla_justo_en_green_duration(self):
        c_alert = self.make_alert(green=5.0)
        self.assertEqual(system_alert(self.world, 4.99), [])
        self.assertEqual(c_alert.state, AlertState.GREEN)
        self.assertEqual(system_alert(self.world, 0.01), [AlertState.YELLOW])
        self.assertEqual(c_alert.state, AlertState.YELLOW)
        self.assertEqual(self.sounds(), [self.sound_of(AlertState.YELLOW)])

    def test_pasa_a_amarilla_con_pasos_de_un_frame(self):
        c_alert = self.make_alert(green=5.0)
        for _ in range(round(5.0 / DT) + 1):
            system_alert(self.world, DT)
        self.assertEqual(c_alert.state, AlertState.YELLOW)

    def test_base_destruida_pone_verde_temporal_y_vuelve_a_amarilla(self):
        c_alert = self.make_alert(green=5.0, base_green=3.0)
        system_alert(self.world, 5.0)
        record_base_destroyed(self.world)
        self.assertEqual(system_alert(self.world, 1.0), [AlertState.GREEN])
        self.assertTrue(c_alert.temporary_green)
        self.assertEqual(system_alert(self.world, 1.99), [])
        self.assertEqual(system_alert(self.world, 1.01), [AlertState.YELLOW])
        self.assertEqual(self.sounds(), [self.sound_of(s) for s in
                                         (AlertState.YELLOW, AlertState.GREEN, AlertState.YELLOW)])

    def test_otra_base_en_el_verde_temporal_reinicia_su_duracion(self):
        c_alert = self.make_alert(green=5.0, base_green=3.0)
        system_alert(self.world, 5.0)
        record_base_destroyed(self.world)
        system_alert(self.world, 2.0)
        record_base_destroyed(self.world)
        self.assertEqual(system_alert(self.world, 2.0), [])
        self.assertEqual(c_alert.state, AlertState.GREEN)
        self.assertEqual(system_alert(self.world, 1.0), [AlertState.YELLOW])
        # Reiniciar el VERDE no es un cambio: no suena.
        self.assertEqual(self.sounds().count(self.sound_of(AlertState.GREEN)), 1)

    def test_base_en_el_verde_inicial_no_cambia_su_cuenta(self):
        c_alert = self.make_alert(green=5.0, base_green=10.0)
        system_alert(self.world, 4.0)
        record_base_destroyed(self.world)
        self.assertEqual(system_alert(self.world, 1.0), [AlertState.YELLOW])
        self.assertFalse(c_alert.temporary_green)

    def test_varias_bases_en_un_paso_cuentan_como_una(self):
        c_alert = self.make_alert(green=5.0, base_green=3.0)
        system_alert(self.world, 5.0)
        record_base_destroyed(self.world)
        record_base_destroyed(self.world)
        self.assertEqual(system_alert(self.world, 0.5), [AlertState.GREEN])
        self.assertEqual(c_alert.bases_destroyed, 0)
        self.assertEqual(system_alert(self.world, 2.5), [AlertState.YELLOW])

    def test_roja_por_tiempo_total_incluso_en_el_verde_temporal(self):
        c_alert = self.make_alert(green=5.0, base_green=30.0, red_after=20.0)
        system_alert(self.world, 10.0)
        record_base_destroyed(self.world)
        system_alert(self.world, 1.0)
        self.assertEqual(c_alert.state, AlertState.GREEN)
        self.assertEqual(system_alert(self.world, 9.0), [AlertState.RED])
        self.assertEqual(c_alert.total_time, 20.0)

    def test_red_after_justo_al_terminar_un_verde_gana_roja(self):
        c_alert = self.make_alert(green=5.0, base_green=5.0, red_after=15.0)
        system_alert(self.world, 10.0)
        record_base_destroyed(self.world)
        system_alert(self.world, 1.0)
        self.play.reset_mock()
        self.assertEqual(system_alert(self.world, 4.0), [AlertState.RED])
        self.assertEqual(self.sounds(), [self.sound_of(AlertState.RED)])
        self.assertEqual(c_alert.state, AlertState.RED)

    def test_base_en_el_paso_que_llega_a_roja_gana_roja(self):
        c_alert = self.make_alert(green=5.0, red_after=10.0)
        system_alert(self.world, 9.0)
        record_base_destroyed(self.world)
        self.assertEqual(system_alert(self.world, 1.0), [AlertState.RED])
        self.assertEqual(c_alert.state, AlertState.RED)

    def test_roja_no_baja(self):
        c_alert = self.make_alert(green=5.0, red_after=10.0)
        system_alert(self.world, 10.0)
        record_base_destroyed(self.world)
        self.assertEqual(system_alert(self.world, 100.0), [])
        self.assertEqual(c_alert.state, AlertState.RED)
        self.assertEqual(c_alert.total_time, 110.0)

    def test_un_paso_largo_pasa_por_amarilla_y_roja_con_dos_sonidos(self):
        c_alert = self.make_alert(green=5.0, red_after=10.0)
        self.assertEqual(system_alert(self.world, 12.0), [AlertState.YELLOW, AlertState.RED])
        self.assertEqual(self.sounds(), [self.sound_of(AlertState.YELLOW), self.sound_of(AlertState.RED)])
        self.assertEqual(c_alert.total_time, 12.0)
        self.assertEqual(c_alert.time_in_state, 2.0)

    def test_red_after_menor_o_igual_que_green_duration_salta_a_roja(self):
        for red_after in (3.0, 5.0):
            with self.subTest(red_after=red_after):
                self.world = esper.World()
                self.play.reset_mock()
                c_alert = self.make_alert(green=5.0, red_after=red_after)
                self.assertEqual(system_alert(self.world, 6.0), [AlertState.RED])
                self.assertEqual(c_alert.state, AlertState.RED)


class TestDeteccionDeBases(AlertTestCase):
    def make_base(self):
        return create_base(self.world, BASE_INFO, pygame.Vector2(100, 100), BaseOrientation.HORIZONTAL)

    def test_destruir_por_el_nucleo_se_registra_una_vez(self):
        c_alert = self.make_alert()
        base = self.make_base()
        destroy_base(self.world, base, POINTS)
        destroy_base(self.world, base, POINTS)
        self.assertEqual(c_alert.bases_destroyed, 1)

    def test_destruir_la_ultima_torreta_se_registra_una_vez(self):
        c_alert = self.make_alert()
        base = self.make_base()
        turrets = list(self.world.component_for_entity(base, CBase).turrets)
        for turret in turrets[:-1]:
            hit_turret(self.world, turret, POINTS)
        self.assertEqual(c_alert.bases_destroyed, 0)
        hit_turret(self.world, turrets[-1], POINTS)
        self.assertEqual(c_alert.bases_destroyed, 1)
        self.world._clear_dead_entities()
        destroy_base(self.world, base, POINTS)
        self.assertEqual(c_alert.bases_destroyed, 1)

    def test_borrar_la_base_al_limpiar_la_escena_no_cuenta(self):
        c_alert = self.make_alert(green=5.0)
        base = self.make_base()
        system_alert(self.world, 5.0)
        self.world.delete_entity(base, immediate=True)
        self.assertEqual(system_alert(self.world, 1.0), [])
        self.assertEqual(c_alert.state, AlertState.YELLOW)

    def test_en_el_paso_de_la_destruccion_aun_sale_un_enemigo_y_en_el_siguiente_rige_verde(self):
        self.make_alert(green=5.0)
        spawner = self.make_spawner(initial_delay=0.5, interval=0.5)
        base = self.make_base()
        system_alert(self.world, 5.0)
        # Paso de la destrucción: alerta, spawner y, más tarde, la bala contra la base.
        system_alert(self.world, 0.5)
        created = system_enemy_spawner(self.world, 0.5, self.camera(), self.enemies_info, 4)
        destroy_base(self.world, base, POINTS)
        self.assertEqual(len(created), 1)
        # Paso siguiente: VERDE y el spawner ya no crea.
        self.assertEqual(system_alert(self.world, 0.5), [AlertState.GREEN])
        self.assertFalse(spawner.active)
        self.assertEqual(system_enemy_spawner(self.world, 0.5, self.camera(), self.enemies_info, 4), [])


class TestEfectos(AlertTestCase):
    def test_spawner_y_nucleos_segun_el_estado(self):
        c_alert = self.make_alert(green=5.0, red_after=10.0, rate=3.0)
        spawner = self.make_spawner()
        system_alert(self.world, 1.0)
        self.assertEqual((spawner.active, spawner.rate_multiplier), (False, 1.0))
        self.assertEqual((alert_allows_launch(c_alert), alert_rate_multiplier(c_alert)), (False, 1.0))
        system_alert(self.world, 4.0)
        self.assertEqual((spawner.active, spawner.rate_multiplier), (True, 1.0))
        self.assertEqual((alert_allows_launch(c_alert), alert_rate_multiplier(c_alert)), (True, 1.0))
        system_alert(self.world, 5.0)
        self.assertEqual((spawner.active, spawner.rate_multiplier), (True, 3.0))
        self.assertEqual((alert_allows_launch(c_alert), alert_rate_multiplier(c_alert)), (True, 3.0))

    def test_sin_alerta_los_nucleos_funcionan_como_antes(self):
        self.assertEqual((alert_allows_launch(None), alert_rate_multiplier(None)), (True, 1.0))

    def test_crear_la_alerta_apaga_el_spawner(self):
        spawner = self.make_spawner()
        self.make_alert()
        self.assertFalse(spawner.active)

    def test_time_to_spawn_queda_congelado_en_verde_y_sigue_al_volver(self):
        self.make_alert(green=2.0)
        spawner = self.make_spawner(initial_delay=1.5)
        for _ in range(3):
            system_alert(self.world, 0.5)
            system_enemy_spawner(self.world, 0.5, self.camera(), self.enemies_info, 4)
        self.assertEqual(spawner.time_to_spawn, 1.5)
        system_alert(self.world, 0.5)
        system_enemy_spawner(self.world, 0.5, self.camera(), self.enemies_info, 4)
        self.assertEqual(spawner.time_to_spawn, 1.0)

    def test_en_roja_el_spawner_respeta_max_alive_y_uno_por_paso(self):
        self.make_alert(green=1.0, red_after=2.0, rate=2.0)
        spawner = self.make_spawner(initial_delay=0.1, interval=0.1, max_alive=2)
        system_alert(self.world, 2.0)
        self.assertEqual(spawner.rate_multiplier, 2.0)
        self.assertEqual(len(system_enemy_spawner(self.world, 1.0, self.camera(), self.enemies_info, 4)), 1)
        for _ in range(5):
            system_enemy_spawner(self.world, 1.0, self.camera(), self.enemies_info, 4)
        self.assertEqual(len(self.world.get_component(CEnemy)), 2)

    def speed_of(self, enemy):
        return (self.world.component_for_entity(enemy, CSteering).max_speed,
                pygame.Vector2(self.world.component_for_entity(enemy, CVelocity).vel))

    def test_roja_duplica_una_vez_la_velocidad_de_los_enemigos_vivos(self):
        self.make_alert(green=1.0, red_after=2.0, speed=2.0)
        enemies = {t: create_enemy(self.world, self.enemies_info, pygame.Vector2(50, 50), t) for t in EnemyType}
        for enemy in enemies.values():
            self.world.component_for_entity(enemy, CVelocity).vel = pygame.Vector2(30, -40)
        # Un E que ya iba recto (STRAIGHT) y un enemigo quieto.
        straight = create_enemy(self.world, self.enemies_info, pygame.Vector2(50, 50), EnemyType.E)
        self.world.component_for_entity(straight, CEnemyState).state = EnemyState.STRAIGHT
        self.world.component_for_entity(straight, CVelocity).vel = pygame.Vector2(80, 0)
        still = create_enemy(self.world, self.enemies_info, pygame.Vector2(50, 50), EnemyType.P)
        before = {e: self.speed_of(e) for e in [*enemies.values(), straight, still]}
        system_alert(self.world, 1.0)
        system_alert_speed(self.world)
        self.assertEqual({e: self.speed_of(e) for e in before}, before)
        system_alert(self.world, 1.0)
        system_alert_speed(self.world)
        system_alert_speed(self.world)
        for enemy, (max_speed, vel) in before.items():
            self.assertEqual(self.speed_of(enemy), (max_speed * 2, vel * 2))
            self.assertTrue(self.world.has_component(enemy, CAlertBoost))
        self.assertEqual(self.speed_of(still)[1], pygame.Vector2(0, 0))

    def test_el_e_nuevo_en_roja_sale_de_aim_con_la_velocidad_doble(self):
        self.make_alert(green=1.0, red_after=2.0, speed=2.0)
        system_alert(self.world, 2.0)
        enemy = create_enemy(self.world, self.enemies_info, pygame.Vector2(50, 50), EnemyType.E)
        system_alert_speed(self.world)
        system_enemy_state(self.world, DT, pygame.Vector2(150, 50))
        c_es = self.world.component_for_entity(enemy, CEnemyState)
        self.assertEqual(c_es.state, EnemyState.STRAIGHT)
        base_speed = self.enemies_info["E"]["steering"]["max_speed"]
        self.assertAlmostEqual(self.speed_of(enemy)[1].length(), base_speed * 2)

    def test_los_enemigos_creados_en_roja_reciben_el_factor(self):
        self.make_alert(green=1.0, red_after=2.0, speed=2.0)
        spawner = self.make_spawner(initial_delay=0.1, weights={"I": 1, "P": 1})
        system_alert(self.world, 2.0)
        created = system_enemy_spawner(self.world, 0.1, self.camera(), self.enemies_info, 4)
        system_alert_speed(self.world)
        enemy = created[0]
        enemy_type = self.world.component_for_entity(enemy, CEnemy).enemy_type
        expected = self.enemies_info[enemy_type.value]["steering"]["max_speed"] * 2
        self.assertEqual(self.speed_of(enemy)[0], expected)
        self.assertTrue(spawner.active)


class TestNucleoConAlerta(AlertTestCase):
    def make_core(self):
        base = create_base(self.world, CORE_BASE_INFO, pygame.Vector2(100, 80),
                           BaseOrientation.HORIZONTAL, CoreMode.CYCLING)
        core = self.world.component_for_entity(base, CBase).core
        return self.world.component_for_entity(core, CBaseCore)

    def step(self, delta_time):
        c_alert = get_alert(self.world)
        system_alert(self.world, delta_time)
        created = system_base_core(self.world, delta_time, self.enemies_info,
                                   alert_allows_launch(c_alert), alert_rate_multiplier(c_alert))
        self.world._clear_dead_entities()
        return created

    def test_en_verde_cicla_pero_no_lanza_ni_acumula(self):
        c_alert = self.make_alert(green=5.0)
        c_core = self.make_core()
        created = []
        # CLOSED (2.0) + OPENING (0.5): se abre a los 2.5 s, todavía en VERDE.
        for _ in range(5):
            created += self.step(0.5)
        self.assertEqual(c_core.state, CoreState.OPEN)
        self.assertEqual(created, [])
        # A los 5 s pasa a AMARILLA y el lanzamiento perdido no sale.
        for _ in range(5):
            created += self.step(0.5)
        self.assertEqual(c_alert.state, AlertState.YELLOW)
        self.assertEqual(created, [])
        # Sale en la apertura siguiente: ciclo de 4 s, a los 6.5 s.
        for _ in range(2):
            created += self.step(0.5)
        self.assertEqual(created, [])
        created += self.step(0.5)
        self.assertEqual(len(created), 1)

    def test_en_roja_cicla_al_doble(self):
        self.make_alert(green=1.0, red_after=2.0, rate=2.0)
        c_core = self.make_core()
        system_alert(self.world, 2.0)
        c_core.state, c_core.time_in_state = CoreState.CLOSED, 0.0
        # CLOSED + OPENING = 2.5 s de ciclo; al doble, se abre a los 1.25 s.
        self.assertEqual(self.step(1.2), [])
        self.assertEqual(len(self.step(0.1)), 1)
        self.assertEqual(c_core.state, CoreState.OPEN)


class TestConfiguracion(unittest.TestCase):
    def test_los_valores_por_defecto(self):
        settings = load_alert_settings(alerts_info(), ALERTS_PATH, {}, LEVEL_PATH)
        self.assertEqual((settings.green_duration, settings.base_destroyed_green_duration, settings.red_after,
                          settings.red_speed_multiplier, settings.red_rate_multiplier),
                         (5.0, 5.0, 120.0, 2.0, 2.0))

    def test_el_bloque_alert_del_nivel_reemplaza_solo_lo_que_trae(self):
        level = {"alert": {"red_after": 60, "red_speed_multiplier": 1.5}}
        settings = load_alert_settings(alerts_info(), ALERTS_PATH, level, LEVEL_PATH)
        self.assertEqual(settings.red_after, 60.0)
        self.assertEqual(settings.red_speed_multiplier, 1.5)
        self.assertEqual(settings.green_duration, 5.0)

    def test_campo_faltante_o_invalido_en_alerts_json(self):
        cases = {
            "green_duration": None, "base_destroyed_green_duration": 0, "red_after": -1,
            "red_speed_multiplier": 0.5, "red_rate_multiplier": "2",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                info = alerts_info()
                if value is None:
                    del info[field]
                else:
                    info[field] = value
                with self.assertRaisesRegex(ValueError, rf"alerts.json: .*{field}"):
                    load_alert_settings(info, ALERTS_PATH, {}, LEVEL_PATH)

    def test_booleano_no_es_numero(self):
        with self.assertRaisesRegex(ValueError, "alerts.json: green_duration"):
            load_alert_settings(alerts_info(green_duration=True), ALERTS_PATH, {}, LEVEL_PATH)

    def test_errores_del_bloque_alert_nombran_el_nivel(self):
        for alert, field in (({"red_after": 0}, "alert.red_after"),
                             ({"red_rate_multiplier": 0.9}, "alert.red_rate_multiplier"),
                             ({"sounds": {}}, "alert.sounds"),
                             ("rojo", "alert")):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, rf"nivel.json: {field}"):
                    load_alert_settings(alerts_info(), ALERTS_PATH, {"alert": alert}, LEVEL_PATH)

    def test_sonido_faltante_o_que_no_existe(self):
        info = alerts_info()
        info["sounds"]["red"] = "assets/snd/no_existe.ogg"
        with self.assertRaisesRegex(ValueError, "alerts.json: sounds.red no existe"):
            load_alert_sounds(info, ALERTS_PATH)
        del info["sounds"]["yellow"]
        with self.assertRaisesRegex(ValueError, "alerts.json: falta sounds.yellow"):
            load_alert_sounds(info, ALERTS_PATH)

    def test_los_sonidos_de_alerts_json_existen(self):
        for state, path in load_alert_sounds(alerts_info(), ALERTS_PATH).items():
            self.assertTrue((ROOT / path).is_file(), state)

    def test_hud_incompleto(self):
        info = alerts_info()
        del info["hud"]["states"]["yellow"]["color"]
        with self.assertRaisesRegex(ValueError, "alerts.json: hud.states.yellow"):
            load_alert_hud(info, ALERTS_PATH)
        info = alerts_info()
        del info["hud"]["label"]["anchor"]
        with self.assertRaisesRegex(ValueError, "alerts.json: falta hud.label.anchor"):
            load_alert_hud(info, ALERTS_PATH)


class TestAlertaEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        game_state = ServiceLocator.game_state_service
        self.addCleanup(setattr, game_state, "level_index", game_state.level_index)
        self.addCleanup(ServiceLocator.cheats_service.load,
                        ServiceLocator.configs_service.get(ServiceLocator.constants_service.cheats_config))
        self.scene = self.engine._scenes["play"]
        self.engine._current_scene = self.scene
        self.scene.start()
        self.settings = get_alert(self.scene.ecs_world).settings

    @property
    def world(self):
        return self.scene.ecs_world

    def alert(self):
        return get_alert(self.world)

    def run_for(self, seconds):
        for _ in range(round(seconds / DT)):
            self.scene.simulate(DT)

    def test_durante_el_blast_off_esta_en_verde_y_el_tiempo_no_corre(self):
        self.assertEqual(self.scene.state, PlayState.STARTING)
        self.scene.simulate(DT)
        self.assertEqual(self.alert().state, AlertState.GREEN)
        self.assertEqual(self.alert().total_time, 0.0)
        self.scene.skip_blast_off()
        self.scene.simulate(DT)
        self.assertAlmostEqual(self.alert().total_time, DT)

    def test_no_salen_enemigos_en_el_verde_inicial(self):
        self.scene.skip_blast_off()
        self.run_for(self.settings.green_duration - 0.1)
        self.assertEqual(self.world.get_component(CEnemy), [])
        self.assertEqual(self.alert().state, AlertState.GREEN)

    def test_en_pausa_el_tiempo_no_corre_y_el_estado_se_conserva(self):
        self.scene.skip_blast_off()
        c_alert = self.alert()
        c_alert.state = AlertState.RED
        c_alert.total_time = self.settings.red_after
        self.scene.toggle_pause()
        self.run_for(1.0)
        self.scene._show_pause_info(ServiceLocator.constants_service.instructions_config)
        self.assertEqual(self.scene.state, PlayState.PAUSED_INFO)
        self.run_for(1.0)
        self.assertEqual(c_alert.total_time, self.settings.red_after)
        self.scene._show_pause_menu(0)
        self.scene.toggle_pause()
        self.scene.simulate(DT)
        self.assertEqual(c_alert.state, AlertState.RED)
        self.assertAlmostEqual(c_alert.total_time, self.settings.red_after + DT)

    def test_la_muerte_del_jugador_no_detiene_la_alerta(self):
        self.scene.skip_blast_off()
        kill_player(self.world, self.scene._player_entity, self.scene._respawn_info)
        self.run_for(0.5)
        self.assertAlmostEqual(self.alert().total_time, 0.5, places=5)

    def test_saltar_de_nivel_con_la_trampa_vuelve_a_verde_desde_cero(self):
        ServiceLocator.cheats_service.enabled = True
        self.scene.skip_blast_off()
        self.alert().state = AlertState.RED
        self.alert().total_time = 200.0
        record_base_destroyed(self.world)
        self.scene.process_events(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n))
        self.engine._handle_switch_scene()
        self.assertEqual(self.alert().state, AlertState.GREEN)
        self.assertEqual((self.alert().total_time, self.alert().bases_destroyed), (0.0, 0))

    def test_continuar_tras_la_derrota_vuelve_a_verde_desde_cero(self):
        self.scene.skip_blast_off()
        self.alert().state = AlertState.YELLOW
        self.alert().total_time = 50.0
        self.engine.switch_scene("defeat")
        self.engine._handle_switch_scene()
        self.engine._scenes["defeat"].accept("CONTINUE")
        self.engine._handle_switch_scene()
        self.assertIs(self.engine._current_scene, self.scene)
        self.assertEqual((self.alert().state, self.alert().total_time), (AlertState.GREEN, 0.0))

    def hud_text(self):
        texts = self.world.get_components(CText, CAlertText)
        self.assertEqual(len(texts), 1)
        return texts[0][1][0]

    def test_el_hud_muestra_la_condicion_con_su_color(self):
        hud = load_json(ALERTS_PATH)["hud"]
        labels = {c.text for _, c in self.world.get_component(CText)}
        self.assertIn(hud["label"]["text"], labels)
        self.scene.skip_blast_off()
        for state in AlertState:
            with self.subTest(state=state):
                self.alert().state = state
                self.scene.simulate(DT)
                self.scene.do_draw(self.engine.screen)
                look = hud["states"][state.value]
                c_text = self.hud_text()
                self.assertEqual(c_text.text, look["text"])
                self.assertEqual(c_text.color, pygame.Color(look["color"]["r"], look["color"]["g"],
                                                            look["color"]["b"]))

    def test_el_hud_de_la_alerta_no_se_solapa_con_el_resto(self):
        self.scene.skip_blast_off()
        screen = self.engine.screen.get_rect()
        for state in AlertState:
            self.alert().state = state
            self.scene.simulate(DT)
            self.scene.do_draw(self.engine.screen)
            hud = load_json(ALERTS_PATH)["hud"]
            alert_texts = {hud["label"]["text"], hud["states"][state.value]["text"]}
            rects = {}
            for entity, (c_t, c_s, _) in self.world.get_components(CTransform, CSurface, CTagUI):
                if c_s.area.width and c_s.area.height:
                    rects[entity] = pygame.Rect(c_t.pos, c_s.area.size)
            mine = [rects[e] for e, c in self.world.get_component(CText) if c.text in alert_texts]
            others = [r for e, r in rects.items() if r not in mine]
            self.assertEqual(len(mine), 2)
            for rect in mine:
                self.assertTrue(screen.contains(rect), rect)
                self.assertEqual(rect.collidelist(others), -1, rect)

    def test_error_de_alerta_en_el_nivel_nombra_el_archivo(self):
        levels = ServiceLocator.configs_service.get(ServiceLocator.constants_service.levels_config)["levels"]
        info = ServiceLocator.configs_service.get(levels[0])
        self.addCleanup(info.pop, "alert", None)
        info["alert"] = {"green_duration": -1}
        ServiceLocator.game_state_service.level_index = 0
        with self.assertRaisesRegex(ValueError, r"levels/level_01.json: alert.green_duration"):
            self.scene.start()


if __name__ == "__main__":
    unittest.main()
