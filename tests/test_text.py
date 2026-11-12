"""Pruebas de los textos de interfaz. Ejecutar con: python -m unittest discover -s tests"""
import os
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_text import create_text
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_text import CText, TextAlignment
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_ui import CTagUI
from src.ecs.systems.s_rendering import system_rendering
from src.ecs.systems.s_text import aligned_position, system_text
from src.engine.service_locator import ServiceLocator

WHITE = pygame.Color(255, 255, 255)
RED = pygame.Color(255, 0, 0)


class TestText(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        interface = ServiceLocator.configs_service.get("assets/cfg/interface.json")
        self.font = pygame.font.Font(interface["font"], interface["font_size"])
        self.world = esper.World()

    def text_rect(self, entity):
        pos = self.world.component_for_entity(entity, CTransform).pos
        area = self.world.component_for_entity(entity, CSurface).area
        return pygame.Rect(pos, area.size)

    def test_from_text_tiene_el_tamano_del_texto(self):
        c_surface = CSurface.from_text("HOLA", self.font, WHITE)
        self.assertEqual(c_surface.area.size, self.font.size("HOLA"))

    def test_alineacion_respecto_al_ancla(self):
        anchor = pygame.Vector2(100, 10)
        self.assertEqual(aligned_position(anchor, 40, TextAlignment.LEFT), pygame.Vector2(100, 10))
        self.assertEqual(aligned_position(anchor, 40, TextAlignment.CENTER), pygame.Vector2(80, 10))
        self.assertEqual(aligned_position(anchor, 40, TextAlignment.RIGHT), pygame.Vector2(60, 10))

    def test_create_text_es_interfaz_y_queda_alineado(self):
        entity = create_text(self.world, "20000", self.font, WHITE, pygame.Vector2(200, 8),
                             TextAlignment.RIGHT)
        self.assertTrue(self.world.has_component(entity, CTagUI))
        self.assertEqual(self.text_rect(entity).right, 200)

    def test_cambiar_el_texto_lo_redibuja_y_conserva_la_alineacion(self):
        entity = create_text(self.world, "0", self.font, WHITE, pygame.Vector2(200, 8),
                             TextAlignment.RIGHT)
        self.world.component_for_entity(entity, CText).text = "12345"
        system_text(self.world)
        rect = self.text_rect(entity)
        self.assertEqual(rect.size, self.font.size("12345"))
        self.assertEqual(rect.right, 200)

    def test_cambiar_el_color_lo_redibuja(self):
        entity = create_text(self.world, "A", self.font, WHITE, pygame.Vector2(0, 0))
        before = self.world.component_for_entity(entity, CSurface).surf
        self.world.component_for_entity(entity, CText).color = RED
        system_text(self.world)
        self.assertIsNot(self.world.component_for_entity(entity, CSurface).surf, before)

    def test_sin_cambios_no_se_redibuja(self):
        entity = create_text(self.world, "A", self.font, WHITE, pygame.Vector2(0, 0))
        before = self.world.component_for_entity(entity, CSurface).surf
        system_text(self.world)
        self.assertIs(self.world.component_for_entity(entity, CSurface).surf, before)

    def test_la_interfaz_se_dibuja_encima_del_mundo(self):
        screen = pygame.Surface((8, 8))
        # La interfaz se crea primero para comprobar que el orden no depende de la creación.
        ui = CSurface(pygame.Vector2(8, 8), RED)
        self.world.create_entity(CTransform(pygame.Vector2(0, 0)), ui, CTagUI())
        world_square = CSurface(pygame.Vector2(8, 8), WHITE)
        self.world.create_entity(CTransform(pygame.Vector2(0, 0)), world_square)
        system_rendering(self.world, screen)
        self.assertEqual(screen.get_at((4, 4)), RED)


if __name__ == "__main__":
    unittest.main()
