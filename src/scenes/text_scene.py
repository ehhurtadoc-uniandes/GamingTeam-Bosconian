from src.create.prefab_menu import create_text_lines
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.engine.service_locator import ServiceLocator
from src.scenes.menu_scene import MenuScene, is_user_input


class TextScene(MenuScene):
    """Pantalla de solo texto que vuelve al título al aceptar o volver.

    Se usa para las instrucciones (LC-ESC-02.3) y los créditos (LC-ESC-02.2): cambia solo el JSON.
    """

    def __init__(self, game_engine, config_path: str) -> None:
        super().__init__(game_engine, config_path)
        self.time_left = 0.0

    def do_create_menu(self) -> None:
        self.time_left = self._config.get("attract_time", 0.0)
        create_text_lines(self.ecs_world, self._config["lines"])

    def do_update(self, delta_time: float) -> None:
        super().do_update(delta_time)
        if self.time_left <= 0 or not ServiceLocator.game_state_service.attract:
            return
        self.time_left -= delta_time
        if self.time_left <= 0:
            self.switch_scene("title")

    def do_process_events(self, event) -> None:
        if ServiceLocator.game_state_service.attract and is_user_input(event):
            self.switch_scene("title")

    def do_action(self, action: CInputCommand) -> None:
        constants = ServiceLocator.constants_service
        if ServiceLocator.game_state_service.attract:
            return
        if action.phase == CommandPhase.START and action.name in (constants.menu_accept_command,
                                                                  constants.menu_back_command):
            ServiceLocator.sounds_service.play_effect("MENU_ACCEPT")
            self.switch_scene("title")
