class CAnimation:
    """Animación de una tira de cuadros del mismo ancho, uno al lado del otro.

    Con loop=False se queda en el último cuadro y marca finished (p. ej. una explosión).
    """

    def __init__(self, number_frames: int, framerate: float, loop: bool = True) -> None:
        self.number_frames = number_frames
        self.frame_time = 1.0 / framerate
        self.time_left = self.frame_time
        self.current_frame = 0
        self.loop = loop
        self.finished = False
