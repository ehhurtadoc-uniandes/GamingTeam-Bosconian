import asyncio
import sys

import pygame

from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator
from src.scenes.play_scene import PlayScene


class GameEngine:
    """Game loop a framerate fijo y manejo de escenas (patrones Game Loop y Scene)."""

    def __init__(self) -> None:
        constants = ServiceLocator.constants_service
        window = ServiceLocator.configs_service.get(constants.window_config)
        pygame.init()
        size = window["size"]
        # En web (pygbag) SCALED falla con "failed to create renderer"; ahí el navegador escala el canvas.
        flags = 0 if sys.platform == "emscripten" else pygame.SCALED
        self.screen = pygame.display.set_mode((size["w"], size["h"]), flags)
        pygame.display.set_caption(window["title"])
        color = window["bg_color"]
        self.bg_color = pygame.Color(color["r"], color["g"], color["b"])
        self.framerate: int = window["framerate"]
        self.clock = pygame.time.Clock()
        self.is_running = False
        self.delta_time = 0.0
        ServiceLocator.game_state_service.load(ServiceLocator.configs_service.get(constants.score_config))

        self._scenes: dict[str, Scene] = {
            "play": PlayScene(self),
        }
        self._current_scene: Scene | None = None
        self._scene_name_to_switch: str | None = None

    async def run(self, start_scene_name: str) -> None:
        """Corre el juego desde start_scene_name hasta que se cierre la ventana."""
        self.is_running = True
        self._current_scene = self._scenes[start_scene_name]
        self._current_scene.start()
        while self.is_running:
            self._calculate_time()
            self._process_events()
            self._update()
            self._draw()
            self._handle_switch_scene()
            # Sin esto la pestaña del navegador se congela con pygbag.
            await asyncio.sleep(0)
        self._current_scene.clean()
        pygame.quit()

    def switch_scene(self, new_scene_name: str) -> None:
        """Anota el cambio de escena; se aplica al final del frame, nunca a mitad de un update."""
        self._scene_name_to_switch = new_scene_name

    def _calculate_time(self) -> None:
        # tick_busy_loop espera hasta completar el frame de forma activa, así el framerate es más
        # exacto que con tick, que duerme y puede despertarse tarde. En el navegador (pygbag) una
        # espera activa congelaría la pestaña, así que ahí se usa tick.
        if sys.platform == "emscripten":
            milliseconds = self.clock.tick(self.framerate)
        else:
            milliseconds = self.clock.tick_busy_loop(self.framerate)
        # tick limita qué tan rápido corre el juego, no cuánto puede durar un frame: si la ventana se
        # arrastra o la pestaña se suspende, el siguiente frame mide segundos y todo saltaría de golpe
        # (balas que atraviesan enemigos, tiempos de vida que vencen). Por eso se acota el delta.
        self.delta_time = min(milliseconds / 1000, ServiceLocator.constants_service.max_delta_time)

    def _process_events(self) -> None:
        for event in pygame.event.get():
            self._current_scene.process_events(event)
            if event.type == pygame.QUIT:
                self.is_running = False

    def _update(self) -> None:
        self._current_scene.simulate(self.delta_time)

    def _draw(self) -> None:
        self.screen.fill(self.bg_color)
        self._current_scene.do_draw(self.screen)
        pygame.display.flip()

    def _handle_switch_scene(self) -> None:
        if self._scene_name_to_switch is None:
            return
        self._current_scene.clean()
        self._current_scene = self._scenes[self._scene_name_to_switch]
        self._scene_name_to_switch = None
        self._current_scene.start()
