import asyncio

import pygame

from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator
from src.scenes.play_scene import PlayScene

WINDOW_CONFIG = "assets/cfg/window.json"


class GameEngine:
    """Game loop con delta fijo y manejo de escenas (patrones Game Loop y Scene)."""

    def __init__(self) -> None:
        window = ServiceLocator.configs_service.get(WINDOW_CONFIG)
        pygame.init()
        size = window["size"]
        self.screen = pygame.display.set_mode((size["w"], size["h"]), pygame.SCALED)
        pygame.display.set_caption(window["title"])
        color = window["bg_color"]
        self.bg_color = pygame.Color(color["r"], color["g"], color["b"])
        self.framerate: int = window["framerate"]
        self.fixed_dt = 1 / self.framerate
        self.max_frame_time: float = window["max_frame_time"]
        self.clock = pygame.time.Clock()
        self.is_running = False
        self._accumulator = 0.0

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
        self.clock.tick(self.framerate)
        self._add_frame_time(self.clock.get_time() / 1000)

    def _add_frame_time(self, frame_time: float) -> None:
        # Se limita para que, tras una pausa larga, el juego no corra cientos de pasos seguidos.
        self._accumulator += min(frame_time, self.max_frame_time)

    def _process_events(self) -> None:
        for event in pygame.event.get():
            self._current_scene.do_process_events(event)
            if event.type == pygame.QUIT:
                self.is_running = False

    def _update(self) -> None:
        while self._accumulator >= self.fixed_dt:
            self._current_scene.simulate(self.fixed_dt)
            self._accumulator -= self.fixed_dt

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
