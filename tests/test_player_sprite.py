import os
import unittest
import warnings

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import esper
import pygame

from src.create.prefab_player import SPRITE_DIRECTIONS, build_directional_frames, create_player
from src.ecs.components.c_directional_sprite import CDirectionalSprite
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_player_movement import CPlayerMovement
from src.ecs.components.c_surface import CSurface
from src.ecs.systems.s_player_sprite import direction_index, system_player_sprite
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator
from tests.test_input import key_event

V = pygame.Vector2


def player_info():
    return ServiceLocator.configs_service.get(ServiceLocator.constants_service.player_config)


class TestDirectionIndex(unittest.TestCase):
    def test_ocho_direcciones_empezando_arriba_en_sentido_horario(self):
        expected = {(0, -1): 0, (1, -1): 1, (1, 0): 2, (1, 1): 3, (0, 1): 4, (-1, 1): 5, (-1, 0): 6, (-1, -1): 7}
        for (x, y), index in expected.items():
            self.assertEqual(direction_index(x, y, 8), index, (x, y))

    def test_direccion_normalizada_da_el_mismo_indice(self):
        v = V(1, -1).normalize()
        self.assertEqual(direction_index(v.x, v.y, 8), 1)


class TestSpritesDelJugador(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.world = esper.World()
        self.info = player_info()
        self.player = create_player(self.world, self.info, V(100, 100))

    def test_la_config_real_apunta_a_una_imagen_que_existe(self):
        self.assertTrue(os.path.exists(self.info["image"]))
        self.assertGreater(ServiceLocator.images_service.get(self.info["image"]).get_width(), 0)

    def test_el_jugador_usa_la_imagen_y_no_el_cuadrado(self):
        c_s = self.world.component_for_entity(self.player, CSurface)
        self.assertEqual(c_s.area.size, (self.info["size"]["w"], self.info["size"]["h"]))
        self.assertGreater(c_s.surf.get_bounding_rect().width, 0)
        self.assertEqual(c_s.surf.get_at((0, 0)).a, 0)

    def test_hay_un_cuadro_por_direccion_todos_del_mismo_tamano(self):
        frames = self.world.component_for_entity(self.player, CDirectionalSprite).frames
        self.assertEqual(len(frames), SPRITE_DIRECTIONS)
        for frame in frames:
            self.assertEqual(frame.get_size(), (self.info["size"]["w"], self.info["size"]["h"]))

    def test_arranca_mirando_hacia_arriba_con_la_nave_centrada(self):
        image = ServiceLocator.images_service.get(self.info["image"])
        c_s = self.world.component_for_entity(self.player, CSurface)
        box = c_s.surf.get_bounding_rect()
        self.assertEqual(box.size, image.get_size())
        self.assertEqual(box.center, c_s.surf.get_rect().center)

    def test_de_lado_la_nave_es_mas_ancha_que_alta(self):
        frames = self.world.component_for_entity(self.player, CDirectionalSprite).frames
        up, right = frames[0].get_bounding_rect(), frames[2].get_bounding_rect()
        self.assertEqual((right.width, right.height), (up.height, up.width))
        self.assertEqual(right.center, frames[2].get_rect().center)

    def test_cambiar_de_direccion_cambia_el_cuadro(self):
        c_s = self.world.component_for_entity(self.player, CSurface)
        c_pm = self.world.component_for_entity(self.player, CPlayerMovement)
        c_ds = self.world.component_for_entity(self.player, CDirectionalSprite)
        c_pm.direction = V(1, 0)
        system_player_sprite(self.world)
        self.assertIs(c_s.surf, c_ds.frames[2])
        c_pm.direction = V(-1, 1).normalize()
        system_player_sprite(self.world)
        self.assertIs(c_s.surf, c_ds.frames[5])

    def test_el_tamano_del_sprite_no_cambia_al_girar(self):
        c_s = self.world.component_for_entity(self.player, CSurface)
        c_pm = self.world.component_for_entity(self.player, CPlayerMovement)
        for direction in (V(1, 0), V(1, 1), V(0, 1), V(-1, 0)):
            c_pm.direction = direction.normalize()
            system_player_sprite(self.world)
            self.assertEqual(c_s.area.size, (self.info["size"]["w"], self.info["size"]["h"]))

    def test_la_hitbox_sigue_centrada_en_el_sprite(self):
        c_h = self.world.component_for_entity(self.player, CHitBox)
        size = self.info["size"]
        self.assertEqual(c_h.offset + c_h.size / 2, V(size["w"], size["h"]) / 2)

    def test_sin_imagen_en_la_config_usa_el_cuadrado(self):
        info = {k: v for k, v in self.info.items() if k != "image"}
        player = create_player(esper.World(), info, V(0, 0))
        self.assertIsNotNone(player)

    def test_construir_cuadros_no_modifica_la_imagen_original(self):
        image = pygame.Surface((4, 6), pygame.SRCALPHA)
        image.fill((255, 0, 0, 255))
        build_directional_frames(image, (8, 8))
        self.assertEqual(image.get_size(), (4, 6))

    def test_una_imagen_que_no_cabe_girada_da_error(self):
        image = pygame.Surface((8, 8), pygame.SRCALPHA)
        # Recta cabe justo, pero girada 45° mide ~12 px.
        with self.assertRaises(ValueError):
            build_directional_frames(image, (8, 8))

    def test_los_cuadros_se_generan_una_vez_y_se_reutilizan(self):
        first = self.world.component_for_entity(self.player, CDirectionalSprite).frames
        other_world = esper.World()
        other = create_player(other_world, self.info, V(0, 0))
        second = other_world.component_for_entity(other, CDirectionalSprite).frames
        for a, b in zip(first, second, strict=True):
            self.assertIs(a, b)

    def test_con_imagen_no_se_crea_el_cuadrado_de_color(self):
        c_s = self.world.component_for_entity(self.player, CSurface)
        frames = self.world.component_for_entity(self.player, CDirectionalSprite).frames
        self.assertIs(c_s.surf, frames[0])


class TestSpriteEnPlayScene(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("ignore", message="no fast renderer")
        self.engine = GameEngine()
        self.addCleanup(pygame.quit)
        self.addCleanup(ServiceLocator.fonts_service.clear)
        self.scene = self.engine._scenes["play"]
        self.scene.start()

    def test_al_presionar_una_flecha_la_nave_gira(self):
        world = self.scene.ecs_world
        c_ds = world.get_component(CDirectionalSprite)[0][1]
        self.assertEqual(c_ds.current, 0)
        self.scene.process_events(key_event(pygame.KEYDOWN, pygame.K_RIGHT))
        self.scene.simulate(1 / 60)
        self.assertEqual(c_ds.current, 2)
        self.scene.do_draw(self.engine.screen)


if __name__ == "__main__":
    unittest.main()
