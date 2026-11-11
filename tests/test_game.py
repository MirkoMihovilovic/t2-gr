import unittest

import numpy as np
import pyglet
from pyglet.window import key

from invaders import (BULLET_END, ENEMY_ADVANCE, ENEMY_LIMIT, SHIP_START,
                      remove_object, reset_game, shoot, update_bullets,
                      update_enemies, update_game_state)
from tarea2 import create_game


class GameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = create_game(visible=False)
        cls.game.switch_to()
        cls.game.dispatch_events()

    @classmethod
    def tearDownClass(cls):
        cls.game.close()

    def setUp(self):
        self.g = self.game
        self.w = self.g.world
        reset_game(self.w, self.g)
        self.g.spotlight_on = True
        self.g.camera_mode = 1
        self.w.camera = self.g.ship_camera
        self.g.update_game(0)

    def press(self, symbol):
        self.g.dispatch_event("on_key_press", symbol, 0)
        self.g.dispatch_events()

    def release(self, symbol):
        self.g.dispatch_event("on_key_release", symbol, 0)
        self.g.dispatch_events()

    def advance(self, seconds, fps=60):
        for _ in range(round(seconds * fps)):
            self.g.update_game(1 / fps)

    def fire(self):
        shoot(self.w["ship"]["position"], self.w, self.g.bullet_mesh, self.g)

    def test_four_rows_with_distinct_textures(self):
        self.assertEqual(len(self.g.enemies), 32)
        uvs = set()
        for row in range(4):
            members = [e for e in self.g.enemies if e["row"] == row]
            self.assertEqual(len(members), 8)
            self.assertEqual(len({float(e["position"][2]) for e in members}), 1)
            uvs.add(tuple(self.w[members[0]["name"]]["mesh"].uv_data))
        self.assertEqual(len(uvs), 4)

    def test_ship_controls_and_limits(self):
        self.press(key.D)
        self.advance(2)
        self.release(key.D)
        np.testing.assert_allclose(self.w["ship"]["position"], [6, 0.6, 10])
        self.press(key.LEFT)
        self.advance(3)
        self.release(key.LEFT)
        np.testing.assert_allclose(self.w["ship"]["position"], [-6, 0.6, 10])
        before = self.w["ship"]["position"].copy()
        self.advance(0.5)
        np.testing.assert_allclose(self.w["ship"]["position"], before)

    def test_movement_is_independent_of_frame_rate(self):
        positions = []
        for fps in (30, 60, 144):
            reset_game(self.w, self.g)
            self.g.right = True
            self.advance(0.5, fps)
            positions.append((self.w["ship"]["position"].copy(),
                              self.g.enemies[0]["position"].copy()))
        np.testing.assert_allclose(positions[0], positions[1], atol=1e-5)
        np.testing.assert_allclose(positions[0], positions[2], atol=1e-5)

    def test_formation_bounces_at_both_limits(self):
        for direction in (1, -1):
            self.g.direction = direction
            xs = [e["position"][0] for e in self.g.enemies]
            offset = 9.99 - max(xs) if direction == 1 else -9.99 - min(xs)
            previous_z = [e["position"][2] for e in self.g.enemies]
            for enemy in self.g.enemies:
                enemy["position"][0] += offset
            self.g.dt = 0.1
            update_enemies(self.w, self.g)
            self.assertEqual(self.g.direction, -direction)
            self.assertTrue(all(abs(e["position"][0]) <= ENEMY_LIMIT + 1e-5
                                for e in self.g.enemies))
            np.testing.assert_allclose([e["position"][2] for e in self.g.enemies],
                                       np.array(previous_z) + ENEMY_ADVANCE)

    def test_dead_enemies_do_not_trigger_bounces(self):
        enemy = self.g.enemies[0]
        remove_object(self.w, enemy)
        enemy["position"][0] = 20
        self.g.dt = 0.1
        update_enemies(self.w, self.g)
        self.assertEqual(self.g.direction, 1)

    def test_space_creates_bullet_at_ship_with_independent_position(self):
        self.press(key.SPACE)
        self.assertEqual(len(self.g.bullets), 1)
        bullet = self.g.bullets[0]
        np.testing.assert_allclose(bullet["position"], SHIP_START)
        self.w["ship"]["position"][0] = 4
        self.assertEqual(bullet["position"][0], 0)
        self.assertIn(bullet["name"], self.w)

    def test_swept_collision_hits_only_the_nearest_enemy(self):
        near, far = self.g.enemies[:2]
        near["position"] = np.array([0, 0.6, 6], dtype=np.float32)
        far["position"] = np.array([0, 0.6, 3], dtype=np.float32)
        self.fire()
        self.g.dt = 0.6
        update_bullets(self.w, self.g)
        self.assertFalse(near["alive"])
        self.assertTrue(far["alive"])
        self.assertNotIn(near["name"], self.w)
        self.assertEqual(self.g.score, 100)
        self.assertEqual(self.g.bullets, [])

    def test_simultaneous_bullets_do_not_score_twice(self):
        enemy = self.g.enemies[0]
        enemy["position"] = np.array([0, 0.6, 9], dtype=np.float32)
        self.fire()
        self.fire()
        self.g.dt = 0.1
        update_bullets(self.w, self.g)
        self.assertEqual(self.g.score, 100)
        self.assertEqual(len(self.g.bullets), 1)

    def test_all_out_of_bounds_bullets_are_removed(self):
        for _ in range(3):
            self.fire()
            self.g.bullets[-1]["position"][2] = BULLET_END - 1
        names = [b["name"] for b in self.g.bullets]
        self.g.dt = 0.1
        update_bullets(self.w, self.g)
        self.assertEqual(self.g.bullets, [])
        self.assertTrue(all(name not in self.w for name in names))

    def test_pause_stops_everything_including_shooting(self):
        self.fire()
        ship = self.w["ship"]["position"].copy()
        enemies = [e["position"].copy() for e in self.g.enemies]
        bullet = self.g.bullets[0]["position"].copy()
        self.press(key.P)
        self.press(key.D)
        self.press(key.SPACE)
        self.advance(2)
        self.assertTrue(self.g.paused)
        self.assertEqual(len(self.g.bullets), 1)
        np.testing.assert_allclose(self.w["ship"]["position"], ship)
        np.testing.assert_allclose([e["position"] for e in self.g.enemies], enemies)
        np.testing.assert_allclose(self.g.bullets[0]["position"], bullet)
        self.press(key.P)
        self.advance(0.1)
        self.assertFalse(self.g.paused)
        self.assertLess(self.g.bullets[0]["position"][2], bullet[2])

    def test_cameras_switch_and_top_camera_stays_fixed(self):
        top_position = self.g.top_camera.position.copy()
        self.press(key.C)
        self.assertIs(self.w.camera, self.g.top_camera)
        self.press(key.D)
        self.advance(0.5)
        self.release(key.D)
        np.testing.assert_allclose(self.g.top_camera.position, top_position)
        self.assertAlmostEqual(self.g.ship_camera.position[0], self.w["ship"]["position"][0])
        self.press(key.C)
        self.assertIs(self.w.camera, self.g.ship_camera)
        self.assertTrue(np.isfinite(self.g.top_camera.get_view()).all())

    def test_victory_and_defeat_stop_the_game(self):
        for enemy in self.g.enemies:
            remove_object(self.w, enemy)
        update_game_state(self.w, self.g)
        self.assertEqual(self.g.game_state, "won")
        self.fire()
        self.assertEqual(self.g.bullets, [])
        reset_game(self.w, self.g)
        self.g.enemies[0]["position"][2] = 9.2
        self.advance(0.1)
        self.assertEqual(self.g.game_state, "lost")
        before = self.g.enemies[0]["position"].copy()
        self.advance(1)
        np.testing.assert_allclose(self.g.enemies[0]["position"], before)

    def test_restart_restores_clean_scene(self):
        initial_nodes = len(self.w.graph.nodes)
        self.fire()
        remove_object(self.w, self.g.enemies[0])
        self.g.score = 100
        self.g.paused = True
        self.press(key.R)
        self.assertEqual(len(self.w.graph.nodes), initial_nodes)
        self.assertEqual(len(self.g.enemies), 32)
        self.assertEqual(self.g.bullets, [])
        self.assertEqual(self.g.score, 0)
        self.assertFalse(self.g.paused)
        self.assertEqual(self.g.game_state, "playing")
        np.testing.assert_allclose(self.w["ship"]["position"], SHIP_START)

    def test_shoot_and_restart_can_render_before_next_update(self):
        self.press(key.SPACE)
        self.g.dispatch_event("on_draw")
        self.g.dispatch_events()
        self.assertIn(self.g.bullets[0]["name"], self.w.transformations)
        self.press(key.R)
        self.g.dispatch_event("on_draw")
        self.g.dispatch_events()
        self.assertEqual(self.g.bullets, [])

    def test_rendered_spotlight_changes_scene_brightness(self):
        def pixels():
            self.g.dispatch_event("on_draw")
            self.g.dispatch_events()
            data = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
            return np.frombuffer(data.get_bytes("RGBA", data.width * 4), dtype=np.uint8).reshape(
                data.height, data.width, 4
            )[80:-80, :, :3].astype(float)

        lit = pixels()
        self.press(key.F)
        self.assertFalse(self.g.spotlight_on)
        unlit = pixels()
        self.assertGreater(lit.sum(), unlit.sum() * 1.05)
        self.press(key.F)
        self.assertTrue(self.g.spotlight_on)
        self.press(key.C)
        self.assertGreater(pixels().std(), 1)


if __name__ == "__main__":
    unittest.main()
