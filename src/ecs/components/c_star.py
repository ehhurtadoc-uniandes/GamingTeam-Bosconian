class CStar:
    """Una estrella del fondo.

    parallax: qué fracción del movimiento de la cámara sigue (0.5 = la mitad, se ve más lejos).
    alpha y rising: el brillo (LC-EST-02). alpha va de 0 a 255 y vuelve, subiendo si rising.
    """

    def __init__(self, parallax: float, alpha: float, rising: bool) -> None:
        self.parallax = parallax
        self.alpha = alpha
        self.rising = rising
