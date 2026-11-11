import pygame
import random
import sys
import math
from functools import lru_cache
from pathlib import Path

pygame.init()

# =========================================================
# 기본 설정
# =========================================================

WIDTH = 1280
HEIGHT = 900
FIELD_TOP = 430
GAME_TITLE = "그랜드슬램 2026"

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(GAME_TITLE)

clock = pygame.time.Clock()

# =========================================================
# 색상
# =========================================================

GREEN = (35, 130, 65)
DARK_GREEN = (20, 90, 45)

WHITE = (255, 255, 255)
BLACK = (30, 30, 30)

RED = (230, 60, 60)
BLUE = (60, 100, 220)
YELLOW = (255, 220, 60)

GRAY = (140, 140, 140)
BROWN = (130, 75, 35)
LIGHT_BROWN = (205, 145, 80)

# =========================================================
# 폰트
# =========================================================

# 모든 화면 문구에 한글 폰트를 사용한다.
FONT_PATH = str(Path(__file__).resolve().parent / "assets" / "fonts" / "NanumGothic-Regular.ttf")
font_small = pygame.font.Font(FONT_PATH, 22)
font_medium = pygame.font.Font(FONT_PATH, 30)
font_big = pygame.font.Font(FONT_PATH, 56)
font_title = pygame.font.Font(FONT_PATH, 64)

@lru_cache(maxsize=256)
def render_text(font, text, color):
    """같은 글자는 재사용하고 캐시 크기를 제한한다."""
    return font.render(text, True, color)


# =========================================================
# 버튼
# =========================================================

start_button = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 100, 240, 80)
pvp_button = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 200, 240, 80)
pitch_button = pygame.Rect(WIDTH - 280, HEIGHT - 110, 240, 70)
settings_button = pygame.Rect(WIDTH - 155, 24, 130, 48)
settings_panel = pygame.Rect(WIDTH // 2 - 320, HEIGHT // 2 - 170, 640, 340)
settings_close_button = pygame.Rect(settings_panel.right - 70, settings_panel.top + 20, 44, 44)
speed_slider = pygame.Rect(settings_panel.left + 90, settings_panel.top + 200, 460, 8)

# =========================================================
# 스트라이크존
# =========================================================

strike_zone = pygame.Rect(
    WIDTH // 2 - 92,
    525,
    184,
    210
)

# =========================================================
# 투수
# =========================================================

pitcher_x = WIDTH // 2
PITCHER_SCALE = 0.52
PITCHER_FEET_Y = 572
pitcher_y = PITCHER_FEET_Y - round(100 * PITCHER_SCALE)

# 타석에서 바라본 베이스 위치 (중심 x, 발이 닿는 y, 원근 크기)
BASE_LAYOUT = {
    "1B": (1188, 631, 0.76),
    "2B": (WIDTH // 2, 495, 0.45),
    "3B": (92, 631, 0.76),
}
HOME_POSITION = (WIDTH // 2, HEIGHT - 95)

# =========================================================
# 공
# =========================================================

ball_x = pitcher_x
ball_y = pitcher_y

ball_start_x = pitcher_x
ball_start_y = pitcher_y

ball_target_x, ball_target_y = strike_zone.center

# =========================================================
# 배트 설정
# =========================================================

BAT_WIDTH = 150
BAT_HEIGHT = 22

HANDLE_WIDTH = 45
SWING_DURATION = 820
SWING_CONTACT_WINDOW = 280
PLATE_CONTACT_WINDOW = 220
swing_started = None
swing_origin = None
windup_return_pose = None
BATTED_SPEED = 1.35

cursor_visible = None


def set_cursor_visible(visible):
    global cursor_visible
    if cursor_visible != visible:
        pygame.mouse.set_visible(visible)
        cursor_visible = visible


# 마우스 커서 숨김
set_cursor_visible(False)

# 한 투구에서 이미 스윙했는지
swung = False

# =========================================================
# 게임 상태
# =========================================================

game_state = "START"
game_mode = "AI"
settings_open = False
settings_opened_at = 0
settings_background = None
speed_dragging = False
pitch_speed = 1.0
MIN_PITCH_SPEED = 0.5
MAX_PITCH_SPEED = 2.0

# START
# READY
# HANDOFF (PvP: 투수가 목표를 확정하고 타자가 시작하기를 기다림)
# WINDUP
# PITCHING
# RESULT
# GAME_OVER

inning = 1
half = "TOP"
half_pending = False
ai_score = 0
selected_pitch = "FASTBALL"
pitch_aim = strike_zone.center
locked_aim = pitch_aim
locked_pitch = selected_pitch
PITCH_NAMES = {"FASTBALL": "직구", "CURVE": "커브", "SLIDER": "슬라이더"}

balls = 0
strikes = 0
outs = 0

score = 0

# 베이스
base1 = False
base2 = False
base3 = False

message = ""

# =========================================================
# 시간
# =========================================================

windup_start = 0
windup_duration = 1400

pitch_start = 0
pitch_duration = 850

# 구종: 이름, 비행 시간(ms), 좌우 휘어짐, 낙차 연출.
PITCH_TYPES = (
    ("FASTBALL", 850, 0, 8),
    ("SLIDER", 1000, 65, 20),
    ("CURVE", 1150, -30, 85),
)
pitch_type = "FASTBALL"
pitch_break_x = 0
pitch_drop = 8
pitch_progress = 0.0
ball_radius = 4
pending_swing_result = None
last_pitch = None
batted_play = None
result_start = 0
result_duration = 1400

# =========================================================
# 버튼
# =========================================================

def draw_button(rect, text, enabled=True):

    mouse_pos = pygame.mouse.get_pos()

    if enabled:

        if rect.collidepoint(mouse_pos):
            color = (90, 150, 240)
        else:
            color = BLUE

    else:
        color = GRAY

    pygame.draw.rect(
        screen,
        color,
        rect,
        border_radius=12
    )

    pygame.draw.rect(
        screen,
        WHITE,
        rect,
        3,
        border_radius=12
    )

    text_surface = render_text(font_medium, text, WHITE)

    text_rect = text_surface.get_rect(
        center=rect.center
    )

    screen.blit(
        text_surface,
        text_rect
    )


def set_pitch_speed_from_x(x):
    """슬라이더 위치를 0.1배 단위의 투구 속도로 바꾼다."""
    global pitch_speed
    ratio = max(0.0, min(1.0, (x - speed_slider.left) / speed_slider.width))
    pitch_speed = round(MIN_PITCH_SPEED + ratio * (MAX_PITCH_SPEED - MIN_PITCH_SPEED), 1)


def open_settings():
    global settings_open, settings_opened_at, speed_dragging, settings_background
    settings_open = True
    settings_opened_at = pygame.time.get_ticks()
    settings_background = screen.copy()
    speed_dragging = False
    set_cursor_visible(True)


def close_settings():
    global settings_open, speed_dragging, windup_start, pitch_start, result_start, swing_started
    if not settings_open:
        return
    paused = pygame.time.get_ticks() - settings_opened_at
    windup_start += paused
    pitch_start += paused
    result_start += paused
    if batted_play is not None:
        batted_play["start"] += paused
    if swing_started is not None:
        # 스윙 애니메이션도 정지한 시점에서 이어진다.
        swing_started += paused
    settings_open = False
    speed_dragging = False


def draw_settings():
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 185))
    screen.blit(shade, (0, 0))
    pygame.draw.rect(screen, BLACK, settings_panel, border_radius=18)
    pygame.draw.rect(screen, WHITE, settings_panel, 3, border_radius=18)
    title = render_text(font_big, "설정", WHITE)
    screen.blit(title, title.get_rect(center=(settings_panel.centerx, settings_panel.top + 60)))
    pygame.draw.rect(screen, RED, settings_close_button, border_radius=8)
    close_text = render_text(font_medium, "X", WHITE)
    screen.blit(close_text, close_text.get_rect(center=settings_close_button.center))
    value = render_text(font_medium, f"투구 속도  {pitch_speed:.1f}배", YELLOW)
    screen.blit(value, value.get_rect(center=(settings_panel.centerx, settings_panel.top + 145)))
    pygame.draw.rect(screen, GRAY, speed_slider, border_radius=4)
    ratio = (pitch_speed - MIN_PITCH_SPEED) / (MAX_PITCH_SPEED - MIN_PITCH_SPEED)
    knob_x = round(speed_slider.left + ratio * speed_slider.width)
    pygame.draw.rect(screen, BLUE,
                     (speed_slider.left, speed_slider.top, knob_x - speed_slider.left, speed_slider.height),
                     border_radius=4)
    pygame.draw.circle(screen, YELLOW, (knob_x, speed_slider.centery), 15)
    for label, x in (("0.5배", speed_slider.left), ("1.0배", speed_slider.left + speed_slider.width / 3),
                     ("2.0배", speed_slider.right)):
        image = render_text(font_small, label, WHITE)
        screen.blit(image, image.get_rect(center=(x, speed_slider.top + 38)))
    hint = render_text(font_small, "다음 투구부터 적용 · 설정 중 경기는 일시정지", WHITE)
    screen.blit(hint, hint.get_rect(center=(settings_panel.centerx, settings_panel.bottom - 48)))

# =========================================================
# 시작 화면
# =========================================================

def draw_start_screen():

    screen.fill(DARK_GREEN)

    title = render_text(font_title, GAME_TITLE, WHITE)

    screen.blit(
        title,
        title.get_rect(
            center=(WIDTH // 2, 200)
        )
    )

    subtitle = render_text(font_medium, "3이닝 야구 · 경기 모드를 선택하세요", YELLOW)

    screen.blit(
        subtitle,
        subtitle.get_rect(
            center=(WIDTH // 2, 280)
        )
    )

    draw_button(
        start_button,
        "AI 대전 / 엔터"
    )
    draw_button(pvp_button, "2인 PvP")


def draw_handoff_screen():
    """확정한 투구 위치를 가린 채 타자에게 화면을 넘긴다."""
    screen.fill(DARK_GREEN)
    title = render_text(font_big, f"{batter_name()} 타격 차례", WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 240)))
    instruction = render_text(font_medium, "준비되면 시작을 누르세요", YELLOW)
    screen.blit(instruction, instruction.get_rect(center=(WIDTH // 2, 335)))
    draw_button(start_button, "시작 / 엔터")

# =========================================================
# 경기장
# =========================================================

field_surface = None


def draw_field():
    global field_surface

    if field_surface is None:
        field_surface = pygame.Surface((WIDTH, HEIGHT)).convert()
        # 카메라 높이를 타자의 무릎 아래로 낮춘 구도. 땅은 화면 중간의 수평선에서 시작한다.
        for y in range(FIELD_TOP + 40):
            t = min(1, y / (FIELD_TOP + 40))
            pygame.draw.line(field_surface,
                             (round(30 + 86 * t), round(68 + 107 * t),
                              round(107 + 105 * t)), (0, y), (WIDTH, y))
        pygame.draw.rect(field_surface, (31, 111, 64),
                         (0, FIELD_TOP + 15, WIDTH, HEIGHT - FIELD_TOP - 15))
        # 관중석과 외야 펜스는 거의 수평으로 보여 먼 거리를 만든다.
        pygame.draw.polygon(field_surface, (39, 51, 69),
                            [(0, 300), (WIDTH, 300), (WIDTH, 465), (0, 465)])
        pygame.draw.rect(field_surface, (26, 42, 60), (0, 290, WIDTH, 16))
        crowd_colors = ((191, 205, 214), (181, 76, 77), (83, 145, 198), (227, 177, 81))
        for row in range(7):
            y = 319 + row * 19
            for col in range(73):
                x = col * 18 + (row % 2) * 9
                pygame.draw.circle(field_surface, crowd_colors[(col * 5 + row * 3) % 4],
                                   (x, y), 2)
        pygame.draw.polygon(field_surface, (25, 79, 73),
                            [(0, 490), (320, 463), (WIDTH // 2, 449),
                             (WIDTH - 320, 463), (WIDTH, 490),
                             (WIDTH, 552), (0, 552)])
        pygame.draw.lines(field_surface, (217, 186, 90), False,
                          [(0, 490), (320, 463), (WIDTH // 2, 449),
                           (WIDTH - 320, 463), (WIDTH, 490)], 5)
        for x, y in ((80, 483), (200, 473), (WIDTH - 200, 473), (WIDTH - 80, 483)):
            pygame.draw.line(field_surface, (202, 211, 209), (x, y), (x, y - 90), 3)
        pygame.draw.polygon(field_surface, (34, 116, 67),
                            [(0, 491), (320, 464), (WIDTH // 2, 450),
                             (WIDTH - 320, 464), (WIDTH, 491),
                             (WIDTH, HEIGHT), (0, HEIGHT)])
        # 잔디 띠는 멀리서는 촘촘하고 화면 아래에서 넓다.
        stripe_edges = (482, 495, 512, 535, 566, 610, 671, 759, HEIGHT)
        for index, (top, bottom) in enumerate(zip(stripe_edges, stripe_edges[1:])):
            color = (38, 126, 72) if index % 2 else (34, 117, 68)
            pygame.draw.rect(field_surface, color, (0, top, WIDTH, bottom - top))
        # 2루와 내야수 뒤쪽으로 휘는 흙 구역. 중앙의 투수와 마운드는 잔디에 둔다.
        third_x, third_y, _ = BASE_LAYOUT["3B"]
        first_x, first_y, _ = BASE_LAYOUT["1B"]
        pygame.draw.polygon(field_surface, (151, 101, 66), [
            (-60, 625), (third_x, third_y - 26), (270, 567), (452, 522),
            (560, 493), (640, 480), (720, 493), (828, 522), (1010, 567),
            (first_x, first_y - 26), (WIDTH + 60, 625),
            (WIDTH + 60, 675), (first_x, first_y + 24), (1010, 625),
            (828, 606), (720, 543), (640, 525), (560, 543),
            (452, 606), (270, 625), (third_x, third_y + 24), (-60, 675),
        ])
        hx, hy = HOME_POSITION
        # 베이스에서 홈으로 이어지는 흙길과 홈 주변의 흙은 하나로 연결한다.
        pygame.draw.polygon(field_surface, (164, 109, 70), [
            (third_x - 19, third_y - 8), (third_x + 19, third_y + 8),
            (hx - 30, hy - 19), (hx - 135, hy + 9),
        ])
        pygame.draw.polygon(field_surface, (164, 109, 70), [
            (first_x + 19, first_y - 8), (first_x - 19, first_y + 8),
            (hx + 30, hy - 19), (hx + 135, hy + 9),
        ])
        pygame.draw.polygon(field_surface, (170, 115, 74), [
            (0, HEIGHT), (0, hy + 8), (250, hy + 5), (450, hy - 2),
            (560, hy - 21), (hx, hy - 33), (720, hy - 21),
            (830, hy - 2), (1030, hy + 5), (WIDTH, hy + 8),
            (WIDTH, HEIGHT),
        ])
        far_y = FIELD_TOP + 70
        for base_name in ("3B", "1B"):
            bx, by, _ = BASE_LAYOUT[base_name]
            reach = (hy - far_y) / (hy - by)
            end_x = round(hx + (bx - hx) * reach)
            pygame.draw.line(field_surface, (241, 233, 208), HOME_POSITION,
                             (end_x, far_y), 3)
        feet_y = round(pitcher_y + 100 * PITCHER_SCALE)
        pygame.draw.ellipse(field_surface, (164, 110, 71),
                            (pitcher_x - 76, feet_y - 22, 152, 43))
        pygame.draw.ellipse(field_surface, (189, 131, 82),
                            (pitcher_x - 58, feet_y - 15, 116, 29))
        pygame.draw.rect(field_surface, WHITE, (pitcher_x - 14, feet_y - 6, 28, 5))
        for side in (-1, 1):
            box_x = hx + side * 116
            pygame.draw.line(field_surface, (235, 225, 196), (box_x, hy - 52),
                             (box_x, hy + 38), 2)
            pygame.draw.line(field_surface, (235, 225, 196),
                             (box_x - side * 60, hy - 52), (box_x, hy - 52), 2)

    screen.blit(field_surface, (0, 0))


def draw_runner(x, y, scale):
    """발을 베이스에 맞추고 먼 2루 주자는 작게 그린다."""
    def point(dx, dy):
        return (round(x + dx * scale), round(y + dy * scale))

    pygame.draw.ellipse(screen, (85, 65, 40),
                        (round(x - 22 * scale), round(y - 5 * scale),
                         round(44 * scale), round(10 * scale)))
    for side in (-1, 1):
        pygame.draw.line(screen, WHITE, point(side * 6, -35),
                         point(side * 11, -4), max(2, round(9 * scale)))
        pygame.draw.line(screen, BLACK, point(side * 11, -3),
                         point(side * 17, -3), max(2, round(6 * scale)))
        pygame.draw.line(screen, RED, point(side * 11, -59),
                         point(side * 20, -37), max(2, round(8 * scale)))
    pygame.draw.polygon(screen, RED,
                        [point(-13, -64), point(13, -64),
                         point(10, -34), point(-10, -34)])
    pygame.draw.circle(screen, (230, 190, 150), point(0, -75), round(11 * scale))
    pygame.draw.ellipse(screen, RED,
                        (round(x - 13 * scale), round(y - 88 * scale),
                         round(26 * scale), round(14 * scale)))
    pygame.draw.line(screen, WHITE, point(-10, -35), point(10, -35),
                     max(1, round(3 * scale)))


def draw_base(x, y, active, name, scale=1.0):
    # 원근에 맞춰 납작한 베이스를 그린다.
    width, depth = round(24 * scale), round(10 * scale)
    points = [(x, y - depth), (x + width, y),
              (x, y + depth), (x - width, y)]
    pygame.draw.polygon(screen, YELLOW if active else WHITE, points)
    pygame.draw.polygon(screen, BLACK, points, 2)
    if active:
        draw_runner(x, y, scale)


def draw_bases():
    for name, active in (("2B", base2), ("3B", base3), ("1B", base1)):
        x, y, scale = BASE_LAYOUT[name]
        draw_base(x, y, active, name, scale)

# 투수와 별도로 내야수 4명, 외야수 3명.
def defender_positions():
    second_x, second_y, _ = BASE_LAYOUT["2B"]

    def corner_position(name):
        x, y, _ = BASE_LAYOUT[name]
        # 주자 유무와 관계없이 기본 수비 위치를 유지한다.
        fraction = 0.11
        return (round(x + (second_x - x) * fraction),
                round(y + (second_y - y) * fraction), 0.74)

    return {
        "LF": (220, 511, 0.45),
        "CF": (WIDTH // 2, 484, 0.37),
        "RF": (WIDTH - 220, 511, 0.45),
        "SS": (452, 592, 0.65),
        "2B": (828, 592, 0.65),
        "3B": corner_position("3B"),
        "1B": corner_position("1B"),
    }


def draw_defenders():
    for name, (x, y, scale) in sorted(defender_positions().items(), key=lambda item: item[1][1]):
        def point(dx, dy):
            return round(x + dx * scale), round(y + dy * scale)

        pygame.draw.ellipse(screen, DARK_GREEN,
                            (round(x - 19 * scale), round(y - 4 * scale),
                             round(38 * scale), round(8 * scale)))
        for side in (-1, 1):
            pygame.draw.line(screen, WHITE, point(side * 5, -30), point(side * 13, -3),
                             max(2, round(7 * scale)))
            pygame.draw.line(screen, BLUE, point(side * 10, -52), point(side * 20, -33),
                             max(2, round(7 * scale)))
        pygame.draw.polygon(screen, BLUE,
                            [point(-12, -57), point(12, -57), point(9, -29), point(-9, -29)])
        pygame.draw.circle(screen, (230, 190, 150), point(0, -68), max(4, round(10 * scale)))
        pygame.draw.line(screen, BLUE, point(-12, -76), point(13, -76), max(3, round(7 * scale)))
        pygame.draw.circle(screen, BROWN, point(-20, -33), max(3, round(8 * scale)))


# =========================================================
# 홈
# =========================================================

def draw_home():

    x, y = HOME_POSITION
    points = [(x - 33, y - 8), (x + 33, y - 8),
              (x + 39, y + 2), (x, y + 15), (x - 39, y + 2)]

    pygame.draw.polygon(
        screen,
        WHITE,
        points
    )

# =========================================================
# 스트라이크존
# =========================================================

def draw_strike_zone():
    overlay = pygame.Surface(strike_zone.size, pygame.SRCALPHA)
    overlay.fill((210, 230, 245, 17))
    for fraction in (1 / 3, 2 / 3):
        pygame.draw.line(overlay, (225, 240, 250, 72),
                         (round(strike_zone.width * fraction), 0),
                         (round(strike_zone.width * fraction), strike_zone.height), 1)
        pygame.draw.line(overlay, (225, 240, 250, 72),
                         (0, round(strike_zone.height * fraction)),
                         (strike_zone.width, round(strike_zone.height * fraction)), 1)
    pygame.draw.rect(overlay, (245, 248, 250, 185), overlay.get_rect(), 2)
    screen.blit(overlay, strike_zone.topleft)
    text = render_text(font_small, "스트라이크 존", WHITE)
    screen.blit(text, text.get_rect(midtop=(strike_zone.centerx, strike_zone.bottom + 10)))

# =========================================================
# 투수
# =========================================================

PITCHER_SET = {
    "head": (0, 0), "shoulders": (0, 22), "hip": (0, 64),
    "back_knee": (-15, 83), "back_foot": (-19, 101),
    "lead_knee": (17, 83), "lead_foot": (21, 101),
    "glove_elbow": (-25, 32), "glove": (-5, 43),
    "throw_elbow": (24, 31), "hand": (5, 43),
}
PITCHER_LIFT = {
    "head": (-3, -3), "shoulders": (-5, 20), "hip": (-4, 64),
    "back_knee": (-16, 82), "back_foot": (-19, 101),
    "lead_knee": (20, 55), "lead_foot": (16, 72),
    "glove_elbow": (-22, 25), "glove": (-3, 36),
    "throw_elbow": (22, 26), "hand": (5, 38),
}
PITCHER_STRIDE = {
    "head": (0, -2), "shoulders": (2, 21), "hip": (-3, 64),
    "back_knee": (-16, 84), "back_foot": (-20, 101),
    "lead_knee": (24, 78), "lead_foot": (30, 111),
    "glove_elbow": (-31, 25), "glove": (-43, 33),
    "throw_elbow": (37, 3), "hand": (16, -27),
}
PITCHER_RELEASE = {
    "head": (4, -7), "shoulders": (4, 17), "hip": (-3, 62),
    "back_knee": (-15, 84), "back_foot": (-20, 101),
    "lead_knee": (25, 82), "lead_foot": (30, 111),
    "glove_elbow": (-23, 28), "glove": (-26, 52),
    "throw_elbow": (39, -8), "hand": (29, -51),
}
PITCHER_FOLLOW = {
    "head": (9, 7), "shoulders": (10, 29), "hip": (-2, 65),
    "back_knee": (-15, 83), "back_foot": (-21, 83),
    "lead_knee": (26, 85), "lead_foot": (30, 111),
    "glove_elbow": (-14, 42), "glove": (-7, 59),
    "throw_elbow": (34, 35), "hand": (12, 76),
}


def motion_curve(frames, progress):
    """시간 간격을 고려한 Hermite 곡선으로 관절의 속도를 부드럽게 잇는다."""
    progress = max(frames[0][0], min(frames[-1][0], progress))
    for i in range(len(frames) - 1):
        t0, p0 = frames[i]
        t1, p1 = frames[i + 1]
        if progress <= t1:
            dt = t1 - t0
            u = (progress - t0) / dt
            before = frames[max(0, i - 1)]
            after = frames[min(len(frames) - 1, i + 2)]
            v0 = ((p1 - before[1]) / (t1 - before[0])
                  if i else p0 * 0)
            v1 = ((after[1] - p0) / (after[0] - t0)
                  if i + 2 < len(frames) else p1 * 0)
            return ((2*u**3 - 3*u**2 + 1)*p0 + (u**3 - 2*u**2 + u)*dt*v0
                    + (-2*u**3 + 3*u**2)*p1 + (u**3 - u**2)*dt*v1)
    return frames[-1][1]


def pitcher_pose(progress, after_release=False):
    """발을 딛고 몸통을 회전한 뒤 팔을 뻗고 천천히 균형을 회복한다."""
    # 릴리스 전후도 같은 곡선에서 평가해 손의 움직임이 끊기지 않는다.
    frames = ((0, PITCHER_SET), (.40, PITCHER_LIFT),
              (.78, PITCHER_STRIDE), (1, PITCHER_RELEASE),
              (1.20, PITCHER_FOLLOW), (1.48, PITCHER_FOLLOW),
              (1.95, PITCHER_SET))
    phase = 1 + max(0, progress) * .95 if after_release else progress
    return {key: motion_curve([(t, pygame.Vector2(pose[key]))
                               for t, pose in frames], phase)
            for key in PITCHER_SET}


def draw_pitcher():
    if game_state == "WINDUP":
        progress = (pygame.time.get_ticks() - windup_start) / windup_duration
        pose = pitcher_pose(progress)
    elif game_state in ("PITCHING", "BATTED", "RESULT"):
        pose = pitcher_pose((pygame.time.get_ticks() - pitch_start) /
                            (windup_duration * .95), after_release=True)
    else:
        pose = pitcher_pose(0)

    def point(local):
        return (round(pitcher_x + local[0] * PITCHER_SCALE),
                round(pitcher_y + local[1] * PITCHER_SCALE))

    detail_scale = PITCHER_SCALE / 1.22

    def size(value):
        return max(2, round(value * detail_scale))

    shoulders, hip = pose["shoulders"], pose["hip"]
    pygame.draw.ellipse(screen, (35, 84, 56),
                        (pitcher_x - size(42), pitcher_y + round(99 * PITCHER_SCALE),
                         size(90), size(14)))
    for knee_name, foot_name in (("back_knee", "back_foot"),
                                 ("lead_knee", "lead_foot")):
        pygame.draw.line(screen, (231, 235, 239), point(hip), point(pose[knee_name]), size(12))
        pygame.draw.line(screen, (231, 235, 239), point(pose[knee_name]),
                         point(pose[foot_name]), size(11))
        shoe = pose[foot_name]
        pygame.draw.line(screen, (30, 47, 66), point(shoe + (-5, 0)),
                         point(shoe + (9, 0)), size(7))
    pygame.draw.polygon(screen, (225, 231, 237),
                        [point(shoulders + (-18, -3)), point(shoulders + (18, -3)),
                         point(hip + (14, 2)), point(hip + (-14, 2))])
    pygame.draw.line(screen, (48, 83, 130), point(shoulders + (-17, 2)),
                     point(pose["glove_elbow"]), size(11))
    pygame.draw.line(screen, (211, 169, 134), point(pose["glove_elbow"]),
                     point(pose["glove"]), size(7))
    pygame.draw.circle(screen, (115, 70, 42), point(pose["glove"]), size(10))
    pygame.draw.line(screen, (48, 83, 130), point(shoulders + (17, 2)),
                     point(pose["throw_elbow"]), size(11))
    pygame.draw.line(screen, (211, 169, 134), point(pose["throw_elbow"]),
                     point(pose["hand"]), size(8))
    pygame.draw.circle(screen, (211, 169, 134), point(pose["hand"]), size(5))
    if game_state == "WINDUP" and progress < 1:
        pygame.draw.circle(screen, WHITE, point(pose["hand"] + (3, -3)), size(4))
    pygame.draw.circle(screen, (211, 169, 134), point(pose["head"]), size(12))
    cap = point(pose["head"] + (-16, -18))
    pygame.draw.ellipse(screen, (31, 59, 97), (cap[0], cap[1], size(35), size(13)))
    pygame.draw.line(screen, (26, 49, 83), point(pose["head"] + (-14, -9)),
                     point(pose["head"] + (19, -9)), size(6))


def project_batter(point):
    """카메라에서 멀어지는 +Z 방향을 원근 투영한다."""
    scale = 700 / (700 + point.z)
    return pygame.Vector2(350 + (point.x - 350) * scale,
                          640 + (point.y - 640) * scale)


BATTER_ARM_LENGTH = 80
BATTER_SHOULDER_HALF_WIDTH = 36


def batter_preparation(now):
    """투구 준비와 타격을 같은 시간축에서 이어 붙인다."""
    def smooth(value):
        value = max(0., min(1., value))
        return value * value * (3 - 2 * value)

    if swing_started is not None:
        progress = max(0., min(.88, (now - swing_started) / SWING_DURATION))
        initial_load = smooth((swing_started - windup_start) / windup_duration)
        # 먼저 130ms 동안 발을 내딛고, 착지 후 상체의 비틀림을 푼다.
        stride = smooth(progress / .16)
        if progress <= .18:
            upper_progress = 0.
        elif progress < .43:
            upper_progress = (progress - .18) / .25 * .43
        else:
            upper_progress = progress
        coil = initial_load * (1 - smooth(upper_progress / .40))
        return upper_progress, coil, stride
    if game_state == "WINDUP":
        elapsed = max(0, now - windup_start)
        if windup_return_pose is not None:
            # 다음 투구 준비의 첫 350ms에만 마무리 자세를 풀어 준다.
            recovery = smooth(elapsed / 350)
            if elapsed < 350:
                old_progress, old_load, old_stride = windup_return_pose
                return (old_progress + (1 - old_progress) * recovery,
                        old_load * (1 - recovery), old_stride * (1 - recovery))
            return 0., smooth((elapsed - 350) / max(1, windup_duration - 350)), 0.
        return 0., smooth(elapsed / windup_duration), 0.
    if game_state == "PITCHING":
        return 0., 1., 0.
    if game_state == "RESULT":
        return 0., 1 - smooth((now - result_start) / 400), 0.
    return 0., 0., 0.


def uses_high_pitch_swing(target_y):
    return target_y <= strike_zone.top + strike_zone.height / 3


def batter_skeleton(progress, load=0., high_pitch=False):
    """모은 팔 → 낮은 4~5시 궤적 → 높은 10~11시 궤적 → 몸 앞쪽 마무리."""
    progress = max(0., min(1., progress))
    keys = [
        # 시간, 양손 위치 XYZ, 수평 회전각, 배트 기울기, 몸통 이동
        # 준비 자세의 손을 어깨보다 높여 양팔과 배트를 함께 들어 준다.
        (0., (405, 607, -12), 145, -65, 0),
        (.20, (359, 617, 75), 155, -58, -12),
        (.30, (432, 660, 48), 100, 22, 8),
        (.43, (544, 698, -12), 0, 37, 28),
        (.59, (460, 610, 160), -100, -12, 38),
        (.73, (192, 544, 95), -200, -37, 30),
        (.84, (327, 595, -80), -395, -10, 36),
        (.88, (327, 595, -80), -395, -10, 36),
        (1., (405, 607, -12), -215, -65, 0),
    ]
    if high_pitch:
        # 높은 공은 손과 배트를 수평으로 내보낸 뒤 같은 높은 마무리로 잇는다.
        keys[2] = (.30, (432, 636, 48), 100, 0, 8)
        keys[3] = (.43, (544, 636, -12), 0, 0, 28)
    hands = motion_curve([(k[0], pygame.Vector3(k[1])) for k in keys], progress)
    hands += pygame.Vector3(-10, -48, 12) * load
    # 스윙은 이전과 반대 방향. 마무리 후에는 같은 경로로 준비 자세를 회복한다.
    yaw = motion_curve([(k[0], float(k[2])) for k in keys], progress)
    elevation = motion_curve([(k[0], float(k[3])) for k in keys], progress)
    turn = motion_curve([(k[0], float(k[4])) for k in keys], progress)
    yaw, elevation = math.radians(yaw), math.radians(elevation)
    axis = pygame.Vector3(math.cos(yaw)*math.cos(elevation),
                          math.sin(elevation), math.sin(yaw)*math.cos(elevation))
    tip = hands + axis * 178
    arms = []
    extension = motion_curve([(0., 0.), (.20, 0.), (.43, 1.),
                              (.73, 1.), (.84, .25), (.88, .25), (1., 0.)], progress)
    extension = max(0., min(1., extension))
    center = pygame.Vector3(327 + turn, 636, 0)
    reach = hands - center
    flat = pygame.Vector3(reach.x, 0, reach.z).normalize()
    # 양쪽 어깨도 몸통과 회전해야 두 팔이 동시에 펴진다.
    shoulder_axis = pygame.Vector3(.16, 0, .987).lerp(
        pygame.Vector3(-flat.z, 0, flat.x), extension).normalize()
    # 팔을 편 길이는 유지하면서 손도 낮은 곳에서 높은 곳으로 이동한다.
    arm_span = 2 * BATTER_ARM_LENGTH - 1
    shoulder_width = BATTER_SHOULDER_HALF_WIDTH
    target_reach = reach.normalize() * math.sqrt(arm_span**2 - shoulder_width**2)
    reach = reach.lerp(target_reach, extension)
    alignment = abs(reach.normalize().dot(shoulder_axis))
    max_reach = -shoulder_width * alignment + math.sqrt(
        arm_span**2 - shoulder_width**2 + (shoulder_width * alignment)**2)
    if reach.length() > max_reach:
        reach.scale_to_length(max_reach)
    hands = center + reach
    tip = hands + axis * 178
    for side in (-1, 1):
        shoulder = center + shoulder_axis * (shoulder_width * side)
        delta = hands - shoulder
        distance = delta.length()
        direction = delta.normalize() if distance else pygame.Vector3(1, 0, 0)
        # 같은 길이의 상완/전완으로 손잡이를 잡는 3D 두 관절 역기구학.
        bend = pygame.Vector3(side * .35, 1, -.25)
        bend -= direction * bend.dot(direction)
        bend = bend.normalize()
        elbow = (shoulder + delta * .5 + bend *
                 math.sqrt(max(0, BATTER_ARM_LENGTH**2 - (distance * .5)**2)))
        arms.append((shoulder, elbow, hands))
    # 준비 동작의 몸통·팔·배트를 사용자가 지정한 반대쪽으로 함께 감는다.
    # 관절과 배트를 함께 강체 회전하므로 팔/배트 길이와 손잡이 접점이 유지된다.
    coil = math.radians(-105 * max(0., min(1., load)))
    cosine, sine = math.cos(coil), math.sin(coil)
    weight_shift = pygame.Vector3(10 * load, 0, -12 * load)

    def coil_point(point):
        local = point - center
        return center + weight_shift + pygame.Vector3(
            local.x * cosine - local.z * sine, local.y,
            local.x * sine + local.z * cosine)

    hands, tip = coil_point(hands), coil_point(tip)
    arms = [(coil_point(shoulder), coil_point(elbow), hands)
            for shoulder, elbow, _ in arms]
    turn += 10 * load
    return hands, tip, turn, arms


def batter_pose(progress):
    hands, tip, turn, _ = batter_skeleton(progress)
    return project_batter(hands), project_batter(tip), turn


def batter_field_turn(stride):
    """화면의 실제 수비 위치를 향하도록 발 방향과 머리 회전을 계산한다."""
    shortstop = pygame.Vector2(defender_positions()["SS"][:2])
    origin = pygame.Vector2(360, 820)
    direction = shortstop - origin
    # view()의 가로/세로 배율을 역적용한다.
    direction = pygame.Vector2(direction.x / 1.03, direction.y / 1.27).normalize()
    foot_angle = math.atan2(direction.y, direction.x) * stride
    foot_axis = pygame.Vector2(math.cos(foot_angle), math.sin(foot_angle))
    gaze = shortstop - origin
    target_yaw = math.atan2(gaze.x, -gaze.y)
    head_yaw = math.pi / 2 + (target_yaw - math.pi / 2) * stride
    return direction * (36 * stride), foot_axis, head_yaw


def batter_leg_pose(near, load, stride):
    """먼쪽 다리가 내딛고 가까운 다리는 발목을 축으로 회전한다."""
    step, step_axis, _ = batter_field_turn(stride)
    offset = 0 if near else -6
    hip = pygame.Vector2(327 + offset, 729)
    if not near:
        knee = pygame.Vector2(357 + offset + 23 * load + step.x * .55,
                              782 - 43 * load + step.y * .35)
        ankle = pygame.Vector2(331 + offset + 12 * load + step.x,
                               837 - 44 * load + step.y)
        axis = step_axis
        # 착지할수록 무릎을 펴고, 굽힘 방향을 신발의 지면 회전과 맞춘다.
        planted_knee = hip.lerp(ankle, .5) + axis * 5
        knee = knee.lerp(planted_knee, stride)
    else:
        ankle = pygame.Vector2(331, 837)
        shortstop = pygame.Vector2(defender_positions()["SS"][:2]) - (360, 820)
        target = pygame.Vector2(shortstop.x / 1.03, shortstop.y / 1.27).normalize()
        angle = math.atan2(target.y, target.x) * stride
        axis = pygame.Vector2(math.cos(angle), math.sin(angle))
        # 무릎의 굽힘 방향도 발끝과 함께 돌아가며 지지 다리가 펴진다.
        bend = 27 * (1 - stride) + 8 * stride
        knee = hip.lerp(ankle, .5) + axis * bend
    return hip, knee, ankle, axis


def batter_shoe_mesh(axis):
    """신발을 지면 XZ 위에서 회전한다. Y는 높이로 회전과 독립적이다."""
    yaw = math.atan2(-axis.y, axis.x)
    cosine, sine = math.cos(yaw), math.sin(yaw)
    # 둥근 앞코와 좁은 뒤꿈치, 밑창/갑피의 세 단면.
    outline = [(-12, -7), (13, -9), (29, -7), (34, -3),
               (34, 3), (29, 7), (13, 9), (-12, 7)]
    vertices = []
    for height, taper in ((0, 1.), (3, 1.), (12, .80)):
        for along, across in outline:
            along = along if height < 12 else along * .82
            across *= taper
            vertices.append(pygame.Vector3(along*cosine - across*sine,
                                           height, along*sine + across*cosine))
    return vertices


def draw_batter_shoe(ankle, axis, near):
    vertices = batter_shoe_mesh(axis)
    origin = pygame.Vector2(360 + (ankle.x - 330) * 1.03,
                            820 + (ankle.y - 852) * 1.27)

    def project(point):
        # 지면의 깊이를 세로로 압축해 발이 수직으로 서 보이지 않게 한다.
        perspective = 760 / (760 + point.z)
        return (round(origin.x + point.x * perspective * 1.03),
                round(origin.y + (12 - point.y - point.z * .24) * perspective * 1.27))

    faces = []
    for ring in (0, 1):
        for j in range(8):
            nxt = (j + 1) % 8
            indices = (ring*8+j, ring*8+nxt, (ring+1)*8+nxt, (ring+1)*8+j)
            points = [vertices[index] for index in indices]
            edge = points[1] - points[0]
            # 카메라를 향하는 옆면만 그린다.
            outward_z = -edge.x
            if outward_z >= 0:
                continue
            if ring == 0:
                color = (208, 215, 221) if near else (162, 173, 185)
            else:
                shade = round(12 * abs(edge.x) / max(1, edge.length()))
                color = (29 + shade, 43 + shade, 60 + shade)
            faces.append((sum(v.z for v in points) / 4, points, color))
    faces.append((sum(v.z for v in vertices[16:]) / 8,
                  vertices[16:], (54, 72, 94) if near else (43, 58, 78)))
    for _, points, color in sorted(faces, key=lambda face: -face[0]):
        pygame.draw.polygon(screen, color, [project(v) for v in points])
    # 발등의 끈에도 동일한 3D 회전을 적용한다.
    yaw = math.atan2(-axis.y, axis.x)
    for along in (2, 7, 12):
        ends = [pygame.Vector3(along*math.cos(yaw) - across*math.sin(yaw), 12.5,
                               along*math.sin(yaw) + across*math.cos(yaw))
                for across in (-4, 4)]
        pygame.draw.line(screen, (148, 164, 183), project(ends[0]), project(ends[1]), 2)


def draw_foreground_batter():
    """타격 자세, 체중 이동, 임팩트, 팔로스루를 같은 화면 좌표에서 그린다."""
    if game_state not in ("READY", "WINDUP", "PITCHING", "BATTED", "RESULT"):
        return
    progress, load, stride = batter_preparation(pygame.time.get_ticks())
    hands3, tip3, turn, arms = batter_skeleton(
        progress, load, high_pitch=uses_high_pitch_swing(ball_target_y))
    step, foot_axis, head_yaw = batter_field_turn(stride)
    x, floor = 330, 852
    screen_x, screen_floor = 360, 820
    shift = round(turn)
    # 전경 타자를 투수 쪽으로 조금 옮기고 원근에 맞게 살짝 작게 그린다.
    def view(pos):
        # 발은 땅에 고정하고 무릎과 골반에 체중 이동을 전달한다.
        lower_weight = max(0.0, min(1.0, (floor - pos[1] - 12) / 115))
        lower_shift = turn * .42 * lower_weight if pos[1] >= floor - 130 else 0
        body_weight = max(0., min(1., (floor - pos[1] - 15) / 105))
        return (round(screen_x + (pos[0] - x + lower_shift + (step.x * .42 - 14 * stride) * body_weight) * 1.03),
                round(screen_floor + (pos[1] - floor + step.y * .20 * body_weight) * 1.27))

    def outline(points):
        return [view(point) for point in points]

    # 팔과 배트를 작은 3D 구간으로 나눠 몸통 뒤/앞 순서로 그린다.
    parts = []
    def add_segment(start, end, radius, color, count=12):
        for i in range(count):
            p0 = start.lerp(end, i / count)
            p1 = start.lerp(end, (i + 1) / count)
            parts.append(((p0.z + p1.z) * .5, p0, p1, radius, color))

    for shoulder, elbow, grip in arms:
        add_segment(shoulder, elbow, 12, (42, 84, 138))
        add_segment(elbow, grip, 7, (211, 168, 133))
    for i in range(28):
        t = i / 28
        p0, p1 = hands3.lerp(tip3, t), hands3.lerp(tip3, (i + 1) / 28)
        radius = 5 + 5 * min(1, t / .65)
        color = (109, 67, 39) if t < .25 else (219, 165, 96)
        add_segment(p0, p1, radius, color, 1)
    for offset in (-5, 5):
        grip = hands3 + (tip3 - hands3).normalize() * offset
        add_segment(grip, grip, 10, (233, 232, 222), 1)

    def draw_swing_parts(behind):
        for depth, p0, p1, radius, color in sorted(parts, key=lambda part: -part[0]):
            if (depth > 0) != behind:
                continue
            start, end = view(project_batter(p0)), view(project_batter(p1))
            width = max(2, round(radius * 2 * 700 / (700 + depth)))
            pygame.draw.line(screen, color, start, end, width)
            pygame.draw.circle(screen, color, end, max(1, width // 2))
            if color == (219, 165, 96):
                pygame.draw.line(screen, (244, 200, 135),
                                 (start[0] - 2, start[1] - 2),
                                 (end[0] - 2, end[1] - 2), 2)

    draw_swing_parts(True)
    pygame.draw.ellipse(screen, (26, 68, 48),
                        (screen_x - 35, screen_floor - 13, 94, 24))
    # 기존과 반대로 먼쪽 다리를 들어 내딛고 가까운 다리는 제자리 회전한다.
    for near, color in ((False, (27, 41, 59)), (True, (37, 54, 75))):
        hip, knee, ankle, leg_axis = batter_leg_pose(near, load * (1 - stride), stride)
        pygame.draw.line(screen, color, view(hip), view(knee), 31)
        pygame.draw.circle(screen, color, view(knee), 15)
        ankle_screen = (round(screen_x + (ankle[0] - x) * 1.03),
                        round(screen_floor + (ankle[1] - floor) * 1.27))
        pygame.draw.line(screen, color, view(knee), ankle_screen, 26)
        draw_batter_shoe(ankle, leg_axis, near)
    shoulder_edges = sorted((project_batter(arm[0]) for arm in arms), key=lambda p: p.x)
    pygame.draw.polygon(screen, (232, 235, 237),
                        outline([shoulder_edges[0] + (-8, -16),
                                 shoulder_edges[1] + (8, -16),
                                 (x + 20 + 8 * load, floor - 126),
                                 (x - 21 - 8 * load, floor - 120)]))
    head_x = x - 6 + shift // 2
    face = view((head_x, floor - 265))
    pygame.draw.ellipse(screen, (212, 171, 139),
                        (face[0] - 40, face[1] - 46, 80, 92))
    # 옆얼굴에서 유격수를 보는 뒤쪽 3/4 얼굴로 회전한다.
    # 코·눈·챙도 함께 이동하고, 돌아설수록 헬멧 뒤쪽이 얼굴을 가린다.
    facing = math.sin(head_yaw)
    away = max(0., math.cos(head_yaw))
    nose_x = head_x + 43 * facing
    if facing > .55:
        pygame.draw.polygon(screen, (212, 171, 139),
                            outline([(nose_x - 10, floor - 274),
                                     (nose_x + 9 * facing, floor - 265),
                                     (nose_x - 9, floor - 258)]))
    helmet_left = view((head_x - 48, floor - 312))
    pygame.draw.ellipse(screen, (35, 63, 104),
                        (helmet_left[0], helmet_left[1], 94, 50))
    if away > 0:
        pygame.draw.ellipse(screen, (35, 63, 104),
                            (face[0] - 41, face[1] - 42, round(80 * away), 74))
    pygame.draw.line(screen, (27, 50, 88),
                     view((head_x - 33 * facing, floor - 276 - 9 * away)),
                     view((head_x + 56 * facing, floor - 278 - 12 * away)), 11)
    if facing > .65:
        pygame.draw.circle(screen, (39, 43, 48),
                           view((head_x + 30 * facing, floor - 269 - 4 * away)), 3)
    number = render_text(font_medium, "26", (50, 87, 136))
    screen.blit(number, number.get_rect(center=view((x + shift, floor - 175))))

    draw_swing_parts(False)

# =========================================================
# 배트
# =========================================================

def get_bat_rect():

    mouse_x, mouse_y = pygame.mouse.get_pos()

    return pygame.Rect(
        mouse_x - BAT_WIDTH // 2,
        mouse_y - BAT_HEIGHT // 2,
        BAT_WIDTH,
        BAT_HEIGHT
    )


def draw_bat():
    if (game_state not in ("READY", "WINDUP", "PITCHING", "BATTED", "RESULT") or
        (game_mode == "PVP" and game_state == "READY")):
        return
    if game_mode == "AI" and is_player_pitching():
        return
    elapsed = pygame.time.get_ticks() - swing_started if swing_started is not None else SWING_DURATION
    animating = swing_origin is not None and 0 <= elapsed < SWING_DURATION
    if game_state == "BATTED" and not animating:
        return
    bat = (pygame.Rect(round(swing_origin[0] - 12), round(swing_origin[1] - BAT_HEIGHT / 2),
                       BAT_WIDTH, BAT_HEIGHT) if animating else get_bat_rect())
    if not animating and not strike_zone.inflate(360, 200).collidepoint(bat.center):
        return
    guide = pygame.Surface(bat.size, pygame.SRCALPHA)
    if animating:
        glow = round(240 * (1 - min(1, elapsed / SWING_DURATION)))
        pygame.draw.rect(guide, (255, 233, 143, glow), guide.get_rect(), 3, border_radius=8)
        pygame.draw.circle(guide, (255, 242, 170, glow),
                           (BAT_WIDTH // 2, BAT_HEIGHT // 2), 10, 2)
    else:
        pygame.draw.rect(guide, (255, 232, 132, 42), guide.get_rect(), border_radius=8)
        pygame.draw.rect(guide, (255, 238, 169, 190), guide.get_rect(), 2, border_radius=8)
        pygame.draw.line(guide, (255, 245, 206, 220),
                         (HANDLE_WIDTH, 2), (HANDLE_WIDTH, BAT_HEIGHT - 2), 2)
        pygame.draw.circle(guide, (255, 245, 206, 240),
                           (BAT_WIDTH // 2, BAT_HEIGHT // 2), 4, 1)
    screen.blit(guide, bat.topleft)

# =========================================================
# 스코어보드
# =========================================================

def draw_scoreboard():

    pygame.draw.rect(
        screen,
        BLACK,
        (20, 20, 290, 175),
        border_radius=10
    )

    texts = [
        (
            f"{inning}회{'초' if half == 'TOP' else '말'} / 3회",
            WHITE,
            40,
            35
        ),
        (
            f"볼       {balls}",
            (100, 255, 100),
            40,
            85
        ),
        (
            f"스트라이크 {strikes}",
            YELLOW,
            40,
            112
        ),
        (
            f"아웃    {outs}",
            RED,
            40,
            139
        ),
        (
            f"{'P1' if game_mode == 'PVP' else '나'} {score} : {'P2' if game_mode == 'PVP' else 'AI'} {ai_score}",
            WHITE,
            40,
            166
        )
    ]

    for text, color, x, y in texts:

        img = render_text(font_small, text, color)

        screen.blit(
            img,
            (x, y)
        )

# =========================================================
# 투구 위치
# =========================================================

def choose_pitch_target():

    roll = random.random()

    # 70% 존 안
    if roll < 0.70:

        x = random.randint(
            strike_zone.left + 10,
            strike_zone.right - 10
        )

        y = random.randint(
            strike_zone.top + 10,
            strike_zone.bottom - 10
        )

    # 20% 존 밖
    elif roll < 0.90:

        while True:

            x = random.randint(
                strike_zone.left - 95,
                strike_zone.right + 95
            )

            y = random.randint(
                strike_zone.top - 40,
                strike_zone.bottom + 60
            )

            if not strike_zone.collidepoint(
                x,
                y
            ):
                break

    # 10% 완전 랜덤
    else:

        x = random.randint(
            strike_zone.left - 95,
            strike_zone.right + 95
        )

        y = random.randint(
            strike_zone.top - 40,
            strike_zone.bottom + 60
        )

    return x, y

# =========================================================
# 카운트 초기화
# =========================================================

def reset_count():

    global balls
    global strikes

    balls = 0
    strikes = 0

# =========================================================
# 이닝 / 아웃 처리
# =========================================================

def is_player_pitching():
    return half == "TOP"


def pitcher_name():
    return "P1" if half == "TOP" else "P2"


def batter_name():
    return "P2" if half == "TOP" else "P1"


def ready_message():
    if game_mode == "PVP":
        return f"{pitcher_name()} 투구: 구종과 목표 선택 후 준비 완료"
    if is_player_pitching():
        return "내 투구: 1 직구 / 2 커브 / 3 슬라이더 · 클릭으로 목표 지정 · 엔터로 던지기"
    return "내 타격: 엔터로 투구 시작 · 마우스로 조준 · 스페이스로 스윙"


def add_runs(amount=1):
    global score, ai_score
    if is_player_pitching():
        ai_score += amount
    else:
        score += amount


def add_outs(amount=1):
    global outs, half_pending, message
    outs = min(3, outs + amount)
    reset_count()
    if outs == 3:
        half_pending = True
        message = "3아웃! 공수 교대"
        return True
    return False


def prepare_next_half():
    global half, inning, outs, half_pending, base1, base2, base3
    global last_pitch, batted_play, game_state, message, swing_started
    if not half_pending:
        return
    half_pending = False
    if half == "BOTTOM" and inning == 3:
        game_state = "GAME_OVER"
        return
    if half == "TOP":
        half = "BOTTOM"
    else:
        half = "TOP"
        inning += 1
    outs = 0
    reset_count()
    base1 = base2 = base3 = False
    last_pitch = batted_play = swing_started = None
    message = ready_message()


# =========================================================
# 볼넷
# =========================================================

def walk_batter():

    global base1
    global base2
    global base3
    global score

    old1 = base1
    old2 = base2
    old3 = base3

    # 만루
    if old1 and old2 and old3:

        add_runs()

        base1 = True
        base2 = True
        base3 = True

    # 1,2루
    elif old1 and old2:

        base3 = True
        base2 = True
        base1 = True

    # 1루 주자 있음
    elif old1:

        base2 = True
        base1 = True

        # 기존 3루 주자는 유지
        base3 = old3

    # 1루 비어있음
    else:

        base1 = True

# =========================================================
# 안타 진루
# =========================================================

def advance_runners(bases):
    """안타 거리만큼 기존 주자와 타자를 진루시킨다."""
    global base1, base2, base3, score

    runners = [False, False, False]
    for start, occupied in enumerate((base1, base2, base3), start=1):
        if occupied:
            destination = start + bases
            if destination >= 4:
                add_runs()
            else:
                runners[destination - 1] = True

    if bases == 4:
        add_runs()
    else:
        runners[bases - 1] = True
    base1, base2, base3 = runners


def hit_single():
    advance_runners(1)


def hit_double():
    advance_runners(2)


def hit_triple():
    advance_runners(3)


def hit_homerun():
    advance_runners(4)

# =========================================================
# 뜬공
# =========================================================

def fly_out():

    global base1
    global base2
    global base3
    global score
    global message

    old2 = base2
    old3 = base3

    extra_messages = []

    # 먼저 타자 아웃
    inning_ended = add_outs(1)

    if inning_ended:
        return

    # 3루 주자
    third_scored = False

    if old3:

        if random.random() < 0.80:

            add_runs()
            base3 = False

            third_scored = True

            extra_messages.append(
                "3루 주자 득점"
            )

        else:

            base3 = True

            extra_messages.append(
                "3루 주자 대기"
            )

    # 2루 주자
    if old2:

        can_try = False

        # 3루에 원래 주자가 없었다면 바로 시도
        if not old3:
            can_try = True

        # 2,3루였으면 3루 주자가 득점 성공해야 시도
        elif third_scored:
            can_try = True

        if can_try:

            if random.random() < 0.30:

                base2 = False
                base3 = True

                extra_messages.append(
                    "2루 주자 3루 진루"
                )

            else:

                base2 = True

                extra_messages.append(
                    "2루 주자 대기"
                )

    if extra_messages:

        message = "뜬공 아웃 / " + " / ".join(
            extra_messages
        )

    else:

        message = "뜬공 아웃"

# =========================================================
# 땅볼
# =========================================================

def ground_ball():

    global base1
    global message

    # 1루 주자가 있고 2아웃 미만
    if base1 and outs < 2:

        if random.random() < 0.50:

            # 병살
            base1 = False

            inning_ended = add_outs(2)

            if not inning_ended:
                message = "병살타!"

            return

    # 일반 땅볼 아웃
    inning_ended = add_outs(1)

    if not inning_ended:
        message = "땅볼 아웃"

# =========================================================
# 타격 결과 확률
# =========================================================

def choose_batting_result(hit_type):

    if random.random() < (0.15 if hit_type == "CENTER" else 0.35):
        return "FOUL"
    roll = random.random() * 100

    # ----------------------------------
    # 배트 중심
    # ----------------------------------

    if hit_type == "CENTER":

        if roll < 50:
            return "SINGLE"

        elif roll < 70:
            return "DOUBLE"

        elif roll < 75:
            return "TRIPLE"

        elif roll < 85:
            return "HOMERUN"

        elif roll < 95:
            return "FLY"

        else:
            return "GROUND"

    # ----------------------------------
    # 손잡이
    # ----------------------------------

    else:

        if roll < 20:
            return "SINGLE"

        elif roll < 25:
            return "DOUBLE"

        elif roll < 55:
            return "FLY"

        else:
            return "GROUND"

# =========================================================
# 타격 결과 처리
# =========================================================

def apply_batting_result(result):

    global message
    global game_state
    global result_start

    if result == "FOUL":
        register_foul()
        return
    reset_count()

    if result == "SINGLE":

        hit_single()
        message = "1루타!"

    elif result == "DOUBLE":

        hit_double()
        message = "2루타!"

    elif result == "TRIPLE":

        hit_triple()
        message = "3루타!"

    elif result == "HOMERUN":

        hit_homerun()
        message = "홈런!"

    elif result == "FLY":

        fly_out()

    elif result == "GROUND":

        ground_ball()

    if game_state != "GAME_OVER":

        game_state = "RESULT"

        result_start = pygame.time.get_ticks()

# =========================================================
# 스윙
# =========================================================

def swing_bat():
    global swung, pending_swing_result, message, swing_started, swing_origin

    if (game_mode == "AI" and is_player_pitching()) or game_state != "PITCHING" or swung:
        return
    # 이벤트 시점의 위치로 판정하여 이전 프레임 좌표를 사용하지 않는다.
    update_pitch()
    if game_state != "PITCHING":
        return

    swung = True
    bat = get_bat_rect()
    swing_started = pygame.time.get_ticks()
    swing_origin = (bat.left + 12, bat.centery)
    pending_swing_result = "MISS"
    message = "스윙!"
    check_swing_contact(swing_started)


def check_swing_contact(now):
    """공이 타석에 도착했을 때만 잠근 조준 위치와 비교한다."""
    global ball_x, ball_y, ball_radius, pitch_progress, last_pitch
    global pending_swing_result, message
    if (game_state != "PITCHING" or not swung or swing_started is None or
            swing_origin is None or
            pending_swing_result != "MISS" or
            (game_mode == "AI" and is_player_pitching())):
        return
    arrival = pitch_start + pitch_duration
    if (now < arrival or swing_started > arrival + PLATE_CONTACT_WINDOW or
            swing_started + SWING_CONTACT_WINDOW < arrival):
        return
    bat = pygame.Rect(round(swing_origin[0] - 12),
                      round(swing_origin[1] - BAT_HEIGHT / 2), BAT_WIDTH, BAT_HEIGHT)
    x, y, radius = pitch_pose(1)
    nearest_x = max(bat.left, min(x, bat.right))
    nearest_y = max(bat.top, min(y, bat.bottom))
    if (x - nearest_x) ** 2 + (y - nearest_y) ** 2 > radius ** 2:
        return
    ball_x, ball_y, ball_radius, pitch_progress = x, y, radius, 1.0
    contact = "HANDLE" if x - bat.left <= HANDLE_WIDTH else "CENTER"
    result = choose_batting_result(contact)
    pending_swing_result = None
    last_pitch = (ball_target_x, ball_target_y, pitch_type)
    start_batted_ball(result)
    if result != "FOUL":
        message = ("정타! 타구가 날아갑니다!" if contact == "CENTER" else
                   "빗맞았지만 타구가 날아갑니다!")


# 안타가 된 뒤의 단타/2루타/3루타/홈런 비율.
AI_HIT_WEIGHTS = {
    (True, True): (65, 22, 3, 10),
    (True, False): (70, 20, 3, 7),
    (False, True): (78, 17, 2, 3),
    (False, False): (82, 14, 2, 2),
}


def ai_batting_probabilities(kind, target):
    x, y = target
    inside = strike_zone.collidepoint(x, y)
    fastball = kind == "FASTBALL"
    if inside:
        return (0.70, 0.50, 0.50) if fastball else (0.45, 0.70, 0.60)
    # 모서리에서도 높낮이를 우선한다. bottom은 존 바깥 경계다.
    if fastball:
        return (0.10, 0.0, 0.0) if y >= strike_zone.bottom else (0.40, 0.30, 0.40)
    return (0.10, 0.0, 0.0) if y < strike_zone.top else (0.70, 0.10, 0.70)


def choose_ai_result(kind, target):
    swing, contact, hit = ai_batting_probabilities(kind, target)
    if random.random() >= swing:
        return "TAKE"
    if random.random() >= contact:
        return "MISS"
    # 컨택 직후 안타 판정을 해 요청한 조건부 확률을 유지한다.
    if random.random() < hit:
        weights = AI_HIT_WEIGHTS[(bool(strike_zone.collidepoint(*target)), kind == "FASTBALL")]
        return random.choices(("SINGLE", "DOUBLE", "TRIPLE", "HOMERUN"), weights=weights)[0]
    if random.random() < 0.30:
        return "FOUL"
    return random.choice(("FLY", "GROUND"))


def register_foul():
    global strikes, message, game_state, result_start
    already_two = strikes == 2
    strikes = min(2, strikes + 1)
    message = "파울!" + (" 2스트라이크 유지" if already_two else "")
    game_state = "RESULT"
    result_start = pygame.time.get_ticks()


def finish_pitch():
    global strikes, message, game_state, result_start, pending_swing_result

    global last_pitch, swung, swing_started, swing_origin

    if game_mode == "AI" and is_player_pitching():
        pending_swing_result = choose_ai_result(pitch_type, (ball_target_x, ball_target_y))
        swung = pending_swing_result != "TAKE"
        if swung:
            swing_started = pygame.time.get_ticks()
            swing_origin = (strike_zone.left - 45, strike_zone.centery)

    last_pitch = (ball_target_x, ball_target_y, pitch_type)
    result = pending_swing_result
    pending_swing_result = None
    if not swung:
        judge_pitch()
    elif result == "MISS":
        strikes += 1
        message = "헛스윙!"
        if strikes >= 3:
            message = "헛스윙 삼진!"
            add_outs(1)
        if game_state != "GAME_OVER":
            game_state = "RESULT"
            result_start = pygame.time.get_ticks()
    else:
        start_batted_ball(result)

# =========================================================
# 투구 판정
# =========================================================

def judge_pitch():

    global balls
    global strikes
    global message
    global game_state
    global result_start

    # 스윙을 안 했을 경우만 판정
    if strike_zone.collidepoint(
        ball_target_x,
        ball_target_y
    ):

        strikes += 1

        message = "스트라이크!"

        if strikes >= 3:

            message = "루킹 삼진!"

            add_outs(1)

    else:

        balls += 1

        message = "볼!"

        if balls >= 4:

            walk_batter()

            reset_count()

            message = "볼넷!"

    if game_state != "GAME_OVER":

        game_state = "RESULT"

        result_start = pygame.time.get_ticks()

# =========================================================
# 새 게임
# =========================================================

def new_game(mode="AI"):

    global inning, windup_return_pose
    windup_return_pose = None
    global balls
    global strikes
    global outs
    global score

    global base1
    global base2
    global base3

    global message
    global game_state
    global swung
    global last_pitch, batted_play, swing_started, swing_origin

    global half, half_pending, ai_score, selected_pitch, pitch_aim, game_mode
    game_mode = mode
    half, half_pending, ai_score = "TOP", False, 0
    selected_pitch, pitch_aim = "FASTBALL", strike_zone.center
    batted_play = None
    swing_started = None
    swing_origin = None
    inning = 1

    balls = 0
    strikes = 0
    outs = 0

    score = 0

    base1 = False
    base2 = False
    base3 = False

    swung = False
    last_pitch = None

    message = ready_message()

    game_state = "READY"


def confirm_pitch():
    """PvP 투수가 목표를 확정하고 타자에게 조작을 넘긴다."""
    global locked_aim, locked_pitch, game_state, message
    if game_mode != "PVP" or game_state != "READY":
        return
    locked_aim, locked_pitch = pitch_aim, selected_pitch
    game_state = "HANDOFF"
    message = f"{batter_name()} 차례: 시작을 누르면 투구합니다"

# =========================================================
# 와인드업
# =========================================================

def start_windup():

    global game_state
    global windup_start, windup_return_pose
    global message
    global swung
    global last_pitch, batted_play, swing_started, swing_origin

    global locked_aim, locked_pitch
    prepare_next_half()
    if game_state == "GAME_OVER":
        return
    if game_mode == "AI":
        locked_aim, locked_pitch = pitch_aim, selected_pitch
    windup_return_pose = (batter_preparation(pygame.time.get_ticks())
                          if swing_started is not None else None)
    batted_play = None
    swing_started = None
    swing_origin = None
    swung = False
    last_pitch = None

    game_state = "WINDUP"

    windup_start = pygame.time.get_ticks()

    message = "투수 준비 중..."

# =========================================================
# 투구 시작
# =========================================================

def start_pitch():
    global game_state, pitch_start, pitch_duration, pitch_type
    global ball_start_x, ball_start_y, ball_target_x, ball_target_y
    global ball_x, ball_y, ball_radius, pitch_progress
    global pitch_break_x, pitch_drop, pending_swing_result, message, swung

    swung = False
    pending_swing_result = None
    pitch_progress = 0.0
    # 공이 릴리스 프레임의 손 위치에서 정확히 출발한다.
    release_hand = pitcher_pose(1)["hand"]
    ball_start_x = pitcher_x + release_hand.x * PITCHER_SCALE
    ball_start_y = pitcher_y + release_hand.y * PITCHER_SCALE
    if game_mode == "PVP" or is_player_pitching():
        ball_target_x, ball_target_y = locked_aim
        pitch_type, pitch_duration, pitch_break_x, pitch_drop = next(p for p in PITCH_TYPES if p[0] == locked_pitch)
    else:
        ball_target_x, ball_target_y = choose_pitch_target()
        pitch_type, pitch_duration, pitch_break_x, pitch_drop = random.choice(PITCH_TYPES)
    pitch_duration = round(pitch_duration / pitch_speed)
    ball_x, ball_y, ball_radius = pitch_pose(0)
    pitch_start = pygame.time.get_ticks()
    game_state = "PITCHING"
    message = "투구!"


def pitch_pose(progress):
    """원근 투영과 구종별 궤적. 커브는 초반에 뜬 뒤 후반에 떨어진다."""
    progress = max(0.0, min(1.0, progress))
    depth = progress / (3.0 - 2.0 * progress)
    bend = math.sin(math.pi * progress) * depth
    x = ball_start_x + (ball_target_x - ball_start_x) * depth + pitch_break_x * bend
    if pitch_type == "CURVE":
        rise = pitch_drop * 0.22
        if progress <= 0.30:
            t = progress / 0.30
            y = ball_start_y - rise * (t * t * (3 - 2 * t))
        else:
            t = (progress - 0.30) / 0.70
            y = ball_start_y - rise + (ball_target_y - ball_start_y + rise) * t ** 2.5
    else:
        y = ball_start_y + (ball_target_y - ball_start_y) * depth - pitch_drop * bend
    radius = 4 + 20 * depth
    # 끝점은 구종과 관계없이 정해진 투구 위치에 정확히 일치한다.
    if progress >= 1:
        return float(ball_target_x), float(ball_target_y), radius
    return x, y, radius


def update_pitch():
    global ball_x, ball_y, ball_radius, pitch_progress

    if game_state != "PITCHING":
        return
    now = pygame.time.get_ticks()
    pitch_progress = max(0.0, min(1.0, (now - pitch_start) / pitch_duration))
    ball_x, ball_y, ball_radius = pitch_pose(pitch_progress)
    check_swing_contact(now)
    if game_state != "PITCHING":
        return
    if (pitch_progress >= 1 and
            ((game_mode == "AI" and is_player_pitching()) or
             now >= pitch_start + pitch_duration + PLATE_CONTACT_WINDOW)):
        finish_pitch()


def start_batted_ball(result):
    global batted_play, game_state, message

    # 지면상 경로와 공 높이를 따로 계산해 내야 통과/낙하/뜬공을 표현한다.
    home = HOME_POSITION
    side = random.choice((-1, 1))
    center_x = WIDTH // 2
    fielders = defender_positions()
    if result == "FOUL":
        points = [home, (-100 if side < 0 else WIDTH + 100, 600)]
        arc, duration, grounder = 80, 950, False
    elif result == "SINGLE":
        if random.random() < 0.5:
            # 유격수-3루수 또는 2루수-1루수 사이를 지나는 땅볼.
            corner = fielders["3B" if side < 0 else "1B"]
            middle = fielders["SS" if side < 0 else "2B"]
            gap = (round((corner[0] + middle[0]) / 2), round((corner[1] + middle[1]) / 2))
            # 홈→내야수 사이의 방향을 그대로 연장한다.
            # 중간 제어점을 없애 통과 후 방향이나 속도가 꺾이지 않게 한다.
            end_y = 530
            extension = (home[1] - end_y) / (home[1] - gap[1])
            end_x = home[0] + (gap[0] - home[0]) * extension
            points = [home, (end_x, end_y)]
            arc, duration, grounder = 0, 1250, True
        else:
            # 좌/우 외야수보다 홈에 가까운 위치에 떨어지는 안타.
            outfielder = fielders["LF" if side < 0 else "RF"]
            points = [home, (outfielder[0], outfielder[1] + 65)]
            arc, duration, grounder = 90, 1500, False
    elif result == "DOUBLE":
        # 기존 외야수 사이 방향을 유지하며 깊은 외야에 뜬공으로 떨어진다.
        wing = fielders["LF" if side < 0 else "RF"]
        center = fielders["CF"]
        gap = (round((wing[0] + center[0]) / 2), round((wing[1] + center[1]) / 2))
        deep = (gap[0] + side * 30, FIELD_TOP + 15)
        points = [home, gap, deep]
        arc, duration, grounder = 220, 1650, False
    elif result == "TRIPLE":
        # 화면 가장자리에서 60px 안쪽인 좌우 펜스 구석으로 보낸다.
        end_x = 60 if side < 0 else WIDTH - 60
        end_y = FIELD_TOP + 15
        points = [home, (end_x, end_y)]
        arc, duration, grounder = 250, 1900, False
    elif result == "HOMERUN":
        points = [home, (center_x + side * 220, -160)]
        arc, duration, grounder = 200, 1800, False
    elif result == "FLY":
        x, y, _ = defender_positions()[random.choice(("LF", "CF", "RF"))]
        points = [home, (x, y)]
        arc, duration, grounder = 140, 1450, False
    else:
        x, y, _ = defender_positions()[random.choice(("SS", "2B", "3B", "1B"))]
        points = [home, (x, y)]
        arc, duration, grounder = 0, 1000, True

    batted_play = dict(result=result, points=points, arc=arc, duration=round(duration / BATTED_SPEED),
                       grounder=grounder, start=pygame.time.get_ticks(),
                       contact=(ball_x, ball_y))
    game_state = "BATTED"
    message = "파울!" if result == "FOUL" else "홈런!" if result == "HOMERUN" else "타구가 날아갑니다!"


def batted_pose(progress):
    play = batted_play
    progress = max(0.0, min(1.0, progress))
    points = play["points"]
    if len(points) == 3 and not play["grounder"]:
        # 기존 2루타의 중간 방향을 75% 지점에서 통과하는 매끈한 곡선.
        a, waypoint, b = points
        t = 0.75
        control = tuple((waypoint[i] - (1 - t) ** 2 * a[i] - t ** 2 * b[i]) /
                        (2 * t * (1 - t)) for i in (0, 1))
        ground_x, ground_y = tuple((1 - progress) ** 2 * a[i] +
                                  2 * progress * (1 - progress) * control[i] +
                                  progress ** 2 * b[i] for i in (0, 1))
    else:
        a, b = points[0], points[-1]
        ground_x = a[0] + (b[0] - a[0]) * progress
        ground_y = a[1] + (b[1] - a[1]) * progress
    # 투구 도착 위치에서 끊김 없이 지면상의 타구 경로로 이어진다.
    settle = max(0.0, 1 - progress / 0.22) if play["grounder"] else 1 - progress
    x = ground_x + (play["contact"][0] - HOME_POSITION[0]) * settle
    height = (HOME_POSITION[1] - play["contact"][1]) * settle
    # 비행 전체에 걸친 포물선: 중간에 착지하거나 구르는 구간이 없다.
    height += play["arc"] * 4 * progress * (1 - progress)
    if play["grounder"] and play["result"] not in ("SINGLE", "TRIPLE") and progress > 0.22:
        height += abs(math.sin(progress * math.pi * 7)) * 10 * (1 - progress)
    radius = max(3, 18 * (1 - progress) + 3 * progress)
    return x, ground_y - height, ground_x, ground_y, radius


def update_batted_ball():
    if game_state != "BATTED" or batted_play is None:
        return
    if pygame.time.get_ticks() - batted_play["start"] >= batted_play["duration"]:
        apply_batting_result(batted_play["result"])


def draw_batted_ball():
    progress = min(1.0, (pygame.time.get_ticks() - batted_play["start"]) / batted_play["duration"])
    x, y, ground_x, ground_y, radius = batted_pose(progress)
    if batted_play["result"] != "HOMERUN" and ground_y >= FIELD_TOP:
        pygame.draw.ellipse(screen, DARK_GREEN, (round(ground_x - 9), round(ground_y - 3), 18, 6))
    for age in (0.075, 0.05, 0.025):
        if 0 <= progress - age and progress < 1:
            tx, ty, _, _, tr = batted_pose(progress - age)
            pygame.draw.circle(screen, (190, 205, 185), (round(tx), round(ty)), max(2, round(tr * 0.6)))
    pygame.draw.circle(screen, WHITE, (round(x), round(y)), round(radius))
    pygame.draw.circle(screen, RED, (round(x), round(y)), round(radius), 1)


def draw_ball():
    if batted_play is not None and game_state in ("BATTED", "RESULT", "READY"):
        draw_batted_ball()
        return
    if game_state == "READY" and last_pitch is None:
        return
    if game_state not in ("PITCHING", "RESULT", "READY"):
        return
    if game_state == "PITCHING":
        # 시간 기준 잔상으로 프레임 속도에 관계없이 일정한 길이를 유지한다.
        for age in (72, 54, 36, 18):
            earlier = pitch_progress - age / pitch_duration
            if earlier >= 0:
                x, y, radius = pitch_pose(earlier)
                color = (115, 155, 135) if age > 36 else (185, 205, 185)
                pygame.draw.circle(screen, color, (round(x), round(y)), max(2, round(radius * 0.7)))
    center = (round(ball_x), round(ball_y))
    radius = round(ball_radius)
    pygame.draw.circle(screen, (190, 195, 195), center, radius + 1)
    pygame.draw.circle(screen, WHITE, center, radius)
    if radius >= 7:
        spin = pitch_progress * math.tau * 3
        for offset in (0, math.pi):
            seam = pygame.Rect(center[0] - radius // 2, center[1] - radius * 3 // 4,
                               radius, radius * 3 // 2)
            pygame.draw.arc(screen, RED, seam, spin + offset, spin + offset + 1.6, 2)

def draw_pitch_label():
    if last_pitch is None or game_state not in ("BATTED", "RESULT", "READY"):
        return
    x, y, name = last_pitch
    pygame.draw.circle(screen, YELLOW, (round(x), round(y)), 20, 2)
    text = render_text(font_small, name, YELLOW)
    rect = text.get_rect(midtop=(round(x), round(y + ball_radius + 9)))
    pygame.draw.rect(screen, BLACK, rect.inflate(12, 6), border_radius=5)
    screen.blit(text, rect)


def start_with_enter():
    """엔터로 게임/다음 투구 시작. 비행 중 중복 입력은 무시한다."""
    if game_state in ("START", "GAME_OVER"):
        new_game(game_mode if game_state == "GAME_OVER" else "AI")
        return
    if game_mode == "PVP" and game_state == "READY":
        confirm_pitch()
    elif game_state == "HANDOFF" or (game_mode == "AI" and game_state in ("READY", "RESULT")):
        set_cursor_visible(False)
        start_windup()


# =========================================================
# 메시지
# =========================================================

def draw_message():
    # 점수판 오른쪽의 공간에 긴 진루 안내를 줄바꿈하여 표시한다.
    area = pygame.Rect(330, 25, WIDTH - 520, 145)
    lines = []
    line = ""
    for word in message.split():
        candidate = f"{line} {word}" if line else word
        if line and font_medium.size(candidate)[0] > area.width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    for index, line in enumerate(lines):
        text = render_text(font_medium, line, YELLOW)
        rect = text.get_rect(midtop=(area.centerx, area.top + index * (font_medium.get_linesize() + 4)))
        screen.blit(text, rect)

# =========================================================
# 도움말
# =========================================================

def draw_controls():

    if game_mode == "PVP":
        controls = (f"{pitcher_name()} 투구: 1/2/3 구종 · 클릭 목표 · 엔터/스페이스 준비 완료 · Esc 종료"
                    if game_state == "READY" else
                    f"{batter_name()} 타격: 마우스 조준 · 스페이스 스윙 · Esc 종료")
    else:
        controls = ("1: 직구  2: 커브  3: 슬라이더 | 클릭: 목표 지정 | 엔터/스페이스: 던지기 | Esc: 종료"
                    if is_player_pitching() else "엔터: 투구 시작    마우스: 조준    스페이스: 스윙    Esc: 종료")
    text = render_text(font_small, controls, WHITE)

    screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT - 22)))

# =========================================================
# 게임오버
# =========================================================

def draw_game_over():

    screen.fill(BLACK)

    set_cursor_visible(True)

    title = render_text(font_big, "경기 종료", WHITE)

    screen.blit(
        title,
        title.get_rect(
            center=(WIDTH // 2, 220)
        )
    )

    if game_mode == "PVP":
        winner = "P1 승리!" if score > ai_score else "P2 승리!" if score < ai_score else "무승부"
        score_label = f"P1 {score} : P2 {ai_score}  ·  {winner}"
    else:
        score_label = f"나 {score} : AI {ai_score}  ·  {'승리!' if score > ai_score else '패배' if score < ai_score else '무승부'}"
    score_text = render_text(font_medium, score_label, YELLOW)

    screen.blit(
        score_text,
        score_text.get_rect(
            center=(WIDTH // 2, 320)
        )
    )

    draw_button(
        start_button,
        "다시 시작 / 엔터"
    )

# =========================================================
# 메인 루프
# =========================================================

if __name__ == "__main__":
    running = True

    while running:

        now = pygame.time.get_ticks()

        # -----------------------------------------------------
        # 이벤트
        # -----------------------------------------------------

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                running = False
                continue

            if settings_open:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_F1):
                    close_settings()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if settings_close_button.collidepoint(event.pos):
                        close_settings()
                    elif speed_slider.inflate(0, 36).collidepoint(event.pos):
                        speed_dragging = True
                        set_pitch_speed_from_x(event.pos[0])
                elif event.type == pygame.MOUSEMOTION and speed_dragging:
                    set_pitch_speed_from_x(event.pos[0])
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    speed_dragging = False
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                open_settings()
                continue

            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and
                settings_button.collidepoint(event.pos)):
                open_settings()
                continue

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:

                    running = False

                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    start_with_enter()

                if ((game_mode == "PVP" and game_state == "READY") or
                    (game_mode == "AI" and game_state in ("READY", "RESULT") and is_player_pitching())):
                    selected_pitch = {pygame.K_1: "FASTBALL", pygame.K_2: "CURVE", pygame.K_3: "SLIDER"}.get(event.key, selected_pitch)

                # SPACE
                if event.key == pygame.K_SPACE:

                    # READY 상태에서는 투구 준비
                    if game_state == "READY":
                        if game_mode == "PVP":
                            confirm_pitch()
                        else:
                            start_windup()

                    elif game_state == "HANDOFF":

                        start_windup()

                    # 공이 날아오고 있으면 스윙
                    elif game_state == "PITCHING":

                        swing_bat()

            if event.type == pygame.MOUSEBUTTONDOWN:

                if event.button == 1:

                    # 시작 화면
                    if game_state == "START":

                        if start_button.collidepoint(
                            event.pos
                        ):

                            set_cursor_visible(False)

                            new_game()

                        elif pvp_button.collidepoint(event.pos):

                            new_game("PVP")

                    elif game_state == "HANDOFF":

                        if start_button.collidepoint(event.pos):
                            start_windup()

                    elif ((game_mode == "PVP" and game_state == "READY") or
                          (game_mode == "AI" and game_state in ("READY", "RESULT") and is_player_pitching())) and strike_zone.top - 65 < event.pos[1] < strike_zone.bottom + 75 and not pitch_button.collidepoint(event.pos):
                        pitch_aim = (max(40, min(WIDTH - 40, event.pos[0])),
                                     max(strike_zone.top - 50,
                                         min(strike_zone.bottom + 60, event.pos[1])))

                    # READY 버튼
                    elif game_state == "READY":

                        if pitch_button.collidepoint(
                            event.pos
                        ):
                            if game_mode == "PVP":
                                confirm_pitch()
                            else:
                                start_windup()

                    # 다시 시작
                    elif game_state == "GAME_OVER":

                        if start_button.collidepoint(
                            event.pos
                        ):

                            set_cursor_visible(False)

                            new_game(game_mode)

        # -----------------------------------------------------
        # 게임 상태 업데이트
        # -----------------------------------------------------

        if settings_open:

            pass

        elif game_state == "WINDUP":

            if (
                now - windup_start
                >= windup_duration
            ):

                start_pitch()

        elif game_state == "PITCHING":

            update_pitch()

        elif game_state == "BATTED":

            update_batted_ball()

        elif game_state == "RESULT":

            if (
                now - result_start
                >= result_duration
            ):

                prepare_next_half()
                if game_state != "GAME_OVER":
                    game_state = "READY"
                    message = ready_message()

        # -----------------------------------------------------
        # 화면 출력
        # -----------------------------------------------------

        if settings_open:

            screen.blit(settings_background, (0, 0))
            draw_settings()

        elif game_state == "START":

            set_cursor_visible(True)

            draw_start_screen()

        elif game_state == "HANDOFF":

            set_cursor_visible(True)
            draw_handoff_screen()

        elif game_state == "GAME_OVER":

            draw_game_over()

        else:

            set_cursor_visible(game_state == "READY" if game_mode == "PVP" else is_player_pitching())

            draw_field()
            draw_defenders()
            draw_bases()
            draw_home()
            draw_pitcher()
            draw_strike_zone()
            draw_scoreboard()
            draw_message()
            draw_controls()

            draw_ball()
            draw_foreground_batter()

            # 투구 버튼
            if game_state == "READY":

                button_text = "준비 완료" if game_mode == "PVP" else "투구 시작"
                enabled = True

            elif game_state == "WINDUP":

                button_text = "투구 준비 중..."
                enabled = False

            elif game_state == "PITCHING":

                button_text = "AI 타격 중" if game_mode == "AI" and is_player_pitching() else "스윙!"
                enabled = False

            else:

                button_text = "대기 중..."
                enabled = False

            draw_button(
                pitch_button,
                button_text,
                enabled
            )

            # 배트는 가장 마지막에 그림
            draw_bat()
            draw_pitch_label()
            if ((game_mode == "PVP" and game_state == "READY") or
                (game_mode == "AI" and is_player_pitching())):
                aim = locked_aim if game_state in ("WINDUP", "PITCHING") else pitch_aim
                pygame.draw.circle(screen, YELLOW, aim, 12, 2)
                pygame.draw.line(screen, YELLOW, (aim[0] - 18, aim[1]), (aim[0] + 18, aim[1]), 2)
                pygame.draw.line(screen, YELLOW, (aim[0], aim[1] - 18), (aim[0], aim[1] + 18), 2)
                name = locked_pitch if game_state in ("WINDUP", "PITCHING") else selected_pitch
                prefix = f"{pitcher_name()} 투구" if game_mode == "PVP" else "내 투구"
                label = render_text(font_medium, prefix + " · " + PITCH_NAMES[name], YELLOW)
                screen.blit(label, (40, HEIGHT - 100))

        if not settings_open:
            draw_button(settings_button, "설정")

        pygame.display.flip()

        clock.tick(60)

    pygame.quit()
    sys.exit()
