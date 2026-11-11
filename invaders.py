import os

import numpy as np
from pyglet.gl import GL_NEAREST

import grafica.transformations as tr
from utils import shapes
from utils.camera import Camera, FreeCamera
from utils.drawables import Model, Texture
from utils.helpers import init_pipeline


SHIP_LIMIT = 6.0
SHIP_SPEED = 7.0
SHIP_START = (0.0, 0.6, 10.0)
ENEMY_LIMIT = 10.0
ENEMY_SPEED = 1.7
ENEMY_ADVANCE = 0.7
ENEMY_COLUMNS = 8
ENEMY_ROWS = 4
BULLET_SPEED = 18.0
BULLET_END = -15.0
FIXED_DT = 1.0 / 120.0


ENEMY_TILES = ((0, 0), (1, 0), (1, 1), (0, 1))
SHIP_TILE = (2, 1)
BULLET_TILE = (2, 0)


def atlas_cube(tile, atlas):

    return Model(
        shapes.Cube["position"], get_atlas_uv(*tile, atlas) * 6,
        index_data=shapes.Cube["indices"], normal_data=shapes.Cube["normal"],
    )


def init_enemies(world, controller):

    controller.enemies = []
    for row, tile in enumerate(ENEMY_TILES):
        for column in range(ENEMY_COLUMNS):
            name = f"enemy_{row}_{column}"
            position = np.array(
                [(column - (ENEMY_COLUMNS - 1) / 2) * 1.8,
                 SHIP_START[1], -1.0 - row * 2.3], dtype=np.float32
            )
            world.add_node(
                name, mesh=atlas_cube(tile, controller.atlas),
                texture=controller.atlas, pipeline=controller.pipeline,
                position=position, scale=[0.8, 0.8, 0.8],
            )
            controller.enemies.append({
                "name": name, "position": position.copy(),
                "alive": True, "row": row,
            })


def is_playing(controller):
    return not controller.paused and controller.game_state == "playing"


def shoot(ship_position, world, bullet_mesh, controller):

    if not is_playing(controller):
        return
    name = f"bullet_{controller.bullet_counter}"
    controller.bullet_counter += 1
    position = np.array(ship_position, dtype=np.float32).copy()

    mesh = Model(bullet_mesh.position_data, bullet_mesh.uv_data,
                 normal_data=bullet_mesh.normal_data,
                 index_data=bullet_mesh.index_data)
    world.add_node(
        name, mesh=mesh, texture=controller.atlas, pipeline=controller.pipeline,
        position=position, scale=[0.5, 0.5, 0.5],
    )
    controller.bullets.append({"name": name, "position": position, "alive": True})


def update_ship(world, controller):
    if not is_playing(controller):
        return
    direction = int(controller.right) - int(controller.left)
    position = world["ship"]["position"]
    position[0] = np.clip(position[0] + direction * SHIP_SPEED * controller.dt,
                          -SHIP_LIMIT, SHIP_LIMIT)


def update_enemies(world, controller):

    if not is_playing(controller):
        return
    enemies = [enemy for enemy in controller.enemies if enemy["alive"]]
    if not enemies:
        return

    remaining = ENEMY_SPEED * controller.dt
    while remaining > 1e-9:
        if controller.direction > 0:
            distance = ENEMY_LIMIT - max(e["position"][0] for e in enemies)
        else:
            distance = min(e["position"][0] for e in enemies) + ENEMY_LIMIT
        distance = max(0.0, float(distance))
        movement = min(distance, remaining)
        for enemy in enemies:
            enemy["position"][0] += controller.direction * movement
        remaining -= movement
        if movement >= distance:
            for enemy in enemies:
                enemy["position"][2] += ENEMY_ADVANCE
            controller.direction *= -1
        else:
            break
    for enemy in enemies:
        world[enemy["name"]]["position"] = enemy["position"].copy()


def remove_object(world, obj):
    obj["alive"] = False
    if obj["name"] in world:
        mesh = world[obj["name"]]["mesh"]
        if mesh is not None and mesh.gpu_data is not None:
            mesh.gpu_data.delete()
        world.remove_node(obj["name"])


def update_bullets(world, controller):

    if not is_playing(controller):
        return
    for bullet in controller.bullets:
        if not bullet["alive"]:
            continue
        previous_z = float(bullet["position"][2])
        bullet["position"][2] -= BULLET_SPEED * controller.dt


        hits = []
        for enemy in controller.enemies:
            if not enemy["alive"]:
                continue
            probe = {"position": bullet["position"].copy()}
            probe["position"][2] = np.clip(
                enemy["position"][2], bullet["position"][2], previous_z
            )
            if check_collision(probe, enemy):
                hits.append(enemy)
        if hits:

            enemy = max(hits, key=lambda e: e["position"][2])
            remove_object(world, enemy)
            remove_object(world, bullet)
            controller.score += 100
        elif bullet["position"][2] < BULLET_END:
            remove_object(world, bullet)
        else:
            world[bullet["name"]]["position"] = bullet["position"].copy()
    controller.bullets = [b for b in controller.bullets if b["alive"]]


def update_camera(ship_camera, dt, world):

    ship_camera.position = world["ship"]["position"] + np.array(
        [0.0, 5.6, 7.0], dtype=np.float32
    )
    ship_camera.time_update(dt)


def update_game_state(world, controller):
    alive = [e for e in controller.enemies if e["alive"]]
    if not alive:
        controller.game_state = "won"
    elif any(e["position"][2] + 0.4 >= world["ship"]["position"][2] - 0.5
             for e in alive):
        controller.game_state = "lost"


def reset_game(world, controller):
    for obj in controller.bullets + controller.enemies:
        remove_object(world, obj)
    controller.bullets = []
    controller.bullet_counter = 0
    controller.direction = 1
    controller.time = 0.0
    controller.accumulator = 0.0
    controller.score = 0
    controller.left = controller.right = False
    controller.paused = False
    controller.game_state = "playing"
    world["ship"]["position"] = np.array(SHIP_START, dtype=np.float32)
    init_enemies(world, controller)


def init_controller(controller):
    root = os.path.dirname(__file__)
    controller.pipeline = init_pipeline(root + "/tarea2.vert", root + "/tarea2.frag")
    controller.atlas = Texture(root + "/atlas.png",
                               minFilterMode=GL_NEAREST, maxFilterMode=GL_NEAREST)


def get_atlas_uv(xoffset, yoffset, atlas):

    deltax = 11 / atlas.width
    deltay = 8 / atlas.height
    return [deltax * xoffset, deltay * yoffset,
            deltax * (xoffset + 1), deltay * yoffset,
            deltax * (xoffset + 1), deltay * (yoffset + 1),
            deltax * xoffset, deltay * (yoffset + 1)]


class MyCam(FreeCamera):
    def __init__(self, position=None, camera_type="perspective"):
        super().__init__([0, 0, 0] if position is None else position, camera_type)
        self.direction = np.array([0, 0, 0])
        self.speed = 2

    def time_update(self, dt):
        self.update()
        direction = self.direction[0] * self.forward + self.direction[1] * self.right
        length = np.linalg.norm(direction)
        if length:
            self.position += direction / length * self.speed * dt
        self.focus = self.position + self.forward

    def get_projection(self):
        return tr.perspective(65, self.width / max(1, self.height), 0.1, 100).reshape(
            (16, 1), order="F"
        )


class TopCamera(Camera):

    def __init__(self):
        super().__init__("orthographic")
        self.position = np.array([0, 30, 0], dtype=np.float32)
        self.focus = np.array([0, 0, 0], dtype=np.float32)

    def get_view(self):
        return tr.lookAt(self.position, self.focus, np.array([0, 0, -1])).reshape(
            (16, 1), order="F"
        )

    def get_projection(self):
        aspect = self.width / max(1, self.height)
        half_height = max(15.0, 12.0 / aspect)
        half_width = half_height * aspect
        return tr.ortho(-half_width, half_width, -half_height, half_height,
                        0.1, 100).reshape((16, 1), order="F")


def check_collision(bullet, enemy):

    bx, by, bz = bullet["position"]
    ex, ey, ez = enemy["position"]
    bw, bh, bd = [0.5, 0.5, 0.5]
    ew, eh, ed = [0.8, 0.8, 0.8]
    return (bx - bw / 2 <= ex + ew / 2 and bx + bw / 2 >= ex - ew / 2
            and by - bh / 2 <= ey + eh / 2 and by + bh / 2 >= ey - eh / 2
            and bz - bd / 2 <= ez + ed / 2 and bz + bd / 2 >= ez - ed / 2)
