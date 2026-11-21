class CLeavingBase:
    """Enemigo que acaba de salir del núcleo de base y todavía está dentro de su cuerpo (#27).

    Mientras lo tenga, system_enemy_bounce no lo hace rebotar contra esa base: si no,
    al nacer en el centro del núcleo lo empujaría al borde de la base y podría invertir
    su rumbo. system_enemy_bounce lo quita en cuanto el enemigo deja de tocar la base.
    """

    def __init__(self, base: int) -> None:
        self.base = base
