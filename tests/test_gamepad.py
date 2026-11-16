import os
import unittest
import warnings
from unittest import mock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_input import create_gamepad_input, create_input
from src.ecs.components.c_gamepad_binding import CGamepadBinding, GamepadSource
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.tags.c_tag_player_bullet import CTagPlayerBullet
from src.ecs.systems.s_input import system_input
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.engine.services.gamepad_service import GamepadService
from src.scenes.play_scene import PlayState
from tests.test_input import key_event

V = pygame.Vector2

GAMEPAD_INFO = {
    "dead_zone": 0.5,
    "buttons": {"PLAYER_FIRE": [0], "PAUSE": [7]},
    "axes": {"PLAYER_LEFT": [{"axis": 0, "sign": -1}], "PLAYER_RIGHT": [{"axis": 0, "sign": 1}]},
    "hats": {"PLAYER_UP": [{"hat": 0, "y": 1}], "PLAYER_DOWN": [{"hat": 0, "y": -1}]},
}


def button(event_type, index):
    return pygame.event.Event(event_type, button=index, instance_id=0)


def axis(index, value):
    return pygame.event.Event(pygame.JOYAXISMOTION, axis=index, value=value, instance_id=0)


def hat(index, x, y):
    return pygame.event.Event(pygame.JOYHATMOTION, hat=index, value=(x, y), instance_id=0)


class InputHarness(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        self.world = esper.World()
        create_input(self.world, {"PLAYER_FIRE": ["z"]}, GAMEPAD_INFO)
        self.actions = []

    def send(self, event):
        system_input(self.world, event, lambda c: self.actions.append((c.name, c.phase)))


class TestBotones(InputHarness):
    def test_presionar_y_soltar_dan_start_y_end(self):
        self.send(button(pygame.JOYBUTTONDOWN, 0))
        self.send(button(pygame.JOYBUTTONUP, 0))
        self.assertEqual(self.actions, [("PLAYER_FIRE", CommandPhase.START), ("PLAYER_FIRE", CommandPhase.END)])

    def test_otro_boton_no_genera_comando(self):
        self.send(button(pygame.JOYBUTTONDOWN, 5))
        self.assertEqual(self.actions, [])

    def test_boton_de_pausa(self):
        self.send(button(pygame.JOYBUTTONDOWN, 7))
        self.assertEqual(self.actions, [("PAUSE", CommandPhase.START)])


class TestStick(InputHarness):
    def test_stick_a_la_izquierda_activa_el_comando(self):
        self.send(axis(0, -1.0))
        self.assertEqual(self.actions, [("PLAYER_LEFT", CommandPhase.START)])

    def test_stick_a_la_derecha_activa_el_comando(self):
        self.send(axis(0, 0.9))
        self.assertEqual(self.actions, [("PLAYER_RIGHT", CommandPhase.START)])

    def test_la_zona_muerta_se_ignora(self):
        self.send(axis(0, -0.3))
        self.send(axis(0, 0.4))
        self.assertEqual(self.actions, [])

    def test_volver_al_centro_suelta_el_comando(self):
        self.send(axis(0, -1.0))
        self.send(axis(0, 0.0))
        self.assertEqual(self.actions, [("PLAYER_LEFT", CommandPhase.START), ("PLAYER_LEFT", CommandPhase.END)])

    def test_mantener_el_stick_no_repite_el_start(self):
        self.send(axis(0, -0.8))
        self.send(axis(0, -0.9))
        self.send(axis(0, -1.0))
        self.assertEqual(self.actions, [("PLAYER_LEFT", CommandPhase.START)])

    def test_cruzar_de_izquierda_a_derecha(self):
        self.send(axis(0, -1.0))
        self.send(axis(0, 1.0))
        self.assertEqual(self.actions, [("PLAYER_LEFT", CommandPhase.START), ("PLAYER_LEFT", CommandPhase.END),
                                        ("PLAYER_RIGHT", CommandPhase.START)])

    def test_soltar_sin_haber_presionado_no_hace_nada(self):
        self.send(axis(0, 0.0))
        self.assertEqual(self.actions, [])

    def test_otro_eje_no_afecta(self):
        self.send(axis(3, 1.0))
        self.assertEqual(self.actions, [])


class TestCruceta(InputHarness):
    def test_cruceta_hacia_arriba(self):
        self.send(hat(0, 0, 1))
        self.assertEqual(self.actions, [("PLAYER_UP", CommandPhase.START)])

    def test_soltar_la_cruceta(self):
        self.send(hat(0, 0, -1))
        self.send(hat(0, 0, 0))
        self.assertEqual(self.actions, [("PLAYER_DOWN", CommandPhase.START), ("PLAYER_DOWN", CommandPhase.END)])

    def test_la_diagonal_solo_activa_lo_que_esta_configurado(self):
        self.send(hat(0, 1, 1))
        self.assertEqual(self.actions, [("PLAYER_UP", CommandPhase.START)])


class TestTecladoYGamepad(InputHarness):
    def test_el_teclado_sigue_funcionando(self):
        self.send(key_event(pygame.KEYDOWN, pygame.K_z))
        self.assertEqual(self.actions, [("PLAYER_FIRE", CommandPhase.START)])

    def test_la_misma_accion_viene_de_las_dos_fuentes(self):
        self.send(key_event(pygame.KEYDOWN, pygame.K_z))
        self.send(button(pygame.JOYBUTTONDOWN, 0))
        self.assertEqual([name for name, _ in self.actions], ["PLAYER_FIRE", "PLAYER_FIRE"])

    def test_un_evento_de_gamepad_no_activa_teclas(self):
        self.send(button(pygame.JOYBUTTONDOWN, 0))
        self.assertEqual(len(self.actions), 1)

    def test_las_fuentes_tienen_claves_distintas(self):
        keys = [c.key for _, c in self.world.get_component(CInputCommand) if c.name == "PLAYER_FIRE"]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn(pygame.K_z, keys)
        self.assertTrue(any(k < 0 for k in keys))


class TestCrearComandosDeGamepad(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)

    def test_un_comando_por_boton_eje_y_cruceta(self):
        world = esper.World()
        create_gamepad_input(world, GAMEPAD_INFO)
        sources = [c.source for _, c in world.get_component(CGamepadBinding)]
        self.assertEqual(sources.count(GamepadSource.BUTTON), 2)
        self.assertEqual(sources.count(GamepadSource.AXIS), 2)
        self.assertEqual(sources.count(GamepadSource.HAT), 2)

    def test_las_claves_son_negativas_y_unicas(self):
        world = esper.World()
        create_gamepad_input(world, GAMEPAD_INFO)
        keys = [c.key for _, c in world.get_component(CInputCommand)]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(k < 0 for k in keys))

    def test_sin_gamepad_info_solo_hay_teclado(self):
        world = esper.World()
        create_input(world, {"PLAYER_FIRE": ["z"]})
        self.assertEqual(len(world.get_component(CGamepadBinding)), 0)

    def test_sign_invalido_da_error(self):
        with self.assertRaisesRegex(ValueError, "sign"):
            create_gamepad_input(esper.World(), {"dead_zone": 0.5, "axes": {"PLAYER_LEFT": [{"axis": 0, "sign": 0}]}})

    def test_cruceta_sin_direccion_da_error(self):
        with self.assertRaisesRegex(ValueError, "cruceta"):
            create_gamepad_input(esper.World(), {"dead_zone": 0.5, "hats": {"PLAYER_UP": [{"hat": 0}]}})


class TestGamepadService(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        pygame.init()
        self.addCleanup(pygame.quit)
        self.service = GamepadService()

    def fake_joystick(self, instance_id):
        joystick = mock.Mock()
        joystick.get_instance_id.return_value = instance_id
        return joystick

    def test_sin_gamepads_conectados_no_falla(self):
        self.service.open_connected()
        self.assertEqual(self.service.count, 0)

    def test_al_conectar_un_gamepad_lo_abre(self):
        with mock.patch("pygame.joystick.Joystick", return_value=self.fake_joystick(7)):
            self.service.handle_event(pygame.event.Event(pygame.JOYDEVICEADDED, device_index=0))
        self.assertEqual(self.service.count, 1)

    def test_el_mismo_gamepad_no_se_cuenta_dos_veces(self):
        with mock.patch("pygame.joystick.Joystick", return_value=self.fake_joystick(7)):
            self.service.handle_event(pygame.event.Event(pygame.JOYDEVICEADDED, device_index=0))
            self.service.handle_event(pygame.event.Event(pygame.JOYDEVICEADDED, device_index=0))
        self.assertEqual(self.service.count, 1)

    def test_al_desconectar_lo_olvida(self):
        with mock.patch("pygame.joystick.Joystick", return_value=self.fake_joystick(7)):
            self.service.handle_event(pygame.event.Event(pygame.JOYDEVICEADDED, device_index=0))
        self.service.handle_event(pygame.event.Event(pygame.JOYDEVICEREMOVED, instance_id=7))
        self.assertEqual(self.service.count, 0)

    def test_desconectar_uno_desconocido_no_falla(self):
        self.service.handle_event(pygame.event.Event(pygame.JOYDEVICEREMOVED, instance_id=99))
        self.assertEqual(self.service.count, 0)

    def test_si_pygame_no_puede_abrirlo_se_ignora(self):
        with mock.patch("pygame.joystick.Joystick", side_effect=pygame.error("fallo")):
            self.service.handle_event(pygame.event.Event(pygame.JOYDEVICEADDED, device_index=0))
        self.assertEqual(self.service.count, 0)

    def test_eventos_que_no_son_de_dispositivos_se_ignoran(self):
        self.service.handle_event(button(pygame.JOYBUTTONDOWN, 0))
        self.assertEqual(self.service.count, 0)


class TestGamepadEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.scene.start()
        self.world = self.scene.ecs_world

    def direction(self):
        return self.world.get_component(CPlayerMovement)[0][1].direction

    def bullets(self):
        return [e for e, _ in self.world.get_component(CTagPlayerBullet) if self.world.entity_exists(e)]

    def test_la_config_real_solo_usa_acciones_que_existen_en_input_json(self):
        constants = ServiceLocator.constants_service
        gamepad = ServiceLocator.configs_service.get(constants.gamepad_config)
        known = set(ServiceLocator.configs_service.get(constants.input_config))
        for section in ("buttons", "axes", "hats"):
            self.assertLessEqual(set(gamepad[section]), known, section)

    def test_el_stick_cambia_la_direccion_de_la_nave(self):
        self.scene.process_events(axis(0, 1.0))
        self.assertEqual(self.direction(), V(1, 0))
        self.scene.process_events(axis(0, 0.0))
        self.assertEqual(self.direction(), V(1, 0))

    def test_stick_en_diagonal(self):
        self.scene.process_events(axis(0, -1.0))
        self.scene.process_events(axis(1, -1.0))
        self.assertEqual(self.direction(), V(-1, -1).normalize())

    def test_la_cruceta_cambia_la_direccion(self):
        self.scene.process_events(hat(0, 0, -1))
        self.assertEqual(self.direction(), V(0, 1))

    def test_boton_a_dispara(self):
        self.scene.process_events(button(pygame.JOYBUTTONDOWN, 0))
        self.assertGreaterEqual(len(self.bullets()), 2)

    def test_boton_start_pausa_y_reanuda(self):
        self.scene.process_events(button(pygame.JOYBUTTONDOWN, 7))
        self.assertEqual(self.scene.state, PlayState.PAUSED)
        self.scene.process_events(button(pygame.JOYBUTTONDOWN, 7))
        self.assertEqual(self.scene.state, PlayState.PLAYING)

    def test_cambiar_de_teclado_a_gamepad_sin_problema(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_UP))
        self.assertEqual(self.direction(), V(0, -1))
        self.scene.process_events(key_event(pygame.KEYUP, pygame.K_UP))
        self.scene.process_events(axis(0, 1.0))
        self.assertEqual(self.direction(), V(1, 0))
        self.scene.process_events(axis(0, 0.0))
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_LEFT))
        self.assertEqual(self.direction(), V(-1, 0))

    def test_teclado_y_stick_a_la_vez_se_suman_y_soltar_uno_conserva_el_otro(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_UP))
        self.scene.process_events(axis(0, 1.0))
        self.assertEqual(self.direction(), V(1, -1).normalize())
        self.scene.process_events(axis(0, 0.0))
        self.assertEqual(self.direction(), V(0, -1))

    def test_desconectar_el_gamepad_suelta_las_direcciones(self):
        self.scene.process_events(axis(0, 1.0))
        self.scene.process_events(pygame.event.Event(pygame.JOYDEVICEREMOVED, instance_id=0))
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_UP))
        self.assertEqual(self.direction(), V(0, -1))

    def test_el_juego_corre_y_dibuja_con_gamepad(self):
        self.scene.process_events(axis(1, -1.0))
        self.scene.process_events(button(pygame.JOYBUTTONDOWN, 0))
        for _ in range(30):
            self.scene.simulate(1 / 60)
            self.scene.do_draw(self.engine.screen)


if __name__ == "__main__":
    unittest.main()
