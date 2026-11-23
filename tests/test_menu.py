"""Pruebas de la escena de título, las instrucciones y los créditos (#33).

Ejecutar con: python -m unittest discover -s tests
"""
import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_menu import create_menu, update_menu_values
from src.ecs.components.c_menu_item import CMenuItem
from src.ecs.components.c_star import CStar
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_text import CText
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_menu import get_menu, move_selection, selected_action, system_menu_highlight
from src.ecs.systems.s_starfield import system_starfield_fall
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator

BLINK = {"speed": 340}
MENU = {
    "anchor": {"x": 100, "y": 50}, "line_height": 10, "alignment": "CENTER",
    "color": {"r": 255, "g": 255, "b": 255}, "selected_color": {"r": 255, "g": 230, "b": 80},
    "options": [{"text": "JUGAR", "action": "PLAY"}, {"text": "RONDA {level}", "action": "LEVEL"}],
}
DT = 1 / 60


def key_event(event_type, key):
    return pygame.event.Event(event_type, key=key)


def texts(world):
    return {c.text for _, c in world.get_component(CText)}


class TestMenuHelpers(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.world = esper.World()
        create_menu(self.world, MENU, {"level": 1})

    def item_text(self, index):
        for _, (c_item, c_text) in self.world.get_components(CMenuItem, CText):
            if c_item.index == index:
                return c_text

    def test_seleccion_da_la_vuelta(self):
        self.assertEqual(move_selection(0, -1, 4), 3)
        self.assertEqual(move_selection(3, 1, 4), 0)
        self.assertEqual(move_selection(1, 1, 4), 2)

    def test_crea_una_linea_por_opcion_con_sus_valores(self):
        self.assertEqual(texts(self.world), {"JUGAR", "RONDA 1"})
        self.assertEqual(self.item_text(1).anchor.y - self.item_text(0).anchor.y, 10)

    def test_la_opcion_elegida_se_pinta_con_otro_color(self):
        get_menu(self.world).selected = 1
        system_menu_highlight(self.world)
        self.assertEqual(self.item_text(1).color, pygame.Color(255, 230, 80))
        self.assertEqual(self.item_text(0).color, pygame.Color(255, 255, 255))
        self.assertEqual(selected_action(self.world), "LEVEL")

    def test_cambiar_valores_actualiza_el_texto(self):
        update_menu_values(self.world, {"level": 3})
        self.assertEqual(texts(self.world), {"JUGAR", "RONDA 3"})


class TestStarfieldFall(unittest.TestCase):
    def test_las_estrellas_bajan_segun_su_capa_y_vuelven_por_arriba(self):
        world = esper.World()
        view = pygame.Rect(0, 0, 100, 100)
        near = world.create_entity(CTransform(pygame.Vector2(10, 50)),
                                   CSurface(pygame.Vector2(1, 1), pygame.Color(255, 255, 255)), CStar(0.5, 100, True))
        far = world.create_entity(CTransform(pygame.Vector2(20, 99)),
                                  CSurface(pygame.Vector2(1, 1), pygame.Color(255, 255, 255)), CStar(0.25, 100, True))
        system_starfield_fall(world, 1.0, 20, view, BLINK)
        self.assertEqual(world.component_for_entity(near, CTransform).pos, pygame.Vector2(10, 60))
        self.assertEqual(world.component_for_entity(far, CTransform).pos, pygame.Vector2(20, 4))


class TestTitleScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        game_state = ServiceLocator.game_state_service
        self.addCleanup(setattr, game_state, "level_index", game_state.level_index)
        self.scene = self.engine._scenes["title"]
        self.scene.start()

    def press(self, key):
        self.scene.process_events(key_event(pygame.KEYDOWN, key))
        self.scene.process_events(key_event(pygame.KEYUP, key))

    def test_muestra_el_menu_y_las_estrellas(self):
        self.scene.simulate(DT)
        self.scene.do_draw(self.engine.screen)
        self.assertIn("JUGAR", texts(self.scene.ecs_world))
        self.assertIn("< RONDA 1 >", texts(self.scene.ecs_world))
        self.assertGreater(len(self.scene.ecs_world.get_component(CStar)), 0)

    def test_aceptar_en_jugar_reinicia_la_partida_y_va_al_juego(self):
        ServiceLocator.game_state_service.add_score(500)
        self.press(pygame.K_z)
        self.assertEqual(ServiceLocator.game_state_service.score, 0)
        self.assertEqual(self.engine._scene_name_to_switch, "play")

    def test_enter_tambien_acepta(self):
        self.press(pygame.K_RETURN)
        self.assertEqual(self.engine._scene_name_to_switch, "play")

    def test_abajo_y_aceptar_lleva_a_instrucciones_y_creditos(self):
        self.press(pygame.K_DOWN)
        self.press(pygame.K_DOWN)
        self.press(pygame.K_z)
        self.assertEqual(self.engine._scene_name_to_switch, "instructions")
        self.press(pygame.K_DOWN)
        self.press(pygame.K_z)
        self.assertEqual(self.engine._scene_name_to_switch, "credits")

    def test_arriba_desde_la_primera_va_a_la_ultima(self):
        self.press(pygame.K_UP)
        self.press(pygame.K_z)
        self.assertEqual(self.engine._scene_name_to_switch, "credits")

    def test_cambiar_ronda_da_la_vuelta_por_los_niveles(self):
        count = len(ServiceLocator.configs_service.get(ServiceLocator.constants_service.levels_config)["levels"])
        self.press(pygame.K_DOWN)
        self.press(pygame.K_LEFT)
        self.assertEqual(ServiceLocator.game_state_service.level_index, count - 1)
        self.assertIn(f"< RONDA {count} >", texts(self.scene.ecs_world))
        self.press(pygame.K_RIGHT)
        self.assertEqual(ServiceLocator.game_state_service.level_index, 0)

    def test_izquierda_fuera_de_la_ronda_no_cambia_nada(self):
        self.press(pygame.K_LEFT)
        self.assertEqual(ServiceLocator.game_state_service.level_index, 0)

    def test_el_juego_usa_la_ronda_elegida(self):
        ServiceLocator.game_state_service.level_index = 0
        play = self.engine._scenes["play"]
        play.start()
        self.assertEqual(play.level_index, 0)

    def test_ir_y_volver_cambia_de_escena_de_verdad(self):
        self.press(pygame.K_DOWN)
        self.press(pygame.K_DOWN)
        self.engine._current_scene = self.scene
        self.press(pygame.K_z)
        self.engine._handle_switch_scene()
        instructions = self.engine._current_scene
        self.assertIn("INSTRUCCIONES", texts(instructions.ecs_world))
        instructions.process_events(key_event(pygame.KEYDOWN, pygame.K_ESCAPE))
        self.engine._handle_switch_scene()
        self.assertIs(self.engine._current_scene, self.scene)
        self.assertIn("JUGAR", texts(self.scene.ecs_world))


class TestTextScenes(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)

    def test_creditos_muestran_al_equipo_y_vuelven_al_titulo(self):
        scene = self.engine._scenes["credits"]
        scene.start()
        self.assertIn("ESTEBAN LEAL", texts(scene.ecs_world))
        scene.simulate(DT)
        scene.do_draw(self.engine.screen)
        scene.process_events(key_event(pygame.KEYDOWN, pygame.K_x))
        self.assertEqual(self.engine._scene_name_to_switch, "title")

    def test_instrucciones_vuelven_al_titulo_con_aceptar(self):
        scene = self.engine._scenes["instructions"]
        scene.start()
        scene.process_events(key_event(pygame.KEYDOWN, pygame.K_z))
        self.assertEqual(self.engine._scene_name_to_switch, "title")


if __name__ == "__main__":
    unittest.main()
