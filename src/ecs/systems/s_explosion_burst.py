import esper

from src.create.prefab_explosion import create_explosion
from src.ecs.components.c_explosion_burst import CExplosionBurst
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity


def system_explosion_burst(world: esper.World, delta_time: float) -> None:
    c_t: CTransform
    c_v: CVelocity
    c_b: CExplosionBurst
    for entity, (c_t, c_v, c_b) in world.get_components(CTransform, CVelocity, CExplosionBurst):
        c_b.elapsed += delta_time
        due = [item for item in c_b.pending if item[0] <= c_b.elapsed]
        c_b.pending = [item for item in c_b.pending if item[0] > c_b.elapsed]
        for _, offset in due:
            create_explosion(world, c_b.explosion_info, c_t.pos + offset, c_v.vel)
        if not c_b.pending:
            world.delete_entity(entity)
