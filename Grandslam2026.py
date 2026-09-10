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
FIELD_TOP = 225
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
pitch_button = pygame.Rect(WIDTH - 280, HEIGHT - 110, 240, 70)

# =========================================================
# 스트라이크존
# =========================================================

strike_zone = pygame.Rect(
    WIDTH // 2 - 75,
    520,
    150,
    180
)

# =========================================================
# 투수
# =========================================================

pitcher_x = WIDTH // 2
pitcher_y = 420
PITCHER_SCALE = 0.65

# 타석에서 바라본 베이스 위치 (중심 x, 발이 닿는 y, 원근 크기)
BASE_LAYOUT = {
    "1B": (1030, 580, 1.0),
    "2B": (WIDTH // 2, 390, 0.65),
    "3B": (250, 580, 1.0),
}
HOME_POSITION = (WIDTH // 2, HEIGHT - 75)

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
SWING_DURATION = 520
SWING_FOLLOW_END = 0.62
SWING_HOLD_END = 0.80
swing_started = None
swing_origin = None
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

# START
# READY
# WINDUP
# PITCHING
# RESULT
# GAME_OVER

inning = 1

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
CONTACT_START = 0.78  # 공이 타석 가까이 온 마지막 구간에서만 타격 가능.

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

    subtitle = render_text(font_medium, "3이닝 경기", YELLOW)

    screen.blit(
        subtitle,
        subtitle.get_rect(
            center=(WIDTH // 2, 280)
        )
    )

    draw_button(
        start_button,
        "시작 / 엔터"
    )

# =========================================================
# 경기장
# =========================================================

field_surface = None


def draw_field():
    global field_surface

    if field_surface is None:
        field_surface = pygame.Surface((WIDTH, HEIGHT)).convert()
        field_surface.fill((105, 175, 220))
        # 점수판 아래에서 경기장이 시작되어 외야수를 가리지 않는다.
        pygame.draw.rect(field_surface, DARK_GREEN, (0, FIELD_TOP - 40, WIDTH, 40))
        pygame.draw.line(field_surface, YELLOW, (0, FIELD_TOP - 40), (WIDTH, FIELD_TOP - 40), 4)
        pygame.draw.rect(field_surface, GREEN, (0, FIELD_TOP, WIDTH, HEIGHT - FIELD_TOP))
        for y in range(FIELD_TOP + 35, HEIGHT, 85):
            pygame.draw.rect(field_surface, (32, 120, 60), (0, y, WIDTH, 30))

        first = BASE_LAYOUT["1B"][:2]
        second = BASE_LAYOUT["2B"][:2]
        third = BASE_LAYOUT["3B"][:2]
        diamond = [HOME_POSITION, first, second, third]
        pygame.draw.polygon(field_surface, (170, 115, 65), diamond)
        center = (WIDTH // 2, first[1])
        inner = [(round(center[0] + (x - center[0]) * 0.84),
                  round(center[1] + (y - center[1]) * 0.84)) for x, y in diamond]
        pygame.draw.polygon(field_surface, GREEN, inner)
        # 베이스 위치에서 파울 라인을 계산해 화면 확장에도 일치시킨다.
        hx, hy = HOME_POSITION
        for bx, by in (first, third):
            factor = (hy - FIELD_TOP) / (hy - by)
            end = (round(hx + (bx - hx) * factor), FIELD_TOP)
            pygame.draw.line(field_surface, WHITE, HOME_POSITION, end, 3)
        feet_y = round(pitcher_y + 100 * PITCHER_SCALE)
        pygame.draw.ellipse(field_surface, LIGHT_BROWN, (pitcher_x - 48, feet_y - 17, 96, 30))
        pygame.draw.rect(field_surface, WHITE, (pitcher_x - 14, feet_y - 6, 28, 5))
        pygame.draw.ellipse(field_surface, (170, 115, 65), (hx - 78, hy - 49, 156, 80))

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
    text = render_text(font_small, name, WHITE)
    label_x = x - 42 if name == "2B" else x
    screen.blit(text, text.get_rect(center=(label_x, y + depth + 18)))


def draw_bases():
    for name, active in (("2B", base2), ("3B", base3), ("1B", base1)):
        x, y, scale = BASE_LAYOUT[name]
        draw_base(x, y, active, name, scale)

# 투수와 별도로 내야수 4명, 외야수 3명.
def defender_positions():
    second_x, second_y, _ = BASE_LAYOUT["2B"]

    def corner_position(name, occupied):
        x, y, _ = BASE_LAYOUT[name]
        # 주자가 있으면 1·3루에서 2루 방향의 페어 지역으로 물러선다.
        fraction = 0.23 if occupied else 0.08
        return (round(x + (second_x - x) * fraction),
                round(y + (second_y - y) * fraction), 0.85)

    return {
        "LF": (360, 330, 0.55),
        "CF": (WIDTH // 2, 280, 0.43),
        "RF": (WIDTH - 360, 330, 0.55),
        "SS": (470, 480, 0.70),
        "2B": (710, 420, 0.65) if base2 else (810, 480, 0.70),
        "3B": corner_position("3B", base3),
        "1B": corner_position("1B", base1),
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
        label = render_text(font_small, name, (185, 215, 255))
        screen.blit(label, label.get_rect(midtop=(x, y + 5)))


# =========================================================
# 홈
# =========================================================

def draw_home():

    x, y = HOME_POSITION
    points = [(x - 20, y - 15), (x + 20, y - 15),
              (x + 30, y), (x, y + 25), (x - 30, y)]

    pygame.draw.polygon(
        screen,
        WHITE,
        points
    )

# =========================================================
# 스트라이크존
# =========================================================

def draw_strike_zone():

    pygame.draw.rect(
        screen,
        WHITE,
        strike_zone,
        3
    )

    text = render_text(font_small, "스트라이크 존", WHITE)

    screen.blit(
        text,
        (
            strike_zone.x,
            strike_zone.bottom + 12
        )
    )

# =========================================================
# 투수
# =========================================================

def draw_pitcher():
    def point(dx, dy):
        return (round(pitcher_x + dx * PITCHER_SCALE),
                round(pitcher_y + dy * PITCHER_SCALE))

    progress = 0
    if game_state == "WINDUP":
        progress = max(0, min(1, (pygame.time.get_ticks() - windup_start) / windup_duration))
    motion = math.sin(progress * math.pi)
    angle = math.radians(45 - motion * 80)

    pygame.draw.circle(screen, (230, 190, 150), point(0, 0), 11)
    pygame.draw.line(screen, BLUE, point(-15, -8), point(15, -8), 6)
    pygame.draw.line(screen, BLUE, point(0, 17), point(0, 65), 11)
    pygame.draw.line(screen, WHITE, point(0, 65), point(-20, 100), 6)
    pygame.draw.line(screen, WHITE, point(0, 65), point(20, 100 - motion * 25), 6)
    pygame.draw.line(screen, BLUE, point(0, 30), point(-26, 52), 6)
    pygame.draw.circle(screen, BROWN, point(-26, 52), 7)
    pygame.draw.line(screen, RED, point(0, 30),
                     point(math.cos(angle) * 45, 30 + math.sin(angle) * 45), 6)

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


@lru_cache(maxsize=1)
def bat_image():
    surface = pygame.Surface((BAT_WIDTH, BAT_HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(surface, BROWN, (0, 4, HANDLE_WIDTH, BAT_HEIGHT - 8), border_radius=5)
    pygame.draw.rect(surface, LIGHT_BROWN,
                     (HANDLE_WIDTH, 0, BAT_WIDTH - HANDLE_WIDTH, BAT_HEIGHT), border_radius=10)
    sweet_x = HANDLE_WIDTH + (BAT_WIDTH - HANDLE_WIDTH) // 2
    pygame.draw.line(surface, YELLOW, (sweet_x, 0), (sweet_x, BAT_HEIGHT), 3)
    return surface


def swing_extension(progress):
    progress = max(0.0, min(1.0, progress))
    if progress <= SWING_FOLLOW_END:
        t = progress / SWING_FOLLOW_END
        return t * t * (3 - 2 * t)
    if progress <= SWING_HOLD_END:
        return 1.0
    t = (progress - SWING_HOLD_END) / (1 - SWING_HOLD_END)
    return 1 - t * t * (3 - 2 * t)


def projected_bat(progress, origin, target):
    """수평 회전 180도에 상승 궤적을 더한 어퍼스윙을 원근 투영한다."""
    extension = swing_extension(progress)
    anchor = pygame.Vector2(origin)
    if progress > SWING_HOLD_END:
        t = min(1.0, (progress - SWING_HOLD_END) / (1 - SWING_HOLD_END))
        anchor = anchor.lerp(target, t * t * (3 - 2 * t))
    yaw = math.pi * extension
    # 초반에는 낮게 진입하고, 후반에는 손과 배트 끝을 함께 높이 올린다.
    anchor += pygame.Vector2(30 * math.sin(yaw) - 20 * extension,
                             18 * math.sin(yaw) - 60 * extension ** 2)
    lift = extension * extension * (3 - 2 * extension)
    direction = pygame.Vector2(math.cos(yaw),
                               0.25 * math.sin(2 * yaw) - 0.95 * lift)
    normal = pygame.Vector2(-direction.y, direction.x).normalize()

    def project(distance, width=0):
        depth = 30 * extension + max(0, distance) * math.sin(yaw)
        scale = 320 / (320 + depth)
        center = anchor + direction * distance * scale
        return center + normal * width * scale

    def outline(profile):
        return ([project(distance, -width) for distance, width in profile] +
                [project(distance, width) for distance, width in reversed(profile)])

    handle = outline([(-12, 4), (-8, 7), (HANDLE_WIDTH - 12, 7)])
    body = outline([(HANDLE_WIDTH - 12, 7), (HANDLE_WIDTH - 5, 11),
                    (BAT_WIDTH - 20, 11), (BAT_WIDTH - 12, 6)])
    sweet = HANDLE_WIDTH + (BAT_WIDTH - HANDLE_WIDTH) // 2 - 12
    return handle, body, (project(sweet, -11), project(sweet, 11)), project


def draw_projected_bat(progress, origin, target, alpha):
    handle, body, sweet, project = projected_bat(progress, origin, target)
    points = handle + body
    left = math.floor(min(p.x for p in points)) - 3
    top = math.floor(min(p.y for p in points)) - 3
    width = math.ceil(max(p.x for p in points)) - left + 4
    height = math.ceil(max(p.y for p in points)) - top + 4
    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    def local(point):
        return round(point.x - left), round(point.y - top)

    pygame.draw.polygon(surface, BROWN, [local(p) for p in handle])
    pygame.draw.polygon(surface, LIGHT_BROWN, [local(p) for p in body])
    # 배트 윗면에 밝은 선을 넣어 둥근 입체감을 표현한다.
    pygame.draw.line(surface, (235, 180, 110), local(project(HANDLE_WIDTH, -6)),
                     local(project(BAT_WIDTH - 23, -6)), 2)
    pygame.draw.line(surface, YELLOW, local(sweet[0]), local(sweet[1]), 2)
    surface.set_alpha(alpha)
    screen.blit(surface, (left, top))


def draw_bat():
    if game_state not in ("READY", "WINDUP", "PITCHING", "BATTED", "RESULT"):
        return
    elapsed = pygame.time.get_ticks() - swing_started if swing_started is not None else SWING_DURATION
    animating = 0 <= elapsed < SWING_DURATION
    if game_state == "BATTED" and not animating:
        return
    if not animating:
        screen.blit(bat_image(), get_bat_rect())
        return

    bat = get_bat_rect()
    target = (bat.left + 12, bat.centery)
    # 잔상도 각 시점의 손 이동과 원근 효과를 포함한다.
    for age, alpha in ((42, 40), (21, 75), (0, 255)):
        if elapsed >= age:
            draw_projected_bat((elapsed - age) / SWING_DURATION, swing_origin, target, alpha)

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
            f"이닝 {inning} / 3",
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
            f"점수 {score}",
            WHITE,
            170,
            139
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

def add_outs(amount=1):

    global outs
    global inning

    global base1
    global base2
    global base3

    global game_state
    global message

    outs += amount

    reset_count()

    if outs >= 3:

        outs = 0

        base1 = False
        base2 = False
        base3 = False

        inning += 1

        if inning > 3:

            game_state = "GAME_OVER"
            message = "경기 종료"

            return True

        else:

            message = "다음 이닝"

        return True

    return False

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

        score += 1

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
                score += 1
            else:
                runners[destination - 1] = True

    if bases == 4:
        score += 1
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

            score += 1
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

    if game_state != "PITCHING" or swung:
        return
    # 이벤트 시점의 위치로 판정하여 이전 프레임 좌표를 사용하지 않는다.
    update_pitch()
    if game_state != "PITCHING":
        return

    swung = True
    bat = get_bat_rect()
    swing_started = pygame.time.get_ticks()
    swing_origin = (bat.left + 12, bat.centery)
    nearest_x = max(bat.left, min(ball_x, bat.right))
    nearest_y = max(bat.top, min(ball_y, bat.bottom))
    touching = (ball_x - nearest_x) ** 2 + (ball_y - nearest_y) ** 2 <= ball_radius ** 2

    if pitch_progress >= CONTACT_START and touching:
        contact = "HANDLE" if ball_x - bat.left <= HANDLE_WIDTH else "CENTER"
        pending_swing_result = choose_batting_result(contact)
        message = "정타!" if contact == "CENTER" else "손잡이에 맞았습니다!"
    else:
        pending_swing_result = "MISS"
        message = "스윙이 너무 빠릅니다!" if pitch_progress < CONTACT_START else "스윙!"
    # 판정만 저장한다. 타구 결과/삼진/게임 종료는 공이 도착한 뒤 반영한다.


def finish_pitch():
    global strikes, message, game_state, result_start, pending_swing_result

    global last_pitch

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

def new_game():

    global inning
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

    message = "엔터를 눌러 투구 시작"

    game_state = "READY"

# =========================================================
# 와인드업
# =========================================================

def start_windup():

    global game_state
    global windup_start
    global message
    global swung
    global last_pitch, batted_play, swing_started, swing_origin

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
    # 와인드업 마지막 자세의 던지는 손에서 출발한다.
    ball_start_x = pitcher_x + math.cos(math.radians(45)) * 45 * PITCHER_SCALE
    ball_start_y = pitcher_y + (30 + math.sin(math.radians(45)) * 45) * PITCHER_SCALE
    ball_target_x, ball_target_y = choose_pitch_target()
    pitch_type, pitch_duration, pitch_break_x, pitch_drop = random.choice(PITCH_TYPES)
    ball_x, ball_y, ball_radius = pitch_pose(0)
    pitch_start = pygame.time.get_ticks()
    game_state = "PITCHING"
    message = "투구!"


def pitch_pose(progress):
    """원근 투영: 가까워질수록 공 크기와 화면상 이동 속도가 증가한다."""
    progress = max(0.0, min(1.0, progress))
    depth = progress / (3.0 - 2.0 * progress)
    bend = math.sin(math.pi * progress) * depth
    x = ball_start_x + (ball_target_x - ball_start_x) * depth + pitch_break_x * bend
    y = ball_start_y + (ball_target_y - ball_start_y) * depth - pitch_drop * bend
    radius = 4 + 14 * depth
    # 끝점은 구종과 관계없이 정해진 투구 위치에 정확히 일치한다.
    if progress >= 1:
        return float(ball_target_x), float(ball_target_y), radius
    return x, y, radius


def update_pitch():
    global ball_x, ball_y, ball_radius, pitch_progress

    if game_state != "PITCHING":
        return
    pitch_progress = max(0.0, min(1.0, (pygame.time.get_ticks() - pitch_start) / pitch_duration))
    ball_x, ball_y, ball_radius = pitch_pose(pitch_progress)
    if pitch_progress >= 1:
        finish_pitch()


def start_batted_ball(result):
    global batted_play, game_state, message

    # 지면상 경로와 공 높이를 따로 계산해 내야 통과/낙하/뜬공을 표현한다.
    home = HOME_POSITION
    side = random.choice((-1, 1))
    center_x = WIDTH // 2
    fielders = defender_positions()
    if result == "SINGLE":
        if random.random() < 0.5:
            # 유격수-3루수 또는 2루수-1루수 사이를 지나는 땅볼.
            corner = fielders["3B" if side < 0 else "1B"]
            middle = fielders["SS" if side < 0 else "2B"]
            gap = (round((corner[0] + middle[0]) / 2), round((corner[1] + middle[1]) / 2))
            # 홈→내야수 사이의 방향을 그대로 연장한다.
            # 중간 제어점을 없애 통과 후 방향이나 속도가 꺾이지 않게 한다.
            end_y = 410
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
    message = "홈런!" if result == "HOMERUN" else "타구가 날아갑니다!"


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
        new_game()
    if game_state in ("READY", "RESULT"):
        set_cursor_visible(False)
        start_windup()


# =========================================================
# 메시지
# =========================================================

def draw_message():
    # 점수판 오른쪽의 공간에 긴 진루 안내를 줄바꿈하여 표시한다.
    area = pygame.Rect(330, 25, WIDTH - 350, 145)
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

    text = render_text(font_small, "엔터: 투구 시작    마우스: 조준    스페이스: 스윙    이스케이프: 종료", WHITE)

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

    score_text = render_text(font_medium, f"최종 점수: {score}", YELLOW)

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

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:

                    running = False

                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    start_with_enter()

                # SPACE
                if event.key == pygame.K_SPACE:

                    # READY 상태에서는 투구 준비
                    if game_state == "READY":

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

                    # READY 버튼
                    elif game_state == "READY":

                        if pitch_button.collidepoint(
                            event.pos
                        ):

                            start_windup()

                    # 다시 시작
                    elif game_state == "GAME_OVER":

                        if start_button.collidepoint(
                            event.pos
                        ):

                            set_cursor_visible(False)

                            new_game()

        # -----------------------------------------------------
        # 게임 상태 업데이트
        # -----------------------------------------------------

        if game_state == "WINDUP":

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

                game_state = "READY"

                message = "엔터를 눌러 투구 시작"

        # -----------------------------------------------------
        # 화면 출력
        # -----------------------------------------------------

        if game_state == "START":

            set_cursor_visible(True)

            draw_start_screen()

        elif game_state == "GAME_OVER":

            draw_game_over()

        else:

            set_cursor_visible(False)

            draw_field()
            draw_defenders()
            draw_bases()
            draw_home()
            draw_strike_zone()
            draw_pitcher()
            draw_scoreboard()
            draw_message()
            draw_controls()

            draw_ball()

            # 투구 버튼
            if game_state == "READY":

                button_text = "투구 시작"
                enabled = True

            elif game_state == "WINDUP":

                button_text = "투구 준비 중..."
                enabled = False

            elif game_state == "PITCHING":

                button_text = "스윙!"
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

        pygame.display.flip()

        clock.tick(60)

    pygame.quit()
    sys.exit()
