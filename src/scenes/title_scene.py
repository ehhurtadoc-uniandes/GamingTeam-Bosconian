from src.create.prefab_menu import create_menu, update_menu_values
from src.ecs.components.c_input_command import CInputCommand, CommandPhase
from src.ecs.systems.s_menu import get_menu, move_selection, selected_action, system_menu_highlight
from src.engine.service_locator import ServiceLocator
from src.scenes.menu_scene import MenuScene


class TitleScene(MenuScene):
    """Escena de título (LC-ESC-02): jugar, elegir la ronda, instrucciones y créditos.

    Arriba y abajo eligen la opción; izquierda y derecha cambian la ronda; aceptar la ejecuta.
    Las opciones y sus acciones (PLAY, LEVEL, INSTRUCTIONS, CREDITS) vienen de title.json.
    """

    def __init__(self, game_engine) -> None:
        super().__init__(game_engine, ServiceLocator.constants_service.title_config)

    def do_create_menu(self) -> None:
        constants = ServiceLocator.constants_service
        self._level_count = len(ServiceLocator.configs_service.get(constants.levels_config)["levels"])
        create_menu(self.ecs_world, self._config["menu"], self._menu_values())

    def _menu_values(self) -> dict:
        # La ronda se muestra desde 1; level_index empieza en 0.
        return {"level": ServiceLocator.game_state_service.level_index + 1}

    def do_update(self, delta_time: float) -> None:
        super().do_update(delta_time)
        system_menu_highlight(self.ecs_world)

    def do_action(self, action: CInputCommand) -> None:
        if action.phase != CommandPhase.START:
            return
        constants = ServiceLocator.constants_service
        menu = get_menu(self.ecs_world)
        if action.name in constants.menu_move_commands:
            menu.selected = move_selection(menu.selected, constants.menu_move_commands[action.name], menu.count)
        elif action.name in constants.menu_change_commands:
            if selected_action(self.ecs_world) == "LEVEL":
                self.change_level(constants.menu_change_commands[action.name])
        elif action.name == constants.menu_accept_command:
            self.accept(selected_action(self.ecs_world))

    def change_level(self, step: int) -> None:
        """Elige la ronda anterior o la siguiente; de la última pasa a la primera (LC-ESC-02.1)."""
        game_state = ServiceLocator.game_state_service
        game_state.level_index = move_selection(game_state.level_index, step, self._level_count)
        update_menu_values(self.ecs_world, self._menu_values())

    def accept(self, action: str) -> None:
        """Ejecuta la opción elegida. En la ronda, aceptar también empieza a jugar."""
        if action in ("PLAY", "LEVEL"):
            ServiceLocator.game_state_service.new_game()
            self.switch_scene("play")
        elif action == "INSTRUCTIONS":
            self.switch_scene("instructions")
        elif action == "CREDITS":
            self.switch_scene("credits")
