import numpy as np
import pyglet
from pyglet import clock
from pyglet.app import run
from pyglet.gl import (GL_BLEND, GL_DEPTH_TEST, GL_ONE_MINUS_SRC_ALPHA,
                       GL_SRC_ALPHA, glBlendFunc, glClearColor, glDisable, glEnable)
from pyglet.window import Window, key

from invaders import (BULLET_TILE, ENEMY_COLUMNS, ENEMY_ROWS, FIXED_DT,
                      SHIP_START, SHIP_TILE, MyCam, TopCamera, atlas_cube,
                      init_controller, init_enemies, is_playing, reset_game,
                      shoot, update_bullets, update_camera, update_enemies,
                      update_game_state, update_ship)
from utils import shapes
from utils.drawables import Model, Texture
from utils.scene_graph import SceneGraph


class Controller(Window):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.time = 0.0
        self.left = False
        self.right = False

        self.camera_mode = 1
        self.pipeline = None
        self.atlas = None
        self.enemies = []
        self.bullets = []
        self.bullet_counter = 0
        self.direction = 1
        self.dt = FIXED_DT
        self.accumulator = 0.0
        self.paused = False
        self.spotlight_on = True
        self.game_state = "playing"
        self.score = 0


class HUD:

    def __init__(self, window):
        self.window = window
        self.batch = pyglet.graphics.Batch()
        self.background = pyglet.graphics.Group(order=0)
        self.foreground = pyglet.graphics.Group(order=1)
        self.top = pyglet.shapes.Rectangle(
            0, 0, window.width, 80, color=(9, 16, 29, 235),
            batch=self.batch, group=self.background,
        )
        self.bottom = pyglet.shapes.Rectangle(
            0, 0, window.width, 50, color=(9, 16, 29, 235),
            batch=self.batch, group=self.background,
        )
        self.title = self.label("SPACE INVADERS", 19, (118, 218, 255, 255))
        self.subtitle = self.label("CC3501  /  TAREA 02", 10, (146, 162, 186, 255))
        self.status = self.label("", 12, (234, 241, 250, 255), anchor_x="right")
        self.camera = self.label("", 10, (146, 162, 186, 255), anchor_x="right")
        self.controls = self.label("A / D o flechas: mover    ESPACIO: disparar    C: cámara", 11)
        self.extras = self.label("P: pausa    F: foco    R: reiniciar    ESC: salir", 10,
                                 (146, 162, 186, 255))
        self.message = pyglet.text.Label(
            "", font_name="Arial", font_size=28, weight="bold",
            anchor_x="center", anchor_y="center", color=(234, 241, 250, 255),
        )
        self.hint = pyglet.text.Label(
            "", font_name="Arial", font_size=13,
            anchor_x="center", anchor_y="center", color=(161, 210, 232, 255),
        )
        self.overlay = pyglet.shapes.Rectangle(0, 0, window.width, window.height,
                                                color=(4, 9, 19, 205))

    def label(self, text, size, color=(234, 241, 250, 255), **kwargs):
        return pyglet.text.Label(text, font_name="Arial", font_size=size,
                                 color=color, batch=self.batch,
                                 group=self.foreground, **kwargs)

    def draw(self):
        w, h = self.window.width, self.window.height
        c = self.window
        self.top.width, self.top.y = w, h - 80
        self.bottom.width = w
        self.title.position = (22, h - 34, 0)
        self.subtitle.position = (23, h - 57, 0)
        self.status.position = (w - 22, h - 32, 0)
        self.camera.position = (w - 22, h - 56, 0)
        alive = sum(e["alive"] for e in c.enemies)
        self.status.text = f"PUNTOS {c.score:04d}    ENEMIGOS {alive:02d}/{ENEMY_ROWS * ENEMY_COLUMNS}"
        view = "NAVE" if c.camera_mode == 1 else "CENITAL"
        self.camera.text = f"VISTA {view}    |    FOCO {'ON' if c.spotlight_on else 'OFF'}"
        self.controls.position = (22, 30, 0)
        self.extras.position = (22, 11, 0)
        self.batch.draw()
        if c.paused or c.game_state != "playing":
            self.overlay.width, self.overlay.height = w, h - 130
            self.overlay.y = 50
            self.overlay.draw()
            if c.game_state == "won":
                self.message.text = "SECTOR DESPEJADO"
                self.hint.text = "Destruiste todos los enemigos. Pulsa R para jugar otra vez."
            elif c.game_state == "lost":
                self.message.text = "INVASIÓN COMPLETADA"
                self.hint.text = "Los enemigos alcanzaron tu nave. Pulsa R para reintentar."
            else:
                self.message.text = "PAUSA"
                self.hint.text = "Pulsa P para continuar."
            self.message.position = (w / 2, h / 2 + 18, 0)
            self.hint.position = (w / 2, h / 2 - 24, 0)
            self.message.draw()
            self.hint.draw()


def add_arena(world, controller):

    white_texture = Texture()

    def box(name, position, scale, color):
        mesh = Model(shapes.Cube["position"], shapes.Cube["uv"],
                     normal_data=shapes.Cube["normal"], index_data=shapes.Cube["indices"])
        world.add_node(name, mesh=mesh, texture=white_texture,
                       pipeline=controller.pipeline, position=position,
                       scale=scale, color=color)

    box("floor", [0, -0.08, -1], [22, 0.1, 28], [0.055, 0.08, 0.13])
    for x in range(-10, 11, 2):
        box(f"grid_x_{x}", [x, -0.018, -1], [0.018, 0.01, 28], [0.12, 0.19, 0.28])
    for z in range(-14, 13, 2):
        box(f"grid_z_{z}", [0, -0.018, z], [22, 0.01, 0.018], [0.12, 0.19, 0.28])
    for x in (-10, 10):
        box(f"border_{x}", [x, 0, -1], [0.06, 0.02, 28], [0.16, 0.40, 0.60])
    box("ship_lane", [0, 0, 10], [13, 0.02, 0.06], [0.16, 0.65, 0.74])


def create_game(visible=True):
    controller = Controller(1000, 750, "Space Invaders | CC3501 - Tarea 2",
                            resizable=True, visible=visible, vsync=True)
    controller.set_minimum_size(800, 600)
    init_controller(controller)
    ship_camera = MyCam(np.array([0, 6.2, 17.0]))
    ship_camera.pitch = -0.43
    top_camera = TopCamera()
    ship_camera.resize(controller.width, controller.height)
    top_camera.resize(controller.width, controller.height)
    ship_mesh = atlas_cube(SHIP_TILE, controller.atlas)
    bullet_mesh = atlas_cube(BULLET_TILE, controller.atlas)
    world = SceneGraph(ship_camera)
    world.add_node("ship", mesh=ship_mesh, texture=controller.atlas,
                   pipeline=controller.pipeline, position=SHIP_START,
                   scale=[1.0, 0.8, 1.0])
    add_arena(world, controller)
    init_enemies(world, controller)


    @controller.event
    def on_key_press(symbol, modifiers):
        if symbol == key.A or symbol == key.LEFT:
            controller.left = True

        if symbol == key.D or symbol == key.RIGHT:
            controller.right = True

        if symbol == key.SPACE:
            shoot(world["ship"]["position"], world, bullet_mesh, controller)

        if symbol == key.C:
            if controller.camera_mode == 0:
                world.camera = ship_camera
                controller.camera_mode = 1
            else:
                world.camera = top_camera
                controller.camera_mode = 0

    @controller.event
    def on_key_release(symbol, modifiers):
        if symbol == key.A or symbol == key.LEFT:
            controller.left = False

        if symbol == key.D or symbol == key.RIGHT:
            controller.right = False


    def on_extra_key_press(symbol, modifiers):
        if symbol == key.P and controller.game_state == "playing":
            controller.paused = not controller.paused
            controller.left = controller.right = False
            controller.accumulator = 0.0
        elif symbol == key.F:
            controller.spotlight_on = not controller.spotlight_on
        elif symbol == key.R:
            reset_game(world, controller)
        elif symbol == key.ESCAPE:
            controller.close()

    controller.push_handlers(on_key_press=on_extra_key_press)

    @controller.event
    def on_resize(width, height):
        ship_camera.resize(width, max(1, height))
        top_camera.resize(width, max(1, height))


    @controller.event
    def on_deactivate():

        controller.left = controller.right = False

    hud = HUD(controller)

    def update(dt):
        if is_playing(controller):


            controller.accumulator += min(max(0.0, dt), 0.25)
            while controller.accumulator + 1e-10 >= FIXED_DT and is_playing(controller):
                controller.dt = FIXED_DT
                controller.time += FIXED_DT
                update_ship(world, controller)
                update_enemies(world, controller)
                update_bullets(world, controller)
                update_game_state(world, controller)
                controller.accumulator -= FIXED_DT
        else:
            controller.accumulator = 0.0
        update_camera(ship_camera, dt, world)
        world.update()

    @controller.event
    def on_draw():
        glClearColor(0.018, 0.028, 0.05, 1.0)
        controller.clear()


        world.update()
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        controller.pipeline.use()
        controller.pipeline["u_shipPos"] = tuple(float(v) for v in world["ship"]["position"])
        controller.pipeline["u_spotlightOn"] = controller.spotlight_on
        world.draw()
        glDisable(GL_DEPTH_TEST)
        hud.draw()


    controller.world = world
    controller.ship_camera = ship_camera
    controller.top_camera = top_camera
    controller.bullet_mesh = bullet_mesh
    controller.update_game = update
    controller.hud = hud
    update(0.0)
    return controller


if __name__ == "__main__":
    game = create_game()
    clock.schedule_interval(game.update_game, 1 / 60)
    run()
