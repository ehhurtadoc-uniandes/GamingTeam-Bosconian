"""Punto de entrada del juego, en escritorio y en web (pygbag)."""
import asyncio

import pygame  # pygbag detecta las dependencias por los imports de este archivo

from src.engine.game_engine import GameEngine


async def main() -> None:
    engine = GameEngine()
    await engine.run("play")


if __name__ == "__main__":
    asyncio.run(main())
