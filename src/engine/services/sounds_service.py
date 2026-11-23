import pygame


class SoundsService:
    """Efectos y música del juego (#38), con los nombres de sounds.json.

    Los efectos se cargan una sola vez (caché) y se reproducen con play_effect y el nombre del efecto.
    La música se reproduce en streaming con pygame.mixer.music: una pista a la vez, en bucle.
    Sin dispositivo de audio (mixer apagado) nada suena, pero current_music se sigue
    actualizando, así la lógica funciona igual en las pruebas y en máquinas sin sonido.
    """

    def __init__(self) -> None:
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._effects: dict[str, str] = {}
        self._music: dict[str, str] = {}
        self._level_music: list[str] = []
        self._effects_volume = 1.0
        self._music_volume = 1.0
        self.current_music: str | None = None

    def load(self, sounds_info: dict) -> None:
        """Lee sounds.json. Lo llama GameEngine al iniciar."""
        self._effects = sounds_info["effects"]
        self._music = sounds_info["music"]
        self._level_music = sounds_info["level_music"]
        self._effects_volume = sounds_info["effects_volume"]
        self._music_volume = sounds_info["music_volume"]
        self.current_music = None

    def _ensure_loaded(self) -> None:
        """Si nadie llamó a load (p. ej. una prueba sin GameEngine), lee sounds.json la primera vez."""
        if not self._effects:
            # Import local: ServiceLocator importa este módulo.
            from src.engine.service_locator import ServiceLocator
            constants = ServiceLocator.constants_service
            self.load(ServiceLocator.configs_service.get(constants.sounds_config))

    def get(self, path: str) -> pygame.mixer.Sound:
        """Devuelve el sonido de path, cargándolo solo la primera vez."""
        if path not in self._sounds:
            self._sounds[path] = pygame.mixer.Sound(path)
            self._sounds[path].set_volume(self._effects_volume)
        return self._sounds[path]

    def play(self, path: str) -> None:
        """Reproduce el sonido de path. Sin dispositivo de audio (mixer apagado) no hace nada."""
        if pygame.mixer.get_init() is None:
            return
        self.get(path).play()

    def play_effect(self, name: str) -> None:
        """Reproduce el efecto name de sounds.json (p. ej. "PLAYER_FIRE")."""
        self._ensure_loaded()
        self.play(self._effects[name])

    def level_music(self, level_index: int) -> str:
        """Pista de la ronda: las de level_music se turnan, así la música cambia en cada ronda."""
        self._ensure_loaded()
        return self._level_music[level_index % len(self._level_music)]

    def play_music(self, name: str) -> None:
        """Pone la pista name en bucle. Si ya sonaba, sigue sin empezar de nuevo (y se reanuda si estaba en pausa)."""
        self._ensure_loaded()
        if name == self.current_music:
            self.resume_music()
            return
        path = self._music[name]
        self.current_music = name
        if pygame.mixer.get_init() is None:
            return
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(self._music_volume)
        pygame.mixer.music.play(-1)

    def pause_music(self) -> None:
        if pygame.mixer.get_init() is not None:
            pygame.mixer.music.pause()

    def resume_music(self) -> None:
        if pygame.mixer.get_init() is not None:
            pygame.mixer.music.unpause()

    def stop_music(self) -> None:
        self.current_music = None
        if pygame.mixer.get_init() is not None:
            pygame.mixer.music.stop()
