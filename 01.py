import pygame
import random
import sys
import math

pygame.init()

# =========================================================
# 기본 설정
# =========================================================

WIDTH = 1000
HEIGHT = 700

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("2D Baseball")

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

font_small = pygame.font.Font(None, 30)
font_medium = pygame.font.Font(None, 42)
font_big = pygame.font.Font(None, 70)

# =========================================================
# 버튼
# =========================================================

start_button = pygame.Rect(380, 450, 240, 80)
pitch_button = pygame.Rect(760, 590, 200, 70)

# =========================================================
# 스트라이크존
# =========================================================

strike_zone = pygame.Rect(
    425,
    310,
    150,
    180
)

# =========================================================
# 투수
# =========================================================

pitcher_x = 500
pitcher_y = 135

# =========================================================
# 공
# =========================================================

ball_x = pitcher_x
ball_y = pitcher_y

ball_start_x = pitcher_x
ball_start_y = pitcher_y

ball_target_x = 500
ball_target_y = 400

# =========================================================
# 배트 설정
# =========================================================

BAT_WIDTH = 150
BAT_HEIGHT = 22

HANDLE_WIDTH = 45

# 마우스 커서 숨김
pygame.mouse.set_visible(False)

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

    text_surface = font_medium.render(
        text,
        True,
        WHITE
    )

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

    title = font_big.render(
        "2D BASEBALL",
        True,
        WHITE
    )

    screen.blit(
        title,
        title.get_rect(
            center=(WIDTH // 2, 200)
        )
    )

    subtitle = font_medium.render(
        "3 INNING GAME",
        True,
        YELLOW
    )

    screen.blit(
        subtitle,
        subtitle.get_rect(
            center=(WIDTH // 2, 280)
        )
    )

    draw_button(
        start_button,
        "GAME START"
    )

# =========================================================
# 경기장
# =========================================================

def draw_field():

    screen.fill(GREEN)

    pygame.draw.polygon(
        screen,
        (170, 115, 65),
        [
            (500, 180),
            (750, 430),
            (500, 650),
            (250, 430)
        ]
    )

    pygame.draw.polygon(
        screen,
        DARK_GREEN,
        [
            (500, 240),
            (680, 430),
            (500, 590),
            (320, 430)
        ]
    )

# =========================================================
# 베이스
# =========================================================

def draw_base(x, y, active, name):

    size = 28

    points = [
        (x, y - size),
        (x + size, y),
        (x, y + size),
        (x - size, y)
    ]

    if active:
        color = YELLOW
    else:
        color = WHITE

    pygame.draw.polygon(
        screen,
        color,
        points
    )

    pygame.draw.polygon(
        screen,
        BLACK,
        points,
        2
    )

    text = font_small.render(
        name,
        True,
        WHITE
    )

    screen.blit(
        text,
        text.get_rect(
            center=(x, y + 50)
        )
    )


def draw_bases():

    draw_base(
        680,
        430,
        base1,
        "1B"
    )

    draw_base(
        500,
        250,
        base2,
        "2B"
    )

    draw_base(
        320,
        430,
        base3,
        "3B"
    )

# =========================================================
# 홈
# =========================================================

def draw_home():

    points = [
        (480, 610),
        (520, 610),
        (530, 625),
        (500, 650),
        (470, 625)
    ]

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

    text = font_small.render(
        "STRIKE ZONE",
        True,
        WHITE
    )

    screen.blit(
        text,
        (
            strike_zone.x,
            strike_zone.y - 30
        )
    )

# =========================================================
# 투수
# =========================================================

def draw_pitcher():

    x = pitcher_x
    y = pitcher_y

    now = pygame.time.get_ticks()

    arm_angle = 0
    leg_offset = 0

    if game_state == "WINDUP":

        progress = (
            now - windup_start
        ) / windup_duration

        progress = max(
            0,
            min(1, progress)
        )

        arm_angle = (
            math.sin(progress * math.pi)
            * 80
        )

        leg_offset = (
            math.sin(progress * math.pi)
            * 25
        )

    # 머리
    pygame.draw.circle(
        screen,
        (230, 190, 150),
        (int(x), int(y)),
        17
    )

    # 몸
    pygame.draw.line(
        screen,
        BLUE,
        (x, y + 17),
        (x, y + 65),
        12
    )

    # 다리
    pygame.draw.line(
        screen,
        WHITE,
        (x, y + 65),
        (x - 20, y + 100),
        8
    )

    pygame.draw.line(
        screen,
        WHITE,
        (x, y + 65),
        (
            x + 20,
            y + 100 - leg_offset
        ),
        8
    )

    # 팔
    arm_length = 45

    angle = math.radians(
        45 - arm_angle
    )

    arm_x = (
        x
        + math.cos(angle)
        * arm_length
    )

    arm_y = (
        y
        + 30
        + math.sin(angle)
        * arm_length
    )

    pygame.draw.line(
        screen,
        RED,
        (x, y + 30),
        (
            int(arm_x),
            int(arm_y)
        ),
        8
    )

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

    if game_state not in [
        "READY",
        "WINDUP",
        "PITCHING",
        "RESULT"
    ]:
        return

    bat = get_bat_rect()

    # 손잡이
    handle_rect = pygame.Rect(
        bat.left,
        bat.top + 4,
        HANDLE_WIDTH,
        BAT_HEIGHT - 8
    )

    pygame.draw.rect(
        screen,
        BROWN,
        handle_rect,
        border_radius=5
    )

    # 배트 몸통
    body_rect = pygame.Rect(
        bat.left + HANDLE_WIDTH,
        bat.top,
        BAT_WIDTH - HANDLE_WIDTH,
        BAT_HEIGHT
    )

    pygame.draw.rect(
        screen,
        LIGHT_BROWN,
        body_rect,
        border_radius=10
    )

    # 중심 표시
    sweet_x = (
        bat.left
        + HANDLE_WIDTH
        + (
            BAT_WIDTH
            - HANDLE_WIDTH
        ) // 2
    )

    pygame.draw.line(
        screen,
        YELLOW,
        (sweet_x, bat.top),
        (sweet_x, bat.bottom),
        3
    )

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
            f"INNING {inning} / 3",
            WHITE,
            40,
            35
        ),
        (
            f"BALL    {balls}",
            (100, 255, 100),
            40,
            85
        ),
        (
            f"STRIKE  {strikes}",
            YELLOW,
            40,
            112
        ),
        (
            f"OUT     {outs}",
            RED,
            40,
            139
        ),
        (
            f"SCORE {score}",
            WHITE,
            170,
            139
        )
    ]

    for text, color, x, y in texts:

        img = font_small.render(
            text,
            True,
            color
        )

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
                330,
                670
            )

            y = random.randint(
                270,
                550
            )

            if not strike_zone.collidepoint(
                x,
                y
            ):
                break

    # 10% 완전 랜덤
    else:

        x = random.randint(
            330,
            670
        )

        y = random.randint(
            270,
            550
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
            message = "GAME OVER"

            return True

        else:

            message = "CHANGE INNING"

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

def hit_single():

    global base1
    global base2
    global base3
    global score

    old1 = base1
    old2 = base2
    old3 = base3

    # 3루 → 홈
    if old3:
        score += 1

    base3 = old2
    base2 = old1
    base1 = True


def hit_double():

    global base1
    global base2
    global base3
    global score

    old1 = base1
    old2 = base2
    old3 = base3

    # 2루, 3루 주자 득점
    if old3:
        score += 1

    if old2:
        score += 1

    # 1루 → 3루
    base3 = old1

    # 타자 → 2루
    base2 = True

    base1 = False


def hit_triple():

    global base1
    global base2
    global base3
    global score

    if base1:
        score += 1

    if base2:
        score += 1

    if base3:
        score += 1

    base1 = False
    base2 = False
    base3 = True


def hit_homerun():

    global base1
    global base2
    global base3
    global score

    runs = 1

    if base1:
        runs += 1

    if base2:
        runs += 1

    if base3:
        runs += 1

    score += runs

    base1 = False
    base2 = False
    base3 = False

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
                "3B RUNNER SCORED"
            )

        else:

            base3 = True

            extra_messages.append(
                "3B RUNNER HELD"
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
                    "2B RUNNER TO 3B"
                )

            else:

                base2 = True

                extra_messages.append(
                    "2B RUNNER HELD"
                )

    if extra_messages:

        message = "FLY OUT / " + " / ".join(
            extra_messages
        )

    else:

        message = "FLY OUT"

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

            add_outs(2)

            if game_state != "GAME_OVER":
                message = "DOUBLE PLAY!"

            return

    # 일반 땅볼 아웃
    add_outs(1)

    if game_state != "GAME_OVER":
        message = "GROUND OUT"

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

        elif roll < 25:
            return "TRIPLE"

        elif roll < 25:
            return "HOMERUN"

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
        message = "SINGLE!"

    elif result == "DOUBLE":

        hit_double()
        message = "DOUBLE!"

    elif result == "TRIPLE":

        hit_triple()
        message = "TRIPLE!"

    elif result == "HOMERUN":

        hit_homerun()
        message = "HOME RUN!"

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

    global swung
    global strikes
    global message
    global game_state
    global result_start

    if game_state != "PITCHING":
        return

    if swung:
        return

    swung = True

    bat = get_bat_rect()

    # 공 충돌 범위
    ball_rect = pygame.Rect(
        int(ball_x) - 10,
        int(ball_y) - 10,
        20,
        20
    )

    # 배트에 공이 맞음
    if bat.colliderect(ball_rect):

        # 공이 배트의 어느 위치에 맞았는지
        relative_x = (
            ball_x - bat.left
        )

        # 손잡이 부분
        if relative_x <= HANDLE_WIDTH:

            contact = "HANDLE"
            message = "HANDLE CONTACT!"

        else:

            contact = "CENTER"
            message = "GOOD CONTACT!"

        result = choose_batting_result(
            contact
        )

        apply_batting_result(
            result
        )

    # 헛스윙
    else:

        strikes += 1

        if strikes >= 3:

            message = "SWING STRIKE OUT!"

            add_outs(1)

        else:

            message = "SWING STRIKE!"

        if game_state != "GAME_OVER":

            game_state = "RESULT"

            result_start = pygame.time.get_ticks()

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

        message = "CALLED STRIKE!"

        if strikes >= 3:

            message = "STRIKE OUT!"

            add_outs(1)

    else:

        balls += 1

        message = "BALL!"

        if balls >= 4:

            walk_batter()

            reset_count()

            message = "WALK!"

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

    inning = 1

    balls = 0
    strikes = 0
    outs = 0

    score = 0

    base1 = False
    base2 = False
    base3 = False

    swung = False

    message = "PRESS READY"

    game_state = "READY"

# =========================================================
# 와인드업
# =========================================================

def start_windup():

    global game_state
    global windup_start
    global message
    global swung

    swung = False

    game_state = "WINDUP"

    windup_start = pygame.time.get_ticks()

    message = "PITCHER WINDUP..."

# =========================================================
# 투구 시작
# =========================================================

def start_pitch():

    global game_state
    global pitch_start

    global ball_start_x
    global ball_start_y

    global ball_target_x
    global ball_target_y

    global ball_x
    global ball_y

    global message
    global swung

    swung = False

    ball_start_x = pitcher_x
    ball_start_y = pitcher_y + 30

    ball_x = ball_start_x
    ball_y = ball_start_y

    ball_target_x, ball_target_y = (
        choose_pitch_target()
    )

    pitch_start = pygame.time.get_ticks()

    game_state = "PITCHING"

    message = "PITCH!"

# =========================================================
# 공 이동
# =========================================================

def update_pitch():

    global ball_x
    global ball_y

    now = pygame.time.get_ticks()

    progress = (
        now - pitch_start
    ) / pitch_duration

    if progress >= 1:

        ball_x = ball_target_x
        ball_y = ball_target_y

        # 스윙하지 않았다면 자동 판정
        if not swung:
            judge_pitch()

        return

    # 부드러운 이동
    smooth = (
        progress
        * progress
        * (3 - 2 * progress)
    )

    ball_x = (
        ball_start_x
        + (
            ball_target_x
            - ball_start_x
        )
        * smooth
    )

    ball_y = (
        ball_start_y
        + (
            ball_target_y
            - ball_start_y
        )
        * smooth
    )

# =========================================================
# 메시지
# =========================================================

def draw_message():

    text = font_medium.render(
        message,
        True,
        YELLOW
    )

    rect = text.get_rect(
        center=(
            WIDTH // 2,
            60
        )
    )

    screen.blit(
        text,
        rect
    )

# =========================================================
# 도움말
# =========================================================

def draw_controls():

    text = font_small.render(
        "MOVE MOUSE = BAT    SPACE = SWING",
        True,
        WHITE
    )

    screen.blit(
        text,
        (
            335,
            665
        )
    )

# =========================================================
# 게임오버
# =========================================================

def draw_game_over():

    screen.fill(BLACK)

    pygame.mouse.set_visible(True)

    title = font_big.render(
        "GAME OVER",
        True,
        WHITE
    )

    screen.blit(
        title,
        title.get_rect(
            center=(WIDTH // 2, 220)
        )
    )

    score_text = font_medium.render(
        f"SCORE : {score}",
        True,
        YELLOW
    )

    screen.blit(
        score_text,
        score_text.get_rect(
            center=(WIDTH // 2, 320)
        )
    )

    draw_button(
        start_button,
        "PLAY AGAIN"
    )

# =========================================================
# 메인 루프
# =========================================================

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

                        pygame.mouse.set_visible(False)

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

                        pygame.mouse.set_visible(False)

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

    elif game_state == "RESULT":

        if (
            now - result_start
            >= result_duration
        ):

            game_state = "READY"

            message = "PRESS READY"

    # -----------------------------------------------------
    # 화면 출력
    # -----------------------------------------------------

    if game_state == "START":

        pygame.mouse.set_visible(True)

        draw_start_screen()

    elif game_state == "GAME_OVER":

        draw_game_over()

    else:

        pygame.mouse.set_visible(False)

        draw_field()
        draw_bases()
        draw_home()
        draw_strike_zone()
        draw_pitcher()
        draw_scoreboard()
        draw_message()
        draw_controls()

        # 공
        if game_state == "PITCHING":

            pygame.draw.circle(
                screen,
                WHITE,
                (
                    int(ball_x),
                    int(ball_y)
                ),
                11
            )

            pygame.draw.circle(
                screen,
                RED,
                (
                    int(ball_x),
                    int(ball_y)
                ),
                11,
                2
            )

        elif game_state == "RESULT":

            pygame.draw.circle(
                screen,
                WHITE,
                (
                    int(ball_x),
                    int(ball_y)
                ),
                11
            )

        # 투구 버튼
        if game_state == "READY":

            button_text = "READY / PITCH"
            enabled = True

        elif game_state == "WINDUP":

            button_text = "WINDUP..."
            enabled = False

        elif game_state == "PITCHING":

            button_text = "SWING!"
            enabled = False

        else:

            button_text = "WAIT..."
            enabled = False

        draw_button(
            pitch_button,
            button_text,
            enabled
        )

        # 배트는 가장 마지막에 그림
        draw_bat()

    pygame.display.flip()

    clock.tick(60)

pygame.quit()
sys.exit()
