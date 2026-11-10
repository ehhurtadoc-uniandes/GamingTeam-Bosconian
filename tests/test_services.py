"""Pruebas del Service Locator. Ejecutar con: python -m unittest discover -s tests"""
import json
import os
import tempfile
import unittest
import wave

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from src.engine.service_locator import ServiceLocator
from src.engine.services.configs_service import ConfigsService
from src.engine.services.fonts_service import FontsService
from src.engine.services.images_service import ImagesService
from src.engine.services.sounds_service import SoundsService


class TestServices(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((1, 1))
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.addCleanup(pygame.quit)
        self.dir = temp_dir.name

    def _wav(self):
        path = os.path.join(self.dir, "sonido.wav")
        with wave.open(path, "wb") as file:
            file.setnchannels(1)
            file.setsampwidth(2)
            file.setframerate(44100)
            file.writeframes(b"\x00\x00" * 100)
        return path

    def test_imagen_se_carga_una_sola_vez(self):
        path = os.path.join(self.dir, "imagen.png")
        pygame.image.save(pygame.Surface((4, 2)), path)
        service = ImagesService()
        image = service.get(path)
        self.assertEqual(image.get_size(), (4, 2))
        self.assertIs(service.get(path), image)

    def test_sonido_se_carga_una_sola_vez(self):
        path = self._wav()
        service = SoundsService()
        self.assertIs(service.get(path), service.get(path))
        service.play(path)

    def test_fuente_se_guarda_por_ruta_y_tamano(self):
        path = os.path.join(os.path.dirname(pygame.__file__), pygame.font.get_default_font())
        service = FontsService()
        font = service.get(path, 8)
        self.assertIs(service.get(path, 8), font)
        self.assertIsNot(service.get(path, 16), font)

    def test_config_se_carga_una_sola_vez(self):
        path = os.path.join(self.dir, "config.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump({"nombre": "ñandú"}, file, ensure_ascii=False)
        service = ConfigsService()
        config = service.get(path)
        self.assertEqual(config["nombre"], "ñandú")
        self.assertIs(service.get(path), config)

    def test_ventana_usa_la_resolucion_del_juego(self):
        window = ConfigsService().get("assets/cfg/window.json")
        self.assertEqual(window["size"], {"w": 256, "h": 208})

    def test_locator_expone_los_servicios(self):
        self.assertIsInstance(ServiceLocator.images_service, ImagesService)
        self.assertIsInstance(ServiceLocator.sounds_service, SoundsService)
        self.assertIsInstance(ServiceLocator.fonts_service, FontsService)
        self.assertIsInstance(ServiceLocator.configs_service, ConfigsService)


if __name__ == "__main__":
    unittest.main()
