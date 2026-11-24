import argparse
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

OUTPUT = "assets/img"

ROTATED = {"core_open.png", "core_opening.png", "core_closing.png", "core_closed.png"}

SPRITES = {
    "enemy_i.png": (0, 111, 14, 14),
    "enemy_p.png": (56, 112, 11, 13),
    "enemy_e.png": (41, 109, 7, 16),
    "turret_closed.png": (0, 9, 16, 16),
    "turret_open.png": (42, 9, 16, 16),
    "core_open.png": (0, 46, 20, 20),
    "core_opening.png": (24, 46, 20, 20),
    "core_closing.png": (48, 46, 20, 20),
    "core_closed.png": (72, 46, 20, 20),
    "turret_bullet.png": (13, 76, 6, 4),
}

EXPLOSION_FRAMES = [(0, 133, 16, 16), (16, 133, 16, 16), (32, 133, 16, 16),
                    (49, 134, 14, 15), (66, 134, 13, 13), (83, 136, 11, 10)]
EXPLOSION_CELL = 16

BODY_RECT = (124, 56, 72, 64)
BODY_POD_CENTERS = [(8, 32), (64, 32), (24, 8), (48, 8), (24, 56), (48, 56)]
BODY_POD_RADIUS = 9
BODY_CORE_RECT = (26, 22, 20, 20)


def is_key_color(color: pygame.Color) -> bool:
    return color.r > 200 and color.g < 60 and color.b > 200


def crop(sheet: pygame.Surface, rect: tuple[int, int, int, int]) -> pygame.Surface:
    piece = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    piece.blit(sheet, (0, 0), pygame.Rect(rect))
    for x in range(piece.get_width()):
        for y in range(piece.get_height()):
            if is_key_color(piece.get_at((x, y))):
                piece.set_at((x, y), (0, 0, 0, 0))
    return piece


def build_explosion_strip(sheet: pygame.Surface) -> pygame.Surface:
    strip = pygame.Surface((EXPLOSION_CELL * len(EXPLOSION_FRAMES), EXPLOSION_CELL), pygame.SRCALPHA)
    for index, rect in enumerate(EXPLOSION_FRAMES):
        frame = crop(sheet, rect)
        cell = pygame.Rect(index * EXPLOSION_CELL, 0, EXPLOSION_CELL, EXPLOSION_CELL)
        strip.blit(frame, frame.get_rect(center=cell.center))
    return strip


def build_base_body(sheet: pygame.Surface) -> pygame.Surface:
    body = crop(sheet, BODY_RECT)
    for x in range(body.get_width()):
        for y in range(body.get_height()):
            for cx, cy in BODY_POD_CENTERS:
                if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= BODY_POD_RADIUS ** 2:
                    body.set_at((x, y), (0, 0, 0, 0))
    core = pygame.Rect(BODY_CORE_RECT)
    for x in range(core.left, core.right):
        for y in range(core.top, core.bottom):
            body.set_at((x, y), (0, 0, 0, 0))
    return pygame.transform.rotate(body, -90)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sheet")
    parser.add_argument("--output", default=OUTPUT)
    args = parser.parse_args()
    pygame.init()
    pygame.display.set_mode((1, 1))
    sheet = pygame.image.load(args.sheet).convert_alpha()
    for name, rect in SPRITES.items():
        piece = crop(sheet, rect)
        if name in ROTATED:
            piece = pygame.transform.rotate(piece, -90)
        pygame.image.save(piece, os.path.join(args.output, name))
    pygame.image.save(build_explosion_strip(sheet), os.path.join(args.output, "explosion.png"))
    pygame.image.save(build_base_body(sheet), os.path.join(args.output, "base_body.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
