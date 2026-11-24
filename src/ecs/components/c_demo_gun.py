class CDemoGun:

    def __init__(self, interval: float, bullet_info: dict) -> None:
        self.interval = interval
        self.remaining = interval
        self.bullet_info = bullet_info
