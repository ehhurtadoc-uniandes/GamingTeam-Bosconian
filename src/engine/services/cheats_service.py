class CheatsService:
    """Modo trampa (LC-EG-04): qué trampas están activas.

    Vive en el ServiceLocator para que una trampa activada siga activa al cambiar de nivel,
    al reaparecer o al continuar. enabled sale de cheats.json: si es false, ninguna trampa
    funciona aunque se presionen sus teclas.
    """

    def __init__(self) -> None:
        self.enabled = False
        self._active: set[str] = set()

    def load(self, cheats_info: dict) -> None:
        """Arranca sin trampas activas. Lo llama GameEngine al iniciar."""
        self.enabled = cheats_info["enabled"]
        self._active.clear()

    def is_active(self, name: str) -> bool:
        return self.enabled and name in self._active

    def toggle(self, name: str) -> bool:
        """Activa la trampa si estaba apagada y al revés. Devuelve si quedó activa."""
        if name in self._active:
            self._active.discard(name)
        else:
            self._active.add(name)
        return name in self._active
