"""Pruebas del input con patrón Command. Ejecutar con: python -m unittest discover -s tests"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_input import create_input
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.systems.s_input import system_input
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from src.scenes.play_scene import direction_from_commands


def key_event(event_type, key):
    return pygame.event.Event(event_type, key=key)


class TestSystemInput(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()
        self.world.create_entity(CInputCommand("PLAYER_FIRE", pygame.K_z))
        self.actions = []

    def do_action(self, action):
        self.actions.append((action.name, action.phase))

    def test_presionar_y_soltar_dan_start_y_end(self):
        system_input(self.world, key_event(pygame.KEYDOWN, pygame.K_z), self.do_action)
        system_input(self.world, key_event(pygame.KEYUP, pygame.K_z), self.do_action)
        self.assertEqual(self.actions, [("PLAYER_FIRE", CommandPhase.START),
                                        ("PLAYER_FIRE", CommandPhase.END)])

    def test_otra_tecla_no_genera_comando(self):
        system_input(self.world, key_event(pygame.KEYDOWN, pygame.K_x), self.do_action)
        self.assertEqual(self.actions, [])

    def test_eventos_que_no_son_teclas_se_ignoran(self):
        system_input(self.world, pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1), self.do_action)
        self.assertEqual(self.actions, [])


class TestCreateInput(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)

    def test_crea_un_comando_por_tecla(self):
        world = esper.World()
        create_input(world, {"PAUSE": ["p", "escape"]})
        keys = {c.key for _, c in world.get_component(CInputCommand) if c.name == "PAUSE"}
        self.assertEqual(keys, {pygame.K_p, pygame.K_ESCAPE})

    def test_input_json_solo_tiene_teclas_validas(self):
        create_input(esper.World(), ServiceLocator.configs_service.get("assets/cfg/input.json"))


class TestPlaySceneInput(unittest.TestCase):
    def setUp(self):
        # El driver dummy no tiene renderer acelerado para pygame.SCALED; en una ventana real no aparece.
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.scene = self.engine._scenes["play"]
        self.scene.start()

    def player_direction(self):
        return self.scene.ecs_world.get_component(CPlayerMovement)[0][1].direction

    def test_direcciones_se_combinan(self):
        self.assertEqual(direction_from_commands({"PLAYER_UP", "PLAYER_LEFT"}), pygame.Vector2(-1, -1))
        self.assertEqual(direction_from_commands({"PLAYER_UP", "PLAYER_DOWN"}), pygame.Vector2(0, 0))

    def test_flecha_cambia_la_direccion_y_se_conserva_al_soltar(self):
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_RIGHT))
        self.assertEqual(self.player_direction(), pygame.Vector2(1, 0))
        self.scene.process_events(key_event(pygame.KEYUP, pygame.K_RIGHT))
        self.assertEqual(self.player_direction(), pygame.Vector2(1, 0))


if __name__ == "__main__":
    unittest.main()
