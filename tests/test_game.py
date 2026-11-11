import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import Grandslam2026 as g


class GameTests(unittest.TestCase):
    def test_swing_3d_geometry_and_recovery(self):
        projected_lengths = []
        for frame in range(201):
            hands, tip, _, arms = g.batter_skeleton(frame / 200)
            self.assertAlmostEqual(hands.distance_to(tip), 178)
            for shoulder, elbow, grip in arms:
                self.assertAlmostEqual(shoulder.distance_to(elbow), g.BATTER_ARM_LENGTH)
                self.assertAlmostEqual(elbow.distance_to(grip), g.BATTER_ARM_LENGTH)
                self.assertEqual(grip, hands)
            projected_lengths.append(g.project_batter(hands).distance_to(
                g.project_batter(tip)))
        self.assertGreater(max(projected_lengths) - min(projected_lengths), 40)
        for start, end in zip(g.batter_pose(0)[:2], g.batter_pose(1)[:2]):
            self.assertLess(start.distance_to(end), 1e-7)
        ready = g.batter_skeleton(0)[0]
        loaded = g.batter_skeleton(.20)[0]
        contact = g.batter_skeleton(.43)[0]
        self.assertLess(loaded.x, ready.x)
        self.assertGreater(loaded.z, ready.z)
        self.assertGreater(contact.x, loaded.x)
        self.assertLess(contact.z, loaded.z)

    def test_upper_swing_extends_and_finishes_behind(self):
        for progress in (.43, .50, .59, .66, .73):
            hands, tip, _, arms = g.batter_skeleton(progress)
            for shoulder, elbow, grip in arms:
                self.assertGreater(shoulder.distance_to(grip), 2 * g.BATTER_ARM_LENGTH - 3)
        low_hands, low_tip, _, _ = g.batter_skeleton(.43)
        high_hands, high_tip, _, _ = g.batter_skeleton(.73)
        self.assertLess(high_hands.y, low_hands.y - 90)
        for hands, tip, angle_min, angle_max in (
                (low_hands, low_tip, 30, 60),
                (high_hands, high_tip, -150, -120)):
            delta = g.project_batter(tip) - g.project_batter(hands)
            angle = g.math.degrees(g.math.atan2(delta.y * 1.27, delta.x * 1.03))
            self.assertGreater(angle, angle_min)
            self.assertLess(angle, angle_max)
        hands, tip, _, _ = g.batter_skeleton(.73)
        self.assertGreater(hands.z, 0)
        self.assertGreater(tip.z, hands.z)
        # XZ 평면의 회전 부호가 이전 스윙과 반대여야 한다.
        for frame in range(21, 72):
            h0, t0, _, _ = g.batter_skeleton(frame / 100)
            h1, t1, _, _ = g.batter_skeleton((frame + 1) / 100)
            a, b = t0 - h0, t1 - h1
            self.assertLess(a.x * b.z - a.z * b.x, 0)

    def test_preparation_flows_into_swing(self):
        g.game_state = 'WINDUP'
        g.windup_start = 1000
        g.swing_started = None
        self.assertEqual(g.batter_preparation(1000), (0., 0., 0.))
        self.assertAlmostEqual(g.batter_preparation(1700)[1], .5)
        ready_hands, ready_tip, _, _ = g.batter_skeleton(0)
        loaded_hands, loaded_tip, _, _ = g.batter_skeleton(0, 1)
        self.assertLess(loaded_hands.y, ready_hands.y - 30)
        self.assertLess(loaded_tip.y, ready_tip.y - 30)
        g.game_state = 'PITCHING'
        before = g.batter_preparation(2500)
        g.swing_started = 2500
        self.assertEqual(before, g.batter_preparation(2500))
        _, lift, stride = g.batter_preparation(2500 + .43 * g.SWING_DURATION)
        self.assertEqual(lift, 0)
        self.assertEqual(stride, 1)
        self.assertEqual(g.batter_preparation(2500 + g.SWING_DURATION), (.88, 0., 1.))

    def test_feet_and_head_face_field_targets(self):
        step, axis, yaw = g.batter_field_turn(1)
        target = g.pygame.Vector2(g.defender_positions()['SS'][:2])
        projected = g.pygame.Vector2(step.x * 1.03, step.y * 1.27)
        self.assertAlmostEqual(projected.normalize().dot(
            (target - (360, 820)).normalize()), 1)
        self.assertAlmostEqual(axis.dot(step.normalize()), 1)
        gaze = g.pygame.Vector2(g.math.sin(yaw), -g.math.cos(yaw))
        self.assertAlmostEqual(gaze.dot((g.pygame.Vector2(
            g.defender_positions()['SS'][:2]) - (360, 820)).normalize()), 1)
        self.assertEqual(g.batter_field_turn(0)[0], g.pygame.Vector2())

    def test_opposite_leg_steps_and_support_leg_pivots(self):
        far_ready = g.batter_leg_pose(False, 0, 0)
        far_loaded = g.batter_leg_pose(False, 1, 0)
        far_finish = g.batter_leg_pose(False, 0, 1)
        self.assertLess(far_loaded[2].y, far_ready[2].y)
        self.assertAlmostEqual(far_finish[2].distance_to(far_ready[2]), 36)
        near_ready = g.batter_leg_pose(True, 0, 0)
        near_finish = g.batter_leg_pose(True, 0, 1)
        self.assertEqual(near_ready[2], near_finish[2])
        self.assertLess(near_finish[1].distance_to(near_finish[0].lerp(near_finish[2], .5)),
                        near_ready[1].distance_to(near_ready[0].lerp(near_ready[2], .5)))
        self.assertLess(near_finish[3].y, 0)

    def test_shoes_rotate_on_ground_without_tipping(self):
        initial = g.batter_shoe_mesh(g.pygame.Vector2(1, 0))
        for frame in range(101):
            stride = frame / 100
            for near in (False, True):
                axis = g.batter_leg_pose(near, 0, stride)[3]
                vertices = g.batter_shoe_mesh(axis)
                for start, rotated in zip(initial, vertices):
                    self.assertAlmostEqual(start.y, rotated.y)
                    self.assertAlmostEqual(start.length(), rotated.length())
                for index in range(8):
                    self.assertEqual(vertices[index].y, 0)
                    self.assertEqual(vertices[index + 8].y, 3)
                self.assertAlmostEqual(vertices[0].distance_to(vertices[4]),
                                       initial[0].distance_to(initial[4]))

    def test_stepping_knee_straightens_and_turns_on_landing(self):
        hip, knee, ankle, axis = g.batter_leg_pose(False, 0, 1)
        bend = knee - hip.lerp(ankle, .5)
        self.assertAlmostEqual(bend.length(), 5)
        self.assertAlmostEqual(bend.normalize().dot(axis), 1)
        ready_hip, ready_knee, ready_ankle, _ = g.batter_leg_pose(False, 0, 0)
        self.assertLess(bend.length(), ready_knee.distance_to(
            ready_hip.lerp(ready_ankle, .5)))

    def test_fielders_stay_fixed_for_all_runner_combinations(self):
        g.base1 = g.base2 = g.base3 = False
        positions = g.defender_positions()
        for occupied in range(8):
            g.base1 = bool(occupied & 1)
            g.base2 = bool(occupied & 2)
            g.base3 = bool(occupied & 4)
            self.assertEqual(g.defender_positions(), positions)

    def test_loading_coils_arms_and_bat_back_together(self):
        ready_hands, ready_tip, _, ready_arms = g.batter_skeleton(0, 0)
        for frame in range(1, 101):
            load = frame / 100
            hands, tip, _, arms = g.batter_skeleton(0, load)
            self.assertAlmostEqual(hands.distance_to(tip), 178)
            for shoulder, elbow, grip in arms:
                self.assertAlmostEqual(shoulder.distance_to(elbow), g.BATTER_ARM_LENGTH)
                self.assertAlmostEqual(elbow.distance_to(grip), g.BATTER_ARM_LENGTH)
            ready_axis = ready_tip - ready_hands
            loaded_axis = tip - hands
            self.assertLess(ready_axis.x * loaded_axis.z - ready_axis.z * loaded_axis.x, 0)
        self.assertLess(hands.z - ready_hands.z, -50)
        self.assertLess(hands.x, ready_hands.x)
        projected_shoulders = [g.project_batter(arm[0]).x for arm in arms]
        self.assertGreaterEqual(g.project_batter(hands).x, min(projected_shoulders))
        self.assertLessEqual(g.project_batter(hands).x, max(projected_shoulders))
        self.assertGreater(abs(arms[1][0].x - arms[0][0].x),
                           abs(ready_arms[1][0].x - ready_arms[0][0].x))

    def test_step_lands_before_upper_body_swing(self):
        g.windup_start = 0
        g.swing_started = 1500
        g.game_state = 'PITCHING'
        for fraction in (.04, .08, .12, .16, .18):
            progress, coil, stride = g.batter_preparation(1500 + fraction * g.SWING_DURATION)
            self.assertEqual(progress, 0)
            self.assertEqual(coil, 1)
            self.assertGreater(stride, 0)
        progress, coil, stride = g.batter_preparation(1500 + .18 * g.SWING_DURATION)
        self.assertEqual(stride, 1)
        self.assertEqual(g.batter_leg_pose(False, coil * (1 - stride), stride)[2],
                         g.batter_leg_pose(False, 0, 1)[2])
        progress, coil, stride = g.batter_preparation(1500 + .25 * g.SWING_DURATION)
        self.assertGreater(progress, 0)
        self.assertLess(coil, 1)
        self.assertEqual(stride, 1)

    def test_high_pitch_uses_level_start_and_high_finish(self):
        boundary = g.strike_zone.top + g.strike_zone.height / 3
        for height in (g.strike_zone.top - 80, g.strike_zone.top, boundary):
            self.assertTrue(g.uses_high_pitch_swing(height))
        self.assertFalse(g.uses_high_pitch_swing(boundary + 1))
        self.assertFalse(g.uses_high_pitch_swing(g.strike_zone.centery))
        hands, tip, _, _ = g.batter_skeleton(.43, high_pitch=True)
        self.assertAlmostEqual(hands.y, tip.y)
        self.assertGreater(tip.x, hands.x)
        high_hands, high_tip, _, _ = g.batter_skeleton(.73, high_pitch=True)
        delta = g.project_batter(high_tip) - g.project_batter(high_hands)
        angle = g.math.degrees(g.math.atan2(delta.y * 1.27, delta.x * 1.03))
        self.assertGreater(angle, -150)
        self.assertLess(angle, -120)
        low_hands, low_tip, _, _ = g.batter_skeleton(.43)
        self.assertGreater(low_tip.y, low_hands.y)
        for frame in range(101):
            h, t, _, arms = g.batter_skeleton(frame / 100, high_pitch=True)
            self.assertAlmostEqual(h.distance_to(t), 178)
            for shoulder, elbow, grip in arms:
                self.assertAlmostEqual(shoulder.distance_to(elbow), g.BATTER_ARM_LENGTH)
                self.assertAlmostEqual(elbow.distance_to(grip), g.BATTER_ARM_LENGTH)

    def test_follow_through_wraps_in_front_of_body(self):
        for high in (False, True):
            h0, t0, _, _ = g.batter_skeleton(.73, high_pitch=high)
            hands, tip, _, arms = g.batter_skeleton(.84, high_pitch=high)
            self.assertLess(hands.z, -75)
            self.assertLess(tip.z, hands.z - 80)
            self.assertGreater(abs(tip.x - hands.x), 110)
            for shoulder, elbow, grip in arms:
                self.assertLess(shoulder.distance_to(grip), 150)
                self.assertAlmostEqual(shoulder.distance_to(elbow), g.BATTER_ARM_LENGTH)
                self.assertAlmostEqual(elbow.distance_to(grip), g.BATTER_ARM_LENGTH)

    def test_finish_holds_until_next_windup(self):
        g.windup_start = 0
        g.swing_started = 1500
        for state in ('PITCHING', 'BATTED', 'RESULT', 'READY'):
            g.game_state = state
            self.assertEqual(g.batter_preparation(5000), (.88, 0., 1.))
        with patch.object(g.pygame.time, 'get_ticks', return_value=5000):
            g.start_windup()
        self.assertEqual(g.batter_preparation(5000), (.88, 0., 1.))
        progress, load, stride = g.batter_preparation(5175)
        self.assertGreater(progress, .88)
        self.assertLess(stride, 1)
        self.assertEqual(g.batter_preparation(5350), (0., 0., 0.))
        self.assertEqual(g.batter_preparation(6400), (0., 1., 0.))

    def test_bat_remains_visible_in_held_finish(self):
        g.game_state = 'RESULT'
        g.windup_start = 0
        g.swing_started = 1500
        for target_y in (g.strike_zone.top, g.strike_zone.bottom):
            g.ball_target_y = target_y
            g.screen.fill((0, 0, 0))
            with patch.object(g.pygame.time, 'get_ticks', return_value=4000):
                g.draw_foreground_batter()
            pixels = g.pygame.PixelArray(g.screen)
            barrel = g.screen.map_rgb((219, 165, 96))
            visible = sum(pixels[x, y] == barrel for x in range(1280)
                          for y in range(900))
            del pixels
            self.assertGreater(visible, 200)

    def setUp(self):
        g.new_game()
        g.pitch_speed = 1.0

    def test_probability_table_and_corners(self):
        z = g.strike_zone
        for kind in ('FASTBALL', 'CURVE', 'SLIDER'):
            fast = kind == 'FASTBALL'
            self.assertEqual(g.ai_batting_probabilities(kind, z.center),
                             (.7, .5, .5) if fast else (.45, .7, .6))
            for target in ((z.left - 1, z.centery), (z.right, z.centery)):
                self.assertEqual(g.ai_batting_probabilities(kind, target),
                                 (.4, .3, .4) if fast else (.7, .1, .7))
            self.assertEqual(g.ai_batting_probabilities(kind, (z.left - 1, z.bottom)),
                             (.1, 0, 0) if fast else (.7, .1, .7))
            self.assertEqual(g.ai_batting_probabilities(kind, (z.right, z.top - 1)),
                             (.4, .3, .4) if fast else (.1, 0, 0))

    def test_conditional_hit_and_foul(self):
        target = g.strike_zone.center
        for rolls, expected in [([.8], 'TAKE'), ([.1, .6], 'MISS'),
                                ([.1, .1, .6, .1], 'FOUL')]:
            with patch.object(g.random, 'random', side_effect=rolls):
                self.assertEqual(g.choose_ai_result('FASTBALL', target), expected)
        with patch.object(g.random, 'random', side_effect=[.1, .1, .49]), \
             patch.object(g.random, 'choices', return_value=['DOUBLE']) as choices:
            self.assertEqual(g.choose_ai_result('FASTBALL', target), 'DOUBLE')
            self.assertEqual(choices.call_args.kwargs['weights'], (65, 22, 3, 10))
        with patch.object(g.random, 'random', side_effect=[.1, .1, .5, .9]), \
             patch.object(g.random, 'choice', return_value='GROUND'):
            self.assertEqual(g.choose_ai_result('FASTBALL', target), 'GROUND')

    def test_six_half_innings_and_reset(self):
        for inning in range(1, 4):
            for half in ('TOP', 'BOTTOM'):
                self.assertEqual((g.inning, g.half), (inning, half))
                g.base1 = g.base2 = g.base3 = True
                g.balls, g.strikes = 3, 2
                g.add_outs(3)
                self.assertTrue(g.half_pending)
                g.prepare_next_half()
                if (inning, half) != (3, 'BOTTOM'):
                    self.assertEqual((g.outs, g.balls, g.strikes), (0, 0, 0))
                    self.assertFalse(g.base1 or g.base2 or g.base3)
                    self.assertNotEqual(g.game_state, 'GAME_OVER')
        self.assertEqual(g.game_state, 'GAME_OVER')

    def test_scoring_walk_and_sacrifice(self):
        g.base1 = g.base2 = g.base3 = True
        g.walk_batter()
        self.assertEqual((g.score, g.ai_score), (0, 1))
        g.hit_homerun()
        self.assertEqual((g.score, g.ai_score), (0, 5))
        g.add_outs(3)
        g.prepare_next_half()
        g.hit_homerun()
        self.assertEqual((g.score, g.ai_score), (1, 5))
        g.base3 = True
        with patch.object(g.random, 'random', return_value=0):
            g.fly_out()
        self.assertEqual(g.score, 2)
        g.outs, g.base3 = 2, True
        g.fly_out()
        self.assertEqual(g.score, 2)

    def test_fouls_preserve_runners_and_balls(self):
        for half in ('TOP', 'BOTTOM'):
            g.half = half
            g.balls, g.strikes, g.outs, g.base1 = 3, 0, 1, True
            for expected in (1, 2, 2, 2):
                g.apply_batting_result('FOUL')
                self.assertEqual((g.balls, g.strikes, g.outs, g.base1), (3, expected, 1, True))

    def test_locked_pitch_and_ai_resolution(self):
        for kind in ('FASTBALL', 'CURVE', 'SLIDER'):
            g.selected_pitch, g.pitch_aim = kind, (590, 555)
            g.start_windup()
            g.selected_pitch, g.pitch_aim = 'FASTBALL', (400, 730)
            g.start_pitch()
            self.assertEqual((g.pitch_type, g.ball_target_x, g.ball_target_y), (kind, 590, 555))
            self.assertEqual(g.pitch_pose(1)[:2], (590., 555.))
            with patch.object(g, 'choose_ai_result', return_value='MISS'):
                g.finish_pitch()
        self.assertEqual(g.outs, 1)
        g.start_windup()
        g.start_pitch()
        with patch.object(g, 'choose_ai_result', return_value='HOMERUN'):
            g.finish_pitch()
        self.assertEqual(g.game_state, 'BATTED')
        g.apply_batting_result(g.batted_play['result'])
        self.assertEqual(g.ai_score, 1)

    def test_player_swing_ignored_on_defense(self):
        g.game_state, g.swung = 'PITCHING', False
        g.swing_bat()
        self.assertFalse(g.swung)

    def test_swing_connects_only_when_ball_reaches_plate(self):
        g.new_game('PVP')
        g.locked_aim, g.locked_pitch = g.strike_zone.center, 'FASTBALL'
        g.start_pitch()
        g.pitch_start = 1000
        with patch.object(g.pygame.time, 'get_ticks', return_value=1620), \
             patch.object(g.pygame.mouse, 'get_pos', return_value=g.strike_zone.center):
            g.swing_bat()
        self.assertEqual(g.game_state, 'PITCHING')
        self.assertEqual(g.pending_swing_result, 'MISS')
        with patch.object(g.pygame.time, 'get_ticks', return_value=1816), \
             patch.object(g, 'choose_batting_result', return_value='SINGLE'):
            g.update_pitch()
        self.assertEqual(g.game_state, 'PITCHING')
        with patch.object(g.pygame.time, 'get_ticks', return_value=1850), \
             patch.object(g.pygame.mouse, 'get_pos', return_value=(0, 0)), \
             patch.object(g, 'choose_batting_result', return_value='SINGLE'):
            g.update_pitch()
        self.assertEqual(g.game_state, 'BATTED')
        self.assertEqual(g.batted_play['result'], 'SINGLE')
        self.assertEqual(g.batted_play['contact'], g.strike_zone.center)

    def test_ball_crossing_aim_in_midair_does_not_connect(self):
        g.new_game('PVP')
        g.locked_aim, g.locked_pitch = g.strike_zone.center, 'FASTBALL'
        g.start_pitch()
        g.pitch_start = 1000
        x, y, _ = g.pitch_pose(.9)
        with patch.object(g.pygame.time, 'get_ticks', return_value=1680), \
             patch.object(g.pygame.mouse, 'get_pos',
                          return_value=(round(x), round(y))):
            g.swing_bat()
        with patch.object(g.pygame.time, 'get_ticks', return_value=1765):
            g.update_pitch()
        self.assertEqual(g.game_state, 'PITCHING')
        with patch.object(g.pygame.time, 'get_ticks', return_value=1850):
            g.update_pitch()
        self.assertEqual(g.game_state, 'PITCHING')
        with patch.object(g.pygame.time, 'get_ticks', return_value=2070):
            g.update_pitch()
        self.assertEqual((g.game_state, g.strikes), ('RESULT', 1))

    def test_swing_after_arrival_during_contact_window(self):
        g.new_game('PVP')
        g.locked_aim, g.locked_pitch = g.strike_zone.center, 'FASTBALL'
        g.start_pitch()
        g.pitch_start = 1000
        with patch.object(g.pygame.time, 'get_ticks', return_value=1850):
            g.update_pitch()
        self.assertEqual(g.game_state, 'PITCHING')
        with patch.object(g.pygame.time, 'get_ticks', return_value=1950), \
             patch.object(g.pygame.mouse, 'get_pos', return_value=g.strike_zone.center), \
             patch.object(g, 'choose_batting_result', return_value='SINGLE'):
            g.swing_bat()
        self.assertEqual(g.game_state, 'BATTED')

    def test_early_swing_expires_before_ball_arrives(self):
        g.new_game('PVP')
        g.locked_aim, g.locked_pitch = g.strike_zone.center, 'FASTBALL'
        g.start_pitch()
        g.pitch_start = 1000
        with patch.object(g.pygame.time, 'get_ticks', return_value=1170), \
             patch.object(g.pygame.mouse, 'get_pos', return_value=g.strike_zone.center):
            g.swing_bat()
        with patch.object(g.pygame.time, 'get_ticks', return_value=1850):
            g.update_pitch()
        self.assertEqual(g.game_state, 'PITCHING')
        with patch.object(g.pygame.time, 'get_ticks', return_value=2070):
            g.update_pitch()
        self.assertEqual(g.game_state, 'RESULT')
        self.assertEqual(g.strikes, 1)

    def test_fast_pitch_contact_between_frames(self):
        g.new_game('PVP')
        g.pitch_speed = 2.0
        g.locked_aim, g.locked_pitch = g.strike_zone.center, 'FASTBALL'
        g.start_pitch()
        g.pitch_start = 1000
        with patch.object(g.pygame.time, 'get_ticks', return_value=1319), \
             patch.object(g.pygame.mouse, 'get_pos',
                          return_value=g.strike_zone.center):
            g.swing_bat()
        with patch.object(g.pygame.time, 'get_ticks', return_value=1425), \
             patch.object(g, 'choose_batting_result', return_value='DOUBLE'):
            g.update_pitch()
        self.assertEqual(g.game_state, 'BATTED')
        self.assertEqual(g.batted_play['result'], 'DOUBLE')

    def test_pvp_pitch_handoff_and_human_batting(self):
        g.new_game('PVP')
        self.assertEqual((g.pitcher_name(), g.batter_name()), ('P1', 'P2'))
        g.selected_pitch, g.pitch_aim = 'SLIDER', (590, 555)
        g.start_with_enter()
        self.assertEqual(g.game_state, 'HANDOFF')
        self.assertEqual((g.locked_pitch, g.locked_aim), ('SLIDER', (590, 555)))
        g.selected_pitch, g.pitch_aim = 'FASTBALL', (400, 730)
        g.start_with_enter()
        self.assertEqual(g.game_state, 'WINDUP')
        g.start_pitch()
        self.assertEqual((g.pitch_type, g.ball_target_x, g.ball_target_y),
                         ('SLIDER', 590, 555))
        with patch.object(g, 'choose_ai_result', side_effect=AssertionError('AI batted in PvP')):
            g.finish_pitch()
        self.assertEqual((g.strikes, g.game_state), (1, 'RESULT'))
        g.game_state, g.swung = 'PITCHING', False
        with patch.object(g, 'update_pitch'):
            g.swing_bat()
        self.assertTrue(g.swung)

    def test_pvp_roles_and_scores_swap_each_half(self):
        g.new_game('PVP')
        g.add_runs(2)
        self.assertEqual((g.score, g.ai_score), (0, 2))
        g.add_outs(3)
        g.prepare_next_half()
        self.assertEqual((g.pitcher_name(), g.batter_name()), ('P2', 'P1'))
        g.add_runs()
        self.assertEqual((g.score, g.ai_score), (1, 2))
        g.start_with_enter()
        self.assertEqual(g.game_state, 'HANDOFF')

    def test_pitch_speed_changes_flight_time_in_both_modes(self):
        for mode in ('AI', 'PVP'):
            for speed, expected in ((0.5, 1700), (1.0, 850), (2.0, 425)):
                g.new_game(mode)
                g.pitch_speed = speed
                if mode == 'PVP':
                    g.confirm_pitch()
                g.start_windup()
                g.start_pitch()
                self.assertEqual(g.pitch_duration, expected)

    def test_settings_pause_preserves_pitch_timing(self):
        g.game_state = 'PITCHING'
        g.pitch_start = 800
        g.windup_start = 700
        g.result_start = 600
        g.batted_play = {'start': 500}
        g.swing_started = 900
        with patch.object(g.pygame.time, 'get_ticks', side_effect=(1000, 1600)):
            g.open_settings()
            g.close_settings()
        self.assertEqual((g.pitch_start, g.windup_start, g.result_start,
                          g.batted_play['start'], g.swing_started),
                         (1400, 1300, 1200, 1100, 1500))
        self.assertFalse(g.settings_open)

    def test_drawing_both_roles_and_foul(self):
        for half in ('TOP', 'BOTTOM'):
            g.half = half
            g.draw_field()
            g.draw_scoreboard()
            g.draw_controls()
            g.draw_bat()
            g.start_batted_ball('FOUL')
            g.draw_batted_ball()
            g.draw_game_over()


if __name__ == '__main__':
    unittest.main()
