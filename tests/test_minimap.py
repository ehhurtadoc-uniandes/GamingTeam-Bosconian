"""Pruebas del minimapa."""
import unittest

import esper
import pygame

from src.create.prefab_minimap import create_minimap
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.tags.c_tag_base import CTagBase
from src.ecs.components.tags.c_tag_player import CTagPlayer
from src.ecs.systems.s_minimap import system_minimap, to_minimap

WORLD = pygame.Vector2(1024, 1536)
INFO = {"rect": {"x": 192, "y": 80, "w": 64, "h": 96}, "bg_color": {"r": 0, "g": 0, "b": 100},
        "base_color": {"r": 0, "g": 255, "b": 0}, "player_color": {"r": 255, "g": 255, "b": 255},
        "dot_size": 2, "player_blink": 0.25}


class TestMinimap(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()
        self.minimap = create_minimap(self.world, INFO)

    def surface(self):
        return self.world.component_for_entity(self.minimap, CSurface).surf

    def add(self, center, tag):
        surf = CSurface(pygame.Vector2(16, 16), pygame.Color(0, 0, 0))
        return self.world.create_entity(CTransform(pygame.Vector2(center) - pygame.Vector2(8, 8)), surf, tag)

    def test_escala_el_mundo_al_minimapa(self):
        self.assertEqual(to_minimap(pygame.Vector2(512, 768), WORLD, (64, 96)), pygame.Vector2(32, 48))

    def test_posicion_pasada_del_borde_sale_por_el_otro_lado(self):
        self.assertEqual(to_minimap(pygame.Vector2(1024 + 16, -16), WORLD, (64, 96)), pygame.Vector2(1, 95))

    def test_jugador_en_el_borde_se_ve_completo(self):
        """pos.x cerca del borde derecho: el centro se pasa del mundo y el punto sale a la izquierda."""
        self.add((1028, 768), CTagPlayer())
        system_minimap(self.world, 0.0, WORLD)
        white = sum(self.surface().get_at((x, y))[:3] == (255, 255, 255) for x in range(64) for y in range(96))
        self.assertEqual(white, INFO["dot_size"] ** 2)

    def test_dibuja_bases_y_jugador(self):
        self.add((512, 768), CTagBase())
        self.add((0, 0), CTagPlayer())
        system_minimap(self.world, 0.0, WORLD)
        self.assertEqual(self.surface().get_at((32, 48))[:3], (0, 255, 0))
        self.assertEqual(self.surface().get_at((0, 0))[:3], (255, 255, 255))

    def test_base_destruida_desaparece(self):
        base = self.add((512, 768), CTagBase())
        system_minimap(self.world, 0.0, WORLD)
        self.world.delete_entity(base, immediate=True)
        system_minimap(self.world, 0.0, WORLD)
        self.assertEqual(self.surface().get_at((32, 48))[:3], (0, 0, 100))

    def test_jugador_parpadea(self):
        self.add((0, 0), CTagPlayer())
        system_minimap(self.world, 0.3, WORLD)
        self.assertEqual(self.surface().get_at((0, 0))[:3], (0, 0, 100))


if __name__ == "__main__":
    unittest.main()
