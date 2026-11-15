from src.create.prefab_menu import create_text_lines
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.engine.service_locator import ServiceLocator
from src.scenes.menu_scene import MenuScene


class TextScene(MenuScene):
    """Pantalla de solo texto que vuelve al título al aceptar o volver.

    Se usa para las instrucciones (LC-ESC-02.3) y los créditos (LC-ESC-02.2): cambia solo el JSON.
    """

    def do_create_menu(self) -> None:
        create_text_lines(self.ecs_world, self._config["lines"])

    def do_action(self, action: CInputCommand) -> None:
        constants = ServiceLocator.constants_service
        if action.phase == CommandPhase.START and action.name in (constants.menu_accept_command,
                                                                  constants.menu_back_command):
            self.switch_scene("title")
