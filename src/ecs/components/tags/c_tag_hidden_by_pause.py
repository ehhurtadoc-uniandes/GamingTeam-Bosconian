class CTagHiddenByPause:
    """Marca las entidades que escondió la pausa, para que al reanudar solo se muestren esas.

    Así, si algo ya tenía CTagHidden por otra razón (por ejemplo, el jugador mientras
    reaparece), reanudar no lo vuelve a mostrar antes de tiempo.
    """
