import json
import math
import os
import random
import array
import pygame
pygame.mixer.pre_init(22050, -16, 1, 512)

pygame.init()

# ------------------------------------------------------------
# 1) 화면 / 글씨체 설정
# ------------------------------------------------------------
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.RESIZABLE)
pygame.display.set_caption("SURVIVOR: 끝없는 던전")
clock = pygame.time.Clock()
world = pygame.Surface((WIDTH, HEIGHT))  # 게임 화면을 여기에 그린 뒤 흔들어서 붙여요 (화면 흔들림용)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "fonts", "neodgm.ttf")
SYS_FONTS = "malgungothic,applegothic,nanumgothic,notosanscjkkr,notosanscjk,arial"


def load_font(size, sys_size):
    """fonts/neodgm.ttf가 있으면 그걸, 없으면 시스템 한글 굵은 글씨를 써요."""
    if os.path.exists(FONT_PATH):
        return pygame.font.Font(FONT_PATH, size)
    return pygame.font.SysFont(SYS_FONTS, sys_size, bold=False)


def outline_surface(base, px, color):
    """글씨 이미지 둘레에 외곽선을 둘러서 어떤 배경에서도 또렷하게 만들어요."""
    w, h = base.get_size()
    dark = base.copy()
    dark.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MIN)  # 색은 검게, 모양(투명도)은 그대로
    dark.fill((color[0], color[1], color[2], 0), special_flags=pygame.BLEND_RGBA_ADD)  # 외곽선 색 입히기
    out = pygame.Surface((w + 2 * px, h + 2 * px + 1), pygame.SRCALPHA)
    for dx in range(-px, px + 1):
        for dy in range(-px, px + 1):
            if (dx or dy) and dx * dx + dy * dy <= px * px + 1:
                out.blit(dark, (px + dx, px + dy + 1))  # 아래쪽으로 살짝 더 깔아 입체감
    out.blit(base, (px, px))
    return out


class OutlineFont:
    """render()만 바꿔치기한 글꼴. 기존 코드는 그대로 두고 모든 글씨에 외곽선이 생겨요."""

    def __init__(self, f, px=2):
        self.f, self.px, self.cache = f, px, {}

    def render(self, text, aa, color):
        key = (text, tuple(color))
        s = self.cache.get(key)
        if s is None:
            if len(self.cache) > 600:
                self.cache.clear()
            s = outline_surface(self.f.render(text, True, color), self.px, (14, 12, 30))
            self.cache[key] = s
        return s

    def get_linesize(self):
        return self.f.get_linesize()

    def size(self, text):
        return self.f.size(text)


font = OutlineFont(load_font(44, 42), 2)
small_font = OutlineFont(load_font(28, 22), 1)
tiny_font = OutlineFont(load_font(16, 16), 1)  # 데미지 숫자용

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def make_stone_title(text, size, top=(190, 184, 172), bottom=(92, 88, 84), seed=3, moss=False):
    """진짜 돌에 새긴 글씨: 겹친 질감 + 입체 모서리 + 균열 + 구멍 + 이끼 + 두께감."""
    base = load_font(size, int(size * 0.9)).render(text, True, (255, 255, 255))
    w, h = base.get_size()
    rng = random.Random(seed)

    # 1) 돌 질감: 큰 덩어리 + 중간 + 잔 알갱이 노이즈를 겹쳐요
    layers = []
    for cell, amp in ((16, 34), (6, 22), (2, 16)):
        sw, sh = max(2, w // cell), max(2, h // cell)
        n = pygame.Surface((sw, sh), 0, 24)
        for x in range(sw):
            for y in range(sh):
                v = rng.randint(0, 255)
                n.set_at((x, y), (v, v, v))
        layers.append((pygame.transform.smoothscale(n, (w, h)), amp))
    stone = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        gc = lerp_color(top, bottom, y / max(1, h - 1))
        for x in range(w):
            d = sum((n.get_at((x, y))[0] - 128) / 128 * amp for n, amp in layers)
            stone.set_at((x, y), (*[max(0, min(255, int(c + d))) for c in gc], 255))

    # 2) 균열: 어두운 틈 + 아래쪽 밝은 선 + 가지
    for _ in range(max(4, w // 45)):
        x, y = rng.randrange(w), rng.randrange(h // 2)
        for _ in range(rng.randint(3, 5)):
            nx, ny = x + rng.randint(-7, 7), y + rng.randint(4, 11)
            pygame.draw.line(stone, (210, 205, 195), (x + 1, y + 1), (nx + 1, ny + 1), 1)
            pygame.draw.line(stone, (22, 18, 26), (x, y), (nx, ny), 1)
            if rng.random() < 0.25:
                pygame.draw.line(stone, (22, 18, 26), (nx, ny), (nx + rng.randint(-8, 8), ny + rng.randint(2, 7)), 1)
            x, y = nx, ny

    # 3) 움푹 팬 구멍 (어두운 점 + 아래쪽 밝은 점)
    for _ in range(w * h // 260):
        x, y = rng.randrange(1, w - 2), rng.randrange(1, h - 3)
        pygame.draw.rect(stone, (40, 36, 42), (x, y, 2, 2))
        pygame.draw.line(stone, (200, 195, 185), (x, y + 2), (x + 1, y + 2))

    # 4) 이끼 (아래쪽에만)
    if moss:
        for _ in range(w // 3):
            x, y = rng.randrange(w), rng.randint(h * 2 // 3, h - 1)
            c = rng.choice([(70, 110, 55), (95, 140, 70), (50, 85, 45)])
            pygame.draw.rect(stone, c, (x, y, rng.choice([2, 3, 4]), rng.choice([2, 3])))

    # 5) 입체 모서리: 왼쪽 위는 빛을 받아 밝게, 오른쪽 아래는 그늘져 어둡게
    m = pygame.mask.from_surface(base).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    ew = 2 if size > 40 else 1

    def edge(dx, dy, color):
        sh = pygame.Surface((w, h), pygame.SRCALPHA)
        sh.blit(m, (dx, dy))
        e = m.copy()
        e.blit(sh, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        e.fill(color, special_flags=pygame.BLEND_RGBA_MULT)
        return e

    stone.blit(edge(ew, ew, (255, 240, 215, 190)), (0, 0))
    stone.blit(edge(-ew, -ew, (15, 12, 20, 200)), (0, 0))
    stone.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)  # 글자 모양만 남기기

    # 6) 두께감: 돌 옆면(어두운 회색) -> 가장 바깥 검은 테두리
    side = outline_surface(stone, 2, (58, 54, 60))
    return outline_surface(side, 3, (16, 12, 20))


title_img = make_stone_title("SURVIVOR", 76)
subtitle_img = make_stone_title("끝없는 던전", 34, (240, 160, 90), (130, 55, 30), seed=5)  # 불씨처럼 붉은 부제

# ------------------------------------------------------------
# 2) 저장 파일 (survivor.py 옆의 save.json: 골드, 강화, 무기, 기록, 스테이지, 업적이 전부 들어 있어요)
# ------------------------------------------------------------
SAVE_PATH = os.path.join(BASE_DIR, "save.json")
OLD_BEST_PATH = os.path.join(BASE_DIR, "best.json")  # 예전 기록 파일 (있으면 한 번 읽어 와요)
best_time = 0   # 무한 모드 최고 생존 시간(초)
best_kills = 0  # 무한 모드 최고 처치 수
gold = 0        # 가진 골드
meta_levels = {}    # 영구 강화 단계
weapon_stars = {}   # 가진 무기 {무기 이름: 별 개수 1~5}
equipped_weapon = ""
equipped_gear = {"armor": "", "acc": "", "rune": "", "rune2": "", "pet": ""}
PITY_SLOTS = ("weapon", "armor", "acc", "rune", "pet")
pity_by_slot = {slot: 0 for slot in PITY_SLOTS}  # 분류별 전설 확정 횟수
last_gain = 0       # 마지막 판에서 번 골드 (게임오버 화면용)
last_bonus = 0
last_clear = 0      # 마지막 판의 스테이지 클리어 보상
stages_cleared = set()  # 클리어한 스테이지 번호들
stage_best = {}         # 스테이지별 최단 클리어 시간(초) {"1": 212, ...}
total_kills = 0         # 지금까지 잡은 적 (업적용)
total_bosses = 0
total_elites = 0
achv_done = {}          # 달성한 업적 {키: True}
cur_stage = 0           # 지금 고른 스테이지 (0이면 무한 모드)


def make_sound(freq, ms, vol=0.3, slide=0.0, noise=False):
    """주파수(freq)에서 시작해 slide만큼 변하는 짧은 효과음을 만들어요."""
    rate = 22050
    n = int(rate * ms / 1000)
    buf = array.array("h")
    for i in range(n):
        t = i / rate
        v = random.uniform(-1, 1) if noise else math.sin(2 * math.pi * (freq + slide * t) * t)
        buf.append(int(v * (1 - i / n) * vol * 32767))  # 뒤로 갈수록 작아져요
    return pygame.mixer.Sound(buffer=buf.tobytes())


def make_projectile_sound(root_hz, seed):
    """반복해서 쏠 때 튀는 전자음 대신 낮고 짧은 발사음을 만들어요."""
    rate = 22050
    duration = 0.085
    n = int(rate * duration)
    rng = random.Random(seed)
    buf = array.array("h")
    phase = 0.0
    smooth_noise = 0.0
    for i in range(n):
        t = i / rate
        progress = t / duration
        phase += 2 * math.pi * (root_hz * (1 - 0.35 * progress)) / rate
        smooth_noise = smooth_noise * 0.8 + rng.uniform(-1, 1) * 0.2
        envelope = math.exp(-t * 42)
        body = math.sin(phase) * envelope * 0.26
        air = smooth_noise * math.exp(-t * 72) * 0.09
        click = math.sin(2 * math.pi * 720 * t) * math.exp(-t * 210) * 0.045
        sample = max(-1.0, min(1.0, body + air + click))
        buf.append(int(sample * 32767))
    return pygame.mixer.Sound(buffer=buf.tobytes())


def make_impact_sound(root_hz, seed):
    """짧은 저음 타격음에 부드러운 잡음을 섞어 날카로운 치찰음을 줄여요."""
    rate = 22050
    duration = 0.11
    n = int(rate * duration)
    rng = random.Random(seed)
    buf = array.array("h")
    phase = 0.0
    smooth_noise = 0.0
    for i in range(n):
        t = i / rate
        progress = t / duration
        phase += 2 * math.pi * (root_hz * (1 - 0.48 * progress)) / rate
        smooth_noise = smooth_noise * 0.78 + rng.uniform(-1, 1) * 0.22
        body = math.sin(phase) * math.exp(-t * 32) * 0.36
        thump = math.sin(2 * math.pi * 62 * t) * math.exp(-t * 24) * 0.18
        crack = smooth_noise * math.exp(-t * 115) * 0.13
        sample = max(-1.0, min(1.0, body + thump + crack))
        buf.append(int(sample * 32767))
    return pygame.mixer.Sound(buffer=buf.tobytes())


def make_slash_sound(seed):
    """고음 잡음 대신 낮게 훑고 지나가는 짧은 칼바람 소리를 만들어요."""
    rate = 22050
    duration = 0.14
    n = int(rate * duration)
    rng = random.Random(seed)
    buf = array.array("h")
    phase = 0.0
    smooth_noise = 0.0
    for i in range(n):
        t = i / rate
        progress = t / duration
        phase += 2 * math.pi * (360 - 230 * progress) / rate
        smooth_noise = smooth_noise * 0.82 + rng.uniform(-1, 1) * 0.18
        envelope = min(1.0, t / 0.012) * (1 - progress) ** 1.25
        whoosh = math.sin(phase) * 0.20 + smooth_noise * 0.20
        low_swipe = math.sin(2 * math.pi * 118 * t) * math.exp(-t * 36) * 0.12
        sample = max(-1.0, min(1.0, whoosh * envelope + low_swipe))
        buf.append(int(sample * 32767))
    return pygame.mixer.Sound(buffer=buf.tobytes())


class SoundVariants:
    """같은 효과가 연속으로 날 때 음색이 조금씩 달라지게 재생해요."""
    def __init__(self, *sounds):
        self.sounds = sounds
        self.index = 0

    def play(self):
        sound = self.sounds[self.index % len(self.sounds)]
        self.index += 1
        return sound.play()


snd_shoot = SoundVariants(
    make_projectile_sound(250, 7),
    make_projectile_sound(285, 13),
    make_projectile_sound(225, 21),
)
snd_hit = SoundVariants(
    make_impact_sound(132, 17),
    make_impact_sound(154, 29),
    make_impact_sound(118, 43),
)
snd_hurt = make_sound(160, 250, 0.35, -400)
snd_level = make_sound(500, 300, 0.25, 1500)
snd_dash = make_sound(300, 120, 0.15, 2000)
snd_boss = make_sound(100, 600, 0.40, 100)
snd_zap = make_sound(1400, 140, 0.25, -7000)
snd_flame = make_sound(320, 220, 0.22, 900, noise=True)
snd_click = make_sound(900, 40, 0.10, -2000)
snd_buy = make_sound(600, 130, 0.20, 1800)
snd_fail = make_sound(150, 140, 0.22, -100)
snd_clear = make_sound(400, 700, 0.30, 900)

# ------------------------------------------------------------
# 3) 판이 바뀌어도 변하지 않는 값들
# ------------------------------------------------------------
player_radius = 14
projectile_radius = 5
projectile_speed = 8
gem_radius = 5
blade_orbit = 62   # 회전 칼날이 도는 반지름
blade_radius = 11  # 회전 칼날의 충돌 크기

# 보스 공격 범위
ORC_REACH = 125        # 오크 몽둥이가 닿는 거리
ORC_ARC = 70           # 오크가 몽둥이를 휘두르는 각도(좌우 각각)
DRAGON_TAIL_LEN = 200  # 드래곤 꼬리 길이
DRAGON_TAIL_ARC = 60   # 드래곤 꼬리가 훑는 각도(좌우 각각)
GOLEM_SLAM_R = 85      # 골렘이 내려찍는 범위 반지름
METEOR_WARN = 70       # 낙하물이 떨어지기 전 예고 시간(프레임)

BOSS_NAMES = {"orc": "오크 대장", "dragon": "드래곤", "golem": "바위 골렘"}
ENDLESS_BOSSES = ["orc", "dragon", "golem"]  # 무한 모드 보스 순서

hazard_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)  # 보스 예고 구역을 그리는 반투명 층

# 던전 벽에 걸린 횃불 위치 (불꽃은 매 프레임 일렁이게 그려요)
TORCH_POS = [(70, 150), (730, 150), (40, 330), (760, 330), (70, 500), (730, 500)]

# ------------------------------------------------------------
# 4) 도트 그림
# ------------------------------------------------------------
HERO_PIXELS = [
    "....HHHH....",
    "..HhhllhhH..",
    ".HhhhlhhhhH.",
    ".HhhhhhhhhH.",
    ".HsewssewsH.",
    ".HseesseessH",
    ".HpssmmssspH",
    "..HssssssH..",
    "..RrrrrrrR..",
    ".sNnnnnnnNs.",
    "..NnggggnN..",
    "..bbb..bbb..",
]
HERO_COLORS = {
    "H": (70, 60, 120), "h": (205, 210, 245), "l": (245, 247, 255),
    "s": (255, 214, 178), "e": (30, 26, 50), "w": (255, 255, 255),
    "p": (255, 150, 150), "m": (205, 105, 105),
    "r": (240, 95, 60), "R": (170, 50, 45),
    "n": (60, 85, 175), "N": (35, 45, 110), "g": (245, 205, 85), "b": (115, 72, 45),
}

SLIME_PIXELS = [
    "............",
    "............",
    "....dddd....",
    "...dggggd...",
    "..dgllgggd..",
    ".dggggggggd.",
    ".dggkggkggd.",
    ".dggggggggd.",
    "dggggggggggd",
    "dggggggggggd",
    ".dddddddddd.",
    "............",
]
SLIME_COLORS = {
    "d": (40, 120, 70), "g": (110, 210, 110), "l": (200, 250, 200), "k": (20, 40, 30),
}

GOBLIN_PIXELS = [
    "............",
    "...dddddd...",
    "..dggggggd..",
    "dddgrggrgddd",
    ".dgdggggdgd.",
    "..dgwgwgwgd.",
    "...dddddd...",
    "...dbbbbd...",
    "..dbbbbbbd..",
    "..dbbbbbbd..",
    "..dgd..dgd..",
    "..ddd..ddd..",
]
GOBLIN_COLORS = {
    "d": (50, 90, 40), "g": (130, 180, 70), "r": (230, 60, 60),
    "w": (245, 245, 235), "b": (140, 90, 50),
}

# --- 업그레이드 아이콘 ---
SWORD_PIXELS = [
    ".....lw.....",
    ".....lw.....",
    ".....lw.....",
    ".....lw.....",
    ".....lw.....",
    ".....lw.....",
    ".....lw.....",
    "..gggggggg..",
    ".....bb.....",
    ".....bb.....",
    ".....bb.....",
    "....gggg....",
]
SWORD_COLORS = {"l": (170, 200, 255), "w": (240, 245, 255), "g": (230, 190, 70), "b": (140, 90, 50)}

BOLT_PIXELS = [
    "......yyyy..",
    ".....yyyy...",
    "....yyyy....",
    "...yyyy.....",
    "...yyyyyyyy.",
    "......yyyy..",
    ".....yyyy...",
    "....yyy.....",
    "...yyy......",
    "..yy........",
    "..y.........",
    "............",
]
BOLT_COLORS = {"y": (255, 220, 60)}

CHEVRON_PIXELS = [
    "............",
    "cc....cc....",
    ".cc....cc...",
    "..cc....cc..",
    "...cc....cc.",
    "....cc....cc",
    "....cc....cc",
    "...cc....cc.",
    "..cc....cc..",
    ".cc....cc...",
    "cc....cc....",
    "............",
]
CHEVRON_COLORS = {"c": (100, 200, 255)}

MAGNET_PIXELS = [
    "wwww....wwww",
    "rrrr....bbbb",
    "rrrr....bbbb",
    "rrrr....bbbb",
    "rrrr....bbbb",
    "rrrr....bbbb",
    "rrrrr..bbbbb",
    ".rrrrrbbbbb.",
    ".rrrrrbbbbb.",
    "..rrrrbbbb..",
    "...rrrbbb...",
    "............",
]
MAGNET_COLORS = {"w": (240, 240, 240), "r": (220, 60, 60), "b": (70, 110, 230)}

HEART_PIXELS = [
    "............",
    ".hhh....hhh.",
    "hhhhh..hhhhh",
    "hhwhhhhhhhhh",
    "hhhhhhhhhhhh",
    "hhhhhhhhhhhh",
    ".hhhhhhhhhh.",
    "..hhhhhhhh..",
    "...hhhhhh...",
    "....hhhh....",
    ".....hh.....",
    "............",
]
HEART_COLORS = {"h": (230, 70, 90), "w": (255, 170, 180)}
HEART_EMPTY_COLORS = {"h": (62, 56, 78), "w": (80, 74, 98)}

MULTISHOT_PIXELS = [
    "y....y....y.",
    ".y...y...y..",
    "..y..y..y...",
    "...y.y.y....",
    "....yyy.....",
    ".....y......",
    ".....y......",
    ".....y......",
    ".....y......",
    "............",
    "............",
    "............",
]
MULTISHOT_COLORS = {"y": (255, 160, 60)}

PIERCE_PIXELS = [
    "......c.....",
    ".....ccc....",
    "....ccccc...",
    "......c.....",
    "ddddddcddddd",
    "......c.....",
    "......c.....",
    "ddddddcddddd",
    "......c.....",
    "......c.....",
    ".....c.c....",
    "............",
]
PIERCE_COLORS = {"c": (190, 255, 120), "d": (120, 120, 160)}

BLADE_PIXELS = [
    "...oooooo...",
    "..o......o..",
    ".o........o.",
    "o..........o",
    "o....ww....o",
    "o...wwww...o",
    "o...wwww...o",
    "o....ww....o",
    "o..........o",
    ".o........o.",
    "..o......o..",
    "...oooooo...",
]
BLADE_COLORS = {"o": (80, 225, 205), "w": (240, 255, 250)}

CRIT_PIXELS = [
    ".....oo.....",
    ".....oo.....",
    ".....oo.....",
    ".....oo.....",
    "....oyyo....",
    "ooooyyyyoooo",
    "ooooyyyyoooo",
    "....oyyo....",
    ".....oo.....",
    ".....oo.....",
    ".....oo.....",
    ".....oo.....",
]
CRIT_COLORS = {"o": (255, 150, 40), "y": (255, 240, 150)}

DROP_PIXELS = [
    ".....rr.....",
    ".....rr.....",
    "....rrrr....",
    "....rrrr....",
    "...rrrrrr...",
    "..rrwrrrrr..",
    "..rrwrrrrr..",
    "..rrrrrrrr..",
    "..rrrrrrrr..",
    "...rrrrrr...",
    "....rrrr....",
    "............",
]
DROP_COLORS = {"r": (200, 40, 70), "w": (255, 150, 170)}

GEM_PIXELS = [
    "............",
    "....bbbb....",
    "...bwbbbb...",
    "..bwbbbbbb..",
    ".bbbbbbbbbb.",
    "bbbbbbbbbbbb",
    ".bbbbbbbbbb.",
    "..bbbbbbbb..",
    "...bbbbbb...",
    "....bbbb....",
    ".....bb.....",
    "............",
]
GEM_COLORS = {"b": (90, 170, 255), "w": (220, 240, 255)}

SHIELD_PIXELS = [
    "dddddddddddd",
    "dssssssssssd",
    "dsslsssssssd",
    "dsslsssssssd",
    "dssssssssssd",
    "dssssssssssd",
    ".dssssssssd.",
    ".dssssssssd.",
    "..dssssssd..",
    "...dssssd...",
    "....dssd....",
    ".....dd.....",
]
SHIELD_COLORS = {"d": (50, 70, 120), "s": (120, 160, 230), "l": (200, 225, 255)}
BARRIER_COLORS = {"d": (30, 100, 115), "s": (110, 225, 235), "l": (235, 255, 255)}  # 보호막 아이콘 (청록색)

# --- 새 스킬 5종 아이콘 ---
STORM_PIXELS = [
    "...cccc.....",
    "..cccccc.cc.",
    ".cccccccccc.",
    "cccccccccccc",
    ".cccccccccc.",
    ".....yy.....",
    "....yy......",
    "...yyyyy....",
    ".....yy.....",
    "....yy......",
    "...y........",
    "............",
]
STORM_COLORS = {"c": (170, 180, 210), "y": (255, 230, 70)}

AURA_PIXELS = [
    "....oooo....",
    "..oo....oo..",
    ".o........o.",
    ".o..pppp..o.",
    "o..pppppp..o",
    "o..pppppp..o",
    "o..pppppp..o",
    "o..pppppp..o",
    ".o..pppp..o.",
    ".o........o.",
    "..oo....oo..",
    "....oooo....",
]
AURA_COLORS = {"o": (200, 120, 255), "p": (240, 200, 255)}

BLAST_PIXELS = [
    ".....rr.....",
    "..r..rr..r..",
    "...rroorr...",
    "....roor....",
    "rrrroyyorrrr",
    "rrrroyyorrrr",
    "....roor....",
    "...rroorr...",
    "..r..rr..r..",
    ".....rr.....",
    "............",
    "............",
]
BLAST_COLORS = {"r": (255, 110, 40), "o": (255, 180, 60), "y": (255, 240, 150)}

DASH_PIXELS = [
    "............",
    "......c.....",
    ".......cc...",
    "ww......ccc.",
    "wwwwwwwwcccc",
    "wwwwwwwwcccc",
    "ww......ccc.",
    ".......cc...",
    "......c.....",
    "............",
    "............",
    "............",
]
DASH_COLORS = {"w": (230, 255, 240), "c": (110, 255, 170)}

FROST_PIXELS = [
    ".....bb.....",
    "..b..bb..b..",
    "...b.bb.b...",
    "....bbbb....",
    "bbbbbwwbbbbb",
    "bbbbbwwbbbbb",
    "....bbbb....",
    "...b.bb.b...",
    "..b..bb..b..",
    ".....bb.....",
    "............",
    "............",
]
FROST_COLORS = {"b": (120, 200, 255), "w": (240, 250, 255)}

# --- 보스 ---
# 오크 대장: 16x16 (몽둥이는 코드로 따로 그려서 휘둘러요)
ORC_PIXELS = [
    "................",
    ".....dddddd.....",
    "....dggggggd....",
    "...dggggggggd...",
    "...dggrggrggd...",
    "...dggggggggd...",
    "...dgwggggwgd...",
    "....dggggggd....",
    "..ddbbbbbbbbdd..",
    ".dgdbmbbbbmbdgd.",
    ".dgdbbbbbbbbdgd.",
    ".dggdBBBBBBdggd.",
    "...ddBBBBBBdd...",
    "....dggd..dggd..",
    "....dggd..dggd..",
    "...dddd....dddd.",
]
ORC_COLORS = {
    "d": (35, 60, 35), "g": (120, 170, 85), "r": (240, 60, 50), "w": (245, 240, 215),
    "b": (130, 90, 50), "B": (90, 60, 35), "m": (190, 190, 200),
}

# 드래곤: 20x16 (꼬리는 코드로 따로 그려서 휘둘러요)
DRAGON_PIXELS = [
    ".....w........w.....",
    ".....dw......wd.....",
    "....ddrrrrrrrrdd....",
    "...drrrrrrrrrrrrd...",
    "..drrrykrrrrkyrrrd..",
    "..drrrrrrrrrrrrrrd..",
    ".dffdrrrnrrnrrrdffd.",
    "dfffdrrrrrrrrrrdfffd",
    "dffffdwrwrrwrwdffffd",
    ".dfffdddRRRRdddfffd.",
    "..dffdRRooooRRdffd..",
    "...ddRRooooooRRdd...",
    "....dRRooooooRRd....",
    "....dRRooooooRRd....",
    "....ddRRRRRRRRdd....",
    "...dwwd......dwwd...",
]
DRAGON_COLORS = {
    "d": (45, 20, 35), "r": (205, 65, 55), "R": (140, 38, 45), "o": (245, 180, 90),
    "y": (255, 230, 80), "k": (30, 20, 20), "w": (245, 240, 220), "n": (60, 20, 25),
    "f": (170, 60, 110),
}

# 바위 골렘: 16x16 (내려찍기 + 사방으로 파편 발사)
GOLEM_PIXELS = [
    "................",
    "....dddddddd....",
    "...dggggggggd...",
    "...dgeggggegd...",
    "...dggggggggd...",
    "....ddggggdd....",
    ".dddddddddddddd.",
    "dgggdggggggdgggd",
    "dggldggggggdgggd",
    "dgggdgmggmgdgggd",
    "dgggdggggggdgggd",
    "..dddggggggddd..",
    "...dggggggggd...",
    "...dggd..dggd...",
    "...dggd..dggd...",
    "..dddddd.dddddd.",
]
GOLEM_COLORS = {"d": (45, 45, 55), "g": (140, 145, 160), "l": (190, 195, 210),
                "e": (255, 170, 60), "m": (80, 130, 80)}

MAGE_PIXELS = [
    "....dddd....",
    "...dppppd...",
    "..dppppppd..",
    "..dpkyykpd..",
    "..dpkkkkpd..",
    "...dppppd...",
    ".dppppppppd.",
    ".dpppoopppd.",
    ".dppppppppd.",
    ".dppppppppd.",
    "..ddppppdd..",
    "...dddddd...",
]
MAGE_COLORS = {"d": (45, 25, 80), "p": (140, 80, 210), "k": (25, 15, 35),
               "y": (255, 230, 80), "o": (255, 200, 90)}

BOAR_PIXELS = [
    "..w......w..",
    "..ww....ww..",
    "..dbbbbbbd..",
    ".dbbbbbbbbd.",
    ".dbwkbbkwbd.",
    ".dbbbbbbbbd.",
    "..dbbnnbbd..",
    "..dbbnnbbd..",
    ".dbbbbbbbbd.",
    ".dbBbbbbBbd.",
    ".ddbbbbbbdd.",
    "..dd....dd..",
]
BOAR_COLORS = {"w": (245, 240, 220), "d": (60, 30, 25), "b": (170, 80, 55),
               "B": (130, 55, 40), "k": (20, 15, 15), "n": (230, 150, 140)}

JELLY_PIXELS = [
    "............",
    "....dddd....",
    "...dbbbbd...",
    "..dbllbbbd..",
    ".dbbllbbbbd.",
    ".dbbbbbbbbd.",
    ".dbkbbbbkbd.",
    ".dbbbbbbbbd.",
    "dbbbbbbbbbbd",
    "dbbbbbbbbbbd",
    ".dddddddddd.",
    "............",
]
JELLY_COLORS = {"d": (30, 70, 140), "b": (90, 160, 240), "l": (200, 230, 255), "k": (15, 30, 60)}

# 박쥐: 지그재그로 빠르게 날아와요
BAT_PIXELS = [
    "............",
    "dd........dd",
    "dbd..dd..dbd",
    "dbbdddddbbbd",
    "dbbbbbbbbbbd",
    ".dbbrbbrbbd.",
    "..dbbbbbbd..",
    "...dbwwbd...",
    "....dbbd....",
    ".....dd.....",
    "............",
    "............",
]
BAT_COLORS = {"d": (40, 30, 70), "b": (110, 90, 160), "r": (255, 80, 80), "w": (240, 240, 240)}

def make_sprite(rows, colors, scale=3):
    """글자로 된 도트 그림을 pygame 이미지(Surface)로 바꿔요."""
    h, w = len(rows), len(rows[0])
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in colors:
                surf.set_at((x, y), colors[ch])
    return pygame.transform.scale(surf, (w * scale, h * scale))


def make_flash(sprite):
    """맞았을 때 번쩍이는 하얀 버전 그림을 만들어요."""
    flash = sprite.copy()
    flash.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_ADD)
    return flash


def make_tint(sprite, rgb):
    """그림에 색을 더해서 물들인 버전을 만들어요 (냉기에 맞은 적은 푸르게)."""
    tinted = sprite.copy()
    tinted.fill((*rgb, 0), special_flags=pygame.BLEND_RGB_ADD)
    return tinted


def make_glow(radius, color):
    """둥글게 퍼지는 빛 그림. BLEND_RGB_ADD로 겹쳐 그리면 은은하게 빛나요."""
    surf = pygame.Surface((radius * 2, radius * 2))
    for i in range(radius, 0, -1):
        k = (1 - i / radius) ** 2
        pygame.draw.circle(surf, (int(color[0] * k), int(color[1] * k), int(color[2] * k)),
                           (radius, radius), i)
    return surf


def make_vignette(color, strength=120, depth=70):
    """화면 가장자리만 색이 짙어지는 반투명 층 (체력이 1일 때 붉게 깜빡여요)."""
    v = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(depth):
        a = int(strength * (1 - i / depth) ** 2)
        pygame.draw.rect(v, (*color, a), (i, i, WIDTH - 2 * i, HEIGHT - 2 * i), 1)
    return v


def make_weapon_icon(shape, colors, scale=3):
    """16x16 도트로 무기를 그리고 외곽선을 둘러서 크게 키워요. (날 색, 밝은 색, 손잡이 색)"""
    blade, light, grip = colors
    gold_c = (235, 195, 80)
    s = pygame.Surface((16, 16), pygame.SRCALPHA)
    ln = pygame.draw.line
    if shape in ("sword", "flame"):
        ln(s, blade, (6, 9), (14, 1), 3)
        ln(s, light, (6, 9), (14, 1), 1)
        ln(s, gold_c, (3, 8), (8, 13), 2)
        ln(s, grip, (5, 10), (2, 13), 2)
        pygame.draw.circle(s, gold_c, (2, 13), 1)
        if shape == "flame":  # 칼날 둘레에 일렁이는 불꽃
            for (x, y, c) in [(9, 1, 0), (12, 0, 1), (15, 3, 0), (13, 5, 1), (10, 3, 1), (8, 4, 0), (15, 6, 1)]:
                s.set_at((x, y), (255, 200, 60) if c else (255, 110, 30))
            s.set_at((15, 0), (255, 245, 180))
    elif shape == "dagger":
        ln(s, blade, (6, 9), (12, 3), 3)
        ln(s, light, (6, 9), (12, 3), 1)
        ln(s, gold_c, (4, 8), (7, 11), 2)
        ln(s, grip, (5, 10), (3, 12), 2)
    elif shape == "axe":
        ln(s, grip, (3, 14), (11, 6), 2)
        pygame.draw.polygon(s, blade, [(9, 2), (14, 4), (14, 9), (11, 8)])
        ln(s, light, (10, 3), (13, 5), 1)
    elif shape == "staff":
        ln(s, grip, (2, 14), (11, 5), 2)
        pygame.draw.circle(s, blade, (12, 4), 3)
        pygame.draw.circle(s, light, (11, 3), 1)
    elif shape == "spear":
        ln(s, grip, (2, 14), (11, 5), 2)
        pygame.draw.polygon(s, blade, [(14, 1), (9, 3), (13, 7)])
        ln(s, light, (13, 2), (11, 5), 1)
    elif shape == "bow":
        pygame.draw.lines(s, blade, False, [(5, 1), (10, 3), (12, 8), (10, 13), (5, 15)], 2)
        ln(s, light, (5, 1), (5, 15), 1)
        pygame.draw.rect(s, grip, (11, 7, 2, 3))
    elif shape in ("armor", "robe"):
        pts = [(3, 3), (6, 2), (10, 2), (13, 3), (13, 9), (8, 14), (3, 9)] if shape == "armor" \
            else [(8, 1), (12, 4), (14, 14), (2, 14), (4, 4)]
        pygame.draw.polygon(s, blade, pts)
        ln(s, light, (5, 4), (5, 8), 1)
        ln(s, grip, (8, 3), (8, 12), 2)
    elif shape == "ring":
        pygame.draw.circle(s, blade, (8, 10), 5, 2)
        pygame.draw.circle(s, light, (8, 4), 2)
        s.set_at((7, 3), grip)
    elif shape == "boots":
        pygame.draw.polygon(s, blade, [(4, 2), (9, 2), (9, 9), (14, 11), (14, 14), (4, 14)])
        ln(s, light, (5, 3), (5, 12), 1)
        ln(s, grip, (4, 14), (14, 14), 1)
    elif shape == "amulet":
        ln(s, grip, (4, 1), (8, 8), 1)
        ln(s, grip, (12, 1), (8, 8), 1)
        pygame.draw.circle(s, blade, (8, 10), 4)
        pygame.draw.circle(s, light, (7, 9), 1)
    elif shape == "crown":
        pygame.draw.polygon(s, blade, [(2, 13), (2, 5), (5, 8), (8, 3), (11, 8), (14, 5), (14, 13)])
        ln(s, light, (3, 12), (13, 12), 1)
        for cx in (2, 8, 14):
            s.set_at((cx, 3 if cx == 8 else 4), grip)
    elif shape == "rune":
        pygame.draw.polygon(s, grip, [(8, 1), (14, 8), (8, 15), (2, 8)])
        pygame.draw.polygon(s, blade, [(8, 3), (12, 8), (8, 13), (4, 8)])
        ln(s, light, (8, 5), (8, 11), 1)
        ln(s, light, (6, 8), (10, 8), 1)
    elif shape in ("pet", "petw"):
        if shape == "petw":
            pygame.draw.polygon(s, light, [(3, 8), (0, 3), (5, 6)])
            pygame.draw.polygon(s, light, [(13, 8), (15, 3), (11, 6)])
        pygame.draw.circle(s, blade, (8, 9), 5)
        pygame.draw.circle(s, light, (6, 7), 1)
        pygame.draw.circle(s, blade, (4, 4), 2)
        pygame.draw.circle(s, blade, (12, 4), 2)
        s.set_at((6, 9), grip)
        s.set_at((10, 9), grip)
    img = outline_surface(s, 1, (16, 12, 28))
    return pygame.transform.scale(img, (img.get_width() * scale, img.get_height() * scale))


def make_coin(size=20):
    """동그란 금화 그림."""
    c = size // 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(s, (120, 80, 20), (c, c), c)
    pygame.draw.circle(s, (250, 200, 60), (c, c), c - 2)
    pygame.draw.circle(s, (255, 236, 150), (c - 2, c - 2), max(1, c // 3))
    pygame.draw.rect(s, (200, 140, 30), (c - 1, c - 4, 3, 8))
    return s


coin_img = make_coin(20)


def draw_star(surf, center, r, color, empty=False):
    """별 하나 (글꼴에 별 글자가 없어도 되게 직접 그려요)."""
    pts = []
    for i in range(10):
        a = math.radians(-90 + i * 36)
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((center[0] + math.cos(a) * rad, center[1] + math.sin(a) * rad))
    pygame.draw.polygon(surf, (58, 62, 88) if empty else color, pts)


_shadow_cache = {}


def get_shadow(w):
    """발밑 그림자(반투명 타원). 크기별로 한 번만 만들어 둬요."""
    if w not in _shadow_cache:
        s = pygame.Surface((w, max(6, w // 3)), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 90), s.get_rect())
        _shadow_cache[w] = s
    return _shadow_cache[w]


_glow_cache = {}


def add_glow(surf, glow, pos, scale=1.0):
    """빛 그림을 겹쳐 그려서 은은하게 빛나게 해요. 크기별로 한 번만 만들어 둬요."""
    key = (id(glow), round(scale, 2))
    g = _glow_cache.get(key)
    if g is None:
        if scale == 1.0:
            g = glow
        else:
            g = pygame.transform.smoothscale(
                glow, (max(2, int(glow.get_width() * scale)), max(2, int(glow.get_height() * scale))))
        _glow_cache[key] = g
    surf.blit(g, g.get_rect(center=(int(pos[0]), int(pos[1]))), special_flags=pygame.BLEND_RGB_ADD)


_squash_cache = {}


def squashed(sprite, w, h):
    """찌그러진 크기의 그림. 같은 크기는 한 번만 만들어 둬요."""
    key = (id(sprite), w, h)
    s = _squash_cache.get(key)
    if s is None:
        s = pygame.transform.scale(sprite, (w, h))
        _squash_cache[key] = s
    return s


def draw_shadow(surf, pos, w, dy):
    sh = get_shadow(w)
    surf.blit(sh, sh.get_rect(center=(int(pos[0]), int(pos[1] + dy))))


def blit_text(surf, fnt, text, color, pos, center=False):
    """외곽선이 둘린 글씨 (어떤 배경에서도 잘 보여요)."""
    txt = fnt.render(text, True, color)
    r = txt.get_rect(center=pos) if center else txt.get_rect(topleft=pos)
    surf.blit(txt, r)


def blit_text_right(surf, fnt, text, color, right, y):
    """텍스트의 오른쪽 끝을 지정한 좌표에 맞춰 배치합니다."""
    txt = fnt.render(str(text), True, color)
    surf.blit(txt, txt.get_rect(topright=(int(right), int(y))))


def aura_radius(lv):
    return 0 if lv == 0 else 55 + 15 * lv


def blast_radius(lv):
    return 0 if lv == 0 else 40 + 12 * lv


def frost_factor(lv):
    """냉기 단계별 이동 속도 배율 (1.0이면 느려지지 않음)."""
    return 1.0 if lv == 0 else max(0.3, 0.8 - 0.1 * lv)


# 불꽃검: 가까운 적이 있으면 부채꼴로 크게 베고, 맞은 적은 3초 동안 불에 타요 (보스는 타지 않아요)
def flame_reach(lv):
    return 84 + 10 * lv        # 94 ~ 134


def flame_half(lv):
    return 50 + 4 * lv         # 한쪽 각도 54 ~ 70


def flame_cd(lv):
    return 160 - 12 * lv       # 2.5초 -> 1.7초


def flame_damage(lv):
    return projectile_damage + 2 * lv


def flame_burn(lv):
    return 1 + lv // 2         # 0.5초마다 1~3 피해 (최대 6번)


def shield_regen(lv):
    """보호막 한 장이 다시 차오르는 시간(프레임). 단계가 높을수록 빨라져요."""
    return max(600, 1500 - 250 * lv)


hero_sprite = make_sprite(HERO_PIXELS, HERO_COLORS)
hero_big = pygame.transform.scale(hero_sprite, (144, 144))  # 타이틀 화면용

slime_sprite = make_sprite(SLIME_PIXELS, SLIME_COLORS)
goblin_sprite = make_sprite(GOBLIN_PIXELS, GOBLIN_COLORS)
slime_big = pygame.transform.scale(slime_sprite, (84, 84))
goblin_big = pygame.transform.scale(goblin_sprite, (84, 84))
orc_sprite = make_sprite(ORC_PIXELS, ORC_COLORS, 5)           # 80x80
dragon_sprite = make_sprite(DRAGON_PIXELS, DRAGON_COLORS, 6)  # 120x96
golem_sprite = make_sprite(GOLEM_PIXELS, GOLEM_COLORS, 5)     # 80x80
mage_sprite = make_sprite(MAGE_PIXELS, MAGE_COLORS)            # 36x36
boar_sprite = make_sprite(BOAR_PIXELS, BOAR_COLORS)            # 36x36
jelly_sprite = make_sprite(JELLY_PIXELS, JELLY_COLORS, 4)      # 48x48
mini_sprite = make_sprite(JELLY_PIXELS, JELLY_COLORS, 2)       # 24x24
bat_sprite = make_sprite(BAT_PIXELS, BAT_COLORS)               # 36x36
glow_mage = make_glow(26, (110, 50, 170))

heart_full = make_sprite(HEART_PIXELS, HEART_COLORS, 2)
heart_empty = make_sprite(HEART_PIXELS, HEART_EMPTY_COLORS, 2)
magnet_small = make_sprite(MAGNET_PIXELS, MAGNET_COLORS, 2)
gem_sprite = pygame.transform.scale(make_sprite(GEM_PIXELS, GEM_COLORS, 1), (16, 16))

hero_left = pygame.transform.flip(hero_sprite, True, False)  # 왼쪽을 볼 때 쓰는 그림
hero_ghost = hero_sprite.copy()                               # 대시 잔상용
hero_ghost_left = hero_left.copy()
glow_gem = make_glow(14, (40, 90, 200))
glow_proj = make_glow(16, (200, 150, 40))
glow_hero = make_glow(130, (30, 40, 70))
glow_zap = make_glow(40, (120, 120, 60))
glow_torch = make_glow(95, (120, 65, 22))
glow_fire = make_glow(34, (150, 70, 20))
glow_elite = make_glow(40, (150, 105, 20))  # 엘리트 적 뒤에서 금빛으로 빛나요
glow_rage = make_glow(40, (170, 30, 30))
freeze_tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
freeze_tint.fill((90, 150, 255, 45))
low_hp_vig = make_vignette((220, 20, 40), 200, 90)

# 적 종류 표: color는 죽을 때 튀는 파편 색
enemy_types = {
    "slime": {"speed": 0.8, "hp_bonus": 0, "radius": 14, "color": (110, 210, 110),
              "sprite": slime_sprite, "flash": make_flash(slime_sprite)},
    "goblin": {"speed": 1.4, "hp_bonus": -1, "radius": 11, "color": (160, 200, 80),
               "sprite": goblin_sprite, "flash": make_flash(goblin_sprite)},
    "mage": {"speed": 0.9, "hp_bonus": 0, "radius": 12, "color": (170, 110, 230),
             "sprite": mage_sprite, "flash": make_flash(mage_sprite)},
    "boar": {"speed": 1.0, "hp_bonus": 1, "radius": 13, "color": (200, 100, 70),
             "sprite": boar_sprite, "flash": make_flash(boar_sprite)},
    "jelly": {"speed": 0.7, "hp_bonus": 2, "radius": 18, "color": (90, 160, 240),
              "sprite": jelly_sprite, "flash": make_flash(jelly_sprite)},
    "mini": {"speed": 1.6, "hp_bonus": -1, "radius": 9, "color": (90, 160, 240),
             "sprite": mini_sprite, "flash": make_flash(mini_sprite)},
    "bat": {"speed": 1.5, "hp_bonus": -1, "radius": 11, "color": (130, 110, 180),
            "sprite": bat_sprite, "flash": make_flash(bat_sprite)},
    # 보스: speed / hp_bonus는 쓰지 않고(보스는 자기 행동이 따로 있어요), radius는 충돌 크기예요
    "orc": {"speed": 1.0, "hp_bonus": 0, "radius": 30, "color": (120, 170, 85),
            "sprite": orc_sprite, "flash": make_flash(orc_sprite)},
    "dragon": {"speed": 1.0, "hp_bonus": 0, "radius": 42, "color": (220, 90, 70),
               "sprite": dragon_sprite, "flash": make_flash(dragon_sprite)},
    "golem": {"speed": 1.0, "hp_bonus": 0, "radius": 34, "color": (150, 155, 175),
              "sprite": golem_sprite, "flash": make_flash(golem_sprite)},
}

# ───────── 새 몬스터 ─────────
YETI_PIXELS = [
    "..dd....dd..", ".dwwd..dwwd.", ".dwwwddwwwd.", "dwwwwwwwwwwd", "dwwkwwwwkwwd", "dwwwwwwwwwwd",
    ".dwwbbbbwwd.", "dwwwbbbbwwwd", "dwwwwwwwwwwd", "dwwwwwwwwwwd", ".dwwd..dwwd.", ".ddd....ddd.",
]
IMP_PIXELS = [
    "yd........dy", ".dd......dd.", "..drrrrrrd..", ".drrrrrrrrd.", ".drykrrkyrd.", ".drrrrrrrrd.",
    "..drwwwwrd..", "...drrrrd...", "..drrrrrrd..", ".dorrrrrrod.", "..drd..drd..", "..ddd..ddd..",
]
SKEL_PIXELS = [
    "...wwwwww...", "..wwwwwwww..", "..wkkwwkkw..", "..wkkwwkkw..", "...wwnnww...", "....wwww....",
    "...wwwwww...", ".ww.wwww.ww.", ".w..wwww..w.", "....wwww....", "...ww..ww...", "..www..www..",
]
GHOST_PIXELS = [
    "....wwww....", "...wwwwww...", "..wwwwwwww..", "..wkkwwkkw..", "..wkkwwkkw..", "..wwwooowww.",
    ".wwwwwwwwwww", ".wwwwwwwwwww", "wwwwwwwwwwww", "wwwwwwwwwwww", "ww.ww.ww.ww.", "w...w..w...w",
]
SCORP_PIXELS = [
    "..cc....cc..", ".c..c..c..c.", ".c..cddc..c.", "..cddooddc..", "...dokkod...", "..cdoooodc..",
    ".c.dddddd.c.", "...odooodo..", "..c.dooood.c", "...c.dddd.c.", "........c.c.", "..........c.",
]
FROST_WOLF_PIXELS = [
    "..c.....c...", ".cc......cc.", "..wwwwwwww..", ".wwwwwwwwww.", "wwkwwwwwwkww",
    "wwwwwwwwwwww", "wwwwwwwwwwww", ".wwwwwwwwww.", "..cc.ww.cc..", "..cc....cc..",
]
yeti_sprite = make_sprite(YETI_PIXELS, {"d": (90, 110, 150), "w": (235, 245, 255), "k": (30, 40, 70), "b": (160, 200, 235)}, 4)
imp_sprite = make_sprite(IMP_PIXELS, {"d": (80, 20, 25), "r": (230, 70, 40), "y": (255, 220, 80), "k": (30, 10, 10),
                                      "w": (255, 240, 220), "o": (255, 150, 60)})
skel_sprite = make_sprite(SKEL_PIXELS, {"w": (225, 225, 210), "k": (20, 20, 30), "n": (110, 110, 120)})
ghost_sprite = make_sprite(GHOST_PIXELS, {"w": (190, 215, 255), "k": (30, 30, 70), "o": (255, 150, 170)})
scorp_sprite = make_sprite(SCORP_PIXELS, {"c": (210, 160, 70), "d": (110, 70, 30), "o": (230, 190, 100), "k": (30, 20, 10)})
mummy_sprite = make_sprite(GOBLIN_PIXELS, {"d": (110, 90, 60), "g": (225, 205, 160), "r": (230, 60, 60),
                                           "w": (245, 245, 235), "b": (190, 170, 120)})
toad_sprite = make_sprite(SLIME_PIXELS, {"d": (50, 70, 30), "g": (130, 160, 60), "l": (210, 230, 120), "k": (20, 30, 10)})
shroom_sprite = make_sprite(JELLY_PIXELS, {"d": (90, 25, 35), "b": (220, 70, 80), "l": (255, 240, 240), "k": (40, 15, 20)}, 3)
frost_wolf_sprite = make_sprite(FROST_WOLF_PIXELS,
                                {"c": (90, 155, 210), "w": (215, 240, 255), "k": (35, 55, 85)}, 4)
ash_hound_sprite = make_sprite(FROST_WOLF_PIXELS,
                               {"c": (75, 32, 24), "w": (235, 105, 45), "k": (45, 24, 20)}, 4)
ice_jelly_sprite = make_sprite(JELLY_PIXELS,
                               {"d": (40, 110, 160), "b": (90, 190, 235), "l": (210, 250, 255), "k": (25, 60, 90)}, 4)
magma_slime_sprite = make_sprite(SLIME_PIXELS,
                                 {"d": (90, 30, 20), "g": (205, 65, 30), "l": (255, 175, 55), "k": (40, 15, 10)}, 4)
ice_mage_sprite = make_sprite(MAGE_PIXELS,
                              {"d": (25, 55, 95), "p": (65, 145, 220), "k": (15, 30, 55),
                               "y": (190, 245, 255), "o": (120, 220, 255)}, 3)
fire_mage_sprite = make_sprite(MAGE_PIXELS,
                               {"d": (75, 25, 18), "p": (195, 65, 30), "k": (40, 15, 15),
                                "y": (255, 225, 90), "o": (255, 130, 35)}, 3)
ice_wisp_sprite = make_sprite(GHOST_PIXELS,
                              {"w": (125, 205, 255), "k": (25, 55, 100), "o": (225, 250, 255)}, 3)
raider_sprite = make_sprite(GOBLIN_PIXELS,
                            {"d": (70, 45, 25), "g": (190, 130, 55), "r": (170, 50, 35),
                             "w": (250, 220, 160), "b": (125, 78, 42)}, 3)
sand_boar_sprite = make_sprite(BOAR_PIXELS,
                               {"w": (245, 220, 160), "d": (85, 55, 30), "b": (185, 125, 65),
                                "B": (130, 80, 40), "k": (30, 22, 16), "n": (220, 150, 110)}, 3)


def _et(speed, hp, r, color, spr):
    return {"speed": speed, "hp_bonus": hp, "radius": r, "color": color, "sprite": spr, "flash": make_flash(spr)}


enemy_types.update({
    "yeti": _et(1.0, 3, 17, (200, 225, 255), yeti_sprite),
    "imp": _et(1.5, -1, 11, (255, 120, 60), imp_sprite),
    "skeleton": _et(0.9, 1, 12, (225, 225, 210), skel_sprite),
    "ghost": _et(1.0, 0, 12, (190, 215, 255), ghost_sprite),
    "scorpion": _et(1.1, 1, 13, (210, 160, 70), scorp_sprite),
    "mummy": _et(0.8, 3, 14, (225, 205, 160), mummy_sprite),
    "toad": _et(0.9, 2, 14, (130, 160, 60), toad_sprite),
    "shroom": _et(0.8, 1, 14, (220, 70, 80), shroom_sprite),
    "frost_wolf": _et(1.25, 1, 14, (170, 220, 255), frost_wolf_sprite),
    "ash_hound": _et(1.3, 0, 14, (255, 130, 65), ash_hound_sprite),
    "ice_jelly": _et(0.75, 2, 17, (110, 215, 255), ice_jelly_sprite),
    "magma_slime": _et(0.7, 3, 17, (255, 120, 45), magma_slime_sprite),
    "ice_mage": _et(0.9, 0, 12, (100, 195, 255), ice_mage_sprite),
    "fire_mage": _et(0.95, 0, 12, (255, 120, 55), fire_mage_sprite),
    "ice_wisp": _et(1.2, -1, 12, (135, 220, 255), ice_wisp_sprite),
    "raider": _et(1.35, 0, 11, (205, 150, 80), raider_sprite),
    "sand_boar": _et(1.05, 2, 13, (205, 150, 80), sand_boar_sprite),
})
enemy_types["ice_mage"]["shot_color"] = (100, 205, 255)
enemy_types["fire_mage"]["shot_color"] = (255, 120, 50)
# 행동 묶음: 돌진형 / 원거리형 / 날아다니는 형 (새 몬스터를 만들면 여기에 이름만 넣으세요)
CHARGERS = {"boar", "yeti", "scorpion", "frost_wolf", "ash_hound", "sand_boar"}
SHOOTERS = {"mage", "skeleton", "shroom", "ice_mage", "fire_mage"}
FLYERS = {"bat", "ghost", "imp", "ice_wisp"}

for _t in enemy_types.values():
    _t["frost"] = make_tint(_t["sprite"], (30, 80, 150))  # 냉기에 맞아 느려진 적은 푸르게 보여요

# ------------------------------------------------------------
# 5) Upgrade pool: 28 attack and support skills after merging overlaps.
# ------------------------------------------------------------
upgrades = {
    "공격 속도": "발사 간격이\n짧아져요",
    "공격력": "투사체\n데미지 +1",
    "이동 속도": "이동이 빨라지고\n대시를 더 자주 써요",
    "줍기 범위": "구슬을 더\n멀리서 주워요",
    "최대 체력": "체력 +1\n바로 회복",
    "멀티샷": "투사체가\n한 발 늘어요",
    "관통": "적을 뚫고\n지나가요",
    "회전 칼날": "몸 주위를\n도는 칼날",
    "치명타": "가끔 2배의\n피해를 줘요",
    "경험 증가": "경험치를\n더 얻어요",
    "번개": "주기적으로\n적에게 낙뢰",
    "오라": "주변 적에게\n지속 피해",
    "폭발탄": "맞은 곳이 폭발\n처치 시 연쇄 폭발",
    "냉기": "맞은 적이\n느려져요",
    "무적 연장": "맞은 뒤 무적\n시간이 늘어요",
    "불꽃검": "전방을 크게 베고\n적을 불태워요",
    "보호막": "피해를 막아주는\n보호막이 생겨요",
}
# 새 스킬은 여기 표에만 추가하면 돼요: desc 설명 / max 최대 단계 / icon (기존 도트, 색) / prev 미리보기
NEW_SKILLS = {
    "혜성": {"desc": "하늘에서 운석이\n떨어져 폭발해요", "max": 5, "color": (130, 190, 255),
           "icon": (BLAST_PIXELS, {"r": (90, 150, 255), "o": (150, 200, 255), "y": (240, 250, 255)}),
           "prev": lambda lv: f"운석 {lv} -> {lv + 1}발"},
    "가시 갑옷": {"desc": "맞으면 주변 적에게\n반격 피해", "max": 5, "color": (255, 110, 110),
              "icon": (SHIELD_PIXELS, {"d": (110, 30, 40), "s": (230, 90, 90), "l": (255, 200, 200)}),
              "prev": lambda lv: f"반격 {3 * lv} -> {3 * lv + 3}"},
    "재생": {"desc": "시간이 지나면 회복\n적 처치 시 HP+1", "max": 5, "color": (120, 255, 150),
           "icon": (HEART_PIXELS, {"h": (90, 220, 120), "w": (200, 255, 210)}),
           "prev": lambda lv: f"{(1150 - 150 * (lv + 1)) / 60:.0f}초 마다 / 처치 {46 - 8 * (lv + 1)}회마다 HP+1"},
    "충격 대시": {"desc": "대시할 때 주변에\n충격파를 내요", "max": 5, "color": (255, 150, 60),
               "icon": (DASH_PIXELS, {"w": (255, 230, 200), "c": (255, 150, 60)}),
               "prev": lambda lv: f"충격 피해 {3 * lv + 5 if lv else 0} -> {2 * (lv + 1) + 4}"},
    "별빛 난사": {"desc": "주기적으로 사방에\n투사체를 쏴요", "max": 5, "color": (255, 235, 130),
              "icon": (MULTISHOT_PIXELS, {"y": (255, 240, 130)}),
              "prev": lambda lv: f"{4 + lv if lv else 0} -> {5 + lv}발 · 피해 65%"},
    "독 구름": {"desc": "지나온 자리에\n독 구름이 남아요", "max": 5, "color": (140, 230, 90),
             "icon": (STORM_PIXELS, {"c": (110, 200, 80), "y": (200, 255, 130)}),
             "prev": lambda lv: f"반경 {38 + 6 * lv if lv else 0} -> {44 + 6 * lv}"},
    "시간 정지": {"desc": "주기적으로 적이\n잠시 멈춰요", "max": 5, "color": (140, 200, 255),
              "icon": (AURA_PIXELS, {"o": (120, 200, 255), "p": (225, 242, 255)}),
              "prev": lambda lv: f"정지 {(45 + 15 * lv) / 60 if lv else 0:g} -> {(60 + 15 * lv) / 60:g}초"},
    "광폭화": {"desc": "체력이 절반 이하면\n공격력이 올라요", "max": 5, "color": (255, 90, 70),
            "icon": (SWORD_PIXELS, {"l": (255, 130, 100), "w": (255, 215, 190), "g": (255, 170, 60), "b": (120, 40, 30)}),
            "prev": lambda lv: f"공격력 +{10 * lv}% -> +{10 * lv + 10}%"},
    "회피": {"desc": "가끔 공격을\n피해요", "max": 5, "color": (190, 230, 255),
           "icon": (CHEVRON_PIXELS, {"c": (190, 230, 255)}),
           "prev": lambda lv: f"회피 {8 * lv}% -> {8 * lv + 8}%"},
    "행운": {"desc": "골드와 아이템 획득\n확률과 드랍률이 올라요", "max": 5, "color": (120, 255, 160),
           "icon": (GEM_PIXELS, {"b": (110, 230, 140), "w": (220, 255, 230)}),
            "prev": lambda lv: f"골드 +{10 * (lv + 1)}% / 드랍 {3 + 2 * lv}% -> {5 + 2 * lv}%"},
    "보스 사냥꾼": {"desc": "보스에게 주는\n피해가 늘어요", "max": 5, "color": (200, 140, 255),
               "icon": (CRIT_PIXELS, {"o": (190, 120, 255), "y": (235, 210, 255)}),
               "prev": lambda lv: f"보스 피해 +{12 * lv}% -> +{12 * lv + 12}%"},

    "화염 파동": {"desc": "주기적으로 주변을\n불길로 휩쓸어요", "max": 5, "color": (255, 145, 70),
               "icon": (BLAST_PIXELS, {"r": (255, 90, 45), "o": (255, 170, 60), "y": (255, 235, 130)}),
               "prev": lambda lv: f"반경 {78 + 10 * lv} -> {88 + 10 * lv} · 간격 {max(120, 270 - 30 * lv) / 60:.1f} -> {max(120, 270 - 30 * (lv + 1)) / 60:.1f}초"},
    "영혼 사슬": {"desc": "가까운 적 사이로\n번개를 이어 쳐요", "max": 5, "color": (180, 145, 255),
               "icon": (STORM_PIXELS, {"c": (160, 120, 255), "y": (235, 220, 255)}),
               "prev": lambda lv: f"연쇄 {2 + lv} -> {3 + lv}명 · 간격 {max(150, 300 - 25 * lv) / 60:.1f} -> {max(150, 300 - 25 * (lv + 1)) / 60:.1f}초"},
    "연쇄 집중": {"desc": "처치 콤보가 쌓이면\n공격력이 올라요", "max": 5, "color": (255, 205, 100),
               "icon": (BOLT_PIXELS, {"y": (255, 220, 120), "w": (255, 250, 220)}),
               "prev": lambda lv: f"콤보 5당 피해 +{lv}% -> +{lv + 1}% (최대 25%)"},
}

upgrades.update({k: v["desc"] for k, v in NEW_SKILLS.items()})
upgrades.pop("흡혈", None)  # Folded into regeneration.
SKILL_SYNERGIES = {
    "화염 폭발": {"skills": ("폭발탄", "불꽃검"), "color": (255, 150, 70)},
    "빙독 지대": {"skills": ("냉기", "독 구름"), "color": (140, 230, 130)},
    "유성 파편": {"skills": ("혜성", "별빛 난사"), "color": (255, 225, 130)},
    "영혼 공명": {"skills": ("영혼 사슬", "연쇄 집중"), "color": (190, 165, 255)},
}

SKILL_EVOLUTIONS = {
    "화염 폭풍": {"skills": ("폭발탄", "불꽃검"), "synergy": "화염 폭발", "min_level": 4,
                 "color": (255, 135, 55), "desc": "진화: 폭발 범위 +15% · 화상 지속 시간 2초",
                 "preview": "범위 +15% · 화상 지속 1.25초 → 2초"},
    "빙독 폭풍": {"skills": ("냉기", "독 구름"), "synergy": "빙독 지대", "min_level": 4,
                 "color": (130, 235, 215), "desc": "진화: 느려진 적 처치 시 1초 독안개 생성 (최대 2개)",
                 "preview": "처치 시 독안개 · 동시 최대 2개"},
}

MAX_RUN_RELICS = 2
RUN_RELICS = {
    "화염핵": {"color": (255, 145, 75), "desc": "폭발 범위 +15% · 공격력 -5%",
              "preview": "폭발 범위 +15% · 공격력 -5%"},
    "서리독 병": {"color": (120, 220, 220), "desc": "독구름 범위 +20%, 감속 +0.25초 · 이동 속도 -0.2",
                 "preview": "독구름 범위 +20% · 감속 +0.25초 · 이동 -0.2"},
    "사냥꾼의 문장": {"color": (245, 210, 105), "desc": "정예·보스 피해 +15% · 골드 획득 -10%",
                    "preview": "정예·보스 피해 +15% · 골드 -10%"},
}


def synergy_active(name):
    data = SKILL_SYNERGIES.get(name)
    if not data:
        return False
    if any(evo in globals().get("skill_evolutions", set()) and evo_data["synergy"] == name
           for evo, evo_data in SKILL_EVOLUTIONS.items()):
        return True
    return all(skill_levels.get(skill, 0) > 0 for skill in data["skills"])


upgrade_names = list(upgrades.keys())

# Attack skills directly damage or control enemies; support skills improve stats, survival, or rewards.
ATTACK_SKILLS = {
    "멀티샷", "관통", "회전 칼날", "번개", "오라",
    "폭발탄", "냉기", "불꽃검", "혜성", "가시 갑옷",
    "충격 대시", "별빛 난사", "독 구름", "화염 파동", "영혼 사슬",
}
SUPPORT_SKILLS = set(upgrade_names) - ATTACK_SKILLS
ATTACK_SKILL_SLOTS = 5
SUPPORT_SKILL_SLOTS = 5
ATTACK_SKILL_MAX_LEVEL = 5
SUPPORT_SKILL_MAX_LEVEL = 5
assert len(ATTACK_SKILLS) == 15 and len(SUPPORT_SKILLS) == 16

upgrade_style = {
    "공격 속도": {"icon": make_sprite(BOLT_PIXELS, BOLT_COLORS, 5), "color": (255, 200, 60)},
    "공격력": {"icon": make_sprite(SWORD_PIXELS, SWORD_COLORS, 5), "color": (235, 85, 85)},
    "이동 속도": {"icon": make_sprite(DASH_PIXELS, DASH_COLORS, 5), "color": (110, 255, 170)},
    "줍기 범위": {"icon": make_sprite(MAGNET_PIXELS, MAGNET_COLORS, 5), "color": (175, 125, 255)},
    "최대 체력": {"icon": make_sprite(HEART_PIXELS, HEART_COLORS, 5), "color": (255, 110, 130)},
    "멀티샷": {"icon": make_sprite(MULTISHOT_PIXELS, MULTISHOT_COLORS, 5), "color": (255, 160, 60)},
    "관통": {"icon": make_sprite(PIERCE_PIXELS, PIERCE_COLORS, 5), "color": (170, 235, 90)},
    "회전 칼날": {"icon": make_sprite(BLADE_PIXELS, BLADE_COLORS, 5), "color": (80, 225, 205)},
    "치명타": {"icon": make_sprite(CRIT_PIXELS, CRIT_COLORS, 5), "color": (255, 120, 50)},
    "흡혈": {"icon": make_sprite(DROP_PIXELS, DROP_COLORS, 5), "color": (215, 55, 95)},
    "경험 증가": {"icon": make_sprite(GEM_PIXELS, GEM_COLORS, 5), "color": (130, 200, 255)},
    "무적 연장": {"icon": make_sprite(SHIELD_PIXELS, SHIELD_COLORS, 5), "color": (150, 170, 255)},
    "번개": {"icon": make_sprite(STORM_PIXELS, STORM_COLORS, 5), "color": (255, 235, 90)},
    "오라": {"icon": make_sprite(AURA_PIXELS, AURA_COLORS, 5), "color": (210, 130, 255)},
    "폭발탄": {"icon": make_sprite(BLAST_PIXELS, BLAST_COLORS, 5), "color": (255, 130, 50)},
    "질주": {"icon": make_sprite(DASH_PIXELS, DASH_COLORS, 5), "color": (110, 255, 170)},
    "냉기": {"icon": make_sprite(FROST_PIXELS, FROST_COLORS, 5), "color": (120, 210, 255)},
    "불꽃검": {"icon": make_weapon_icon("flame", ((255, 110, 40), (255, 230, 120), (110, 50, 30)), 4),
            "color": (255, 130, 50)},
    "보호막": {"icon": make_sprite(SHIELD_PIXELS, BARRIER_COLORS, 5), "color": (110, 225, 235)},
}

for _k, _v in NEW_SKILLS.items():
    upgrade_style[_k] = {"icon": make_sprite(_v["icon"][0], _v["icon"][1], 5), "color": _v["color"]}
small_icons = {n: pygame.transform.scale(s["icon"], (24, 24)) for n, s in upgrade_style.items()}
for _name, _data in SKILL_EVOLUTIONS.items():
    upgrades[_name] = _data["desc"]
    if _name == "화염 폭풍":
        _icon = make_weapon_icon("flame", ((255, 90, 35), (255, 225, 110), (135, 35, 20)), 5)
    else:
        _icon = make_sprite(STORM_PIXELS, {"c": (105, 205, 220), "y": (220, 255, 230)}, 5)
    upgrade_style[_name] = {"icon": _icon, "color": _data["color"]}
    small_icons[_name] = pygame.transform.scale(_icon, (24, 24))
for _name, _data in RUN_RELICS.items():
    upgrades[_name] = _data["desc"]
    if _name == "화염핵":
        _icon = make_sprite(BLAST_PIXELS, BLAST_COLORS, 5)
    elif _name == "서리독 병":
        _icon = make_sprite(STORM_PIXELS, {"c": (105, 205, 220), "y": (220, 255, 230)}, 5)
    else:
        _icon = make_sprite(CRIT_PIXELS, CRIT_COLORS, 5)
    upgrade_style[_name] = {"icon": _icon, "color": _data["color"]}
    small_icons[_name] = pygame.transform.scale(_icon, (24, 24))

# ------------------------------------------------------------
# 5-2) 스테이지 / 업적 / 영구 강화 / 무기 / 저장 데이터
# ------------------------------------------------------------
# 스테이지: 0번은 무한 모드(원래 방식), 1~3번은 보스를 쓰러뜨리면 클리어예요.
# pool: (적 종류, 가중치, 등장 시작 프레임) / bosses: (보스, 등장 프레임, 체력 배율) - 마지막 보스가 최종 보스
# haz: 하늘에서 떨어지는 위험 구역 (rate는 간격 프레임, r은 반지름)
POOL_DUNGEON = [("slime", 10, 0), ("goblin", 5, 1200), ("jelly", 2, 1800), ("mage", 2, 2400), ("boar", 2, 3000)]
POOL_ICE = [("slime", 6, 0), ("bat", 6, 600), ("goblin", 5, 900), ("jelly", 3, 1500),
            ("mage", 3, 2000), ("boar", 3, 2600)]
POOL_LAVA = [("slime", 3, 0), ("goblin", 6, 0), ("boar", 5, 600), ("bat", 5, 900),
             ("mage", 5, 1500), ("jelly", 3, 1800)]

STAGES = {
    0: {"name": "무한 모드", "style": "dungeon", "pool": POOL_DUNGEON, "bosses": None, "haz": None,
        "hp_add": 0, "spd_add": 0.0, "interval": 75, "reward": 0,
        "glow": glow_torch, "mote": (110, 110, 150),
        "desc": "끝없이 몰려오는 적을 버텨라\n최고 기록에 도전해요"},
    1: {"name": "고블린 던전", "style": "dungeon", "pool": POOL_DUNGEON,
        "bosses": [("orc", 5400, 1.0), ("dragon", 12600, 1.0)], "haz": None,
        "hp_add": 0, "spd_add": 0.0, "interval": 75, "reward": 300,
        "glow": glow_torch, "mote": (110, 110, 150),
        "desc": "오크 대장 -> 드래곤을 쓰러뜨려요\n(약 3분 30초)"},
    2: {"name": "얼어붙은 동굴", "style": "ice", "pool": POOL_ICE,
        "bosses": [("orc", 4200, 1.4), ("golem", 10800, 1.2)],
        "haz": {"rate": 150, "r": 34, "color": (110, 190, 255), "light": (225, 245, 255)},
        "hp_add": 1, "spd_add": 0.2, "interval": 68, "reward": 500,
        "glow": make_glow(95, (30, 70, 130)), "mote": (170, 200, 240),
        "desc": "고드름이 떨어져요! 오크 -> 골렘\n(약 3분)"},
    3: {"name": "용암 지옥", "style": "lava", "pool": POOL_LAVA,
        "bosses": [("orc", 3600, 1.8), ("golem", 8400, 1.4), ("dragon", 13200, 2.2)],
        "haz": {"rate": 110, "r": 46, "color": (255, 100, 40), "light": (255, 220, 120)},
        "hp_add": 2, "spd_add": 0.4, "interval": 60, "reward": 800,
        "glow": make_glow(95, (150, 55, 20)), "mote": (255, 120, 40),
        "desc": "용암이 솟아요! 오크, 골렘, 드래곤\n(약 3분 40초)"},
}

# ───────── 새 스테이지 (4~6) ─────────
# 눈/용암 지역은 전용 외형의 몬스터가 주로 나타나요.
POOL_ICE[:] = [("ice_jelly", 7, 0), ("ice_wisp", 4, 0), ("frost_wolf", 5, 500),
               ("ice_mage", 3, 1100), ("yeti", 3, 1700)]
POOL_LAVA[:] = [("magma_slime", 7, 0), ("imp", 5, 400), ("ash_hound", 4, 900),
                ("fire_mage", 3, 1500)]
STAGES.update({
    4: {"name": "망자의 묘지", "style": "grave",
        "pool": [("skeleton", 8, 0), ("ghost", 5, 700), ("bat", 3, 1200), ("mummy", 4, 1800)],
        "bosses": [("orc", 4800, 2.0), ("golem", 9600, 1.8), ("dragon", 14400, 2.6)],
        "haz": {"rate": 100, "r": 40, "color": (110, 230, 150), "light": (225, 255, 235)},
        "hp_add": 3, "spd_add": 0.5, "interval": 56, "reward": 1100,
        "glow": make_glow(95, (30, 110, 70)), "mote": (150, 255, 190),
        "desc": "해골과 유령이 깨어난 묘지\n저주받은 불꽃이 떨어져요 (약 4분)"},
    5: {"name": "불타는 사막", "style": "desert",
        "pool": [("scorpion", 8, 0), ("mummy", 6, 600), ("raider", 5, 1100), ("sand_boar", 3, 1900)],
        "bosses": [("golem", 4200, 2.2), ("orc", 9000, 2.4), ("dragon", 14400, 3.0)],
        "haz": {"rate": 95, "r": 48, "color": (235, 185, 80), "light": (255, 240, 180)},
        "hp_add": 4, "spd_add": 0.6, "interval": 54, "reward": 1500,
        "glow": make_glow(95, (150, 100, 30)), "mote": (240, 200, 120),
        "desc": "전갈과 미라가 사는 사막\n모래 기둥이 솟아올라요 (약 4분)"},
    6: {"name": "독 늪", "style": "swamp",
        "pool": [("toad", 8, 0), ("shroom", 5, 600), ("bat", 3, 900), ("jelly", 3, 1500), ("ghost", 3, 2000)],
        "bosses": [("golem", 4800, 2.6), ("orc", 9600, 3.0), ("dragon", 15600, 3.8)],
        "haz": {"rate": 90, "r": 50, "color": (140, 225, 70), "light": (230, 255, 160)},
        "hp_add": 5, "spd_add": 0.8, "interval": 50, "reward": 2200,
        "glow": make_glow(95, (60, 120, 20)), "mote": (170, 240, 90),
        "desc": "독 두꺼비와 버섯의 늪\n독 웅덩이가 터져요 (약 4분 20초)"},
})

# 업적: 달성하면 골드를 받아요 (check_achievements가 조건을 확인해요)
ACHIEVEMENTS = [
    {"key": "kill100", "name": "사냥꾼", "desc": "적 100마리 처치", "reward": 100},
    {"key": "kill1000", "name": "학살자", "desc": "적 1000마리 처치", "reward": 500},
    {"key": "survive5", "name": "끈질긴 생존자", "desc": "한 판에서 5분 생존", "reward": 300},
    {"key": "level15", "name": "성장의 길", "desc": "한 판에서 Lv.15 달성", "reward": 200},
    {"key": "combo50", "name": "연쇄 학살", "desc": "50콤보 달성", "reward": 200},
    {"key": "boss1", "name": "보스 사냥", "desc": "보스 처치", "reward": 150},
    {"key": "elite10", "name": "엘리트 헌터", "desc": "엘리트 적 10마리 처치", "reward": 200},
    {"key": "clear1", "name": "던전 정복", "desc": "스테이지 1 클리어", "reward": 300},
    {"key": "clear2", "name": "동굴 정복", "desc": "스테이지 2 클리어", "reward": 500},
    {"key": "clear3", "name": "지옥 정복", "desc": "스테이지 3 클리어", "reward": 800},
    {"key": "allclear", "name": "전설의 용사", "desc": "모든 스테이지 클리어", "reward": 1500},
    {"key": "rich", "name": "부자", "desc": "골드 3000 이상 보유", "reward": 300},
]

MAX_STAR = 5         # 무기 최대 별 (같은 무기를 또 뽑으면 별이 올라요)
PULL_COST = 300      # 1회 뽑기 가격
PULL10_COST = 2700   # 10회 뽑기 가격 (10% 할인)
DUP_REFUND = 100     # 별이 이미 최대일 때 돌려받는 골드
PITY_LIMIT = 30      # 이만큼 못 뽑으면 전설 확정

# 영구 강화: base 가격 x (1 + 0.7 x 현재 단계)
META_DEFS = [
    {"key": "hp", "name": "튼튼한 몸", "desc": "시작 체력 +1", "max": 4, "base": 150,
     "icon": "최대 체력", "color": (255, 110, 130)},
    {"key": "atk", "name": "날카로운 날", "desc": "공격력 +8%", "max": 8, "base": 120,
     "icon": "공격력", "color": (235, 85, 85)},
    {"key": "spd", "name": "가벼운 발", "desc": "이동 속도 +0.15", "max": 7, "base": 90,
     "icon": "이동 속도", "color": (90, 190, 255)},
    {"key": "pick", "name": "자석 손", "desc": "줍기 범위 +6", "max": 8, "base": 80,
     "icon": "줍기 범위", "color": (175, 125, 255)},
    {"key": "xp", "name": "배움의 길", "desc": "경험치 +6%", "max": 8, "base": 110,
     "icon": "경험 증가", "color": (130, 200, 255)},
    {"key": "crit", "name": "급소 노리기", "desc": "치명타 확률 +2%", "max": 7, "base": 130,
     "icon": "치명타", "color": (255, 120, 50)},
    {"key": "gold", "name": "황금 손", "desc": "골드 획득 +10%", "max": 8, "base": 100,
     "icon": None, "color": (255, 210, 70)},
    {"key": "revive", "name": "불사의 부적", "desc": "죽어도 한 번 부활", "max": 1, "base": 1500,
     "icon": "무적 연장", "color": (150, 170, 255)},
]


def meta_cost(d, lv):
    return int(round(d["base"] * (1 + 0.7 * lv) / 10) * 10)


RARITY = {
    "common": {"name": "일반", "color": (175, 185, 205), "w": 60},
    "rare": {"name": "희귀", "color": (90, 170, 255), "w": 28},
    "epic": {"name": "영웅", "color": (195, 115, 255), "w": 10},
    "legend": {"name": "전설", "color": (255, 195, 60), "w": 2},
}
RARITY_ORDER = ["common", "rare", "epic", "legend"]

# 무기: c = (날 색, 밝은 색, 손잡이 색), 나머지는 능력치 (별 1개 기준, 별이 늘 때마다 +20%)
# atk 공격력 / spd 공격속도 / crit 치명타(%) / pick 줍기범위 / xp 경험치 / gold 골드 / move 이동속도 / hp 체력(+고정) / start 시작 스킬
WEAPONS = {
    "wood_sword": {"name": "나무 검", "rarity": "common", "shape": "sword",
                   "c": ((150, 105, 60), (205, 155, 95), (100, 65, 35)), "atk": 0.05, "spd": 0.04},
    "dagger": {"name": "낡은 단검", "rarity": "common", "shape": "dagger",
               "c": ((170, 175, 190), (235, 240, 250), (110, 80, 50)), "spd": 0.08, "crit": 2},
    "novice_staff": {"name": "수련 지팡이", "rarity": "common", "shape": "staff",
                     "c": ((120, 200, 255), (230, 250, 255), (120, 85, 50)), "pick": 14, "xp": 0.05},
    "stone_spear": {"name": "돌 창", "rarity": "common", "shape": "spear",
                    "c": ((150, 150, 160), (210, 210, 220), (125, 90, 55)), "atk": 0.07, "gold": 0.05},
    "iron_sword": {"name": "철제 검", "rarity": "rare", "shape": "sword",
                   "c": ((150, 175, 210), (235, 245, 255), (90, 70, 60)), "atk": 0.12, "spd": 0.05},
    "hunter_bow": {"name": "사냥꾼의 활", "rarity": "rare", "shape": "bow",
                   "c": ((95, 175, 95), (210, 255, 210), (130, 90, 50)), "spd": 0.12, "crit": 4},
    "battle_axe": {"name": "전투 도끼", "rarity": "rare", "shape": "axe",
                   "c": ((170, 180, 200), (240, 245, 255), (120, 80, 45)), "atk": 0.18, "gold": 0.06},
    "thunder_spear": {"name": "번개 창", "rarity": "epic", "shape": "spear",
                      "c": ((255, 230, 90), (255, 255, 215), (70, 70, 110)), "atk": 0.10, "start": "번개"},
    "frost_staff": {"name": "서리 지팡이", "rarity": "epic", "shape": "staff",
                    "c": ((110, 210, 255), (230, 255, 255), (150, 190, 230)), "xp": 0.10, "spd": 0.05,
                    "start": "냉기"},
    "vampire_fang": {"name": "붉은 송곳니", "rarity": "epic", "shape": "dagger",
                     "c": ((215, 55, 95), (255, 150, 170), (60, 30, 50)), "crit": 6, "spd": 0.06,
                     "start": "재생"},
    "flame_greatsword": {"name": "불꽃의 대검", "rarity": "legend", "shape": "flame",
                         "c": ((255, 110, 40), (255, 230, 120), (110, 50, 30)), "atk": 0.15, "spd": 0.05,
                         "start": "불꽃검"},
    "holy_sword": {"name": "용사의 성검", "rarity": "legend", "shape": "sword",
                   "c": ((255, 235, 150), (255, 255, 240), (230, 190, 70)), "atk": 0.18, "crit": 6, "hp": 1},
}


# 장비/룬/펫 데이터. 한 줄 = key, 이름, 등급, 모양, (날색, 밝은색, 테두리색), 능력치
def _items(slot, rows):
    for key, name, rar, shape, c, extra in rows:
        WEAPONS[key] = {"name": name, "slot": slot, "rarity": rar, "shape": shape, "c": c, **extra}


for _w in WEAPONS.values():
    _w.setdefault("slot", "weapon")
# 능력치: atk 공격력 / spd 공격속도 / crit 치명타 / pick 줍기 / xp 경험치 / gold 골드 / move 이동 / hp 체력 / inv 무적(프레임) / dash 대시쿨(프레임) / start 시작 스킬
_items("armor", [
    ("a_leather", "가죽 갑옷", "common", "armor", ((150, 100, 60), (205, 155, 100), (95, 60, 35)), {"inv": 8, "move": 0.1}),
    ("a_robe", "수련 로브", "common", "robe", ((90, 120, 200), (170, 200, 255), (230, 200, 90)), {"xp": 0.06, "pick": 10}),
    ("a_chain", "사슬 갑옷", "rare", "armor", ((150, 160, 180), (225, 230, 245), (80, 85, 100)), {"hp": 1, "inv": 10}),
    ("a_knight", "기사의 갑옷", "rare", "armor", ((170, 180, 200), (240, 245, 255), (200, 60, 60)), {"atk": 0.08, "inv": 14}),
    ("a_mage", "마도사 로브", "epic", "robe", ((140, 80, 210), (210, 170, 255), (255, 210, 90)), {"xp": 0.10, "spd": 0.05, "start": "오라"}),
    ("a_guard", "수호자의 갑옷", "epic", "armor", ((90, 200, 215), (210, 250, 255), (40, 90, 110)), {"hp": 1, "inv": 10, "start": "보호막"}),
    ("a_dragon", "용린 갑옷", "legend", "armor", ((220, 70, 55), (255, 190, 120), (90, 30, 30)), {"hp": 2, "atk": 0.10, "inv": 14, "start": "가시 갑옷"}),
])
_items("acc", [
    ("t_copper", "구리 반지", "common", "ring", ((205, 125, 70), (255, 190, 130), (110, 60, 30)), {"crit": 2, "gold": 0.05}),
    ("t_charm", "행운 부적", "common", "amulet", ((90, 200, 120), (200, 255, 210), (110, 80, 40)), {"gold": 0.10, "pick": 8}),
    ("t_boots", "날쌘 장화", "rare", "boots", ((130, 95, 60), (200, 160, 110), (240, 240, 240)), {"move": 0.3, "dash": 15}),
    ("t_magnet", "자석 목걸이", "rare", "amulet", ((220, 70, 70), (255, 170, 170), (120, 120, 140)), {"pick": 24, "xp": 0.06}),
    ("t_ruby", "루비 반지", "epic", "ring", ((230, 60, 90), (255, 170, 190), (235, 195, 80)), {"atk": 0.10, "crit": 5, "start": "폭발탄"}),
    ("t_wind", "바람의 장화", "epic", "boots", ((110, 230, 190), (220, 255, 245), (255, 255, 255)), {"move": 0.25, "dash": 22, "start": "이동 속도"}),
    ("t_crown", "왕의 왕관", "legend", "crown", ((255, 215, 80), (255, 250, 200), (230, 70, 90)), {"xp": 0.12, "gold": 0.15, "atk": 0.08, "hp": 1}),
])
_items("rune", [
    ("r_power", "힘의 룬", "common", "rune", ((255, 110, 90), (255, 200, 190), (60, 20, 25)), {"atk": 0.06}),
    ("r_wisdom", "지혜의 룬", "common", "rune", ((90, 170, 255), (200, 230, 255), (20, 40, 70)), {"xp": 0.08}),
    ("r_wind", "질풍의 룬", "rare", "rune", ((110, 240, 170), (210, 255, 230), (20, 60, 45)), {"spd": 0.08, "move": 0.2}),
    ("r_greed", "탐욕의 룬", "rare", "rune", ((255, 215, 80), (255, 245, 190), (70, 50, 10)), {"gold": 0.15, "pick": 12}),
    ("r_thunder", "뇌전의 룬", "epic", "rune", ((255, 235, 90), (255, 255, 210), (60, 50, 90)), {"atk": 0.08, "start": "번개"}),
    ("r_guard", "수호의 룬", "epic", "rune", ((100, 225, 235), (225, 255, 255), (20, 60, 70)), {"hp": 1, "start": "보호막"}),
    ("r_chaos", "혼돈의 룬", "legend", "rune", ((200, 110, 255), (245, 210, 255), (50, 20, 80)), {"atk": 0.15, "crit": 8, "start": "혜성"}),
])
# 펫: pcd 공격 간격(프레임) / pshots 발수 / pdmg 피해 배율 / pheal 이 프레임마다 체력 +1
_items("pet", [
    ("p_slime", "슬라임 친구", "common", "pet", ((110, 210, 110), (200, 250, 200), (20, 40, 30)), {"pet": True, "pcd": 100, "pshots": 1, "pdmg": 1}),
    ("p_bat", "아기 박쥐", "common", "petw", ((110, 90, 160), (190, 170, 230), (255, 80, 80)), {"pet": True, "pcd": 75, "pshots": 1, "pdmg": 1}),
    ("p_fairy", "숲 요정", "rare", "petw", ((130, 240, 170), (230, 255, 240), (30, 70, 50)), {"pet": True, "pcd": 110, "pshots": 1, "pdmg": 1, "pheal": 1500}),
    ("p_wolf", "새끼 늑대", "rare", "pet", ((160, 170, 190), (235, 240, 250), (30, 30, 50)), {"pet": True, "pcd": 55, "pshots": 1, "pdmg": 2}),
    ("p_phoenix", "불사조", "epic", "petw", ((255, 130, 50), (255, 225, 120), (80, 30, 20)), {"pet": True, "pcd": 80, "pshots": 3, "pdmg": 2, "pheal": 2400}),
    ("p_dragon", "아기 용", "legend", "petw", ((220, 70, 70), (255, 190, 110), (40, 15, 20)), {"pet": True, "pcd": 60, "pshots": 3, "pdmg": 3, "pheal": 1800}),
])
_items("weapon", [
    ("bronze_sword", "청동 검", "common", "sword", ((205, 135, 70), (255, 200, 130), (100, 65, 35)), {"atk": 0.06, "spd": 0.03}),
    ("short_bow", "단궁", "common", "bow", ((150, 120, 80), (230, 205, 160), (110, 80, 50)), {"spd": 0.10, "pick": 8}),
    ("knight_lance", "기사의 창", "rare", "spear", ((190, 200, 225), (245, 248, 255), (150, 50, 50)), {"atk": 0.14, "crit": 3}),
    ("wind_dagger", "바람 단검", "rare", "dagger", ((120, 235, 200), (225, 255, 245), (60, 90, 80)), {"spd": 0.14, "move": 0.2}),
    ("venom_dagger", "독니 단검", "epic", "dagger", ((130, 225, 80), (215, 255, 160), (50, 45, 70)), {"crit": 4, "spd": 0.06, "start": "독 구름"}),
    ("star_staff", "별빛 지팡이", "epic", "staff", ((255, 230, 120), (255, 252, 210), (110, 80, 160)), {"xp": 0.08, "spd": 0.05, "start": "별빛 난사"}),
    ("rage_axe", "광전사의 도끼", "epic", "axe", ((235, 80, 60), (255, 190, 170), (80, 45, 40)), {"atk": 0.14, "start": "광폭화"}),
    ("time_staff", "시간의 지팡이", "legend", "staff", ((130, 190, 255), (235, 248, 255), (190, 200, 230)), {"xp": 0.12, "spd": 0.08, "start": "시간 정지"}),
])
ALL_ORDER = list(WEAPONS.keys())
WEAPON_ORDER = [k for k in ALL_ORDER if WEAPONS[k]["slot"] == "weapon"]  # 상점이 지금 보여주는 분류의 목록
WEAPONS_BY_RARITY = {r: [k for k, v in WEAPONS.items() if v["rarity"] == r] for r in RARITY_ORDER}
SCALED_KEYS = ("atk", "spd", "pick", "xp", "crit", "gold", "move", "inv", "dash")


def weapon_stats(wid, star=None):
    """무기의 능력치 합계 (별 개수 반영). 장착한 무기가 없으면 전부 0이에요."""
    out = {k: 0 for k in SCALED_KEYS}
    out["hp"] = 0
    out["start"] = []
    w = WEAPONS.get(wid)
    if not w:
        return out
    if star is None:
        star = weapon_stars.get(wid, 1)
    f = 1 + 0.2 * (star - 1)
    for k in SCALED_KEYS:
        out[k] = w.get(k, 0) * f
    out["hp"] = w.get("hp", 0)
    if w.get("start"):
        out["start"] = [w["start"]] * (2 if star >= MAX_STAR else 1)  # 별 5개면 시작 스킬 2단계
    return out


def load_save():
    """save.json (없으면 예전 best.json)을 읽어요. 깨진 값은 안전한 값으로 고쳐요."""
    global best_time, best_kills, gold, meta_levels, weapon_stars, equipped_weapon, pity_by_slot
    global stages_cleared, stage_best, total_kills, total_bosses, total_elites, achv_done
    data = {}
    for path in (SAVE_PATH, OLD_BEST_PATH):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
                break
        except (OSError, ValueError):
            continue

    def num(key, default=0):
        try:
            return max(0, int(data.get(key, default)))
        except (TypeError, ValueError):
            return default

    best_time = num("best_time", num("time"))
    best_kills = num("best_kills", num("kills"))
    gold = num("gold")
    raw_pity = data.get("pity_by_slot")
    pity_by_slot = {}
    for slot in PITY_SLOTS:
        if isinstance(raw_pity, dict):
            try:
                slot_pity = int(raw_pity.get(slot, 0))
            except (TypeError, ValueError):
                slot_pity = 0
        else:
            # 예전 저장 파일의 공용 횟수는 기존 무기 뽑기 진행도로 보존해요.
            slot_pity = num("pity") if slot == "weapon" else 0
        pity_by_slot[slot] = max(0, min(PITY_LIMIT - 1, slot_pity))
    total_kills = num("total_kills")
    total_bosses = num("total_bosses")
    total_elites = num("total_elites")
    raw_meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    meta_levels = {}
    for d in META_DEFS:
        try:
            lv = int(raw_meta.get(d["key"], 0))
        except (TypeError, ValueError):
            lv = 0
        meta_levels[d["key"]] = max(0, min(d["max"], lv))
    raw_w = data.get("weapons") if isinstance(data.get("weapons"), dict) else {}
    weapon_stars = {}
    for wid in WEAPONS:
        if wid in raw_w:
            try:
                weapon_stars[wid] = max(1, min(MAX_STAR, int(raw_w[wid])))
            except (TypeError, ValueError):
                weapon_stars[wid] = 1
    if not weapon_stars:  # 처음 시작하면 나무 검을 줘요
        weapon_stars["wood_sword"] = 1
    eq = data.get("equipped")
    equipped_weapon = eq if eq in weapon_stars else next(iter(weapon_stars))
    raw_g = data.get("gear") if isinstance(data.get("gear"), dict) else {}
    for sl in equipped_gear:
        gid = raw_g.get(sl)
        equipped_gear[sl] = gid if (gid in weapon_stars and WEAPONS[gid]["slot"] == sl.rstrip("2")) else ""

    # 스테이지 클리어 기록 / 업적
    raw_sc = data.get("stages_cleared")
    stages_cleared = set()
    if isinstance(raw_sc, list):
        for x in raw_sc:
            if isinstance(x, int) and x in range(1, 7):
                stages_cleared.add(x)
    raw_sb = data.get("stage_best") if isinstance(data.get("stage_best"), dict) else {}
    stage_best = {}
    for k, v in raw_sb.items():
        try:
            if k in [str(i) for i in range(1, 7)] and int(v) > 0:
                stage_best[k] = int(v)
        except (TypeError, ValueError):
            continue
    raw_a = data.get("achv") if isinstance(data.get("achv"), dict) else {}
    achv_done = {a["key"]: True for a in ACHIEVEMENTS if raw_a.get(a["key"])}


def save_game():
    data = {"best_time": best_time, "best_kills": best_kills, "gold": gold, "meta": meta_levels,
            "weapons": weapon_stars, "equipped": equipped_weapon, "gear": equipped_gear,
            "pity_by_slot": pity_by_slot, "pity": pity_by_slot["weapon"],
            "stages_cleared": sorted(stages_cleared), "stage_best": stage_best,
            "total_kills": total_kills, "total_bosses": total_bosses, "total_elites": total_elites,
            "achv": achv_done}
    tmp = SAVE_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, SAVE_PATH)  # 저장 도중 꺼져도 파일이 깨지지 않게 바꿔치기해요
    except OSError:
        pass  # 저장 못 해도 게임은 계속돼요


load_save()

# 적 종류별 골드 (황금 손 강화로 늘어나요)
GOLD_VALUE = {"slime": 1, "goblin": 2, "mage": 3, "boar": 3, "jelly": 3, "mini": 1, "bat": 2,
              "orc": 40, "dragon": 100, "golem": 70}


# ------------------------------------------------------------
# 6) 게임 상태 초기화 / 종료
# ------------------------------------------------------------
def reset_game():
    """판이 시작될 때마다 바뀌는 값들을 처음 상태로 되돌려요. (cur_stage에 맞는 스테이지로 시작해요)"""
    global player_pos, player_speed, player_hp, player_max_hp, invuln_timer
    global enemies, enemy_speed, enemy_hp, spawn_interval, spawn_timer
    global projectiles, projectile_damage, fire_interval, fire_timer
    global extra_shots, pierce_level, blade_count, blade_angle
    global gems, pickup_range, xp, level, xp_to_next
    global particles, floaters, shake, hurt_flash
    global fires, banner_text, banner_timer, banner_color, banner_blink, next_boss_frame, boss_count
    global crit_percent, heal_every, heal_progress, xp_level, invuln_level
    global choices, state, kills, game_over, survive_frames, level_up_anim, new_record
    global rerolls_left
    global dash_timer, dash_cd, dash_dir, skill_levels, drops, next_wave_frame
    global chests, chest_mode
    global lightning_level, aura_level, blast_level, dash_cd_max, frost_level
    global lightning_timer, aura_timer, bolts, rings, ghosts
    global enemy_shots
    global dmg_mult, xp_bonus, gold_mult, revive_left, flame_level, flame_timer, flames
    global weapon_swing, run_gold
    global cur_def, stage_bg, stage_boss_idx, meteors, meteor_timer
    global combo, combo_timer, best_combo, run_elites, run_bosses
    global altar_pos, altar_used, altar_next_frame, skill_evolutions
    global run_relics, run_relic_offer_count, pending_relic_offers, relic_choices
    global shield_level, shield_hp, shield_timer, stage_cleared, stage_clear_pending
    global xt, pet_id, pet_pos, pet_timer, pet_heal, inv_bonus
    enemy_shots = []

    cur_def = STAGES[cur_stage]       # 이번 판의 스테이지 정보
    stage_bg = stage_bgs[cur_stage]   # 이번 판의 바닥 그림
    stage_boss_idx = 0                # 다음에 나올 스테이지 보스 번호
    meteors = []                      # 하늘에서 떨어지는 위험 구역 (고드름 / 용암)
    meteor_timer = 0
    combo = 0                         # 연속 처치 수
    combo_timer = 0
    best_combo = 0
    run_elites = 0                    # 이번 판에 잡은 엘리트 / 보스 수 (업적용)
    run_bosses = 0
    altar_pos = None
    altar_used = False
    altar_next_frame = random.randint(3000, 4500)  # 한 판에 한 번, 50~75초 사이
    run_relics = set()
    run_relic_offer_count = 0
    pending_relic_offers = 0
    relic_choices = []
    shield_level = 0                  # 보호막: 단계만큼 보호막이 생겨요
    shield_hp = 0
    shield_timer = 0
    stage_cleared = False
    stage_clear_pending = False

    player_pos = pygame.Vector2(WIDTH / 2, HEIGHT / 2)
    player_speed = 4
    player_max_hp = 3
    player_hp = player_max_hp
    invuln_timer = 0  # 맞은 뒤 남은 무적 프레임 수
    dash_timer = 0    # 대시가 남은 프레임
    dash_cd = 0       # 다시 쓸 수 있을 때까지 남은 프레임
    dash_dir = pygame.Vector2(0, 0)

    enemies = []
    enemy_speed = 1.5 + cur_def["spd_add"]
    enemy_hp = 3 + cur_def["hp_add"]
    spawn_interval = cur_def["interval"]
    spawn_timer = 0

    projectiles = []
    projectile_damage = 1
    fire_interval = 30
    fire_timer = 0
    extra_shots = 0   # 멀티샷: 기본 1발에 더해지는 발수
    pierce_level = 0  # 관통: 몇 명까지 더 뚫는지
    blade_count = 0   # 회전 칼날 개수
    blade_angle = 0

    gems = []
    pickup_range = 30
    xp = 0
    level = 1
    xp_to_next = 5

    particles = []  # 죽을 때 튀는 파편
    floaters = []   # 떠오르는 데미지 숫자
    shake = 0       # 화면 흔들림 남은 프레임
    hurt_flash = 0  # 맞았을 때 붉은 번쩍임 남은 프레임

    fires = []            # 드래곤 브레스가 남긴 불 (3초 동안 유지)
    banner_text = ""      # 화면 가운데 큰 글씨 ("WARNING" 등)
    banner_timer = 0
    banner_color = (255, 255, 255)
    banner_blink = False
    next_boss_frame = 5400  # (무한 모드) 첫 보스는 1분 30초에 등장 (테스트할 땐 300으로 바꿔보세요)
    boss_count = 0          # 지금까지 나온 보스 수 (무한 모드에서는 오크 -> 드래곤 -> 골렘 순서)

    crit_percent = 0   # 치명타 확률(%)
    heal_every = 0     # 흡혈: 몇 마리 잡을 때마다 체력 1 회복 (0이면 아직 없음)
    heal_progress = 0  # 흡혈: 지금까지 센 처치 수
    xp_level = 0       # 경험 증가 단계 (한 단계마다 구슬 경험치 +25%)
    invuln_level = 0   # 무적 연장 단계 (한 단계마다 무적 +0.25초)

    choices = []
    rerolls_left = 3
    state = "playing"  # "title" / "playing" / "level_up" / "paused"
    kills = 0
    game_over = False
    survive_frames = 0
    level_up_anim = 0
    new_record = False
    skill_levels = {}
    skill_evolutions = set()
    drops = []                # 바닥에 떨어진 아이템
    next_wave_frame = 9000    # 첫 웨이브는 2분 30초 (테스트할 땐 300으로 바꿔보세요)
    chests = []               # 보스가 떨군 상자
    chest_mode = False        # 지금 뜬 카드 선택이 상자 때문인지

    lightning_level = 0   # 번개: 한 번에 떨어지는 낙뢰 수
    lightning_timer = 0
    aura_level = 0        # 오라: 단계마다 범위가 넓어져요
    aura_timer = 0
    blast_level = 0       # 폭발탄: 단계마다 폭발 반경이 커져요
    dash_cd_max = 120     # 질주: 대시 쿨타임(프레임)
    frost_level = 0       # 냉기: 단계마다 더 많이 느려져요
    bolts = []            # 번개 그림 효과
    rings = []            # 폭발 고리 효과
    ghosts = []           # 대시 잔상

    # --- 영구 강화 + 장착 무기 반영 ---
    ws = gear_stats()  # 무기 + 방어구 + 장신구 + 룬 합산
    m = meta_levels
    dmg_mult = 1 + 0.08 * m["atk"] + ws["atk"]
    xp_bonus = 0.06 * m["xp"] + ws["xp"]
    gold_mult = 1 + 0.10 * m["gold"] + ws["gold"]
    revive_left = m["revive"]
    flame_level = 0       # 불꽃검 단계
    flame_timer = 0
    flames = []           # 불꽃검 휘두르는 효과
    weapon_swing = 0      # 무기 휘두르기 애니메이션
    run_gold = 0          # 이번 판에서 모은 골드
    player_max_hp = 3 + m["hp"] + ws["hp"]
    player_hp = player_max_hp
    player_speed = 4 + 0.15 * m["spd"] + ws["move"]
    pickup_range = 30 + 6 * m["pick"] + ws["pick"]
    crit_percent = 2 * m["crit"] + ws["crit"]
    fire_interval = max(10, round(30 * (1 - ws["spd"])))
    inv_bonus = int(ws["inv"])
    dash_cd_max = max(60, 120 - int(ws["dash"]))
    xt = {"comet": 0, "regen": 0, "star": 0, "cloud": 0, "time": 0, "freeze": 0,
          "wave": 0, "soul": 0, "clouds": [], "comets": [], "chain_arcs": []}
    pet_id = equipped_gear["pet"]
    pet_pos = player_pos + pygame.Vector2(30, -30)
    pet_timer = pet_heal = 0
    for sk in ws["start"]:
        apply_upgrade(sk)  # 무기가 주는 시작 스킬


def check_achievements():
    """업적 조건을 확인하고, 새로 달성한 업적은 골드를 주고 알려줘요."""
    global gold
    done_clear = {i: i in stages_cleared for i in range(1, 7)}
    conds = {
        "kill100": total_kills + kills >= 100,
        "kill1000": total_kills + kills >= 1000,
        "survive5": survive_frames >= 18000,
        "level15": level >= 15,
        "combo50": best_combo >= 50,
        "boss1": total_bosses + run_bosses >= 1,
        "elite10": total_elites + run_elites >= 10,
        "clear1": done_clear[1],
        "clear2": done_clear[2],
        "clear3": done_clear[3],
        "allclear": all(done_clear.values()),
        "rich": gold >= 3000,
    }
    for a in ACHIEVEMENTS:
        if not achv_done.get(a["key"]) and conds.get(a["key"]):
            achv_done[a["key"]] = True
            gold += a["reward"]
            show_toast(f"업적 달성!  {a['name']}  +{a['reward']}G", (255, 235, 120))
            snd_level.play()


def end_game(cleared=False):
    """게임오버(또는 스테이지 클리어) 처리 + 최고 기록 갱신 + 번 골드 저장."""
    global game_over, best_time, best_kills, new_record, gold, last_gain, last_bonus, last_clear
    global stage_cleared, total_kills, total_bosses, total_elites
    game_over = True
    stage_cleared = cleared
    secs = survive_frames // 60
    new_record = False
    last_clear = 0
    if cur_stage == 0:  # 무한 모드 기록만 따로 저장해요
        new_record = secs > best_time
        if secs > best_time:
            best_time = secs
        if kills > best_kills:
            best_kills = kills
    if cleared:
        first = cur_stage not in stages_cleared
        stages_cleared.add(cur_stage)
        last_clear = cur_def["reward"] * (2 if first else 1)  # 처음 클리어하면 보상 2배
        prev = stage_best.get(str(cur_stage))
        if prev is None or secs < prev:
            stage_best[str(cur_stage)] = secs
        snd_clear.play()
    last_bonus = secs // 6               # 오래 버틴 보너스 (6초에 1골드)
    last_gain = run_gold + last_bonus + last_clear
    gold += last_gain
    check_achievements()
    total_kills += kills
    total_bosses += run_bosses
    total_elites += run_elites
    save_game()


UPGRADE_CAPS = {"멀티샷": 5, "관통": 5, "회전 칼날": 5, "경험 증가": 5, "무적 연장": 5,
                "번개": 5, "오라": 5, "폭발탄": 5, "냉기": 5, "불꽃검": 5, "보호막": 5}

def is_maxed(name):
    """더 올릴 수 없는 업그레이드는 카드 후보에서 빼요."""
    cap = ATTACK_SKILL_MAX_LEVEL if name in ATTACK_SKILLS else SUPPORT_SKILL_MAX_LEVEL
    if skill_levels.get(name, 0) >= cap:
        return True
    if name in NEW_SKILLS:
        return skill_levels.get(name, 0) >= NEW_SKILLS[name]["max"]
    if name in UPGRADE_CAPS:
        return skill_levels.get(name, 0) >= UPGRADE_CAPS[name]
    if name == "공격 속도":
        return fire_interval <= 8
    if name == "이동 속도":
        return player_speed >= 8
    if name == "줍기 범위":
        return pickup_range >= 220
    if name == "최대 체력":
        return player_max_hp >= 8
    if name == "치명타":
        return crit_percent >= 70
    return False  # 공격력은 끝없이 올라요


def apply_upgrade(name):
    """고른 업그레이드를 실제 숫자에 반영해요."""
    global fire_interval, projectile_damage, player_speed, pickup_range
    global player_max_hp, player_hp, extra_shots, pierce_level, blade_count
    global crit_percent, heal_every, xp_level, invuln_level
    global lightning_level, aura_level, blast_level, dash_cd_max, frost_level
    global flame_level, shield_level, shield_hp, gold_mult
    global dmg_mult
    if name in RUN_RELICS:
        if name in run_relics or len(run_relics) >= MAX_RUN_RELICS:
            return
        run_relics.add(name)
        if name == "화염핵":
            dmg_mult *= 0.95
        elif name == "서리독 병":
            player_speed = max(2.5, player_speed - 0.2)
        else:
            gold_mult *= 0.90
        show_toast(f"유물 획득: {name}", RUN_RELICS[name]["color"])
        spawn_burst(player_pos, RUN_RELICS[name]["color"], 16)
        snd_level.play()
        return
    if name in SKILL_EVOLUTIONS:
        data = SKILL_EVOLUTIONS[name]
        if name in skill_evolutions or not all(
                skill_levels.get(skill, 0) >= data["min_level"] for skill in data["skills"]):
            return
        skill_evolutions.add(name)
        show_toast(f"{name} 진화 완료!", data["color"])
        rings.append({"pos": player_pos.copy(), "r": 115, "life": 24, "max": 24, "color": data["color"]})
        spawn_burst(player_pos, data["color"], 24)
        add_shake(8)
        snd_level.play()
        return
    old_level = skill_levels.get(name, 0)
    skill_levels[name] = old_level + 1
    if old_level == 0:
        for synergy_name, data in SKILL_SYNERGIES.items():
            if name in data["skills"] and synergy_active(synergy_name):
                show_toast(f"{synergy_name} 조합 활성화!", data["color"])
                snd_level.play()
    if name == "재생":
        heal_every = max(14, 46 - 8 * skill_levels[name])
    if name == "행운":
        gold_mult += 0.10
    if name == "공격 속도":
        fire_interval = max(8, fire_interval - 5)
    elif name == "공격력":
        projectile_damage += 1
    elif name == "이동 속도":
        player_speed += 0.25
        dash_cd_max = max(40, dash_cd_max - 8)
    elif name == "줍기 범위":
        pickup_range += 15
    elif name == "최대 체력":
        player_max_hp += 1
        player_hp = min(player_max_hp, player_hp + 1)
    elif name == "멀티샷":
        extra_shots += 1
    elif name == "관통":
        pierce_level += 1
    elif name == "회전 칼날":
        blade_count += 1
    elif name == "치명타":
        crit_percent = min(70, crit_percent + 10)
    elif name == "경험 증가":
        xp_level += 1
    elif name == "무적 연장":
        invuln_level += 1
    elif name == "번개":
        lightning_level += 1
    elif name == "오라":
        aura_level += 1
    elif name == "폭발탄":
        blast_level += 1
    elif name == "냉기":
        frost_level += 1
    elif name == "불꽃검":
        flame_level += 1
    elif name == "보호막":
        shield_level += 1
        shield_hp += 1  # 고르자마자 한 장이 생겨요


def preview_text(name):
    """이 업그레이드를 고르면 숫자가 어떻게 바뀌는지 보여줘요."""
    if name in NEW_SKILLS:
        return NEW_SKILLS[name]["prev"](skill_levels.get(name, 0))
    if name == "공격 속도":
        return f"간격 {fire_interval} -> {max(8, fire_interval - 5)}"
    if name == "공격력":
        return f"데미지 {projectile_damage} -> {projectile_damage + 1}"
    if name == "이동 속도":
        return f"이동 속도 {player_speed:g} -> {player_speed + 0.25:g} · 대시 대기 {dash_cd_max / 60:.1f}초 -> {max(40, dash_cd_max - 8) / 60:.1f}초"
    if name == "줍기 범위":
        return f"범위 {pickup_range} -> {pickup_range + 15}"
    if name == "최대 체력":
        return f"최대 HP {player_max_hp} -> {player_max_hp + 1}"
    if name == "멀티샷":
        return f"발사 수 {1 + extra_shots} -> {2 + extra_shots}"
    if name == "관통":
        return f"관통 {pierce_level} -> {pierce_level + 1}"
    if name == "치명타":
        return f"확률 {crit_percent}% -> {min(70, crit_percent + 10)}%"
    if name == "경험 증가":
        return f"경험치 +{25 * xp_level}% -> +{25 * (xp_level + 1)}%"
    if name == "무적 연장":
        return f"무적 {(60 + 15 * invuln_level) / 60:g} -> {(75 + 15 * invuln_level) / 60:g}초"
    if name == "번개":
        return f"낙뢰 {lightning_level} -> {lightning_level + 1}발"
    if name == "오라":
        return f"범위 {aura_radius(aura_level)} -> {aura_radius(aura_level + 1)}"
    if name == "폭발탄":
        return f"반경 {blast_radius(blast_level)} -> {blast_radius(blast_level + 1)} · 연쇄 {10 + 4 * blast_level}% -> {14 + 4 * blast_level}%"
    if name == "냉기":
        return f"감속 {round((1 - frost_factor(frost_level)) * 100)}% -> {round((1 - frost_factor(frost_level + 1)) * 100)}%"
    if name == "불꽃검":
        if flame_level == 0:
            return f"피해 {flame_damage(1)}  쿨 {flame_cd(1) / 60:.1f}초"
        return f"피해 {flame_damage(flame_level)} -> {flame_damage(flame_level + 1)}"
    if name == "보호막":
        return f"보호막 {shield_level} -> {shield_level + 1}장"
    return f"칼날 {blade_count} -> {blade_count + 1}"


# ------------------------------------------------------------
# 7) 전투 도우미 함수 (타격감 포함)
# ------------------------------------------------------------
def damage_enemy(e, dmg, quiet=False):
    """적에게 피해를 주고, 하얗게 번쩍이게 하고, 데미지 숫자를 띄워요."""
    dmg = dmg * dmg_mult  # 영구 강화 + 무기 배율 (소수점은 확률로 올림해서 평균이 맞아요)
    if skill_levels.get("광폭화") and player_hp * 2 <= player_max_hp:
        # 최대 레벨에서도 분노 피해 증가는 +50%로 제한해 다른 공격 강화와의 중첩 폭주를 막습니다.
        dmg *= 1 + 0.10 * skill_levels["광폭화"]
    if (e.get("boss") or e.get("mini_boss")) and skill_levels.get("보스 사냥꾼"):
        # 메인 보스와 미니 보스에 적용하되, 5레벨 보너스는 +60%로 제한합니다.
        dmg *= 1 + 0.12 * skill_levels["보스 사냥꾼"]
    if (e.get("boss") or e.get("elite")) and "사냥꾼의 문장" in run_relics:
        dmg *= 1.15
    focus_level = skill_levels.get("연쇄 집중", 0)
    if focus_level and combo >= 5:
        dmg *= 1 + min(0.25, (combo // 5) * 0.01 * focus_level)
    whole = int(dmg)
    if random.random() < dmg - whole:
        whole += 1
    dmg = max(1, whole)
    crit = random.random() * 100 < crit_percent  # 치명타: 확률적으로 2배 피해
    if crit:
        dmg *= 2
    e["hp"] -= dmg
    e["flash"] = 4
    if not quiet:  # 오라/폭발 같은 연속 피해는 소리와 불꽃을 생략해요
        snd_hit.play()
        spawn_burst(e["pos"], (255, 245, 200), 2)  # 맞은 곳에서 작은 불꽃이 튀어요
    if len(floaters) < 40:
        floaters.append({
            "pos": e["pos"] + pygame.Vector2(random.randint(-8, 8), -16),
            "text": f"{dmg}!" if crit else str(dmg),
            "color": (255, 220, 80) if crit else (255, 255, 255),  # 치명타는 노란 숫자
            "life": 30,
        })


def spawn_burst(pos, color, n=8):
    """죽은 자리에서 작은 파편이 사방으로 튀어요."""
    for _ in range(n):
        if len(particles) >= 150:
            break
        speed = random.uniform(1.5, 4.5)
        particles.append({
            "pos": pos.copy(),
            "vel": pygame.Vector2(speed, 0).rotate(random.uniform(0, 360)),
            "life": random.randint(18, 30),
            "color": color,
        })


def explode(pos):
    """폭발탄: 맞은 자리 주변 적에게 피해를 주고 고리 효과를 남겨요."""
    evolved_fire = "화염 폭풍" in skill_evolutions
    r = blast_radius(blast_level) * (1.15 if evolved_fire else 1.0)
    if "화염핵" in run_relics:
        r *= 1.15
    ring_color = (255, 95, 35) if evolved_fire else (255, 150, 60)
    rings.append({"pos": pos.copy(), "r": r, "life": 14, "max": 14, "color": ring_color})
    for o in enemies:
        if o["hp"] > 0 and o["pos"].distance_to(pos) < r + enemy_types[o["kind"]]["radius"]:
            damage_enemy(o, max(1, projectile_damage // 2), quiet=True)
            if synergy_active("화염 폭발"):
                burn_duration = 120 if evolved_fire else 75
                o["burn"] = max(o.get("burn", 0), burn_duration)
                o["burn_dmg"] = max(o.get("burn_dmg", 0), max(1, flame_burn(flame_level) // 2))
    spawn_burst(pos, (255, 170, 70), 6)


def spawn_evolved_poison_cloud(pos):
    if "빙독 폭풍" not in skill_evolutions:
        return False
    active = sum(1 for cloud in xt["clouds"] if cloud.get("evolved"))
    if active >= 2:
        return False
    level = skill_levels.get("독 구름", 0)
    radius = (28 + 3 * level) * (1.2 if "서리독 병" in run_relics else 1.0)
    xt["clouds"].append({"pos": pos.copy(), "life": 60, "r": radius, "evolved": True})
    spawn_burst(pos, (115, 235, 210), 8)
    return True


def get_blade_positions():
    """회전 칼날들의 (위치, 각도) 목록. 그리기와 충돌 검사가 같이 써요."""
    result = []
    for i in range(blade_count):
        ang = blade_angle + 360 * i / blade_count
        result.append((player_pos + pygame.Vector2(blade_orbit, 0).rotate(ang), ang))
    return result


# ------------------------------------------------------------
# 7-2) 플레이어 피해 + 보스
# ------------------------------------------------------------
def angle_of(v):
    """벡터가 가리키는 방향을 각도(도)로 바꿔요."""
    return math.degrees(math.atan2(v.y, v.x))


def angle_diff(a, b):
    """두 각도의 차이를 -180 ~ 180 범위로 돌려줘요."""
    return (a - b + 180) % 360 - 180


def add_shake(n):
    global shake
    shake = max(shake, n)


def hurt_player(damage=1):
    """플레이어가 피해를 입어요. 무적 중이면 아무 일도 일어나지 않아요.
    일반 적, 오크 몽둥이, 드래곤 꼬리, 불, 골렘, 낙하물 모두 이 함수 하나로 피해를 줘요."""
    global player_hp, invuln_timer, shake, hurt_flash, revive_left
    global banner_text, banner_timer, banner_color, banner_blink
    global shield_hp, shield_timer
    if invuln_timer > 0 or game_over:
        return
    dg = skill_levels.get("회피", 0)
    if dg and random.random() < 0.08 * dg:
        invuln_timer = 30
        floaters.append({"pos": player_pos + pygame.Vector2(0, -26), "text": "MISS",
                         "color": (190, 230, 255), "life": 40})
        return
    if skill_levels.get("광폭화") and player_hp * 2 <= player_max_hp:
        add_glow(world, glow_rage, player_pos, 1.0 + 0.1 * math.sin(frame_tick * 0.3))
    damage_left = max(1, int(damage))
    if shield_hp > 0:
        absorbed = min(shield_hp, damage_left)
        shield_hp -= absorbed
        damage_left -= absorbed
        shield_timer = 0
        rings.append({"pos": player_pos.copy(), "r": 90, "life": 14, "max": 14, "color": (120, 230, 240)})
        spawn_burst(player_pos, (150, 245, 255), 8)
        add_shake(4)
        if damage_left == 0:
            invuln_timer = 45
            snd_hit.play()
            return
    player_hp -= damage_left
    invuln_timer = 60 + 15 * invuln_level + inv_bonus  # 기본 1초 무적 (+ 무적 연장 한 단계마다 0.25초)
    shake = 12
    hurt_flash = 10
    snd_hurt.play()

    tl = skill_levels.get("가시 갑옷", 0)
    if tl:  # 가시 갑옷: 맞으면 주변 적에게 반격
        for o in enemies:
            if o["pos"].distance_to(player_pos) < 130:
                damage_enemy(o, 3 * tl, quiet=True)

    # 충격파: 가까이 있던 일반 적들을 밀어내서 숨 돌릴 틈을 줘요 (보스는 안 밀려요)
    rings.append({"pos": player_pos.copy(), "r": 110, "life": 14, "max": 14, "color": (255, 90, 90)})
    for e in enemies:
        if e.get("boss"):
            continue
        away = e["pos"] - player_pos
        if 0 < away.length() < 110:
            e["pos"] += away.normalize() * 70
    if player_hp <= 0:
        if revive_left > 0:  # 불사의 부적: 체력 절반으로 되살아나요
            revive_left -= 1
            player_hp = max(1, (player_max_hp + 1) // 2)
            invuln_timer = 180
            rings.append({"pos": player_pos.copy(), "r": 260, "life": 20, "max": 20, "color": (150, 255, 180)})
            for e in enemies:
                away = e["pos"] - player_pos
                if not e.get("boss") and 0 < away.length() < 260:
                    e["pos"] += away.normalize() * 140
            banner_text, banner_timer, banner_color, banner_blink = "부활!", 90, (150, 255, 180), False
            snd_level.play()
        else:
            end_game()


def spawn_boss(kind, hp_scale=None, final=False):
    """보스를 등장시키고 경고 문구를 띄워요. hp_scale은 스테이지가 정해 주는 체력 배율이에요."""
    global boss_count, next_boss_frame, banner_text, banner_timer, banner_color, banner_blink
    if hp_scale is None:  # 무한 모드: 보스를 다시 만날 때마다 더 단단해져요
        scale = 1 + (boss_count // len(ENDLESS_BOSSES)) * 0.6
    else:
        scale = hp_scale
    name = BOSS_NAMES[kind]
    if kind == "orc":
        hp = int((50 + 10 * level) * scale)
        pos = pygame.Vector2(random.choice([-50, WIDTH + 50]), random.randint(100, HEIGHT - 100))
    elif kind == "golem":
        hp = int((110 + 12 * level) * scale)
        pos = pygame.Vector2(random.choice([-50, WIDTH + 50]), random.randint(100, HEIGHT - 100))
    else:
        hp = int((140 + 15 * level) * scale)
        pos = pygame.Vector2(WIDTH / 2, -90)  # 화면 위에서 내려와요
    enemies.append({
        "pos": pos, "hp": hp, "max_hp": hp, "kind": kind, "flash": 0, "blade_cd": 0,
        "boss": True,
        "final": final,  # 스테이지의 마지막 보스인지 (쓰러뜨리면 클리어)
        "state": "enter" if kind == "dragon" else "chase",
        "st_timer": 0,   # 지금 상태가 된 뒤 지난 프레임 수
        "cooldown": 60,  # 다음 공격까지 남은 프레임 수
        "angle": 0.0,    # 공격을 시작할 때 고정해 둔 방향 (플레이어가 피할 수 있게)
        "sweep": 1,      # 휘두르는 방향 (1 또는 -1)
        "dur": 40,       # 예고 시간
    })
    boss_count += 1
    next_boss_frame = survive_frames + 5400  # (무한 모드) 다음 보스는 이때부터 1분 30초 뒤
    banner_text = f"WARNING!  {name} 등장"
    banner_timer = 150
    banner_color = (255, 90, 90)
    banner_blink = True
    snd_boss.play()


def update_orc(e, to_player, dist, enraged):
    """오크: 쫓아옴 -> (붉은 부채꼴 예고) -> 몽둥이 휘두르기 -> 잠깐 쉼"""
    st = e["state"]
    if st == "chase":
        if dist > 45:
            e["pos"] += to_player.normalize() * (1.9 if enraged else 1.3)
        e["cooldown"] -= 1
        if dist < 140 and e["cooldown"] <= 0:
            e["angle"] = angle_of(to_player)  # 이 순간의 방향으로 고정 -> 피할 수 있어요
            e["dur"] = 26 if enraged else 40
            e["state"] = "windup"
            e["st_timer"] = 0
    elif st == "windup":
        if e["st_timer"] >= e["dur"]:
            e["state"] = "swing"
            e["st_timer"] = 0
    elif st == "swing":
        t = e["st_timer"]
        # 몽둥이 끝이 지금 가리키는 각도 (왼쪽 끝에서 오른쪽 끝까지 12프레임 동안 훑음)
        tip = e["angle"] - ORC_ARC - 25 + (2 * ORC_ARC + 25) * t / 12
        off = player_pos - e["pos"]
        if 0 < off.length() <= ORC_REACH + player_radius:
            pa = angle_of(off)
            if abs(angle_diff(pa, e["angle"])) <= ORC_ARC + 6 and abs(angle_diff(pa, tip)) <= 30:
                hurt_player(4)
        if t == 8:
            add_shake(6)
            spawn_burst(e["pos"] + pygame.Vector2(ORC_REACH - 15, 0).rotate(tip), (200, 180, 140), 6)
        if t >= 12:
            e["state"] = "recover"
            e["st_timer"] = 0
    elif st == "recover":  # 휘두른 뒤 숨 고르는 시간 = 플레이어가 공격할 기회
        if e["st_timer"] >= (30 if enraged else 50):
            e["state"] = "chase"
            e["st_timer"] = 0
            e["cooldown"] = 30 if enraged else 60


def update_golem(e, to_player, dist, enraged):
    """골렘: 느리게 쫓아옴 -> (붉은 원 예고) 내려찍기 / (잠깐 멈춤) 사방으로 파편 발사 -> 쉼"""
    st = e["state"]
    if st == "chase":
        e["pos"] += to_player.normalize() * (1.3 if enraged else 0.9)
        e["cooldown"] -= 1
        if e["cooldown"] <= 0:
            e["atk"] = e.get("atk", 0) + 1
            e["st_timer"] = 0
            if e["atk"] % 2 == 1:  # 홀수 번째는 내려찍기, 짝수 번째는 파편 발사
                e["target"] = player_pos.copy()  # 지금 서 있는 자리에 떨어져요 -> 피할 수 있어요
                e["dur"] = 36 if enraged else 52
                e["state"] = "slam_windup"
            else:
                e["dur"] = 30
                e["state"] = "shard_windup"
    elif st == "slam_windup":
        if e["st_timer"] >= e["dur"]:
            tgt = e["target"]
            rings.append({"pos": tgt.copy(), "r": GOLEM_SLAM_R + 25, "life": 16, "max": 16, "color": (200, 200, 220)})
            spawn_burst(tgt, (180, 180, 200), 14)
            add_shake(9)
            snd_boss.play()
            if player_pos.distance_to(tgt) < GOLEM_SLAM_R + player_radius:
                hurt_player(4)
            e["state"] = "recover"
            e["st_timer"] = 0
    elif st == "shard_windup":
        if e["st_timer"] >= e["dur"]:
            n = 12 if enraged else 8
            base = random.uniform(0, 360)
            for i in range(n):
                enemy_shots.append({"pos": e["pos"].copy(),
                                    "vel": pygame.Vector2(4.0, 0).rotate(base + 360 * i / n),
                                    "life": 240, "color": (190, 200, 220), "boss": True})
            add_shake(4)
            snd_zap.play()
            e["state"] = "recover"
            e["st_timer"] = 0
    elif st == "recover":
        if e["st_timer"] >= (35 if enraged else 55):
            e["state"] = "chase"
            e["st_timer"] = 0
            e["cooldown"] = 40 if enraged else 70


def breath_angle(e):
    """브레스가 지금 향하는 각도. 처음 방향에서 좌우로 천천히 훑어요."""
    progress = min(1.0, e["st_timer"] / 40)
    return e["angle"] + e["sweep"] * (-22 + 44 * progress)


def update_dragon(e, to_player, dist, enraged):
    """드래곤: 거리를 유지하며 떠다님 -> 가까우면 꼬리 후려치기, 멀면 브레스"""
    st = e["state"]
    if st == "enter":  # 화면 위에서 내려오는 중
        e["pos"].y += 2.2
        if e["pos"].y >= 110:
            e["state"] = "chase"
            e["st_timer"] = 0
            e["cooldown"] = 80
    elif st == "chase":
        speed = 1.6 if enraged else 1.1
        if dist > 260:
            e["pos"] += to_player.normalize() * speed
        elif dist < 170:
            e["pos"] -= to_player.normalize() * speed * 0.8
        e["pos"].x = max(70, min(WIDTH - 70, e["pos"].x))
        e["pos"].y = max(60, min(HEIGHT - 60, e["pos"].y))
        e["cooldown"] -= 1
        if e["cooldown"] <= 0:
            e["angle"] = angle_of(to_player)
            e["sweep"] = random.choice([-1, 1])
            e["st_timer"] = 0
            if dist < 210:
                e["state"] = "tail_windup"
                e["dur"] = 28 if enraged else 44
            else:
                e["state"] = "breath_windup"
                e["dur"] = 40 if enraged else 55
    elif st == "tail_windup":
        if e["st_timer"] >= e["dur"]:
            e["state"] = "tail_swing"
            e["st_timer"] = 0
            add_shake(5)
    elif st == "tail_swing":
        t = e["st_timer"]
        tip = e["angle"] + e["sweep"] * (-DRAGON_TAIL_ARC + 2 * DRAGON_TAIL_ARC * t / 14)
        off = player_pos - e["pos"]
        if 0 < off.length() <= DRAGON_TAIL_LEN + player_radius:
            pa = angle_of(off)
            if abs(angle_diff(pa, e["angle"])) <= DRAGON_TAIL_ARC + 16 and abs(angle_diff(pa, tip)) <= 16:
                hurt_player(4)
        if t >= 14:
            e["state"] = "recover"
            e["st_timer"] = 0
    elif st == "breath_windup":
        if e["st_timer"] >= e["dur"]:
            e["state"] = "breath"
            e["st_timer"] = 0
            add_shake(4)
    elif st == "breath":
        a = breath_angle(e)
        progress = min(1.0, e["st_timer"] / 40)
        front = 80 + 330 * progress  # 불줄기 끝이 점점 멀리 뻗어요
        direction = pygame.Vector2(1, 0).rotate(a)
        side = pygame.Vector2(-direction.y, direction.x)
        # 매 프레임 불씨 2개를 지나간 자리에 남겨요. life 180프레임 = 3초
        for _ in range(2):
            d = front - random.uniform(0, 45)
            spread = 6 + d * 0.07  # 멀수록 불줄기가 넓어져요
            if len(fires) < 220:
                fires.append({
                    "pos": e["pos"] + direction * d + side * random.uniform(-spread, spread),
                    "life": 180, "boss": True,
                })
        if e["st_timer"] >= 40:
            e["state"] = "recover"
            e["st_timer"] = 0
    elif st == "recover":
        if e["st_timer"] >= (36 if enraged else 56):
            e["state"] = "chase"
            e["st_timer"] = 0
            e["cooldown"] = 50 if enraged else 80


def update_boss(e):
    """보스 행동을 한 프레임 진행하고 체력이 낮아지면 분노 패턴을 시작해요."""
    to_player = player_pos - e["pos"]
    dist = to_player.length()
    if dist == 0:
        to_player = pygame.Vector2(0, 1)
        dist = 1
    enrage_at = 0.80 if e.get("final") else 0.70
    enraged = e["hp"] <= e["max_hp"] * enrage_at
    e["st_timer"] += 1
    if e["kind"] == "orc":
        update_orc(e, to_player, dist, enraged)
    elif e["kind"] == "golem":
        update_golem(e, to_player, dist, enraged)
    else:
        update_dragon(e, to_player, dist, enraged)


def make_enemy(kind, pos):
    """적 한 마리를 만들어요 (체력은 시간에 따라 올라가는 enemy_hp를 따라가요)."""
    hp = max(1, enemy_hp + enemy_types[kind]["hp_bonus"])
    return {"pos": pos, "hp": hp, "kind": kind, "flash": 0, "blade_cd": 0}


def make_elite(kind, pos):
    """엘리트 적: 체력 3배, 금빛으로 빛나고, 잡으면 골드/구슬을 많이 줘요."""
    e = make_enemy(kind, pos)
    e["hp"] *= 3
    e["max_hp"] = e["hp"]
    e["elite"] = True
    return e


def update_mage(e, to_player, dist, speed):
    """마법사: 적당한 거리를 유지하며 구체를 쏴요. to_player는 길이 1로 만든 방향이에요."""
    if dist > 280:
        e["pos"] += to_player * speed
    elif dist < 200:
        e["pos"] -= to_player * speed * 0.8
        e["pos"].x = max(20, min(WIDTH - 20, e["pos"].x))
        e["pos"].y = max(20, min(HEIGHT - 20, e["pos"].y))
    e["cd"] = e.get("cd", random.randint(50, 130)) - 1
    if e["cd"] <= 0:
        enemy_shots.append({"pos": e["pos"].copy(), "vel": to_player * 4.2, "life": 300,
                            "color": enemy_types[e["kind"]].get("shot_color", (200, 130, 255))})
        e["cd"] = 150


def update_bat(e, to_player, dist, speed):
    """박쥐: 플레이어 쪽으로 날아오면서 좌우로 지그재그로 흔들려요."""
    e["t"] = e.get("t", 0) + 1
    side = pygame.Vector2(-to_player.y, to_player.x)
    wobble = math.sin(e["t"] * 0.15 + (id(e) % 7))
    e["pos"] += to_player * speed * 0.9 + side * wobble * speed * 1.1


def update_boar(e, to_player, dist, speed):
    """멧돼지: 쫓아옴 -> 멈춰서 예고(붉은 길) -> 직선 돌진 -> 숨 고르기"""
    st = e.get("st", "chase")
    e["t"] = e.get("t", 0) + 1
    if st == "chase":
        e["pos"] += to_player * speed
        e["cd"] = e.get("cd", 90) - 1
        if e["cd"] <= 0 and 120 < dist < 380:
            e["st"], e["t"] = "windup", 0
            e["dir"] = to_player.copy()
    elif st == "windup":
        if e["t"] < 25:
            e["dir"] = to_player.copy()  # 처음엔 따라가다가, 마지막 15프레임은 방향 고정 -> 피할 수 있어요
        if e["t"] >= 40:
            e["st"], e["t"] = "dash", 0
    elif st == "dash":
        e["pos"] += e["dir"] * 9
        if e["t"] >= 28:
            e["st"], e["t"] = "recover", 0
    elif st == "recover":
        if e["t"] >= 45:
            e["st"], e["t"], e["cd"] = "chase", 0, 120


def draw_charge_lane(layer, e):
    """돌진형 적의 종류에 맞는 색으로 공격 경로를 예고해요."""
    d = e["dir"]
    n = pygame.Vector2(-d.y, d.x)
    prog = min(1.0, e["t"] / 40)
    a, b = e["pos"], e["pos"] + d * 260
    pts = [a + n * 18, b + n * 18, b - n * 18, a - n * 18]
    base = enemy_types[e["kind"]]["color"]
    fill = tuple(min(255, int(c * 0.72 + 70)) for c in base)
    edge = tuple(min(255, int(c * 0.65 + 110)) for c in base)
    pygame.draw.polygon(layer, (*fill, int(35 + 85 * prog)), pts)
    pygame.draw.polygon(layer, (*edge, 220), pts, 2)


# ------------------------------------------------------------
# 8) 그리기 도우미 함수
# ------------------------------------------------------------
def get_card_rects():
    """선택 카드 3장의 위치(사각형)를 돌려줘요."""
    card_w, card_h, gap = 240, 320, 20
    start_x = (WIDTH - (card_w * 3 + gap * 2)) // 2
    return [
        pygame.Rect(start_x + i * (card_w + gap), 150, card_w, card_h)
        for i in range(3)
    ]


# 스테이지별 바닥 분위기: off는 타일 색 보정, moss는 이끼/눈/용암 얼룩 색, crack은 균열 색
BG_STYLES = {
    "dungeon": {"off": (0, 0, 0), "moss": (34, 62, 48), "crack": (22, 20, 32)},
    "ice": {"off": (-4, 12, 34), "moss": (120, 150, 190), "crack": (24, 40, 74)},
    "lava": {"off": (32, -10, -12), "moss": (170, 60, 20), "crack": (225, 90, 25)},
}


REROLL_RECT = pygame.Rect(WIDTH // 2 - 92, 496, 184, 38)


def make_background(style="dungeon"):
    """어두운 던전 바닥(타일 + 균열 + 이끼 + 돌부스러기 + 횃불 받침)을 한 번만 그려서 이미지로 만들어 둬요."""
    st = BG_STYLES[style]
    off = st["off"]

    def cl(v):
        return max(0, min(255, v))

    bg = pygame.Surface((WIDTH, HEIGHT))
    rng = random.Random(7)
    tile = 40
    for ty in range(0, HEIGHT, tile):
        for tx in range(0, WIDTH, tile):
            base = 40 if ((tx // tile + ty // tile) % 2 == 0) else 44
            shade = rng.randint(-3, 3)
            color = (cl(base + shade + off[0]), cl(base - 2 + shade + off[1]), cl(base + 14 + shade + off[2]))
            pygame.draw.rect(bg, color, (tx, ty, tile, tile))
            # 타일 테두리: 위/왼쪽은 밝게, 아래/오른쪽은 어둡게 -> 살짝 입체감
            light = (cl(color[0] + 9), cl(color[1] + 9), cl(color[2] + 10))
            dark = (cl(color[0] - 12), cl(color[1] - 12), cl(color[2] - 14))
            pygame.draw.line(bg, light, (tx + 1, ty + 1), (tx + tile - 2, ty + 1))
            pygame.draw.line(bg, light, (tx + 1, ty + 1), (tx + 1, ty + tile - 2))
            pygame.draw.rect(bg, dark, (tx, ty, tile, tile), 1)
            for _ in range(rng.randint(0, 3)):
                x = tx + rng.randint(4, tile - 6)
                y = ty + rng.randint(4, tile - 6)
                pygame.draw.rect(bg, (cl(color[0] - 8), cl(color[1] - 8), cl(color[2] - 8)),
                                 (x, y, rng.choice([2, 3]), 2))

    # 바닥 균열
    for _ in range(26):
        x, y = rng.randint(10, WIDTH - 10), rng.randint(10, HEIGHT - 10)
        pts = [(x, y)]
        for _ in range(3):
            x += rng.randint(-14, 14)
            y += rng.randint(4, 14)
            pts.append((x, y))
        pygame.draw.lines(bg, st["crack"], False, pts, 2)

    # 이끼 (얼음 동굴은 눈, 용암 지옥은 용암 얼룩)
    for _ in range(22):
        mx, my = rng.randint(10, WIDTH - 20), rng.randint(10, HEIGHT - 20)
        for _ in range(rng.randint(4, 9)):
            pygame.draw.rect(bg, st["moss"], (mx + rng.randint(-8, 8), my + rng.randint(-5, 5),
                                              rng.choice([3, 4, 5]), rng.choice([2, 3])))

    # 지역마다 바닥 위에 남는 큰 형태를 넣어 전투 중에도 장소가 구분돼요.
    if style == "ice":
        for _ in range(10):
            x = rng.randint(18, WIDTH - 18)
            length = rng.randint(16, 42)
            width = rng.randint(7, 15)
            for y, direction in ((0, 1), (HEIGHT, -1)):
                points = [(x - width, y), (x + width, y), (x, y + direction * length)]
                pygame.draw.polygon(bg, (65, 105, 145), points)
                pygame.draw.line(bg, (130, 180, 215), (x, y + direction * 3),
                                 (x, y + direction * (length - 5)), 2)
        for _ in range(22):
            x, y = rng.randint(10, WIDTH - 10), rng.randint(10, HEIGHT - 10)
            pygame.draw.lines(bg, (75, 120, 160), False,
                              [(x, y), (x + 5, y + 4), (x + 2, y + 10), (x + 8, y + 15)], 1)
    elif style == "lava":
        for _ in range(18):
            x, y = rng.randint(8, WIDTH - 8), rng.randint(8, HEIGHT - 8)
            pts = [(x, y)]
            for _ in range(4):
                x += rng.randint(-17, 17)
                y += rng.randint(-13, 13)
                pts.append((max(4, min(WIDTH - 4, x)), max(4, min(HEIGHT - 4, y))))
            pygame.draw.lines(bg, (75, 35, 30), False, pts, 6)
            pygame.draw.lines(bg, (190, 75, 28), False, pts, 2)
            pygame.draw.lines(bg, (245, 145, 48), False, pts, 1)
    elif style == "grave":
        for _ in range(9):
            x, y = rng.randint(24, WIDTH - 24), rng.randint(35, HEIGHT - 30)
            w, h = rng.randint(10, 17), rng.randint(16, 25)
            stone = (57, 76, 66)
            pygame.draw.rect(bg, stone, (x - w // 2, y - h // 2, w, h))
            pygame.draw.rect(bg, (76, 95, 80), (x - w // 2, y - h // 2, w, 3))
            pygame.draw.rect(bg, (41, 56, 50), (x - w // 2 + 2, y + h // 2 - 3, w - 4, 2))
            pygame.draw.line(bg, (105, 125, 102), (x, y - 4), (x, y + 5), 1)
            pygame.draw.line(bg, (105, 125, 102), (x - 3, y), (x + 3, y), 1)
    elif style == "desert":
        for _ in range(34):
            x, y = rng.randint(0, WIDTH - 50), rng.randint(12, HEIGHT - 12)
            length = rng.randint(14, 45)
            pygame.draw.line(bg, (154, 124, 70), (x, y), (x + length, y - 2), 1)
            pygame.draw.line(bg, (207, 174, 105), (x + 2, y + 2), (x + length - 4, y + 1), 1)
        for x, y in ((70, 130), (WIDTH - 80, HEIGHT - 125), (WIDTH // 2 + 115, 75)):
            pygame.draw.rect(bg, (103, 112, 59), (x - 3, y - 16, 6, 30))
            pygame.draw.rect(bg, (103, 112, 59), (x - 12, y - 8, 6, 14))
            pygame.draw.rect(bg, (103, 112, 59), (x - 10, y - 10, 5, 5))
            pygame.draw.rect(bg, (103, 112, 59), (x + 7, y - 3, 6, 12))
            pygame.draw.rect(bg, (103, 112, 59), (x + 5, y - 5, 5, 5))
    elif style == "swamp":
        for _ in range(12):
            x, y = rng.randint(20, WIDTH - 20), rng.randint(20, HEIGHT - 20)
            w, h = rng.randint(18, 38), rng.randint(7, 16)
            pygame.draw.ellipse(bg, (35, 68, 32), (x - w, y - h, w * 2, h * 2))
            pygame.draw.arc(bg, (100, 145, 55), (x - w + 3, y - h + 2, w * 2 - 6, h * 2 - 4), 0, math.pi, 1)
            for _ in range(3):
                rx = x + rng.randint(-w, w)
                pygame.draw.line(bg, (83, 120, 48), (rx, y), (rx + rng.randint(-4, 4), y - rng.randint(6, 13)), 1)
    elif style == "abyss":
        for _ in range(8):
            x, y = rng.randint(35, WIDTH - 35), rng.randint(35, HEIGHT - 35)
            r = rng.randint(10, 22)
            col = (78, 50, 106)
            pygame.draw.circle(bg, col, (x, y), r, 1)
            pygame.draw.polygon(bg, col, [(x, y - r - 4), (x + r + 4, y), (x, y + r + 4), (x - r - 4, y)], 1)
            pygame.draw.circle(bg, (108, 68, 135), (x, y), 2)

    # 돌부스러기
    for _ in range(40):
        rx, ry = rng.randint(6, WIDTH - 10), rng.randint(6, HEIGHT - 10)
        s = rng.choice([3, 4, 5])
        pygame.draw.rect(bg, (24, 22, 34), (rx + 1, ry + 2, s, s - 1))
        pygame.draw.rect(bg, (68, 66, 84), (rx, ry, s, s - 1))
        pygame.draw.rect(bg, (92, 90, 110), (rx, ry, s, 1))

    vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(80):
        alpha = int(110 * (1 - i / 80) ** 2)
        pygame.draw.rect(vignette, (0, 0, 0, alpha),
                         (i, i, WIDTH - 2 * i, HEIGHT - 2 * i), 1)
    bg.blit(vignette, (0, 0))

    # 횃불 받침 (불꽃은 draw_torches가 매 프레임 그려요)
    for tx, ty in TORCH_POS:
        pygame.draw.rect(bg, (30, 24, 24), (tx - 3, ty + 2, 8, 20))
        pygame.draw.rect(bg, (92, 70, 50), (tx - 4, ty, 8, 20))
        pygame.draw.rect(bg, (120, 120, 135), (tx - 8, ty - 3, 16, 5))
        pygame.draw.rect(bg, (60, 60, 72), (tx - 8, ty + 1, 16, 2))
    return bg


def pixel_panel(surf, rect, border, fill, n=8, bw=4):
    """모서리가 계단처럼 깎인, 도트 게임 느낌의 상자를 그려요."""
    for r in (rect.inflate(-2 * n, 0), rect.inflate(0, -2 * n)):
        pygame.draw.rect(surf, border, r)
    inner = rect.inflate(-2 * bw, -2 * bw)
    m = max(0, n - bw)
    for r in (inner.inflate(-2 * m, 0), inner.inflate(0, -2 * m)):
        pygame.draw.rect(surf, fill, r)


def wrap_text_pixels(text, font, max_width):
    """픽셀 너비에 맞춰 문장을 줄바꿈해요."""
    lines = []
    for paragraph in str(text).split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = word if not line else f"{line} {word}"
            if font.size(candidate)[0] <= max_width:
                line = candidate
                continue
            if line:
                lines.append(line)
                line = ""
            # 공백이 없는 긴 단어도 카드 밖으로 나가지 않게 글자 단위로 나눠요.
            for char in word:
                if line and font.size(line + char)[0] > max_width:
                    lines.append(line)
                    line = char
                else:
                    line += char
        if line or not paragraph:
            lines.append(line)
    return lines


def draw_card(surf, card, name, index, hovered, slide=0):
    """스킬 카드의 제목·설명·조합·수치 영역을 분리해 글자가 겹치지 않게 그립니다."""
    style = upgrade_style.get(name, {"color": (145, 165, 210), "icon": None})
    accent = style.get("color", (145, 165, 210))
    dark_accent = tuple(c // 3 for c in accent)
    rect = card.move(0, slide - (10 if hovered else 0))

    if hovered:
        pixel_panel(surf, rect.inflate(12, 12), dark_accent, dark_accent)
    border = accent if hovered else (95, 105, 160)
    fill = (52, 58, 96) if hovered else (36, 40, 66)
    pixel_panel(surf, rect, border, fill)
    pygame.draw.rect(surf, accent, (rect.x + 12, rect.y + 8, rect.w - 24, 6))

    # 내부 글자가 카드 밖이나 이웃 카드 영역으로 넘치지 않게 클리핑합니다.
    old_clip = surf.get_clip()
    surf.set_clip(old_clip.clip(rect.inflate(-8, -8)))
    try:
        badge = pygame.Rect(rect.x + 14, rect.y + 22, 36, 36)
        pixel_panel(surf, badge, accent, (20, 22, 40), n=4, bw=3)
        num = small_font.render(str(index + 1), True, accent)
        surf.blit(num, num.get_rect(center=badge.center))

        if name in RUN_RELICS:
            kind, kind_color = "유물", RUN_RELICS[name]["color"]
        elif name in SKILL_EVOLUTIONS:
            kind, kind_color = "진화", SKILL_EVOLUTIONS[name]["color"]
        else:
            kind = "공격" if name in ATTACK_SKILLS else "보조"
            kind_color = (255, 150, 120) if name in ATTACK_SKILLS else (130, 220, 240)
        tag = tiny_font.render(kind, True, kind_color)
        surf.blit(tag, tag.get_rect(midright=(rect.right - 12, rect.y + 40)))

        icon = style.get("icon")
        icon_pos = (rect.centerx, rect.y + 96 + (int(3 * math.sin(frame_tick * 0.1)) if hovered else 0))
        if icon is not None:
            if hovered:
                add_glow(surf, glow_proj, icon_pos, 2.2)
            surf.blit(icon, icon.get_rect(center=icon_pos))

        # 제목은 카드 중앙 정렬, 긴 이름은 자동으로 줄바꿈합니다.
        title_lines = wrap_text_pixels(name, small_font, rect.w - 32)
        title_font = small_font
        if len(title_lines) > 1:
            title_font = tiny_font
            title_lines = wrap_text_pixels(name, title_font, rect.w - 32)
        title_lh = title_font.get_linesize()
        title_center_y = rect.y + (159 if len(title_lines) <= 1 else 155)
        title_start_y = title_center_y - (len(title_lines) - 1) * title_lh // 2
        for i, line in enumerate(title_lines):
            rendered = title_font.render(line, True, (255, 255, 255))
            surf.blit(rendered, rendered.get_rect(center=(rect.centerx, title_start_y + i * title_lh)))

        pygame.draw.rect(surf, accent, (rect.centerx - 24, rect.y + 184, 48, 4))

        # 설명은 별도 높이에 배치합니다. 예상보다 긴 문장은 작은 글꼴로 다시 나눕니다.
        desc_top = rect.y + 196
        desc_bottom = rect.y + 252
        desc_font = small_font
        desc_lines = wrap_text_pixels(upgrades.get(name, "스킬 효과"), desc_font, rect.w - 34)
        if len(desc_lines) > 3:
            desc_font = tiny_font
            desc_lines = wrap_text_pixels(upgrades.get(name, "스킬 효과"), desc_font, rect.w - 30)
        max_desc = max(1, (desc_bottom - desc_top) // max(1, desc_font.get_linesize()))
        if len(desc_lines) > max_desc:
            desc_lines = desc_lines[:max_desc]
            if desc_lines:
                desc_lines[-1] = (desc_lines[-1][:-1] + "…") if len(desc_lines[-1]) > 1 else "…"
        desc_lh = desc_font.get_linesize()
        desc_start_y = desc_top + max(0, (desc_bottom - desc_top - len(desc_lines) * desc_lh) // 2)
        for i, line in enumerate(desc_lines):
            rendered = desc_font.render(line, True, (180, 190, 220))
            surf.blit(rendered, rendered.get_rect(center=(rect.centerx, desc_start_y + i * desc_lh + desc_lh // 2)))

        active_synergy = next((syn for syn, data in SKILL_SYNERGIES.items()
                               if name in data["skills"] and synergy_active(syn)), None)
        if active_synergy:
            synergy_text = tiny_font.render(f"조합 활성: {active_synergy}", True,
                                            SKILL_SYNERGIES[active_synergy]["color"])
            surf.blit(synergy_text, synergy_text.get_rect(center=(rect.centerx, rect.y + 260)))

        # 단계별 수치는 맨 아래 한 구역에 정렬해 설명 문장과 겹치지 않게 합니다.
        preview_font = tiny_font
        preview_lines = wrap_text_pixels(preview_text(name), preview_font, rect.w - 28)
        preview_top = rect.y + (274 if active_synergy else 266)
        preview_bottom = rect.bottom - 7
        max_preview = max(1, (preview_bottom - preview_top) // max(1, preview_font.get_linesize()))
        if len(preview_lines) > max_preview:
            preview_lines = preview_lines[:max_preview]
            if preview_lines:
                preview_lines[-1] = (preview_lines[-1][:-1] + "…") if len(preview_lines[-1]) > 1 else "…"
        preview_lh = preview_font.get_linesize()
        block_h = len(preview_lines) * preview_lh
        preview_start_y = preview_top + max(0, (preview_bottom - preview_top - block_h) // 2)
        for i, line in enumerate(preview_lines):
            rendered = preview_font.render(line, True, accent)
            surf.blit(rendered, rendered.get_rect(center=(rect.centerx, preview_start_y + i * preview_lh + preview_lh // 2)))
    finally:
        surf.set_clip(old_clip)

def draw_blade(surf, pos, ang):
    """회전 칼날: 도는 방향으로 길쭉한 마름모."""
    tangent = pygame.Vector2(1, 0).rotate(ang + 90)
    normal = pygame.Vector2(1, 0).rotate(ang)
    pts = [pos + tangent * 13, pos + normal * 5, pos - tangent * 13, pos - normal * 5]
    pygame.draw.polygon(surf, (230, 250, 255), pts)
    pygame.draw.polygon(surf, (80, 225, 205), pts, 2)


def draw_pixel_bar(surf, rect, ratio, fill, hi, lo, seg_w=10, gap=2):
    """도트 느낌의 막대: 계단 모서리 틀 + 칸으로 나뉜 게이지 + 위아래 명암 줄.
    경험치 바와 보스 체력 바가 같이 써요."""
    pixel_panel(surf, rect, (90, 100, 170), (20, 22, 40), n=3, bw=3)  # 바깥 틀
    inner = rect.inflate(-10, -10)  # 틀 안쪽 영역
    pygame.draw.rect(surf, (28, 30, 52), inner)
    count = max(1, inner.w // (seg_w + gap))  # 칸 수
    filled = max(0.0, min(1.0, ratio)) * count
    band = max(1, inner.h // 3)  # 밝은 줄/어두운 줄 두께
    for i in range(count):
        if i + 1 <= filled:
            w = seg_w
        elif i < filled:
            w = max(1, int(seg_w * (filled - i)))  # 마지막 칸은 일부만 채워요
        else:
            break
        x = inner.x + i * (seg_w + gap)
        pygame.draw.rect(surf, fill, (x, inner.y, w, inner.h))
        pygame.draw.rect(surf, hi, (x, inner.y, w, band))
        pygame.draw.rect(surf, lo, (x, inner.bottom - band, w, band))


def wedge_points(center, angle, half, radius):
    """부채꼴(예고 구역)의 꼭짓점들."""
    steps = max(6, int(half * 2 / 8))
    pts = [center]
    for i in range(steps + 1):
        a = angle - half + 2 * half * i / steps
        pts.append(center + pygame.Vector2(radius, 0).rotate(a))
    return pts


def club_angle(e):
    """오크 몽둥이가 지금 향하는 각도."""
    st = e["state"]
    if st == "windup":
        return e["angle"] - ORC_ARC - 25 * min(1.0, e["st_timer"] / e["dur"])  # 뒤로 젖힘
    if st == "swing":
        return e["angle"] - ORC_ARC - 25 + (2 * ORC_ARC + 25) * e["st_timer"] / 12
    if st == "recover":
        return e["angle"] + ORC_ARC  # 휘두른 자세 그대로 쉼
    face = angle_of(player_pos - e["pos"])
    return face - 100 + 6 * math.sin(frame_tick * 0.12)  # 평소엔 어깨에 걸치고 걸어요


def draw_orc_club(surf, e):
    """오크가 한 손에 든 큰 나무 몽둥이."""
    a = club_angle(e)
    u = pygame.Vector2(1, 0).rotate(a)  # 몽둥이가 뻗는 방향
    n = pygame.Vector2(-u.y, u.x)       # 그에 수직인 방향 (굵기용)
    base = e["pos"] + u * 14
    mid = e["pos"] + u * 66
    tip = e["pos"] + u * 106
    pts = [base + n * 4, mid + n * 8, tip + n * 15, tip - n * 15, mid - n * 8, base - n * 4]
    pygame.draw.polygon(surf, (150, 100, 55), pts)
    pygame.draw.polygon(surf, (75, 48, 28), pts, 3)
    # 나뭇결 하이라이트
    pygame.draw.line(surf, (190, 135, 80), base + n * 1, tip + n * 6, 2)
    for k in (-8, 0, 8):  # 몽둥이 머리의 쇠 박힌 장식
        pygame.draw.circle(surf, (190, 190, 200), tip - u * 12 + n * k, 3)


def draw_tail(surf, pos, a, length, lag):
    """드래곤 꼬리: 마디마디 이어진 선. lag는 끝부분이 뒤처지는 각도라서 채찍처럼 휘어 보여요."""
    n = 10
    pts = []
    for i in range(n + 1):
        r = 20 + (length - 20) * i / n
        pts.append(pos + pygame.Vector2(r, 0).rotate(a - lag * i / n))
    for i in range(n):  # 먼저 어두운 윤곽, 그 위에 비늘 색
        w = max(3, 14 - i)
        pygame.draw.line(surf, (60, 20, 30), pts[i], pts[i + 1], w + 4)
        pygame.draw.circle(surf, (60, 20, 30), pts[i], (w + 4) // 2)
    for i in range(n):
        w = max(3, 14 - i)
        pygame.draw.line(surf, (190, 55, 50), pts[i], pts[i + 1], w)
        pygame.draw.circle(surf, (190, 55, 50), pts[i], w // 2)
        if i % 2 == 0:  # 등 쪽 밝은 비늘
            pygame.draw.circle(surf, (225, 95, 75), pts[i], max(1, w // 4))
    d = pygame.Vector2(1, 0).rotate(a - lag)
    nn = pygame.Vector2(-d.y, d.x)
    tip = pts[-1]
    pygame.draw.polygon(surf, (250, 200, 80), [tip + d * 14, tip + nn * 8, tip - d * 4, tip - nn * 8])


def draw_dragon_tail(surf, e):
    st = e["state"]
    s = e["sweep"]
    if st == "tail_windup":  # 꼬리를 뒤로 말아 젖힘
        prog = min(1.0, e["st_timer"] / e["dur"])
        draw_tail(surf, e["pos"], e["angle"] - s * DRAGON_TAIL_ARC,
                  110 + (DRAGON_TAIL_LEN - 110) * prog, -s * 30)
    elif st == "tail_swing":  # 채찍처럼 훑고 지나감
        tip = e["angle"] + s * (-DRAGON_TAIL_ARC + 2 * DRAGON_TAIL_ARC * e["st_timer"] / 14)
        draw_tail(surf, e["pos"], tip, DRAGON_TAIL_LEN, s * 28)
    else:  # 평소엔 아래쪽에서 살랑살랑
        sway = math.sin(frame_tick * 0.05)
        draw_tail(surf, e["pos"], 90 + 14 * sway, 120, 22 * sway)


def draw_fire(surf, f):
    """드래곤 브레스가 남긴 불. 꺼지기 직전(마지막 0.75초)에는 깜빡이며 작아져요."""
    x, y = int(f["pos"].x), int(f["pos"].y)
    life = f["life"]
    flick = (frame_tick // 5 + x // 10) % 3
    if life < 45 and (life // 4) % 2 == 0:
        h = 8
    else:
        h = 14 + flick * 4
    pygame.draw.rect(surf, (170, 40, 30), (x - 16, y - 2, 32, 12))
    pygame.draw.rect(surf, (255, 120, 30), (x - 12, y - h, 24, h + 6))
    pygame.draw.rect(surf, (255, 210, 80), (x - 6, y - h // 2 - 4, 12, h // 2 + 8))


def draw_boss_layer(layer, e):
    """보스 공격 예고(붉은 구역)와 불줄기를 반투명 층에 그려요."""
    st = e["state"]
    if e["kind"] == "orc":
        if st in ("windup", "swing"):
            prog = min(1.0, e["st_timer"] / e["dur"]) if st == "windup" else 1.0
            pts = wedge_points(e["pos"], e["angle"], ORC_ARC + 6, ORC_REACH)
            pygame.draw.polygon(layer, (255, 70, 60, int(45 + 85 * prog)), pts)
            pygame.draw.polygon(layer, (255, 150, 130, 230), pts, 2)
        return
    if e["kind"] == "golem":  # 골렘: 내려찍을 자리에 붉은 원이 점점 차올라요
        if st == "slam_windup":
            prog = min(1.0, e["st_timer"] / e["dur"])
            tgt = (int(e["target"].x), int(e["target"].y))
            pygame.draw.circle(layer, (255, 70, 60, int(35 + 55 * prog)), tgt, GOLEM_SLAM_R)
            pygame.draw.circle(layer, (255, 110, 90, int(70 + 110 * prog)), tgt, max(2, int(GOLEM_SLAM_R * prog)))
            pygame.draw.circle(layer, (255, 150, 130, 230), tgt, GOLEM_SLAM_R, 3)
        elif st == "shard_windup":
            prog = min(1.0, e["st_timer"] / e["dur"])
            pygame.draw.circle(layer, (200, 130, 255, int(40 + 90 * prog)),
                               (int(e["pos"].x), int(e["pos"].y)), int(30 + 30 * prog), 3)
        return
    if st in ("tail_windup", "tail_swing"):
        prog = min(1.0, e["st_timer"] / e["dur"]) if st == "tail_windup" else 1.0
        pts = wedge_points(e["pos"], e["angle"], DRAGON_TAIL_ARC + 16, DRAGON_TAIL_LEN)
        pygame.draw.polygon(layer, (255, 70, 60, int(45 + 85 * prog)), pts)
        pygame.draw.polygon(layer, (255, 150, 130, 230), pts, 2)
    elif st == "breath_windup":
        prog = min(1.0, e["st_timer"] / e["dur"])
        pts = wedge_points(e["pos"], e["angle"], 30, 410)
        pygame.draw.polygon(layer, (255, 140, 40, int(35 + 75 * prog)), pts)
        pygame.draw.polygon(layer, (255, 190, 90, 220), pts, 2)
    elif st == "breath":
        a = breath_angle(e)
        front = 80 + 330 * min(1.0, e["st_timer"] / 40)
        mouth = e["pos"] + pygame.Vector2(40, 0).rotate(a)
        outer = [mouth, mouth + pygame.Vector2(front, 0).rotate(a - 14), mouth + pygame.Vector2(front, 0).rotate(a + 14)]
        inner = [mouth, mouth + pygame.Vector2(front * 0.9, 0).rotate(a - 6), mouth + pygame.Vector2(front * 0.9, 0).rotate(a + 6)]
        pygame.draw.polygon(layer, (255, 130, 40, 170), outer)
        pygame.draw.polygon(layer, (255, 225, 110, 210), inner)


def time_string():
    seconds = survive_frames // 60
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def mmss(seconds):
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def draw_dim(alpha=170):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    screen.blit(overlay, (0, 0))


def draw_motes(surf, n, base_color, speed=1.0):
    """공중에 떠다니는 작은 먼지/불씨. 계산으로만 움직여서 따로 저장할 게 없어요."""
    for i in range(n):
        if (frame_tick // 7 + i) % 9 == 0:
            continue  # 가끔 깜빡
        x = (i * 97 + frame_tick * (0.25 + (i % 5) * 0.12) * speed + 40 * math.sin(frame_tick * 0.01 + i)) % WIDTH
        y = HEIGHT - (i * 53 + frame_tick * (0.35 + (i % 4) * 0.18) * speed) % HEIGHT
        s = 1 + i % 3
        pygame.draw.rect(surf, base_color, (x, y, s, s))


def draw_torches(surf, glow=None):
    """벽 횃불: 불꽃이 일렁이고 주변 바닥이 물들어요. (스테이지마다 빛 색이 달라요)"""
    g = glow if glow is not None else glow_torch
    if cur_def["style"] == "ice":
        flame, core, spark = (90, 175, 255), (155, 220, 255), (235, 250, 255)
    elif cur_def["style"] == "lava":
        flame, core, spark = (235, 70, 25), (255, 145, 40), (255, 230, 115)
    else:
        flame, core, spark = (200, 70, 25), (255, 150, 45), (255, 230, 135)
    for i, (tx, ty) in enumerate(TORCH_POS):
        flick = (frame_tick // 4 + i * 3) % 3
        add_glow(surf, g, (tx, ty - 10), 1.0 + 0.07 * flick)
        h = 10 + flick * 3
        pygame.draw.rect(surf, flame, (tx - 5, ty - h, 10, h))
        pygame.draw.rect(surf, core, (tx - 3, ty - h + 2, 6, h - 3))
        pygame.draw.rect(surf, spark, (tx - 1, ty - h // 2, 2, h // 2 - 1))


# ------------------------------------------------------------
# 8-2) 첫 화면 / 스테이지 선택 / 업적 / 영구 강화 / 무기 상점
# ------------------------------------------------------------
menu_index = 0       # 첫 화면에서 고른 버튼
stage_sel = 0        # 스테이지 선택에서 고른 칸
upg_sel = 0          # 영구 강화에서 고른 칸
shop_sel = 0         # 상점에서 고른 무기
shop_results = []    # 방금 뽑은 결과 (비어 있으면 결과창 없음)
shop_anim = 0
toast_text = ""
toast_timer = 0
toast_color = (255, 230, 120)

BACK_RECT = pygame.Rect(12, 12, 104, 36)
PULL1_RECT = pygame.Rect(356, 102, 196, 52)
PULL10_RECT = pygame.Rect(568, 102, 196, 52)
EQUIP_RECT = pygame.Rect(40, 466, 260, 46)
coin_big = pygame.transform.scale(make_coin(20), (40, 40))
rarity_glows = {k: make_glow(80, tuple(int(c * 0.55) for c in v["color"])) for k, v in RARITY.items()}
meta_icons = {}
for _d in META_DEFS:
    _img = upgrade_style[_d["icon"]]["icon"] if _d["icon"] else coin_big
    meta_icons[_d["key"]] = pygame.transform.scale(_img, (44, 44))

STAGE_ORDER = [1, 2, 3, 4, 5, 6, 0]  # 스테이지 선택 화면의 칸 순서 (마지막이 무한 모드)
STAGE_ACCENT = {0: (190, 140, 255), 1: (255, 170, 80), 2: (110, 200, 255), 3: (255, 100, 60)}

_wimg_cache = {}
_boss_glow_cache = {}


def weapon_img(wid, scale, dark=False):
    """무기 그림 (크기별로 한 번만 만들어 둬요). dark=True면 못 얻은 무기의 그림자."""
    key = (wid, scale, dark)
    img = _wimg_cache.get(key)
    if img is None:
        w = WEAPONS[wid]
        img = make_weapon_icon(w["shape"], w["c"], scale)
        if dark:
            img = img.copy()
            img.fill((12, 14, 26, 255), special_flags=pygame.BLEND_RGBA_MIN)
            img.fill((40, 46, 74, 0), special_flags=pygame.BLEND_RGB_ADD)
        _wimg_cache[key] = img
    return img


def draw_hero_weapon(surf, pos, left, bob):
    """주인공이 손에 든 무기. 공격할 때 휙 휘둘러요."""
    if not equipped_weapon:
        return
    weapon = WEAPONS[equipped_weapon]
    img = weapon_img(equipped_weapon, 2)
    if left:
        img = pygame.transform.flip(img, True, False)
    ang = (70 if left else -70) * (weapon_swing / 10)
    if ang:
        img = pygame.transform.rotate(img, ang)
    x = pos.x + (-15 if left else 15)
    center = pygame.Vector2(x, pos.y + 2 - bob)
    if weapon_swing > 0:
        rarity = weapon.get("rarity", "common")
        accent = RARITY.get(rarity, RARITY["common"])["color"]
        tip_offset = pygame.Vector2(-1 if left else 1, -0.55).normalize() * 22
        tip = center + tip_offset.rotate(-ang)
        add_glow(surf, rarity_glows.get(rarity, glow_proj), tip, 0.48 + 0.05 * weapon_swing)
        for i in range(3):
            phase = frame_tick * 0.23 + i * 2.1
            spark = tip + pygame.Vector2(math.cos(phase), math.sin(phase)) * (4 + i * 3)
            pygame.draw.rect(surf, accent, (int(spark.x), int(spark.y), 2, 2))
    surf.blit(img, img.get_rect(center=center))


def show_toast(msg, color=(255, 230, 120)):
    global toast_text, toast_timer, toast_color
    toast_text, toast_timer, toast_color = msg, 100, color


def draw_toast(surf, y=546):
    if toast_timer <= 0:
        return
    t = small_font.render(toast_text, True, toast_color)
    r = pygame.Rect(0, 0, t.get_width() + 40, 36)
    r.center = (WIDTH // 2, y)
    pixel_panel(surf, r, toast_color, (20, 22, 40), n=4, bw=2)
    surf.blit(t, t.get_rect(center=r.center))


def draw_menu_bg(dim=90):
    screen.blit(background, (0, 0))
    draw_torches(screen)
    draw_dim(dim)
    draw_motes(screen, 40, (255, 190, 90), 1.0)


def draw_button(surf, rect, text, hovered, enabled=True, accent=(255, 210, 90)):
    """도트 느낌의 버튼. 마우스를 올리면 밝아져요."""
    if not enabled:
        border, fill, tc = (70, 74, 100), (28, 30, 48), (125, 130, 155)
    elif hovered:
        border, fill, tc = accent, tuple(min(255, c // 3 + 30) for c in accent), (255, 255, 255)
    else:
        border, fill, tc = tuple(c * 2 // 3 for c in accent), (36, 40, 66), (232, 236, 250)
    if hovered and enabled:
        pixel_panel(surf, rect.inflate(8, 8), tuple(c // 3 for c in accent), tuple(c // 3 for c in accent), n=5, bw=3)
    pixel_panel(surf, rect, border, fill, n=5, bw=3)
    if text:
        blit_text(surf, small_font, text, tc, rect.center, True)


def draw_gold_panel(surf):
    rect = pygame.Rect(WIDTH - 190, 12, 178, 36)
    pixel_panel(surf, rect, (235, 190, 70), (40, 34, 20), n=4, bw=3)
    surf.blit(coin_img, coin_img.get_rect(center=(rect.x + 22, rect.centery)))
    t = small_font.render(f"{gold:,}", True, (255, 230, 120))
    surf.blit(t, t.get_rect(midright=(rect.right - 12, rect.centery)))


def weapon_stat_lines(wid, star):
    st = weapon_stats(wid, star)
    lines = []
    if st["atk"]:
        lines.append(f"공격력 +{round(st['atk'] * 100)}%")
    if st["spd"]:
        lines.append(f"공격 속도 +{round(st['spd'] * 100)}%")
    if st["crit"]:
        lines.append(f"치명타 +{round(st['crit'])}%")
    if st["pick"]:
        lines.append(f"줍기 범위 +{round(st['pick'])}")
    if st["xp"]:
        lines.append(f"경험치 +{round(st['xp'] * 100)}%")
    if st["gold"]:
        lines.append(f"골드 +{round(st['gold'] * 100)}%")
    if st["move"]:
        lines.append(f"이동 속도 +{st['move']:.2f}")
    if st["hp"]:
        lines.append(f"체력 +{st['hp']}")
    if st["inv"]:
        lines.append(f"무적 시간 +{st['inv'] / 60:.2f}초")
    if st["dash"]:
        lines.append(f"대시 쿨타임 -{st['dash'] / 60:.2f}초")
    pw = WEAPONS[wid]
    if pw.get("pet"):
        lines.append(f"{max(20, int(pw['pcd'] * (1 - 0.08 * (star - 1)))) / 60:.1f}초마다 {pw['pshots']}발")
        if pw.get("pheal"):
            lines.append(f"{pw['pheal'] // 60}초마다 체력 +1")
    for sk in sorted(set(st["start"])):
        n = st["start"].count(sk)
        lines.append(f"시작 스킬: {sk}" + (f" Lv.{n}" if n > 1 else ""))
    return lines


# --- 영구 강화 구매 ---
def buy_meta(i):
    global gold
    d = META_DEFS[i]
    lv = meta_levels[d["key"]]
    if lv >= d["max"]:
        show_toast("이미 최대 단계예요", (180, 190, 220))
        snd_fail.play()
        return
    cost = meta_cost(d, lv)
    if gold < cost:
        show_toast("골드가 부족해요", (255, 130, 130))
        snd_fail.play()
        return
    gold -= cost
    meta_levels[d["key"]] = lv + 1
    save_game()
    snd_buy.play()
    show_toast(f"{d['name']} 강화 완료!  Lv.{lv + 1}", (140, 255, 170))


# --- 무기 뽑기 ---
def roll_weapon(min_rarity=None, slot=None):
    """등급을 정하고 그 등급의 무기 하나를 뽑아요. 30번째까지 전설이 안 나오면 전설 확정."""
    global pity_by_slot
    slot = slot or SLOTS[shop_tab]
    slot_pity = pity_by_slot.get(slot, 0)
    if slot_pity >= PITY_LIMIT - 1:
        rar = "legend"
    else:
        rar = random.choices(RARITY_ORDER, [RARITY[r]["w"] for r in RARITY_ORDER])[0]
    if min_rarity and RARITY_ORDER.index(rar) < RARITY_ORDER.index(min_rarity):
        rar = min_rarity
    i = RARITY_ORDER.index(rar)
    while i > 0 and not _slot_pool(RARITY_ORDER[i], slot):
        i -= 1
    rar = RARITY_ORDER[i]
    pity_by_slot[slot] = 0 if rar in ("legend", "myth") else min(PITY_LIMIT - 1, slot_pity + 1)
    return random.choice(_slot_pool(rar, slot))


def do_pull(n):
    global gold, shop_results, shop_anim, shop_sel
    cost = PULL_COST if n == 1 else PULL10_COST
    if gold < cost:
        show_toast("골드가 부족해요", (255, 130, 130))
        snd_fail.play()
        return
    gold -= cost
    results = []
    got_rare = False
    for i in range(n):
        force = "rare" if (n == 10 and i == 9 and not got_rare) else None  # 10회는 희귀 이상 1개 보장
        wid = roll_weapon(force)
        if RARITY_ORDER.index(WEAPONS[wid]["rarity"]) >= 1:
            got_rare = True
        if wid in weapon_stars:
            if weapon_stars[wid] < MAX_STAR:
                weapon_stars[wid] += 1
                kind = "star"
            else:
                gold += DUP_REFUND
                kind = "refund"
        else:
            weapon_stars[wid] = 1
            kind = "new"
        results.append({"id": wid, "kind": kind})
    best = max(results, key=lambda r: RARITY_ORDER.index(WEAPONS[r["id"]]["rarity"]))
    set_tab(WEAPONS[best["id"]]["slot"], best["id"])
    shop_results = results
    shop_anim = 0
    check_achievements()  # 골드가 바뀌었으니 '부자' 업적 확인
    save_game()
    snd_level.play()


def equip_selected():
    global equipped_weapon
    wid = WEAPON_ORDER[shop_sel]
    if wid not in weapon_stars:
        show_toast("아직 얻지 못한 무기예요", (255, 130, 130))
        snd_fail.play()
        return
    if wid == equipped_weapon:
        return
    equipped_weapon = wid
    save_game()
    snd_buy.play()
    show_toast(f"{WEAPONS[wid]['name']} 장착!", (140, 255, 170))


# --- 스테이지 ---
def stage_unlocked(sid):
    """무한 모드와 1스테이지는 처음부터 열려 있고, 나머지는 앞 스테이지를 클리어해야 열려요."""
    return sid in (0, 1) or (sid - 1) in stages_cleared


def start_stage(sid):
    global cur_stage
    if not stage_unlocked(sid):
        show_toast("앞 스테이지를 먼저 클리어하세요", (255, 130, 130))
        snd_fail.play()
        return
    cur_stage = sid
    snd_click.play()
    reset_game()  # 게임 시작 (state가 playing으로 바뀌어요)


# --- 칸 위치 ---
def menu_rects():
    return [pygame.Rect(WIDTH // 2 - 130, 388 + i * 44, 260, 38) for i in range(4)]


def stage_card_rects():
    return [pygame.Rect(20 + (i % 2) * 390, 66 + (i // 2) * 196, 380, 186) for i in range(4)]


def achv_rects():
    return [pygame.Rect(20 + (i % 2) * 390, 66 + (i // 2) * 80, 380, 72) for i in range(len(ACHIEVEMENTS))]


def upgrade_rects():
    return [pygame.Rect(30 + (i % 2) * 380, 100 + (i // 2) * 104, 360, 94) for i in range(len(META_DEFS))]


def shop_cell_rects():
    return [pygame.Rect(340 + (i % 5) * 88, 238 + (i // 5) * 80, 84, 76) for i in range(len(WEAPON_ORDER))]

def menu_activate(i):
    global state, upg_sel, stage_sel
    snd_click.play()
    if i == 0:
        state = "stage_select"
        stage_sel = 0
    elif i == 1:
        state = "upgrade"
        upg_sel = 0
    elif i == 2:
        state = "shop"
    else:
        state = "achv"


def menu_event(event):
    """첫 화면 / 스테이지 선택 / 업적 / 영구 강화 / 상점의 키보드와 마우스 입력을 처리해요."""
    global state, menu_index, upg_sel, shop_sel, shop_results, stage_sel
    if state == "stage_select":
        stage_event(event)
        return
    is_click = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
    is_key = event.type == pygame.KEYDOWN
    k = event.key if is_key else None
    enter = k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)

    if state == "title":
        rects = menu_rects()
        if event.type == pygame.MOUSEMOTION:
            for i, r in enumerate(rects):
                if r.collidepoint(event.pos):
                    menu_index = i
        elif is_click:
            for i, r in enumerate(rects):
                if r.collidepoint(event.pos):
                    menu_index = i
                    menu_activate(i)
                    break
        elif is_key:
            if k in (pygame.K_UP, pygame.K_w):
                menu_index = (menu_index - 1) % 4
                snd_click.play()
            elif k in (pygame.K_DOWN, pygame.K_s):
                menu_index = (menu_index + 1) % 4
                snd_click.play()
            elif enter:
                menu_activate(menu_index)
            elif k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                menu_index = k - pygame.K_1
                menu_activate(menu_index)

    elif state == "stage_select":
        rects = stage_card_rects()
        if event.type == pygame.MOUSEMOTION:
            for i, r in enumerate(rects):
                if r.collidepoint(event.pos):
                    stage_sel = i
        elif is_click:
            if BACK_RECT.collidepoint(event.pos):
                state = "title"
                snd_click.play()
                return
            for i, r in enumerate(rects):
                if r.collidepoint(event.pos):
                    stage_sel = i
                    start_stage(STAGE_ORDER[i])
                    break
        elif is_key:
            if k in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                state = "title"
                snd_click.play()
            elif k in (pygame.K_UP, pygame.K_w):
                stage_sel = max(0, stage_sel - 2)
            elif k in (pygame.K_DOWN, pygame.K_s):
                stage_sel = min(3, stage_sel + 2)
            elif k in (pygame.K_LEFT, pygame.K_a):
                if stage_sel % 2 == 1:
                    stage_sel -= 1
            elif k in (pygame.K_RIGHT, pygame.K_d):
                if stage_sel % 2 == 0:
                    stage_sel += 1
            elif enter:
                start_stage(STAGE_ORDER[stage_sel])
            elif k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                stage_sel = k - pygame.K_1
                start_stage(STAGE_ORDER[stage_sel])

    elif state == "achv":
        if (is_click and BACK_RECT.collidepoint(event.pos)) or (is_key and k in (pygame.K_ESCAPE, pygame.K_BACKSPACE)):
            state = "title"
            snd_click.play()

    elif state == "upgrade":
        rects = upgrade_rects()
        n = len(META_DEFS)
        if event.type == pygame.MOUSEMOTION:
            for i, r in enumerate(rects):
                if r.collidepoint(event.pos):
                    upg_sel = i
        elif is_click:
            if BACK_RECT.collidepoint(event.pos):
                state = "title"
                snd_click.play()
                return
            for i, r in enumerate(rects):
                if r.collidepoint(event.pos):
                    upg_sel = i
                    buy_meta(i)
                    break
        elif is_key:
            if k in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                state = "title"
                snd_click.play()
            elif k in (pygame.K_UP, pygame.K_w):
                upg_sel = max(0, upg_sel - 2)
            elif k in (pygame.K_DOWN, pygame.K_s):
                upg_sel = min(n - 1, upg_sel + 2)
            elif k in (pygame.K_LEFT, pygame.K_a):
                if upg_sel % 2 == 1:
                    upg_sel -= 1
            elif k in (pygame.K_RIGHT, pygame.K_d):
                if upg_sel % 2 == 0 and upg_sel + 1 < n:
                    upg_sel += 1
            elif enter:
                buy_meta(upg_sel)

    elif state == "shop":
        if shop_results:  # 뽑기 결과창이 떠 있을 땐 닫기만 해요
            if shop_anim > 20 and (is_key or is_click):
                shop_results = []
            return
        cells = shop_cell_rects()
        n = len(WEAPON_ORDER)
        if event.type == pygame.MOUSEMOTION:
            for i, r in enumerate(cells):
                if r.collidepoint(event.pos):
                    shop_sel = i
        elif is_click:
            p = event.pos
            if BACK_RECT.collidepoint(p):
                state = "title"
                snd_click.play()
            elif PULL1_RECT.collidepoint(p):
                do_pull(1)
            elif PULL10_RECT.collidepoint(p):
                do_pull(10)
            elif any(r.collidepoint(p) for r in TAB_RECTS):
                set_tab(SLOTS[[r.collidepoint(p) for r in TAB_RECTS].index(True)])
                snd_click.play()
            elif EQUIP_RECT.collidepoint(p):
                equip_selected()
            else:
                for i, r in enumerate(cells):
                    if r.collidepoint(p):
                        shop_sel = i
                        snd_click.play()
        elif is_key:
            if k in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                state = "title"
                snd_click.play()
            elif k == pygame.K_1:
                do_pull(1)
            elif k == pygame.K_2:
                do_pull(10)
            elif k in (pygame.K_LEFT, pygame.K_a):
                shop_sel = max(0, shop_sel - 1)
            elif k in (pygame.K_RIGHT, pygame.K_d):
                shop_sel = min(n - 1, shop_sel + 1)
            elif k in (pygame.K_UP, pygame.K_w):
                if shop_sel >= 5:
                    shop_sel -= 5
            elif k in (pygame.K_DOWN, pygame.K_s):
                if shop_sel + 5 < n:
                    shop_sel += 5   
            elif k == pygame.K_TAB:
                set_tab(SLOTS[(shop_tab + 1) % len(SLOTS)])
                snd_click.play()
            elif k == pygame.K_e or enter:
                equip_selected()


# --- 그리기 ---
def draw_title():
    """첫 화면: 제목, 주인공(장착 무기 포함), 메뉴 버튼, 골드와 최고 기록."""
    draw_menu_bg(90)
    bob = int(6 * math.sin(frame_tick * 0.08))
    add_glow(screen, glow_torch, (WIDTH // 2, 125 + bob), 3.2)  # 횃불빛이 뒤에서 번져요
    screen.blit(title_img, title_img.get_rect(center=(WIDTH // 2, 95 + bob)))
    screen.blit(subtitle_img, subtitle_img.get_rect(center=(WIDTH // 2, 158 + bob)))
    sub = small_font.render("몰려오는 적을 버텨라", True, (180, 190, 220))
    screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 200)))

    # 가운데 주인공, 양옆에 슬라임과 고블린 (살짝 위아래로 움직임)
    hy = 285 + int(5 * math.sin(frame_tick * 0.1))
    sy = 305 + int(4 * math.sin(frame_tick * 0.1 + 1.5))
    gy = 305 + int(4 * math.sin(frame_tick * 0.1 + 3.0))
    add_glow(screen, glow_hero, (WIDTH // 2, 285), 1.5)
    draw_shadow(screen, (WIDTH // 2, 285), 120, 78)
    draw_shadow(screen, (WIDTH // 2 - 190, 305), 80, 44)
    draw_shadow(screen, (WIDTH // 2 + 190, 305), 80, 44)
    screen.blit(hero_big, hero_big.get_rect(center=(WIDTH // 2, hy)))
    screen.blit(slime_big, slime_big.get_rect(center=(WIDTH // 2 - 190, sy)))
    screen.blit(goblin_big, goblin_big.get_rect(center=(WIDTH // 2 + 190, gy)))
    if equipped_weapon:  # 장착한 무기를 손에 들고 있어요
        rar = WEAPONS[equipped_weapon]["rarity"]
        wimg = pygame.transform.rotate(weapon_img(equipped_weapon, 5), 8 * math.sin(frame_tick * 0.08))
        wpos = (WIDTH // 2 + 84, hy + 22)
        add_glow(screen, rarity_glows[rar], wpos, 1.2)
        screen.blit(wimg, wimg.get_rect(center=wpos))

    if best_time > 0:
        bt = f"{best_time // 60:02d}:{best_time % 60:02d}"
        blit_text(screen, small_font, f"무한 모드 최고  {bt}  |  Kills {best_kills}", (255, 230, 120),
                  (WIDTH // 2, 370), True)

    labels = [("게임 시작", (255, 210, 90)), ("영구 강화", (110, 220, 255)),
              ("무기 상점", (200, 140, 255)), ("업적", (140, 255, 170))]
    for i, (r, (txt, acc)) in enumerate(zip(menu_rects(), labels)):
        draw_button(screen, r, txt, i == menu_index, True, acc)
    if gold >= PULL_COST and (frame_tick // 20) % 2 == 0:  # 뽑기 가능하면 상점 버튼에 표시
        blit_text(screen, tiny_font, "NEW", (255, 120, 140), (menu_rects()[2].right - 26, menu_rects()[2].y + 8), True)

    draw_gold_panel(screen)
    blit_text(screen, tiny_font, "이동: WASD / 방향키     대시: SPACE     일시정지: P     메뉴: 방향키 + Enter",
              (150, 160, 190), (WIDTH // 2, 582), True)
    draw_toast(screen, 350)


def draw_stage_select():
    draw_menu_bg(110)
    blit_text(screen, font, "스테이지 선택", (255, 230, 120), (WIDTH // 2, 30), True)
    draw_gold_panel(screen)
    mouse = pygame.mouse.get_pos()
    draw_button(screen, BACK_RECT, "< 뒤로", BACK_RECT.collidepoint(mouse), True, (150, 170, 255))
    page = stage_sel // 4
    blit_text(screen, tiny_font, f"{page + 1}/{(len(STAGE_ORDER) + 3) // 4}", (200, 210, 235),
              (150, 32), True)
    for i, (sid, rect) in enumerate(zip(STAGE_ORDER[page * 4:page * 4 + 4], stage_card_rects()), page * 4):
        sd = STAGES[sid]
        acc = STAGE_ACCENT[sid]
        unlocked = stage_unlocked(sid)
        cleared = sid in stages_cleared
        sel = i == stage_sel
        if sel:
            dark = tuple(c // 3 for c in acc)
            pixel_panel(screen, rect.inflate(10, 10), dark, dark, n=7, bw=3)
        pixel_panel(screen, rect, acc if sel else tuple(c * 2 // 3 for c in acc),
                    (50, 56, 94) if sel else (34, 38, 64), n=7, bw=3)
        label = "ENDLESS" if sid == 0 else f"STAGE {sid}"
        blit_text(screen, tiny_font, label, acc, (rect.x + 16, rect.y + 14))
        thumb = stage_thumbs[sid]
        tr = thumb.get_rect(topleft=(rect.x + 16, rect.y + 38))
        screen.blit(thumb, tr)
        pygame.draw.rect(screen, acc, tr, 2)
        blit_text(screen, small_font, sd["name"], (255, 255, 255), (rect.x + 150, rect.y + 40))
        if sid == 0:
            info = f"최고 기록 {mmss(best_time)}" if best_time > 0 else "기록 없음"
        elif cleared:
            info = f"클리어!  최단 {mmss(stage_best.get(str(sid), 0))}"
        else:
            info = f"클리어 보상 {sd['reward']} G"
        blit_text(screen, tiny_font, fit_text(tiny_font, info, rect.w - 170),
                  (255, 230, 120) if (sid == 0 or cleared) else (185, 195, 225),
                  (rect.x + 150, rect.y + 84))
        if sid != 0 and not cleared:
            blit_text(screen, tiny_font, "첫 클리어 보상 2배", (185, 195, 225),
                      (rect.x + 150, rect.y + 106))
        if cleared:
            draw_star(screen, (rect.right - 28, rect.y + 24), 12, (255, 215, 70))
        for ln, line in enumerate(sd["desc"].split("\n")):
            blit_text(screen, tiny_font, line, (185, 195, 225), (rect.x + 16, rect.y + 138 + ln * 22))
        if not unlocked:
            lock = pygame.Surface(rect.size, pygame.SRCALPHA)
            lock.fill((10, 10, 24, 255))
            screen.blit(lock, rect)
            dim_thumb = thumb.copy()
            dim_thumb.fill((100, 108, 145), special_flags=pygame.BLEND_RGB_MULT)
            screen.blit(dim_thumb, tr)
            pygame.draw.rect(screen, (74, 78, 108), tr, 2)
            blit_text(screen, tiny_font, label, tuple(c // 2 for c in acc), (rect.x + 16, rect.y + 14))
            blit_text(screen, small_font, sd["name"], (145, 150, 180), (rect.x + 150, rect.y + 40))
            blit_text(screen, small_font, "잠김", (200, 205, 230), (rect.centerx, rect.centery - 14), True)
            blit_text(screen, tiny_font, "앞 스테이지를 클리어하세요", (160, 170, 200),
                      (rect.centerx, rect.centery + 16), True)
    draw_toast(screen)
    blit_text(screen, tiny_font, "방향키 / 마우스: 선택     Enter / 클릭 / 1~4: 시작     ESC: 뒤로",
              (150, 160, 190), (WIDTH // 2, 580), True)


def draw_achv_screen():
    draw_menu_bg(110)
    blit_text(screen, font, "업적", (255, 230, 120), (WIDTH // 2, 30), True)
    draw_gold_panel(screen)
    mouse = pygame.mouse.get_pos()
    draw_button(screen, BACK_RECT, "< 뒤로", BACK_RECT.collidepoint(mouse), True, (150, 170, 255))
    done_n = sum(1 for a in ACHIEVEMENTS if achv_done.get(a["key"]))
    blit_text(screen, tiny_font, f"달성 {done_n} / {len(ACHIEVEMENTS)}", (255, 230, 120), (WIDTH // 2 + 90, 32), True)
    for a, rect in zip(ACHIEVEMENTS, achv_rects()):
        done = bool(achv_done.get(a["key"]))
        acc = (255, 215, 90) if done else (90, 96, 130)
        pixel_panel(screen, rect, acc, (46, 42, 28) if done else (28, 30, 50), n=6, bw=3)
        draw_star(screen, (rect.x + 32, rect.centery), 16, (255, 215, 70), empty=not done)
        blit_text(screen, small_font, a["name"], (255, 255, 255) if done else (150, 156, 185), (rect.x + 62, rect.y + 8))
        blit_text(screen, tiny_font, a["desc"], (200, 210, 235) if done else (120, 126, 156), (rect.x + 62, rect.y + 44))
        rt = tiny_font.render(f"+{a['reward']} G" if not done else "달성!", True,
                              (255, 230, 120) if not done else (140, 255, 170))
        screen.blit(rt, rt.get_rect(midright=(rect.right - 14, rect.y + 20)))
    draw_toast(screen)
    blit_text(screen, tiny_font, "업적을 달성하면 골드를 받아요     ESC: 뒤로", (150, 160, 190), (WIDTH // 2, 580), True)


def draw_upgrade_screen():
    draw_menu_bg(110)
    blit_text(screen, font, "영구 강화", (255, 230, 120), (WIDTH // 2, 30), True)
    draw_gold_panel(screen)
    mouse = pygame.mouse.get_pos()
    draw_button(screen, BACK_RECT, "< 뒤로", BACK_RECT.collidepoint(mouse), True, (150, 170, 255))
    for i, (d, rect) in enumerate(zip(META_DEFS, upgrade_rects())):
        lv = meta_levels[d["key"]]
        maxed = lv >= d["max"]
        cost = meta_cost(d, lv)
        can = (not maxed) and gold >= cost
        accent = d["color"]
        sel = i == upg_sel
        if sel:
            dark = tuple(c // 3 for c in accent)
            pixel_panel(screen, rect.inflate(10, 10), dark, dark, n=7, bw=3)
        pixel_panel(screen, rect, accent if sel else (95, 105, 160), (50, 56, 94) if sel else (34, 38, 64), n=7, bw=3)
        icon = meta_icons[d["key"]]
        screen.blit(icon, icon.get_rect(center=(rect.x + 40, rect.centery)))
        blit_text(screen, small_font, d["name"], (255, 255, 255), (rect.x + 76, rect.y + 10))
        lt = tiny_font.render(f"Lv {lv}/{d['max']}", True, accent)
        screen.blit(lt, lt.get_rect(midright=(rect.right - 14, rect.y + 24)))
        blit_text(screen, tiny_font, d["desc"], (185, 195, 225), (rect.x + 76, rect.y + 44))
        for p in range(d["max"]):  # 단계 칸
            pr = pygame.Rect(rect.x + 76 + p * 20, rect.y + 70, 16, 9)
            pygame.draw.rect(screen, accent if p < lv else (24, 26, 46), pr)
            pygame.draw.rect(screen, (14, 12, 30), pr, 1)
        if maxed:
            ct = small_font.render("MAX", True, accent)
        else:
            ct = small_font.render(f"{cost:,} G", True, (255, 230, 120) if can else (255, 120, 120))
        screen.blit(ct, ct.get_rect(midright=(rect.right - 14, rect.y + 74)))
    draw_toast(screen)
    blit_text(screen, tiny_font, "방향키 / 마우스: 선택     Enter / 클릭: 구매     ESC: 뒤로",
              (150, 160, 190), (WIDTH // 2, 580), True)


def draw_weapon_cell(rect, wid, selected):
    w = WEAPONS[wid]
    rc = RARITY[w["rarity"]]["color"]
    owned = wid in weapon_stars
    if selected:
        pixel_panel(screen, rect.inflate(10, 10), (255, 255, 255), (255, 255, 255), n=7, bw=3)
    pixel_panel(screen, rect, rc if owned else (60, 64, 90),
                tuple(c // 6 + 16 for c in rc) if owned else (22, 24, 40), n=6, bw=3)
    img = weapon_img(wid, 3, dark=not owned)
    if owned:
        add_glow(screen, rarity_glows[w["rarity"]], (rect.centerx, rect.y + 44), 0.55)
    screen.blit(img, img.get_rect(center=(rect.centerx, rect.y + 44)))
    if owned:
        stars = weapon_stars[wid]
        for k in range(MAX_STAR):
            draw_star(screen, (rect.centerx - 24 + k * 12, rect.bottom - 14), 5, rc, empty=k >= stars)
        if wid == equipped_weapon:
            tag = pygame.Rect(rect.x + 7, rect.y + 7, 18, 18)
            pygame.draw.rect(screen, (60, 190, 110), tag)
            pygame.draw.rect(screen, (14, 12, 30), tag, 2)
            blit_text(screen, tiny_font, "E", (255, 255, 255), tag.center, True)
    else:
        blit_text(screen, tiny_font, "???", (110, 116, 150), (rect.centerx, rect.bottom - 14), True)


def draw_pull_button(rect, label, cost, hovered):
    can = gold >= cost
    draw_button(screen, rect, "", hovered, can, (255, 210, 90))
    blit_text(screen, small_font, label, (255, 255, 255) if can else (125, 130, 155), (rect.centerx, rect.y + 17), True)
    ct = tiny_font.render(f"{cost:,} G", True, (255, 230, 120) if can else (255, 120, 120))
    screen.blit(ct, ct.get_rect(center=(rect.centerx, rect.y + 39)))


def draw_shop_screen():
    draw_menu_bg(110)
    blit_text(screen, font, "장비 상점", (255, 230, 120), (WIDTH // 2, 30), True)
    draw_gold_panel(screen)
    mouse = pygame.mouse.get_pos()
    draw_button(screen, BACK_RECT, "< 뒤로", BACK_RECT.collidepoint(mouse), True, (150, 170, 255))

    # 왼쪽: 고른 무기 자세히 보기
    wid = WEAPON_ORDER[shop_sel]
    w = WEAPONS[wid]
    rc = RARITY[w["rarity"]]["color"]
    owned = wid in weapon_stars
    star = weapon_stars.get(wid, 1)
    panel = pygame.Rect(20, 66, 300, 458)
    pixel_panel(screen, panel, tuple(c * 2 // 3 for c in rc), (24, 26, 46), n=8, bw=4)
    blit_text(screen, small_font, RARITY[w["rarity"]]["name"], rc, (panel.centerx, panel.y + 26), True)
    add_glow(screen, rarity_glows[w["rarity"]], (panel.centerx, panel.y + 130), 1.7)
    img = weapon_img(wid, 7, dark=not owned)
    screen.blit(img, img.get_rect(center=(panel.centerx, panel.y + 130 + int(4 * math.sin(frame_tick * 0.08)))))
    blit_text(screen, small_font, w["name"], (255, 255, 255), (panel.centerx, panel.y + 220), True)
    for k in range(MAX_STAR):
        draw_star(screen, (panel.centerx - 52 + k * 26, panel.y + 254), 10, rc, empty=(not owned) or k >= star)
    for i, line in enumerate(weapon_stat_lines(wid, star)):
        blit_text(screen, tiny_font, line, (200, 225, 255), (panel.centerx, panel.y + 292 + i * 24), True)
    if not owned:
        hint = "뽑기에서 얻을 수 있어요"
    elif star >= MAX_STAR:
        hint = "최대 강화!"
    else:
        hint = "같은 무기를 또 뽑으면 강화돼요 (+20%)"
    blit_text(screen, tiny_font, hint, (150, 160, 190), (panel.centerx, panel.bottom - 84), True)
    if not owned:
        draw_button(screen, EQUIP_RECT, "미획득", False, False)
    elif wid == equipped_weapon:
        draw_button(screen, EQUIP_RECT, "장착 중", False, False, (90, 220, 140))
    else:
        draw_button(screen, EQUIP_RECT, "장착하기", EQUIP_RECT.collidepoint(mouse), True, (90, 220, 140))

    # 오른쪽 위: 뽑기
    pp = pygame.Rect(340, 66, 440, 128)
    pixel_panel(screen, pp, (235, 190, 70), (30, 28, 48), n=8, bw=4)
    blit_text(screen, small_font, "무기 뽑기", (255, 230, 120), (pp.x + 18, pp.y + 6))
    current_pity = pity_by_slot.get(SLOTS[shop_tab], 0)
    pt = tiny_font.render(f"전설 이상 확정까지 {PITY_LIMIT - current_pity}회", True, (255, 195, 60))
    screen.blit(pt, pt.get_rect(topright=(pp.right - 16, pp.y + 14)))
    draw_pull_button(PULL1_RECT, "1회 뽑기", PULL_COST, PULL1_RECT.collidepoint(mouse))
    draw_pull_button(PULL10_RECT, "10회 뽑기", PULL10_COST, PULL10_RECT.collidepoint(mouse))

    # 오른쪽 아래: 가진 무기 모음
    for i, (wid2, cell) in enumerate(zip(WEAPON_ORDER, shop_cell_rects())):
        draw_weapon_cell(cell, wid2, i == shop_sel)
    draw_toast(screen)
    blit_text(screen, tiny_font, "방향키: 선택   E: 장착   1: 1회 뽑기   2: 10회 뽑기   ESC: 뒤로",
              (150, 160, 190), (WIDTH // 2, 582), True)
    if shop_results:
        draw_pull_results()


def draw_result_card(rect, res, t, big):
    w = WEAPONS[res["id"]]
    rc = RARITY[w["rarity"]]["color"]
    ease = 1 - (1 - t) ** 3
    r = rect.move(0, int((1 - ease) * 40))
    legend = w["rarity"] == "legend"
    if legend:
        add_glow(screen, rarity_glows["legend"], r.center, 3.0 if big else 1.8)
    pixel_panel(screen, r, rc, tuple(c // 6 + 16 for c in rc), n=8, bw=4)
    blit_text(screen, small_font if big else tiny_font, RARITY[w["rarity"]]["name"], rc, (r.centerx, r.y + (24 if big else 14)), True)
    add_glow(screen, rarity_glows[w["rarity"]], (r.centerx, r.y + r.h // 2 - 10), 1.2 if big else 0.7)
    img = weapon_img(res["id"], 6 if big else 3)
    screen.blit(img, img.get_rect(center=(r.centerx, r.y + r.h // 2 - 10)))
    blit_text(screen, small_font if big else tiny_font, w["name"], (255, 255, 255), (r.centerx, r.bottom - (64 if big else 46)), True)
    if res["kind"] == "new":
        col, txt = ((255, 235, 110) if (frame_tick // 10) % 2 == 0 else (255, 160, 70)), "NEW!"
    elif res["kind"] == "star":
        col, txt = (140, 255, 170), f"강화!  별 {weapon_stars[res['id']]}"
    else:
        col, txt = (255, 210, 90), f"중복  +{DUP_REFUND}G"
    blit_text(screen, small_font if big else tiny_font, txt, col, (r.centerx, r.bottom - (28 if big else 20)), True)


def draw_pull_results():
    draw_dim(205)
    blit_text(screen, font, "획득!", (255, 230, 120), (WIDTH // 2, 44), True)
    n = len(shop_results)
    if n == 1:
        rect = pygame.Rect(WIDTH // 2 - 120, 100, 240, 360)
        draw_result_card(rect, shop_results[0], max(0.0, min(1.0, shop_anim / 14)), True)
    else:
        for i, res in enumerate(shop_results):
            rect = pygame.Rect(26 + (i % 5) * 152, 92 + (i // 5) * 204, 140, 192)
            t = max(0.0, min(1.0, (shop_anim - i * 5) / 12))
            if t > 0:
                draw_result_card(rect, res, t, False)
    if shop_anim > 20:
        blit_text(screen, small_font, "아무 키나 누르거나 클릭", (180, 190, 220), (WIDTH // 2, 560), True)



def draw_world():
    """게임 장면(바닥, 적, 캐릭터, 효과)을 world 이미지에 그려요."""
    world.blit(stage_bg, (0, 0))
    region_style = cur_def["style"]
    if region_style in ("dungeon", "ice", "lava"):
        draw_torches(world, cur_def["glow"])
    else:
        ambient = {"grave": (120, 255, 170), "desert": (245, 205, 120),
                   "swamp": (170, 240, 90), "abyss": (205, 135, 255)}.get(region_style, cur_def["mote"])
        for i in range(6):
            px = (i * 137 + frame_tick * (0.22 + i * 0.035) + 24 * math.sin(frame_tick * 0.02 + i)) % WIDTH
            py = (i * 91 + 38 * math.sin(frame_tick * 0.018 + i * 1.7)) % HEIGHT
            add_glow(world, cur_def["glow"], (px, py), 0.24)
            if (frame_tick // 5 + i * 3) % 8 < 5:
                pygame.draw.circle(world, ambient, (int(px), int(py)), 2 if i % 2 else 1)
    add_glow(world, glow_hero, player_pos)  # 주인공 주변이 밝아져요 (던전 분위기)
    draw_motes(world, 26, cur_def["mote"], 0.6)  # 떠다니는 먼지 / 눈 / 불씨

    for f in fires:  # 바닥에 남은 불    
        add_glow(world, glow_fire, f["pos"])
        draw_fire(world, f)
    # 보스 예고 구역(붉은 부채꼴)과 불줄기는 반투명 층에 한꺼번에 그려서 붙여요
    hazards = [e for e in enemies if e.get("boss") or (e["kind"] in CHARGERS and e.get("st") == "windup")]
    if hazards:
        hazard_layer.fill((0, 0, 0, 0))
        for b in hazards:
            if b.get("boss"):
                draw_boss_layer(hazard_layer, b)
            else:
                draw_charge_lane(hazard_layer, b)
        world.blit(hazard_layer, (0, 0))

    # 스테이지 위험 구역: 떨어질 자리를 미리 보여 줘요 (고드름 / 용암)
    if meteors and cur_def["haz"]:
        hz = cur_def["haz"]
        hazard_layer.fill((0, 0, 0, 0))
        for m in meteors:
            if m["t"] < METEOR_WARN:
                prog = m["t"] / METEOR_WARN
                c = (int(m["pos"].x), int(m["pos"].y))
                pygame.draw.circle(hazard_layer, (*hz["color"], int(40 + 70 * prog)), c, hz["r"])
                pygame.draw.circle(hazard_layer, (*hz["color"], 170), c, max(2, int(hz["r"] * prog)))
                pygame.draw.circle(hazard_layer, (*hz["light"], 230), c, hz["r"], 2)
        world.blit(hazard_layer, (0, 0))
        for m in meteors:  # 하늘에서 떨어지는 덩어리
            if m["t"] < METEOR_WARN:
                prog = m["t"] / METEOR_WARN
                fy = m["pos"].y - (1 - prog) ** 2 * 320
                cx, cy = int(m["pos"].x), int(fy)
                if cur_def["style"] == "ice":
                    pts = [(cx - 7, cy - 5), (cx + 7, cy - 5), (cx + 4, cy + 3), (cx, cy + 12), (cx - 4, cy + 3)]
                    pygame.draw.polygon(world, hz["color"], pts)
                    pygame.draw.line(world, hz["light"], (cx - 2, cy - 3), (cx, cy + 7), 2)
                elif cur_def["style"] == "lava":
                    pts = [(cx - 8, cy - 2), (cx - 4, cy - 8), (cx + 4, cy - 6),
                           (cx + 8, cy), (cx + 3, cy + 8), (cx - 5, cy + 5)]
                    pygame.draw.polygon(world, (170, 50, 25), pts)
                    pygame.draw.polygon(world, hz["color"], [(cx - 4, cy - 2), (cx + 3, cy - 4), (cx + 4, cy + 2), (cx - 2, cy + 4)])
                    pygame.draw.circle(world, hz["light"], (cx - 1, cy), 2)
                elif cur_def["style"] == "desert":
                    pts = [(cx, cy - 8), (cx + 8, cy), (cx, cy + 8), (cx - 8, cy)]
                    pygame.draw.polygon(world, (150, 115, 62), pts)
                    pygame.draw.line(world, hz["light"], (cx - 3, cy - 1), (cx + 3, cy - 4), 2)
                elif cur_def["style"] in ("grave", "swamp"):
                    pygame.draw.circle(world, hz["color"], (cx, cy), 8)
                    pygame.draw.circle(world, hz["light"], (cx - 2, cy - 2), 3)
                    pygame.draw.circle(world, (205, 255, 195), (cx + 3, cy + 2), 1)
                elif cur_def["style"] == "abyss":
                    pts = [(cx, cy - 9), (cx + 6, cy), (cx, cy + 9), (cx - 6, cy)]
                    pygame.draw.polygon(world, hz["color"], pts)
                    pygame.draw.circle(world, hz["light"], (cx, cy), 3)
                else:
                    pygame.draw.circle(world, hz["color"], (cx, cy), 8)
                    pygame.draw.circle(world, hz["light"], (cx, cy), 4)

    # 오라: 맥동하는 고리 + 도는 빛 알갱이
    if aura_level:
        r = aura_radius(aura_level)
        pulse = 1 + 0.04 * math.sin(frame_tick * 0.15)
        aura_s = pygame.Surface((r * 2 + 12, r * 2 + 12), pygame.SRCALPHA)
        c = (r + 6, r + 6)
        pygame.draw.circle(aura_s, (190, 110, 255, 38), c, int(r * pulse))
        pygame.draw.circle(aura_s, (220, 160, 255, 150), c, int(r * pulse), 3)
        for k in range(8):
            a = math.radians(frame_tick * 3 + k * 45)
            pt = (c[0] + math.cos(a) * r, c[1] + math.sin(a) * r)
            pygame.draw.circle(aura_s, (255, 230, 255, 230), pt, 3)
        world.blit(aura_s, aura_s.get_rect(center=(int(player_pos.x), int(player_pos.y))))
    for c in xt["clouds"]:
        a = min(1.0, c["life"] / 40)
        cs = pygame.Surface((c["r"] * 2 + 8, c["r"] * 2 + 8), pygame.SRCALPHA)
        cc = (c["r"] + 4, c["r"] + 4)
        cloud_fill = (95, 205, 175) if c.get("evolved") else (110, 220, 80)
        cloud_edge = (175, 255, 230) if c.get("evolved") else (170, 255, 120)
        pygame.draw.circle(cs, (*cloud_fill, int(55 * a)), cc, int(c["r"] * (1 + 0.04 * math.sin(frame_tick * 0.2))))
        pygame.draw.circle(cs, (*cloud_edge, int(130 * a)), cc, c["r"], 2)
        world.blit(cs, cs.get_rect(center=(int(c["pos"].x), int(c["pos"].y))))
    # 구슬: 위아래로 떠다니며 빛나요
    for g in gems:
        bob = math.sin(frame_tick * 0.12 + g.x * 0.05) * 2
        add_glow(world, glow_gem, g)
        world.blit(gem_sprite, gem_sprite.get_rect(center=(g.x, g.y + bob)))
    if altar_pos is not None and not altar_used:
        ax, ay = int(altar_pos.x), int(altar_pos.y)
        pulse = 1 + 0.08 * math.sin(frame_tick * 0.12)
        add_glow(world, glow_gem, altar_pos, 1.25 * pulse)
        pygame.draw.circle(world, (245, 205, 105), (ax, ay), int(26 * pulse), 2)
        pygame.draw.polygon(world, (110, 75, 45), [(ax, ay - 14), (ax + 14, ay), (ax, ay + 14), (ax - 14, ay)])
        pygame.draw.polygon(world, (255, 225, 135), [(ax, ay - 8), (ax + 8, ay), (ax, ay + 8), (ax - 8, ay)])
        blit_text(world, tiny_font, "고대 제단", (255, 230, 150), (ax, ay - 34), True)

    for d in drops:
        if d["life"] < 120 and (d["life"] // 6) % 2 == 0:
            continue  # 사라지기 직전 2초는 깜빡여요
        p = d["pos"]
        bob = math.sin(frame_tick * 0.1 + p.x) * 3
        draw_shadow(world, p, 22, 14)
        if d["kind"] == "elite_gear":
            item = d["item"]
            color = RARITY[WEAPONS[item]["rarity"]]["color"]
            add_glow(world, glow_elite, p, 1.15)
            pygame.draw.circle(world, color, (int(p.x), int(p.y + bob)), 16, 2)
            icon = weapon_img(item, 2)
            world.blit(icon, icon.get_rect(center=(p.x, p.y + bob)))
        elif d["kind"] == "heart":
            add_glow(world, glow_proj, p, 0.8)
            world.blit(heart_full, heart_full.get_rect(center=(p.x, p.y + bob)))
        elif d["kind"] == "magnet":
            add_glow(world, glow_gem, p, 1.2)
            world.blit(magnet_small, magnet_small.get_rect(center=(p.x, p.y + bob)))
        else:
            pygame.draw.circle(world, (40, 40, 50), (p.x, p.y + bob), 10)
            pygame.draw.circle(world, (255, 140, 40), (p.x + 7, p.y - 9 + bob), 3)
    for c in chests:
        bob = int(3 * math.sin(frame_tick * 0.1))
        add_glow(world, glow_proj, c, 1.6)
        draw_shadow(world, c, 44, 18)
        pygame.draw.rect(world, (90, 55, 25), (c.x - 20, c.y - 14 + bob, 40, 28))
        pygame.draw.rect(world, (150, 100, 50), (c.x - 18, c.y - 12 + bob, 36, 12))
        pygame.draw.rect(world, (250, 200, 80), (c.x - 18, c.y - 1 + bob, 36, 4))
        pygame.draw.rect(world, (250, 200, 80), (c.x - 4, c.y - 4 + bob, 8, 10))

    # 대시 잔상
    for gh in ghosts:
        base_img = hero_ghost_left if gh["left"] else hero_ghost
        s = base_img.copy()
        s.set_alpha(int(150 * gh["life"] / 14))
        world.blit(s, s.get_rect(center=gh["pos"]))

    # 적: 그림자 + 통통 튀는 움직임 + 냉기에 맞으면 푸르게
    for e in enemies:
        t = enemy_types[e["kind"]]
        boss = e.get("boss")
        if boss and e["kind"] == "dragon":
            draw_dragon_tail(world, e)  # 꼬리는 몸 뒤에 깔려요
        base_sprite = t["sprite"]
        sw, sh = base_sprite.get_size()
        draw_shadow(world, e["pos"], int(sw * 0.8), sh // 2 - 2)
        if boss:
            boss_glow = _boss_glow_cache.get(e["kind"])
            if boss_glow is None:
                boss_glow = make_glow(54, t["color"])
                _boss_glow_cache[e["kind"]] = boss_glow
            pulse = 0.72 + 0.08 * math.sin(frame_tick * 0.12)
            if e["hp"] <= e["max_hp"] * (0.62 if e.get("final") else 0.55):
                pulse += 0.24 + 0.08 * math.sin(frame_tick * 0.3)
            add_glow(world, boss_glow, e["pos"], pulse)
        if e["flash"] > 0:
            sprite = t["flash"]  # 맞은 직후엔 하얀 그림
        elif e.get("slow", 0) > 0:
            sprite = t["frost"]  # 냉기에 맞은 적은 푸른 그림
        else:
            sprite = base_sprite
        if e["kind"] in CHARGERS and e.get("st") == "windup" and (frame_tick // 3) % 2 == 0:
            sprite = t["flash"]
        if e["kind"] in SHOOTERS and e.get("cd", 99) < 40:
            shot_color = t.get("shot_color", (170, 110, 230))
            shot_glow = glow_fire if shot_color[0] > shot_color[2] else (glow_gem if shot_color[2] > shot_color[0] else glow_mage)
            add_glow(world, shot_glow, e["pos"], 1.0)
        if e["kind"] == "golem" and e["state"] in ("slam_windup", "shard_windup") and (frame_tick // 4) % 2 == 0:
            sprite = t["flash"]  # 공격 직전에 번쩍여요
        if e.get("elite"):  # 엘리트: 뒤에서 금빛이 맥동해요
            add_glow(world, glow_elite, e["pos"], 1.0 + 0.1 * math.sin(frame_tick * 0.2))
        ph = (id(e) % 100) * 0.3
        if boss:
            bob = math.sin(frame_tick * 0.08 + ph) * 3
            world.blit(sprite, sprite.get_rect(center=(e["pos"].x, e["pos"].y + bob)))
        else:
            k = math.sin(frame_tick * 0.25 + ph)  # 눌렸다 늘어났다 하며 걸어요
            w2, h2 = int(sw * (1 + 0.06 * k)), int(sh * (1 - 0.06 * k))
            sp = squashed(sprite, w2, h2)
            world.blit(sp, sp.get_rect(midbottom=(e["pos"].x, e["pos"].y + sh // 2)))
        if e.get("burn", 0) > 0:  # 불에 타는 중: 머리 위에서 불꽃이 일렁여요
            fx, fy = e["pos"].x, e["pos"].y - sh // 2
            add_glow(world, glow_fire, (fx, fy + 6), 0.9)
            for k in range(3):
                fh = 6 + ((frame_tick // 3 + k * 2) % 3) * 3
                pygame.draw.rect(world, (255, 120, 30), (fx - 9 + k * 7, fy - fh + 6, 5, fh))
                pygame.draw.rect(world, (255, 225, 110), (fx - 8 + k * 7, fy - fh + 8, 3, max(1, fh - 4)))
        if e.get("elite"):  # 엘리트 체력 바
            bw = 38
            bx, by = e["pos"].x - bw / 2, e["pos"].y - sh // 2 - 14
            pygame.draw.rect(world, (30, 10, 10), (bx - 1, by - 1, bw + 2, 7))
            pygame.draw.rect(world, (255, 200, 60), (bx, by, bw * max(0, e["hp"]) / e["max_hp"], 5))
        if boss and e["kind"] == "orc":
            draw_orc_club(world, e)  # 몽둥이는 몸 앞에 그려요
        if boss and e["kind"] == "dragon" and e["state"] in ("breath_windup", "breath"):
            add_glow(world, glow_fire, e["pos"] + pygame.Vector2(40, 0).rotate(breath_angle(e) if e["state"] == "breath" else e["angle"]), 1.6)

    # 주인공: 그림자 + 바라보는 방향 + 걸을 때 통통
    if invuln_timer == 0 or (invuln_timer // 4) % 2 == 0:
        hb = abs(math.sin(frame_tick * 0.3)) * 3 if hero_walking else math.sin(frame_tick * 0.08)
        draw_shadow(world, player_pos, 34, 20)
        hs = hero_left if facing_left else hero_sprite
        world.blit(hs, hs.get_rect(center=(player_pos.x, player_pos.y - hb)))
        draw_hero_weapon(world, player_pos, facing_left, hb)
    if shield_hp > 0:  # 보호막: 주인공을 감싸는 청록색 방울
        br = 26 + int(2 * math.sin(frame_tick * 0.15))
        bs = pygame.Surface((br * 2 + 6, br * 2 + 6), pygame.SRCALPHA)
        pygame.draw.circle(bs, (110, 230, 240, 45), (br + 3, br + 3), br)
        pygame.draw.circle(bs, (190, 250, 255, 210), (br + 3, br + 3), br, 2)
        world.blit(bs, bs.get_rect(center=(int(player_pos.x), int(player_pos.y))))
    for pos, ang in get_blade_positions():
        add_glow(world, glow_gem, pos, 0.8)
        draw_blade(world, pos, ang)

    if pet_id:
        pimg = weapon_img(pet_id, 2)
        draw_shadow(world, pet_pos, 20, 12)
        world.blit(pimg, pimg.get_rect(center=(pet_pos.x, pet_pos.y + math.sin(frame_tick * 0.15) * 3)))

    # 투사체: 빛 + 꼬리
    for s in enemy_shots:
        shot_color = s.get("color", (200, 130, 255))
        shot_glow = glow_fire if shot_color[0] > shot_color[2] else (glow_gem if shot_color[2] > shot_color[0] else glow_mage)
        add_glow(world, shot_glow, s["pos"], 0.8)
        pygame.draw.circle(world, shot_color, s["pos"], 7)
        pygame.draw.circle(world, (245, 245, 255), s["pos"], 3)
    shot_weapon = WEAPONS.get(equipped_weapon, {})
    shot_colors = shot_weapon.get("c", ((255, 190, 70), (255, 245, 185), (100, 70, 40)))
    shot_rarity = shot_weapon.get("rarity", "common")
    for p in projectiles:
        add_glow(world, rarity_glows.get(shot_rarity, glow_proj), p["pos"], 0.72)
        tail = p["pos"] - p["vel"] * 1.6
        pygame.draw.line(world, shot_colors[0], tail, p["pos"], 4)
        pygame.draw.line(world, shot_colors[1], tail, p["pos"], 1)
        pygame.draw.circle(world, shot_colors[0], p["pos"], projectile_radius + 1)
        pygame.draw.circle(world, shot_colors[1], p["pos"], max(2, projectile_radius - 1))
    for c in xt["comets"]:
        direction = c["target"] - c["start"]
        if direction.length_squared() > 0:
            direction = direction.normalize()
            tail = c["pos"] - direction * 38
            pygame.draw.line(world, (90, 145, 255), tail, c["pos"], 12)
            pygame.draw.line(world, (205, 235, 255), tail, c["pos"], 5)
        add_glow(world, glow_proj, c["pos"], 1.35)
        pygame.draw.circle(world, (245, 250, 255), c["pos"], 5)

    # 불꽃검: 휘두르는 불꽃 호 + 불타는 칼날
    for fl in flames:
        k = 1 - fl["life"] / fl["max"]
        start = fl["ang"] - fl["half"]
        cur = start + 2 * fl["half"] * min(1.0, k * 1.5)
        fade = max(0.0, 1 - k)
        mid = (start + cur) / 2
        hh = max(1.0, (cur - start) / 2)
        hazard_layer.fill((0, 0, 0, 0))
        pygame.draw.polygon(hazard_layer, (255, 110, 30, int(120 * fade)), wedge_points(player_pos, mid, hh, fl["reach"]))
        pygame.draw.polygon(hazard_layer, (255, 210, 90, int(170 * fade)), wedge_points(player_pos, mid, hh, fl["reach"] * 0.7))
        tip = player_pos + pygame.Vector2(fl["reach"], 0).rotate(cur)
        pygame.draw.line(hazard_layer, (255, 140, 40, int(255 * fade)), player_pos, tip, 7)
        pygame.draw.line(hazard_layer, (255, 245, 200, int(255 * fade)), player_pos, tip, 3)
        world.blit(hazard_layer, (0, 0))
        add_glow(world, glow_fire, tip, 2.2)

    # 번개 낙뢰: 하늘에서 꽂히는 지그재그
    for b in bolts:
        x, y = b["pos"].x, b["pos"].y
        bolt_rng = random.Random(b.get("seed", int(x * 31 + y * 17)))
        pts, cx = [], x + bolt_rng.randint(-14, 14)
        for yy in range(-10, int(y), 24):
            pts.append((int(cx), yy))
            cx = x + bolt_rng.randint(-20, 20)
        pts.append((int(x), int(y)))
        if len(pts) > 1:
            pygame.draw.lines(world, (95, 150, 255), False, pts, 9)
            pygame.draw.lines(world, (255, 220, 100), False, pts, 5)
            pygame.draw.lines(world, (255, 255, 235), False, pts, 2)
            for i in range(2, len(pts) - 2, 4):
                bx, by = pts[i]
                end = (bx + bolt_rng.choice((-1, 1)) * bolt_rng.randint(12, 26), by + bolt_rng.randint(10, 24))
                pygame.draw.line(world, (255, 225, 130), (bx, by), end, 2)
        add_glow(world, glow_zap, b["pos"], 1.5)

    for arc in xt.get("chain_arcs", []):
        start, end = arc["a"], arc["b"]
        delta = end - start
        if delta.length_squared() == 0:
            continue
        side = pygame.Vector2(-delta.y, delta.x).normalize()
        arc_rng = random.Random(arc["seed"])
        fade = max(0.2, arc["life"] / arc["max"])
        points = [(round(start.x), round(start.y))]
        for j in range(1, 4):
            t = j / 4
            offset = arc_rng.randint(-10, 10) * fade
            points.append((round(start.x + delta.x * t + side.x * offset),
                           round(start.y + delta.y * t + side.y * offset)))
        points.append((round(end.x), round(end.y)))
        pygame.draw.lines(world, (int(75 * fade), int(95 * fade), int(220 * fade)), False, points, 7)
        pygame.draw.lines(world, (int(155 * fade), int(195 * fade), 255), False, points, 3)

    # 폭발 / 충격 고리
    for rg in rings:
        k = 1 - rg["life"] / rg["max"]
        rad = max(4, int(rg["r"] * (0.3 + 0.7 * k)))
        rs = pygame.Surface((rad * 2 + 8, rad * 2 + 8), pygame.SRCALPHA)
        a = int(220 * (1 - k))
        pygame.draw.circle(rs, (*rg["color"], a // 3), (rad + 4, rad + 4), rad)
        pygame.draw.circle(rs, (*rg["color"], a), (rad + 4, rad + 4), rad, 4)
        world.blit(rs, rs.get_rect(center=(int(rg["pos"].x), int(rg["pos"].y))))

    # 파편: 빛나며 줄어들어요
    for p in particles:
        size = 2 + p["life"] // 8
        pygame.draw.rect(world, p["color"], (p["pos"].x - size / 2, p["pos"].y - size / 2, size, size))
        if p["life"] > 12:
            add_glow(world, glow_zap, p["pos"], 0.3)

    # 데미지 숫자: 처음엔 크게 뜨고 점점 작아져요
    for f in floaters:
        shadow_t = tiny_font.render(f["text"], True, (0, 0, 0))
        text_t = tiny_font.render(f["text"], True, f["color"])
        grow = 1 + 0.4 * max(0, f["life"] - 20) / 10
        if grow > 1.05:
            size = (int(text_t.get_width() * grow), int(text_t.get_height() * grow))
            text_t = pygame.transform.scale(text_t, size)
            shadow_t = pygame.transform.scale(shadow_t, size)
        world.blit(shadow_t, shadow_t.get_rect(center=(f["pos"].x + 1, f["pos"].y + 1)))
        world.blit(text_t, text_t.get_rect(center=f["pos"]))

    if xt["freeze"] > 0:
        world.blit(freeze_tint, (0, 0))

_hud_shadow_cache = {}


def hud_panel(surf, rect, accent, n=4, bw=3):
    """HUD 상자: 그림자 + 어두운 바탕 + 위쪽 하이라이트 + 아래 그늘 + 포인트 색 윗줄."""
    sh = _hud_shadow_cache.get(rect.size)
    if sh is None:
        sh = pygame.Surface(rect.size, pygame.SRCALPHA)
        sh.fill((0, 0, 0, 110))
        _hud_shadow_cache[rect.size] = sh
    surf.blit(sh, rect.move(2, 3))
    pixel_panel(surf, rect, tuple(c * 3 // 5 for c in accent), (22, 24, 44), n=n, bw=bw)
    inner = rect.inflate(-2 * bw, -2 * bw)
    pygame.draw.line(surf, (46, 50, 84), (inner.x + n, inner.y), (inner.right - n - 1, inner.y))
    pygame.draw.line(surf, (12, 13, 26), (inner.x + n, inner.bottom - 1), (inner.right - n - 1, inner.bottom - 1))
    pygame.draw.line(surf, accent, (rect.x + n + 2, rect.y + 1), (rect.right - n - 3, rect.y + 1))
def draw_gauge(surf, rect, ratio, top, bottom, seg=0):
    """어두운 홈 + 그라데이션 + 윗면 광택 + 아래 그늘 + 흐르는 빛줄기 + 끝 반짝임."""
    pixel_panel(surf, rect, (8, 9, 18), (8, 9, 18), n=3, bw=3)
    pixel_panel(surf, rect.inflate(-2, -2), (88, 98, 170), (16, 18, 34), n=3, bw=2)
    inner = rect.inflate(-8, -8)
    pygame.draw.rect(surf, (20, 22, 42), inner)
    pygame.draw.line(surf, (10, 11, 22), inner.topleft, (inner.right - 1, inner.y))
    w = int(inner.w * max(0.0, min(1.0, ratio)))
    if w > 0:
        fill = pygame.Rect(inner.x, inner.y + 1, w, inner.h - 1)
        for yy in range(fill.h):
            col = lerp_color(top, bottom, yy / max(1, fill.h - 1))
            pygame.draw.line(surf, col, (fill.x, fill.y + yy), (fill.x + w - 1, fill.y + yy))
        white = (255, 255, 255)
        pygame.draw.line(surf, lerp_color(top, white, 0.6), (fill.x, fill.y), (fill.x + w - 1, fill.y))
        pygame.draw.line(surf, lerp_color(top, white, 0.3), (fill.x, fill.y + 1), (fill.x + w - 1, fill.y + 1))
        pygame.draw.line(surf, lerp_color(bottom, (0, 0, 0), 0.45), (fill.x, fill.bottom - 1), (fill.x + w - 1, fill.bottom - 1))
        surf.set_clip(fill)
        sheen = pygame.Surface((14, fill.h), pygame.SRCALPHA)
        sheen.fill((255, 255, 255, 45))
        surf.blit(sheen, (inner.x + (frame_tick * 3) % (inner.w + 80) - 40, fill.y))
        surf.set_clip(None)
        pygame.draw.rect(surf, lerp_color(top, white, 0.8), (fill.x + w - 2, fill.y, 2, fill.h))
    for i in range(1, seg):
        x = inner.x + inner.w * i // seg
        pygame.draw.line(surf, (12, 14, 28), (x, inner.bottom - 4), (x, inner.bottom - 1))


def next_boss_seconds():
    """다음 보스가 나올 때까지 남은 초 (없으면 None)."""
    if cur_stage == 0:
        nf = next_boss_frame
    else:
        bl = cur_def["bosses"]
        if stage_boss_idx >= len(bl):
            return None
        nf = bl[stage_boss_idx][1]
    return max(0, (nf - survive_frames) // 60)


shield_icon_dim = small_icons["보호막"].copy()
shield_icon_dim.fill((70, 80, 90, 255), special_flags=pygame.BLEND_RGBA_MULT)
dash_icon_dim = small_icons["질주"].copy()
dash_icon_dim.fill((90, 100, 110, 255), special_flags=pygame.BLEND_RGBA_MULT)
glow_dash = make_glow(22, (40, 150, 110))


def draw_hud():
    # ── 맨 위: 경험치 바 ──
    xp_rect = pygame.Rect(8, 6, WIDTH - 16, 26)
    draw_gauge(screen, xp_rect, xp / xp_to_next, (120, 220, 255), (40, 110, 225))
    xp_label = pygame.Rect(xp_rect.x + 5, xp_rect.y + 3, 48, xp_rect.h - 6)
    xp_value = pygame.Rect(xp_rect.right - 109, xp_rect.y + 3, 104, xp_rect.h - 6)
    pixel_panel(screen, xp_label, (70, 125, 195), (18, 25, 48), n=4, bw=2)
    pixel_panel(screen, xp_value, (70, 125, 195), (18, 25, 48), n=4, bw=2)
    blit_text(screen, tiny_font, "EXP", (225, 242, 255), xp_label.center, True)
    blit_text(screen, tiny_font, f"{int(xp)} / {xp_to_next}", (255, 255, 255), xp_value.center, True)

    # ── 첫째 줄 (y=36): 레벨 | 보스 타이머 | 시간 | 스테이지 | 처치 수 ──
    r1 = 36
    lv_rect = pygame.Rect(8, r1, 84, 32)
    hud_panel(screen, lv_rect, (255, 210, 90))
    blit_text(screen, small_font, f"Lv.{level}", (255, 230, 120), lv_rect.center, True)

    boss_rect = pygame.Rect(WIDTH // 2 - 170, r1, 104, 32)
    if any(e.get("boss") for e in enemies):
        hud_panel(screen, boss_rect, (255, 90, 90))
        if (frame_tick // 15) % 2 == 0:
            blit_text(screen, tiny_font, "BOSS!", (255, 100, 100), boss_rect.center, True)
    elif not game_over:
        nb = next_boss_seconds()
        if nb is not None:
            hud_panel(screen, boss_rect, (200, 80, 80))
            blit_text(screen, tiny_font, f"BOSS {mmss(nb)}", (255, 150, 140), boss_rect.center, True)

    time_rect = pygame.Rect(WIDTH // 2 - 56, r1, 112, 32)
    hud_panel(screen, time_rect, (130, 140, 210))
    blit_text(screen, small_font, time_string(), (255, 255, 255), time_rect.center, True)

    stage_rect = pygame.Rect(WIDTH // 2 + 66, r1, 140, 32)
    hud_panel(screen, stage_rect, STAGE_ACCENT[cur_stage])
    blit_text(screen, tiny_font, cur_def["name"], STAGE_ACCENT[cur_stage], stage_rect.center, True)

    kill_rect = pygame.Rect(WIDTH - 158, r1, 150, 32)
    hud_panel(screen, kill_rect, (235, 100, 100))
    blit_text(screen, small_font, f"Kills {kills}", (255, 200, 200), kill_rect.center, True)

    # ── 둘째 줄 (y=74): 체력 하트 | 보스 체력 | 골드 ──
    hp_rect = pygame.Rect(8, 74, player_max_hp * 28 + 14, 34)
    hud_panel(screen, hp_rect, (220, 90, 110))
    for i in range(player_max_hp):
        img = heart_full if i < player_hp else heart_empty
        dy = int(2 * math.sin(frame_tick * 0.25)) if (player_hp == 1 and i == 0) else 0
        screen.blit(img, (15 + i * 28, 79 + dy))

    g_rect = pygame.Rect(WIDTH - 158, 74, 150, 32)
    hud_panel(screen, g_rect, (235, 190, 70))
    screen.blit(coin_img, coin_img.get_rect(center=(g_rect.x + 22, g_rect.centery)))
    gt = small_font.render(f"{run_gold:,}", True, (255, 230, 120))
    screen.blit(gt, gt.get_rect(midright=(g_rect.right - 12, g_rect.centery)))

    for e in enemies:
        if e.get("boss"):
            if e.get("mini_boss"):
                mini_ratio = max(0.0, min(1.0, e["hp"] / max(1.0, e["max_hp"])))
                draw_gauge(screen, pygame.Rect(WIDTH // 2 - 150, 85, 300, 16),
                           mini_ratio, (255, 205, 100), (115, 65, 35), seg=20)
                boss_label = "미니 보스 · " + BOSS_NAMES[e["kind"]]
            else:
                half_hp = max(1.0, e["max_hp"] / 2)
                first_bar = max(0.0, min(1.0, (e["hp"] - half_hp) / half_hp))
                second_bar = max(0.0, min(1.0, e["hp"] / half_hp))
                draw_gauge(screen, pygame.Rect(WIDTH // 2 - 150, 76, 300, 14),
                           first_bar, (255, 150, 105), (190, 55, 45), seg=20)
                draw_gauge(screen, pygame.Rect(WIDTH // 2 - 150, 94, 300, 14),
                           second_bar, (255, 95, 110), (155, 25, 50), seg=20)
                boss_label = BOSS_NAMES[e["kind"]] + (" (최종)" if e.get("final") else "")
            blit_text(screen, tiny_font, boss_label, (255, 255, 255), (WIDTH // 2, 118), True)
            break

    # ── 셋째 줄 (y=114): 대시 | 보호막 ──
    dr = pygame.Rect(8, 114, 156, 28)
    ready = dash_cd == 0
    hud_panel(screen, dr, (110, 255, 200) if ready else (90, 110, 140))
    if ready:
        add_glow(screen, glow_dash, (dr.x + 18, dr.centery), 1.0 + 0.1 * math.sin(frame_tick * 0.2))
    screen.blit(small_icons["질주"] if ready else dash_icon_dim, (dr.x + 6, dr.y + 2))
    draw_gauge(screen, pygame.Rect(dr.x + 36, dr.y + 6, 70, 16), 1 - dash_cd / dash_cd_max,
               (140, 255, 230), (50, 190, 150))
    if ready:
        col = (210, 255, 235) if (frame_tick // 20) % 2 == 0 else (120, 235, 195)
        blit_text(screen, tiny_font, "READY", col, (dr.x + 132, dr.centery), True)
    else:
        blit_text(screen, tiny_font, f"{dash_cd / 60:.1f}s", (160, 180, 205), (dr.x + 132, dr.centery), True)

    if shield_level:
        sr = pygame.Rect(172, 114, shield_level * 28 + 10, 28)
        hud_panel(screen, sr, (110, 225, 235))
        for i in range(shield_level):
            screen.blit(small_icons["보호막"] if i < shield_hp else shield_icon_dim, (sr.x + 6 + i * 28, sr.y + 2))

    # ── 오른쪽 아래 줄: 부활 / 콤보 ──
    ry = 112
    if revive_left:
        rr = pygame.Rect(WIDTH - 158, ry, 150, 28)
        hud_panel(screen, rr, (120, 255, 170))
        blit_text(screen, tiny_font, f"부활 x{revive_left}", (150, 255, 180), rr.center, True)
        ry += 34
    if combo >= 5:
        cc = (255, 235, 120) if combo < 25 else (255, 160, 70)
        cr = pygame.Rect(WIDTH - 158, ry, 150, 30)
        hud_panel(screen, cr, cc)
        blit_text(screen, tiny_font, f"COMBO {combo}", cc, (cr.centerx, cr.centery - 3), True)
        pygame.draw.rect(screen, (20, 16, 10), (cr.x + 12, cr.bottom - 8, cr.w - 24, 3))
        pygame.draw.rect(screen, cc, (cr.x + 12, cr.bottom - 8, int((cr.w - 24) * combo_timer / 150), 3))

    # ── 화면 가운데 큰 안내 문구 ──
    if banner_timer > 0 and (not banner_blink or (frame_tick // 8) % 2 == 0):
        blit_text(screen, font, banner_text, banner_color, (WIDTH // 2, 170), True)

    # ── 보유 스킬: 공격과 보조를 나눠서 표시해요 ──
    owned_attack = [n for n in upgrade_names if n in ATTACK_SKILLS and skill_levels.get(n, 0) > 0]
    owned_support = [n for n in upgrade_names if n in SUPPORT_SKILLS and skill_levels.get(n, 0) > 0]
    groups = [
        ("공격", owned_attack, (255, 150, 120), 10),
        ("보조", owned_support, (130, 220, 240), 210),
    ]
    for label, names, label_color, group_x in groups:
        blit_text(screen, tiny_font, f"{label} {len(names)}/5", label_color, (group_x + 2, HEIGHT - 78))
        for i, name in enumerate(names):
            x = group_x + i * 36
            lv = skill_levels[name]
            slot = pygame.Rect(x - 2, HEIGHT - 60, 32, 52)
            hud_panel(screen, slot, upgrade_style[name]["color"], n=3, bw=2)
            screen.blit(small_icons[name], (x + 2, HEIGHT - 56))
            blit_text(screen, tiny_font, str(lv), (255, 255, 255), (x + 14, HEIGHT - 18), True)
    if skill_evolutions:
        evolved = ", ".join(sorted(skill_evolutions))
        blit_text(screen, tiny_font, f"진화: {evolved}", (225, 235, 190), (WIDTH // 2, HEIGHT - 74), True)
    draw_toast(screen, 500)


def draw_level_up():
    draw_dim(170)
    bob = int(3 * math.sin(level_up_anim * 0.15))
    head = "보물 상자!" if chest_mode else "LEVEL UP!"
    add_glow(screen, glow_proj, (WIDTH // 2, 60 + bob), 4.5)
    blit_text(screen, font, head, (255, 230, 120), (WIDTH // 2, 60 + bob), True)
    sub_msg = "업그레이드를 하나 고르세요" if chest_mode else f"Lv.{level - 1} -> Lv.{level}"
    sub = small_font.render(sub_msg, True, (180, 190, 220))
    screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 105)))
    attack_used = sum(1 for n in ATTACK_SKILLS if skill_levels.get(n, 0) > 0)
    support_used = sum(1 for n in SUPPORT_SKILLS if skill_levels.get(n, 0) > 0)
    blit_text(screen, tiny_font,
              f"공격 {attack_used}/{ATTACK_SKILL_SLOTS}  ·  보조 {support_used}/{SUPPORT_SKILL_SLOTS}  ·  LV 5/5",
              (175, 195, 220), (WIDTH // 2, 130), True)

    mouse_pos = pygame.mouse.get_pos()
    for i, (name, card) in enumerate(zip(choices, get_card_rects())):
        t = max(0.0, min(1.0, (level_up_anim - i * 4) / 14))
        ease = 1 - (1 - t) ** 3
        slide = int((1 - ease) * 80)
        hovered = card.collidepoint(mouse_pos) and level_up_anim > 12
        draw_card(screen, card, name, i, hovered, slide)

    hint = small_font.render("선택 1 / 2 / 3  ·  R: 리롤", True, (180, 190, 220))
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 40)))
    can_reroll = rerolls_left > 0 and any(name not in choices for name in available_upgrades())
    reroll_hover = REROLL_RECT.collidepoint(mouse_pos)
    draw_button(screen, REROLL_RECT, f"리롤 (R) {rerolls_left}/3", reroll_hover, can_reroll,
                (160, 190, 255))


def draw_pause():
    draw_dim(150)
    blit_text(screen, font, "PAUSED", (255, 255, 255), (WIDTH // 2, HEIGHT // 2 - 30), True)
    hint = small_font.render("P 키로 계속하기", True, (180, 190, 220))
    screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)))
    quit_hint = small_font.render("Q 키: 포기하고 골드 받기", True, (255, 215, 90))
    screen.blit(quit_hint, quit_hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 80)))


def draw_game_over():
    draw_dim(170)
    if stage_cleared:
        head, head_col = "STAGE CLEAR!", (255, 230, 120)
        add_glow(screen, glow_proj, (WIDTH // 2, HEIGHT // 2 - 100), 5.0)
    else:
        head, head_col = "GAME OVER", (255, 255, 255)
    blit_text(screen, font, head, head_col, (WIDTH // 2, HEIGHT // 2 - 100), True)
    blit_text(screen, tiny_font, cur_def["name"], STAGE_ACCENT[cur_stage], (WIDTH // 2, HEIGHT // 2 - 66), True)
    stats = small_font.render(
        f"생존 {time_string()}  |  Lv.{level}  |  Kills {kills}", True, (255, 230, 120)
    )
    screen.blit(stats, stats.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30)))

    if cur_stage == 0 and new_record and (frame_tick // 20) % 2 == 0:
        nr = small_font.render("NEW RECORD!", True, (255, 120, 140))
        screen.blit(nr, nr.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 15)))
    elif cur_stage == 0 and not new_record:
        bt = f"{best_time // 60:02d}:{best_time % 60:02d}"
        rec = small_font.render(f"최고 기록  {bt}", True, (180, 190, 220))
        screen.blit(rec, rec.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 15)))
    elif cur_stage > 0:
        extra = f"  |  최고 콤보 {best_combo}"
        rec = small_font.render(("스테이지 클리어!" if stage_cleared else "스테이지 실패") + extra, True,
                                (140, 255, 170) if stage_cleared else (180, 190, 220))
        screen.blit(rec, rec.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 15)))

    detail = f"처치 {run_gold} + 생존 {last_bonus}"
    if last_clear:
        detail += f" + 클리어 {last_clear}"
    gain = small_font.render(f"+{last_gain} G   ({detail})", True, (255, 215, 90))
    screen.blit(gain, gain.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 52)))
    if stage_cleared and cur_stage in (1, 2, 3, 4, 5, 6, 8):
        tail = "N 키: 다음 스토리 스테이지     R 키: 다시     ESC: 타이틀"
    else:
        tail = "R 키: 다시 시작     ESC: 타이틀 (강화 / 상점)"
    retry = small_font.render(tail, True, (180, 190, 220))
    screen.blit(retry, retry.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 102)))


# ------------------------------------------------------------
# 장비 / 룬 / 펫 / 상점 탭 / 스테이지 선택(2페이지)
# ------------------------------------------------------------
GOLD_VALUE.update({"yeti": 4, "imp": 3, "skeleton": 3, "ghost": 3, "scorpion": 3, "mummy": 4,
                   "toad": 3, "shroom": 3, "frost_wolf": 3, "ash_hound": 3, "ice_jelly": 3,
                   "magma_slime": 3, "ice_mage": 4, "fire_mage": 4, "ice_wisp": 3,
                   "raider": 3, "sand_boar": 4})
SLOTS = ["weapon", "armor", "acc", "rune", "pet"]
SLOT_NAMES = {"weapon": "무기", "armor": "방어구", "acc": "장신구", "rune": "룬", "pet": "펫"}
TAB_RECTS = [pygame.Rect(340 + i * 88, 200, 84, 30) for i in range(5)]
shop_tab = 0


def is_equipped(wid):
    return wid == equipped_weapon or wid in equipped_gear.values()


def gear_stats():
    """무기 + 방어구 + 장신구 + 룬 + 펫의 능력치를 전부 더해요."""
    out = weapon_stats(equipped_weapon)
    for gid in equipped_gear.values():
        if gid:
            s = weapon_stats(gid)
            for k in SCALED_KEYS + ("hp",):
                out[k] += s[k]
            out["start"] = out["start"] + s["start"]
    return out


def set_tab(slot, wid=None):
    """상점 분류를 바꿔요. WEAPON_ORDER를 그 분류의 목록으로 갈아 끼워서 기존 상점 코드가 그대로 동작해요."""
    global shop_tab, shop_sel
    shop_tab = SLOTS.index(slot)
    WEAPON_ORDER[:] = [k for k in ALL_ORDER if WEAPONS[k]["slot"] == slot]
    shop_sel = WEAPON_ORDER.index(wid) if wid else 0


def shop_cell_rects():
    return [pygame.Rect(340 + (i % 4) * 110, 238 + (i // 4) * 98, 100, 94) for i in range(len(WEAPON_ORDER))]


def equip_selected():
    global equipped_weapon
    wid = WEAPON_ORDER[shop_sel]
    if wid not in weapon_stars:
        show_toast("아직 얻지 못한 장비예요", (255, 130, 130))
        snd_fail.play()
        return
    if is_equipped(wid):
        return
    sl = WEAPONS[wid]["slot"]
    if sl == "weapon":
        equipped_weapon = wid
    elif sl == "rune":  # 룬은 2칸: 빈 칸에 먼저 끼우고, 다 차면 오래된 쪽부터 교체
        if not equipped_gear["rune"]:
            equipped_gear["rune"] = wid
        elif not equipped_gear["rune2"]:
            equipped_gear["rune2"] = wid
        else:
            equipped_gear["rune"], equipped_gear["rune2"] = equipped_gear["rune2"], wid
    else:
        equipped_gear[sl] = wid
    save_game()
    snd_buy.play()
    show_toast(f"{WEAPONS[wid]['name']} 장착!", (140, 255, 170))


_draw_weapon_cell = draw_weapon_cell


def draw_weapon_cell(rect, wid, selected):
    w = WEAPONS[wid]
    rc = RARITY[w["rarity"]]["color"]
    owned = wid in weapon_stars
    if selected:
        pixel_panel(screen, rect.inflate(8, 8), (255, 255, 255), (255, 255, 255), n=6, bw=3)
    pixel_panel(screen, rect, rc if owned else (60, 64, 90),
                tuple(c // 6 + 16 for c in rc) if owned else (22, 24, 40), n=5, bw=3)
    img = weapon_img(wid, 2, dark=not owned)
    if owned:
        add_glow(screen, rarity_glows[w["rarity"]], (rect.centerx, rect.y + 30), 0.45)
    screen.blit(img, img.get_rect(center=(rect.centerx, rect.y + 31)))
    if owned:
        stars = weapon_stars[wid]
        for k in range(MAX_STAR):
            draw_star(screen, (rect.centerx - 20 + k * 10, rect.bottom - 11), 4, rc, empty=k >= stars)
        if wid == equipped_weapon:
            tag = pygame.Rect(rect.x + 7, rect.y + 7, 18, 18)
            pygame.draw.rect(screen, (60, 190, 110), tag)
            pygame.draw.rect(screen, (14, 12, 30), tag, 2)
            blit_text(screen, tiny_font, "E", (255, 255, 255), tag.center, True)
    else:
        blit_text(screen, tiny_font, "???", (110, 116, 150), (rect.centerx, rect.bottom - 12), True)
    _draw_weapon_cell(rect, wid, selected)
    if wid != equipped_weapon and is_equipped(wid):  # 방어구/장신구/룬/펫에도 E 표시
        tag = pygame.Rect(rect.x + 7, rect.y + 7, 18, 18)
        pygame.draw.rect(screen, (60, 190, 110), tag)
        pygame.draw.rect(screen, (14, 12, 30), tag, 2)
        blit_text(screen, tiny_font, "E", (255, 255, 255), tag.center, True)


_draw_shop_screen = draw_shop_screen


def draw_shop_screen():
    _draw_shop_screen()
    if not shop_results:
        for i, r in enumerate(TAB_RECTS):
            draw_button(screen, r, "", i == shop_tab, True, (200, 140, 255) if i == shop_tab else (110, 120, 170))
            blit_text(screen, tiny_font, SLOT_NAMES[SLOTS[i]], (255, 255, 255), r.center, True)
        blit_text(screen, tiny_font, "TAB: 무기 / 방어구 / 장신구 / 룬 / 펫 분류 바꾸기", (150, 160, 190),
                  (WIDTH // 2, 566), True)


def stage_event(event):
    """스테이지 선택 (7칸, 4칸씩 2페이지): 방향키 / 마우스 / Enter / 1~4"""
    global state, stage_sel
    n = len(STAGE_ORDER)
    off = (stage_sel // 4) * 4
    if event.type == pygame.MOUSEMOTION:
        for i, r in enumerate(stage_card_rects()):
            if off + i < n and r.collidepoint(event.pos):
                stage_sel = off + i
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if BACK_RECT.collidepoint(event.pos):
            state = "title"
            snd_click.play()
            return
        for i, r in enumerate(stage_card_rects()):
            if off + i < n and r.collidepoint(event.pos):
                stage_sel = off + i
                start_stage(STAGE_ORDER[stage_sel])
                break
    elif event.type == pygame.KEYDOWN:
        k = event.key
        if k in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            state = "title"
            snd_click.play()
        elif k in (pygame.K_UP, pygame.K_w):
            stage_sel = max(0, stage_sel - 2)
        elif k in (pygame.K_DOWN, pygame.K_s):
            stage_sel = min(n - 1, stage_sel + 2)
        elif k in (pygame.K_LEFT, pygame.K_a):
            stage_sel = max(0, stage_sel - 1)
        elif k in (pygame.K_RIGHT, pygame.K_d):
            stage_sel = min(n - 1, stage_sel + 1)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            start_stage(STAGE_ORDER[stage_sel])
        elif k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            if off + k - pygame.K_1 < n:
                stage_sel = off + k - pygame.K_1
                start_stage(STAGE_ORDER[stage_sel])
# ============================================================
# [패치 2] 캐릭터 창 / 세트 효과 / 근접·원거리 공격 / 던전 첫 화면
# 붙여넣는 곳: set_tab("weapon") 줄 바로 아래, "# 9) 시작" 바로 위 (딱 한 곳!)
# 메인 루프는 건드리지 않아요.
# ============================================================

# ------------------------------------------------------------
# 1) 세트 효과 + 새 장비 20종 (4세트 x 5부위)
# ------------------------------------------------------------
_STAT_TXT = [("atk", "공격력 +{:g}%", 100), ("spd", "공격 속도 +{:g}%", 100), ("crit", "치명타 +{:g}%", 1),
             ("move", "이동 +{:g}", 1), ("pick", "줍기 +{:g}", 1), ("xp", "경험치 +{:g}%", 100),
             ("gold", "골드 +{:g}%", 100), ("hp", "체력 +{:g}", 1), ("inv", "무적 +{:.2f}초", 1 / 60),
             ("dash", "대시 -{:.2f}초", 1 / 60)]


def bonus_desc(b):
    """세트 보너스 숫자를 글자로 바꿔요 (숫자만 고치면 설명도 같이 바뀌어요)."""
    parts = []
    for k, fmt, mul in _STAT_TXT:
        if b.get(k):
            parts.append(fmt.format(round(b[k] * mul, 2)))
    sk = b.get("skills")
    if sk:
        names = [s + (f" Lv.{sk.count(s)}" if sk.count(s) > 1 else "") for s in dict.fromkeys(sk)]
        parts.append("시작 스킬 " + ", ".join(names))
    return ", ".join(parts)


# 세트 보너스: 2개 / 4개 / 5개(완성) 장착하면 차례로 쌓여요
# atk 공격력 / spd 공격속도 / crit 치명타 / move 이동 / pick 줍기 / xp 경험치 / gold 골드 / hp 체력 / inv 무적 프레임 / skills 시작 스킬
SETS = {
    "forest": {"name": "숲의 수호", "color": (120, 230, 130), "bonus": {
        2: {"hp": 1, "pick": 20},
        4: {"skills": ["재생"], "move": 0.3},
        5: {"hp": 1, "xp": 0.08}}},
    "flame": {"name": "화염 군주", "color": (255, 120, 60), "bonus": {
        2: {"atk": 0.10},
        4: {"skills": ["불꽃검"], "crit": 6},
        5: {"atk": 0.08, "spd": 0.05}}},
    "frost": {"name": "서리 여왕", "color": (120, 210, 255), "bonus": {
        2: {"spd": 0.08, "move": 0.15},
        4: {"skills": ["냉기", "냉기"], "xp": 0.06},
        5: {"hp": 1, "inv": 10}}},
    "storm": {"name": "폭풍의 군주", "color": (255, 235, 90), "bonus": {
        2: {"crit": 6, "move": 0.2},
        4: {"skills": ["번개", "번개"], "atk": 0.08},
        5: {"atk": 0.08, "spd": 0.06, "gold": 0.10}}},
}
for _sd in SETS.values():
    for _b in _sd["bonus"].values():
        _b["desc"] = bonus_desc(_b)

# 세트 장비는 같은 등급의 일반 장비보다 능력치가 조금 낮아요 (대신 세트 효과가 있어요)
_items("weapon", [
    ("f_bow", "숲의 활", "rare", "bow", ((110, 200, 100), (215, 255, 205), (120, 85, 45)),
     {"spd": 0.08, "pick": 10, "set": "forest"}),
    ("fl_sword", "군주의 화염검", "epic", "sword", ((255, 100, 45), (255, 225, 130), (110, 45, 30)),
     {"atk": 0.09, "crit": 3, "set": "flame"}),
    ("fr_staff", "서리 여왕의 홀", "epic", "staff", ((120, 210, 255), (235, 255, 255), (160, 200, 235)),
     {"spd": 0.06, "xp": 0.05, "set": "frost"}),
    ("st_spear", "폭풍의 창", "legend", "spear", ((255, 230, 90), (255, 255, 215), (70, 70, 120)),
     {"atk": 0.11, "crit": 4, "set": "storm"}),
])
_items("armor", [
    ("f_armor", "숲의 갑옷", "rare", "armor", ((90, 160, 80), (200, 240, 170), (90, 60, 35)),
     {"hp": 1, "move": 0.1, "set": "forest"}),
    ("fl_armor", "군주의 갑주", "epic", "armor", ((200, 60, 40), (255, 170, 110), (90, 30, 25)),
     {"hp": 1, "atk": 0.04, "inv": 8, "set": "flame"}),
    ("fr_armor", "서리 갑옷", "epic", "armor", ((130, 200, 240), (230, 250, 255), (60, 100, 150)),
     {"hp": 1, "inv": 10, "set": "frost"}),
    ("st_robe", "뇌운의 로브", "legend", "robe", ((120, 130, 200), (210, 220, 255), (255, 230, 90)),
     {"hp": 1, "xp": 0.06, "inv": 10, "set": "storm"}),
])
_items("acc", [
    ("f_ring", "숲의 반지", "rare", "ring", ((110, 210, 120), (215, 255, 215), (120, 85, 45)),
     {"xp": 0.06, "pick": 10, "set": "forest"}),
    ("fl_ring", "군주의 인장", "epic", "ring", ((255, 110, 50), (255, 210, 150), (235, 195, 80)),
     {"atk": 0.05, "crit": 3, "set": "flame"}),
    ("fr_amulet", "빙정 목걸이", "epic", "amulet", ((140, 215, 255), (235, 255, 255), (90, 130, 180)),
     {"xp": 0.06, "pick": 14, "set": "frost"}),
    ("st_crown", "폭풍의 왕관", "legend", "crown", ((255, 225, 90), (255, 250, 200), (100, 110, 220)),
     {"atk": 0.05, "gold": 0.10, "crit": 4, "set": "storm"}),
])
_items("rune", [
    ("f_rune", "숲의 룬", "rare", "rune", ((120, 235, 130), (215, 255, 220), (25, 60, 30)),
     {"move": 0.15, "gold": 0.08, "set": "forest"}),
    ("fl_rune", "화염의 룬", "epic", "rune", ((255, 120, 50), (255, 215, 170), (70, 25, 15)),
     {"atk": 0.06, "spd": 0.04, "set": "flame"}),
    ("fr_rune", "서리의 룬", "epic", "rune", ((130, 215, 255), (235, 255, 255), (20, 50, 90)),
     {"spd": 0.05, "move": 0.15, "set": "frost"}),
    ("st_rune", "폭풍의 룬", "legend", "rune", ((255, 235, 100), (255, 255, 220), (40, 40, 90)),
     {"atk": 0.08, "spd": 0.06, "set": "storm"}),
])
_items("pet", [
    ("f_pet", "숲의 정령", "rare", "petw", ((130, 230, 150), (235, 255, 240), (30, 80, 50)),
     {"pet": True, "pcd": 105, "pshots": 1, "pdmg": 1, "pheal": 1800, "set": "forest"}),
    ("fl_pet", "불꽃 도마뱀", "epic", "pet", ((255, 125, 55), (255, 215, 140), (70, 25, 15)),
     {"pet": True, "pcd": 80, "pshots": 2, "pdmg": 2, "set": "flame"}),
    ("fr_pet", "눈의 정령", "epic", "petw", ((190, 230, 255), (245, 252, 255), (60, 110, 170)),
     {"pet": True, "pcd": 90, "pshots": 2, "pdmg": 1, "pheal": 2700, "set": "frost"}),
    ("st_pet", "천둥새", "legend", "petw", ((255, 235, 110), (255, 255, 225), (70, 80, 160)),
     {"pet": True, "pcd": 58, "pshots": 3, "pdmg": 2, "pheal": 2100, "set": "storm"}),
])
ALL_ORDER[:] = list(WEAPONS.keys())
for _r in RARITY_ORDER:
    WEAPONS_BY_RARITY[_r] = [k for k, v in WEAPONS.items() if v["rarity"] == _r]
SET_SIZE = {k: sum(1 for w in WEAPONS.values() if w.get("set") == k) for k in SETS}


def equipped_ids():
    return [i for i in [equipped_weapon] + list(equipped_gear.values()) if i]


def set_counts():
    """지금 끼고 있는 세트별 장비 개수."""
    cnt = {}
    for i in equipped_ids():
        s = WEAPONS.get(i, {}).get("set")
        if s:
            cnt[s] = cnt.get(s, 0) + 1
    return cnt


def set_bonus_total():
    out = {k: 0 for k in SCALED_KEYS}
    out["hp"] = 0
    out["start"] = []
    for sk, n in set_counts().items():
        for thr, b in sorted(SETS[sk]["bonus"].items()):
            if n >= thr:
                for k in SCALED_KEYS + ("hp",):
                    out[k] += b.get(k, 0)
                out["start"] = out["start"] + list(b.get("skills", []))
    return out


_gear_stats_p2 = gear_stats


def gear_stats():
    """장비 능력치 + 세트 효과를 합쳐요 (판이 시작될 때 reset_game이 불러요)."""
    out = _gear_stats_p2()
    sb = set_bonus_total()
    for k in SCALED_KEYS + ("hp",):
        out[k] += sb[k]
    out["start"] = out["start"] + sb["start"]
    return out


# ------------------------------------------------------------
# 2) 근접 / 원거리: 무기 모양이 공격 방식을 정해요
#    검·단검·도끼·창 = 자동 근접 베기 / 활·지팡이 = 원거리 투사체
# ------------------------------------------------------------
# reach 사거리 / half 한쪽 각도 / cd 공격 간격 배율 / mult 피해 배율 (근접은 위험한 대신 범위 + 조금 더 강해요)
MELEE = {
    "sword": {"reach": 92, "half": 55, "cd": 1.00, "mult": 1.30, "col": (215, 235, 255), "tag": "균형형 베기"},
    "dagger": {"reach": 68, "half": 48, "cd": 0.60, "mult": 0.80, "col": (205, 255, 235), "tag": "빠른 연타"},
    "axe": {"reach": 86, "half": 85, "cd": 1.50, "mult": 2.00, "col": (255, 215, 170), "tag": "넓고 묵직한 휘두르기"},
    "spear": {"reach": 132, "half": 22, "cd": 1.15, "mult": 1.55, "col": (255, 245, 170), "tag": "긴 사거리 찌르기"},
    "flame": {"reach": 100, "half": 60, "cd": 1.00, "mult": 1.50, "col": (255, 150, 60), "tag": "불꽃 베기 (화상)",
              "burn": True},
}
# dmg 피해 배율 / pierce 추가 관통 / speed 탄속 배율 / home 유도
RANGED = {
    "bow": {"dmg": 1.00, "pierce": 1, "speed": 1.35, "home": False, "tag": "관통 화살"},
    "staff": {"dmg": 1.15, "pierce": 0, "speed": 1.00, "home": True, "tag": "유도 마법탄"},
}
RANGED_DEFAULT = {"dmg": 1.0, "pierce": 0, "speed": 1.0, "home": False, "tag": "기본 사격"}


def weapon_style(wid):
    """('melee' | 'ranged', 능력치 표)"""
    w = WEAPONS.get(wid)
    shape = w["shape"] if w else ""
    if shape in MELEE:
        return "melee", MELEE[shape]
    if shape in RANGED:
        return "ranged", RANGED[shape]
    return "ranged", RANGED_DEFAULT


atk_mode = "ranged"
atk_params = RANGED_DEFAULT
melee_timer = 0
slashes = []  # 근접 베기 효과
snd_slash = SoundVariants(make_slash_sound(101), make_slash_sound(202), make_slash_sound(303))
_UP_TXT = {"멀티샷": upgrades["멀티샷"], "관통": upgrades["관통"]}
_slash_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)


def melee_reach(plus=0):
    return atk_params["reach"] + min(50, 10 * (pierce_level + plus))  # 관통 카드 = 사거리 증가


def melee_half(plus=0):
    return min(110, atk_params["half"] + min(40, 7 * (extra_shots + plus)))  # 멀티샷 카드 = 각도 증가


def melee_step():
    """근접: 사거리 안에 적이 있으면 가까운 적 쪽으로 부채꼴 베기. 적 탄환도 베어서 없애요."""
    global melee_timer, weapon_swing
    melee_timer += 1
    p = atk_params
    if melee_timer < max(6, int(fire_interval * p["cd"])):
        return
    reach, half = melee_reach(), melee_half()
    best, bd = None, 1e9
    for e in enemies:
        if e["hp"] <= 0:
            continue
        d = e["pos"].distance_to(player_pos)
        if d <= reach + enemy_types[e["kind"]]["radius"] and d < bd:
            best, bd = e, d
    if best is None:
        return
    melee_timer = 0
    aim = angle_of(best["pos"] - player_pos)
    dmg = projectile_damage * p["mult"]
    hit = 0
    for e in list(enemies):
        if e["hp"] <= 0:
            continue
        off = e["pos"] - player_pos
        d = off.length()
        r = enemy_types[e["kind"]]["radius"]
        if d > reach + r:
            continue
        if d > 34 + r and abs(angle_diff(angle_of(off), aim)) > half:
            continue
        damage_enemy(e, dmg * (1.2 if e.get("boss") else 1.0), quiet=hit > 0)  # 보스에겐 +20% (가까이 붙는 보상)
        hit += 1
        if frost_level:
            e["slow"] = 120
        if not e.get("boss"):
            if d > 0:
                e["pos"] += off / d * 10  # 살짝 밀려나요
            if p.get("burn"):
                e["burn"] = 180
                e["burn_dmg"] = 1 + projectile_damage // 4
    for s in enemy_shots:  # 베기로 적 탄환 막기
        off = s["pos"] - player_pos
        d = off.length()
        if d <= reach and (d < 40 or abs(angle_diff(angle_of(off), aim)) <= half):
            s["life"] = 0
            spawn_burst(s["pos"], (190, 120, 255), 4)
    if blast_level and hit:
        explode(player_pos + pygame.Vector2(reach * 0.7, 0).rotate(aim))
    slashes.append({"ang": aim, "half": half, "reach": reach, "life": 10, "max": 10, "col": p["col"]})
    weapon_swing = 10
    snd_slash.play()
    if hit >= 3:
        add_shake(2)


def ranged_tune():
    """원거리: 자동 발사된 투사체에 활(관통+빠름) / 지팡이(유도) 특성을 입혀요."""
    p = atk_params
    for pr in projectiles:
        if "dmg" not in pr:  # 방금 발사된 내 투사체 (펫/별빛은 이미 dmg가 있어요)
            pr["dmg"] = projectile_damage * p["dmg"]
            pr["pierce"] += p["pierce"]
            if p["speed"] != 1.0:
                pr["vel"] = pr["vel"] * p["speed"]
            pr["home"] = p["home"]
        if pr.get("home"):
            best, bd = None, 280
            for e in enemies:
                if e["hp"] > 0 and id(e) not in pr["hit"]:
                    d = e["pos"].distance_to(pr["pos"])
                    if d < bd:
                        best, bd = e, d
            if best is not None:
                spd = pr["vel"].length()
                if spd > 0:
                    cur = angle_of(pr["vel"])
                    diff = angle_diff(angle_of(best["pos"] - pr["pos"]), cur)
                    pr["vel"] = pygame.Vector2(spd, 0).rotate(cur + max(-8, min(8, diff)))


def p2_frame():
    """매 프레임 끝에서 한 번 불려요 (아래 _P2Clock이 clock.tick 앞에서 호출)."""
    global fire_timer
    if state != "playing" or game_over:
        return
    if atk_mode == "melee":
        fire_timer = 0  # 기본 투사체 자동 발사를 막아요 (근접은 베기로 공격)
        melee_step()
    else:
        ranged_tune()
    for s in slashes:
        s["life"] -= 1
    slashes[:] = [s for s in slashes if s["life"] > 0]


class _P2Clock:
    def __init__(self, c):
        self._c = c

    def tick(self, *a, **k):
        p2_frame()
        return self._c.tick(*a, **k)

    def __getattr__(self, name):
        return getattr(self._c, name)


clock = _P2Clock(clock)

_reset_game_p2 = reset_game


def reset_game():
    global atk_mode, atk_params, melee_timer
    _reset_game_p2()
    atk_mode, atk_params = weapon_style(equipped_weapon)
    melee_timer = 0
    slashes.clear()
    if atk_mode == "melee":  # 근접이면 카드 설명도 바꿔요
        upgrades["멀티샷"] = "베는 각도가\n넓어져요"
        upgrades["관통"] = "베는 거리가\n길어져요"
    else:
        upgrades["멀티샷"] = _UP_TXT["멀티샷"]
        upgrades["관통"] = _UP_TXT["관통"]


_preview_text_p2 = preview_text


def preview_text(name):
    if name in RUN_RELICS:
        return RUN_RELICS[name]["preview"]
    if name in SKILL_EVOLUTIONS:
        return SKILL_EVOLUTIONS[name]["preview"]
    if atk_mode == "melee":
        if name == "멀티샷":
            return f"베기 각도 {melee_half() * 2} -> {melee_half(1) * 2}도"
        if name == "관통":
            return f"사거리 {melee_reach()} -> {melee_reach(1)}"
    return _preview_text_p2(name)


_is_maxed_p2 = is_maxed


def is_maxed(name):
    if atk_mode == "melee" and name == "관통" and skill_levels.get(name, 0) >= 5:
        return True  # 근접 사거리 보너스는 5단계까지
    return _is_maxed_p2(name)


def available_upgrades():
    """Owned skills can rank up; new skills need an open category slot."""
    attack_used = sum(1 for n in ATTACK_SKILLS if skill_levels.get(n, 0) > 0)
    support_used = sum(1 for n in SUPPORT_SKILLS if skill_levels.get(n, 0) > 0)
    result = []
    for n in upgrade_names:
        if is_maxed(n):
            continue
        if skill_levels.get(n, 0) > 0:
            result.append(n)
        elif n in ATTACK_SKILLS and attack_used < ATTACK_SKILL_SLOTS:
            result.append(n)
        elif n in SUPPORT_SKILLS and support_used < SUPPORT_SKILL_SLOTS:
            result.append(n)
    for name, data in SKILL_EVOLUTIONS.items():
        if name not in skill_evolutions and all(
                skill_levels.get(skill, 0) >= data["min_level"] for skill in data["skills"]):
            result.append(name)
    return result


def choose_upgrade_cards(available, count=3):
    """Keep an earned evolution visible while filling remaining cards normally."""
    pool = list(available)
    selected = []
    evolutions = [name for name in pool if name in SKILL_EVOLUTIONS]
    if evolutions and count > 0:
        selected.append(random.choice(evolutions))
        pool.remove(selected[0])
    selected.extend(random.sample(pool, min(max(0, count - len(selected)), len(pool))))
    random.shuffle(selected)
    return selected


def can_offer_run_relic():
    return (run_relic_offer_count < MAX_RUN_RELICS and len(run_relics) < MAX_RUN_RELICS
            and any(name not in run_relics for name in RUN_RELICS))


def choose_boss_chest_cards(available, count=3):
    """Boss chests can offer one run relic alongside regular upgrades."""
    global run_relic_offer_count
    if not can_offer_run_relic():
        return choose_upgrade_cards(available, count)
    relic_pool = [name for name in RUN_RELICS if name not in run_relics]
    if not relic_pool or count <= 0:
        return choose_upgrade_cards(available, count)
    selected = [random.choice(relic_pool)]
    run_relic_offer_count += 1
    pool = list(available)
    evolutions = [name for name in pool if name in SKILL_EVOLUTIONS]
    if evolutions and len(selected) < count:
        evolution = random.choice(evolutions)
        selected.append(evolution)
        pool.remove(evolution)
    selected.extend(random.sample(pool, min(max(0, count - len(selected)), len(pool))))
    random.shuffle(selected)
    return selected


def open_pending_relic_offer():
    global pending_relic_offers, relic_choices, state
    if state != "playing" or pending_relic_offers <= 0 or len(run_relics) >= MAX_RUN_RELICS:
        return False
    pool = [name for name in RUN_RELICS if name not in run_relics]
    if not pool:
        pending_relic_offers = 0
        return False
    pending_relic_offers -= 1
    relic_choices = random.sample(pool, min(3, len(pool)))
    state = "relic_choice"
    return True


def choose_run_relic(name):
    global relic_choices, state
    if state != "relic_choice" or name not in relic_choices:
        return False
    apply_upgrade(name)
    relic_choices = []
    state = "playing"
    return True


def reroll_choices():
    """현재 레벨업 선택지를 이번 판 리롤 횟수 하나를 써서 다시 뽑아요."""
    global choices, rerolls_left
    if rerolls_left <= 0:
        return False
    available = available_upgrades()
    alternatives = [name for name in available if name not in choices]
    if not alternatives:
        return False
    wanted = min(3, len(available))
    # A reroll should refresh the regular cards without hiding a ready evolution.
    evolutions = [name for name in available if name in SKILL_EVOLUTIONS]
    replacement = [random.choice(evolutions)] if evolutions else []
    pool = [name for name in alternatives if name not in replacement]
    replacement.extend(random.sample(pool, min(wanted - len(replacement), len(pool))))
    keepers = [name for name in available if name in choices and name not in replacement]
    if len(replacement) < wanted and keepers:
        replacement.extend(random.sample(keepers, min(wanted - len(replacement), len(keepers))))
    if not replacement:
        return False
    random.shuffle(replacement)
    choices = replacement
    rerolls_left -= 1
    snd_click.play()
    return True


def draw_slashes():
    if not slashes:
        return
    _slash_layer.fill((0, 0, 0, 0))
    for s in slashes:
        k = 1 - s["life"] / s["max"]
        fade = max(0.0, 1 - k)
        a0 = s["ang"] - s["half"]
        a1 = a0 + 2 * s["half"] * min(1.0, k * 2.4 + 0.25)
        steps = max(4, int((a1 - a0) / 8))
        outer = [player_pos + pygame.Vector2(s["reach"], 0).rotate(a0 + (a1 - a0) * i / steps) for i in range(steps + 1)]
        inner = [player_pos + pygame.Vector2(s["reach"] * 0.5, 0).rotate(a0 + (a1 - a0) * i / steps)
                 for i in reversed(range(steps + 1))]
        pygame.draw.polygon(_slash_layer, (*s["col"], int(140 * fade)), outer + inner)
        pygame.draw.lines(_slash_layer, (255, 255, 255, int(235 * fade)), False, outer, 3)
    world.blit(_slash_layer, (0, 0))


_draw_world_p2 = draw_world


def draw_world():
    _draw_world_p2()
    draw_slashes()


# 상점 정보창에 근접/원거리, 세트 이름을 작게 표시해요
_draw_shop_screen_p2 = draw_shop_screen


def draw_shop_screen():
    _draw_shop_screen_p2()
    if shop_results or not WEAPON_ORDER:
        return
    wid = WEAPON_ORDER[min(shop_sel, len(WEAPON_ORDER) - 1)]
    w = WEAPONS[wid]
    if w["slot"] == "weapon":
        mode, _par = weapon_style(wid)
        blit_text(screen, tiny_font, "근접" if mode == "melee" else "원거리", (255, 200, 120), (34, 84))
    sk = w.get("set")
    if sk:
        t = tiny_font.render(SETS[sk]["name"], True, SETS[sk]["color"])
        screen.blit(t, t.get_rect(topright=(306, 84)))


# ------------------------------------------------------------
# 3) 캐릭터 창 (타이틀의 "캐릭터" 버튼 또는 C 키)
#    기존 "업적" 화면 상태를 빌려 쓰는 방식이라 메인 루프를 고칠 필요가 없어요.
# ------------------------------------------------------------
CHAR_SLOTS = [("weapon", "무기"), ("armor", "방어구"), ("acc", "장신구"), ("rune", "룬 1"), ("rune2", "룬 2"), ("pet", "펫")]
CHAR_SLOT_POS = {"weapon": (60, 122), "armor": (60, 206), "acc": (60, 290),
                 "rune": (276, 122), "rune2": (276, 206), "pet": (276, 290)}
CHAR_CL = pygame.Rect(30, 334, 30, 28)
CHAR_CR = pygame.Rect(276, 334, 30, 28)
WHEEL_EVT = getattr(pygame, "MOUSEWHEEL", -1)
char_open = False
char_slot = 0
char_sel = 0
char_scroll = 0


def char_slot_rect(key):
    cx, cy = CHAR_SLOT_POS[key]
    return pygame.Rect(cx - 32, cy - 32, 64, 64)


def char_cell_rects():
    return [pygame.Rect(340 + c * 88, 94 + r * 48, 84, 44) for r in range(3) for c in range(5)]


def char_items(key):
    """고른 부위에서 가진 장비 목록 (높은 등급 먼저). 무기 말고는 맨 앞에 '해제' 칸이 있어요."""
    st = key.rstrip("2")
    ids = [k for k in ALL_ORDER if WEAPONS[k]["slot"] == st and k in weapon_stars]
    ids.sort(key=lambda k: (-RARITY_ORDER.index(WEAPONS[k]["rarity"]), WEAPONS[k]["name"]))
    return ids if key == "weapon" else [""] + ids


def char_current(key):
    return equipped_weapon if key == "weapon" else equipped_gear[key]


def _char_clamp(n):
    global char_sel, char_scroll
    char_sel = max(0, min(char_sel, max(0, n - 1)))
    row = char_sel // 5
    if row < char_scroll:
        char_scroll = row
    if row > char_scroll + 2:
        char_scroll = row - 2
    char_scroll = max(0, min(char_scroll, max(0, (n - 1) // 5 - 2)))


def _char_goto_equipped():
    global char_sel, char_scroll
    items = char_items(CHAR_SLOTS[char_slot][0])
    cur = char_current(CHAR_SLOTS[char_slot][0])
    char_sel = items.index(cur) if cur in items else 0
    char_scroll = max(0, char_sel // 5 - 1)
    _char_clamp(len(items))


def open_character():
    global state, char_open, char_slot
    state = "achv"
    char_open = True
    char_slot = 0
    _char_goto_equipped()


def close_character():
    global state, char_open
    char_open = False
    state = "title"
    snd_click.play()


def char_equip(key, wid):
    global equipped_weapon
    if key == "weapon":
        equipped_weapon = wid
    elif key in ("rune", "rune2"):
        other = "rune2" if key == "rune" else "rune"
        if equipped_gear[other] == wid:  # 같은 룬이 다른 칸에 있으면 서로 바꿔요
            equipped_gear[other] = equipped_gear[key]
        equipped_gear[key] = wid
    else:
        equipped_gear[key] = wid
    save_game()


def char_apply(idx):
    """고른 칸의 장비를 장착해요. 장착하면 세트 효과가 새로 켜졌는지 알려줘요."""
    key = CHAR_SLOTS[char_slot][0]
    items = char_items(key)
    if not (0 <= idx < len(items)):
        return
    wid = items[idx]
    if wid == "":
        if equipped_gear.get(key):
            equipped_gear[key] = ""
            save_game()
            snd_click.play()
            show_toast("장비를 해제했어요", (180, 190, 220))
        return
    if char_current(key) == wid:
        show_toast("이미 장착 중이에요", (180, 190, 220))
        return
    old = set_counts()
    char_equip(key, wid)
    snd_buy.play()
    show_toast(f"{WEAPONS[wid]['name']} 장착!", (140, 255, 170))
    for sk, n in set_counts().items():
        if n > old.get(sk, 0) and n in SETS[sk]["bonus"]:
            show_toast(f"{SETS[sk]['name']} {n}세트 효과 발동!", SETS[sk]["color"])
            snd_level.play()


def char_event(event):
    global char_slot, char_sel, char_scroll
    key = CHAR_SLOTS[char_slot][0]
    items = char_items(key)
    n = len(items)
    cells = char_cell_rects()
    if event.type == pygame.MOUSEMOTION:
        for i, r in enumerate(cells):
            gi = char_scroll * 5 + i
            if gi < n and r.collidepoint(event.pos):
                char_sel = gi
    elif event.type == WHEEL_EVT:
        char_scroll = max(0, min(max(0, (n - 1) // 5 - 2), char_scroll - event.y))
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        p = event.pos
        if BACK_RECT.collidepoint(p):
            close_character()
        elif CHAR_CL.collidepoint(p):
            set_class(cur_class - 1)
        elif CHAR_CR.collidepoint(p):
            set_class(cur_class + 1)
        else:
            for i, (k, _lbl) in enumerate(CHAR_SLOTS):
                if char_slot_rect(k).collidepoint(p):
                    char_slot = i
                    snd_click.play()
                    _char_goto_equipped()
                    return
            for i, r in enumerate(cells):
                gi = char_scroll * 5 + i
                if gi < n and r.collidepoint(p):
                    char_sel = gi
                    char_apply(gi)
                    return
    elif event.type == pygame.KEYDOWN:
        k = event.key
        if k in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            close_character()
        elif k in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s, pygame.K_TAB):
            step = -1 if k in (pygame.K_UP, pygame.K_w) else 1
            char_slot = (char_slot + step) % len(CHAR_SLOTS)
            snd_click.play()
            _char_goto_equipped()
        elif k in (pygame.K_LEFT, pygame.K_a):
            char_sel = max(0, char_sel - 1)
        elif k in (pygame.K_RIGHT, pygame.K_d):
            char_sel = min(n - 1, char_sel + 1)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            char_apply(char_sel)
        elif k in (pygame.K_x, pygame.K_DELETE):
            char_apply(0) if key != "weapon" else None
        elif k == pygame.K_q:
            set_class(cur_class - 1)
        elif k == pygame.K_e:
            set_class(cur_class + 1)


def fit_text(fnt, text, maxw):
    """글씨가 칸보다 길면 뒤를 잘라요."""
    while len(text) > 1 and fnt.render(text, True, (255, 255, 255)).get_width() > maxw:
        text = text[:-1]
    return text


def char_preview():
    """영구 강화 + 장비 + 세트 + 직업을 모두 합친 시작 능력치 (reset_game과 같은 계산)."""
    ws, m, c = gear_stats(), meta_levels, CLASSES[cur_class]
    mode, par = weapon_style(equipped_weapon)
    base = max(10, round(30 * (1 - ws["spd"])))
    base = max(10, round(base * c["fire"]))
    interval = max(6, int(base * par["cd"])) if mode == "melee" else base
    n_skill = len(ws["start"]) + len(c["start"])
    col = (200, 225, 255)
    return [
        ("근접 공격" if mode == "melee" else "원거리 공격", (255, 200, 120)),
        (f"체력 {max(1, 3 + m['hp'] + ws['hp'] + c['hp'])}", col),
        (f"공격력 +{round((0.08 * m['atk'] + ws['atk'] + c['atk']) * 100)}%", col),
        (f"공격 간격 {interval / 60:.2f}초", col),
        (f"치명타 +{round(2 * m['crit'] + ws['crit'] + c['crit'])}%", col),
        (f"이동 속도 {4 + 0.15 * m['spd'] + ws['move'] + c['move']:.2f}", col),
        (f"줍기 범위 {round(30 + 6 * m['pick'] + ws['pick'])}", col),
        (f"경험치 +{round((0.06 * m['xp'] + ws['xp'] + c['xp']) * 100)}%", col),
        (f"골드 +{round((0.10 * m['gold'] + ws['gold']) * 100)}%", col),
        (f"무적 {(60 + ws['inv'] + c['inv']) / 60:.2f}초", col),
        (f"대시 쿨 {max(60, 120 - ws['dash']) / 60:.1f}초", col),
        (f"시작 스킬 {n_skill}개", (255, 230, 120)),
    ]


def draw_char_cell(rect, wid, selected, current, key):
    if selected:
        pixel_panel(screen, rect.inflate(6, 6), (255, 255, 255), (255, 255, 255), n=5, bw=3)
    if wid == "":
        pixel_panel(screen, rect, (120, 60, 64), (40, 22, 26), n=5, bw=3)
        blit_text(screen, tiny_font, "해제", (255, 150, 150), rect.center, True)
        return
    w = WEAPONS[wid]
    rc = RARITY[w["rarity"]]["color"]
    if w["rarity"] == "myth":
        rc = lerp_color(rc, (255, 255, 255), 0.35 + 0.35 * math.sin(frame_tick * 0.1))
    pixel_panel(screen, rect, rc, tuple(c // 6 + 16 for c in rc), n=5, bw=3)
    add_glow(screen, rarity_glows[w["rarity"]], (rect.centerx, rect.y + 17), 0.4)
    im = weapon_img(wid, 2)
    screen.blit(im, im.get_rect(center=(rect.centerx, rect.y + 17)))
    for k in range(MAX_STAR):
        draw_star(screen, (rect.centerx - 16 + k * 8, rect.bottom - 7), 3, rc, empty=k >= weapon_stars[wid])
    if current:
        tag = pygame.Rect(rect.x + 4, rect.y + 4, 14, 14)
        pygame.draw.rect(screen, (60, 190, 110), tag)
        pygame.draw.rect(screen, (14, 12, 30), tag, 2)
        blit_text(screen, tiny_font, "E", (255, 255, 255), tag.center, True)
    sk = w.get("set")
    if sk:
        pygame.draw.circle(screen, (14, 12, 30), (rect.right - 10, rect.y + 10), 6)
        pygame.draw.circle(screen, SETS[sk]["color"], (rect.right - 10, rect.y + 10), 4)


def draw_char_detail(rect, wid):
    pixel_panel(screen, rect, (95, 105, 160), (26, 28, 50), n=6, bw=3)
    if wid == "":
        blit_text(screen, tiny_font, "이 칸의 장비를 해제해요 (Enter / 클릭)", (255, 170, 170), rect.center, True)
        return
    w = WEAPONS[wid]
    rc = RARITY[w["rarity"]]["color"]
    star = weapon_stars.get(wid, 1)
    add_glow(screen, rarity_glows[w["rarity"]], (rect.x + 42, rect.y + 38), 0.9)
    im = weapon_img(wid, 3)
    screen.blit(im, im.get_rect(center=(rect.x + 42, rect.y + 38)))
    for k in range(MAX_STAR):
        draw_star(screen, (rect.x + 14 + k * 14, rect.y + 82), 5, rc, empty=k >= star)
    blit_text(screen, small_font, w["name"], (255, 255, 255), (rect.x + 86, rect.y + 6))
    tags = [(RARITY[w["rarity"]]["name"], rc)]
    if w["slot"] == "weapon":
        mode, par = weapon_style(wid)
        tags.append(("근접" if mode == "melee" else "원거리", (255, 200, 120)))
        tags.append((par["tag"], (190, 200, 230)))
    if w.get("set"):
        tags.append((SETS[w["set"]]["name"] + " 세트", SETS[w["set"]]["color"]))
    x = rect.x + 86
    for txt, col in tags:
        t = tiny_font.render(txt, True, col)
        screen.blit(t, (x, rect.y + 44))
        x += t.get_width() + 12
    for i, line in enumerate(weapon_stat_lines(wid, star)[:6]):
        blit_text(screen, tiny_font, line, (200, 225, 255), (rect.x + 86 + (i % 2) * 180, rect.y + 62 + (i // 2) * 15))


def set_panel_lines():
    cnt = set_counts()
    lines = []  # (글씨, 색, 꼭 보여줄지)
    for sk, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
        sd = SETS[sk]
        lines.append((f"{sd['name']}   {n} / {SET_SIZE[sk]}", sd["color"], True))
        for thr, b in sorted(sd["bonus"].items()):
            on = n >= thr
            lines.append((f"{thr}세트  {b['desc']}", (200, 255, 210) if on else (112, 118, 152), on))
    if len(lines) > 10:
        lines = [ln for ln in lines if ln[2]]
    if not cnt:
        lines.append(("같은 세트 장비를 맞춰 끼면 효과가 발동해요!", (255, 230, 120), True))
    for sk, sd in SETS.items():
        if sk not in cnt and len(lines) < 10:
            have = sum(1 for k, w in WEAPONS.items() if w.get("set") == sk and k in weapon_stars)
            lines.append((f"{sd['name']}   보유 {have} / {SET_SIZE[sk]}", tuple(c * 2 // 3 for c in sd["color"]), True))
    return lines[:10]


def draw_character_screen():
    draw_menu_bg(120)
    blit_text(screen, font, "캐릭터", (255, 230, 120), (WIDTH // 2, 30), True)
    draw_gold_panel(screen)
    mouse = pygame.mouse.get_pos()
    draw_button(screen, BACK_RECT, "< 뒤로", BACK_RECT.collidepoint(mouse), True, (150, 170, 255))
    cls = CLASSES[cur_class]
    acc = cls["color"]
    key = CHAR_SLOTS[char_slot][0]
    items = char_items(key)
    _char_clamp(len(items))

    # ── 왼쪽: 캐릭터 + 장비 칸 6개 ──
    lp = pygame.Rect(16, 62, 304, 500)
    pixel_panel(screen, lp, tuple(v * 2 // 3 for v in acc), (22, 24, 44), n=8, bw=4)
    bob = int(3 * math.sin(frame_tick * 0.08))
    add_glow(screen, glow_hero, (168, 206), 0.9)
    draw_shadow(screen, (168, 262), 84, 0)
    himg = _dg_scaled(CLASS_SPRITES[cur_class], 112)
    screen.blit(himg, himg.get_rect(midbottom=(168, 262 + bob)))
    if equipped_weapon:
        wimg = pygame.transform.rotate(weapon_img(equipped_weapon, 3), 8 * math.sin(frame_tick * 0.08))
        screen.blit(wimg, wimg.get_rect(center=(214, 246 + bob)))
    for i, (k, label) in enumerate(CHAR_SLOTS):
        r = char_slot_rect(k)
        wid = char_current(k)
        blit_text(screen, tiny_font, label, (200, 210, 240) if i == char_slot else (140, 150, 185), (r.centerx, r.y - 9), True)
        if i == char_slot:
            pixel_panel(screen, r.inflate(10, 10), (255, 255, 255), (255, 255, 255), n=6, bw=3)
        if wid:
            w = WEAPONS[wid]
            rc = RARITY[w["rarity"]]["color"]
            if w["rarity"] == "myth":
                rc = lerp_color(rc, (255, 255, 255), 0.35 + 0.35 * math.sin(frame_tick * 0.1))
            pixel_panel(screen, r, rc, tuple(c // 6 + 16 for c in rc), n=6, bw=3)
            add_glow(screen, rarity_glows[w["rarity"]], r.center, 0.5)
            im = weapon_img(wid, 3)
            screen.blit(im, im.get_rect(center=(r.centerx, r.centery - 3)))
            for s in range(MAX_STAR):
                draw_star(screen, (r.centerx - 16 + s * 8, r.bottom - 7), 3, rc, empty=s >= weapon_stars.get(wid, 1))
            if w.get("set"):
                pygame.draw.circle(screen, (14, 12, 30), (r.right - 9, r.y + 9), 6)
                pygame.draw.circle(screen, SETS[w["set"]]["color"], (r.right - 9, r.y + 9), 4)
        else:
            pixel_panel(screen, r, (70, 76, 110), (24, 26, 44), n=6, bw=3)
            blit_text(screen, small_font, "+", (110, 118, 155), r.center, True)

    # 직업 선택 + 직업 효과
    draw_button(screen, CHAR_CL, "<", CHAR_CL.collidepoint(mouse), True, acc)
    draw_button(screen, CHAR_CR, ">", CHAR_CR.collidepoint(mouse), True, acc)
    blit_text(screen, small_font, cls["name"], acc, (168, 310), True)
    for i, (text, kind) in enumerate(cls["lines"]):
        col = (150, 255, 180) if kind == 1 else (255, 140, 140) if kind == 0 else (255, 230, 120)
        blit_text(screen, tiny_font, text, col, (168, 332 + 18 * i), True)

    # 능력치 요약
    blit_text(screen, tiny_font, "현재 능력치", (255, 230, 120), (168, 422), True)
    for i, (txt, col) in enumerate(char_preview()):
        blit_text(screen, tiny_font, txt, col, (lp.x + 18 + (i // 6) * 142, 442 + 18 * (i % 6)))

    # ── 오른쪽 위: 고른 부위의 장비 목록 ──
    pp = pygame.Rect(332, 62, 452, 176)
    pixel_panel(screen, pp, (150, 170, 255), (24, 26, 46), n=7, bw=3)
    blit_text(screen, tiny_font, f"{CHAR_SLOTS[char_slot][1]} 선택   (보유 {len(items) - (0 if key == 'weapon' else 1)}개)",
              (255, 230, 120), (pp.x + 14, pp.y + 10))
    if len(items) > 15:
        blit_text(screen, tiny_font, "마우스 휠: 스크롤", (150, 160, 190), (pp.right - 130, pp.y + 10))
    cur = char_current(key)
    for i, r in enumerate(char_cell_rects()):
        gi = char_scroll * 5 + i
        if gi < len(items):
            wid = items[gi]
            draw_char_cell(r, wid, gi == char_sel, wid != "" and wid == cur, key)

    # ── 오른쪽 가운데: 고른 장비 자세히 ──
    draw_char_detail(pygame.Rect(332, 244, 452, 104), items[char_sel] if items else "")

    # ── 오른쪽 아래: 세트 효과 ──
    sp = pygame.Rect(332, 354, 452, 208)
    pixel_panel(screen, sp, (235, 190, 70), (24, 26, 46), n=7, bw=3)
    blit_text(screen, tiny_font, "세트 효과", (255, 230, 120), (sp.x + 14, sp.y + 10))
    for i, (txt, col, _keep) in enumerate(set_panel_lines()):
        blit_text(screen, tiny_font, fit_text(tiny_font, txt, sp.w - 28), col, (sp.x + 14, sp.y + 32 + 17 * i))

    draw_toast(screen, 544)
    blit_text(screen, tiny_font, "W/S: 부위   A/D: 장비 선택   Enter / 클릭: 장착   X: 해제   Q/E: 직업   ESC: 뒤로",
              (150, 160, 190), (WIDTH // 2, 582), True)


_draw_achv_screen_p2 = draw_achv_screen


def draw_achv_screen():
    if char_open:
        draw_character_screen()
    else:
        _draw_achv_screen_p2()


# ------------------------------------------------------------
# 4) 던전 느낌 첫 화면
# ------------------------------------------------------------
DG_FLOOR_Y = 410
DG_TORCHES = [(78, 250), (722, 250), (236, 330), (564, 330)]
dg_gate_glow = make_glow(170, (130, 56, 18))
dg_torch_glow = make_glow(150, (135, 72, 26))
_dg = {"bg": None, "fog_a": None, "fog_b": None, "cache": {}}
TITLE_LABELS = [("게임 시작", (255, 210, 90)), ("캐릭터", (255, 140, 110)), ("영구 강화", (110, 220, 255)),
                ("무기 상점", (200, 140, 255)), ("업적", (140, 255, 170))]


def _dg_scaled(surf, size):
    key = (id(surf), size)
    s = _dg["cache"].get(key)
    if s is None:
        s = pygame.transform.scale(surf, (size, size))
        _dg["cache"][key] = s
    return s


def make_dungeon_title_bg():
    """돌벽 + 창살 문 + 아치 + 기둥 + 바닥 + 거미줄을 한 번만 그려 둬요."""
    W, H, FY = WIDTH, HEIGHT, DG_FLOOR_Y
    rng = random.Random(11)

    def cl(v):
        return max(0, min(255, int(v)))

    bg = pygame.Surface((W, H))
    bg.fill((12, 10, 18))

    # 1) 돌벽돌
    bw, bh = 52, 26
    for row in range(H // bh + 1):
        off = -(bw // 2) if row % 2 else 0
        for col in range(-1, W // bw + 2):
            x, y = col * bw + off, row * bh
            v = rng.randint(-17, 14)
            c = (cl(52 + v), cl(46 + v), cl(60 + v))
            pygame.draw.rect(bg, c, (x, y, bw, bh))
            pygame.draw.line(bg, (cl(c[0] + 18), cl(c[1] + 17), cl(c[2] + 18)),
                             (x + 3, y + 2), (x + rng.randint(18, bw - 5), y + 2))
            pygame.draw.line(bg, (cl(c[0] + 8), cl(c[1] + 7), cl(c[2] + 8)),
                             (x + rng.randint(8, bw - 16), y + 4), (x + bw - 5, y + 4))
            pygame.draw.line(bg, (cl(c[0] - 20), cl(c[1] - 19), cl(c[2] - 20)), (x + 2, y + bh - 3), (x + bw - 3, y + bh - 3))
            pygame.draw.rect(bg, (18, 15, 24), (x, y, bw, bh), 2)
            for _ in range(rng.randint(0, 2)):
                px, py = x + rng.randint(5, bw - 9), y + rng.randint(5, bh - 9)
                pygame.draw.rect(bg, (cl(c[0] - 14), cl(c[1] - 14), cl(c[2] - 14)), (px, py, rng.choice([2, 3]), 2))
            if rng.random() < 0.18:  # Damp, uneven moss gathers between old blocks.
                mx = x + rng.randint(5, bw - 12)
                my = y + bh - rng.randint(5, 8)
                moss = rng.choice(((42, 80, 43), (58, 99, 48), (70, 108, 52)))
                pygame.draw.rect(bg, moss, (mx, my, rng.randint(5, 11), rng.choice((2, 3))))
                pygame.draw.rect(bg, (76, 111, 59), (mx + 2, my - 2, 2, 2))
    for _ in range(14):  # 벽 균열
        x, y = rng.randint(60, W - 60), rng.randint(20, FY - 40)
        pts = [(x, y)]
        for _ in range(4):
            x += rng.randint(-10, 10)
            y += rng.randint(6, 16)
            pts.append((x, y))
        pygame.draw.lines(bg, (16, 13, 22), False, pts, 2)
    shade = pygame.Surface((W, H), pygame.SRCALPHA)  # 천장 쪽이 더 어두워요
    for y in range(FY):
        pygame.draw.line(shade, (0, 0, 0, int(150 * (1 - y / FY) ** 1.3)), (0, y), (W, y))
    bg.blit(shade, (0, 0))

    # 2) 바닥 (원근감 있는 타일)
    floor = pygame.Rect(0, FY, W, H - FY)
    pygame.draw.rect(bg, (34, 30, 42), floor)
    bg.set_clip(floor)
    prev = FY
    for k in range(1, 10):
        y = FY + int((H - FY) * (k / 9) ** 1.8)
        pygame.draw.rect(bg, (40, 35, 48) if k % 2 else (32, 28, 40), (0, prev, W, y - prev + 1))
        pygame.draw.line(bg, (16, 13, 22), (0, y), (W, y), 2)
        prev = y
    vx, vy = W // 2, 318
    for bx in range(-900, W + 901, 130):
        pygame.draw.line(bg, (18, 15, 24), (int(vx + (bx - vx) * (FY - vy) / (H - vy)), FY), (bx, H), 2)
    for _ in range(90):
        px, py = rng.randint(0, W), rng.randint(FY, H)
        pygame.draw.rect(bg, (26, 22, 32), (px, py, rng.choice([2, 3, 4]), 2))
    bg.set_clip(None)
    pygame.draw.line(bg, (8, 6, 12), (0, FY), (W, FY), 4)

    # 3) 양옆 기둥
    for px0, side in ((0, 1), (W - 52, -1)):
        for x in range(52):
            di = 51 - x if side == 1 else x  # 문 쪽 가장자리가 불빛을 받아 더 밝아요
            t = di / 51
            pygame.draw.line(bg, (cl(30 + 40 * (1 - t)), cl(27 + 36 * (1 - t)), cl(38 + 40 * (1 - t))),
                             (px0 + x, 0), (px0 + x, H))
        for y in range(40, H, 110):
            pygame.draw.rect(bg, (74, 68, 84), (px0, y, 52, 14))
            pygame.draw.rect(bg, (16, 13, 22), (px0, y + 14, 52, 4))
            pygame.draw.rect(bg, (16, 13, 22), (px0, y, 52, 14), 2)
        pygame.draw.line(bg, (12, 10, 16), (px0 + (51 if side == 1 else 0), 0), (px0 + (51 if side == 1 else 0), H), 3)

    # 4) 문: 불빛이 새어 나오는 반쯤 열린 쇠창살 문
    door = pygame.Surface((192, 188), pygame.SRCALPHA)
    for y in range(188):
        pygame.draw.line(door, lerp_color((8, 3, 8), (70, 28, 12), (y / 187) ** 1.4), (0, y), (191, y))
    door.blit(make_glow(130, (150, 62, 20)), (96 - 130, 188 - 130 - 24), special_flags=pygame.BLEND_RGB_ADD)
    for i in range(3):  # 안쪽으로 이어지는 계단
        pygame.draw.line(door, (130, 56, 24), (30 + i * 12, 188 - 16 * (i + 1)), (162 - i * 12, 188 - 16 * (i + 1)), 2)
    for x in range(14, 192, 26):
        pygame.draw.line(door, (14, 12, 18), (x, 0), (x, 104), 6)
        pygame.draw.line(door, (86, 82, 98), (x - 1, 0), (x - 1, 104), 1)
        pygame.draw.polygon(door, (14, 12, 18), [(x - 4, 104), (x + 4, 104), (x, 120)])
    for y in (36, 84):
        pygame.draw.line(door, (14, 12, 18), (0, y), (191, y), 6)
        pygame.draw.line(door, (86, 82, 98), (0, y - 2), (191, y - 2), 1)
    mask = pygame.Surface((192, 188), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (96, 96), 96)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 96, 192, 92))
    door.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    bg.blit(door, (304, FY - 188))

    # 5) 아치 돌 + 문기둥 + 해골 장식
    cx0, cy0 = 400, FY - 92
    n_v = 11
    for k in range(n_v):
        a0 = math.radians(180 + k * 180 / n_v)
        a1 = math.radians(180 + (k + 1) * 180 / n_v)
        ro = 124 + (12 if k == n_v // 2 else 0)
        pts = [(cx0 + 96 * math.cos(a0), cy0 + 96 * math.sin(a0)), (cx0 + ro * math.cos(a0), cy0 + ro * math.sin(a0)),
               (cx0 + ro * math.cos(a1), cy0 + ro * math.sin(a1)), (cx0 + 96 * math.cos(a1), cy0 + 96 * math.sin(a1))]
        sh = 70 + 12 * (k % 2) + rng.randint(-6, 6)
        pygame.draw.polygon(bg, (cl(sh), cl(sh - 5), cl(sh + 8)), pts)
        pygame.draw.polygon(bg, (14, 12, 18), pts, 2)
    for edge, d in ((304, -1), (496, 1)):
        for i in range(4):
            w = 28 if i % 2 == 0 else 22
            r = pygame.Rect(edge - w if d == -1 else edge, cy0 + 23 * i, w, 23)
            sh = 72 + 10 * (i % 2) + rng.randint(-5, 5)
            pygame.draw.rect(bg, (cl(sh), cl(sh - 5), cl(sh + 8)), r)
            pygame.draw.rect(bg, (14, 12, 18), r, 2)
    pygame.draw.rect(bg, (66, 60, 74), (270, FY, 260, 10))
    pygame.draw.line(bg, (104, 98, 112), (270, FY), (529, FY), 2)
    pygame.draw.rect(bg, (54, 49, 62), (250, FY + 10, 300, 10))
    pygame.draw.rect(bg, (14, 12, 18), (270, FY, 260, 10), 2)
    pygame.draw.rect(bg, (14, 12, 18), (250, FY + 10, 300, 10), 2)

    def skull(x, y, r):
        pygame.draw.circle(bg, (28, 24, 30), (x, y), r + 2)
        pygame.draw.circle(bg, (216, 210, 192), (x, y), r)
        pygame.draw.rect(bg, (216, 210, 192), (x - r // 2, y + r // 2, r, r * 3 // 4))
        pygame.draw.circle(bg, (20, 16, 22), (x - r // 3, y - 1), max(2, r // 3))
        pygame.draw.circle(bg, (20, 16, 22), (x + r // 3, y - 1), max(2, r // 3))
        pygame.draw.polygon(bg, (20, 16, 22), [(x, y + 2), (x - 2, y + r // 2 + 1), (x + 2, y + r // 2 + 1)])
        for tx in (-r // 3, 0, r // 3):
            pygame.draw.line(bg, (70, 62, 66), (x + tx, y + r), (x + tx, y + r + r // 3))

    skull(400, cy0 - 116, 10)
    skull(676, 452, 8)

    def bone(x, y, ang):
        d = pygame.Vector2(11, 0).rotate(ang)
        a, b = pygame.Vector2(x, y) - d, pygame.Vector2(x, y) + d
        pygame.draw.line(bg, (28, 24, 30), a + pygame.Vector2(0, 2), b + pygame.Vector2(0, 2), 5)
        pygame.draw.line(bg, (204, 198, 180), a, b, 3)
        pygame.draw.circle(bg, (204, 198, 180), a, 3)
        pygame.draw.circle(bg, (204, 198, 180), b, 3)

    bone(142, 458, 18)
    bone(150, 462, -32)
    bone(640, 466, 12)
    for _ in range(70):  # 이끼
        x, y = rng.randint(52, W - 52), FY - rng.randint(0, 20)
        pygame.draw.rect(bg, rng.choice([(34, 62, 40), (46, 84, 50), (26, 50, 34)]), (x, y, rng.choice([2, 3, 4]), rng.choice([2, 3])))

    # 6) 구석 거미줄
    def web(cx, cy, dx):
        col = (150, 150, 172)
        for ang in range(0, 91, 18):
            r = math.radians(ang)
            pygame.draw.line(bg, col, (cx, cy), (cx + dx * 96 * math.cos(r), cy + 96 * math.sin(r)), 1)
        for rad in (26, 48, 72, 96):
            prev_p = None
            for i, ang in enumerate(range(0, 91, 18)):
                r = math.radians(ang)
                rd = rad * (0.88 if i % 2 else 1.0)
                p = (cx + dx * rd * math.cos(r), cy + rd * math.sin(r))
                if prev_p:
                    pygame.draw.line(bg, col, prev_p, p, 1)
                prev_p = p

    web(52, 0, 1)
    web(W - 52, 0, -1)

    # 7) 횃불 받침 + 어둠
    for tx, ty in DG_TORCHES:
        pygame.draw.rect(bg, (30, 24, 24), (tx - 3, ty + 2, 8, 20))
        pygame.draw.rect(bg, (92, 70, 50), (tx - 4, ty, 8, 20))
        pygame.draw.rect(bg, (120, 120, 135), (tx - 8, ty - 3, 16, 5))
        pygame.draw.rect(bg, (60, 60, 72), (tx - 8, ty + 1, 16, 2))
    low = pygame.Surface((W, H), pygame.SRCALPHA)
    for y in range(FY, H):
        pygame.draw.line(low, (0, 0, 0, int(130 * (y - FY) / (H - FY))), (0, y), (W, y))
    bg.blit(low, (0, 0))
    bg.blit(make_vignette((0, 0, 0), 230, 120), (0, 0))
    return bg


def _make_fog(color, seed):
    fog = pygame.Surface((WIDTH, 150))
    fog.fill((0, 0, 0))
    r = random.Random(seed)
    blob = make_glow(70, color)
    for _ in range(14):
        x, y = r.randint(0, WIDTH), r.randint(30, 120)
        for dx in (-WIDTH, 0, WIDTH):  # 가장자리에서도 이어지게 세 번 찍어요
            fog.blit(blob, (x - 70 + dx, y - 70), special_flags=pygame.BLEND_RGB_ADD)
    return fog


def title_rects():
    gap = 10
    ws_ = [small_font.render(t, True, c).get_width() + 30 for t, c in TITLE_LABELS]
    x = (WIDTH - (sum(ws_) + gap * (len(ws_) - 1))) // 2
    rects = []
    for w in ws_:
        rects.append(pygame.Rect(x, 490, w, 46))
        x += w + gap
    return rects


def draw_dungeon_button(rect, text, hovered, accent):
    if hovered:
        add_glow(screen, glow_torch, rect.center, 1.0 + 0.05 * math.sin(frame_tick * 0.2))
    pixel_panel(screen, rect, (12, 9, 18), (12, 9, 18), n=5, bw=3)
    pixel_panel(screen, rect.inflate(-6, -6), accent if hovered else (86, 80, 98),
                (66, 59, 74) if hovered else (44, 40, 52), n=4, bw=2)
    pygame.draw.line(screen, (96, 88, 106) if hovered else (62, 57, 72), (rect.x + 8, rect.y + 7), (rect.right - 9, rect.y + 7))
    for rx, ry in ((rect.x + 8, rect.y + 9), (rect.right - 9, rect.y + 9), (rect.x + 8, rect.bottom - 10), (rect.right - 9, rect.bottom - 10)):
        pygame.draw.circle(screen, (150, 144, 160), (rx, ry), 2)  # 대갈못
    blit_text(screen, small_font, text, (255, 255, 255) if hovered else (214, 208, 226), rect.center, True)


def draw_title():
    """던전 입구: 돌벽, 횃불, 안개, 박쥐, 쇠사슬에 걸린 돌 간판, 철문 앞에 선 주인공."""
    t = frame_tick
    if _dg["bg"] is None:
        _dg["bg"] = make_dungeon_title_bg()
        _dg["fog_a"] = _make_fog((34, 30, 46), 5)
        _dg["fog_b"] = _make_fog((22, 20, 32), 9)
    screen.blit(_dg["bg"], (0, 0))
    add_glow(screen, dg_gate_glow, (400, 372), 1.0 + 0.06 * math.sin(t * 0.05) + 0.03 * math.sin(t * 0.23))

    for i, (tx, ty) in enumerate(DG_TORCHES):  # 일렁이는 횃불
        flick = (t // 4 + i * 3) % 3
        add_glow(screen, dg_torch_glow, (tx, ty - 12), 1.0 + 0.08 * flick)
        h = 10 + flick * 3
        pygame.draw.rect(screen, (200, 70, 25), (tx - 5, ty - h, 10, h))
        pygame.draw.rect(screen, (255, 160, 50), (tx - 3, ty - h + 2, 6, h - 3))
        pygame.draw.rect(screen, (255, 235, 150), (tx - 1, ty - h // 2, 2, h // 2 - 1))

    off = int(t * 0.35) % WIDTH  # 바닥 안개 (뒤쪽)
    for x in (-off, WIDTH - off):
        screen.blit(_dg["fog_b"], (x, 330), special_flags=pygame.BLEND_RGB_ADD)

    bobh = int(4 * math.sin(t * 0.08))  # 주인공 + 문지기들
    for px, size, ph in ((260, 64, 1.5), (540, 64, 3.0)):
        spr = slime_big if px < 400 else goblin_big
        img = _dg_scaled(spr, size)
        draw_shadow(screen, (px, 432), 56, 0)
        screen.blit(img, img.get_rect(midbottom=(px, 432 + int(3 * math.sin(t * 0.1 + ph)))))
    add_glow(screen, glow_hero, (400, 372), 0.9)
    draw_shadow(screen, (400, 424), 84, 0)
    himg = _dg_scaled(hero_sprite, 108)
    screen.blit(himg, himg.get_rect(midbottom=(400, 424 + bobh)))
    if equipped_weapon:
        rar = WEAPONS[equipped_weapon]["rarity"]
        wimg = pygame.transform.rotate(weapon_img(equipped_weapon, 4), 8 * math.sin(t * 0.08))
        wpos = (458, 396 + bobh)
        add_glow(screen, rarity_glows[rar], wpos, 0.9)
        screen.blit(wimg, wimg.get_rect(center=wpos))

    off = int(t * 0.6) % WIDTH  # 바닥 안개 (앞쪽, 반대 방향)
    for x in (off - WIDTH, off):
        screen.blit(_dg["fog_a"], (x, 440), special_flags=pygame.BLEND_RGB_ADD)
    draw_motes(screen, 36, (255, 170, 70), 1.0)  # 떠오르는 불씨

    for i in range(3):  # 박쥐
        bx = (t * (1.2 + 0.5 * i) + i * 330) % (WIDTH + 160) - 80
        by = 120 + 50 * i + 26 * math.sin(t * 0.04 + i * 2)
        w2 = max(14, int(36 * (0.55 + 0.45 * abs(math.sin(t * 0.3 + i)))))
        sp = squashed(bat_sprite, w2, 36)
        screen.blit(sp, sp.get_rect(center=(bx, by)))

    # 쇠사슬에 걸린 돌 간판
    tw, th = title_img.get_size()
    sw, sh = subtitle_img.get_size()
    plate = pygame.Rect(0, 0, max(tw, sw) + 80, th + sh + 10)
    plate.midtop = (WIDTH // 2, 46 + int(2 * math.sin(t * 0.04)))
    for cx in (plate.x + 36, plate.right - 36):
        for i, y in enumerate(range(0, plate.y, 12)):
            lw = 9 if i % 2 == 0 else 5
            pygame.draw.rect(screen, (30, 30, 38), (cx - lw // 2 - 1, y - 1, lw + 2, 17), 1)
            pygame.draw.rect(screen, (100, 102, 116), (cx - lw // 2, y, lw, 15), 2 if lw == 9 else 1)
    pixel_panel(screen, plate.move(0, 4), (6, 4, 10), (6, 4, 10), n=10, bw=5)
    pixel_panel(screen, plate, (69, 67, 70), (27, 25, 29), n=10, bw=5)
    # 간판 바깥 여백에 돌판 이음새와 아래쪽 이끼를 얹어 던전 벽과 한 덩어리처럼 보여요.
    stone = (47, 45, 49)
    # Broken joints and shallow chips make the hanging slab look hand-hewn.
    for side in (0, 1):
        sx = plate.x if side == 0 else plate.right
        direction = 1 if side == 0 else -1
        pygame.draw.lines(screen, (15, 14, 18), False,
                          [(sx + direction * 18, plate.y + 48),
                           (sx + direction * 27, plate.y + 57),
                           (sx + direction * 22, plate.y + 68),
                           (sx + direction * 34, plate.y + 78)], 2)
        pygame.draw.lines(screen, (91, 85, 81), False,
                          [(sx + direction * 19, plate.y + 48),
                           (sx + direction * 28, plate.y + 57),
                           (sx + direction * 23, plate.y + 68)], 1)
        pygame.draw.line(screen, stone, (sx + direction * 20, plate.y + 14),
                         (sx + direction * 20, plate.y + 35), 2)
    moss_colors = ((53, 92, 45), (76, 116, 53), (39, 72, 39))
    for side in (0, 1):
        mx = plate.x + 16 if side == 0 else plate.right - 29
        for j in range(9):
            my = plate.bottom - 15 - (j % 4) * 4
            pygame.draw.rect(screen, moss_colors[(j + side) % len(moss_colors)],
                             (mx + (j % 3) * 3, my, 4 + j % 3, 3))
    # Small worn pits in the exposed stone margins; keep the title lettering clear.
    for side in (0, 1):
        sx = plate.x + 38 if side == 0 else plate.right - 43
        for j in range(4):
            py = plate.y + 27 + j * 23
            pygame.draw.rect(screen, (18, 17, 21), (sx + (j % 2) * 4, py, 3, 2))
            pygame.draw.rect(screen, (91, 86, 82), (sx + 1 + (j % 2) * 4, py + 2, 2, 1))
    pygame.draw.rect(screen, (46, 42, 56), plate.inflate(-16, -16), 2)
    for rx, ry in ((plate.x + 14, plate.y + 14), (plate.right - 14, plate.y + 14),
                   (plate.x + 14, plate.bottom - 14), (plate.right - 14, plate.bottom - 14)):
        pygame.draw.circle(screen, (20, 18, 26), (rx, ry + 1), 5)
        pygame.draw.circle(screen, (150, 144, 160), (rx, ry), 4)
        pygame.draw.circle(screen, (225, 220, 232), (rx - 1, ry - 1), 1)
    screen.blit(title_img, title_img.get_rect(midtop=(plate.centerx, plate.y + 6)))
    screen.blit(subtitle_img, subtitle_img.get_rect(midtop=(plate.centerx, plate.y + 6 + th - 6)))

    if best_time > 0:
        blit_text(screen, small_font, f"무한 모드 최고  {best_time // 60:02d}:{best_time % 60:02d}  |  Kills {best_kills}",
                  (255, 230, 120), (WIDTH // 2, 462), True)

    mouse_rects = title_rects()
    for i, (r, (txt, acc)) in enumerate(zip(mouse_rects, TITLE_LABELS)):
        draw_dungeon_button(r, txt, i == menu_index, acc)
    if gold >= PULL_COST and (t // 20) % 2 == 0:
        blit_text(screen, tiny_font, "NEW", (255, 120, 140), (mouse_rects[3].right - 20, mouse_rects[3].y - 4), True)

    c = CLASSES[cur_class]
    chip = pygame.Rect(12, 12, 150, 34)
    pixel_panel(screen, chip, tuple(v * 2 // 3 for v in c["color"]), (22, 24, 44), n=4, bw=3)
    blit_text(screen, tiny_font, f"직업  {c['name']}", c["color"], chip.center, True)
    draw_gold_panel(screen)
    dash_name = pygame.key.name(feature_settings["dash_key"]).upper() if "feature_settings" in globals() else "SPACE"
    blit_text(screen, tiny_font,
              f"이동: WASD / 방향키     대시: {dash_name}     일시정지: P     메뉴: 방향키 + Enter     C: 캐릭터",
              (150, 160, 190), (WIDTH // 2, 582), True)
    draw_toast(screen, 440)


def title_activate(i):
    global state, stage_sel, upg_sel
    snd_click.play()
    if i == 0:
        state = "stage_select"
        stage_sel = 0
    elif i == 1:
        open_character()
    elif i == 2:
        state = "upgrade"
        upg_sel = 0
    elif i == 3:
        state = "shop"
    else:
        state = "achv"


def title_event(event):
    global menu_index
    rects = title_rects()
    n = len(rects)
    if event.type == pygame.MOUSEMOTION:
        for i, r in enumerate(rects):
            if r.collidepoint(event.pos):
                menu_index = i
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        for i, r in enumerate(rects):
            if r.collidepoint(event.pos):
                menu_index = i
                title_activate(i)
                break
    elif event.type == pygame.KEYDOWN:
        k = event.key
        if k in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
            menu_index = (menu_index - 1) % n
            snd_click.play()
        elif k in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
            menu_index = (menu_index + 1) % n
            snd_click.play()
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            title_activate(menu_index)
        elif k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
            menu_index = k - pygame.K_1
            title_activate(menu_index)
        elif k == pygame.K_c:
            menu_index = 1
            title_activate(1)


_menu_event_p2 = menu_event


def menu_event(event):
    if state == "title":
        title_event(event)
    elif state == "achv" and char_open:
        char_event(event)
    else:
        _menu_event_p2(event)

# ============================================================
# [패치 3] 직업 시스템 (CLASSES / set_class / apply_class_visuals)
# 붙여넣는 곳: "# 새 장비가 등록됐으니 저장 파일을 다시 읽어요" 줄 바로 위 (딱 한 곳!)
# ============================================================
# hp 체력 / atk 공격력 / fire 공격간격 배율 / move 이동 / crit 치명타 / xp 경험치 / inv 무적(프레임) / start 시작 스킬
# lines: (글씨, 1=장점 0=단점 2=특징)
CLASSES = [
    {"name": "용사", "color": (120, 160, 255), "hp": 0, "atk": 0.0, "fire": 1.0, "move": 0.0, "crit": 0,
     "xp": 0.0, "inv": 0, "start": [], "hair": ((70, 60, 120), (205, 210, 245), (245, 247, 255)),
     "cloth": ((60, 85, 175), (35, 45, 110)), "lines": [("균형 잡힌 기본 직업", 2)]},
    {"name": "전사", "color": (255, 120, 90), "hp": 1, "atk": 0.10, "fire": 1.0, "move": -0.3, "crit": 0,
     "xp": 0.0, "inv": 0, "start": [], "hair": ((90, 40, 30), (220, 110, 80), (255, 190, 160)),
     "cloth": ((190, 60, 50), (110, 30, 30)),
     "lines": [("체력 +1", 1), ("공격력 +10%", 1), ("이동 속도 -0.3", 0)]},
    {"name": "마법사", "color": (190, 130, 255), "hp": -1, "atk": 0.0, "fire": 0.9, "move": 0.0, "crit": 0,
     "xp": 0.10, "inv": 0, "start": ["오라"], "hair": ((60, 30, 110), (150, 100, 230), (215, 180, 255)),
     "cloth": ((120, 70, 200), (70, 35, 130)),
     "lines": [("경험치 +10%", 1), ("시작 스킬: 오라", 1), ("체력 -1", 0)]},
    {"name": "도적", "color": (110, 230, 170), "hp": -1, "atk": 0.0, "fire": 0.85, "move": 0.5, "crit": 8,
     "xp": 0.0, "inv": 0, "start": [], "hair": ((30, 60, 50), (80, 170, 130), (170, 240, 205)),
     "cloth": ((50, 120, 90), (25, 65, 50)),
     "lines": [("이동 +0.5", 1), ("치명타 +8%", 1), ("공격 빠름", 1), ("체력 -1", 0)]},
    {"name": "성기사", "color": (255, 220, 100), "hp": 2, "atk": -0.05, "fire": 1.0, "move": -0.2, "crit": 0,
     "xp": 0.0, "inv": 15, "start": ["보호막"], "hair": ((120, 90, 30), (240, 200, 90), (255, 240, 170)),
     "cloth": ((220, 190, 80), (140, 110, 40)),
     "lines": [("체력 +2", 1), ("무적 +0.25초", 1), ("시작 스킬: 보호막", 1), ("공격력 -5%", 0)]},
]
cur_class = 0
CLASS_PATH = os.path.join(BASE_DIR, "class.json")


def _make_class_sprite(c):
    col = dict(HERO_COLORS)
    col["H"], col["h"], col["l"] = c["hair"]
    col["n"], col["N"] = c["cloth"]
    return make_sprite(HERO_PIXELS, col)


CLASS_SPRITES = [_make_class_sprite(c) for c in CLASSES]


def apply_class_visuals():
    """고른 직업의 색으로 주인공 그림을 바꿔요."""
    global hero_sprite, hero_left, hero_ghost, hero_ghost_left, hero_big
    spr = CLASS_SPRITES[cur_class]
    hero_sprite = spr
    hero_left = pygame.transform.flip(spr, True, False)
    hero_ghost = spr.copy()
    hero_ghost_left = hero_left.copy()
    hero_big = pygame.transform.scale(spr, (144, 144))


def set_class(i):
    global cur_class
    cur_class = i % len(CLASSES)
    apply_class_visuals()
    try:
        with open(CLASS_PATH, "w", encoding="utf-8") as f:
            json.dump({"cls": cur_class}, f)
    except OSError:
        pass
    snd_click.play()
    show_toast(f"직업: {CLASSES[cur_class]['name']}", CLASSES[cur_class]["color"])


_load_save_cls = load_save


def load_save():
    global cur_class
    _load_save_cls()
    try:
        with open(CLASS_PATH, "r", encoding="utf-8") as f:
            cur_class = int(json.load(f).get("cls", 0)) % len(CLASSES)
    except (OSError, ValueError, TypeError, AttributeError):
        cur_class = 0


_reset_game_cls = reset_game


def reset_game():
    global player_max_hp, player_hp, dmg_mult, fire_interval, player_speed
    global crit_percent, xp_bonus, inv_bonus
    _reset_game_cls()
    c = CLASSES[cur_class]
    player_max_hp = max(1, player_max_hp + c["hp"])
    player_hp = player_max_hp
    dmg_mult += c["atk"]
    fire_interval = max(10, round(fire_interval * c["fire"]))
    player_speed += c["move"]
    crit_percent += c["crit"]
    xp_bonus += c["xp"]
    inv_bonus += c["inv"]
    for sk in c["start"]:
        apply_upgrade(sk)

# ============================================================
# [패치 1 통합] 신화 등급 / 부위별 뽑기 / 등급순 정렬 / 직업 3종
# 붙여넣는 곳: "# 새 장비가 등록됐으니 저장 파일을 다시 읽어요" 줄 바로 위 (딱 한 곳!)
# (예전 [패치 3] 직업 코드는 지우세요)
# ============================================================
RARITY["common"]["w"], RARITY["rare"]["w"] = 58, 28
RARITY["epic"]["w"], RARITY["legend"]["w"] = 11, 2.6
RARITY["myth"] = {"name": "신화", "color": (255, 95, 150), "w": 0.4}
RARITY_ORDER.append("myth")
rarity_glows["myth"] = make_glow(80, tuple(int(c * 0.55) for c in RARITY["myth"]["color"]))

_items("weapon", [("m_worldsword", "세계수의 성검", "myth", "sword",
                   ((120, 255, 170), (240, 255, 245), (255, 215, 90)),
                   {"atk": 0.30, "spd": 0.10, "crit": 8, "start": "혜성"})])
_items("armor", [("m_aegis", "신의 방패 아이기스", "myth", "armor",
                  ((255, 215, 90), (255, 250, 210), (200, 60, 90)),
                  {"hp": 3, "atk": 0.12, "inv": 20, "start": "보호막"})])
_items("acc", [("m_infinity", "무한의 반지", "myth", "ring",
                ((190, 120, 255), (250, 220, 255), (255, 215, 90)),
                {"crit": 10, "gold": 0.25, "xp": 0.15, "start": "폭발탄"})])
_items("rune", [("m_void", "공허의 룬", "myth", "rune",
                 ((170, 90, 255), (240, 215, 255), (20, 10, 40)),
                 {"atk": 0.20, "spd": 0.12, "start": "시간 정지"})])
_items("pet", [("m_sunbird", "태양 불사조", "myth", "petw",
                ((255, 190, 60), (255, 250, 190), (255, 90, 40)),
                {"pet": True, "pcd": 55, "pshots": 4, "pdmg": 2, "pheal": 1500})])
ELITE_GEAR_IDS = ("elite_blade", "elite_plate", "elite_charm", "elite_rune", "elite_companion")
_items("weapon", [
    ("elite_blade", "정예 토벌검", "legend", "sword", ((225, 165, 70), (255, 235, 150), (255, 110, 45)), {"atk": 0.12, "spd": 0.04, "crit": 2}),
])
_items("armor", [
    ("elite_plate", "정예 수호 갑옷", "legend", "armor", ((170, 115, 55), (255, 205, 110), (255, 130, 55)), {"hp": 1, "inv": 6}),
])
_items("acc", [
    ("elite_charm", "정예 사냥 부적", "legend", "amulet", ((225, 160, 65), (255, 235, 150), (255, 115, 45)), {"crit": 4, "gold": 0.06}),
])
_items("rune", [
    ("elite_rune", "정예 추적 룬", "legend", "rune", ((195, 120, 55), (255, 220, 125), (255, 115, 50)), {"atk": 0.08, "xp": 0.05}),
])
_items("pet", [
    ("elite_companion", "정예 불씨 정령", "legend", "petw", ((235, 105, 45), (255, 225, 130), (255, 80, 35)), {"pet": True, "pcd": 55, "pshots": 2, "pdmg": 1}),
])
ALL_ORDER[:] = list(WEAPONS.keys())
for _r in RARITY_ORDER:
    WEAPONS_BY_RARITY[_r] = [k for k, v in WEAPONS.items() if v["rarity"] == _r]


# --- 상점 목록: 등급 낮은 것 -> 높은 것 (높은 것부터 보려면 sorted(..., reverse=True)) ---
def set_tab(slot, wid=None):
    global shop_tab, shop_sel
    shop_tab = SLOTS.index(slot)
    WEAPON_ORDER[:] = sorted((k for k in ALL_ORDER if WEAPONS[k]["slot"] == slot),
                             key=lambda k: RARITY_ORDER.index(WEAPONS[k]["rarity"]))
    shop_sel = WEAPON_ORDER.index(wid) if wid in WEAPON_ORDER else 0
reverse=True

def shop_cell_rects():
    return [pygame.Rect(340 + (i % 5) * 88, 236 + (i // 5) * 60, 84, 56) for i in range(len(WEAPON_ORDER))]


def draw_weapon_cell(rect, wid, selected):
    w = WEAPONS[wid]
    rc = RARITY[w["rarity"]]["color"]
    owned = wid in weapon_stars
    if owned and w["rarity"] == "myth":  # 신화는 테두리가 반짝여요
        rc = lerp_color(rc, (255, 255, 255), 0.35 + 0.35 * math.sin(frame_tick * 0.1))
    if selected:
        pixel_panel(screen, rect.inflate(6, 6), (255, 255, 255), (255, 255, 255), n=5, bw=3)
    pixel_panel(screen, rect, rc if owned else (60, 64, 90),
                tuple(c // 6 + 16 for c in rc) if owned else (22, 24, 40), n=5, bw=3)
    if owned:
        add_glow(screen, rarity_glows[w["rarity"]], (rect.centerx, rect.y + 24), 0.4)
    img = weapon_img(wid, 2, dark=not owned)
    screen.blit(img, img.get_rect(center=(rect.centerx, rect.y + 24)))
    if owned:
        for k in range(MAX_STAR):
            draw_star(screen, (rect.centerx - 20 + k * 10, rect.bottom - 10), 3.5, rc, empty=k >= weapon_stars[wid])
        if is_equipped(wid):
            tag = pygame.Rect(rect.x + 5, rect.y + 5, 16, 16)
            pygame.draw.rect(screen, (60, 190, 110), tag)
            pygame.draw.rect(screen, (14, 12, 30), tag, 2)
            blit_text(screen, tiny_font, "E", (255, 255, 255), tag.center, True)
    else:
        blit_text(screen, tiny_font, "???", (110, 116, 150), (rect.centerx, rect.bottom - 10), True)


# --- 뽑기: 지금 보고 있는 분류(무기/방어구/장신구/룬/펫)에서만 나와요 ---
def _slot_pool(rar, slot):
    return [k for k in WEAPONS_BY_RARITY[rar] if WEAPONS[k]["slot"] == slot and k not in ELITE_GEAR_IDS]


def roll_weapon(min_rarity=None, slot=None):
    global pity_by_slot
    slot = slot or SLOTS[shop_tab]
    slot_pity = pity_by_slot.get(slot, 0)
    if slot_pity >= PITY_LIMIT - 1:
        rar = "legend"
    else:
        rar = random.choices(RARITY_ORDER, [RARITY[r]["w"] for r in RARITY_ORDER])[0]
    if min_rarity and RARITY_ORDER.index(rar) < RARITY_ORDER.index(min_rarity):
        rar = min_rarity
    i = RARITY_ORDER.index(rar)
    while i > 0 and not _slot_pool(RARITY_ORDER[i], slot):
        i -= 1
    rar = RARITY_ORDER[i]
    pity_by_slot[slot] = 0 if rar in ("legend", "myth") else min(PITY_LIMIT - 1, slot_pity + 1)
    return random.choice(_slot_pool(rar, slot))


def do_pull(n):
    global gold, shop_results, shop_anim
    cost = PULL_COST if n == 1 else PULL10_COST
    if gold < cost:
        show_toast("골드가 부족해요", (255, 130, 130))
        snd_fail.play()
        return
    gold -= cost
    slot = SLOTS[shop_tab]
    results = []
    got_rare = False
    for i in range(n):
        force = "rare" if (n == 10 and i == 9 and not got_rare) else None
        wid = roll_weapon(force, slot)
        if RARITY_ORDER.index(WEAPONS[wid]["rarity"]) >= 1:
            got_rare = True
        if wid in weapon_stars:
            if weapon_stars[wid] < MAX_STAR:
                weapon_stars[wid] += 1
                kind = "star"
            else:
                gold += DUP_REFUND
                kind = "refund"
        else:
            weapon_stars[wid] = 1
            kind = "new"
        results.append({"id": wid, "kind": kind})
    best = max(results, key=lambda r: RARITY_ORDER.index(WEAPONS[r["id"]]["rarity"]))
    set_tab(slot, best["id"])
    shop_results = results
    shop_anim = 0
    check_achievements()
    save_game()
    snd_level.play()


_draw_result_card_old = draw_result_card


def draw_result_card(rect, res, t, big):
    if WEAPONS[res["id"]]["rarity"] == "myth":
        add_glow(screen, rarity_glows["myth"], rect.center, 3.4 if big else 2.0)
    _draw_result_card_old(rect, res, t, big)


_draw_shop_screen2 = draw_shop_screen


def draw_shop_screen():
    _draw_shop_screen2()
    if shop_results:
        return
    panel_bg = (30, 28, 48)
    pygame.draw.rect(screen, panel_bg, (348, 70, 200, 32))
    blit_text(screen, small_font, f"{SLOT_NAMES[SLOTS[shop_tab]]} 뽑기", (255, 230, 120), (358, 72))
    # Draw the odds and guarantee once, on short aligned rows.
    pygame.draw.rect(screen, panel_bg, (344, 158, 432, 36))
    blit_text(screen, tiny_font, "일반 58%  ·  희귀 28%  ·  영웅 11%",
              (170, 180, 210), (560, 166), True)
    blit_text(screen, tiny_font, "전설 2.6%  ·  신화 0.4%  ·  10회: 희귀 이상 1개 보장",
              (170, 180, 210), (560, 183), True)



# --- 직업 3종 ---
# hp 체력 / atk 공격력 / fire 발사 간격 배율(작을수록 빠름) / move 이동 / xp 경험치 / crit 치명타 / inv 무적 프레임
CLASSES = [
    {"name": "전사", "color": (255, 130, 90), "hp": 2, "atk": 0.15, "fire": 1.10, "move": -0.2, "xp": 0, "crit": 0,
     "inv": 18, "start": ["회전 칼날"],
     "lines": [("체력 +2", 1), ("공격력 +15%", 1), ("무적 +0.3초", 1), ("공속 -10% / 이동 -0.2", 0), ("시작: 회전 칼날", 2)],
     "pal": {"n": (150, 55, 50), "N": (95, 28, 30), "H": (90, 40, 40), "r": (230, 190, 70), "R": (160, 120, 40)}},
    {"name": "마법사", "color": (170, 120, 255), "hp": -1, "atk": 0.10, "fire": 1.0, "move": 0, "xp": 0.15, "crit": 5,
     "inv": 0, "start": ["번개"],
     "lines": [("체력 -1", 0), ("공격력 +10%", 1), ("경험치 +15%", 1), ("치명타 +5%", 1), ("시작: 번개", 2)],
     "pal": {"n": (110, 70, 190), "N": (60, 35, 120), "H": (60, 40, 110), "r": (120, 200, 255), "R": (60, 130, 200)}},
    {"name": "궁수", "color": (120, 230, 130), "hp": 0, "atk": -0.05, "fire": 0.80, "move": 0.4, "xp": 0, "crit": 8,
     "inv": 0, "start": ["관통"],
     "lines": [("공속 +25%", 1), ("이동 +0.4", 1), ("치명타 +8%", 1), ("공격력 -5%", 0), ("시작: 관통", 2)],
     "pal": {"n": (70, 150, 80), "N": (35, 90, 50), "H": (60, 90, 50), "r": (235, 170, 60), "R": (160, 100, 40),
             "b": (95, 70, 40)}},
]
CLASS_SPRITES = [make_sprite(HERO_PIXELS, {**HERO_COLORS, **c["pal"]}) for c in CLASSES]
cur_class = 0


def apply_class_visuals():
    global hero_sprite, hero_left, hero_ghost, hero_ghost_left, hero_big
    hero_sprite = CLASS_SPRITES[cur_class]
    hero_left = pygame.transform.flip(hero_sprite, True, False)
    hero_ghost = hero_sprite.copy()
    hero_ghost_left = hero_left.copy()
    hero_big = pygame.transform.scale(hero_sprite, (144, 144))


def apply_class_bonuses():
    global player_max_hp, player_hp, player_speed, fire_interval, dmg_mult
    global xp_bonus, crit_percent, inv_bonus
    c = CLASSES[cur_class]
    player_max_hp = max(1, player_max_hp + c["hp"])
    player_hp = player_max_hp
    player_speed += c["move"]
    fire_interval = max(10, round(fire_interval * c["fire"]))
    dmg_mult += c["atk"]
    xp_bonus += c["xp"]
    crit_percent += c["crit"]
    inv_bonus += c["inv"]
    for sk in c["start"]:
        apply_upgrade(sk)


# 능력치 중복 방지: 직업 보너스를 넣기 전의 기본 초기화 함수(P2 포함)를 호출합니다.
# 기존 reset_game 래퍼(5909행)는 직업 보너스를 이미 적용하므로 여기서 다시 감싸면 중복됩니다.
_reset_game_old = _reset_game_cls


def reset_game():
    _reset_game_old()
    apply_class_bonuses()  # 직업 보너스는 판마다 딱 한 번 적용


def set_class(i):
    global cur_class
    cur_class = i % len(CLASSES)
    apply_class_visuals()
    save_game()
    snd_click.play()


def save_game():
    data = {"best_time": best_time, "best_kills": best_kills, "gold": gold, "meta": meta_levels,
            "weapons": weapon_stars, "equipped": equipped_weapon, "gear": equipped_gear,
            "pity_by_slot": pity_by_slot, "pity": pity_by_slot["weapon"],
            "stages_cleared": sorted(stages_cleared), "stage_best": stage_best,
            "total_kills": total_kills, "total_bosses": total_bosses, "total_elites": total_elites,
            "achv": achv_done, "cls": cur_class}
    tmp = SAVE_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, SAVE_PATH)
    except OSError:
        pass


_load_save_old = load_save


def load_save():
    global cur_class
    _load_save_old()
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            v = int(json.load(f).get("cls", 0))
    except (OSError, ValueError, TypeError, AttributeError):
        v = 0
    cur_class = v if 0 <= v < len(CLASSES) else 0


# ============================================================
# ============================================================
# ============================================================
# [패치 6] 새 보스 3종: 뱀파이어 군주 / 리치 왕 / 서리 거인
# 붙여넣는 곳: "# 새 장비가 등록됐으니 저장 파일을 다시 읽어요" 줄 바로 위 (딱 한 곳!)
# ============================================================
def _fix16(rows):
    """도트 그림 한 줄이 16칸이 아니어도 자동으로 맞춰요 (오타로 꺼지는 걸 막아요)."""
    return [r.ljust(16, ".")[:16] for r in rows][:16]


VAMPIRE_PIXELS = [
    "................",
    ".....dddddd.....",
    "....dkkkkkkd....",
    "...dkkkkkkkkd...",
    "...dkrkkkkrkd...",
    "...dkkkkkkkkd...",
    "....dkwkkwkd....",
    "..dd.dkkkkd.dd..",
    ".dRRddkkkkddRRd.",
    "dRRRRdRRRRdRRRRd",
    "dRRRRRRrrRRRRRRd",
    "dRRRRRRrrRRRRRRd",
    ".dRRRRRRRRRRRRd.",
    "..dRRRRddRRRRd..",
    "...dRRd..dRRd...",
    "....ddd..ddd....",
]
VAMPIRE_COLORS = {"d": (30, 15, 35), "k": (235, 225, 235), "r": (255, 70, 80),
                  "R": (140, 25, 55), "w": (255, 255, 255)}

LICH_PIXELS = [
    ".....y.yy.y.....",
    "....yyyyyyyy....",
    "....dwwwwwwd....",
    "...dwwwwwwwwd...",
    "...dwgwwwwgwd...",
    "...dwgwwwwgwd...",
    "...dwwwddwwwd...",
    "....dwdwwdwd....",
    "..dppppppppppd..",
    ".dwdpppwwpppdwd.",
    "dwwdppwppwppdwwd",
    ".dddpppppppppddd",
    "...dpppPPpppd...",
    "..dppPPPPPPppd..",
    ".dppPPPPPPPPppd.",
    "dpPpPpPPPPpPpPpd",
]
LICH_COLORS = {"y": (255, 215, 80), "d": (20, 15, 40), "w": (225, 225, 215),
               "g": (120, 255, 150), "p": (80, 50, 140), "P": (45, 28, 90)}

GIANT_PIXELS = [
    "..i...i..i...i..",
    "..ii.iiiiii.ii..",
    "...iiiiiiiiii...",
    "...dwwwwwwwwd...",
    "...dwbwwwwbwd...",
    "...dwwwwwwwwd...",
    "....dwwddwwd....",
    "..dddwwwwwwddd..",
    ".diiiwwwwwwiiid.",
    "diwwiwwwwwwiwwid",
    "dwwwdwwiiwwdwwwd",
    "dwwwdwiiiiwdwwwd",
    ".dddwwiiiiwwddd.",
    "...dwwwddwwwd...",
    "...dwwd..dwwd...",
    "..iiiii..iiiii..",
]
GIANT_COLORS = {"d": (30, 60, 110), "w": (225, 240, 255), "i": (130, 200, 245), "b": (40, 90, 220)}

vampire_sprite = make_sprite(_fix16(VAMPIRE_PIXELS), VAMPIRE_COLORS, 5)
lich_sprite = make_sprite(_fix16(LICH_PIXELS), LICH_COLORS, 5)
giant_sprite = make_sprite(_fix16(GIANT_PIXELS), GIANT_COLORS, 5)


def _bt(r, color, spr):
    d = _et(1.0, 0, r, color, spr)
    d["frost"] = make_tint(spr, (30, 80, 150))
    return d


enemy_types.update({
    "vampire": _bt(28, (255, 70, 90), vampire_sprite),
    "lich": _bt(30, (120, 255, 150), lich_sprite),
    "frostgiant": _bt(38, (150, 215, 255), giant_sprite),
})
BOSS_NAMES.update({"vampire": "뱀파이어 군주", "lich": "리치 왕", "frostgiant": "서리 거인"})
GOLD_VALUE.update({"vampire": 80, "lich": 90, "frostgiant": 110})
BOSS_NEW = {"vampire", "lich", "frostgiant"}
RAIN_R = 52

# 무한 / 도전 모드 보스 순서
ENDLESS_BOSSES[:] = ["vampire", "lich", "frostgiant", "orc", "dragon", "golem"]

# 스테이지 보스 (kind, 등장 프레임, 체력 배율) - 마지막이 최종 보스
STAGES[2]["bosses"] = [("golem", 4200, 1.4), ("frostgiant", 10800, 1.3)]
STAGES[2]["desc"] = "고드름이 떨어져요! 골렘 -> 서리 거인\n(약 3분)"
STAGES[4]["bosses"] = [("vampire", 4200, 2.0), ("golem", 9000, 1.8), ("lich", 14400, 2.6)]
STAGES[6]["bosses"] = [("vampire", 4800, 2.6), ("lich", 9600, 3.0), ("dragon", 15600, 3.8)]


# --- 등장 ---
_spawn_boss_new_old = spawn_boss


def spawn_boss(kind, hp_scale=None, final=False):
    global banner_text
    if kind not in BOSS_NEW:
        return _spawn_boss_new_old(kind, hp_scale, final)
    scale = hp_scale if hp_scale is not None else 1 + (boss_count // len(ENDLESS_BOSSES)) * 0.6
    _spawn_boss_new_old("orc", hp_scale, final)  # 경고 문구 / 소리 / 타이머는 그대로 쓰고 내용만 바꿔요
    e = enemies[-1]
    e["kind"] = kind
    if kind == "vampire":
        hp = int((95 + 11 * level) * scale)
    elif kind == "lich":
        hp = int((125 + 13 * level) * scale)
    else:
        hp = int((170 + 16 * level) * scale)
    e["hp"] = e["max_hp"] = hp
    if kind == "lich":
        e["pos"] = pygame.Vector2(WIDTH / 2, -90)
        e["state"] = "enter"
    else:
        e["pos"] = pygame.Vector2(random.choice([-50, WIDTH + 50]), random.randint(100, HEIGHT - 100))
        e["state"] = "chase"
    e["st_timer"] = 0
    e["cooldown"] = 70
    e["atk"] = 0
    banner_text = f"WARNING!  {BOSS_NAMES[kind]} 등장"


# --- 공통 도우미 ---
def _go(e, state):
    e["state"] = state
    e["st_timer"] = 0


def _clamp_boss(e, m=60):
    e["pos"].x = max(m, min(WIDTH - m, e["pos"].x))
    e["pos"].y = max(m, min(HEIGHT - m, e["pos"].y))


def _boss_shot(pos, ang, spd, life=260, color=(200, 130, 255)):
    enemy_shots.append({"pos": pos.copy(), "vel": pygame.Vector2(spd, 0).rotate(ang),
                        "life": life, "color": color, "boss": True})


def _prog(e):
    return min(1.0, e["st_timer"] / max(1, e.get("dur", 30)))


# --- 뱀파이어 군주: 순간이동 / 박쥐 소환 / 나선 탄막 ---
def update_vampire(e, to_player, dist, enraged):
    st = e["state"]
    if st == "chase":
        sp = 1.7 if enraged else 1.2
        if dist > 230:
            e["pos"] += to_player.normalize() * sp
        elif dist < 140:
            e["pos"] -= to_player.normalize() * sp
        _clamp_boss(e)
        e["cooldown"] -= 1
        if e["cooldown"] <= 0:
            e["atk"] += 1
            a = e["atk"] % 3
            if a == 1:  # 순간이동
                tgt = player_pos + pygame.Vector2(170, 0).rotate(random.uniform(0, 360))
                tgt.x = max(60, min(WIDTH - 60, tgt.x))
                tgt.y = max(130, min(HEIGHT - 60, tgt.y))
                e["target"] = tgt
                e["dur"] = 26 if enraged else 38
                _go(e, "blink_windup")
            elif a == 2:  # 박쥐 소환
                e["dur"] = 30
                _go(e, "bat_windup")
            else:  # 나선 탄막
                e["angle"] = angle_of(to_player)
                e["sweep"] = random.choice([-1, 1])
                e["dur"] = 30
                _go(e, "spiral_windup")
    elif st == "blink_windup":
        if e["st_timer"] >= e["dur"]:
            rings.append({"pos": e["pos"].copy(), "r": 70, "life": 12, "max": 12, "color": (255, 80, 110)})
            e["pos"] = e["target"].copy()
            rings.append({"pos": e["pos"].copy(), "r": 90, "life": 14, "max": 14, "color": (255, 80, 110)})
            spawn_burst(e["pos"], (255, 80, 110), 12)
            n = 14 if enraged else 10
            base = angle_of(player_pos - e["pos"]) + 180 / n
            for i in range(n):
                _boss_shot(e["pos"], base + 360 * i / n, 3.6, color=(245, 85, 135))
            snd_zap.play()
            add_shake(5)
            _go(e, "recover")
    elif st == "bat_windup":
        if e["st_timer"] >= e["dur"]:
            n = 14 if enraged else 10
            base = angle_of(player_pos - e["pos"]) + 180 / n
            for i in range(n):
                _boss_shot(e["pos"], base + 360 * i / n, 4.0 if enraged else 3.5,
                           color=(210, 100, 255))
            rings.append({"pos": e["pos"].copy(), "r": 90, "life": 14, "max": 14, "color": (190, 90, 255)})
            spawn_burst(e["pos"], (190, 90, 255), 10)
            snd_boss.play()
            _go(e, "recover")
    elif st == "spiral_windup":
        if e["st_timer"] >= e["dur"]:
            _go(e, "spiral")
    elif st == "spiral":
        t = e["st_timer"]
        if t % (3 if enraged else 4) == 0:
            a = e["angle"] + e["sweep"] * t * 11
            _boss_shot(e["pos"], a, 3.3, color=(225, 95, 150))
            if enraged:
                _boss_shot(e["pos"], a + 180, 3.3, color=(225, 95, 150))
            if t % 12 == 0:
                snd_zap.play()
        if t >= 90:
            _go(e, "recover")
    elif st == "recover":
        if e["st_timer"] >= (32 if enraged else 50):
            _go(e, "chase")
            e["cooldown"] = 45 if enraged else 75


def _layer_vampire(layer, e):
    st = e["state"]
    pg = _prog(e)
    bp = (int(e["pos"].x), int(e["pos"].y))
    if st == "blink_windup":
        c = (int(e["target"].x), int(e["target"].y))
        pygame.draw.circle(layer, (255, 70, 60, int(35 + 60 * pg)), c, 52)
        pygame.draw.circle(layer, (255, 110, 90, int(70 + 110 * pg)), c, max(2, int(52 * pg)))
        pygame.draw.circle(layer, (255, 150, 130, 230), c, 52, 3)
    elif st == "bat_windup":
        pygame.draw.circle(layer, (190, 80, 255, int(40 + 90 * pg)), bp, int(30 + 50 * pg), 4)
    elif st == "spiral_windup":
        pygame.draw.circle(layer, (255, 110, 150, int(40 + 90 * pg)), bp, int(26 + 40 * pg), 4)


# --- 리치 왕: 회전 레이저 / 해골 소환 / 영혼 폭발 ---
def _beam_hit(e, angles):
    off = player_pos - e["pos"]
    for a in angles:
        u = pygame.Vector2(1, 0).rotate(a)
        along = off.x * u.x + off.y * u.y
        perp = abs(off.x * u.y - off.y * u.x)
        if 0 < along < 900 and perp < 13 + player_radius * 0.7:
            return True
    return False


def update_lich(e, to_player, dist, enraged):
    st = e["state"]
    if st == "enter":
        e["pos"].y += 2.0
        if e["pos"].y >= 120:
            _go(e, "chase")
            e["cooldown"] = 70
    elif st == "chase":
        sp = 1.2 if enraged else 0.9
        if dist > 300:
            e["pos"] += to_player.normalize() * sp
        elif dist < 210:
            e["pos"] -= to_player.normalize() * sp
        _clamp_boss(e, 70)
        e["cooldown"] -= 1
        if e["cooldown"] <= 0:
            e["atk"] += 1
            a = e["atk"] % 3
            if a == 1:  # 회전 레이저
                e["beam"] = e["beam0"] = angle_of(to_player)
                e["sweep"] = random.choice([-1, 1])
                e["nb"] = 3 if enraged else 2
                e["rate"] = 0.7 if enraged else 0.9
                e["dur"] = 42 if enraged else 60
                _go(e, "laser_windup")
            elif a == 2:  # 해골 소환
                e["dur"] = 40
                _go(e, "summon_windup")
            else:  # 영혼 폭발
                n = 6 if enraged else 5
                marks = [{"pos": player_pos.copy(), "delay": 0}]
                for i in range(1, n):
                    p = player_pos + pygame.Vector2(random.uniform(40, 170), 0).rotate(random.uniform(0, 360))
                    p.x = max(40, min(WIDTH - 40, p.x))
                    p.y = max(120, min(HEIGHT - 40, p.y))
                    marks.append({"pos": p, "delay": i * 9})
                e["marks"] = marks
                e["dur"] = 20
                _go(e, "rain_windup")
    elif st == "laser_windup":
        if e["st_timer"] >= e["dur"]:
            add_shake(3)
            snd_zap.play()
            _go(e, "laser")
    elif st == "laser":
        t = e["st_timer"]
        e["beam"] += e["rate"] * min(1.0, t / 25) * e["sweep"]
        angles = [e["beam"] + 360 * i / e["nb"] for i in range(e["nb"])]
        if _beam_hit(e, angles):
            hurt_player(4)
        if t >= 100:
            _go(e, "recover")
    elif st == "summon_windup":
        if e["st_timer"] >= e["dur"]:
            n = 9 if enraged else 7
            aim = angle_of(to_player)
            spread = 7 if enraged else 9
            for i in range(n):
                angle = aim + (i - (n - 1) / 2) * spread
                _boss_shot(e["pos"], angle, 4.6 if enraged else 4.0,
                           color=(120, 255, 170))
            rings.append({"pos": e["pos"].copy(), "r": 100, "life": 14, "max": 14, "color": (120, 255, 150)})
            spawn_burst(e["pos"], (120, 255, 150), 10)
            snd_boss.play()
            _go(e, "recover")
    elif st == "rain_windup":
        if e["st_timer"] >= e["dur"]:
            _go(e, "rain")
    elif st == "rain":
        t = e["st_timer"]
        for m in e["marks"]:
            if t - m["delay"] == 50:  # 쾅!
                rings.append({"pos": m["pos"].copy(), "r": RAIN_R * 1.6, "life": 12, "max": 12, "color": (140, 255, 180)})
                spawn_burst(m["pos"], (140, 255, 180), 8)
                add_shake(3)
                snd_hit.play()
                if m["pos"].distance_to(player_pos) < RAIN_R + player_radius:
                    hurt_player(4)
        if t >= e["marks"][-1]["delay"] + 62:
            _go(e, "recover")
    elif st == "recover":
        if e["st_timer"] >= (38 if enraged else 55):
            _go(e, "chase")
            e["cooldown"] = 55 if enraged else 85


def _layer_lich(layer, e):
    st = e["state"]
    pg = _prog(e)
    bp = (int(e["pos"].x), int(e["pos"].y))
    if st in ("laser_windup", "laser"):
        nb = e["nb"]
        total = e["rate"] * 87.5  # 레이저가 훑고 지나갈 각도
        for i in range(nb):  # 붉은 부채꼴 = 레이저가 지나갈 위험 구역
            a0 = e["beam0"] + 360 * i / nb
            pts = wedge_points(e["pos"], a0 + e["sweep"] * total / 2, total / 2, 900)
            pygame.draw.polygon(layer, (255, 70, 60, 38), pts)
        for i in range(nb):
            u = pygame.Vector2(1, 0).rotate(e["beam"] + 360 * i / nb)
            end = e["pos"] + u * 900
            if st == "laser_windup":
                pygame.draw.line(layer, (120, 255, 150, int(90 + 110 * pg)), e["pos"], end, 3 + int(8 * pg))
            else:
                pygame.draw.line(layer, (90, 230, 130, 150), e["pos"], end, 28)
                pygame.draw.line(layer, (230, 255, 235, 230), e["pos"], end, 10)
    elif st == "summon_windup":
        pygame.draw.circle(layer, (120, 255, 150, int(40 + 90 * pg)), bp, int(30 + 60 * pg), 4)
    elif st == "rain":
        for m in e["marks"]:
            lt = e["st_timer"] - m["delay"]
            c = (int(m["pos"].x), int(m["pos"].y))
            if 0 <= lt < 50:
                p = lt / 50
                pygame.draw.circle(layer, (255, 70, 60, int(35 + 60 * p)), c, RAIN_R)
                pygame.draw.circle(layer, (255, 110, 90, int(70 + 110 * p)), c, max(2, int(RAIN_R * p)))
                pygame.draw.circle(layer, (255, 150, 130, 230), c, RAIN_R, 3)
            elif 50 <= lt < 58:
                pygame.draw.circle(layer, (190, 255, 210, 200 - (lt - 50) * 20), c, RAIN_R)


# --- 서리 거인: 얼음 가시 / 충격파 고리 / 눈덩이 연사 ---
def update_giant(e, to_player, dist, enraged):
    st = e["state"]
    if st == "chase":
        if dist > 80:
            e["pos"] += to_player.normalize() * (1.25 if enraged else 0.85)
        _clamp_boss(e, 50)
        e["cooldown"] -= 1
        if e["cooldown"] <= 0:
            e["atk"] += 1
            a = e["atk"] % 3
            a0 = angle_of(to_player)
            if a == 1:  # 얼음 가시
                e["lanes"] = [a0 - 26, a0, a0 + 26] if enraged else [a0]
                e["dur"] = 30 if enraged else 46
                _go(e, "spike_windup")
            elif a == 2:  # 충격파 고리 (빈틈에 서면 안전)
                e["angle"] = a0
                e["gap"] = 24 if enraged else 30
                e["dur"] = 30 if enraged else 40
                _go(e, "wave_windup")
            else:  # 눈덩이 연사
                e["dur"] = 28
                _go(e, "volley_windup")
    elif st == "spike_windup":
        if e["st_timer"] >= e["dur"]:
            add_shake(3)
            snd_boss.play()
            _go(e, "spikes")
    elif st == "spikes":
        t = e["st_timer"]
        for a in e["lanes"]:
            u = pygame.Vector2(1, 0).rotate(a)
            for i in range(11):
                lt = t - 3 * i
                if lt < 0 or lt >= 16:
                    continue
                p = e["pos"] + u * (70 + 46 * i)
                if lt == 0:
                    spawn_burst(p, (170, 225, 255), 4)
                if p.distance_to(player_pos) < 30 + player_radius:
                    hurt_player(4)
        if t >= 52:
            _go(e, "recover")
    elif st == "wave_windup":
        if e["st_timer"] >= e["dur"]:
            add_shake(7)
            snd_boss.play()
            _go(e, "wave")
    elif st == "wave":
        r = 40 + e["st_timer"] * 6.5
        off = player_pos - e["pos"]
        d = off.length()
        if d > 0 and abs(d - r) < 14 + player_radius * 0.6 and abs(angle_diff(angle_of(off), e["angle"])) > e["gap"]:
            hurt_player(4)
        if r > 600:
            _go(e, "recover")
    elif st == "volley_windup":
        if e["st_timer"] >= e["dur"]:
            _go(e, "volley")
    elif st == "volley":
        t = e["st_timer"]
        if t in ((1, 16, 31, 46) if enraged else (1, 16, 31)):
            n = 7 if enraged else 5
            aim = angle_of(to_player)
            for k in range(n):
                _boss_shot(e["pos"], aim + (k - (n - 1) / 2) * 13, 4.4,
                           color=(125, 205, 255))
            snd_zap.play()
        if t >= (62 if enraged else 48):
            _go(e, "recover")
    elif st == "recover":
        if e["st_timer"] >= (40 if enraged else 60):
            _go(e, "chase")
            e["cooldown"] = 60 if enraged else 90


def _lane_poly(origin, ang, length, half):
    u = pygame.Vector2(1, 0).rotate(ang)
    n = pygame.Vector2(-u.y, u.x)
    b = origin + u * length
    return [origin + n * half, b + n * half, b - n * half, origin - n * half]


def _layer_giant(layer, e):
    st = e["state"]
    pg = _prog(e)
    bp = (int(e["pos"].x), int(e["pos"].y))
    if st in ("spike_windup", "spikes"):
        for a in e["lanes"]:
            poly = _lane_poly(e["pos"], a, 580, 30)
            if st == "spike_windup":
                pygame.draw.polygon(layer, (255, 70, 60, int(35 + 85 * pg)), poly)
                pygame.draw.polygon(layer, (255, 150, 130, 230), poly, 2)
            else:
                pygame.draw.polygon(layer, (255, 70, 60, 35), poly)
                u = pygame.Vector2(1, 0).rotate(a)
                for i in range(11):
                    lt = e["st_timer"] - 3 * i
                    if 0 <= lt < 16:
                        p = e["pos"] + u * (70 + 46 * i)
                        cx, cy = int(p.x), int(p.y)
                        pygame.draw.circle(layer, (150, 215, 255, int(110 + 110 * (1 - lt / 16))), (cx, cy), 30)
                        pygame.draw.polygon(layer, (235, 248, 255, 235),
                                            [(cx - 14, cy + 14), (cx, cy - 36 + int(10 * lt / 16)), (cx + 14, cy + 14)])
    elif st in ("wave_windup", "wave"):
        # 초록 부채꼴 = 안전한 빈틈
        pygame.draw.polygon(layer, (90, 255, 150, 70), wedge_points(e["pos"], e["angle"], e["gap"], 300))
        if st == "wave_windup":
            pygame.draw.circle(layer, (255, 90, 80, int(60 + 120 * pg)), bp, int(40 + 160 * pg), 4)
        else:
            r = 40 + e["st_timer"] * 6.5
            pts = []
            a = e["angle"] + e["gap"]
            while a <= e["angle"] + 360 - e["gap"]:
                pts.append(e["pos"] + pygame.Vector2(r, 0).rotate(a))
                a += 6
            if len(pts) > 1:
                pygame.draw.lines(layer, (150, 215, 255, 220), False, pts, 10)
                pygame.draw.lines(layer, (255, 255, 255, 220), False, pts, 3)
    elif st == "volley_windup":
        pygame.draw.circle(layer, (170, 225, 255, int(40 + 90 * pg)), bp, int(30 + 50 * pg), 4)


# --- 연결: 기존 보스 함수에 새 보스를 끼워 넣어요 ---
_update_boss_new_old = update_boss


def update_boss(e):
    k = e["kind"]
    if k not in BOSS_NEW:
        return _update_boss_new_old(e)
    to_player = player_pos - e["pos"]
    dist = to_player.length()
    if dist == 0:
        to_player = pygame.Vector2(0, 1)
        dist = 1
    enrage_at = 0.80 if e.get("final") else 0.70
    enraged = e["hp"] <= e["max_hp"] * enrage_at
    e["st_timer"] += 1
    if k == "vampire":
        update_vampire(e, to_player, dist, enraged)
    elif k == "lich":
        update_lich(e, to_player, dist, enraged)
    else:
        update_giant(e, to_player, dist, enraged)
    if e["state"].endswith("windup") and (e["st_timer"] // 4) % 2 == 0:
        e["flash"] = 2  # 공격 직전에 번쩍여요


_draw_boss_layer_new_old = draw_boss_layer


def draw_boss_layer(layer, e):
    k = e["kind"]
    if k == "vampire":
        _layer_vampire(layer, e)
    elif k == "lich":
        _layer_lich(layer, e)
    elif k == "frostgiant":
        _layer_giant(layer, e)
    else:
        _draw_boss_layer_new_old(layer, e)
# ============================================================
# # ============================================================
# [추가 패치] 무기 6등급 x 4종 + 초월 등급 + 전 부위 초월 장비
# ============================================================

# 등급별 확률 합계 = 정확히 100%. 초월은 0.01%
RARITY["common"]["w"] = 58.0
RARITY["rare"]["w"] = 28.0
RARITY["epic"]["w"] = 11.0
RARITY["legend"]["w"] = 2.6
RARITY["myth"]["w"] = 0.39
RARITY["transcendent"] = {
    "name": "초월", "color": (95, 255, 225), "w": 0.01
}

if "transcendent" not in RARITY_ORDER:
    RARITY_ORDER.append("transcendent")

rarity_glows["transcendent"] = make_glow(
    100, tuple(int(c * 0.62) for c in RARITY["transcendent"]["color"])
)

# 각 등급 무기는 검 / 활 / 지팡이 / 삼지창 딱 4종입니다.
# 기존 저장 데이터와 호환되도록 예전 장비 데이터는 지우지 않습니다.
_CATALOG_PALETTE = {
    "common": ((170, 125, 70), (245, 205, 135), (85, 55, 32)),
    "rare": ((90, 160, 255), (220, 245, 255), (45, 70, 145)),
    "epic": ((175, 85, 255), (245, 210, 255), (65, 28, 125)),
    "legend": ((255, 165, 40), (255, 245, 160), (130, 48, 18)),
    "myth": ((255, 75, 175), (255, 215, 250), (105, 18, 110)),
    "transcendent": ((40, 235, 220), (250, 255, 255), (95, 45, 220)),
}

_CATALOG_WEAPON_SPECS = [
    # 일반
    ("cat_common_sword", "훈련용 장검", "common", "sword", {"atk": 0.04, "spd": 0.02}),
    ("cat_common_bow", "수습 사냥꾼의 활", "common", "bow", {"spd": 0.08, "crit": 1}),
    ("cat_common_staff", "견습 마력 지팡이", "common", "staff", {"xp": 0.05, "pick": 6}),
    ("cat_common_trident", "갈대 삼지창", "common", "trident", {"atk": 0.06, "gold": 0.03}),

    # 희귀
    ("cat_rare_sword", "은빛 기사검", "rare", "sword", {"atk": 0.10, "spd": 0.04}),
    ("cat_rare_bow", "질풍 사냥활", "rare", "bow", {"spd": 0.12, "crit": 3}),
    ("cat_rare_staff", "수정 지팡이", "rare", "staff", {"xp": 0.08, "spd": 0.04, "start": "번개"}),
    ("cat_rare_trident", "해일 삼지창", "rare", "trident", {"atk": 0.13, "crit": 3}),

    # 영웅
    ("cat_epic_sword", "심연 절단검", "epic", "sword", {"atk": 0.14, "crit": 4, "start": "불꽃검"}),
    ("cat_epic_bow", "월광 장궁", "epic", "bow", {"spd": 0.15, "crit": 5, "start": "관통"}),
    ("cat_epic_staff", "혜성 마도장", "epic", "staff", {"atk": 0.06, "xp": 0.12, "start": "혜성"}),
    ("cat_epic_trident", "폭풍의 삼지창", "epic", "trident", {"atk": 0.16, "spd": 0.05, "start": "번개"}),

    # 전설
    ("cat_legend_sword", "태양의 심판검", "legend", "sword", {"atk": 0.19, "spd": 0.06, "crit": 6, "start": "불꽃검"}),
    ("cat_legend_bow", "천공의 사냥활", "legend", "bow", {"spd": 0.18, "crit": 8, "start": "관통"}),
    ("cat_legend_staff", "별의 창조 지팡이", "legend", "staff", {"atk": 0.11, "xp": 0.16, "start": "시간 정지"}),
    ("cat_legend_trident", "천둥 군주의 삼지창", "legend", "trident", {"atk": 0.22, "crit": 8, "start": "번개"}),

    # 신화
    ("cat_myth_sword", "세계 파괴검", "myth", "sword", {"atk": 0.25, "spd": 0.10, "crit": 10, "start": "혜성"}),
    ("cat_myth_bow", "무한 관통활", "myth", "bow", {"atk": 0.16, "spd": 0.22, "crit": 12, "start": "관통"}),
    ("cat_myth_staff", "공허의 왕홀", "myth", "staff", {"atk": 0.14, "xp": 0.22, "spd": 0.10, "start": "시간 정지"}),
    ("cat_myth_trident", "창세의 삼지창", "myth", "trident", {"atk": 0.27, "hp": 2, "crit": 10, "start": "번개"}),

    # 초월
    ("cat_trans_sword", "초월·종언의 검", "transcendent", "sword", {"atk": 0.38, "spd": 0.18, "crit": 16, "start": "불꽃검"}),
    ("cat_trans_bow", "초월·별을 꿰뚫는 활", "transcendent", "bow", {"atk": 0.25, "spd": 0.32, "crit": 20, "start": "관통"}),
    ("cat_trans_staff", "초월·창세의 지팡이", "transcendent", "staff", {"atk": 0.22, "xp": 0.35, "spd": 0.16, "start": "시간 정지"}),
    ("cat_trans_trident", "초월·만해의 삼지창", "transcendent", "trident", {"atk": 0.42, "hp": 3, "crit": 16, "start": "번개"}),
]

CATALOG_WEAPON_IDS = []

for _key, _name, _rarity, _shape, _stats in _CATALOG_WEAPON_SPECS:
    WEAPONS[_key] = {
        "name": _name,
        "slot": "weapon",
        "rarity": _rarity,
        "shape": _shape,
        "c": _CATALOG_PALETTE[_rarity],
        **_stats
    }
    CATALOG_WEAPON_IDS.append(_key)


# 삼지창 도트 아이콘 추가. 다른 아이콘은 원래 그리는 함수를 그대로 사용합니다.
_make_weapon_icon_before_trident = make_weapon_icon

def make_weapon_icon(shape, colors, scale=3):
    if shape != "trident":
        return _make_weapon_icon_before_trident(shape, colors, scale)

    blade, light, grip = colors
    s = pygame.Surface((16, 16), pygame.SRCALPHA)

    pygame.draw.line(s, grip, (8, 7), (8, 15), 2)
    pygame.draw.line(s, blade, (3, 2), (3, 7), 2)
    pygame.draw.line(s, blade, (8, 1), (8, 7), 2)
    pygame.draw.line(s, blade, (13, 2), (13, 7), 2)
    pygame.draw.line(s, light, (3, 7), (6, 9), 2)
    pygame.draw.line(s, light, (6, 9), (10, 9), 2)
    pygame.draw.line(s, light, (10, 9), (13, 7), 2)
    pygame.draw.line(s, grip, (6, 10), (10, 10), 2)

    icon = outline_surface(s, 1, (16, 12, 28))
    return pygame.transform.scale(
        icon,
        (icon.get_width() * scale, icon.get_height() * scale)
    )


# 삼지창은 창과 같은 근접 공격 규칙을 사용합니다.
if "spear" in MELEE:
    MELEE["trident"] = dict(MELEE["spear"])


# 갑옷 / 장신구 / 룬 / 펫에도 초월 등급 장비를 하나씩 추가합니다.
_items("armor", [
    ("cat_trans_armor", "초월·영원의 수호갑", "transcendent", "armor",
     ((50, 215, 200), (240, 255, 255), (105, 60, 210)),
     {"hp": 5, "atk": 0.25, "inv": 24, "move": 0.35, "start": "보호막"}),
])

_items("acc", [
    ("cat_trans_acc", "초월·무한의 인장", "transcendent", "ring",
     ((80, 230, 220), (250, 255, 255), (150, 70, 225)),
     {"crit": 18, "gold": 0.45, "xp": 0.28, "atk": 0.12}),
])

_items("rune", [
    ("cat_trans_rune", "초월·시공의 룬", "transcendent", "rune",
     ((65, 220, 210), (245, 255, 255), (125, 60, 220)),
     {"atk": 0.28, "spd": 0.20, "move": 0.35, "start": "시간 정지"}),
])

_items("pet", [
    ("cat_trans_pet", "초월·여명룡", "transcendent", "petw",
     ((65, 230, 210), (250, 255, 255), (135, 55, 230)),
     {"pet": True, "pcd": 32, "pshots": 8, "pdmg": 4, "pheal": 600}),
])


# 모든 기존/신규 아이템 인덱스와 등급별 인덱스를 다시 만듭니다.
ALL_ORDER[:] = list(WEAPONS.keys())

WEAPONS_BY_RARITY = {
    _r: [k for k, v in WEAPONS.items() if v.get("rarity") == _r]
    for _r in RARITY_ORDER
}


# 무기 탭은 새 무기 24종만 표시하고, 다른 탭과 기존 저장 장비는 유지합니다.
def set_tab(slot, wid=None):
    global shop_tab, shop_sel

    if slot not in SLOTS:
        slot = "weapon"

    shop_tab = SLOTS.index(slot)

    if slot == "weapon":
        visible_ids = list(CATALOG_WEAPON_IDS)
    else:
        visible_ids = [
            k for k in ALL_ORDER if WEAPONS[k].get("slot") == slot
        ]

    visible_ids.sort(
        key=lambda k: (
            RARITY_ORDER.index(WEAPONS[k]["rarity"]),
            WEAPONS[k]["name"]
        )
    )

    WEAPON_ORDER[:] = visible_ids
    shop_sel = WEAPON_ORDER.index(wid) if wid in WEAPON_ORDER else 0


# 무기 뽑기는 등급마다 정확히 4종만 대상으로 합니다.
# 다른 부위는 전체 장비를 사용합니다.
def _slot_pool(rar, slot):
    if slot == "weapon":
        return [
            k for k in CATALOG_WEAPON_IDS
            if WEAPONS[k]["rarity"] == rar
        ]

    return [
        k for k in WEAPONS_BY_RARITY.get(rar, [])
        if WEAPONS[k].get("slot") == slot
        and k not in ELITE_GEAR_IDS
    ]


def roll_weapon(min_rarity=None, slot=None):
    global pity_by_slot

    slot = slot or SLOTS[shop_tab]

    if slot not in PITY_SLOTS:
        slot = "weapon"

    slot_pity = pity_by_slot.get(slot, 0)

    if slot_pity >= PITY_LIMIT - 1:
        rarity = "legend"
    else:
        rarity = random.choices(
            RARITY_ORDER,
            weights=[RARITY[r]["w"] for r in RARITY_ORDER],
            k=1
        )[0]

    if (
        min_rarity in RARITY_ORDER
        and RARITY_ORDER.index(rarity) < RARITY_ORDER.index(min_rarity)
    ):
        rarity = min_rarity

    rarity_index = RARITY_ORDER.index(rarity)

    while (
        rarity_index > 0
        and not _slot_pool(RARITY_ORDER[rarity_index], slot)
    ):
        rarity_index -= 1

    rarity = RARITY_ORDER[rarity_index]
    pool = _slot_pool(rarity, slot)

    if not pool:
        raise RuntimeError(
            f"등급별 장비 목록이 비어 있습니다: slot={slot}, rarity={rarity}"
        )

    pity_by_slot[slot] = (
        0 if rarity in ("legend", "myth", "transcendent")
        else min(PITY_LIMIT - 1, slot_pity + 1)
    )

    return random.choice(pool)


# 긴 이름은 말줄임표를 붙여 패널/카드 안에 표시합니다.
def _fit_catalog_label(fnt, label, max_width):
    label = str(label)

    if fnt.render(label, True, (255, 255, 255)).get_width() <= max_width:
        return label

    suffix = "…"

    while (
        label
        and fnt.render(label + suffix, True, (255, 255, 255)).get_width() > max_width
    ):
        label = label[:-1]

    return label + suffix if label else suffix


# 1회/10회 뽑기 결과 카드의 긴 무기 이름도 카드 너비 안에 맞춥니다.
_draw_result_card_before_catalog_patch = draw_result_card

def draw_result_card(rect, res, t, big):
    _draw_result_card_before_catalog_patch(rect, res, t, big)

    ease = 1 - (1 - max(0.0, min(1.0, t))) ** 3
    moved_rect = rect.move(0, int((1 - ease) * 40))
    text_y = moved_rect.bottom - (64 if big else 46)

    name = WEAPONS[res["id"]]["name"]
    name_font = small_font if big else tiny_font
    max_width = moved_rect.w - 20

    # 원래 이름 부분을 덮고, 너비에 맞춘 텍스트를 다시 그립니다.
    card_bg = tuple(
        c // 6 + 16
        for c in RARITY[WEAPONS[res["id"]]["rarity"]]["color"]
    )

    pygame.draw.rect(
        screen,
        card_bg,
        (moved_rect.x + 8, text_y - 11, moved_rect.w - 16, 22)
    )

    blit_text(
        screen,
        name_font,
        _fit_catalog_label(name_font, name, max_width),
        (255, 255, 255),
        (moved_rect.centerx, text_y),
        True
    )


# 상점 확률 문구와 긴 무기 이름이 패널 밖으로 나가지 않게 다듬습니다.
_draw_shop_before_catalog_patch = draw_shop_screen

def draw_shop_screen():
    _draw_shop_before_catalog_patch()

    if shop_results or not WEAPON_ORDER:
        return

    selected_id = WEAPON_ORDER[
        max(0, min(shop_sel, len(WEAPON_ORDER) - 1))
    ]
    selected = WEAPONS[selected_id]

    # 기존 이름 줄을 덮고 폭에 맞는 이름으로 다시 그립니다.
    pygame.draw.rect(screen, (24, 26, 46), (35, 268, 270, 36))

    fitted_name = _fit_catalog_label(
        small_font, selected["name"], 258
    )

    blit_text(
        screen, small_font, fitted_name,
        (255, 255, 255), (170, 286), True
    )

    odds_bg = (30, 28, 48)
    pygame.draw.rect(screen, odds_bg, (344, 151, 432, 60))

    blit_text(
        screen, tiny_font,
        "일반 58%  ·  희귀 28%  ·  영웅 11%",
        (170, 180, 210), (560, 158), True
    )

    blit_text(
        screen, tiny_font,
        "전설 2.6%  ·  신화 0.39%  ·  초월 0.01%",
        (170, 180, 210), (560, 175), True
    )

    blit_text(
        screen, tiny_font,
        "10회 뽑기: 희귀 이상 1개 보장",
        (170, 180, 210), (560, 192), True
    )
# ============================================================
# [2단계] 장비 목록 스크롤 + 화면 잘림 방지
# ============================================================

SHOP_GRID_VIEWPORT = pygame.Rect(336, 232, 444, 286)
SHOP_GRID_TOP = 236
SHOP_GRID_COLS = 5
SHOP_GRID_ROW_STEP = 60
SHOP_GRID_CELL_W = 84
SHOP_GRID_CELL_H = 56
shop_scroll_row = 0


def _shop_max_scroll_row():
    rows = (len(WEAPON_ORDER) + SHOP_GRID_COLS - 1) // SHOP_GRID_COLS
    if rows <= 0:
        return 0

    content_bottom = SHOP_GRID_TOP + (rows - 1) * SHOP_GRID_ROW_STEP + SHOP_GRID_CELL_H
    overflow = max(0, content_bottom - SHOP_GRID_VIEWPORT.bottom)
    return (overflow + SHOP_GRID_ROW_STEP - 1) // SHOP_GRID_ROW_STEP


def _shop_clamp_scroll():
    global shop_scroll_row
    shop_scroll_row = max(0, min(shop_scroll_row, _shop_max_scroll_row()))


def _shop_keep_selection_visible():
    global shop_scroll_row

    if not WEAPON_ORDER:
        shop_scroll_row = 0
        return

    selected = max(0, min(shop_sel, len(WEAPON_ORDER) - 1))
    selected_row = selected // SHOP_GRID_COLS

    visible_rows = max(
        1,
        (SHOP_GRID_VIEWPORT.height - SHOP_GRID_CELL_H)
        // SHOP_GRID_ROW_STEP + 1
    )

    if selected_row < shop_scroll_row:
        shop_scroll_row = selected_row
    elif selected_row >= shop_scroll_row + visible_rows:
        shop_scroll_row = selected_row - visible_rows + 1

    _shop_clamp_scroll()


# 스크롤 위치에 따라 장비 카드가 위아래로 이동합니다.
def shop_cell_rects():
    return [
        pygame.Rect(
            340 + (i % SHOP_GRID_COLS) * 88,
            SHOP_GRID_TOP
            + (i // SHOP_GRID_COLS) * SHOP_GRID_ROW_STEP
            - shop_scroll_row * SHOP_GRID_ROW_STEP,
            SHOP_GRID_CELL_W,
            SHOP_GRID_CELL_H
        )
        for i in range(len(WEAPON_ORDER))
    ]


# 목록 영역 밖으로 아이콘과 카드가 그려지지 않게 합니다.
_draw_weapon_cell_before_scroll_patch = draw_weapon_cell


def draw_weapon_cell(rect, wid, selected):
    old_clip = screen.get_clip()
    screen.set_clip(old_clip.clip(SHOP_GRID_VIEWPORT))

    try:
        _draw_weapon_cell_before_scroll_patch(rect, wid, selected)
    finally:
        screen.set_clip(old_clip)


# 무기 / 갑옷 / 장신구 / 룬 / 펫 탭을 바꾸면 목록을 맨 위로 이동합니다.
_set_tab_before_scroll_patch = set_tab


def set_tab(slot, wid=None):
    global shop_scroll_row

    _set_tab_before_scroll_patch(slot, wid)
    shop_scroll_row = 0
    _shop_clamp_scroll()


# 원래 상점 화면은 유지하고 오른쪽에 스크롤 막대를 추가합니다.
_draw_shop_screen_before_scroll_patch = draw_shop_screen


def draw_shop_screen():
    _draw_shop_screen_before_scroll_patch()

    if shop_results or not WEAPON_ORDER:
        return

    max_scroll = _shop_max_scroll_row()
    if max_scroll <= 0:
        return

    track = pygame.Rect(
        784,
        SHOP_GRID_VIEWPORT.y + 2,
        6,
        SHOP_GRID_VIEWPORT.height - 4
    )

    pygame.draw.rect(screen, (38, 40, 61), track, border_radius=3)

    rows = (len(WEAPON_ORDER) + SHOP_GRID_COLS - 1) // SHOP_GRID_COLS
    content_height = max(SHOP_GRID_ROW_STEP, rows * SHOP_GRID_ROW_STEP)

    thumb_h = max(
        24,
        int(track.height * SHOP_GRID_VIEWPORT.height / content_height)
    )
    thumb_h = min(track.height, thumb_h)

    travel = track.height - thumb_h
    thumb_y = track.y + int(
        travel * shop_scroll_row / max_scroll
    )

    thumb = pygame.Rect(track.x, thumb_y, track.width, thumb_h)
    pygame.draw.rect(screen, (180, 145, 255), thumb, border_radius=3)


# 기존 입력 처리를 유지하면서 마우스 휠 스크롤을 추가합니다.
_menu_event_before_scroll_patch = menu_event


def menu_event(event):
    global shop_scroll_row

    if state == "shop" and not shop_results:
        wheel_type = getattr(pygame, "MOUSEWHEEL", -999)

        # 마우스 휠: 목록 위아래 이동
        if event.type == wheel_type:
            mouse_pos = pygame.mouse.get_pos()

            if SHOP_GRID_VIEWPORT.collidepoint(mouse_pos):
                shop_scroll_row -= int(event.y)
                _shop_clamp_scroll()

            return

        # 목록 표시 영역 안에서만 카드 선택
        if event.type == pygame.MOUSEMOTION:
            if not SHOP_GRID_VIEWPORT.collidepoint(event.pos):
                return

        # 표시 영역 밖의 숨겨진 카드가 클릭되는 문제 방지
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and not SHOP_GRID_VIEWPORT.collidepoint(event.pos)
        ):
            protected_rects = [
                BACK_RECT,
                PULL1_RECT,
                PULL10_RECT,
                EQUIP_RECT,
                *TAB_RECTS
            ]

            protected_click = any(
                r.collidepoint(event.pos) for r in protected_rects
            )

            hidden_card_click = any(
                r.collidepoint(event.pos) for r in shop_cell_rects()
            )

            if hidden_card_click and not protected_click:
                return

    # 기존 마우스 / 키보드 / 뽑기 기능 실행
    _menu_event_before_scroll_patch(event)

    # 방향키로 선택한 아이템이 화면 밖으로 나가면 자동 스크롤
    if state == "shop" and not shop_results:
        _shop_keep_selection_visible()     
# 새 장비가 등록됐으니 저장 파일을 다시 읽어요 (안 그러면 새 장비가 사라져요)
# ============================================================
# [패치 4] 직업별 캐릭터 그림 (전사 / 마법사 / 궁수)
# 붙여넣는 곳: [패치 1 통합] 블록 바로 아래 (딱 한 곳!)
# ============================================================
CLS_WARRIOR_PIXELS = [
    "....rrrr....",
    "..dSSSSSSd..",
    ".dSLLSSSSSd.",
    ".dSSSSSSSSd.",
    ".ddkkkkkkdd.",
    ".dkkekkekkd.",
    "..dkkkkkkd..",
    ".gSSSSSSSSg.",
    "kSSSSggSSSSk",
    ".dSSSSSSSSd.",
    "..bbbbbbbb..",
    "..dSSddSSd..",
]
CLS_WARRIOR_COLORS = {
    "d": (40, 30, 40), "S": (150, 160, 185), "L": (225, 232, 248), "r": (225, 60, 55),
    "k": (255, 214, 178), "e": (30, 26, 50), "g": (235, 190, 80), "b": (120, 75, 45),
}

CLS_MAGE_PIXELS = [
    ".....pp.....",
    "....pPPp....",
    "...pPPPPp...",
    "..pPPyyPPp..",
    ".pppppppppp.",
    "..dkkkkkkd..",
    "..dkekkekd..",
    "..dwwwwwwd..",
    ".RRPPwwPPRR.",
    "kRPPPPPPPPRk",
    ".RPPPooPPPR.",
    "..RRRRRRRR..",
]
CLS_MAGE_COLORS = {
    "d": (35, 20, 60), "p": (150, 100, 230), "P": (110, 70, 190), "R": (60, 35, 120),
    "y": (255, 215, 90), "o": (255, 210, 90), "k": (255, 214, 178), "e": (30, 26, 50),
    "w": (240, 240, 250),
}

CLS_ARCHER_PIXELS = [
    "....dddd.rr.",
    "...dGGGGd...",
    "..dGGGGGGd..",
    ".dGGkkkkGGd.",
    ".dGkkkkkkGd.",
    ".dGkekkekGd.",
    "..dGkkkkGd..",
    "..GGGGGGGG..",
    ".kTgTTTTgTk.",
    ".dTTTTTTTTd.",
    "..bbbbbbbb..",
    "..dbbddbbd..",
]
CLS_ARCHER_COLORS = {
    "d": (25, 50, 30), "G": (60, 130, 70), "T": (95, 175, 95), "g": (235, 190, 80),
    "k": (255, 214, 178), "e": (30, 26, 50), "b": (115, 72, 45), "r": (230, 70, 60),
}

# CLASSES 순서(전사, 마법사, 궁수)와 똑같이 맞춰요
CLASS_SPRITES = [
    make_sprite(CLS_WARRIOR_PIXELS, CLS_WARRIOR_COLORS),
    make_sprite(CLS_MAGE_PIXELS, CLS_MAGE_COLORS),
    make_sprite(CLS_ARCHER_PIXELS, CLS_ARCHER_COLORS),
]
# 확장 직업 2종: 기존 직업·장비 시스템과 동일한 능력치 규칙을 사용합니다.
if not any(c.get("name") == "성기사" for c in CLASSES):
    CLASSES.append({
        "name": "성기사", "color": (255, 220, 110), "hp": 2, "atk": -0.05,
        "fire": 1.06, "move": -0.15, "crit": 0, "xp": 0.0, "inv": 12,
        "start": ["보호막"],
        "lines": [("체력 +2", 1), ("보호막으로 시작", 1), ("피격 무적 +0.2초", 1),
                  ("공격력 -5%", 0), ("이동 속도 -0.15", 0)],
        "pal": {"H": (170, 135, 65), "h": (235, 210, 125), "l": (255, 248, 200),
                "n": (205, 165, 55), "N": (110, 78, 25), "r": (110, 150, 225),
                "R": (45, 75, 145), "g": (250, 225, 125), "b": (90, 65, 35)},
    })
if not any(c.get("name") == "암살자" for c in CLASSES):
    CLASSES.append({
        "name": "암살자", "color": (110, 245, 190), "hp": -1, "atk": 0.08,
        "fire": 0.84, "move": 0.45, "crit": 7, "xp": 0.0, "inv": 0,
        "start": ["회피"],
        "lines": [("이동 속도 +0.45", 1), ("공격력 +8%", 1), ("치명타 +7%", 1),
                  ("회피로 시작", 1), ("체력 -1", 0)],
        "pal": {"H": (45, 65, 65), "h": (105, 150, 135), "l": (205, 255, 225),
                "n": (45, 130, 100), "N": (20, 65, 55), "r": (70, 220, 170),
                "R": (25, 105, 85), "g": (190, 245, 160), "b": (55, 45, 40)},
    })
while len(CLASS_SPRITES) < len(CLASSES):
    _new_class = CLASSES[len(CLASS_SPRITES)]
    CLASS_SPRITES.append(make_sprite(HERO_PIXELS, {**HERO_COLORS, **_new_class.get("pal", {})}))

# ------------------------------------------------------------
# 전용 직업 외형: 성기사 / 암살자
# 능력치와 게임 로직은 그대로 두고 캐릭터 도트 그림만 교체합니다.
# 12x12 도트라 기존 전사/마법사/궁수와 크기 및 스타일이 맞습니다.
# ------------------------------------------------------------
CLS_PALADIN_PIXELS = [
    "....GGGG....",
    "...GSSSSG...",
    "..GSSLLSSG..",
    ".GSSSSSSSSG.",
    ".GSSkkkSSSG.",
    "..GkkkkkkG..",
    "..GkekkekG..",
    ".SSGSSSSGSS.",
    "GSSSSWWSSSSG",
    ".GSSSSSSSSG.",
    "..GGG..GGG..",
    "...GG..GG...",
]
CLS_PALADIN_COLORS = {
    "G": (188, 142, 42),   # 금빛 테두리와 장식
    "S": (135, 151, 176), # 은빛 갑옷
    "L": (225, 235, 250), # 갑옷 하이라이트
    "k": (255, 214, 178), # 얼굴
    "e": (30, 26, 50),    # 눈
    "W": (255, 232, 145), # 가슴의 성스러운 문장
}

CLS_ASSASSIN_PIXELS = [
    "....DDDD....",
    "...DCCCCD...",
    "..DCCCCCCD..",
    ".DCCkkkkCCD.",
    ".DCCkEEkCCD.",
    ".DCCMMMMCCD.",
    "..DCCMMCCD..",
    ".dCCMMMMCCd.",
    "cDCCMMCCDDc.",
    ".dDDCCCCDDd.",
    "..BB....BB..",
    "..B......B..",
]
CLS_ASSASSIN_COLORS = {
    "D": (17, 28, 38),     # 어두운 후드 외곽
    "C": (35, 83, 78),     # 청록색 망토와 복장
    "k": (145, 171, 158),  # 얼굴의 어두운 그림자
    "E": (132, 255, 205),  # 밝은 눈빛
    "M": (12, 35, 42),     # 얼굴 가리개
    "d": (7, 15, 23),      # 가장 어두운 윤곽
    "c": (110, 255, 220),  # 양손의 단검 날
    "B": (28, 33, 42),     # 부츠
}

# 직업 이름으로 위치를 찾아 지정하므로 직업 목록 순서가 바뀌어도 안전합니다.
for _class_index, _class_data in enumerate(CLASSES):
    if _class_data.get("name") == "성기사":
        CLASS_SPRITES[_class_index] = make_sprite(CLS_PALADIN_PIXELS, CLS_PALADIN_COLORS)
    elif _class_data.get("name") == "암살자":
        CLASS_SPRITES[_class_index] = make_sprite(CLS_ASSASSIN_PIXELS, CLS_ASSASSIN_COLORS)

# ============================================================
load_save()
apply_class_visuals()
set_tab("weapon")
# ------------------------------------------------------------
# 9) 시작
# ------------------------------------------------------------
# 스테이지별 바닥 그림을 한 번씩만 만들어 둬요 (무한 모드는 1스테이지와 같은 던전)
BG_STYLES.update({
    "grave": {"off": (-6, 0, 10), "moss": (60, 110, 70), "crack": (18, 22, 26)},
    "desert": {"off": (40, 22, -18), "moss": (200, 160, 80), "crack": (110, 80, 40)},
    "swamp": {"off": (-10, 16, -8), "moss": (90, 150, 40), "crack": (30, 50, 20)},
})
STAGE_ACCENT.update({4: (120, 255, 170), 5: (255, 200, 90), 6: (150, 230, 70)})
stage_stats_dummy = None
stage_bgs = {1: make_background("dungeon"), 2: make_background("ice"), 3: make_background("lava"),
             4: make_background("grave"), 5: make_background("desert"), 6: make_background("swamp")}
stage_bgs[0] = stage_bgs[1]
background = stage_bgs[1]  # 메뉴 화면 배경
stage_thumbs = {sid: pygame.transform.smoothscale(bg, (120, 90)) for sid, bg in stage_bgs.items()}
# ============================================================
# [패치 5] 도전 모드 (제한시간 없음, 오래 버티는 심연 맵)
# 붙여넣는 곳: "stage_thumbs = {...}" 줄 바로 아래, "frame_tick = 0" 줄 바로 위 (딱 한 곳!)
# ============================================================
challenge = False  # 지금 도전 모드 중인지
chal_last = 0      # 몇 분 보너스까지 받았는지
chal_best_time = 0
chal_best_kills = 0
CHAL_PATH = os.path.join(BASE_DIR, "challenge.json")


def load_chal():
    global chal_best_time, chal_best_kills
    try:
        with open(CHAL_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        chal_best_time = max(0, int(d.get("time", 0)))
        chal_best_kills = max(0, int(d.get("kills", 0)))
    except (OSError, ValueError, TypeError, AttributeError):
        chal_best_time = chal_best_kills = 0


def save_chal():
    try:
        with open(CHAL_PATH, "w", encoding="utf-8") as f:
            json.dump({"time": chal_best_time, "kills": chal_best_kills}, f)
    except OSError:
        pass


load_chal()

# --- 맵 / 스테이지 정보 (난이도는 여기 숫자만 고치면 돼요) ---
BG_STYLES["abyss"] = {"off": (8, -6, 22), "moss": (90, 50, 140), "crack": (160, 80, 230)}
stage_bgs[7] = make_background("abyss")
stage_thumbs[7] = pygame.transform.smoothscale(stage_bgs[7], (120, 90))
STAGE_ACCENT[7] = (190, 130, 255)
POOL_ABYSS = [("slime", 6, 0), ("goblin", 5, 0), ("bat", 4, 600), ("boar", 3, 1200), ("skeleton", 4, 1800),
              ("mage", 3, 2400), ("jelly", 3, 3000), ("ghost", 3, 3600), ("yeti", 2, 4800),
              ("scorpion", 2, 5400), ("mummy", 2, 6000), ("imp", 3, 7200), ("toad", 2, 8400),
              ("shroom", 2, 9000)]
STAGES[7] = {"name": "도전 모드", "style": "abyss", "pool": POOL_ABYSS, "bosses": None,
             "haz": {"rate": 130, "r": 44, "color": (190, 110, 255), "light": (240, 220, 255)},
             "hp_add": 2, "spd_add": 0.3, "interval": 62, "reward": 0,
             "glow": make_glow(95, (90, 40, 140)), "mote": (190, 130, 255),
             "desc": "시간 제한 없음! 끝없이 강해지는 심연\n오래 버틸수록 골드 보너스 (+50%)"}
STAGE_ORDER.append(7)

# --- 열림 / 시작 ---
_stage_unlocked_old = stage_unlocked


def stage_unlocked(sid):
    return sid == 7 or _stage_unlocked_old(sid)


_start_stage_old = start_stage


def start_stage(sid):
    global challenge, cur_stage
    if sid == 7:  # 도전 모드는 무한 모드(0번)의 규칙을 쓰되, 맵과 난이도만 바꿔요
        challenge = True
        cur_stage = 0
        snd_click.play()
        reset_game()
        return
    challenge = False
    _start_stage_old(sid)


_reset_game_chal = reset_game


def reset_game():
    global cur_def, stage_bg, enemy_speed, enemy_hp, spawn_interval, chal_last
    _reset_game_chal()
    chal_last = 0
    if challenge:
        cur_def = STAGES[7]
        stage_bg = stage_bgs[7]
        enemy_speed = 1.5 + cur_def["spd_add"]
        enemy_hp = 3 + cur_def["hp_add"]
        spawn_interval = cur_def["interval"]


# --- 1분마다 보너스 + 점점 빨라지는 적 생성 ---
def chal_frame():
    global chal_last, spawn_interval, run_gold
    global banner_text, banner_timer, banner_color, banner_blink
    if not challenge or state != "playing" or game_over:
        return
    m = survive_frames // 3600
    if m > chal_last:
        chal_last = m
        bonus = 20 * m
        run_gold += bonus
        spawn_interval = max(10, spawn_interval - 3)
        banner_text = f"{m}분 생존!  +{bonus}G"
        banner_timer = 120
        banner_color = (190, 130, 255)
        banner_blink = False
        snd_level.play()


class _ChalClock:
    def __init__(self, c):
        self._c = c

    def tick(self, *a, **k):
        chal_frame()
        return self._c.tick(*a, **k)

    def __getattr__(self, name):
        return getattr(self._c, name)


clock = _ChalClock(clock)

# --- 끝났을 때: 기록은 따로 저장하고, 골드는 50% 더 줘요 ---
_end_game_chal = end_game


def end_game(cleared=False):
    global best_time, best_kills, new_record, gold, last_gain, last_bonus
    global chal_best_time, chal_best_kills
    if not challenge:
        _end_game_chal(cleared)
        return
    keep_t, keep_k = best_time, best_kills  # 무한 모드 기록은 건드리지 않아요
    _end_game_chal(cleared)
    best_time, best_kills = keep_t, keep_k
    secs = survive_frames // 60
    new_record = secs > chal_best_time
    chal_best_time = max(chal_best_time, secs)
    chal_best_kills = max(chal_best_kills, kills)
    extra = last_gain // 2
    gold += extra
    last_gain += extra
    last_bonus += extra
    save_chal()
    save_game()


_draw_game_over_chal = draw_game_over


def draw_game_over():
    global best_time
    if challenge:  # 결과 화면의 '최고 기록'을 도전 모드 기록으로 보여줘요
        keep = best_time
        best_time = chal_best_time
        try:
            _draw_game_over_chal()
        finally:
            best_time = keep
    else:
        _draw_game_over_chal()


# --- 스테이지 선택 카드 글씨 덮어쓰기 ---
_draw_stage_select_chal = draw_stage_select


def draw_stage_select():
    _draw_stage_select_chal()
    page = stage_sel // 4
    for i, (sid, rect) in enumerate(zip(STAGE_ORDER[page * 4:page * 4 + 4], stage_card_rects()), page * 4):
        if sid != 7:
            continue
        bgc = (50, 56, 94) if i == stage_sel else (34, 38, 64)
        pygame.draw.rect(screen, bgc, (rect.x + 12, rect.y + 10, 130, 24))
        pygame.draw.rect(screen, bgc, (rect.x + 146, rect.y + 80, 224, 26))
        blit_text(screen, tiny_font, "CHALLENGE", STAGE_ACCENT[7], (rect.x + 16, rect.y + 14))
        info = f"최고 기록 {mmss(chal_best_time)}" if chal_best_time > 0 else "기록 없음"
        blit_text(screen, tiny_font, info, (255, 230, 120) if chal_best_time > 0 else (185, 195, 225),
                  (rect.x + 150, rect.y + 84))
# ============================================================
frame_tick = 0  # 화면 애니메이션용 (게임 시간과 별개로 계속 올라가요)
facing_left = False   # 주인공이 왼쪽을 보고 있는지
hero_walking = False  # 걷는 중인지 (걷는 애니메이션용)
reset_game()
state = "title"  # 처음엔 타이틀 화면에서 시작

running = True
# Boss encounters pause the ordinary battlefield and use two full health bars.
_spawn_boss_two_bar_old = spawn_boss
def spawn_boss(kind, hp_scale=None, final=False):
    global spawn_timer, enemy_shots, fires, meteors
    previous_ids = {id(enemy) for enemy in enemies}
    _spawn_boss_two_bar_old(kind, hp_scale, final)
    boss = next((enemy for enemy in reversed(enemies)
                 if enemy.get("boss") and id(enemy) not in previous_ids), None)
    if boss is None:
        return
    boss["hp"] = max(1, int(boss["hp"])) * 2
    boss["max_hp"] = max(1, int(boss["max_hp"])) * 2
    boss["boss_health_bars"] = 2
    boss["phase_two"] = False
    boss["phase_skill_timer"] = 0
    enemies[:] = [enemy for enemy in enemies if enemy.get("boss")]
    enemy_shots.clear()
    fires.clear()
    meteors.clear()
    spawn_timer = 0

_damage_enemy_two_bar_old = damage_enemy
def damage_enemy(e, dmg, quiet=False):
    global banner_text, banner_timer, banner_color, banner_blink
    _damage_enemy_two_bar_old(e, dmg, quiet)
    if (e.get("boss") and not e.get("mini_boss") and e.get("hp", 0) > 0
            and not e.get("phase_two") and e["hp"] <= e["max_hp"] / 2):
        e["phase_two"] = True
        e["phase_skill_timer"] = 42
        e["cooldown"] = min(e.get("cooldown", 45), 24)
        rings.append({"pos": e["pos"].copy(), "r": 145, "life": 42, "max": 42,
                      "color": (255, 100, 85)})
        spawn_burst(e["pos"], (255, 130, 90), 18)
        banner_text = "분노! {} 2단계".format(BOSS_NAMES[e["kind"]])
        banner_timer = 110
        banner_color = (255, 110, 90)
        banner_blink = True
        snd_boss.play()
        add_shake(8)

_update_boss_two_bar_old = update_boss
def update_boss(e):
    timer = e.get("phase_skill_timer", 0)
    if timer > 0:
        timer -= 1
        e["phase_skill_timer"] = timer
        if timer == 0:
            count = 16 if e.get("final") else 14
            speed = 4.3 if e.get("final") else 3.8
            base = random.uniform(0, 360)
            for i in range(count):
                _boss_shot(e["pos"], base + 360 * i / count, speed,
                           color=enemy_types[e["kind"]]["color"])
            aim = angle_of(player_pos - e["pos"])
            for offset in (-12, 0, 12):
                _boss_shot(e["pos"], aim + offset, speed + 0.4,
                           color=enemy_types[e["kind"]]["color"])
            rings.append({"pos": e["pos"].copy(), "r": 165, "life": 18, "max": 18,
                          "color": enemy_types[e["kind"]]["color"]})
            spawn_burst(e["pos"], enemy_types[e["kind"]]["color"], 22)
            snd_zap.play()
            add_shake(7)
        return
    _update_boss_two_bar_old(e)

_draw_boss_two_bar_old = draw_boss_layer
def draw_boss_layer(layer, e):
    _draw_boss_two_bar_old(layer, e)
    timer = e.get("phase_skill_timer", 0)
    if timer > 0:
        progress = 1 - timer / 42
        radius = int(34 + 130 * progress)
        alpha = int(90 + 135 * progress)
        center = (int(e["pos"].x), int(e["pos"].y))
        color = enemy_types[e["kind"]]["color"]
        pygame.draw.circle(layer, (*color, alpha), center, radius, 4)
        pygame.draw.circle(layer, (255, 245, 220, min(220, alpha)), center,
                           max(8, int(14 + 26 * progress)), 2)


ALTAR_CARD_RECTS = [
    pygame.Rect(WIDTH // 2 - 322, HEIGHT // 2 - 24, 310, 172),
    pygame.Rect(WIDTH // 2 + 12, HEIGHT // 2 - 24, 310, 172),
]

def resolve_altar(choice):
    global altar_pos, altar_used, state, dmg_mult, player_hp, player_max_hp
    global banner_text, banner_color, banner_timer, banner_blink
    if state != "altar_choice" or altar_used:
        return
    altar_pos = None
    altar_used = True
    state = "playing"
    if choice == 0:
        dmg_mult += 0.10
        player_hp = min(player_max_hp, player_hp + 1)
        banner_text = "축복: 공격력 +10%, 체력 +1"
        banner_color = (150, 255, 180)
    else:
        dmg_mult += 0.30
        player_max_hp = max(1, player_max_hp - 1)
        player_hp = min(player_hp, player_max_hp)
        banner_text = "피의 계약: 공격력 +30%, 최대 체력 -1"
        banner_color = (255, 125, 115)
    banner_timer = 100
    banner_blink = False
    snd_level.play()


def draw_altar_choice():
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((6, 8, 18, 205))
    screen.blit(shade, (0, 0))
    panel = pygame.Rect(WIDTH // 2 - 350, HEIGHT // 2 - 185, 700, 370)
    pixel_panel(screen, panel, (225, 190, 100), (28, 28, 45), n=8, bw=4)
    blit_text(screen, font, "고대 제단", (255, 225, 145), (WIDTH // 2, panel.y + 42), True)
    blit_text(screen, small_font, "보상과 대가 중 하나를 고르세요", (215, 220, 240),
              (WIDTH // 2, panel.y + 88), True)
    card_colors = [(120, 235, 170), (255, 125, 110)]
    titles = ["수호의 축복", "피의 계약"]
    lines = [
        ("공격력 +10%", "체력 1 회복", "1 키 또는 클릭"),
        ("공격력 +30%", "최대 체력 -1", "2 키 또는 클릭"),
    ]
    for rect, color, title, detail in zip(ALTAR_CARD_RECTS, card_colors, titles, lines):
        pixel_panel(screen, rect, color, (34, 38, 58), n=6, bw=3)
        blit_text(screen, small_font, title, color, (rect.centerx, rect.y + 30), True)
        blit_text(screen, tiny_font, detail[0], (235, 238, 250), (rect.centerx, rect.y + 72), True)
        blit_text(screen, tiny_font, detail[1], (235, 238, 250), (rect.centerx, rect.y + 98), True)
        blit_text(screen, tiny_font, detail[2], (180, 190, 220), (rect.centerx, rect.y + 138), True)
    blit_text(screen, tiny_font, "ESC: 지나가기", (175, 185, 215),
              (WIDTH // 2, panel.bottom - 18), True)


# ============================================================
# [확장 업데이트] 스킬 진화 / 상태 이상 / 궁극기 / 보스 러시
# 일일·주간 임무 / 도감 / 장비 제작 / 설정 / 전투 통계 / 확장 저장
# ============================================================
from datetime import date as _feature_date

# 스킬 진화 2종을 추가합니다. 기존 시너지 판정·레벨업 카드 흐름을 그대로 사용합니다.
SKILL_EVOLUTIONS.update({
    "유성 폭격": {"skills": ("혜성", "별빛 난사"), "synergy": "유성 파편", "min_level": 4,
                  "color": (255, 220, 120), "desc": "진화: 운석 폭발 범위·피해 증가, 별빛 파편 추가 발사",
                  "preview": "운석 범위 108 · 파편 5~8발"},
    "영혼 폭주": {"skills": ("영혼 사슬", "연쇄 집중"), "synergy": "영혼 공명", "min_level": 4,
                  "color": (210, 155, 255), "desc": "진화: 콤보에 따라 영혼 사슬 피해·연쇄 수 증가",
                  "preview": "콤보에 따라 연쇄 최대 +4 · 피해 증가"},
})
for _evo_name, _evo_data in SKILL_EVOLUTIONS.items():
    upgrades[_evo_name] = _evo_data["desc"]
    if _evo_name not in upgrade_style:
        _evo_pixels = STORM_PIXELS if _evo_name == "영혼 폭주" else BLAST_PIXELS
        _evo_colors = ({"c": (170, 110, 255), "y": (245, 220, 255)}
                       if _evo_name == "영혼 폭주" else
                       {"r": (255, 170, 70), "o": (255, 220, 120), "y": (255, 250, 210)})
        upgrade_style[_evo_name] = {"icon": make_sprite(_evo_pixels, _evo_colors, 5), "color": _evo_data["color"]}
        small_icons[_evo_name] = pygame.transform.scale(upgrade_style[_evo_name]["icon"], (24, 24))

# 저주는 지원 스킬로서 약화 상태 이상을 부여합니다. 기존 스킬 슬롯 시스템을 사용합니다.
if "저주" not in NEW_SKILLS:
    NEW_SKILLS["저주"] = {
        "desc": "공격한 적을 약화해\n이동 속도를 낮춰요", "max": 5,
        "color": (190, 125, 255),
        "icon": (STORM_PIXELS, {"c": (165, 105, 240), "y": (235, 195, 255)}),
        "prev": lambda lv: f"약화 확률 {12 * (lv + 1)}% · 지속 2.5초"
    }
    upgrades["저주"] = NEW_SKILLS["저주"]["desc"]
    upgrade_names.append("저주")
    SUPPORT_SKILLS.add("저주")
    upgrade_style["저주"] = {
        "icon": make_sprite(NEW_SKILLS["저주"]["icon"][0], NEW_SKILLS["저주"]["icon"][1], 5),
        "color": NEW_SKILLS["저주"]["color"]
    }
    small_icons["저주"] = pygame.transform.scale(upgrade_style["저주"]["icon"], (24, 24))

# 추가 공격 스킬 2종: 중력장과 성광. 수치 상한은 NEW_SKILLS의 max=5로 관리합니다.
_FEATURE_ADDED_SKILLS = {
    "중력장": {"desc": "주변 적을 끌어당기며\n작은 광역 피해", "max": 5,
               "color": (165, 120, 255),
               "icon": (AURA_PIXELS, {"o": (145, 90, 230), "p": (225, 205, 255)}),
               "prev": lambda lv: f"범위 {132 + 12 * lv} · 주기 {max(190, 300 - 22 * (lv + 1)) / 60:.1f}초"},
    "성광": {"desc": "가까운 적에게 빛을\n연쇄 발사", "max": 5,
             "color": (255, 225, 125),
             "icon": (STORM_PIXELS, {"c": (255, 220, 100), "y": (255, 250, 205)}),
             "prev": lambda lv: f"연쇄 {3 + lv}명 · 주기 {max(170, 260 - 18 * (lv + 1)) / 60:.1f}초"},
}
for _skill_name, _skill_data in _FEATURE_ADDED_SKILLS.items():
    if _skill_name not in NEW_SKILLS:
        NEW_SKILLS[_skill_name] = _skill_data
    upgrades[_skill_name] = _skill_data["desc"]
    if _skill_name not in upgrade_names:
        upgrade_names.append(_skill_name)
    ATTACK_SKILLS.add(_skill_name)
    SUPPORT_SKILLS.discard(_skill_name)
    if _skill_name not in upgrade_style:
        _spr = make_sprite(_skill_data["icon"][0], _skill_data["icon"][1], 5)
        upgrade_style[_skill_name] = {"icon": _spr, "color": _skill_data["color"]}
        small_icons[_skill_name] = pygame.transform.scale(_spr, (24, 24))

# 새로운 몬스터 4종: 소환사, 암살자, 방패병, 분열 슬라임.
SUMMONER_PIXELS = ["....pppp....", "...pddddp...", "..pdwyywdp..", "..pdkwwkdp..",
                   "...pddddp...", ".pppppppppp.", ".pddp..pddp.", "..pp....pp.."]
ASSASSIN_PIXELS = ["....dddd....", "...dkkkkd...", "..dkdwwdkd..", "..dkkkkkkd..",
                   "...drrrrd...", "..drrrrrrd..", "..dd....dd..", ".dd......dd."]
GUARD_PIXELS = ["....dddd....", "...dggggd...", "..dgwwwwgd..", "..dggggggd..",
                ".dddbbbddd..", ".dgbbbbbgd..", ".dgbbdbbgd..", "..dd....dd.."]
SPLIT_SLIME_PIXELS = ["............", "....dddd....", "...dggggd...", "..dgllgggd..",
                      ".dgggkkgggd.", "dggggggggggd", "dggggggggggd", ".dddddddddd."]

enemy_types.update({
    "summoner": {"speed": 0.65, "hp_bonus": 3, "radius": 15, "color": (180, 105, 240),
                 "sprite": make_sprite(SUMMONER_PIXELS, {"d": (45, 25, 70), "p": (145, 70, 200),
                 "w": (245, 240, 255), "y": (255, 210, 90)}), "shot_color": (200, 120, 255)},
    "assassin": {"speed": 1.7, "hp_bonus": 1, "radius": 12, "color": (210, 75, 100),
                 "sprite": make_sprite(ASSASSIN_PIXELS, {"d": (35, 20, 35), "k": (90, 55, 90),
                 "w": (245, 230, 245), "r": (255, 65, 90)})},
    "shield_guard": {"speed": 0.75, "hp_bonus": 5, "radius": 17, "color": (100, 160, 220),
                     "sprite": make_sprite(GUARD_PIXELS, {"d": (35, 45, 70), "g": (100, 145, 195),
                     "w": (220, 240, 255), "b": (55, 80, 120)})},
    "split_slime": {"speed": 0.85, "hp_bonus": 2, "radius": 16, "color": (115, 220, 130),
                    "sprite": make_sprite(SPLIT_SLIME_PIXELS, {"d": (35, 100, 55), "g": (100, 205, 110),
                    "l": (205, 255, 205), "k": (25, 45, 30)})},
})
for _kind in ("summoner", "assassin", "shield_guard", "split_slime"):
    enemy_types[_kind]["flash"] = make_flash(enemy_types[_kind]["sprite"])
    enemy_types[_kind]["frost"] = make_tint(enemy_types[_kind]["sprite"], (30, 80, 150))
CHARGERS.add("assassin")
SHOOTERS.add("summoner")
GOLD_VALUE.update({"summoner": 5, "assassin": 4, "shield_guard": 5, "split_slime": 3})
# 서로 다른 스테이지에 배치합니다. 기존 스테이지·스폰 풀은 그대로 유지합니다.
STAGES[1]["pool"].append(("summoner", 2, 2700))
STAGES[4]["pool"].append(("assassin", 3, 2400))
STAGES[5]["pool"].append(("shield_guard", 3, 1800))
STAGES[6]["pool"].append(("split_slime", 4, 1500))
if 7 in STAGES:
    STAGES[7]["pool"].extend([("summoner", 2, 2100), ("assassin", 2, 3000),
                              ("shield_guard", 2, 4200), ("split_slime", 3, 1200)])

# 신규 스테이지 8~9: 후반 성장 이후 도전하도록 해금 순서를 제한합니다.
BG_STYLES.update({
    "crystal": {"off": (8, 18, 34), "moss": (80, 140, 185), "crack": (105, 180, 255)},
    "sky": {"off": (24, 16, 30), "moss": (175, 140, 95), "crack": (130, 100, 180)},
})
stage_bgs[8] = make_background("crystal")
stage_bgs[9] = make_background("sky")
stage_thumbs[8] = pygame.transform.smoothscale(stage_bgs[8], (120, 90))
stage_thumbs[9] = pygame.transform.smoothscale(stage_bgs[9], (120, 90))
STAGE_ACCENT.update({8: (110, 205, 255), 9: (255, 205, 130)})
STAGES[8] = {
    "name": "수정 심연", "style": "crystal",
    "pool": [("ice_wisp", 6, 0), ("frost_wolf", 5, 450), ("ice_mage", 4, 900),
             ("summoner", 2, 1200), ("assassin", 3, 1600), ("yeti", 3, 2200)],
    "bosses": [("lich", 4200, 2.5), ("frostgiant", 9000, 2.8), ("vampire", 14400, 3.1)],
    "haz": {"rate": 88, "r": 45, "color": (105, 195, 255), "light": (220, 245, 255)},
    "hp_add": 6, "spd_add": 0.85, "interval": 47, "reward": 2800,
    "glow": make_glow(105, (40, 120, 200)), "mote": (140, 205, 255),
    "desc": "수정 폭풍과 얼음 정령을 돌파하세요\n리치 → 서리 거인 → 흡혈 군주",
}
STAGES[9] = {
    "name": "천공의 심판", "style": "sky",
    "pool": [("ghost", 5, 0), ("imp", 5, 300), ("shield_guard", 3, 600),
             ("assassin", 4, 900), ("summoner", 4, 1400), ("split_slime", 4, 1700),
             ("fire_mage", 3, 2200)],
    "bosses": [("frostgiant", 3600, 3.0), ("lich", 7800, 3.3), ("vampire", 12600, 3.7)],
    "haz": {"rate": 82, "r": 48, "color": (205, 145, 255), "light": (255, 235, 190)},
    "hp_add": 8, "spd_add": 1.0, "interval": 44, "reward": 3800,
    "glow": make_glow(110, (145, 85, 190)), "mote": (235, 195, 255),
    "desc": "정예 적과 강화 보스가 몰려옵니다\n서리 거인 → 리치 → 흡혈 군주",
}
for _sid in (8, 9):
    if _sid not in STAGE_ORDER:
        STAGE_ORDER.append(_sid)
BOSS_NAMES.update({"vampire": "흡혈 군주", "lich": "리치", "frostgiant": "서리 거인"})


# Settings and new persistent state.
FEATURE_SAVE_VERSION = 1
feature_settings = {
    "volume": 0.70,
    "music_volume": 0.28,
    "screen_shake": True,
    "damage_numbers": True,
    "dash_key": pygame.K_SPACE,
    "ult1_key": pygame.K_q,
    "ult2_key": pygame.K_e,
}
feature_codex_kills = {}
feature_discovered_items = set(weapon_stars.keys())
feature_materials = 0
feature_item_enhancements = {}
feature_item_potentials = {}
feature_item_dyes = {}
feature_original_weapon_colors = {wid: data["c"] for wid, data in WEAPONS.items()}
feature_current_damage_source = "기본 공격"
feature_damage_by_source = {}
feature_missions = {"daily_stamp": "", "weekly_stamp": "", "daily": [], "weekly": [], "weekly_classes": []}
feature_stats = {"runs": 0, "total_kills": 0, "total_damage": 0, "boss_damage": 0,
                 "best_kills": 0, "best_survival": 0, "best_boss_rush": 0}
feature_last_run = {}
feature_run_damage = 0
feature_run_boss_damage = 0
feature_ultimate_charge = 0.0
feature_ultimate_q_cd = 0
feature_ultimate_e_cd = 0
feature_ultimate_shield_timer = 0
feature_status_tick = False
feature_boss_rush_active = False
feature_boss_rush_round = 0
feature_boss_rush_timer = 0
feature_boss_rush_complete = False
feature_boss_rush_finish_pending = False
feature_boss_rush_best = 0
feature_starting_boss_rush = False
feature_menu_index = 0
feature_page = "hub"
feature_settings_index = 0
feature_rebind_target = None
feature_codex_category = 0
feature_codex_index = 0
feature_craft_index = 0
feature_button_rects = {}
feature_reward_toast_cooldown = 0

FEATURE_HUB_ITEMS = [
    ("설정", "settings"), ("도감", "codex"), ("일일·주간 임무", "missions"),
    ("장비 제작·분해", "craft"), ("전투 통계", "stats"), ("보스 러시 시작", "boss_rush")
]
FEATURE_DAILY_POOL = [
    ("kills", "몬스터 200마리 처치", 200, 150, 2),
    ("gems", "경험치 구슬 100개 획득", 100, 150, 2),
    ("pulls", "장비 뽑기 3회", 3, 200, 3),
    ("clears", "스테이지 1회 클리어", 1, 250, 3),
    ("bosses", "보스 2마리 처치", 2, 220, 3),
    ("elites", "엘리트 5마리 처치", 5, 180, 2),
]
FEATURE_WEEKLY_POOL = [
    ("kills", "몬스터 1000마리 처치", 1000, 700, 8),
    ("bosses", "보스 10마리 처치", 10, 800, 10),
    ("distinct_classes", "서로 다른 직업으로 클리어", 3, 900, 12),
    ("advanced_clear", "스테이지 4~6 클리어", 3, 850, 10),
    ("pulls", "장비 뽑기 15회", 15, 600, 8),
]

def feature_period_stamps():
    today = _feature_date.today()
    iso = today.isocalendar()
    return today.isoformat(), f"{iso.year}-W{iso.week:02d}"

def _feature_build_tasks(pool, stamp, prefix, count):
    rng = random.Random(f"SURVIVOR:{prefix}:{stamp}")
    chosen = rng.sample(pool, min(count, len(pool)))
    return [{"key": k, "name": name, "goal": goal, "progress": 0,
             "reward_gold": gold_reward, "reward_mat": mat_reward, "claimed": False}
            for k, name, goal, gold_reward, mat_reward in chosen]

def feature_ensure_missions():
    daily_stamp, weekly_stamp = feature_period_stamps()
    if feature_missions.get("daily_stamp") != daily_stamp:
        feature_missions["daily_stamp"] = daily_stamp
        feature_missions["daily"] = _feature_build_tasks(FEATURE_DAILY_POOL, daily_stamp, "daily", 3)
    if feature_missions.get("weekly_stamp") != weekly_stamp:
        feature_missions["weekly_stamp"] = weekly_stamp
        feature_missions["weekly"] = _feature_build_tasks(FEATURE_WEEKLY_POOL, weekly_stamp, "weekly", 3)
        feature_missions["weekly_classes"] = []
        feature_missions["weekly_advanced_stages"] = []
    if not isinstance(feature_missions.get("daily"), list):
        feature_missions["daily"] = _feature_build_tasks(FEATURE_DAILY_POOL, daily_stamp, "daily", 3)
        feature_missions["daily_stamp"] = daily_stamp
    if not isinstance(feature_missions.get("weekly"), list):
        feature_missions["weekly"] = _feature_build_tasks(FEATURE_WEEKLY_POOL, weekly_stamp, "weekly", 3)
        feature_missions["weekly_stamp"] = weekly_stamp
    if not isinstance(feature_missions.get("weekly_classes"), list):
        feature_missions["weekly_classes"] = []
    if not isinstance(feature_missions.get("weekly_advanced_stages"), list):
        feature_missions["weekly_advanced_stages"] = []

def feature_load_extra():
    global feature_settings, feature_codex_kills, feature_discovered_items
    global feature_materials, feature_missions, feature_stats, feature_last_run, feature_boss_rush_best
    global feature_item_enhancements, feature_item_potentials, feature_item_dyes
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        data = raw.get("feature", {}) if isinstance(raw, dict) else {}
        if not isinstance(data, dict):
            data = {}
        saved_settings = data.get("settings", {})
        if isinstance(saved_settings, dict):
            for key in ("screen_shake", "damage_numbers"):
                if isinstance(saved_settings.get(key), bool):
                    feature_settings[key] = saved_settings[key]
            try:
                feature_settings["volume"] = max(0.0, min(1.0, float(saved_settings.get("volume", 0.70))))
                feature_settings["music_volume"] = max(0.0, min(1.0, float(saved_settings.get("music_volume", 0.28))))
            except (TypeError, ValueError):
                pass
            for key, default in (("dash_key", pygame.K_SPACE), ("ult1_key", pygame.K_q), ("ult2_key", pygame.K_e)):
                value = saved_settings.get(key, default)
                if isinstance(value, int) and value >= 0:
                    feature_settings[key] = value
        raw_codex = data.get("codex_kills", {})
        if isinstance(raw_codex, dict):
            feature_codex_kills = {str(k): max(0, int(v)) for k, v in raw_codex.items()
                                   if isinstance(v, (int, float)) and v >= 0}
        raw_items = data.get("discovered_items", [])
        if isinstance(raw_items, list):
            feature_discovered_items = {str(x) for x in raw_items if str(x) in WEAPONS}
        feature_discovered_items.update(k for k in weapon_stars if k in WEAPONS)
        feature_materials = max(0, int(data.get("materials", 0)))
        raw_enh = data.get("item_enhancements", {})
        if isinstance(raw_enh, dict):
            feature_item_enhancements = {str(k): max(0, min(10, int(v))) for k, v in raw_enh.items()
                                         if str(k) in WEAPONS and isinstance(v, (int, float))}
        raw_potentials = data.get("item_potentials", {})
        if isinstance(raw_potentials, dict):
            valid_stats = {"atk", "spd", "crit", "hp", "xp", "gold", "move", "pick"}
            feature_item_potentials = {}
            for k, v in raw_potentials.items():
                if str(k) in WEAPONS and isinstance(v, dict) and v.get("stat") in valid_stats:
                    try:
                        feature_item_potentials[str(k)] = {"stat": v["stat"], "value": float(v["value"]),
                                                           "name": str(v.get("name", v["stat"]))}
                    except (TypeError, ValueError):
                        pass
        raw_dyes = data.get("item_dyes", {})
        if isinstance(raw_dyes, dict):
            feature_item_dyes = {str(k): max(0, min(5, int(v))) for k, v in raw_dyes.items()
                                 if str(k) in WEAPONS and isinstance(v, (int, float))}
        raw_missions = data.get("missions", {})
        if isinstance(raw_missions, dict):
            feature_missions = raw_missions
        raw_stats = data.get("stats", {})
        if isinstance(raw_stats, dict):
            for key in feature_stats:
                try:
                    feature_stats[key] = max(0, int(raw_stats.get(key, feature_stats[key])))
                except (TypeError, ValueError):
                    pass
        raw_last = data.get("last_run", {})
        if isinstance(raw_last, dict):
            feature_last_run = raw_last
        feature_boss_rush_best = feature_stats.get("best_boss_rush", 0)
    except (OSError, ValueError, TypeError, AttributeError):
        feature_discovered_items.update(k for k in weapon_stars if k in WEAPONS)
    feature_ensure_missions()
    feature_set_volume()

def feature_save_payload():
    feature_ensure_missions()
    return {
        "version": FEATURE_SAVE_VERSION,
        "settings": feature_settings,
        "codex_kills": feature_codex_kills,
        "discovered_items": sorted(feature_discovered_items),
        "materials": feature_materials,
        "item_enhancements": feature_item_enhancements,
        "item_potentials": feature_item_potentials,
        "item_dyes": feature_item_dyes,
        "missions": feature_missions,
        "stats": feature_stats,
        "last_run": feature_last_run,
    }

_feature_original_save_game = save_game

def save_game():
    _feature_original_save_game()
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
        data["feature"] = feature_save_payload()
        tmp = SAVE_PATH + ".feature.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, SAVE_PATH)
    except (OSError, ValueError, TypeError):
        # 게임 진행을 저장 실패 때문에 중단하지 않아요.
        pass

_feature_original_load_save = load_save

def load_save():
    _feature_original_load_save()
    feature_load_extra()

# 현재 세션 데이터는 음량 설정 함수 정의가 끝난 뒤 읽어들입니다.

# 음량 변경을 기존 효과음 전체에 반영합니다.
def feature_set_volume():
    volume = max(0.0, min(1.0, float(feature_settings.get("volume", 0.70))))
    seen = set()
    for name, sound_obj in list(globals().items()):
        if not name.startswith("snd_"):
            continue
        sounds = getattr(sound_obj, "sounds", None)
        targets = list(sounds) if sounds is not None else [sound_obj]
        for sound in targets:
            if sound is None or id(sound) in seen:
                continue
            if not hasattr(sound, "set_volume"):
                continue
            seen.add(id(sound))
            try:
                sound.set_volume(volume)
            except (AttributeError, pygame.error):
                pass

def feature_mission_reward(task):
    global gold, feature_materials
    if task.get("claimed") or task.get("progress", 0) < task.get("goal", 1):
        return
    task["claimed"] = True
    gold += int(task.get("reward_gold", 0))
    feature_materials += int(task.get("reward_mat", 0))
    show_toast(f"임무 완료! +{task.get('reward_gold', 0)}G · 재료 +{task.get('reward_mat', 0)}",
               (150, 255, 180))
    snd_level.play()
    save_game()

def feature_record_event(metric, amount=1):
    if amount <= 0:
        return
    feature_ensure_missions()
    for group in (feature_missions.get("daily", []), feature_missions.get("weekly", [])):
        for task in group:
            if task.get("key") == metric and not task.get("claimed"):
                old = int(task.get("progress", 0))
                task["progress"] = min(int(task.get("goal", 1)), old + int(amount))
                if task["progress"] >= task.get("goal", 1):
                    feature_mission_reward(task)

def feature_record_distinct_class(class_name):
    feature_ensure_missions()
    seen = feature_missions.setdefault("weekly_classes", [])
    if class_name not in seen:
        seen.append(class_name)
        for task in feature_missions.get("weekly", []):
            if task.get("key") == "distinct_classes" and not task.get("claimed"):
                task["progress"] = min(task.get("goal", 3), len(seen))
                if task["progress"] >= task.get("goal", 3):
                    feature_mission_reward(task)

def feature_record_advanced_stage(stage_id):
    feature_ensure_missions()
    if stage_id not in (4, 5, 6):
        return
    seen = feature_missions.setdefault("weekly_advanced_stages", [])
    if stage_id not in seen:
        seen.append(stage_id)
        for task in feature_missions.get("weekly", []):
            if task.get("key") == "advanced_clear" and not task.get("claimed"):
                task["progress"] = min(task.get("goal", 3), len(seen))
                if task["progress"] >= task.get("goal", 3):
                    feature_mission_reward(task)

def feature_set_mission_counter(metric, value):
    feature_ensure_missions()
    for task in feature_missions.get("weekly", []):
        if task.get("key") == metric and not task.get("claimed"):
            task["progress"] = min(task.get("goal", value), max(task.get("progress", 0), int(value)))
            if task["progress"] >= task.get("goal", 1):
                feature_mission_reward(task)

def feature_mission_lists():
    feature_ensure_missions()
    return feature_missions.get("daily", []), feature_missions.get("weekly", [])

# Track newly found equipment from the existing summon system.
_feature_original_do_pull = do_pull
def do_pull(n):
    before_gold = gold
    before = set(weapon_stars)
    _feature_original_do_pull(n)
    # A successful pull always spends net gold (even when a max-star duplicate refunds some).
    if gold >= before_gold:
        return
    new_owned = set(weapon_stars) - before
    feature_discovered_items.update(new_owned)
    # All pulled gear counts toward the discovered part of the codex.
    feature_discovered_items.update(item.get("id") for item in shop_results if item.get("id") in WEAPONS)
    feature_record_event("pulls", int(n))
    save_game()

# Status ailments + ult charge + kill/codex tracking are attached to the final damage function.
_feature_original_damage_enemy = damage_enemy

def damage_enemy(e, dmg, quiet=False):
    global feature_run_damage, feature_run_boss_damage, feature_ultimate_charge, feature_status_tick
    global feature_damage_by_source, feature_materials
    global feature_boss_rush_round, feature_boss_rush_best
    if not isinstance(e, dict) or e.get("hp", 0) <= 0:
        return _feature_original_damage_enemy(e, dmg, quiet)
    if e.get("kind") == "shield_guard":
        dmg *= 0.65  # 방패병은 단단한 방패 때문에 피해를 35% 덜 받아요.
    before_hp = float(e.get("hp", 0))
    _feature_original_damage_enemy(e, dmg, quiet)
    after_hp = float(e.get("hp", 0))
    dealt = max(0.0, min(before_hp, before_hp - after_hp))
    feature_run_damage += dealt
    source_name = feature_current_damage_source or "기본 공격"
    feature_damage_by_source[source_name] = feature_damage_by_source.get(source_name, 0.0) + dealt
    if e.get("boss"):
        feature_run_boss_damage += dealt
    # 공격 적중으로 궁극기 게이지를 조금씩 채웁니다.
    if dealt > 0:
        feature_ultimate_charge = min(100.0, feature_ultimate_charge + min(1.4, dealt * 0.12 + 0.15))
    if after_hp > 0 and not feature_status_tick:
        # 화상은 기존 불꽃검 코드가 처리합니다. 아래는 독·빙결·감전·약화 효과입니다.
        poison_level = skill_levels.get("독 구름", 0)
        if poison_level and random.random() < min(0.28, 0.06 + 0.025 * poison_level):
            # 독은 최대 5중첩까지 피해가 증가합니다. 지속 시간은 갱신하되 무한 중첩은 막습니다.
            poison_stacks = min(5, int(e.get("feature_poison_stacks", 0)) + 1)
            e["feature_poison_stacks"] = poison_stacks
            e["feature_poison"] = max(e.get("feature_poison", 0), 150)
            e["feature_poison_dmg"] = min(7, 1 + poison_level // 2 + (poison_stacks - 1) // 2)
        if frost_level > 0 and random.random() < min(0.24, 0.06 + 0.025 * frost_level):
            freeze_frames = 12 + frost_level * 3
            if e.get("boss"):
                freeze_frames = max(6, freeze_frames // 2)  # 보스는 짧게만 빙결됩니다.
            e["feature_frozen"] = max(e.get("feature_frozen", 0), freeze_frames)
            e["slow"] = max(e.get("slow", 0), 45 + frost_level * 8)
        if skill_levels.get("번개", 0) and random.random() < min(0.30, 0.08 + 0.025 * skill_levels.get("번개", 0)):
            e["feature_shock"] = max(e.get("feature_shock", 0), 120)
        curse_level = skill_levels.get("저주", 0)
        if curse_level and random.random() < min(0.65, 0.12 * curse_level):
            e["feature_weaken"] = max(e.get("feature_weaken", 0), 150 + 15 * curse_level)
    if before_hp > 0 and after_hp <= 0 and not e.get("feature_counted_death"):
        e["feature_counted_death"] = True
        kind = str(e.get("kind", "unknown"))
        feature_codex_kills[kind] = feature_codex_kills.get(kind, 0) + 1
        feature_record_event("kills", 1)
        if e.get("boss"):
            feature_record_event("bosses", 1)
            feature_materials += 4
        elif e.get("elite"):
            feature_record_event("elites", 1)
            feature_materials += 2
        elif random.random() < 0.16:
            feature_materials += 1
        feature_ultimate_charge = min(100.0, feature_ultimate_charge + (8.0 if e.get("boss") else 5.0 if e.get("elite") else 1.0))
        if feature_boss_rush_active and e.get("boss"):
            feature_boss_rush_round += 1
            feature_boss_rush_best = max(feature_boss_rush_best, feature_boss_rush_round)
            feature_stats["best_boss_rush"] = max(feature_stats.get("best_boss_rush", 0), feature_boss_rush_best)
            if feature_boss_rush_round >= len(FEATURE_BOSS_RUSH_SEQUENCE):
                globals()["feature_boss_rush_active"] = False
                globals()["feature_boss_rush_complete"] = True
                globals()["feature_boss_rush_finish_pending"] = True
            else:
                globals()["feature_boss_rush_timer"] = 90
    return None

def feature_damage(source, enemy, amount, quiet=False):
    global feature_current_damage_source
    previous = feature_current_damage_source
    feature_current_damage_source = source
    try:
        return damage_enemy(enemy, amount, quiet)
    finally:
        feature_current_damage_source = previous

_feature_original_explode = explode
def explode(pos):
    global feature_current_damage_source
    previous = feature_current_damage_source
    feature_current_damage_source = "폭발탄"
    try:
        return _feature_original_explode(pos)
    finally:
        feature_current_damage_source = previous

# Guard player damage while the temporary E ultimate shield is active.
_feature_original_hurt_player = hurt_player
def hurt_player(damage=1):
    if feature_ultimate_shield_timer > 0 and not game_over:
        if frame_tick % 8 == 0:
            rings.append({"pos": player_pos.copy(), "r": 74, "life": 10, "max": 10, "color": (100, 230, 255)})
        return
    return _feature_original_hurt_player(damage)

# Wrap existing world rendering to support hiding floating damage text without affecting game logic.
_feature_original_add_shake = add_shake
def add_shake(n):
    if feature_settings.get("screen_shake", True):
        _feature_original_add_shake(n)

_feature_original_draw_world = draw_world
def draw_world():
    if feature_settings.get("damage_numbers", True):
        return _feature_original_draw_world()
    global floaters
    keep = floaters
    floaters = []
    try:
        return _feature_original_draw_world()
    finally:
        floaters = keep

# Complete run statistics, mission progression and save data.
_feature_original_end_game = end_game
def end_game(cleared=False):
    global feature_last_run, feature_boss_rush_active
    if game_over:
        return None
    is_boss_rush_run = bool(feature_boss_rush_active or feature_boss_rush_complete)
    endless_best_before = (best_time, best_kills)
    top_damage_source = max(feature_damage_by_source, key=feature_damage_by_source.get) if feature_damage_by_source else "기록 없음"
    run_data = {
        "mode": "보스 러시" if (feature_boss_rush_active or feature_boss_rush_complete) else cur_def.get("name", "게임"),
        "stage": int(cur_stage), "stage_name": cur_def.get("name", "게임"),
        "class": CLASSES[cur_class]["name"], "survival_seconds": int(survive_frames // 60),
        "kills": int(kills), "bosses": int(run_bosses), "elites": int(run_elites),
        "level": int(level), "damage": int(feature_run_damage),
        "boss_damage": int(feature_run_boss_damage),
        "top_skill": top_damage_source,
        "cleared": bool(cleared), "date": _feature_date.today().isoformat(),
    }
    if cleared and not feature_boss_rush_active and cur_stage > 0:
        feature_record_event("clears", 1)
        if cur_stage in (4, 5, 6):
            feature_record_advanced_stage(cur_stage)
        feature_record_distinct_class(CLASSES[cur_class]["name"])
    _feature_original_end_game(cleared)
    if is_boss_rush_run:
        # Boss Rush uses its own record and must not replace Endless-mode records.
        globals()["best_time"], globals()["best_kills"] = endless_best_before
        globals()["new_record"] = False
    feature_last_run = run_data
    feature_stats["runs"] = feature_stats.get("runs", 0) + 1
    feature_stats["total_kills"] = feature_stats.get("total_kills", 0) + int(kills)
    feature_stats["total_damage"] = feature_stats.get("total_damage", 0) + int(feature_run_damage)
    feature_stats["boss_damage"] = feature_stats.get("boss_damage", 0) + int(feature_run_boss_damage)
    feature_stats["best_kills"] = max(feature_stats.get("best_kills", 0), int(kills))
    feature_stats["best_survival"] = max(feature_stats.get("best_survival", 0), int(survive_frames // 60))
    save_game()

# Every new run resets run-only values. The permanent feature statistics remain saved.
_feature_original_reset_game = reset_game
def reset_game():
    global feature_ultimate_charge, feature_ultimate_q_cd, feature_ultimate_e_cd
    global feature_ultimate_shield_timer, feature_run_damage, feature_run_boss_damage, feature_damage_by_source
    global feature_boss_rush_round, feature_boss_rush_timer, feature_boss_rush_finish_pending
    _feature_original_reset_game()
    if not feature_boss_rush_active:
        globals()["feature_boss_rush_complete"] = False
    feature_ultimate_charge = 0.0
    feature_ultimate_q_cd = 0
    feature_ultimate_e_cd = 0
    feature_ultimate_shield_timer = 0
    feature_run_damage = 0
    feature_run_boss_damage = 0
    feature_damage_by_source = {}
    feature_boss_rush_round = 0
    feature_boss_rush_timer = 60 if feature_boss_rush_active else 0
    feature_boss_rush_finish_pending = False
    if feature_boss_rush_active:
        globals()["next_boss_frame"] = 10**9

_feature_original_start_stage = start_stage
def start_stage(sid):
    global feature_boss_rush_active, feature_boss_rush_complete, feature_boss_rush_finish_pending
    if not feature_starting_boss_rush:
        feature_boss_rush_active = False
        feature_boss_rush_complete = False
        feature_boss_rush_finish_pending = False
    return _feature_original_start_stage(sid)

FEATURE_BOSS_RUSH_SEQUENCE = ["orc", "dragon", "golem", "vampire", "lich", "frostgiant"]

def feature_start_boss_rush():
    global feature_starting_boss_rush, feature_boss_rush_active, feature_boss_rush_round
    global feature_boss_rush_timer, feature_boss_rush_complete, feature_boss_rush_finish_pending
    global cur_stage, state, next_boss_frame, challenge
    challenge = False
    feature_starting_boss_rush = True
    feature_boss_rush_active = False
    cur_stage = 0
    reset_game()
    feature_starting_boss_rush = False
    feature_boss_rush_active = True
    feature_boss_rush_round = 0
    feature_boss_rush_timer = 60
    feature_boss_rush_complete = False
    feature_boss_rush_finish_pending = False
    next_boss_frame = 10**9
    state = "playing"
    show_toast("보스 러시 시작! 보스 6마리를 연속으로 처치하세요", (255, 210, 110))
    snd_boss.play()

def feature_find_dense_angle(max_range=245, half_angle=78):
    """사거리 안의 적을 가장 많이 맞힐 수 있는 방향을 계산합니다."""
    live = []
    for enemy in enemies:
        if enemy.get("hp", 0) <= 0:
            continue
        vec = enemy["pos"] - player_pos
        dist = vec.length()
        if 0 < dist <= max_range:
            live.append((enemy, vec, dist, angle_of(vec)))
    if not live:
        return 180.0 if facing_left else 0.0

    best_group = []
    best_score = -1.0
    best_angle = 180.0 if facing_left else 0.0
    for _candidate, _vec, _dist, candidate_angle in live:
        group = [item for item in live
                 if abs(angle_diff(item[3], candidate_angle)) <= half_angle]
        # 숫자로는 적 수를 최우선하고, 같은 수라면 엘리트·보스가 있는 방향을 약간 선호합니다.
        score = len(group) * 10.0
        score += sum(1.8 if item[0].get("boss") else 0.6 if item[0].get("elite") else 0.0
                     for item in group)
        score -= sum(item[2] for item in group) / max(1, len(group)) * 0.004
        if score > best_score:
            best_score, best_group, best_angle = score, group, candidate_angle

    # 고른 무리의 평균 방향으로 살짝 보정해 부채꼴 한쪽에 적이 몰리지 않게 합니다.
    sx = sum(math.cos(math.radians(item[3])) for item in best_group)
    sy = sum(math.sin(math.radians(item[3])) for item in best_group)
    if sx or sy:
        best_angle = math.degrees(math.atan2(sy, sx))
    return best_angle


def feature_use_ultimate(which):
    global feature_ultimate_charge, feature_ultimate_q_cd, feature_ultimate_e_cd
    global feature_ultimate_shield_timer, invuln_timer, facing_left
    if state != "playing" or game_over:
        return False
    if which == 1:
        if feature_ultimate_q_cd > 0 or feature_ultimate_charge < 100:
            show_toast(f"화염검 궁극기: 게이지 {int(feature_ultimate_charge)}%", (255, 175, 90))
            return False
        feature_ultimate_charge -= 100
        feature_ultimate_q_cd = 480
        # 자동 조준: 플레이어가 바라보는 방향보다 현재 사거리 안에서 적이 가장 몰린 방향을 우선합니다.
        aim_angle = feature_find_dense_angle(245, 78)
        facing_left = math.cos(math.radians(aim_angle)) < 0
        hit_count = 0
        impact = player_pos + pygame.Vector2(95, 0).rotate(aim_angle)
        for enemy in list(enemies):
            if enemy.get("hp", 0) <= 0:
                continue
            vec = enemy["pos"] - player_pos
            if vec.length() <= 245 and abs(angle_diff(angle_of(vec), aim_angle)) <= 78:
                feature_damage("궁극기 화염검", enemy, projectile_damage * 5 + 12, quiet=True)
                if not enemy.get("boss"):
                    enemy["burn"] = max(enemy.get("burn", 0), 180)
                    enemy["burn_dmg"] = max(enemy.get("burn_dmg", 0), 2 + flame_level)
                hit_count += 1
        flames.append({"ang": aim_angle, "half": 78, "reach": 245, "life": 30, "max": 30})
        rings.append({"pos": impact, "r": 245, "life": 22, "max": 22, "color": (255, 125, 45)})
        spawn_burst(impact, (255, 185, 75), 28)
        add_shake(8)
        snd_flame.play()
        show_toast(f"궁극기 화염검! 적중 {hit_count}마리", (255, 180, 80))
        return True
    if which == 2:
        if feature_ultimate_e_cd > 0 or feature_ultimate_charge < 60:
            show_toast(f"수호 궁극기: 게이지 60% 필요 (현재 {int(feature_ultimate_charge)}%)", (120, 220, 255))
            return False
        feature_ultimate_charge -= 60
        feature_ultimate_e_cd = 600
        feature_ultimate_shield_timer = 180
        invuln_timer = max(invuln_timer, 25)
        for enemy in list(enemies):
            if enemy.get("hp", 0) <= 0:
                continue
            vec = enemy["pos"] - player_pos
            dist = vec.length()
            if dist <= 150:
                feature_damage("궁극기 보호막", enemy, projectile_damage * 2 + 5, quiet=True)
                if dist > 0:
                    enemy["pos"] += vec.normalize() * 42
        rings.append({"pos": player_pos.copy(), "r": 150, "life": 30, "max": 30, "color": (100, 230, 255)})
        spawn_burst(player_pos, (150, 240, 255), 24)
        snd_zap.play()
        show_toast("수호 궁극기! 3초 동안 피해 무시", (120, 225, 255))
        return True
    return False

def feature_tick():
    global feature_ultimate_q_cd, feature_ultimate_e_cd, feature_ultimate_shield_timer
    global feature_boss_rush_timer, feature_boss_rush_active, feature_boss_rush_finish_pending
    global feature_status_tick, feature_reward_toast_cooldown, shake
    if feature_ultimate_q_cd > 0:
        feature_ultimate_q_cd -= 1
    if feature_ultimate_e_cd > 0:
        feature_ultimate_e_cd -= 1
    if feature_ultimate_shield_timer > 0:
        feature_ultimate_shield_timer -= 1
        if frame_tick % 8 == 0:
            rings.append({"pos": player_pos.copy(), "r": 42, "life": 8, "max": 8, "color": (100, 230, 255)})
    if not feature_settings.get("screen_shake", True):
        shake = 0
    if feature_reward_toast_cooldown > 0:
        feature_reward_toast_cooldown -= 1

    # 전투 중 상태 이상 지속 시간과 피해를 처리합니다. 중첩 피해가 다시 상태 이상을 걸지 않도록 막아요.
    feature_status_tick = True
    try:
        for enemy in list(enemies):
            if enemy.get("feature_frozen", 0) > 0:
                enemy["feature_frozen"] -= 1
            if enemy.get("feature_weaken", 0) > 0:
                enemy["feature_weaken"] -= 1
            poison = enemy.get("feature_poison", 0)
            if poison > 0:
                enemy["feature_poison"] = poison - 1
                if poison % 30 == 0 and enemy.get("hp", 0) > 0:
                    feature_damage("독 피해", enemy, enemy.get("feature_poison_dmg", 1), quiet=True)
                    spawn_burst(enemy["pos"], (130, 230, 90), 2)
            shock = enemy.get("feature_shock", 0)
            if shock > 0:
                enemy["feature_shock"] = shock - 1
                if shock % 45 == 0 and enemy.get("hp", 0) > 0:
                    near = [other for other in enemies if other is not enemy and other.get("hp", 0) > 0
                            and other["pos"].distance_to(enemy["pos"]) <= 110]
                    if near:
                        target = min(near, key=lambda other: other["pos"].distance_to(enemy["pos"]))
                        target["feature_shock"] = max(target.get("feature_shock", 0), 70)
                        feature_damage("감전 연쇄", target, max(1, projectile_damage), quiet=True)
                        rings.append({"pos": target["pos"].copy(), "r": 28, "life": 8, "max": 8,
                                      "color": (255, 240, 110)})
            if enemy.get("kind") == "summoner" and enemy.get("hp", 0) > 0:
                enemy["feature_summon_cd"] = enemy.get("feature_summon_cd", 120) - 1
                if enemy["feature_summon_cd"] <= 0 and len(enemies) < 85:
                    enemy["feature_summon_cd"] = 210
                    for _ in range(2):
                        offset = pygame.Vector2(random.randint(20, 45), 0).rotate(random.uniform(0, 360))
                        enemies.append(make_enemy(random.choice(["slime", "goblin"]), enemy["pos"] + offset))
                    spawn_burst(enemy["pos"], (190, 110, 255), 8)
            elif enemy.get("kind") == "assassin" and enemy.get("hp", 0) > 0:
                enemy["feature_teleport_cd"] = enemy.get("feature_teleport_cd", 150) - 1
                if enemy["feature_teleport_cd"] <= 0:
                    enemy["feature_teleport_cd"] = 180
                    offset = pygame.Vector2(random.choice([-1, 1]) * random.randint(90, 145),
                                            random.randint(-90, 90))
                    enemy["pos"] = player_pos + offset
                    enemy["pos"].x = max(18, min(WIDTH - 18, enemy["pos"].x))
                    enemy["pos"].y = max(18, min(HEIGHT - 18, enemy["pos"].y))
                    spawn_burst(enemy["pos"], (220, 70, 100), 7)
    finally:
        feature_status_tick = False

    if feature_boss_rush_active:
        if feature_boss_rush_timer > 0:
            feature_boss_rush_timer -= 1
        alive_boss = any(e.get("boss") and e.get("hp", 0) > 0 for e in enemies)
        if feature_boss_rush_round == 0 and not alive_boss and feature_boss_rush_timer <= 0:
            spawn_boss(FEATURE_BOSS_RUSH_SEQUENCE[0], 1.0, False)
            show_toast("보스 러시 1/6", (255, 205, 110))
        elif feature_boss_rush_round > 0 and not alive_boss and feature_boss_rush_timer <= 0:
            index = min(feature_boss_rush_round, len(FEATURE_BOSS_RUSH_SEQUENCE) - 1)
            scale = 1.0 + 0.22 * index
            spawn_boss(FEATURE_BOSS_RUSH_SEQUENCE[index], scale, index == len(FEATURE_BOSS_RUSH_SEQUENCE) - 1)
            show_toast(f"보스 러시 {index + 1}/6", (255, 205, 110))
    if feature_boss_rush_finish_pending and not game_over:
        feature_boss_rush_finish_pending = False
        feature_boss_rush_active = False
        feature_boss_rush_complete = True
        feature_stats["best_boss_rush"] = max(feature_stats.get("best_boss_rush", 0), feature_boss_rush_round)
        end_game(False)

# Add an extra-content entry to the existing title menu.
if not any(item[0] == "추가 콘텐츠" for item in TITLE_LABELS):
    TITLE_LABELS.append(("추가 콘텐츠", (210, 170, 255)))
_feature_original_title_activate = title_activate
def title_activate(i):
    global state, feature_page, feature_menu_index
    if i == 5:
        feature_page = "hub"
        feature_menu_index = 0
        state = "features"
        snd_click.play()
        return
    return _feature_original_title_activate(i)

_feature_original_title_event = title_event
def title_event(event):
    if state == "title" and event.type == pygame.KEYDOWN and event.key == pygame.K_6:
        title_activate(5)
        return
    return _feature_original_title_event(event)

# Feature menu helpers.
def feature_hub_rects():
    return [pygame.Rect(58 + (i % 2) * 350, 130 + (i // 2) * 112, 324, 82)
            for i in range(len(FEATURE_HUB_ITEMS))]

def feature_page_back():
    global feature_page
    feature_page = "hub"
    snd_click.play()

def feature_hub_select(i):
    global feature_page, feature_menu_index, state, feature_craft_index, feature_codex_category, feature_codex_index
    if not (0 <= i < len(FEATURE_HUB_ITEMS)):
        return
    feature_menu_index = i
    key = FEATURE_HUB_ITEMS[i][1]
    snd_click.play()
    if key == "boss_rush":
        feature_start_boss_rush()
    else:
        feature_page = key
        if key == "craft":
            if equipped_weapon in ALL_ORDER:
                feature_craft_index = ALL_ORDER.index(equipped_weapon)
        elif key == "codex":
            feature_codex_category = 0
            feature_codex_index = 0

FEATURE_LOCAL_NAMES = {
    "slime": "슬라임", "goblin": "고블린", "mage": "마법사 몬스터", "boar": "멧돼지",
    "jelly": "젤리", "mini": "작은 젤리", "bat": "박쥐", "orc": "오크 대장",
    "dragon": "드래곤", "golem": "바위 골렘", "mummy": "미라", "scorpion": "전갈",
    "raider": "사막 약탈자", "sand_boar": "모래 멧돼지", "toad": "독 두꺼비",
    "shroom": "독버섯", "yeti": "설인", "imp": "임프", "skeleton": "해골 병사",
    "ghost": "유령", "frost_wolf": "서리 늑대", "ash_hound": "잿불 사냥개",
    "ice_jelly": "얼음 젤리", "magma_slime": "마그마 슬라임", "ice_mage": "빙결 마법사",
    "fire_mage": "화염 마법사", "ice_wisp": "얼음 정령", "summoner": "소환사",
    "assassin": "암살자", "shield_guard": "방패병", "split_slime": "분열 슬라임",
    "vampire": "흡혈 군주", "lich": "리치", "frostgiant": "서리 거인",
}

def feature_codex_rows():
    boss_ids = set(BOSS_NAMES) | set(globals().get("BOSS_NEW", set())) | {"vampire", "lich", "frostgiant"} | set(globals().get("THEME_BOSS_META", {}))
    if feature_codex_category == 0:
        return [("몬스터", k, enemy_types[k].get("color", (220, 220, 220)),
                 feature_codex_kills.get(k, 0), "처치 기록")
                for k, v in enemy_types.items() if not v.get("boss") and k not in boss_ids]
    if feature_codex_category == 1:
        order = ["orc", "dragon", "golem", "vampire", "lich", "frostgiant"]
        order.extend(k for k in globals().get("THEME_BOSS_META", {}) if k not in order)
        order.extend(k for k, v in enemy_types.items() if v.get("boss") and k not in order)
        return [("보스", k, enemy_types[k].get("color", (220, 220, 220)),
                 feature_codex_kills.get(k, 0), "처치 기록")
                for k in order if k in enemy_types]
    return [("장비", k, RARITY[WEAPONS[k]["rarity"]]["color"],
             1 if k in feature_discovered_items or k in weapon_stars else 0,
             WEAPONS[k]["name"]) for k in ALL_ORDER]

def feature_craft_cost(wid):
    rarity = WEAPONS[wid]["rarity"]
    return {"common": (3, 100), "rare": (5, 250), "epic": (8, 500),
            "legend": (12, 1000), "myth": (20, 2500)}.get(rarity, (5, 300))

def feature_dismantle_selected():
    global feature_materials, gold
    if not ALL_ORDER:
        return
    wid = ALL_ORDER[feature_craft_index % len(ALL_ORDER)]
    if wid not in weapon_stars:
        show_toast("보유하지 않은 장비예요", (255, 140, 140)); snd_fail.play(); return
    if is_equipped(wid):
        show_toast("장착 중인 장비는 먼저 해제하세요", (255, 140, 140)); snd_fail.play(); return
    rarity = WEAPONS[wid]["rarity"]
    mats = {"common": 2, "rare": 4, "epic": 7, "legend": 12, "myth": 20}.get(rarity, 2)
    refund = {"common": 30, "rare": 70, "epic": 140, "legend": 280, "myth": 500}.get(rarity, 30)
    del weapon_stars[wid]
    feature_item_enhancements.pop(wid, None)
    feature_item_potentials.pop(wid, None)
    feature_item_dyes.pop(wid, None)
    feature_apply_dyes()
    feature_discovered_items.add(wid)  # 도감 발견 기록은 유지합니다.
    feature_materials += mats
    gold += refund
    save_game()
    snd_buy.play()
    show_toast(f"{WEAPONS[wid]['name']} 분해: 재료 +{mats}, 골드 +{refund}", (150, 255, 180))

def feature_craft_selected():
    global feature_materials, gold
    if not ALL_ORDER:
        return
    wid = ALL_ORDER[feature_craft_index % len(ALL_ORDER)]
    mats, cost = feature_craft_cost(wid)
    if wid in weapon_stars:
        show_toast("이미 보유한 장비예요. 별 강화는 S, 능력치 강화는 U를 누르세요", (200, 190, 220)); snd_fail.play(); return
    if feature_materials < mats or gold < cost:
        show_toast(f"제작 비용: 재료 {mats}개 + {cost}G", (255, 145, 145)); snd_fail.play(); return
    feature_materials -= mats
    gold -= cost
    weapon_stars[wid] = 1
    msg = f"{WEAPONS[wid]['name']} 제작 완료"
    feature_discovered_items.add(wid)
    save_game()
    snd_buy.play()
    show_toast(msg, (150, 255, 180))

def feature_upgrade_selected():
    feature_enhance_selected()


def feature_settings_adjust(direction):
    global feature_settings_index, feature_rebind_target
    keys = ["volume", "music_volume", "screen_shake", "damage_numbers", "dash_key", "ult1_key", "ult2_key"]
    key = keys[feature_settings_index % len(keys)]
    if key == "volume":
        feature_settings["volume"] = max(0.0, min(1.0, round(feature_settings["volume"] + 0.1 * direction, 2)))
        feature_set_volume()
    elif key == "music_volume":
        feature_settings["music_volume"] = max(0.0, min(1.0, round(feature_settings.get("music_volume", 0.28) + 0.1 * direction, 2)))
        if globals().get("THEME_MUSIC_CHANNEL") is not None:
            THEME_MUSIC_CHANNEL.set_volume(feature_settings["music_volume"])
    elif key in ("screen_shake", "damage_numbers"):
        feature_settings[key] = not feature_settings[key]
    else:
        feature_rebind_target = key
        show_toast(f"새 키를 누르세요: {key}", (190, 180, 255))
    save_game()

def feature_settings_activate():
    global feature_rebind_target
    keys = ["volume", "music_volume", "screen_shake", "damage_numbers", "dash_key", "ult1_key", "ult2_key"]
    key = keys[feature_settings_index % len(keys)]
    if key in ("dash_key", "ult1_key", "ult2_key"):
        feature_rebind_target = key
        show_toast("지정할 키를 누르세요 (ESC 취소)", (190, 180, 255))
    else:
        feature_settings_adjust(1)

def feature_menu_event(event):
    global feature_menu_index, feature_page, feature_settings_index, feature_rebind_target
    global feature_codex_category, feature_codex_index, feature_craft_index
    if event.type == pygame.KEYDOWN:
        k = event.key
        if feature_rebind_target:
            if k == pygame.K_ESCAPE:
                feature_rebind_target = None
                return
            used = {feature_settings[x] for x in ("dash_key", "ult1_key", "ult2_key") if x != feature_rebind_target}
            reserved = {
                pygame.K_ESCAPE, pygame.K_F11, pygame.K_p, pygame.K_r,
                pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
                pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
                pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_RETURN,
                pygame.K_KP_ENTER,
            }
            if k in used or k in reserved:
                show_toast("이미 사용 중이거나 기본 조작에 예약된 키예요", (255, 145, 145))
                return
            feature_settings[feature_rebind_target] = k
            feature_rebind_target = None
            save_game()
            show_toast("조작 키를 변경했어요", (150, 255, 180))
            return
        if k in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            if feature_page != "hub":
                feature_page_back()
            else:
                globals()["state"] = "title"
                snd_click.play()
            return
        if feature_page == "hub":
            if k in (pygame.K_UP, pygame.K_w):
                feature_menu_index = (feature_menu_index - 2) % len(FEATURE_HUB_ITEMS)
            elif k in (pygame.K_DOWN, pygame.K_s):
                feature_menu_index = (feature_menu_index + 2) % len(FEATURE_HUB_ITEMS)
            elif k in (pygame.K_LEFT, pygame.K_a):
                feature_menu_index = max(0, feature_menu_index - 1)
            elif k in (pygame.K_RIGHT, pygame.K_d):
                feature_menu_index = min(len(FEATURE_HUB_ITEMS) - 1, feature_menu_index + 1)
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                feature_hub_select(feature_menu_index)
            elif pygame.K_1 <= k <= pygame.K_6:
                feature_hub_select(k - pygame.K_1)
            return
        if feature_page == "settings":
            if k in (pygame.K_UP, pygame.K_w): feature_settings_index = (feature_settings_index - 1) % 7
            elif k in (pygame.K_DOWN, pygame.K_s): feature_settings_index = (feature_settings_index + 1) % 7
            elif k in (pygame.K_LEFT, pygame.K_a): feature_settings_adjust(-1)
            elif k in (pygame.K_RIGHT, pygame.K_d): feature_settings_adjust(1)
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE): feature_settings_activate()
            return
        if feature_page == "codex":
            if k in (pygame.K_LEFT, pygame.K_a):
                feature_codex_category = (feature_codex_category - 1) % 3; feature_codex_index = 0
            elif k in (pygame.K_RIGHT, pygame.K_d, pygame.K_TAB):
                feature_codex_category = (feature_codex_category + 1) % 3; feature_codex_index = 0
            elif k in (pygame.K_UP, pygame.K_w):
                feature_codex_index = max(0, feature_codex_index - 1)
            elif k in (pygame.K_DOWN, pygame.K_s):
                feature_codex_index = min(max(0, len(feature_codex_rows()) - 1), feature_codex_index + 1)
            elif k in (pygame.K_1, pygame.K_2, pygame.K_3):
                feature_codex_category = k - pygame.K_1; feature_codex_index = 0
            return
        if feature_page == "craft":
            if k in (pygame.K_LEFT, pygame.K_a): feature_craft_index = (feature_craft_index - 1) % len(ALL_ORDER)
            elif k in (pygame.K_RIGHT, pygame.K_d): feature_craft_index = (feature_craft_index + 1) % len(ALL_ORDER)
            elif k == pygame.K_x: feature_dismantle_selected()
            elif k == pygame.K_c: feature_craft_selected()
            elif k == pygame.K_u: feature_enhance_selected()
            elif k == pygame.K_s: feature_star_selected()
            elif k == pygame.K_p: feature_roll_potential()
            elif k == pygame.K_d: feature_cycle_dye()
            return
        if feature_page in ("missions", "stats"):
            if k in (pygame.K_TAB, pygame.K_RETURN):
                feature_page_back()
            return
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        pos = event.pos
        if feature_page == "hub":
            back_rect = pygame.Rect(20, 16, 120, 38)
            if back_rect.collidepoint(pos):
                globals()["state"] = "title"
                snd_click.play()
                return
            for i, rect in enumerate(feature_hub_rects()):
                if rect.collidepoint(pos):
                    feature_hub_select(i); return
        else:
            back_rect = pygame.Rect(20, 16, 120, 38)
            if back_rect.collidepoint(pos):
                feature_page_back(); return
            if feature_page == "settings":
                for i in range(6):
                    r = pygame.Rect(170, 105 + i * 53, 460, 46)
                    if r.collidepoint(pos):
                        feature_settings_index = i
                        if i in (0,): feature_settings_adjust(1)
                        elif i in (1, 2): feature_settings_activate()
                        else: feature_settings_activate()
                        return
            elif feature_page == "craft":
                for key, rect in feature_button_rects.items():
                    if rect.collidepoint(pos):
                        if key == "prev": feature_craft_index = (feature_craft_index - 1) % len(ALL_ORDER)
                        elif key == "next": feature_craft_index = (feature_craft_index + 1) % len(ALL_ORDER)
                        elif key == "dismantle": feature_dismantle_selected()
                        elif key == "craft": feature_craft_selected()
                        elif key == "enhance": feature_enhance_selected()
                        elif key == "star": feature_star_selected()
                        elif key == "potential": feature_roll_potential()
                        elif key == "dye": feature_cycle_dye()
                        return
            elif feature_page == "codex":
                for i in range(3):
                    r = pygame.Rect(205 + i * 130, 78, 122, 34)
                    if r.collidepoint(pos):
                        feature_codex_category = i; feature_codex_index = 0; return
                list_top = 138
                rows = feature_codex_rows()
                for i, item in enumerate(rows[feature_codex_index:feature_codex_index + 8]):
                    r = pygame.Rect(92, list_top + i * 46, 616, 40)
                    if r.collidepoint(pos):
                        feature_codex_index = min(len(rows) - 1, feature_codex_index + i); return
    elif event.type == pygame.MOUSEWHEEL:
        if feature_page == "codex":
            feature_codex_index = max(0, min(max(0, len(feature_codex_rows()) - 1), feature_codex_index - event.y))
        elif feature_page == "craft":
            feature_craft_index = (feature_craft_index + (-1 if event.y > 0 else 1)) % len(ALL_ORDER)

def feature_draw_background(title):
    screen.fill((12, 13, 26))
    panel = pygame.Rect(20, 16, WIDTH - 40, HEIGHT - 32)
    pixel_panel(screen, panel, (90, 82, 130), (22, 24, 43), n=8, bw=3)
    blit_text(screen, font, title, (235, 225, 255), (WIDTH // 2, 42), True)
    draw_button(screen, pygame.Rect(20, 16, 120, 38), "뒤로 (ESC)", False, True, (190, 170, 255))

def feature_draw_hub():
    feature_draw_background("추가 콘텐츠")
    blit_text(screen, tiny_font, "기능을 선택하세요 · 방향키/Enter 또는 마우스 클릭", (170, 180, 210), (WIDTH // 2, 82), True)
    for i, (label, key) in enumerate(FEATURE_HUB_ITEMS):
        rect = feature_hub_rects()[i]
        color = (255, 205, 105) if i == feature_menu_index else (155, 175, 225)
        draw_dungeon_button(rect, label, i == feature_menu_index, color)
        subtitle = {
            "settings": "소리·화면·키 조절", "codex": "몬스터·보스·장비 기록",
            "missions": "오늘/이번 주 목표", "craft": "장비 분해·제작·강화",
            "stats": "최근 전투 및 누적 기록", "boss_rush": "보스 6연전 · 보상 도전"
        }[key]
        blit_text(screen, tiny_font, subtitle, (175, 185, 215), (rect.centerx, rect.bottom - 17), True)
    blit_text(screen, tiny_font, f"제작 재료 {feature_materials}개 · 최고 보스 러시 {feature_stats.get('best_boss_rush', 0)}라운드",
              (255, 220, 130), (WIDTH // 2, 548), True)

def feature_draw_settings():
    feature_draw_background("설정")
    rows = [
        ("효과음 음량", f"{int(feature_settings['volume'] * 100)}%  (←/→ 조절)"),
        ("배경 음악 음량", f"{int(feature_settings.get('music_volume', 0.28) * 100)}%  (←/→ 조절)"),
        ("화면 흔들림", "켜짐" if feature_settings["screen_shake"] else "꺼짐"),
        ("피해 숫자 표시", "켜짐" if feature_settings["damage_numbers"] else "꺼짐"),
        ("대시 키", pygame.key.name(feature_settings["dash_key"]).upper()),
        ("궁극기 1 키", pygame.key.name(feature_settings["ult1_key"]).upper()),
        ("궁극기 2 키", pygame.key.name(feature_settings["ult2_key"]).upper()),
    ]
    for i, (label, value) in enumerate(rows):
        r = pygame.Rect(170, 130 + i * 58, 460, 46)
        draw_dungeon_button(r, f"{label}: {value}", i == feature_settings_index, (190, 170, 255))
    hint = "위/아래: 선택 · 좌/우: 음량/토글 · Enter: 토글 또는 키 재지정 · 새 키를 누르면 저장"
    if feature_rebind_target:
        hint = f"새 키 입력 대기 중: {feature_rebind_target} · ESC 취소"
    blit_text(screen, tiny_font, hint, (175, 185, 215), (WIDTH // 2, 530), True)
    blit_text(screen, tiny_font, "F11: 전체 화면 전환", (155, 165, 195), (WIDTH // 2, 560), True)

def feature_draw_codex():
    feature_draw_background("도감")
    tabs = ["몬스터", "보스", "장비"]
    for i, label in enumerate(tabs):
        r = pygame.Rect(205 + i * 130, 78, 122, 34)
        draw_dungeon_button(r, label, i == feature_codex_category, (170, 205, 255))
    rows = feature_codex_rows()
    total = len(rows)
    completed = sum(1 for _cat, _key, _c, count, _desc in rows if count > 0)
    blit_text(screen, tiny_font, f"수집/발견 {completed}/{max(1, total)}", (255, 225, 130), (WIDTH // 2, 118), True)
    start = max(0, min(feature_codex_index, max(0, total - 8)))
    for idx, (cat, key, color, count, desc) in enumerate(rows[start:start + 8]):
        r = pygame.Rect(92, 138 + idx * 46, 616, 40)
        selected = (start + idx) == feature_codex_index
        outline = (155, 205, 255) if selected else (color if count else (65, 65, 85))
        pixel_panel(screen, r, outline, (35, 38, 60), n=4, bw=3 if selected else 2)
        if cat == "장비":
            name = WEAPONS[key]["name"]
            detail = f"보유 {weapon_stars.get(key, 0)}성" if key in weapon_stars else "미획득"
        else:
            name = BOSS_NAMES.get(key, FEATURE_LOCAL_NAMES.get(key, key.replace("_", " ").title()))
            detail = f"처치 {count}회" if count else "아직 발견하지 못함"
        name_color = color if count else (165, 170, 195)
        blit_text(screen, tiny_font, fit_text(tiny_font, name, 335), name_color, (r.x + 12, r.y + 11))
        blit_text_right(screen, tiny_font, fit_text(tiny_font, detail, 235), (220, 225, 245), r.right - 12, r.y + 11)
    blit_text(screen, tiny_font, "←/→ 또는 1/2/3: 분류 · ↑/↓: 목록 · 마우스 휠: 이동",
              (175, 185, 215), (WIDTH // 2, 548), True)

def feature_draw_missions():
    feature_ensure_missions()
    daily, weekly = feature_mission_lists()
    feature_draw_background("일일·주간 임무")
    blit_text(screen, tiny_font, f"오늘  {feature_missions.get('daily_stamp', '')}",
              (255, 220, 125), (220, 90), True)
    blit_text(screen, tiny_font, f"이번 주  {feature_missions.get('weekly_stamp', '')}",
              (175, 195, 255), (580, 90), True)
    for label, tasks, x, accent in (("일일", daily, 55, (255, 210, 120)),
                                    ("주간", weekly, 410, (160, 190, 255))):
        blit_text(screen, tiny_font, label + " 임무", accent, (x + 10, 122))
        for i, task in enumerate(tasks[:3]):
            r = pygame.Rect(x, 143 + i * 116, 330, 104)
            pixel_panel(screen, r, accent, (33, 36, 58), n=5, bw=3)
            title = fit_text(tiny_font, str(task.get("name", "임무")), r.w - 24)
            blit_text(screen, tiny_font, title, (230, 235, 250), (r.x + 12, r.y + 10))
            progress = min(task.get("goal", 1), task.get("progress", 0))
            draw_gauge(screen, pygame.Rect(r.x + 12, r.y + 38, r.w - 24, 13),
                       progress / max(1, task.get("goal", 1)), accent, (40, 45, 65))
            blit_text(screen, tiny_font, f"진행 {progress}/{task.get('goal', 1)}",
                      (200, 210, 235), (r.x + 12, r.y + 57))
            reward_text = f"보상 {task.get('reward_gold', 0)}G + 재료 {task.get('reward_mat', 0)}"
            blit_text(screen, tiny_font, fit_text(tiny_font, reward_text, r.w - 68),
                      (180, 190, 215), (r.x + 12, r.y + 78))
            if task.get("claimed"):
                blit_text_right(screen, tiny_font, "완료", (130, 255, 170), r.right - 10, r.y + 57)
    blit_text(screen, tiny_font, "임무 보상은 목표 달성 시 자동 지급됩니다. 날짜가 바뀌면 임무가 갱신됩니다.",
              (175, 185, 215), (WIDTH // 2, 520), True)

def feature_draw_craft():
    global feature_button_rects
    feature_draw_background("장비 제작·분해·강화")
    feature_button_rects = {
        "prev": pygame.Rect(65, 140, 90, 42), "next": pygame.Rect(645, 140, 90, 42),
        "dismantle": pygame.Rect(75, 368, 195, 48), "craft": pygame.Rect(302, 368, 195, 48),
        "enhance": pygame.Rect(529, 368, 195, 48), "star": pygame.Rect(75, 425, 195, 48),
        "potential": pygame.Rect(302, 425, 195, 48), "dye": pygame.Rect(529, 425, 195, 48),
    }
    wid = ALL_ORDER[feature_craft_index % len(ALL_ORDER)] if ALL_ORDER else ""
    if wid:
        w = WEAPONS[wid]
        star = weapon_stars.get(wid, 0)
        rar = RARITY[w["rarity"]]
        level = feature_item_enhancements.get(wid, 0)
        potential = feature_item_potentials.get(wid)
        dye_idx = feature_item_dyes.get(wid, 0)
        pixel_panel(screen, pygame.Rect(175, 124, 450, 224), rar["color"], (33, 36, 58), n=7, bw=3)
        icon = weapon_img(wid, 4)
        screen.blit(icon, icon.get_rect(center=(400, 176)))
        blit_text(screen, small_font, fit_text(small_font, w["name"], 370), rar["color"], (400, 218), True)
        blit_text(screen, tiny_font, f"등급 {rar['name']} · 별 {'없음' if star == 0 else star} · 강화 +{level}/10",
                  (220, 225, 245), (400, 245), True)
        potential_text = potential["name"] if potential else "잠재 능력 없음"
        dye_text = FEATURE_DYE_PALETTES[dye_idx][0]
        blit_text(screen, tiny_font, fit_text(tiny_font, f"잠재: {potential_text} · 도색: {dye_text}", 430),
                  (195, 190, 235), (400, 270), True)
        stats_lines = []
        for key, label in (("atk", "공격"), ("hp", "체력"), ("spd", "공속"), ("crit", "치명타"), ("xp", "경험치"), ("gold", "골드")):
            if w.get(key, 0): stats_lines.append(f"{label} +{w[key]}")
        blit_text(screen, tiny_font, fit_text(tiny_font, " · ".join(stats_lines[:4]) or "특수 효과는 장비 상점에서 확인", 430),
                  (185, 195, 220), (400, 302), True)
        mats, cost = feature_craft_cost(wid)
        next_lv = feature_item_enhancements.get(wid, 0)
        blit_text(screen, tiny_font, f"신규 제작 {mats}재료/{cost}G · 강화 {2 + next_lv}재료/{180 * (next_lv + 1)}G",
                  (255, 220, 130), (400, 333), True)
    draw_dungeon_button(feature_button_rects["prev"], "이전", False, (170, 190, 255))
    draw_dungeon_button(feature_button_rects["next"], "다음", False, (170, 190, 255))
    draw_dungeon_button(feature_button_rects["dismantle"], "X  장비 분해", False, (255, 145, 145))
    draw_dungeon_button(feature_button_rects["craft"], "C  신규 제작", False, (145, 255, 175))
    draw_dungeon_button(feature_button_rects["enhance"], "U  강화 레벨", False, (255, 220, 120))
    draw_dungeon_button(feature_button_rects["star"], "S  별 강화", False, (255, 195, 100))
    draw_dungeon_button(feature_button_rects["potential"], "P  잠재 부여", False, (190, 150, 255))
    draw_dungeon_button(feature_button_rects["dye"], "D  도색 변경", False, (180, 200, 255))
    blit_text(screen, tiny_font, f"보유 골드 {gold:,}G · 재료 {feature_materials}개 · 장비 {feature_craft_index + 1}/{len(ALL_ORDER)}",
              (255, 225, 130), (WIDTH // 2, 490), True)
    blit_text(screen, tiny_font, "←/→ 또는 이전/다음 · X 분해 · C 제작 · U 강화 · S 별 · P 잠재 · D 도색", (175, 185, 215),
              (WIDTH // 2, 526), True)


def feature_draw_stats():
    feature_draw_background("전투 통계")
    last = feature_last_run if isinstance(feature_last_run, dict) else {}
    rows = [
        ("최근 모드", last.get("mode", "아직 기록 없음")),
        ("사용 직업", last.get("class", "-")),
        ("생존 시간", f"{int(last.get('survival_seconds', 0)) // 60:02d}:{int(last.get('survival_seconds', 0)) % 60:02d}"),
        ("처치 / 보스 / 엘리트", f"{last.get('kills', 0)} / {last.get('bosses', 0)} / {last.get('elites', 0)}"),
        ("도달 레벨", last.get("level", 0)),
        ("총 피해 / 보스 피해", f"{last.get('damage', 0)} / {last.get('boss_damage', 0)}"),
        ("가장 큰 피해를 준 공격", last.get("top_skill", "기록 없음")),
        ("누적 플레이", feature_stats.get("runs", 0)),
        ("누적 처치 / 피해", f"{feature_stats.get('total_kills', 0)} / {feature_stats.get('total_damage', 0)}"),
        ("최고 생존 / 처치", f"{feature_stats.get('best_survival', 0)}초 / {feature_stats.get('best_kills', 0)}마리"),
        ("보스 러시 최고", f"{feature_stats.get('best_boss_rush', 0)}라운드"),
    ]
    for i, (label, value) in enumerate(rows):
        r = pygame.Rect(82, 88 + i * 40, 636, 34)
        pixel_panel(screen, r, (115, 125, 175), (32, 35, 57), n=4, bw=2)
        blit_text(screen, tiny_font, fit_text(tiny_font, str(label), 280),
                  (175, 190, 235), (r.x + 12, r.y + 8))
        blit_text_right(screen, tiny_font, fit_text(tiny_font, str(value), 285),
                        (235, 235, 250), r.right - 12, r.y + 8)
    blit_text(screen, tiny_font, "피해 수치는 전투 코드에서 관측한 유효 피해의 합계입니다.",
              (170, 180, 210), (WIDTH // 2, 550), True)

def draw_features_screen():
    global feature_page
    if feature_page == "hub": feature_draw_hub()
    elif feature_page == "settings": feature_draw_settings()
    elif feature_page == "codex": feature_draw_codex()
    elif feature_page == "missions": feature_draw_missions()
    elif feature_page == "craft": feature_draw_craft()
    elif feature_page == "stats": feature_draw_stats()
    else:
        feature_page = "hub"
        feature_draw_hub()

# Extra UI wrappers for ultimate meter and boss-rush result.
_feature_original_draw_hud = draw_hud
def draw_hud():
    _feature_original_draw_hud()
    panel = pygame.Rect(8, 148, 210, 27)
    pixel_panel(screen, panel, (130, 180, 255), (20, 25, 45), n=4, bw=2)
    draw_gauge(screen, pygame.Rect(panel.x + 5, panel.y + 5, 112, 16), feature_ultimate_charge / 100.0,
               (150, 225, 255), (45, 65, 110))
    qtxt = (f"{max(0, feature_ultimate_q_cd) // 60}s" if feature_ultimate_q_cd > 0
            else "준비" if feature_ultimate_charge >= 100 else f"{int(feature_ultimate_charge)}%")
    etxt = (f"{max(0, feature_ultimate_e_cd) // 60}s" if feature_ultimate_e_cd > 0
            else "준비" if feature_ultimate_charge >= 60 else f"{int(feature_ultimate_charge)}%")
    ult1_name = pygame.key.name(feature_settings["ult1_key"]).upper()
    ult2_name = pygame.key.name(feature_settings["ult2_key"]).upper()
    blit_text(screen, tiny_font, f"{ult1_name} {qtxt}  {ult2_name} {etxt}",
              (220, 235, 255), (panel.x + 164, panel.centery), True)

_feature_original_draw_game_over = draw_game_over
def draw_game_over():
    _feature_original_draw_game_over()
    if feature_boss_rush_complete:
        pixel_panel(screen, pygame.Rect(170, 230, 460, 54), (255, 215, 100), (35, 32, 45), n=6, bw=3)
        blit_text(screen, small_font, "보스 러시 완료!  6 / 6", (255, 225, 130), (WIDTH // 2, 246), True)
        blit_text(screen, tiny_font, f"최고 기록 {feature_stats.get('best_boss_rush', 6)}라운드 · 보상 골드는 결과 화면에 합산", (220, 225, 240),
                  (WIDTH // 2, 268), True)

# Per-item enhancement stats are applied through the existing gear_stats calculation.
_feature_original_gear_stats = gear_stats

def gear_stats():
    out = _feature_original_gear_stats()
    for wid in equipped_ids():
        if not wid or wid not in WEAPONS:
            continue
        level = feature_item_enhancements.get(wid, 0)
        # 강화 단계마다 해당 장비의 능력치가 10%씩 추가 증가
        item_stats = weapon_stats(wid)
        bonus_rate = 0.10 * level

        for stat_name in SCALED_KEYS:
            out[stat_name] += item_stats.get(stat_name, 0) * bonus_rate

        out["hp"] += item_stats.get("hp", 0) * bonus_rate
        potential = feature_item_potentials.get(wid)
        if potential and potential.get("stat") in out:
            out[potential["stat"]] += potential.get("value", 0)
    return out

FEATURE_DYE_PALETTES = [
    ("기본", None),
    ("불꽃", ((255, 105, 35), (255, 225, 120), (100, 35, 20))),
    ("서리", ((115, 195, 255), (235, 250, 255), (40, 85, 155))),
    ("독", ((110, 225, 85), (220, 255, 150), (35, 90, 35))),
    ("심연", ((175, 100, 255), (235, 200, 255), (55, 25, 100))),
    ("무지개 금빛", ((255, 205, 90), (255, 250, 190), (170, 70, 200))),
]

def feature_apply_dyes():
    # Replace only the display colors, preserving names, rarity and combat stats.
    for wid, data in WEAPONS.items():
        palette_index = feature_item_dyes.get(wid, 0)
        if 0 < palette_index < len(FEATURE_DYE_PALETTES):
            data["c"] = FEATURE_DYE_PALETTES[palette_index][1]
        else:
            data["c"] = feature_original_weapon_colors.get(wid, data["c"])
    if "_wimg_cache" in globals():
        _wimg_cache.clear()

def feature_enhance_selected():
    global feature_materials, gold
    wid = ALL_ORDER[feature_craft_index % len(ALL_ORDER)]
    if wid not in weapon_stars:
        show_toast("먼저 장비를 획득하거나 제작하세요", (255, 145, 145)); snd_fail.play(); return
    level = feature_item_enhancements.get(wid, 0)
    if level >= 10:
        show_toast("강화 레벨은 최대 +10입니다", (200, 190, 220)); snd_fail.play(); return
    mats, cost = 2 + level, 180 * (level + 1)
    if feature_materials < mats or gold < cost:
        show_toast(f"강화 비용: 재료 {mats}개 + {cost}G", (255, 145, 145)); snd_fail.play(); return
    feature_materials -= mats; gold -= cost
    feature_item_enhancements[wid] = level + 1
    save_game(); snd_buy.play()
    show_toast(f"강화 레벨 +{level + 1} · 능력치 상승", (150, 255, 180))

def feature_star_selected():
    global feature_materials, gold
    wid = ALL_ORDER[feature_craft_index % len(ALL_ORDER)]
    star = weapon_stars.get(wid, 0)
    if star <= 0:
        show_toast("먼저 장비를 획득하거나 제작하세요", (255, 145, 145)); snd_fail.play(); return
    if star >= MAX_STAR:
        show_toast("이미 최대 별이에요", (200, 190, 220)); snd_fail.play(); return
    mats, cost = 2 + star, 150 * star
    if feature_materials < mats or gold < cost:
        show_toast(f"별 강화 비용: 재료 {mats}개 + {cost}G", (255, 145, 145)); snd_fail.play(); return
    feature_materials -= mats; gold -= cost; weapon_stars[wid] = star + 1
    save_game(); snd_buy.play()
    show_toast(f"별 강화 성공! {WEAPONS[wid]['name']} {star + 1}성", (255, 220, 110))

def feature_roll_potential():
    global feature_materials, gold
    wid = ALL_ORDER[feature_craft_index % len(ALL_ORDER)]
    if wid not in weapon_stars:
        show_toast("먼저 장비를 획득하거나 제작하세요", (255, 145, 145)); snd_fail.play(); return
    if wid in feature_item_potentials:
        show_toast("이미 잠재 능력이 있어요", (200, 190, 220)); snd_fail.play(); return
    if feature_materials < 6 or gold < 450:
        show_toast("잠재 부여 비용: 재료 6개 + 450G", (255, 145, 145)); snd_fail.play(); return
    choices = [("atk", 0.05, "공격력 +5%"), ("spd", 0.06, "공격 속도 +6%"),
               ("crit", 3.0, "치명타 +3%"), ("hp", 1.0, "체력 +1"),
               ("xp", 0.05, "경험치 +5%"), ("gold", 0.05, "골드 +5%"),
               ("move", 0.12, "이동 속도 +0.12"), ("pick", 10.0, "줍기 범위 +10")]
    stat, value, label = random.choice(choices)
    feature_materials -= 6; gold -= 450
    feature_item_potentials[wid] = {"stat": stat, "value": value, "name": label}
    save_game(); snd_level.play()
    show_toast(f"잠재 능력 부여: {label}", (190, 155, 255))

def feature_cycle_dye():
    global feature_materials
    wid = ALL_ORDER[feature_craft_index % len(ALL_ORDER)]
    if wid not in weapon_stars:
        show_toast("도색하려면 장비를 먼저 획득하세요", (255, 145, 145)); snd_fail.play(); return
    if feature_materials < 1:
        show_toast("도색 비용: 재료 1개", (255, 145, 145)); snd_fail.play(); return
    feature_materials -= 1
    feature_item_dyes[wid] = (feature_item_dyes.get(wid, 0) + 1) % len(FEATURE_DYE_PALETTES)
    feature_apply_dyes()
    save_game(); snd_buy.play()
    show_toast(f"도색 완료: {FEATURE_DYE_PALETTES[feature_item_dyes[wid]][0]}", (220, 190, 255))

# -----------------------------------------------------------------------------
# Final integration pass: late stages, balance-safe boss pattern layer, combat
# skill effects, additional achievements, and screenshot-aligned UI helpers.
# -----------------------------------------------------------------------------

# Stage 8 opens after stage 6; stage 9 opens after stage 8. Challenge mode remains separate.
_feature_stage_unlocked_old = stage_unlocked
def stage_unlocked(sid):
    if sid == 8:
        return 6 in stages_cleared
    if sid == 9:
        return 8 in stages_cleared
    return _feature_stage_unlocked_old(sid)

FEATURE_EXTRA_ACHIEVEMENTS = [
    {"key": "clear8", "name": "수정 심연 정복", "desc": "스테이지 8 클리어", "reward": 900},
    {"key": "clear9", "name": "천공의 심판자", "desc": "스테이지 9 클리어", "reward": 1400},
]
for _extra_ach in FEATURE_EXTRA_ACHIEVEMENTS:
    if not any(a.get("key") == _extra_ach["key"] for a in ACHIEVEMENTS):
        ACHIEVEMENTS.append(_extra_ach)
_feature_check_achievements_old = check_achievements
def check_achievements():
    global gold
    _feature_check_achievements_old()
    conditions = {"clear8": 8 in stages_cleared, "clear9": 9 in stages_cleared}
    got_new = False
    for ach in FEATURE_EXTRA_ACHIEVEMENTS:
        if conditions.get(ach["key"], False) and not achv_done.get(ach["key"]):
            achv_done[ach["key"]] = True
            gold += ach["reward"]
            got_new = True
            show_toast(f"업적 달성! {ach['name']} +{ach['reward']}G", (255, 225, 120))
            snd_level.play()
    if got_new:
        save_game()

# Additional combat skills use current weapon damage and bounded cooldowns.
def feature_update_added_skills():
    if not isinstance(xt, dict):
        return
    # 중력장: 일반 적을 당겨 모은 뒤 범위 피해. 보스는 끌어당기지 않아 패턴이 깨지지 않습니다.
    gravity_lv = skill_levels.get("중력장", 0)
    xt.setdefault("feature_gravity_cd", 0)
    if gravity_lv > 0:
        xt["feature_gravity_cd"] += 1
        gravity_cd = max(190, 300 - 22 * gravity_lv)
        if xt["feature_gravity_cd"] >= gravity_cd:
            targets = [e for e in enemies if e.get("hp", 0) > 0 and
                       e["pos"].distance_to(player_pos) <= 120 + 12 * gravity_lv + enemy_types[e["kind"]]["radius"]]
            if targets:
                xt["feature_gravity_cd"] = 0
                radius = 120 + 12 * gravity_lv
                rings.append({"pos": player_pos.copy(), "r": radius, "life": 24, "max": 24,
                              "color": (165, 120, 255)})
                for enemy in targets[:16]:
                    vec = player_pos - enemy["pos"]
                    dist = vec.length()
                    if dist > 1 and not enemy.get("boss"):
                        enemy["pos"] += vec.normalize() * min(8.0, 3.5 + 0.55 * gravity_lv)
                    amount = projectile_damage * (0.32 + 0.08 * gravity_lv) + 1
                    feature_damage("중력장", enemy, amount, quiet=True)
                spawn_burst(player_pos, (185, 145, 255), 12)
                snd_zap.play()
                add_shake(3)

    # 성광: 가까운 적을 최대 7명까지 연쇄 공격하되, 멀리 떨어진 적으로 무한 전파되지 않습니다.
    holy_lv = skill_levels.get("성광", 0)
    xt.setdefault("feature_holy_cd", 0)
    if holy_lv > 0:
        xt["feature_holy_cd"] += 1
        holy_cd = max(170, 260 - 18 * holy_lv)
        if xt["feature_holy_cd"] >= holy_cd:
            targets = [e for e in enemies if e.get("hp", 0) > 0]
            if targets:
                xt["feature_holy_cd"] = 0
                previous = player_pos.copy()
                count = min(2 + holy_lv, len(targets))
                for hop in range(count):
                    target = min(targets, key=lambda item: item["pos"].distance_to(previous))
                    target_pos = target["pos"].copy()
                    if target_pos.distance_to(previous) > (185 if hop else 290):
                        break
                    xt["chain_arcs"].append({"a": previous.copy(), "b": target_pos.copy(),
                                              "life": 14, "max": 14,
                                              "seed": random.randint(0, 2**30)})
                    rings.append({"pos": target_pos.copy(), "r": 30 + holy_lv * 2,
                                  "life": 12, "max": 12, "color": (255, 225, 125)})
                    feature_damage("성광", target, projectile_damage * (0.65 + 0.10 * holy_lv) + 1,
                                   quiet=True)
                    spawn_burst(target_pos, (255, 235, 155), 4)
                    targets.remove(target)
                    previous = target_pos
                snd_zap.play()

# Add tough-but-telegraphed combo attacks to every boss. Their special hazards deal 4 HP.
_FEATURE_BOSS_PATTERN_OLD_UPDATE = update_boss
def update_boss(e):
    if e.get("hp", 0) <= 0:
        return
    # Weakening slightly slows boss decisions, while freezing stops a boss only for its short status duration.
    if e.get("feature_weaken", 0) > 0 and frame_tick % 5 == 0:
        return
    _FEATURE_BOSS_PATTERN_OLD_UPDATE(e)
    if e.get("hp", 0) <= 0:
        return

    max_hp = max(1, float(e.get("max_hp", e.get("hp", 1))))
    enraged = bool(e.get("phase_two") or e.get("hp", 0) <= max_hp * 0.30 or e.get("final"))
    if enraged and not e.get("feature_combo_enraged"):
        e["feature_combo_enraged"] = True
        e["feature_combo_cd"] = min(int(e.get("feature_combo_cd", 80)), 45)
        rings.append({"pos": e["pos"].copy(), "r": 100, "life": 22, "max": 22,
                      "color": enemy_types[e["kind"]]["color"]})
        spawn_burst(e["pos"], enemy_types[e["kind"]]["color"], 12)
        add_shake(5)
        show_toast("보스 분노! 연속 패턴이 빨라집니다", (255, 110, 100))

    pattern = e.get("feature_combo_pattern")
    if not pattern:
        e["feature_combo_cd"] = int(e.get("feature_combo_cd", 210)) - 1
        if e["feature_combo_cd"] <= 0:
            pattern = random.choice(("marks", "fan"))
            e["feature_combo_pattern"] = pattern
            e["feature_combo_t"] = 0
            if pattern == "marks":
                px = max(50, min(WIDTH - 50, player_pos.x))
                py = max(90, min(HEIGHT - 50, player_pos.y))
                e["feature_combo_marks"] = [
                    pygame.Vector2(max(45, min(WIDTH - 45, px - 82)), py),
                    pygame.Vector2(px, max(90, min(HEIGHT - 45, py + 48))),
                    pygame.Vector2(max(45, min(WIDTH - 45, px + 82)), py),
                ]
                snd_boss.play()
            else:
                direction = player_pos - e["pos"]
                e["feature_combo_angle"] = angle_of(direction) if direction.length() > 0 else 0.0
                snd_zap.play()
        return

    e["feature_combo_t"] = int(e.get("feature_combo_t", 0)) + 1
    t = e["feature_combo_t"]
    if pattern == "marks" and t == 44:
        marks = e.get("feature_combo_marks", [])
        for pos in marks:
            rings.append({"pos": pos.copy(), "r": 58, "life": 16, "max": 16,
                          "color": enemy_types[e["kind"]]["color"]})
            spawn_burst(pos, enemy_types[e["kind"]]["color"], 10)
            if pos.distance_to(player_pos) <= 48 + player_radius:
                hurt_player(4)
        # 폭발 직후 작은 탄막을 추가해 이동 방향까지 생각하게 합니다.
        num = 12 if enraged else 8
        speed = 4.1 if enraged else 3.5
        base_angle = random.uniform(0, 360)
        for i in range(num):
            _boss_shot(e["pos"], base_angle + 360 * i / num, speed,
                       color=enemy_types[e["kind"]]["color"])
        add_shake(6)
        snd_boss.play()
        e["feature_combo_pattern"] = None
        e["feature_combo_marks"] = []
        e["feature_combo_cd"] = 235 if enraged else 315
    elif pattern == "fan" and t == 36:
        n = 11 if enraged else 7
        spread = 7 if enraged else 10
        speed = 4.7 if enraged else 4.0
        aim = float(e.get("feature_combo_angle", 0.0))
        for i in range(n):
            angle = aim + (i - (n - 1) / 2) * spread
            _boss_shot(e["pos"], angle, speed, color=enemy_types[e["kind"]]["color"])
        snd_zap.play()
    elif pattern == "fan" and t == 50:
        # 2차 좁은 탄막은 위치 고정 플레이를 막지만, 넓은 안전 간격을 남깁니다.
        aim = angle_of(player_pos - e["pos"]) if player_pos.distance_to(e["pos"]) > 0 else 0
        offsets = (-18, -9, 0, 9, 18) if enraged else (-14, 0, 14)
        for offset in offsets:
            _boss_shot(e["pos"], aim + offset, 4.8 if enraged else 4.1,
                       color=enemy_types[e["kind"]]["color"])
        snd_zap.play()
        e["feature_combo_pattern"] = None
        e["feature_combo_cd"] = 220 if enraged else 300
    elif pattern == "fan" and t > 55:
        e["feature_combo_pattern"] = None
        e["feature_combo_cd"] = 220 if enraged else 300

_FEATURE_BOSS_PATTERN_OLD_DRAW = draw_boss_layer
def draw_boss_layer(layer, e):
    _FEATURE_BOSS_PATTERN_OLD_DRAW(layer, e)
    pattern = e.get("feature_combo_pattern")
    t = int(e.get("feature_combo_t", 0))
    if pattern == "marks":
        for pos in e.get("feature_combo_marks", []):
            radius = 42 + int(5 * math.sin(frame_tick * 0.35))
            pygame.draw.circle(layer, (255, 75, 75, 55), (int(pos.x), int(pos.y)), radius, 0)
            pygame.draw.circle(layer, (255, 115, 95, 210), (int(pos.x), int(pos.y)), radius, 3)
            pygame.draw.circle(layer, (255, 235, 215, 220), (int(pos.x), int(pos.y)), max(8, radius - 10), 2)
    elif pattern == "fan":
        a = float(e.get("feature_combo_angle", 0.0))
        spread = 32 if e.get("phase_two") or e.get("final") else 24
        for offset in (-spread, 0, spread):
            end = e["pos"] + pygame.Vector2(1, 0).rotate(a + offset) * 820
            pygame.draw.line(layer, (255, 95, 90, 42), e["pos"], end, 24)
            pygame.draw.line(layer, (255, 170, 150, 165), e["pos"], end, 2)

# Ensure boss attacks consistently deal 4 HP and make the amount visible when damage lands.
_FEATURE_FINAL_HURT_PLAYER_OLD = hurt_player
def hurt_player(damage=1):
    before_hp = player_hp
    result = _FEATURE_FINAL_HURT_PLAYER_OLD(damage)
    lost = max(0, int(before_hp - player_hp))
    if lost > 0:
        floaters.append({"pos": player_pos + pygame.Vector2(0, -30), "text": f"-{lost} HP",
                         "color": (255, 95, 100) if lost >= 2 else (255, 165, 145), "life": 48})
    return result

# ============================================================
# THEME UPDATE: themed mini-bosses, adaptive procedural soundtrack,
# richer character/equipment/rune/pet rendering. No external assets needed.
# ============================================================

# ----- 1) Theme-specific boss sprites and data -----
# Existing pixel templates are recoloured so every region has a recognisable boss silhouette.
THEME_BOSS_SPRITES = {
    "magma_titan": make_sprite(GOLEM_PIXELS, {
        "d": (48, 16, 18), "g": (155, 42, 25), "l": (245, 90, 28),
        "e": (255, 225, 95), "m": (95, 28, 24)}, 6),
    "inferno_dragon": make_sprite(DRAGON_PIXELS, {
        "d": (48, 13, 16), "r": (235, 55, 25), "R": (145, 24, 18),
        "o": (255, 135, 30), "y": (255, 235, 115), "k": (26, 12, 12),
        "w": (255, 240, 195), "n": (120, 35, 18), "f": (190, 50, 28)}, 6),
    "crypt_knight": make_sprite(ORC_PIXELS, {
        "d": (24, 26, 38), "g": (105, 115, 130), "r": (175, 45, 65),
        "w": (225, 235, 235), "b": (75, 62, 72), "B": (45, 43, 55),
        "m": (165, 200, 215)}, 5),
    "scorpion_king": make_sprite(SCORP_PIXELS, {
        "c": (225, 175, 65), "d": (105, 60, 24), "o": (255, 220, 105),
        "k": (35, 22, 15)}, 6),
    "dune_emperor": make_sprite(ORC_PIXELS, {
        "d": (70, 43, 22), "g": (190, 135, 62), "r": (195, 75, 35),
        "w": (255, 230, 165), "b": (140, 88, 42), "B": (95, 55, 25),
        "m": (255, 210, 95)}, 5),
    "sand_wyrm": make_sprite(DRAGON_PIXELS, {
        "d": (60, 40, 23), "r": (200, 125, 45), "R": (130, 75, 27),
        "o": (245, 205, 105), "y": (255, 240, 170), "k": (32, 24, 18),
        "w": (255, 232, 180), "n": (95, 55, 24), "f": (180, 110, 43)}, 6),
    "bog_witch": make_sprite(LICH_PIXELS, {
        "y": (210, 240, 115), "d": (18, 32, 22), "w": (190, 225, 170),
        "g": (120, 255, 95), "p": (48, 110, 55), "P": (24, 65, 36)}, 5),
    "swamp_hydra": make_sprite(DRAGON_PIXELS, {
        "d": (20, 48, 37), "r": (55, 160, 80), "R": (25, 105, 55),
        "o": (140, 235, 95), "y": (225, 255, 135), "k": (10, 28, 24),
        "w": (220, 255, 200), "n": (45, 100, 50), "f": (80, 190, 100)}, 6),
    "marsh_titan": make_sprite(GOLEM_PIXELS, {
        "d": (20, 38, 31), "g": (70, 120, 70), "l": (125, 175, 75),
        "e": (205, 255, 95), "m": (35, 75, 42)}, 6),
    "crystal_sentinel": make_sprite(GOLEM_PIXELS, {
        "d": (20, 35, 70), "g": (55, 120, 185), "l": (110, 215, 255),
        "e": (220, 255, 255), "m": (40, 70, 145)}, 6),
    "crystal_dragon": make_sprite(DRAGON_PIXELS, {
        "d": (15, 35, 65), "r": (60, 155, 235), "R": (35, 90, 180),
        "o": (130, 230, 255), "y": (240, 255, 255), "k": (15, 25, 45),
        "w": (230, 250, 255), "n": (35, 70, 130), "f": (90, 190, 255)}, 6),
    "sky_archon": make_sprite(MAGE_PIXELS, {
        "d": (35, 28, 70), "p": (145, 100, 220), "k": (245, 220, 175),
        "y": (255, 225, 105), "o": (255, 250, 205)}, 6),
    "celestial_dragon": make_sprite(DRAGON_PIXELS, {
        "d": (35, 25, 70), "r": (155, 90, 220), "R": (90, 45, 160),
        "o": (255, 210, 105), "y": (255, 250, 210), "k": (25, 20, 48),
        "w": (255, 255, 255), "n": (100, 60, 150), "f": (205, 155, 255)}, 6),
    "frost_warlord": make_sprite(YETI_PIXELS, {
        "d": (40, 65, 105), "w": (220, 245, 255), "k": (25, 45, 80),
        "b": (95, 175, 235)}, 6),
    "prism_colossus": make_sprite(GOLEM_PIXELS, {
        "d": (22, 35, 65), "g": (75, 135, 195), "l": (165, 235, 255),
        "e": (255, 255, 255), "m": (55, 90, 170)}, 6),
    "astral_seraph": make_sprite(MAGE_PIXELS, {
        "d": (45, 28, 75), "p": (155, 110, 220), "k": (255, 230, 190),
        "y": (255, 235, 145), "o": (255, 255, 235)}, 6),
    "void_reaper": make_sprite(LICH_PIXELS, {
        "y": (175, 120, 255), "d": (15, 10, 30), "w": (205, 190, 255),
        "g": (115, 65, 220), "p": (55, 25, 105), "P": (25, 12, 55)}, 5),
    "abyss_hydra": make_sprite(DRAGON_PIXELS, {
        "d": (20, 12, 40), "r": (100, 45, 165), "R": (55, 25, 100),
        "o": (210, 100, 255), "y": (240, 215, 255), "k": (12, 8, 25),
        "w": (240, 225, 255), "n": (40, 20, 80), "f": (150, 70, 210)}, 6),
}

THEME_BOSS_META = {
    "magma_titan":     {"name": "마그마 타이탄", "radius": 42, "color": (255, 90, 35), "base": 150, "growth": 14, "gold": 130},
    "inferno_dragon":  {"name": "인페르노 드래곤", "radius": 42, "color": (255, 100, 35), "base": 175, "growth": 16, "gold": 155},
    "crypt_knight":    {"name": "망자의 기사", "radius": 34, "color": (185, 205, 220), "base": 125, "growth": 13, "gold": 120},
    "scorpion_king":   {"name": "전갈 왕", "radius": 34, "color": (235, 185, 70), "base": 160, "growth": 15, "gold": 140},
    "dune_emperor":    {"name": "사막 황제", "radius": 34, "color": (230, 155, 65), "base": 175, "growth": 16, "gold": 150},
    "sand_wyrm":       {"name": "모래 와이번", "radius": 42, "color": (235, 185, 95), "base": 190, "growth": 17, "gold": 165},
    "bog_witch":       {"name": "늪의 마녀", "radius": 30, "color": (145, 230, 85), "base": 165, "growth": 15, "gold": 145},
    "swamp_hydra":     {"name": "독늪 히드라", "radius": 42, "color": (95, 225, 95), "base": 205, "growth": 18, "gold": 180},
    "marsh_titan":     {"name": "늪지 거수", "radius": 42, "color": (130, 190, 80), "base": 195, "growth": 17, "gold": 170},
    "crystal_sentinel":{"name": "수정 감시자", "radius": 42, "color": (105, 205, 255), "base": 190, "growth": 17, "gold": 175},
    "crystal_dragon":  {"name": "수정 드래곤", "radius": 42, "color": (100, 195, 255), "base": 220, "growth": 19, "gold": 200},
    "sky_archon":      {"name": "천공의 집행관", "radius": 32, "color": (230, 190, 255), "base": 215, "growth": 19, "gold": 205},
    "celestial_dragon":{"name": "천상의 용", "radius": 44, "color": (255, 210, 125), "base": 250, "growth": 20, "gold": 230},
    "frost_warlord":   {"name": "설원 군주", "radius": 38, "color": (145, 220, 255), "base": 145, "growth": 15, "gold": 130},
    "prism_colossus":  {"name": "프리즘 거수", "radius": 44, "color": (120, 210, 255), "base": 215, "growth": 18, "gold": 195},
    "astral_seraph":   {"name": "아스트랄 세라핌", "radius": 35, "color": (255, 225, 150), "base": 280, "growth": 22, "gold": 260},
    "void_reaper":     {"name": "심연의 사신", "radius": 35, "color": (180, 110, 255), "base": 195, "growth": 18, "gold": 185},
    "abyss_hydra":     {"name": "공허 히드라", "radius": 44, "color": (165, 95, 245), "base": 220, "growth": 19, "gold": 205},
}

for _kind, _meta in THEME_BOSS_META.items():
    _sprite = THEME_BOSS_SPRITES[_kind]
    enemy_types[_kind] = _bt(_meta["radius"], _meta["color"], _sprite)
    BOSS_NAMES[_kind] = _meta["name"]
    GOLD_VALUE[_kind] = _meta["gold"]

BOSS_NEW.update(THEME_BOSS_META.keys())
ENDLESS_BOSSES[:] = [
    "orc", "golem", "dragon", "magma_titan", "inferno_dragon", "vampire",
    "crypt_knight", "lich", "scorpion_king", "dune_emperor", "sand_wyrm",
    "bog_witch", "swamp_hydra", "marsh_titan", "frostgiant", "frost_warlord",
    "crystal_sentinel", "prism_colossus", "crystal_dragon", "sky_archon",
    "celestial_dragon", "astral_seraph", "void_reaper", "abyss_hydra"
]
# Mix familiar bosses with new region bosses in the existing six-round Boss Rush.
if "FEATURE_BOSS_RUSH_SEQUENCE" in globals():
    FEATURE_BOSS_RUSH_SEQUENCE[:] = [
        "orc", "frost_warlord", "magma_titan", "scorpion_king", "crystal_dragon", "astral_seraph"
    ]

# The first encounter on each stage is a one-bar themed mini-boss; later/final encounters retain two bars.
THEME_STAGE_BOSS_ROSTERS = {
    1: [("orc", 4500, 0.95), ("dragon", 10800, 1.05)],
    2: [("frost_warlord", 3900, 0.98), ("frostgiant", 9900, 1.12)],
    3: [("magma_titan", 3300, 1.10), ("inferno_dragon", 7800, 1.28)],
    4: [("vampire", 3600, 1.18), ("crypt_knight", 7800, 1.32), ("lich", 12600, 1.55)],
    5: [("scorpion_king", 3600, 1.22), ("dune_emperor", 7800, 1.40), ("sand_wyrm", 12600, 1.68)],
    6: [("bog_witch", 3300, 1.24), ("marsh_titan", 7500, 1.42), ("swamp_hydra", 12600, 1.72)],
    8: [("crystal_sentinel", 3300, 1.38), ("prism_colossus", 7500, 1.62), ("crystal_dragon", 12000, 1.90)],
    9: [("sky_archon", 3000, 1.45), ("celestial_dragon", 7200, 1.78), ("astral_seraph", 11700, 1.95)],
}
for _sid, _roster in THEME_STAGE_BOSS_ROSTERS.items():
    STAGES[_sid]["bosses"] = list(_roster)
STAGES[2]["desc"] = "설원 군주를 넘어 서리 거인을 쓰러뜨리세요"
STAGES[3]["desc"] = "용암 지대의 마그마 타이탄과 인페르노 드래곤을 처치하세요"
STAGES[4]["desc"] = "흡혈 군주 → 망자의 기사 → 리치의 저주를 돌파하세요"
STAGES[5]["desc"] = "전갈 왕 → 사막 황제 → 모래 와이번"
STAGES[6]["desc"] = "늪의 마녀 → 늪지 거수 → 독늪 히드라"
STAGES[8]["desc"] = "수정 감시자 → 프리즘 거수 → 수정 드래곤"
STAGES[9]["desc"] = "천공의 집행관 → 천상의 용 → 아스트랄 세라핌"

_THEME_OLD_SPAWN_BOSS = spawn_boss

def spawn_boss(kind, hp_scale=None, final=False):
    """모든 보스의 스폰/HP 배율을 한곳에서 정규화합니다."""
    global banner_text, banner_timer, banner_color, banner_blink
    count_before = boss_count
    scale = float(hp_scale) if hp_scale is not None else 1.0 + (count_before // max(1, len(ENDLESS_BOSSES))) * 0.6
    _THEME_OLD_SPAWN_BOSS(kind, hp_scale, final)
    boss = next((e for e in reversed(enemies) if e.get("boss") and e.get("kind") == kind), None)
    if boss is None:
        return
    if kind in THEME_BOSS_META:
        meta = THEME_BOSS_META[kind]
        base_hp = int((meta["base"] + meta["growth"] * level) * scale)
    else:
        hp_table = {
            "orc": (50, 10), "golem": (110, 12), "dragon": (140, 15),
            "vampire": (95, 11), "lich": (125, 13), "frostgiant": (170, 16),
        }
        base, growth = hp_table.get(kind, (135, 13))
        base_hp = int((base + growth * level) * scale)
    # The established boss system uses two bars. The first stage encounter is a shorter mini-boss.
    is_stage_mini = bool((cur_stage in THEME_STAGE_BOSS_ROSTERS and stage_boss_idx == 1 and not final)
                         or (challenge and count_before % 2 == 0 and not final))
    boss["mini_boss"] = is_stage_mini
    boss["hp"] = max(1, base_hp if is_stage_mini else base_hp * 2)
    boss["max_hp"] = boss["hp"]
    boss["boss_health_bars"] = 1 if is_stage_mini else 2
    boss["final"] = bool(final)
    boss["phase_two"] = False
    boss["phase_skill_timer"] = 0
    boss["theme_attack"] = 0
    boss["theme_combo_done"] = False
    boss["atk"] = int(boss.get("atk", 0))
    if kind in ("dragon", "lich", "inferno_dragon", "sand_wyrm", "crystal_dragon", "celestial_dragon", "abyss_hydra", "astral_seraph"):
        boss["pos"] = pygame.Vector2(WIDTH / 2, -90)
        boss["state"] = "enter"
    else:
        boss["state"] = "chase"
    boss["st_timer"] = 0
    boss["cooldown"] = 74 if is_stage_mini else 62
    if is_stage_mini:
        banner_text = f"MINI BOSS · {BOSS_NAMES[kind]} 등장"
        banner_color = THEME_BOSS_META.get(kind, {}).get("color", (255, 200, 100))
        banner_timer = 150
        banner_blink = True
    else:
        banner_text = f"WARNING! {BOSS_NAMES[kind]} 등장"
        banner_color = THEME_BOSS_META.get(kind, {}).get("color", (255, 90, 90))
        banner_timer = 150
        banner_blink = True
    # The original spawn wrapper already plays the boss alert once.

# ----- 2) Distinct boss behaviours with clear telegraphs -----
THEME_BOSS_ATTACKS = {
    "magma_titan": ("marks", "burst"), "inferno_dragon": ("fan", "burst"),
    "crypt_knight": ("charge", "fan"), "scorpion_king": ("marks", "fan"),
    "dune_emperor": ("marks", "fan"), "sand_wyrm": ("charge", "marks"),
    "bog_witch": ("summon", "marks"), "swamp_hydra": ("marks", "fan"),
    "marsh_titan": ("burst", "charge"), "crystal_sentinel": ("fan", "marks"),
    "crystal_dragon": ("fan", "burst"), "sky_archon": ("fan", "marks"),
    "celestial_dragon": ("marks", "fan"),
    "frost_warlord": ("charge", "fan"), "prism_colossus": ("marks", "burst"),
    "astral_seraph": ("fan", "burst"), "void_reaper": ("summon", "marks"),
    "abyss_hydra": ("burst", "fan"),
}
THEME_BOSS_MOTION = {
    "magma_titan": 0.72, "inferno_dragon": 1.05, "crypt_knight": 1.20,
    "scorpion_king": 1.35, "dune_emperor": 1.00, "sand_wyrm": 1.15,
    "bog_witch": 0.78, "swamp_hydra": 0.82, "marsh_titan": 0.72,
    "crystal_sentinel": 0.75, "crystal_dragon": 1.18, "sky_archon": 1.25,
    "celestial_dragon": 1.18, "frost_warlord": 1.06, "prism_colossus": 0.76,
    "astral_seraph": 1.26, "void_reaper": 1.14, "abyss_hydra": 1.02,
}

def _theme_boss_shot(e, angle, speed, color=None):
    col = color or enemy_types[e["kind"]]["color"]
    _boss_shot(e["pos"], angle, speed, life=240, color=col)

def _theme_safe_pos(x, y, margin=48):
    return pygame.Vector2(max(margin, min(WIDTH - margin, x)),
                          max(90, min(HEIGHT - margin, y)))

def _theme_boss_attack(e, enraged):
    kind = e["kind"]
    attack_list = THEME_BOSS_ATTACKS.get(kind, ("marks", "fan"))
    e["theme_attack"] = int(e.get("theme_attack", 0)) + 1
    mode = attack_list[(e["theme_attack"] - 1) % len(attack_list)]
    e["theme_mode"] = mode
    e["st_timer"] = 0
    e["dur"] = (28 if enraged else 42) if mode in ("marks", "summon") else (24 if enraged else 36)
    if mode == "marks":
        base = player_pos.copy()
        spread = 64 if enraged else 78
        e["theme_marks"] = [
            _theme_safe_pos(base.x - spread, base.y + 24),
            _theme_safe_pos(base.x, base.y - 22),
            _theme_safe_pos(base.x + spread, base.y + 24),
        ]
        e["state"] = "theme_marks_windup"
    elif mode == "charge":
        direction = player_pos - e["pos"]
        e["theme_angle"] = angle_of(direction) if direction.length() else 0.0
        e["theme_charge_vec"] = pygame.Vector2(1, 0).rotate(e["theme_angle"])
        e["state"] = "theme_charge_windup"
    elif mode == "summon":
        e["state"] = "theme_summon_windup"
    elif mode == "burst":
        e["theme_angle"] = angle_of(player_pos - e["pos"]) if player_pos.distance_to(e["pos"]) else 0.0
        e["state"] = "theme_burst_windup"
    else:
        direction = player_pos - e["pos"]
        e["theme_angle"] = angle_of(direction) if direction.length() else 0.0
        e["state"] = "theme_fan_windup"
    snd_boss.play()

def _theme_boss_do_attack(e, enraged):
    kind = e["kind"]
    mode = e.get("theme_mode", "fan")
    col = enemy_types[kind]["color"]
    if mode == "marks":
        for pos in e.get("theme_marks", []):
            rings.append({"pos": pos.copy(), "r": 62, "life": 18, "max": 18, "color": col})
            spawn_burst(pos, col, 12)
            if pos.distance_to(player_pos) <= 52 + player_radius:
                hurt_player(4)
        # Scattered aftershock shots punish standing still without filling the whole screen.
        n = 10 if enraged else 6
        start = random.uniform(0, 360)
        for i in range(n):
            _theme_boss_shot(e, start + 360 * i / n, 3.2 if enraged else 2.8, col)
    elif mode == "charge":
        rings.append({"pos": e["pos"].copy(), "r": 90, "life": 14, "max": 14, "color": col})
        for offset in (-18, 0, 18):
            _theme_boss_shot(e, e.get("theme_angle", 0) + offset, 4.0 if enraged else 3.5, col)
    elif mode == "summon":
        minion_kind = ("shroom" if kind in ("bog_witch", "void_reaper") else
                       ("ice_wisp" if kind.startswith("crystal") or kind == "prism_colossus" else "imp"))
        if minion_kind not in enemy_types:
            minion_kind = "goblin"
        for i in range(3 if enraged else 2):
            pos = _theme_safe_pos(e["pos"].x + random.randint(-75, 75), e["pos"].y + random.randint(-60, 60))
            enemies.append(make_enemy(minion_kind, pos))
        spawn_burst(e["pos"], col, 15)
    elif mode == "burst":
        n = 18 if enraged else 12
        phase = random.uniform(0, 360)
        for i in range(n):
            _theme_boss_shot(e, phase + 360 * i / n, 4.0 if enraged else 3.2, col)
        # Three visible ground impacts accompany the radial burst.
        offsets = (-94, 0, 94)
        for off in offsets:
            pos = _theme_safe_pos(e["pos"].x + off, e["pos"].y + random.randint(-28, 28))
            rings.append({"pos": pos.copy(), "r": 44, "life": 14, "max": 14, "color": col})
            if pos.distance_to(player_pos) <= 34 + player_radius:
                hurt_player(4)
    else:  # fan
        base = float(e.get("theme_angle", 0.0))
        n = 11 if enraged else 7
        spread = 8 if enraged else 11
        for i in range(n):
            _theme_boss_shot(e, base + (i - (n - 1) / 2) * spread, 4.5 if enraged else 3.7, col)
        # A second narrower volley is only used at the enraged threshold.
        if enraged:
            aim = angle_of(player_pos - e["pos"]) if player_pos.distance_to(e["pos"]) else base
            for off in (-10, 0, 10):
                _theme_boss_shot(e, aim + off, 4.9, col)
    snd_zap.play()
    add_shake(4 if not enraged else 6)

def update_theme_boss(e):
    """Unique patterns for region bosses; every damaging pattern is telegraphed and deals 4 HP."""
    if e.get("hp", 0) <= 0:
        return
    # Shared two-bar transition burst remains active for custom bosses too.
    if e.get("phase_skill_timer", 0) > 0:
        e["phase_skill_timer"] -= 1
        if e["phase_skill_timer"] <= 0:
            n = 16 if e.get("final") else 12
            base = random.uniform(0, 360)
            for i in range(n):
                _theme_boss_shot(e, base + 360 * i / n, 4.2 if e.get("final") else 3.5)
            snd_zap.play()
        return
    e["st_timer"] = int(e.get("st_timer", 0)) + 1
    to_player = player_pos - e["pos"]
    dist = to_player.length()
    if dist <= 0:
        to_player = pygame.Vector2(0, 1)
        dist = 1
    enrage = bool(e.get("phase_two") or e.get("hp", 0) <= e.get("max_hp", 1) * 0.32 or e.get("final"))
    speed = THEME_BOSS_MOTION.get(e["kind"], 1.0) * (1.22 if enrage else 1.0)
    st = e.get("state", "chase")
    if st == "enter":
        e["pos"].y += 2.1 if not enrage else 2.8
        if e["pos"].y >= 105:
            e["state"] = "chase"
            e["st_timer"] = 0
            e["cooldown"] = 55
        return
    if st == "chase":
        if e["kind"] in ("inferno_dragon", "sand_wyrm", "crystal_dragon", "celestial_dragon"):
            if dist > 210:
                e["pos"] += to_player.normalize() * speed
            elif dist < 140:
                e["pos"] -= to_player.normalize() * speed * 0.6
        elif dist > 100:
            e["pos"] += to_player.normalize() * speed
        e["pos"].x = max(48, min(WIDTH - 48, e["pos"].x))
        e["pos"].y = max(72, min(HEIGHT - 48, e["pos"].y))
        e["cooldown"] = int(e.get("cooldown", 60)) - 1
        if e["cooldown"] <= 0:
            _theme_boss_attack(e, enrage)
        return
    if st.endswith("_windup"):
        if e["st_timer"] >= int(e.get("dur", 32)):
            mode = e.get("theme_mode")
            if mode == "charge":
                e["state"] = "theme_charge"
                e["st_timer"] = 0
            elif mode == "fan":
                e["state"] = "theme_fan_fire"
                e["st_timer"] = 0
                _theme_boss_do_attack(e, enrage)
            else:
                _theme_boss_do_attack(e, enrage)
                e["state"] = "recover"
                e["st_timer"] = 0
                e["cooldown"] = 75 if enrage else 108
        return
    if st == "theme_charge":
        vec = e.get("theme_charge_vec", pygame.Vector2(1, 0))
        e["pos"] += vec * (8.0 if enrage else 6.0)
        e["pos"].x = max(35, min(WIDTH - 35, e["pos"].x))
        e["pos"].y = max(70, min(HEIGHT - 35, e["pos"].y))
        if e["pos"].distance_to(player_pos) < enemy_types[e["kind"]]["radius"] + player_radius + 6:
            hurt_player(4)
            spawn_burst(player_pos, enemy_types[e["kind"]]["color"], 8)
        if e["st_timer"] >= (22 if enrage else 17):
            rings.append({"pos": e["pos"].copy(), "r": 72, "life": 16, "max": 16,
                          "color": enemy_types[e["kind"]]["color"]})
            e["state"] = "recover"
            e["st_timer"] = 0
            e["cooldown"] = 58 if enrage else 82
        return
    if st == "theme_fan_fire":
        # The immediate fan is fired at windup completion; after 15 frames, fire one aimed follow-up.
        if e["st_timer"] == 15:
            aim_vec = player_pos - e["pos"]
            aim = angle_of(aim_vec) if aim_vec.length() else float(e.get("theme_angle", 0.0))
            _theme_boss_shot(e, aim - (8 if enrage else 12), 4.4)
            _theme_boss_shot(e, aim, 4.8 if enrage else 4.2)
            _theme_boss_shot(e, aim + (8 if enrage else 12), 4.4)
        if e["st_timer"] >= (31 if enrage else 37):
            e["state"] = "recover"
            e["st_timer"] = 0
            e["cooldown"] = 64 if enrage else 94
        return
    if st == "recover":
        if e["st_timer"] >= (29 if enrage else 44):
            e["state"] = "chase"
            e["st_timer"] = 0
            e["cooldown"] = 46 if enrage else 68
        return
    e["state"] = "chase"
    e["st_timer"] = 0

_THEME_OLD_UPDATE_BOSS = update_boss
def update_boss(e):
    if e.get("kind") in THEME_BOSS_META:
        return update_theme_boss(e)
    return _THEME_OLD_UPDATE_BOSS(e)

_THEME_OLD_DRAW_BOSS_LAYER = draw_boss_layer
def draw_boss_layer(layer, e):
    _THEME_OLD_DRAW_BOSS_LAYER(layer, e)
    if e.get("kind") not in THEME_BOSS_META:
        return
    kind = e["kind"]
    col = enemy_types[kind]["color"]
    pos = e["pos"]
    center = (int(pos.x), int(pos.y))
    state_now = e.get("state", "chase")
    progress = min(1.0, e.get("st_timer", 0) / max(1, e.get("dur", 36)))
    if state_now == "theme_marks_windup":
        for mark in e.get("theme_marks", []):
            mc = (int(mark.x), int(mark.y))
            radius = 34 + int(12 * progress)
            pygame.draw.circle(layer, (*col, 36 + int(progress * 70)), mc, radius)
            pygame.draw.circle(layer, (*col, 210), mc, radius, 3)
            pygame.draw.circle(layer, (255, 245, 220, 220), mc, max(4, radius - 10), 1)
    elif state_now == "theme_charge_windup":
        angle = float(e.get("theme_angle", 0.0))
        end = pos + pygame.Vector2(1, 0).rotate(angle) * 650
        pygame.draw.line(layer, (*col, 40 + int(progress * 65)), pos, end, 24)
        pygame.draw.line(layer, (*col, 210), pos, end, 2)
    elif state_now == "theme_fan_windup":
        angle = float(e.get("theme_angle", 0.0))
        for offset in (-28, -18, -9, 0, 9, 18, 28):
            end = pos + pygame.Vector2(1, 0).rotate(angle + offset) * 580
            pygame.draw.line(layer, (*col, 38 + int(progress * 55)), pos, end, 8)
        pygame.draw.circle(layer, (*col, 180), center, 28 + int(progress * 18), 2)
    elif state_now == "theme_burst_windup":
        radius = 35 + int(progress * 115)
        pygame.draw.circle(layer, (*col, 45 + int(progress * 70)), center, radius, 4)
        pygame.draw.circle(layer, (255, 245, 220, 180), center, max(8, radius - 20), 2)
    elif state_now == "theme_summon_windup":
        pygame.draw.circle(layer, (*col, 50 + int(progress * 90)), center, 35 + int(progress * 50), 4)
        for i in range(4):
            a = frame_tick * 3 + i * 90
            point = pos + pygame.Vector2(1, 0).rotate(a) * (40 + 20 * progress)
            pygame.draw.circle(layer, (240, 255, 235, 220), (int(point.x), int(point.y)), 4)

# Make the mini-boss health bar treatment reflect its single-bar health pool.
# A separate small badge keeps the encounter identity readable without covering the boss sprite.
_THEME_OLD_DRAW_WORLD = draw_world

# ----- 3) Stage-aware procedural soundtrack -----
# Each style is generated in memory; no MP3/WAV downloads or extra folders are required.
_THEME_MUSIC_RATE = 22050
_THEME_MUSIC_CONFIG = {
    "dungeon": {"bpm": 92, "root": 110.00, "scale": [0, 3, 5, 7, 10], "chords": [0, 8, 5, 10], "motif": [0, 2, 4, 2, 1, 3, 4, 3, 0, 2, 4, 1, 3, 2, 1, -1]},
    "ice": {"bpm": 78, "root": 98.00, "scale": [0, 2, 5, 7, 9], "chords": [0, 7, 5, 9], "motif": [4, 2, 1, -1, 3, 1, 0, -1, 4, 3, 1, 2, 0, -1, 1, -1]},
    "lava": {"bpm": 112, "root": 82.41, "scale": [0, 1, 5, 7, 8], "chords": [0, 1, 8, 7], "motif": [0, 2, 4, 3, 0, 4, 2, 1, 0, 2, 3, 4, 2, 1, 0, -1]},
    "grave": {"bpm": 84, "root": 92.50, "scale": [0, 2, 3, 7, 8], "chords": [0, 8, 3, 7], "motif": [4, -1, 2, 1, 3, -1, 1, 0, 4, 2, -1, 3, 1, 0, -1, -1]},
    "desert": {"bpm": 101, "root": 87.31, "scale": [0, 1, 4, 5, 7, 8], "chords": [0, 1, 5, 8], "motif": [0, 2, 3, 5, 3, 2, 1, -1, 0, 3, 5, 4, 2, 1, 0, -1]},
    "swamp": {"bpm": 88, "root": 73.42, "scale": [0, 3, 5, 6, 10], "chords": [0, 6, 3, 10], "motif": [0, 3, 1, -1, 4, 2, 1, -1, 0, 1, 4, 3, 1, 2, 0, -1]},
    "abyss": {"bpm": 104, "root": 65.41, "scale": [0, 3, 5, 6, 10], "chords": [0, 3, 8, 6], "motif": [0, -1, 3, 4, 2, -1, 1, 0, 4, 3, 1, 2, 0, -1, 3, -1]},
    "crystal": {"bpm": 96, "root": 123.47, "scale": [0, 2, 4, 7, 11], "chords": [0, 7, 4, 11], "motif": [4, 2, 4, 3, 1, -1, 2, 4, 3, 1, 0, 2, 4, -1, 3, 1]},
    "sky": {"bpm": 100, "root": 110.00, "scale": [0, 2, 4, 7, 9], "chords": [0, 9, 5, 7], "motif": [0, 2, 4, 2, 3, 4, 2, 1, 0, 2, 4, 5, 4, 2, 1, -1]},
}

def _theme_note(root, semitone):
    return root * (2.0 ** (semitone / 12.0))

def _theme_build_music(style):
    cfg = _THEME_MUSIC_CONFIG.get(style, _THEME_MUSIC_CONFIG["dungeon"])
    rate = _THEME_MUSIC_RATE
    bpm = float(cfg["bpm"])
    beats = 16  # four-bar looping cue
    duration = beats * 60.0 / bpm
    count = int(rate * duration)
    root = float(cfg["root"])
    scale = cfg["scale"]
    chords = cfg["chords"]
    motif = cfg["motif"]
    output = array.array("h")
    for idx in range(count):
        t = idx / rate
        beat_pos = t * bpm / 60.0
        beat_idx = int(beat_pos) % beats
        frac = beat_pos - int(beat_pos)
        chord = chords[(beat_idx // 4) % len(chords)]
        bass_hz = _theme_note(root * 0.5, chord)
        bass = math.sin(2.0 * math.pi * bass_hz * t) * math.exp(-frac * 3.2) * 0.17
        pad_hz1 = _theme_note(root, chord + 12)
        pad_hz2 = _theme_note(root, chord + 19)
        pad = (math.sin(2.0 * math.pi * pad_hz1 * t) * 0.045 +
               math.sin(2.0 * math.pi * pad_hz2 * t) * 0.026)
        half_idx = int(beat_pos * 2.0) % len(motif)
        note_idx = motif[half_idx]
        melody = 0.0
        if note_idx >= 0:
            note_hz = _theme_note(root * 2.0, scale[note_idx % len(scale)])
            note_phase = (beat_pos * 2.0) % 1.0
            env = math.exp(-note_phase * 4.5)
            melody = math.sin(2.0 * math.pi * note_hz * t) * env * 0.10
        # Soft drum pulses add a pulse without overpowering the stage ambience.
        kick = 0.0
        if beat_idx % 4 == 0:
            kick = math.sin(2.0 * math.pi * (74.0 - 28.0 * frac) * t) * math.exp(-frac * 13.0) * 0.075
        hat = 0.0
        if beat_idx % 4 in (1, 3):
            hat = math.sin(2.0 * math.pi * 3700.0 * t) * math.exp(-frac * 35.0) * 0.012
        fade_in = min(1.0, idx / max(1.0, rate * 0.025))
        fade_out = min(1.0, (count - idx - 1) / max(1.0, rate * 0.025))
        sample = max(-0.88, min(0.88, (bass + pad + melody + kick + hat) * fade_in * fade_out))
        output.append(int(sample * 32767))
    return pygame.mixer.Sound(buffer=output.tobytes())

_THEME_MUSIC_TRACKS = {}
try:
    pygame.mixer.set_reserved(1)
    THEME_MUSIC_CHANNEL = pygame.mixer.Channel(0)
except (pygame.error, AttributeError):
    THEME_MUSIC_CHANNEL = None
_THEME_MUSIC_KEY = None
_THEME_MUSIC_READY = True

def _theme_music_set_volume():
    if THEME_MUSIC_CHANNEL is not None:
        THEME_MUSIC_CHANNEL.set_volume(max(0.0, min(1.0, float(feature_settings.get("music_volume", 0.28)))))

def _theme_music_style():
    if challenge:
        return "abyss"
    stage = STAGES.get(cur_stage, STAGES.get(0, {}))
    return stage.get("style", cur_def.get("style", "dungeon"))

def theme_music_update():
    global _THEME_MUSIC_KEY, _THEME_MUSIC_READY
    if THEME_MUSIC_CHANNEL is None or not _THEME_MUSIC_READY:
        return
    wants_music = state in ("playing", "paused", "level_up", "altar_choice") and not game_over
    wanted = _theme_music_style() if wants_music else None
    if wanted == _THEME_MUSIC_KEY:
        _theme_music_set_volume()
        return
    THEME_MUSIC_CHANNEL.stop()
    _THEME_MUSIC_KEY = wanted
    if wanted is None:
        return
    try:
        if wanted not in _THEME_MUSIC_TRACKS:
            _THEME_MUSIC_TRACKS[wanted] = _theme_build_music(wanted)
        _theme_music_set_volume()
        THEME_MUSIC_CHANNEL.play(_THEME_MUSIC_TRACKS[wanted], loops=-1)
    except (pygame.error, ValueError, MemoryError) as exc:
        # Disable only the optional music layer after a mixer failure; gameplay keeps running.
        print(f"배경 음악을 시작하지 못했습니다 ({wanted}): {exc}")
        _THEME_MUSIC_KEY = None
        _THEME_MUSIC_READY = False

_THEME_OLD_FEATURE_LOAD = feature_load_extra
def feature_load_extra():
    _THEME_OLD_FEATURE_LOAD()
    _theme_music_set_volume()

_THEME_OLD_SET_VOLUME = feature_set_volume
def feature_set_volume():
    _THEME_OLD_SET_VOLUME()
    _theme_music_set_volume()

# ----- 4) Visual upgrades for stage atmosphere, hero equipment, runes, and pets -----
THEME_ATMOSPHERE = {
    "dungeon": ((175, 165, 210), (110, 85, 145)),
    "ice": ((185, 230, 255), (100, 175, 255)),
    "lava": ((255, 160, 65), (255, 75, 30)),
    "grave": ((160, 225, 170), (75, 145, 95)),
    "desert": ((255, 220, 145), (205, 145, 70)),
    "swamp": ((190, 245, 115), (70, 150, 65)),
    "abyss": ((205, 150, 255), (110, 75, 220)),
    "crystal": ((190, 245, 255), (95, 170, 255)),
    "sky": ((255, 240, 195), (170, 135, 255)),
}
THEME_BOSS_GLOWS = {
    k: make_glow(48 if meta["radius"] < 40 else 60, tuple(min(255, int(c * 0.75)) for c in meta["color"]))
    for k, meta in THEME_BOSS_META.items()
}
CLASS_AURA_GLOWS = {
    c["name"]: make_glow(36, tuple(min(255, int(v * 0.65)) for v in c.get("color", (140, 180, 255))))
    for c in CLASSES
}

def _theme_draw_player_gear(surf):
    if game_over or state not in ("playing", "paused", "level_up", "altar_choice"):
        return
    px, py = int(player_pos.x), int(player_pos.y)
    cls = CLASSES[cur_class] if 0 <= cur_class < len(CLASSES) else CLASSES[0]
    base_color = cls.get("color", (140, 180, 255))
    glow = CLASS_AURA_GLOWS.get(cls.get("name"))
    if glow is not None:
        add_glow(surf, glow, (px, py + 7), 0.48)
    # A subtle animated foot ring shows the selected profession without obscuring the sprite.
    phase = frame_tick * 2.0
    pygame.draw.ellipse(surf, tuple(max(20, c // 2) for c in base_color), (px - 16, py + 12, 32, 8), 1)
    pygame.draw.arc(surf, base_color, (px - 21, py + 8, 42, 15), math.radians((phase % 180)), math.radians((phase % 180) + 220), 2)

    armor_id = equipped_gear.get("armor", "")
    armor = WEAPONS.get(armor_id, {}) if armor_id else {}
    if armor:
        c = armor.get("c", (base_color, base_color, (30, 30, 40)))
        ac, hi = c[0], c[1]
        # Paired shoulder plates / trim make armour visible at gameplay scale.
        pygame.draw.polygon(surf, ac, [(px - 15, py - 8), (px - 8, py - 12), (px - 5, py - 5), (px - 12, py - 2)])
        pygame.draw.polygon(surf, ac, [(px + 15, py - 8), (px + 8, py - 12), (px + 5, py - 5), (px + 12, py - 2)])
        pygame.draw.line(surf, hi, (px - 12, py - 7), (px - 8, py - 10), 1)
        pygame.draw.line(surf, hi, (px + 12, py - 7), (px + 8, py - 10), 1)
        rarity = armor.get("rarity", "common")
        add_glow(surf, rarity_glows.get(rarity, glow_proj), (px, py + 3), 0.25)

    acc_id = equipped_gear.get("acc", "")
    if acc_id and acc_id in WEAPONS:
        acc = WEAPONS[acc_id]
        ac = acc.get("c", (base_color, base_color, base_color))[0]
        ring_y = py - 14
        orbit = pygame.Vector2(1, 0).rotate(frame_tick * 2.5) * 20
        pygame.draw.circle(surf, ac, (px, ring_y), 10, 1)
        pygame.draw.circle(surf, acc.get("c", (base_color, base_color, base_color))[1],
                           (int(px + orbit.x), int(ring_y + orbit.y)), 3)

    rune_ids = [equipped_gear.get("rune", ""), equipped_gear.get("rune2", "")]
    active_runes = [wid for wid in rune_ids if wid and wid in WEAPONS]
    for i, wid in enumerate(active_runes):
        data = WEAPONS[wid]
        cols = data.get("c", (base_color, (255, 255, 255), base_color))
        ang = frame_tick * (2.0 if i == 0 else -2.6) + i * 180
        radius = 25 + i * 5
        point = pygame.Vector2(radius, 0).rotate(ang) + pygame.Vector2(px, py)
        diamond = [(int(point.x), int(point.y - 4)), (int(point.x + 4), int(point.y)),
                   (int(point.x), int(point.y + 4)), (int(point.x - 4), int(point.y))]
        pygame.draw.polygon(surf, cols[0], diamond)
        pygame.draw.circle(surf, cols[1], (int(point.x), int(point.y)), 2)
        if frame_tick % 30 < 12:
            add_glow(surf, rarity_glows.get(data.get("rarity", "rare"), glow_gem), point, 0.25)

    pet_id_now = equipped_gear.get("pet", "")
    if pet_id_now and pet_id_now in WEAPONS:
        pet_data = WEAPONS[pet_id_now]
        pet_center = (int(pet_pos.x), int(pet_pos.y))
        pet_rarity = pet_data.get("rarity", "rare")
        add_glow(surf, rarity_glows.get(pet_rarity, glow_gem), pet_center, 0.58)
        color = pet_data.get("c", (base_color, (255, 255, 255), base_color))[1]
        bob = int(math.sin(frame_tick * 0.15) * 2)
        pygame.draw.circle(surf, color, (pet_center[0], pet_center[1] + bob), 11, 1)
        pygame.draw.circle(surf, (255, 255, 255), (pet_center[0] - 3, pet_center[1] - 2 + bob), 2)
        pygame.draw.circle(surf, (255, 255, 255), (pet_center[0] + 3, pet_center[1] - 2 + bob), 2)


def _theme_draw_atmosphere(surf):
    style = cur_def.get("style", "dungeon") if isinstance(cur_def, dict) else "dungeon"
    colors = THEME_ATMOSPHERE.get(style, THEME_ATMOSPHERE["dungeon"])
    c1, c2 = colors
    # Fixed deterministic particle paths prevent random jitter and avoid per-frame allocations.
    for i in range(18):
        speed = 0.35 + (i % 5) * 0.16
        x = int((i * 83 + math.sin(frame_tick * 0.012 + i) * 22 + frame_tick * speed) % WIDTH)
        y = int((i * 59 + math.cos(frame_tick * 0.016 + i * 0.7) * 18 - frame_tick * (0.22 + (i % 3) * 0.08)) % HEIGHT)
        col = c1 if i % 3 else c2
        if style in ("ice", "crystal", "sky"):
            pygame.draw.line(surf, col, (x, y), (x + 2, y - 4), 1)
            if i % 4 == 0:
                pygame.draw.circle(surf, (245, 250, 255), (x, y), 1)
        elif style in ("lava", "desert"):
            pygame.draw.rect(surf, col, (x, y, 2, 3 if i % 2 else 2))
        else:
            pygame.draw.circle(surf, col, (x, y), 1 if i % 3 else 2)


def draw_world():
    result = _THEME_OLD_DRAW_WORLD()
    # These effects are drawn after the original pixel-art layer, so they require no external sprites.
    _theme_draw_atmosphere(world)
    _theme_draw_player_gear(world)
    for boss in enemies:
        if boss.get("boss") and boss.get("kind") in THEME_BOSS_GLOWS:
            add_glow(world, THEME_BOSS_GLOWS[boss["kind"]], boss["pos"], 0.72 if boss.get("mini_boss") else 1.0)
    return result
# ============================================================
# [3단계] 상점 UI 겹침 수정 + 별 최대 3개 + 장비 강화 전용 메뉴
# 붙여넣기 위치:
# '# Track the new skills on every live frame. The effect code uses the existing damage / VFX path.'
# 라는 주석 바로 위. 기존 코드는 삭제하지 마세요.
# ============================================================

# 1) 별은 최대 3개만 사용합니다. 기존 저장 파일의 4~5성도 3성으로 제한합니다.
MAX_STAR = 3
for _stage3_wid in list(weapon_stars):
    try:
        weapon_stars[_stage3_wid] = max(1, min(MAX_STAR, int(weapon_stars[_stage3_wid])))
    except (TypeError, ValueError):
        weapon_stars[_stage3_wid] = 1

# 2) 강화 재료: 3성 장비를 다시 뽑으면 골드 환급 대신 같은 장비의 강화용 복사본을 얻습니다.
feature_duplicate_copies = {}

_STAGE3_OLD_FEATURE_SAVE_PAYLOAD = feature_save_payload

def feature_save_payload():
    _payload = _STAGE3_OLD_FEATURE_SAVE_PAYLOAD()
    _payload["duplicate_copies"] = {
        str(_wid): max(0, int(_count))
        for _wid, _count in feature_duplicate_copies.items()
        if _wid in WEAPONS and isinstance(_count, (int, float)) and _count > 0
    }
    return _payload

_STAGE3_OLD_FEATURE_LOAD_EXTRA = feature_load_extra

def feature_load_extra():
    global feature_duplicate_copies
    _STAGE3_OLD_FEATURE_LOAD_EXTRA()
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as _f:
            _save_data = json.load(_f)
        _feature_data = _save_data.get("feature", {}) if isinstance(_save_data, dict) else {}
        _raw_copies = _feature_data.get("duplicate_copies", {}) if isinstance(_feature_data, dict) else {}
        if isinstance(_raw_copies, dict):
            feature_duplicate_copies = {
                str(_wid): max(0, int(_count))
                for _wid, _count in _raw_copies.items()
                if str(_wid) in WEAPONS and isinstance(_count, (int, float)) and _count > 0
            }
    except (OSError, ValueError, TypeError):
        feature_duplicate_copies = {}

    _stars_changed = False
    for _wid in list(weapon_stars):
        try:
            _old_star = int(weapon_stars[_wid])
            _new_star = max(1, min(MAX_STAR, _old_star))
            if _old_star != _new_star:
                _stars_changed = True
            weapon_stars[_wid] = _new_star
        except (TypeError, ValueError):
            weapon_stars[_wid] = 1
            _stars_changed = True
    if _stars_changed:
        save_game()


# 뽑기 결과에서 3성 장비의 추가 중복을 강화 재료로 전환합니다.
_STAGE3_OLD_DO_PULL = do_pull

def do_pull(n):
    global gold
    _stars_before = dict(weapon_stars)
    _old_results = shop_results
    _STAGE3_OLD_DO_PULL(n)
    if not shop_results or shop_results is _old_results:
        return

    _simulated_stars = dict(_stars_before)
    _materials_gained = 0
    for _res in shop_results:
        _wid = _res.get("id")
        if _wid not in WEAPONS:
            continue
        _current_star = int(_simulated_stars.get(_wid, 0) or 0)
        if _current_star >= MAX_STAR and _res.get("kind") == "refund":
            # 기존 뽑기 코드가 준 중복 환급을 되돌리고 재료 복사본으로 바꿉니다.
            gold = max(0, gold - DUP_REFUND)
            feature_duplicate_copies[_wid] = feature_duplicate_copies.get(_wid, 0) + 1
            _res["kind"] = "material"
            _materials_gained += 1
        else:
            _simulated_stars[_wid] = min(MAX_STAR, max(1, _current_star + 1))

    if _materials_gained:
        show_toast(f"3성 중복 장비: 강화 재료 +{_materials_gained}", (100, 245, 225))
        save_game()


# 강화 재료로 변환된 뽑기 결과는 '중복 골드' 대신 별도 문구로 표시합니다.
_STAGE3_OLD_DRAW_RESULT_CARD = draw_result_card

def draw_result_card(rect, res, t, big):
    _STAGE3_OLD_DRAW_RESULT_CARD(rect, res, t, big)
    if res.get("kind") != "material":
        return
    _ease = 1 - (1 - max(0.0, min(1.0, t))) ** 3
    _r = rect.move(0, int((1 - _ease) * 40))
    _label_y = _r.bottom - (28 if big else 20)
    _rarity_color = RARITY[WEAPONS[res["id"]]["rarity"]]["color"]
    _bg = tuple(c // 6 + 16 for c in _rarity_color)
    pygame.draw.rect(screen, _bg, (_r.x + 6, _label_y - 12, _r.w - 12, 24))
    blit_text(screen, small_font if big else tiny_font,
              "강화 재료 +1", (90, 255, 225), (_r.centerx, _label_y), True)


# 3) 상점: 시작 스킬과 힌트가 겹치지 않도록 왼쪽 설명을 다시 배치합니다.
_STAGE3_OLD_DRAW_SHOP = draw_shop_screen

def draw_shop_screen():
    _STAGE3_OLD_DRAW_SHOP()
    if shop_results or not WEAPON_ORDER:
        return

    _safe_sel = max(0, min(shop_sel, len(WEAPON_ORDER) - 1))
    _wid = WEAPON_ORDER[_safe_sel]
    _w = WEAPONS[_wid]
    _rarity_color = RARITY[_w["rarity"]]["color"]
    _owned = _wid in weapon_stars
    _star = weapon_stars.get(_wid, 1)

    # 겹쳐 있던 하단 정보만 덮고 줄 간격을 재설정합니다.
    pygame.draw.rect(screen, (24, 26, 46), (31, 342, 278, 118))
    _details = weapon_stat_lines(_wid, _star if _owned else 1)
    _numeric_lines = [str(_line) for _line in _details if not str(_line).startswith("시작 스킬:")]
    _skill_lines = [str(_line) for _line in _details if str(_line).startswith("시작 스킬:")]
    for _i, _line in enumerate(_numeric_lines[:4]):
        blit_text(screen, tiny_font, fit_text(tiny_font, _line, 258),
                  (200, 225, 255), (170, 351 + _i * 17), True)
    if _skill_lines:
        blit_text(screen, tiny_font, fit_text(tiny_font, _skill_lines[0], 258),
                  (255, 220, 130), (170, 420), True)

    if not _owned:
        _hint = "뽑기에서 얻을 수 있어요"
    elif _star >= MAX_STAR:
        _hint = "3성 완성 · 추가 중복은 강화 재료"
    else:
        _hint = f"같은 장비를 얻으면 별 상승 ({_star}/{MAX_STAR})"
    blit_text(screen, tiny_font, fit_text(tiny_font, _hint, 258),
              (150, 220, 210) if _owned and _star >= MAX_STAR else (150, 160, 190),
              (170, 446), True)

    # 낮게 남아 있던 확률 문구를 두 줄+보장 문구로 정리합니다.
    _panel_bg = (30, 28, 48)
    pygame.draw.rect(screen, _panel_bg, (344, 151, 432, 43))
    pygame.draw.rect(screen, _panel_bg, (344, 194, 432, 8))
    blit_text(screen, tiny_font, "일반 58% · 희귀 28% · 영웅 11%",
              (170, 180, 210), (560, 157), True)
    blit_text(screen, tiny_font, "전설 2.6% · 신화 0.39% · 초월 0.01%",
              (170, 180, 210), (560, 172), True)
    blit_text(screen, tiny_font, "10회 뽑기: 희귀 이상 1개 보장",
              (170, 180, 210), (560, 187), True)

    # 기존 뽑기 패널이 덮던 분류 탭을 마지막에 다시 그려 항상 보이게 합니다.
    _mouse = pygame.mouse.get_pos()
    for _i, _rect in enumerate(TAB_RECTS):
        _active = (_i == shop_tab)
        draw_button(screen, _rect, "", _active or _rect.collidepoint(_mouse), True,
                    (200, 140, 255) if _active else (110, 120, 170))
        blit_text(screen, tiny_font, SLOT_NAMES[SLOTS[_i]],
                  (255, 255, 255), _rect.center, True)


# 4) 추가 콘텐츠 메뉴에서 '제작·분해'를 없애고 '장비 강화'만 남깁니다.
FEATURE_HUB_ITEMS[:] = [
    ("설정", "settings"), ("도감", "codex"), ("일일·주간 임무", "missions"),
    ("장비 강화", "craft"), ("전투 통계", "stats"), ("보스 러시 시작", "boss_rush")
]

_STAGE3_OLD_DRAW_FEATURE_HUB = feature_draw_hub

def feature_draw_hub():
    _STAGE3_OLD_DRAW_FEATURE_HUB()
    _craft_index = next((i for i, item in enumerate(FEATURE_HUB_ITEMS) if item[1] == "craft"), None)
    if _craft_index is not None:
        _r = feature_hub_rects()[_craft_index]
        blit_text(screen, tiny_font, "3성 장비와 중복 장비로 강화",
                  (175, 185, 215), (_r.centerx, _r.bottom - 17), True)
    _maxed_types = sum(1 for _wid in weapon_stars if weapon_stars.get(_wid, 0) >= MAX_STAR)
    _copy_total = sum(max(0, int(_count)) for _count in feature_duplicate_copies.values())
    pygame.draw.rect(screen, (22, 24, 43), (140, 536, 520, 26))
    blit_text(screen, tiny_font,
              f"3성 장비 {_maxed_types}종 · 강화용 중복 {_copy_total}개 · 보스 러시 최고 {feature_stats.get('best_boss_rush', 0)}라운드",
              (255, 220, 130), (WIDTH // 2, 548), True)


# 강화 단계별 성공률. 실패하면 강화 단계가 1 내려가며 최저 +0입니다.
_STAGE3_ENHANCE_CHANCES = (0.90, 0.80, 0.70, 0.60, 0.50, 0.40, 0.30, 0.22, 0.15, 0.10)
_STAGE3_RARITY_COST_MULT = {
    "common": 1.0, "rare": 1.5, "epic": 2.5, "legend": 4.0,
    "myth": 8.0, "transcendent": 12.0,
}

def _stage3_owned_items():
    return [wid for wid in ALL_ORDER if wid in weapon_stars]

def _stage3_current_item():
    global feature_craft_index
    _owned_ids = _stage3_owned_items()
    if not _owned_ids:
        return ""
    _wid = ALL_ORDER[feature_craft_index % len(ALL_ORDER)] if ALL_ORDER else ""
    if _wid not in _owned_ids:
        _wid = equipped_weapon if equipped_weapon in _owned_ids else _owned_ids[0]
        feature_craft_index = ALL_ORDER.index(_wid)
    return _wid

def _stage3_shift_item(direction):
    global feature_craft_index
    _owned_ids = _stage3_owned_items()
    if not _owned_ids:
        return
    _current = _stage3_current_item()
    _idx = _owned_ids.index(_current) if _current in _owned_ids else 0
    _wid = _owned_ids[(_idx + direction) % len(_owned_ids)]
    feature_craft_index = ALL_ORDER.index(_wid)

def _stage3_enhance_need(level):
    return max(1, math.ceil((int(level) + 1) * 0.5))

def _stage3_enhance_cost(wid, level):
    _rarity = WEAPONS.get(wid, {}).get("rarity", "common")
    _mult = _STAGE3_RARITY_COST_MULT.get(_rarity, 1.0)
    return int(200 * (level + 1) ** 2 * _mult)

def feature_enhance_selected():
    global gold
    _wid = _stage3_current_item()
    if not _wid:
        show_toast("강화할 장비가 없어요", (255, 145, 145)); snd_fail.play(); return
    _star = weapon_stars.get(_wid, 0)
    if _star < MAX_STAR:
        show_toast(f"강화하려면 먼저 별을 {MAX_STAR}개 완성하세요 ({_star}/{MAX_STAR})", (255, 145, 145))
        snd_fail.play(); return
    _level = int(feature_item_enhancements.get(_wid, 0))
    if _level >= 10:
        show_toast("최대 강화 단계 +10입니다", (200, 190, 220)); snd_fail.play(); return

    _need = _stage3_enhance_need(_level)
    _cost = _stage3_enhance_cost(_wid, _level)
    _copies = int(feature_duplicate_copies.get(_wid, 0))
    if _copies < _need:
        show_toast(f"동일 장비 중복이 부족해요: {_copies}/{_need}개 필요", (255, 145, 145))
        snd_fail.play(); return
    if gold < _cost:
        show_toast(f"골드 부족: {_cost:,}G 필요", (255, 145, 145))
        snd_fail.play(); return

    _chance = _STAGE3_ENHANCE_CHANCES[_level]
    # 성공 여부와 관계없이 재료 장비와 골드를 소모합니다.
    feature_duplicate_copies[_wid] = _copies - _need
    gold -= _cost
    if random.random() < _chance:
        feature_item_enhancements[_wid] = _level + 1
        _message = f"강화 성공! {_level:+d} → {_level + 1:+d} · 확률 {_chance:.0%}"
        _color = (120, 255, 175)
        snd_buy.play()
    else:
        _new_level = max(0, _level - 1)
        feature_item_enhancements[_wid] = _new_level
        _message = f"강화 실패! {_level:+d} → {_new_level:+d} · 확률 {_chance:.0%}"
        _color = (255, 145, 145)
        snd_fail.play()
    save_game()
    show_toast(_message, _color)


def feature_draw_craft():
    global feature_button_rects
    feature_draw_background("장비 강화")
    feature_button_rects = {
        "prev": pygame.Rect(220, 315, 130, 40),
        "next": pygame.Rect(450, 315, 130, 40),
        "enhance": pygame.Rect(280, 425, 240, 50),
    }
    _wid = _stage3_current_item()

    if not _wid:
        blit_text(screen, small_font, "보유한 장비가 없습니다", (220, 225, 245), (WIDTH // 2, 220), True)
        return

    _w = WEAPONS[_wid]
    _rarity = RARITY.get(_w.get("rarity", "common"), RARITY["common"])
    _star = int(weapon_stars.get(_wid, 0))
    _level = int(feature_item_enhancements.get(_wid, 0))
    _copies = int(feature_duplicate_copies.get(_wid, 0))
    pixel_panel(screen, pygame.Rect(125, 88, 550, 215), _rarity["color"], (30, 33, 54), n=7, bw=3)
    _icon = weapon_img(_wid, 4, dark=False)
    screen.blit(_icon, _icon.get_rect(center=(WIDTH // 2, 130)))
    blit_text(screen, small_font, fit_text(small_font, _w["name"], 430),
              _rarity["color"], (WIDTH // 2, 178), True)
    for _i in range(MAX_STAR):
        draw_star(screen, (WIDTH // 2 - 28 + _i * 28, 203), 9, _rarity["color"], empty=_i >= _star)
    blit_text(screen, tiny_font, f"별 {_star}/{MAX_STAR} · 강화 +{_level}/10",
              (225, 230, 250), (WIDTH // 2, 229), True)
    _stat_lines = weapon_stat_lines(_wid, max(1, _star))
    _short_stats = " · ".join(str(x) for x in _stat_lines[:2])
    blit_text(screen, tiny_font, fit_text(tiny_font, _short_stats, 500),
              (190, 205, 230), (WIDTH // 2, 258), True)

    draw_dungeon_button(feature_button_rects["prev"], "이전 장비", False, (165, 185, 255))
    draw_dungeon_button(feature_button_rects["next"], "다음 장비", False, (165, 185, 255))

    if _star < MAX_STAR:
        _info_1 = f"강화 잠김: 별 {_star}/{MAX_STAR} · 먼저 같은 장비를 뽑아 3성을 만드세요"
        _info_2 = f"3성 이후 동일 장비 중복 획득 시 강화 재료로 저장됩니다 ({_copies}개 보유)"
        _chance_text = "성공 확률: 별 3개 완성 후 표시"
        _cost_text = "필요 재료: 동일 장비 3성 중복 · 골드"
        _button_text = "별 3개 달성 후 강화 가능"
        _button_color = (110, 115, 140)
    elif _level >= 10:
        _info_1 = "최대 강화 단계에 도달했습니다"
        _info_2 = f"남은 동일 장비 강화 재료: {_copies}개"
        _chance_text = "성공 확률: MAX"
        _cost_text = "필요 재료 없음"
        _button_text = "강화 MAX"
        _button_color = (110, 115, 140)
    else:
        _need = _stage3_enhance_need(_level)
        _cost = _stage3_enhance_cost(_wid, _level)
        _chance = _STAGE3_ENHANCE_CHANCES[_level]
        _info_1 = f"강화 확률 {_chance:.0%} · +{_level} → +{_level + 1}"
        _info_2 = f"동일 장비 중복 {_copies}/{_need}개 필요 · 골드 {_cost:,}G"
        _chance_text = "실패 시 강화 단계가 1 하락합니다 (최저 +0)"
        _cost_text = "시도할 때마다 재료와 골드를 소모합니다"
        _button_text = "강화하기 (U / Enter)"
        _button_color = (110, 230, 175) if _copies >= _need and gold >= _cost else (170, 145, 100)

    blit_text(screen, tiny_font, fit_text(tiny_font, _info_1, 680),
              (255, 220, 130) if _star >= MAX_STAR else (190, 190, 215), (WIDTH // 2, 373), True)
    blit_text(screen, tiny_font, fit_text(tiny_font, _info_2, 680),
              (190, 225, 235), (WIDTH // 2, 394), True)
    draw_dungeon_button(feature_button_rects["enhance"], _button_text, False, _button_color)
    blit_text(screen, tiny_font, _chance_text, (255, 155, 155), (WIDTH // 2, 493), True)
    blit_text(screen, tiny_font, _cost_text, (175, 185, 215), (WIDTH // 2, 520), True)
    blit_text(screen, tiny_font,
              f"보유 골드 {gold:,}G · 강화 재료 {sum(feature_duplicate_copies.values())}개 · 좌우/휠: 장비 선택 · ESC: 뒤로",
              (255, 220, 130), (WIDTH // 2, 550), True)


# 강화 화면에서는 분해/제작/도색/잠재 능력 키가 작동하지 않도록 입력을 교체합니다.
_STAGE3_OLD_FEATURE_MENU_EVENT = feature_menu_event

def feature_menu_event(event):
    if feature_page != "craft":
        return _STAGE3_OLD_FEATURE_MENU_EVENT(event)

    if event.type == pygame.KEYDOWN:
        _key = event.key
        if _key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            return _STAGE3_OLD_FEATURE_MENU_EVENT(event)
        if _key in (pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w):
            _stage3_shift_item(-1)
        elif _key in (pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s):
            _stage3_shift_item(1)
        elif _key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_u):
            feature_enhance_selected()
        return

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        _back = pygame.Rect(20, 16, 120, 38)
        if _back.collidepoint(event.pos):
            return _STAGE3_OLD_FEATURE_MENU_EVENT(event)
        for _key, _rect in feature_button_rects.items():
            if _rect.collidepoint(event.pos):
                if _key == "prev":
                    _stage3_shift_item(-1)
                elif _key == "next":
                    _stage3_shift_item(1)
                elif _key == "enhance":
                    feature_enhance_selected()
                return
        return

    if event.type == pygame.MOUSEWHEEL:
        _stage3_shift_item(-1 if event.y > 0 else 1)
        return

    # 다른 이벤트는 강화 화면에서 아무 동작도 하지 않습니다.
    return
# Track the new skills on every live frame. The effect code uses the existing damage / VFX path.
# Load and persist current discovery state; retain all data in the original save.json.
feature_load_extra()
feature_discovered_items.update(k for k in weapon_stars if k in WEAPONS)
feature_ensure_missions()
feature_apply_dyes()
feature_set_volume()
# ============================================================
# [4단계] 상점 설명 겹침 방지 + 별 3개 중앙 정렬 + 메뉴 부제 중복 제거
# 붙여넣기 위치: 파일 맨 아래의 `while running:` 바로 위
# 기존 코드는 지우지 마세요.
# ============================================================

# 1) 상점 장비 카드의 별을 3개 기준 중앙에 정렬합니다.
_STAGE4_OLD_DRAW_WEAPON_CELL = draw_weapon_cell

def draw_weapon_cell(rect, wid, selected):
    _STAGE4_OLD_DRAW_WEAPON_CELL(rect, wid, selected)
    if wid not in weapon_stars:
        return

    _rarity_color = RARITY[WEAPONS[wid]["rarity"]]["color"]
    _fill_color = tuple(c // 6 + 16 for c in _rarity_color)
    _star_y = rect.bottom - 10

    # 기존 5성 기준으로 왼쪽 치우친 별 3개를 지우고 중앙에 다시 그립니다.
    pygame.draw.rect(
        screen, _fill_color,
        pygame.Rect(rect.centerx - 24, rect.bottom - 17, 48, 13)
    )
    _spacing = 10
    _start_x = rect.centerx - (_spacing * (MAX_STAR - 1)) / 2
    for _i in range(MAX_STAR):
        draw_star(
            screen,
            (round(_start_x + _i * _spacing), _star_y),
            3.5,
            _rarity_color,
            empty=_i >= weapon_stars[wid]
        )


# 2) 장비 상세 패널의 별을 중앙으로 맞추고 설명 문구를 서로 떨어뜨립니다.
_STAGE4_OLD_DRAW_SHOP = draw_shop_screen

def draw_shop_screen():
    _STAGE4_OLD_DRAW_SHOP()
    if shop_results or not WEAPON_ORDER:
        return

    _sel = max(0, min(shop_sel, len(WEAPON_ORDER) - 1))
    _wid = WEAPON_ORDER[_sel]
    _w = WEAPONS[_wid]
    _owned = _wid in weapon_stars
    _star = weapon_stars.get(_wid, 1)
    _rc = RARITY[_w["rarity"]]["color"]
    _panel = pygame.Rect(20, 66, 300, 458)
    _cx = _panel.centerx

    # 별 행: 기존 5개용 위치를 가리고, 현재 최대 별 개수만큼 중앙 정렬합니다.
    pygame.draw.rect(
        screen, (24, 26, 46),
        pygame.Rect(_cx - 66, _panel.y + 238, 132, 36)
    )
    _star_y = _panel.y + 254
    _spacing = 26
    _start_x = _cx - (_spacing * (MAX_STAR - 1)) / 2
    for _i in range(MAX_STAR):
        draw_star(
            screen,
            (round(_start_x + _i * _spacing), _star_y),
            10,
            _rc,
            empty=(not _owned) or _i >= _star
        )

    # 기존 설명 문구가 있던 영역을 통째로 지운 다음 새 위치에 한 번만 그립니다.
    # 장착/미획득 버튼은 y=466부터 시작하므로 그 버튼 영역은 건드리지 않습니다.
    pygame.draw.rect(screen, (24, 26, 46), pygame.Rect(31, 340, 278, 122))

    _details = weapon_stat_lines(_wid, _star if _owned else 1)
    _numbers = [str(x) for x in _details if not str(x).startswith("시작 스킬:")]
    _skills = [str(x) for x in _details if str(x).startswith("시작 스킬:")]

    # 능력치가 4개 이상이면 마지막 줄에 합쳐서 줄 수가 밀리지 않게 합니다.
    if len(_numbers) > 3:
        _numbers = _numbers[:2] + [" · ".join(_numbers[2:])]

    for _i, _line in enumerate(_numbers[:3]):
        blit_text(
            screen, tiny_font, fit_text(tiny_font, _line, 258),
            (200, 225, 255), (_cx, 352 + _i * 20), True
        )

    if _skills:
        blit_text(
            screen, tiny_font, fit_text(tiny_font, _skills[0], 258),
            (255, 220, 130), (_cx, 419), True
        )
        _hint_y = 445
    else:
        _hint_y = 426

    if not _owned:
        _hint = "뽑기에서 얻을 수 있어요"
    elif _star >= MAX_STAR:
        _hint = "3성 완성 · 추가 중복은 강화 재료"
    else:
        _hint = f"같은 장비를 얻으면 별 상승 ({_star}/{MAX_STAR})"

    blit_text(
        screen, tiny_font, fit_text(tiny_font, _hint, 258),
        (150, 220, 210) if _owned and _star >= MAX_STAR else (170, 180, 205),
        (_cx, _hint_y), True
    )


# 3) 추가 콘텐츠 메뉴에서 중복으로 그려진 부제를 제거합니다.
_STAGE4_OLD_DRAW_FEATURE_HUB = feature_draw_hub

def feature_draw_hub():
    _STAGE4_OLD_DRAW_FEATURE_HUB()
    _craft_index = next(
        (i for i, item in enumerate(FEATURE_HUB_ITEMS) if item[1] == "craft"),
        None
    )
    if _craft_index is None:
        return

    _rect = feature_hub_rects()[_craft_index]
    _selected = _craft_index == feature_menu_index
    _accent = (255, 205, 105) if _selected else (155, 175, 225)

    # 버튼 전체를 한 번 다시 그려서 이전 부제 글자가 남지 않게 합니다.
    draw_dungeon_button(_rect, "장비 강화", _selected, _accent)
    blit_text(
        screen, tiny_font, "3성 장비와 중복 장비로 강화",
        (175, 185, 215), (_rect.centerx, _rect.bottom - 17), True
    )
# ============================================================
# [5단계 안전 교체 + 오류 기록] 자동 시작 스킬 비활성화
# 중요: 기존 [5단계 패치] 전체를 삭제하고 이 코드를 그 자리에 붙이세요.
# 위치: 파일 맨 아래의 `while running:` 바로 위
# ============================================================

# 1) 장비가 스킬을 자동 지급하지 않게 합니다.
# reset_game/apply_upgrade를 감싸지 않으므로 레벨업 선택과 스테이지 시작 흐름은 그대로 둡니다.
for _safe_item in WEAPONS.values():
    _safe_item.pop("start", None)

# 2) 캐릭터 시작 스킬만 제거하고 캐릭터의 능력치 보너스는 유지합니다.
for _safe_class in CLASSES:
    _safe_class["start"] = []
    if isinstance(_safe_class.get("lines"), list):
        _safe_class["lines"] = [
            _line for _line in _safe_class["lines"]
            if not (
                isinstance(_line, (tuple, list)) and _line
                and ("시작:" in str(_line[0]) or "시작 스킬" in str(_line[0]))
            )
        ]

# 3) 장비 세트 보너스가 주는 자동 시작 스킬도 비활성화합니다.
_SAFE_OLD_GEAR_STATS_NO_START = gear_stats

def gear_stats():
    _safe_stats = _SAFE_OLD_GEAR_STATS_NO_START()
    _safe_stats["start"] = []
    return _safe_stats

# 4) 예기치 않은 오류가 발생하면 traceback을 crash_log.txt에 기록합니다.
import sys
import traceback


def _safe_write_crash_log(exc_type, exc_value, exc_tb):
    _log_path = os.path.join(BASE_DIR, "crash_log.txt")
    try:
        with open(_log_path, "w", encoding="utf-8") as _log_file:
            traceback.print_exception(exc_type, exc_value, exc_tb, file=_log_file)
    except OSError:
        pass
    try:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    except Exception:
        pass


sys.excepthook = _safe_write_crash_log
print("[패치] 자동 시작 스킬 비활성화 완료 · 오류 기록 활성화")
# ============================================================
# [7단계] 스테이지 진입 직후 종료되는 오류 수정
# 오류 원인: draw_hud()에서 range(player_max_hp)를 호출하는데
# 강화 능력치 10% 계산으로 player_max_hp가 float(예: 4.3)가 된 경우입니다.
# 위치: 다른 모든 패치 아래, `while running:` 바로 위에 붙여 넣으세요.
# ============================================================

# 1) 장비 능력치 합산 결과의 체력은 정수 하트로 처리합니다.
_stage7_gear_stats_before_hp_fix = gear_stats

def gear_stats():
    _stage7_stats = _stage7_gear_stats_before_hp_fix()
    try:
        _stage7_stats["hp"] = max(0, int(round(float(_stage7_stats.get("hp", 0)))))
    except (TypeError, ValueError, OverflowError):
        _stage7_stats["hp"] = 0
    return _stage7_stats


# 2) 스테이지를 시작하거나 재시작할 때 최대 체력/현재 체력을 정수로 보정합니다.
_stage7_reset_game_before_hp_fix = reset_game

def reset_game():
    global player_max_hp, player_hp
    _stage7_reset_game_before_hp_fix()
    try:
        player_max_hp = max(1, int(round(float(player_max_hp))))
    except (TypeError, ValueError, OverflowError):
        player_max_hp = 3
    try:
        player_hp = max(0, min(player_max_hp, int(round(float(player_hp)))))
    except (TypeError, ValueError, OverflowError):
        player_hp = player_max_hp


# 3) 마지막 안전장치: HUD를 그리기 직전에도 최대 체력이 정수인지 확인합니다.
# 기존 draw_hud 구현과 UI 구성은 그대로 유지합니다.
_stage7_draw_hud_before_hp_fix = draw_hud

def draw_hud():
    global player_max_hp
    try:
        _stage7_hp = int(round(float(player_max_hp)))
        player_max_hp = max(1, _stage7_hp)
    except (TypeError, ValueError, OverflowError):
        player_max_hp = 3
    return _stage7_draw_hud_before_hp_fix()

print("[7단계] 체력 자료형 오류 방지 패치 적용 완료")
# ============================================================
# [8단계] 전 구간 난이도 상향 + 보스 전용 외형 + 회피 가능한 즉사 패턴
# 붙여 넣는 위치: 마지막 `while running:` 바로 위
# 기존 코드는 삭제하지 마세요. (이 패치는 중복 실행을 방지합니다.)
# ============================================================
if not globals().get("_HARDCORE_BOSS_PATCH_APPLIED", False):
    _HARDCORE_BOSS_PATCH_APPLIED = True

    # ---------- 1) 전투 난이도 곡선 ----------
    def _hard_stage_index():
        return max(1, int(cur_stage)) if int(cur_stage) > 0 else 1

    def _hard_time_factor():
        # 2분마다 조금씩 더 강해지며, 무한 모드도 계속 상승합니다.
        return 1.0 + min(0.90, max(0, int(survive_frames)) / (60 * 120) * 0.18)

    def _hard_enemy_hp_factor():
        stage = _hard_stage_index()
        if int(cur_stage) <= 0:
            stage_factor = 1.55 + min(0.90, max(0, int(survive_frames)) / (60 * 90) * 0.15)
        else:
            stage_factor = 1.55 + 0.17 * (stage - 1)
        return stage_factor * _hard_time_factor()

    _HARD_OLD_MAKE_ENEMY = make_enemy
    def make_enemy(kind, pos):
        enemy = _HARD_OLD_MAKE_ENEMY(kind, pos)
        factor = _hard_enemy_hp_factor()
        # 보스는 spawn_boss에서 별도로 조정하므로 여기서는 일반 적만 강화합니다.
        enemy["hp"] = max(1, int(math.ceil(enemy.get("hp", 1) * factor)))
        enemy["max_hp"] = enemy["hp"]
        enemy["hardcore"] = True
        return enemy

    _HARD_OLD_MAKE_ELITE = make_elite
    def make_elite(kind, pos):
        enemy = _HARD_OLD_MAKE_ELITE(kind, pos)
        enemy["hp"] = max(1, int(math.ceil(enemy.get("hp", 1) * 1.35)))
        enemy["max_hp"] = enemy["hp"]
        enemy["hardcore_elite"] = True
        return enemy

    # 일반 적은 더 빠르게 몰려오고, 기존 최대 속도 제한은 유지합니다.
    if not globals().get("_HARDCORE_SPEEDS_APPLIED", False):
        for _enemy_meta in enemy_types.values():
            _enemy_meta["speed"] = min(2.65, float(_enemy_meta.get("speed", 1.0)) * 1.24)
        _HARDCORE_SPEEDS_APPLIED = True

    _HARD_OLD_RESET_GAME = reset_game
    def reset_game():
        _HARD_OLD_RESET_GAME()
        # 처음부터 적 출현 간격을 짧게 설정. 후반의 기존 상승도 그대로 적용됩니다.
        global spawn_interval
        spawn_interval = max(9, int(spawn_interval * 0.76))

    # ---------- 2) 보스 체력/공격 템포 강화 ----------
    _HARD_OLD_SPAWN_BOSS = spawn_boss
    def spawn_boss(kind, hp_scale=None, final=False):
        _HARD_OLD_SPAWN_BOSS(kind, hp_scale, final)
        boss = next((e for e in reversed(enemies)
                     if e.get("boss") and e.get("kind") == kind), None)
        if boss is None:
            return

        stage = _hard_stage_index()
        if int(cur_stage) <= 0:
            stage_boss_factor = 2.00 + min(0.85, max(0, int(survive_frames)) / (60 * 300) * 0.28)
        else:
            stage_boss_factor = 2.05 + 0.16 * (stage - 1)
        boss_factor = stage_boss_factor * (1.0 + min(0.55, max(0, int(survive_frames)) / (60 * 300) * 0.11))
        boss["hp"] = max(1, int(math.ceil(boss.get("hp", 1) * boss_factor)))
        boss["max_hp"] = max(1, int(math.ceil(boss.get("max_hp", boss["hp"]) * boss_factor)))
        boss["brutal_cycle"] = 0
        boss["brutal_phase"] = 0
        boss["brutal_total"] = 0
        boss["brutal_cd"] = max(195, 300 - (stage - 1) * 11)
        boss["brutal_mode"] = "marks"
        # 보스가 등장하자마자 첫 패턴을 쏘지 않게 하지만, 대기 시간은 길지 않습니다.
        boss["cooldown"] = max(24, int(boss.get("cooldown", 60) * 0.76))

    # ---------- 3) 각 지역 보스에 완전히 다른 도트 실루엣 ----------
    def _hard_mix(a, b, t):
        return tuple(max(0, min(255, int(a[i] + (b[i] - a[i]) * t))) for i in range(3))

    def _hard_unique_boss_sprite(kind, main_color, radius):
        # 작은 도트 원본을 크게 확대해 픽셀 스타일을 유지합니다.
        S = 48
        surf = pygame.Surface((S, S), pygame.SRCALPHA)
        main = tuple(main_color[:3])
        dark = _hard_mix(main, (10, 8, 25), 0.68)
        light = _hard_mix(main, (255, 255, 255), 0.58)
        gold = (255, 215, 95)
        ice = (185, 245, 255)
        black = (18, 12, 28)

        def poly(points, fill=main, edge=dark, width=2):
            pygame.draw.polygon(surf, fill, points)
            if edge is not None:
                pygame.draw.polygon(surf, edge, points, width)

        def line(points, color, width=2):
            pygame.draw.lines(surf, color, False, points, width)

        def orb(x, y, r, color, outline=dark):
            pygame.draw.circle(surf, outline, (x, y), r + 1)
            pygame.draw.circle(surf, color, (x, y), r)
            pygame.draw.circle(surf, light, (x - max(1, r // 3), y - max(1, r // 3)), max(1, r // 3))

        # 그림자/발은 공통, 몸체와 무기·장식 실루엣은 보스별로 완전히 다르게 그립니다.
        pygame.draw.ellipse(surf, (8, 6, 18, 180), (6, 38, 36, 7))

        if kind == "magma_titan":
            poly([(9, 18), (15, 9), (21, 13), (27, 7), (37, 17), (35, 34), (27, 40), (12, 36)])
            poly([(5, 15), (13, 11), (17, 21), (12, 28), (5, 25)], _hard_mix(main, (20, 10, 10), .25))
            poly([(34, 13), (43, 10), (42, 25), (36, 29), (31, 21)], _hard_mix(main, (20, 10, 10), .25))
            line([(18, 18), (21, 23), (18, 28), (23, 33), (21, 37)], (255, 235, 85), 3)
            orb(24, 22, 4, (255, 235, 85))
        elif kind == "inferno_dragon":
            poly([(8, 16), (1, 7), (13, 11), (18, 18), (13, 26)], main)
            poly([(36, 16), (47, 5), (43, 20), (36, 29), (31, 21)], main)
            poly([(13, 19), (18, 12), (31, 14), (38, 22), (31, 34), (18, 33)])
            poly([(30, 16), (43, 18), (39, 25), (31, 24)], light)
            line([(18, 14), (16, 7), (22, 13)], gold, 2)
            line([(29, 14), (34, 7), (35, 16)], gold, 2)
            orb(27, 21, 2, gold)
        elif kind == "crypt_knight":
            poly([(11, 16), (15, 8), (31, 8), (38, 17), (34, 35), (14, 35)])
            poly([(14, 11), (19, 4), (23, 11), (27, 4), (33, 12), (31, 19), (16, 19)], light)
            pygame.draw.rect(surf, main, (15, 20, 18, 14))
            pygame.draw.rect(surf, light, (20, 22, 3, 11))
            line([(38, 16), (42, 4), (45, 3)], ice, 3)
            poly([(6, 22), (12, 18), (15, 30), (8, 34)], gold)
            orb(20, 16, 2, (255, 55, 70)); orb(28, 16, 2, (255, 55, 70))
        elif kind == "scorpion_king":
            pygame.draw.ellipse(surf, dark, (12, 20, 25, 16))
            for x, y, r in [(15, 27, 5), (23, 29, 6), (31, 26, 5)]: orb(x, y, r, main)
            line([(30, 25), (37, 19), (37, 12), (33, 7)], gold, 4)
            poly([(30, 25), (36, 24), (43, 18), (45, 24), (40, 30)], light)
            poly([(14, 26), (6, 19), (3, 22), (8, 30), (15, 32)], main)
            poly([(32, 28), (41, 31), (44, 35), (39, 36), (31, 33)], main)
            orb(23, 26, 2, (255, 55, 45))
        elif kind == "dune_emperor":
            poly([(12, 17), (17, 11), (31, 11), (37, 18), (33, 35), (15, 35)], main)
            poly([(12, 16), (10, 7), (18, 12), (24, 3), (30, 12), (38, 6), (36, 17)], gold)
            poly([(15, 23), (33, 23), (30, 32), (18, 32)], light)
            line([(9, 18), (4, 31), (9, 34)], gold, 3)
            orb(24, 20, 3, (255, 80, 65))
            pygame.draw.rect(surf, dark, (17, 35, 5, 5)); pygame.draw.rect(surf, dark, (28, 35, 5, 5))
        elif kind == "sand_wyrm":
            for x, y, r in [(11, 30, 7), (19, 26, 7), (27, 22, 7), (34, 16, 6)]:
                orb(x, y, r, main)
            poly([(31, 12), (34, 5), (38, 10), (45, 9), (42, 17), (36, 20)], light)
            line([(11, 30), (6, 35), (4, 31)], gold, 3)
            orb(39, 13, 2, (255, 50, 45))
        elif kind == "bog_witch":
            poly([(10, 19), (14, 11), (20, 16), (26, 9), (35, 18), (32, 34), (17, 39), (8, 31)], dark)
            poly([(8, 17), (18, 2), (25, 12), (38, 15), (29, 19), (16, 19)], main)
            poly([(15, 21), (32, 21), (28, 30), (18, 30)], light)
            line([(39, 12), (42, 25), (42, 38)], (110, 75, 40), 3)
            orb(42, 10, 5, (125, 255, 80))
            orb(20, 22, 2, (230, 255, 115)); orb(28, 22, 2, (230, 255, 115))
        elif kind == "swamp_hydra":
            poly([(13, 25), (18, 19), (30, 19), (36, 28), (31, 36), (17, 36)])
            for x, y, dx in [(13, 20, -5), (23, 15, 0), (34, 20, 5)]:
                line([(23, 27), (23 + dx, y + 5), (x, y)], main, 4)
                orb(x, y, 5, light)
                orb(x - 1, y, 1, (255, 55, 60)); orb(x + 2, y, 1, (255, 55, 60))
            line([(12, 31), (6, 37), (11, 39)], (130, 180, 70), 3)
        elif kind == "marsh_titan":
            poly([(8, 17), (12, 10), (18, 13), (24, 6), (32, 12), (40, 17), (37, 35), (27, 40), (12, 35)])
            for x, y in [(12, 13), (20, 9), (29, 11), (34, 18), (17, 24)]:
                pygame.draw.rect(surf, (85, 135, 55), (x, y, 5, 3))
            line([(10, 17), (5, 11), (4, 5)], (125, 190, 75), 3)
            line([(36, 17), (42, 12), (44, 5)], (125, 190, 75), 3)
            orb(23, 23, 4, (190, 255, 95))
        elif kind == "crystal_sentinel":
            poly([(24, 3), (36, 16), (31, 35), (24, 43), (14, 31), (12, 16)], light)
            poly([(24, 8), (31, 18), (27, 31), (24, 36), (20, 28), (18, 17)], main)
            for pts in [[(8, 18), (3, 10), (12, 13)], [(39, 17), (45, 8), (42, 21)], [(10, 33), (4, 38), (13, 39)], [(38, 31), (44, 37), (35, 39)]]:
                poly(pts, ice)
            orb(24, 22, 3, (255, 255, 255))
        elif kind == "crystal_dragon":
            poly([(8, 17), (1, 8), (14, 12), (19, 19), (14, 28)], ice)
            poly([(37, 17), (47, 8), (43, 23), (36, 29)], light)
            poly([(13, 19), (20, 13), (31, 15), (38, 24), (30, 33), (18, 32)], main)
            poly([(30, 17), (44, 17), (39, 24), (31, 24)], ice)
            line([(18, 16), (17, 7), (23, 14)], (235, 255, 255), 3)
            line([(28, 15), (32, 5), (35, 15)], (235, 255, 255), 3)
            orb(27, 22, 2, (255, 255, 255))
        elif kind == "sky_archon":
            poly([(13, 15), (19, 8), (30, 8), (36, 17), (32, 34), (17, 34)])
            poly([(17, 10), (23, 2), (27, 10)], gold)
            poly([(15, 18), (6, 11), (10, 24), (16, 27)], light)
            poly([(33, 18), (42, 10), (39, 25), (32, 27)], light)
            line([(37, 22), (43, 35), (44, 42)], gold, 3)
            orb(23, 19, 4, (255, 250, 220))
        elif kind == "celestial_dragon":
            pygame.draw.circle(surf, gold, (24, 22), 17, 2)
            poly([(8, 22), (3, 10), (16, 15), (20, 22), (15, 31)], light)
            poly([(36, 20), (46, 10), (42, 25), (33, 31)], gold)
            poly([(17, 20), (22, 14), (31, 17), (35, 25), (28, 33), (19, 30)], main)
            poly([(29, 19), (43, 18), (37, 26), (30, 25)], light)
            line([(21, 15), (19, 8), (25, 14)], gold, 2)
            orb(28, 22, 2, (255, 255, 255))
        elif kind == "frost_warlord":
            poly([(10, 17), (15, 9), (32, 9), (39, 19), (35, 34), (14, 35)])
            poly([(14, 12), (6, 4), (18, 9), (24, 1), (29, 9), (42, 3), (34, 15)], ice)
            poly([(16, 22), (32, 22), (30, 28), (18, 28)], light)
            line([(8, 23), (5, 33), (12, 39)], (120, 175, 230), 4)
            line([(38, 21), (43, 31), (39, 40)], (120, 175, 230), 4)
            orb(20, 20, 2, (45, 90, 150)); orb(28, 20, 2, (45, 90, 150))
        elif kind == "prism_colossus":
            poly([(9, 18), (15, 9), (22, 13), (27, 5), (36, 13), (41, 21), (35, 36), (25, 42), (12, 35)], light)
            poly([(14, 20), (24, 12), (33, 21), (28, 34), (18, 33)], main)
            poly([(4, 16), (10, 11), (15, 20), (10, 29)], ice)
            poly([(38, 15), (44, 10), (45, 25), (39, 30)], (210, 140, 255))
            line([(18, 21), (23, 26), (20, 31)], (255, 255, 255), 2)
            orb(26, 22, 3, (255, 255, 255))
        elif kind == "astral_seraph":
            pygame.draw.circle(surf, gold, (24, 9), 7, 2)
            for a in range(3):
                y = 13 + a * 7
                poly([(15, y), (3, y - 7), (8, y + 4), (16, y + 8)], light)
                poly([(32, y), (45, y - 7), (40, y + 4), (32, y + 8)], main)
            poly([(17, 15), (24, 11), (31, 15), (29, 33), (24, 39), (19, 33)], light)
            poly([(21, 18), (24, 15), (27, 18), (26, 29), (24, 33), (22, 29)], gold)
            orb(24, 21, 2, (255, 255, 255))
        elif kind == "void_reaper":
            poly([(11, 18), (17, 10), (24, 7), (32, 12), (38, 20), (33, 37), (24, 42), (14, 35)], dark)
            poly([(15, 17), (20, 10), (28, 10), (34, 18), (28, 23), (19, 23)], main)
            line([(33, 24), (40, 13), (44, 5)], (180, 150, 255), 3)
            poly([(37, 11), (44, 3), (46, 13), (42, 17)], light)
            orb(21, 19, 2, (255, 70, 210)); orb(28, 19, 2, (255, 70, 210))
            pygame.draw.circle(surf, (190, 130, 255), (24, 30), 5, 1)
        elif kind == "abyss_hydra":
            poly([(12, 27), (17, 20), (31, 20), (37, 29), (31, 38), (17, 38)], dark)
            for x, y, dx in [(10, 15, -3), (22, 10, 0), (36, 14, 3)]:
                line([(24, 29), (24 + dx, y + 7), (x, y)], main, 5)
                orb(x, y, 5, light)
                pygame.draw.circle(surf, (14, 8, 28), (x, y), 2)
                pygame.draw.circle(surf, (255, 65, 210), (x + 1, y), 1)
            line([(13, 33), (5, 38), (6, 43)], (125, 70, 190), 3)
        else:
            # 혹시 새 보스가 추가되어도 기본 실루엣을 생성합니다.
            poly([(11, 18), (16, 8), (32, 8), (38, 18), (34, 35), (14, 35)])
            orb(20, 21, 3, light); orb(28, 21, 3, light)
            line([(13, 12), (8, 5), (18, 10)], gold, 2)

        size = max(72, int(float(radius) * 2.15))
        return pygame.transform.scale(surf, (size, size))

    # 지역 보스는 색상만 바꾼 공통 그림 대신 전용 실루엣을 사용합니다.
    for _hard_kind, _hard_meta in globals().get("THEME_BOSS_META", {}).items():
        if _hard_kind not in enemy_types:
            continue
        _hard_type = enemy_types[_hard_kind]
        _hard_sprite = _hard_unique_boss_sprite(
            _hard_kind, _hard_meta.get("color", _hard_type.get("color", (180, 150, 220))),
            _hard_meta.get("radius", _hard_type.get("radius", 36))
        )
        _hard_type["sprite"] = _hard_sprite
        _hard_type["flash"] = make_flash(_hard_sprite)
        _hard_type["frost"] = make_tint(_hard_sprite, (70, 125, 255))

    # 지역 보스 이동 속도를 높여 반응을 빠르게 합니다.
    if "THEME_BOSS_MOTION" in globals() and not globals().get("_HARDCORE_BOSS_MOTION_APPLIED", False):
        for _motion_key in THEME_BOSS_MOTION:
            THEME_BOSS_MOTION[_motion_key] = min(2.2, THEME_BOSS_MOTION[_motion_key] * 1.27)
        _HARDCORE_BOSS_MOTION_APPLIED = True

    # ---------- 4) 피할 수 있는 즉사 패턴 3종 ----------
    _HARD_OLD_UPDATE_BOSS = update_boss

    def _hard_safe_pos(pos):
        return pygame.Vector2(
            max(38, min(WIDTH - 38, float(pos.x))),
            max(95, min(HEIGHT - 38, float(pos.y)))
        )

    def _hard_begin_brutal_attack(boss):
        stage = _hard_stage_index()
        cycle = int(boss.get("brutal_cycle", 0)) + 1
        boss["brutal_cycle"] = cycle
        kind = boss.get("kind", "orc")

        # 보스 종류에 따라 주력 즉사 패턴이 달라집니다.
        if kind in ("scorpion_king", "swamp_hydra", "abyss_hydra", "bog_witch", "dune_emperor"):
            mode = "marks"
        elif kind in ("magma_titan", "marsh_titan", "prism_colossus", "crystal_sentinel", "golem", "frostgiant"):
            mode = "ring"
        elif kind in ("dragon", "inferno_dragon", "crystal_dragon", "celestial_dragon", "sand_wyrm", "astral_seraph", "sky_archon", "void_reaper", "lich", "vampire", "crypt_knight", "frost_warlord"):
            mode = "beam"
        else:
            mode = ("marks", "beam", "ring")[(cycle - 1) % 3]

        # 보스마다 다음 공격은 주기적으로 바뀌어, 같은 패턴만 반복하지 않습니다.
        if cycle % 3 == 0:
            mode = ("marks", "beam", "ring")[(cycle + stage) % 3]

        boss["brutal_mode"] = mode
        boss["brutal_total"] = max(32, 50 - (stage - 1) * 2)
        boss["brutal_phase"] = boss["brutal_total"]
        boss["brutal_radius"] = 46 + min(18, (stage - 1) * 2)
        boss["brutal_band"] = 30 + min(12, stage)

        to_player = player_pos - boss["pos"]
        if to_player.length_squared() <= 0:
            to_player = pygame.Vector2(1, 0)
        aim = angle_of(to_player)
        boss["brutal_angle"] = aim

        if mode == "marks":
            # 현재 위치와 한쪽 옆을 함께 노립니다. 경고 원 밖으로 벗어나면 안전합니다.
            direction = to_player.normalize()
            side = pygame.Vector2(-direction.y, direction.x)
            spread = 105 + min(20, stage * 2)
            boss["brutal_marks"] = [
                _hard_safe_pos(player_pos.copy()),
                _hard_safe_pos(player_pos + side * spread),
            ]
        elif mode == "ring":
            boss["brutal_ring_radius"] = 150 + min(85, stage * 9)
            # 청록색으로 표시된 부채꼴이 충격파의 안전 통로입니다.
            boss["brutal_gap_angle"] = (aim + 90 + cycle * 37) % 360
            boss["brutal_gap_half"] = max(28, 42 - stage)
        else:
            boss["brutal_beam_width"] = 20 + min(18, stage * 2)

        banner_text = "보스 강력 패턴! 붉은 예고 구역에서 벗어나세요"
        banner_timer = boss["brutal_total"]
        banner_color = (255, 85, 95)
        banner_blink = True
        snd_boss.play()

    def _hard_force_lethal_hit():
        # 강력한 보스 패턴도 공격력 규칙을 지킵니다: 한 번 맞으면 4 피해.
        # 회피, 무적, 보호막 등 기존 방어 시스템도 정상적으로 적용됩니다.
        hurt_player(4)

    def _hard_resolve_brutal_attack(boss):
        mode = boss.get("brutal_mode", "marks")
        pos = boss["pos"]
        caught = False
        if mode == "marks":
            radius = float(boss.get("brutal_radius", 50)) + player_radius
            caught = any(player_pos.distance_to(mark) <= radius for mark in boss.get("brutal_marks", []))
            for mark in boss.get("brutal_marks", []):
                rings.append({"pos": mark.copy(), "r": radius, "life": 22, "max": 22,
                              "color": enemy_types[boss["kind"]]["color"]})
                spawn_burst(mark, enemy_types[boss["kind"]]["color"], 18)
        elif mode == "beam":
            direction = pygame.Vector2(1, 0).rotate(float(boss.get("brutal_angle", 0))).normalize()
            rel = player_pos - pos
            along = rel.x * direction.x + rel.y * direction.y
            across = abs(direction.x * rel.y - direction.y * rel.x)
            caught = 0 <= along <= max(WIDTH, HEIGHT) * 1.6 and across <= float(boss.get("brutal_beam_width", 28)) + player_radius
            rings.append({"pos": pos.copy(), "r": 100, "life": 20, "max": 20,
                          "color": enemy_types[boss["kind"]]["color"]})
        else:
            rel = player_pos - pos
            distance = rel.length()
            ring_radius = float(boss.get("brutal_ring_radius", 180))
            gap_angle = float(boss.get("brutal_gap_angle", 0))
            gap_half = float(boss.get("brutal_gap_half", 35))
            player_angle = angle_of(rel) if rel.length_squared() else 0.0
            outside_gap = abs(angle_diff(player_angle, gap_angle)) > gap_half
            caught = abs(distance - ring_radius) <= float(boss.get("brutal_band", 36)) + player_radius and outside_gap
            rings.append({"pos": pos.copy(), "r": ring_radius, "life": 24, "max": 24,
                          "color": enemy_types[boss["kind"]]["color"]})

        spawn_burst(player_pos if caught else pos, (255, 70, 85) if caught else enemy_types[boss["kind"]]["color"], 22)
        add_shake(14 if caught else 7)
        snd_zap.play()
        if caught and not game_over:
            _hard_force_lethal_hit()

        stage = _hard_stage_index()
        boss["brutal_phase"] = 0
        boss["brutal_cd"] = max(175, 285 - (stage - 1) * 12)
        boss.pop("brutal_marks", None)

    def update_boss(e):
        old_state = e.get("state", "")
        _HARD_OLD_UPDATE_BOSS(e)
        if not e.get("boss") or e.get("hp", 0) <= 0 or game_over:
            return

        # 보스의 공격 전환이 끝난 뒤 다음 기본 공격도 더 빠르게 준비합니다.
        new_state = e.get("state", "")
        if old_state != "chase" and new_state == "chase":
            e["cooldown"] = max(18, int(e.get("cooldown", 55) * 0.73))

        # 즉사 패턴은 별도 타이머로 동작하므로 기존 보스 AI/스테이지 진행을 덮어쓰지 않습니다.
        if not (0 <= e["pos"].y <= HEIGHT):
            return
        if int(e.get("brutal_phase", 0)) > 0:
            e["brutal_phase"] -= 1
            if e["brutal_phase"] <= 0:
                _hard_resolve_brutal_attack(e)
            return
        e["brutal_cd"] = int(e.get("brutal_cd", 220)) - 1
        if e["brutal_cd"] <= 0:
            _hard_begin_brutal_attack(e)

    # 보스 예고 레이어 위에 즉사 공격을 별도 렌더링합니다.
    _HARD_OLD_DRAW_BOSS_LAYER = draw_boss_layer
    def draw_boss_layer(layer, e):
        _HARD_OLD_DRAW_BOSS_LAYER(layer, e)
        phase = int(e.get("brutal_phase", 0))
        if phase <= 0:
            return

        total = max(1, int(e.get("brutal_total", 1)))
        progress = 1.0 - phase / total
        pulse = 0.5 + 0.5 * math.sin(frame_tick * 0.55)
        col = (255, 55, 65)
        center = (int(e["pos"].x), int(e["pos"].y))
        mode = e.get("brutal_mode", "marks")

        if mode == "marks":
            radius = int(e.get("brutal_radius", 50))
            for mark in e.get("brutal_marks", []):
                c = (int(mark.x), int(mark.y))
                pygame.draw.circle(layer, (255, 25, 45, int(35 + 65 * progress)), c, radius)
                pygame.draw.circle(layer, (255, 65, 75, 235), c, radius, 3)
                pygame.draw.circle(layer, (255, 215, 220, 220), c, max(5, int(radius * (0.25 + 0.55 * progress))), 2)
                pygame.draw.line(layer, (255, 200, 205, 210), (c[0] - 8, c[1]), (c[0] + 8, c[1]), 2)
                pygame.draw.line(layer, (255, 200, 205, 210), (c[0], c[1] - 8), (c[0], c[1] + 8), 2)
        elif mode == "beam":
            direction = pygame.Vector2(1, 0).rotate(float(e.get("brutal_angle", 0)))
            end = e["pos"] + direction * max(WIDTH, HEIGHT) * 1.6
            width = int(9 + 20 * progress)
            pygame.draw.line(layer, (255, 25, 45, int(45 + 70 * pulse)), e["pos"], end, width + 16)
            pygame.draw.line(layer, (255, 65, 75, 230), e["pos"], end, width)
            pygame.draw.line(layer, (255, 235, 235, 245), e["pos"], end, max(2, width // 4))
            pygame.draw.circle(layer, (255, 35, 55, 235), center, 22 + int(10 * progress), 3)
        else:
            radius = int(e.get("brutal_ring_radius", 170))
            gap = float(e.get("brutal_gap_angle", 0))
            half_gap = float(e.get("brutal_gap_half", 35))
            pygame.draw.circle(layer, (255, 35, 55, int(45 + 55 * pulse)), center, radius)
            pygame.draw.circle(layer, (255, 55, 65, 230), center, radius, 5)
            # 안전 통로는 청록색 두 선으로 명확히 표시합니다.
            for ang in (gap - half_gap, gap + half_gap):
                end = e["pos"] + pygame.Vector2(radius, 0).rotate(ang)
                pygame.draw.line(layer, (70, 255, 220, 245), e["pos"], end, 4)
            pygame.draw.circle(layer, (255, 235, 235, 210), center, 15 + int(progress * 10), 2)
# ============================================================
# [9단계] 신규 일반 몬스터 8종 + 일반 몬스터 체력 추가 상향
# 붙여 넣는 위치: 파일 맨 아래쪽, 마지막 `while running:` 바로 위
# 기존 코드나 8단계 보스 패치는 삭제하지 마세요.
# ============================================================
if not globals().get("_NEW_REGULAR_MOBS_PATCH_APPLIED", False):
    _NEW_REGULAR_MOBS_PATCH_APPLIED = True

    # ----- 1) 신규 몬스터 도트 외형 -----
    _NEW_MOB_PIXELS = {
        "void_caster": [
            "....dddd....", "...dppppd...", "..dppppppd..", "..dpkyykpd..",
            "..dpkwwkpd..", "...dppppd...", ".ddppppppdd.", ".dpppyyppppd.",
            "..dppppppd..", "...dd..dd...", "..dd....dd..", "..............",
        ],
        "blood_ravager": [
            "....dddddd....", "...drrrrrrd...", "..drrkrrkrrd..", "..drrrrrrrrd..",
            ".ddrrrwwrrrdd.", "drrdrrrrrrdrrd", "drrdrrrrrrdrrd", ".drrrrrrrrrrd.",
            "..drrroorrrd..", "...dd....dd...", "..ddd....ddd..", "..............",
        ],
        "iron_sentinel": [
            "....dddddd....", "...dggggggd...", "..dggllllggd..", "..dgkgyygkgd..",
            ".ddggggggggdd.", "dggggggggggggd", "dggggllllggggd", "dgggglyylggggd",
            ".ddggggggggdd.", "..dgggddgggd..", "..ddd....ddd..", "..............",
        ],
        "rift_wraith": [
            "....cccc....", "...cwwwwc...", "..cwwwwwwc..", "..cwkkwwc...",
            ".ccwwwwwwcc.", "cwwwwwwwwwwc", "cwwcwwcwwwwc", ".ccwwwwwwcc.",
            "..cwwwwwwc..", "...cc..cc...", "....c..c....", "............",
        ],
        "plague_stalker": [
            "....dddd....", "...dggggd...", "..dggyyggd..", "..dgkggkgd..",
            ".ddggggggdd.", "dggggrgggggd", "dggggggggggd", ".dgggddgggd.",
            "..dggggggd..", "...dd..dd...", "..ddd..ddd..", "............",
        ],
        "storm_harrier": [
            "..dd....dd..", ".dcld....dcld.", "..dcccccc..",
            ".dccclyycccd.", "dccclykkylcccd", "..dccccccccd..", "...dccyyccd...",
            "..dd..dd..", "............",
        ],
        "crystal_brute": [
            "....dddd....", "...dbbbbd...", "..dbccccbd..", "..dbcwwcbd..",
            ".ddbccwwccbdd.", "dbbbccyyccbbbd", "dbbbbccccbbbd", ".ddbbbbbbbbdd.",
            "..dbbdddbbd..", "..ddd....ddd..", "..............",
        ],
        "thorn_witch": [
            ".....dddd.....", "....dppppd....", "...dpgyygpd...", "...dpkwwkpd...",
            "....dppppd....", ".dddppppppddd.", "dggdppppppdggd", ".dggdppppdggd.",
            "..dggddddggd..", "..dd......dd..", "..............",
        ],
    }

    _NEW_MOB_COLORS = {
        "void_caster": {"d": (25, 12, 45), "p": (115, 55, 185), "k": (12, 8, 24),
                        "y": (255, 220, 100), "w": (235, 220, 255)},
        "blood_ravager": {"d": (50, 12, 22), "r": (175, 35, 55), "k": (35, 8, 16),
                          "w": (255, 210, 200), "o": (255, 105, 55)},
        "iron_sentinel": {"d": (25, 30, 45), "g": (95, 115, 145), "l": (180, 200, 225),
                          "k": (12, 18, 30), "y": (255, 190, 65)},
        "rift_wraith": {"c": (45, 125, 175), "w": (180, 240, 255), "k": (25, 35, 75)},
        "plague_stalker": {"d": (20, 45, 24), "g": (65, 145, 60), "y": (220, 255, 70),
                           "k": (10, 22, 12), "r": (155, 70, 40)},
        "storm_harrier": {"d": (20, 35, 65), "c": (55, 145, 225), "l": (170, 230, 255),
                          "y": (255, 235, 90), "k": (10, 20, 40)},
        "crystal_brute": {"d": (15, 35, 65), "b": (40, 100, 180), "c": (80, 205, 255),
                          "w": (225, 250, 255), "y": (255, 230, 120)},
        "thorn_witch": {"d": (20, 40, 25), "p": (110, 70, 150), "g": (65, 130, 55), "k": (8, 18, 12),
                        "y": (220, 255, 105), "w": (235, 245, 220)},
    }

    _NEW_MOB_STATS = {
        # 속도, 추가 체력, 충돌 반경, 빛깔, 스프라이트 확대 배율
        "void_caster":    (0.78, 6, 14, (165, 95, 255), 3),
        "blood_ravager":  (1.42, 7, 16, (235, 65, 85), 3),
        "iron_sentinel":  (0.55, 15, 21, (145, 175, 210), 4),
        "rift_wraith":    (1.52, 3, 14, (125, 215, 255), 3),
        "plague_stalker": (1.18, 8, 16, (115, 200, 80), 3),
        "storm_harrier":  (1.62, 4, 14, (95, 185, 255), 3),
        "crystal_brute":  (0.66, 17, 21, (85, 195, 255), 4),
        "thorn_witch":    (0.82, 7, 15, (140, 205, 100), 3),
    }

    def _new_mob_make_sprite(_rows, _colors, _scale):
        # 도트 행의 길이가 조금 달라도 잘리지 않도록 같은 너비로 맞춥니다.
        _width = max(len(_row) for _row in _rows)
        _fixed_rows = [_row.ljust(_width, ".") for _row in _rows]
        return make_sprite(_fixed_rows, _colors, _scale)

    for _mob_kind, (_mob_speed, _mob_bonus, _mob_radius, _mob_color, _mob_scale) in _NEW_MOB_STATS.items():
        _mob_sprite = _new_mob_make_sprite(_NEW_MOB_PIXELS[_mob_kind], _NEW_MOB_COLORS[_mob_kind], _mob_scale)
        enemy_types[_mob_kind] = {
            "speed": _mob_speed, "hp_bonus": _mob_bonus, "radius": _mob_radius,
            "color": _mob_color, "sprite": _mob_sprite, "flash": make_flash(_mob_sprite),
            "frost": make_tint(_mob_sprite, (30, 80, 150)),
        }

    # 각자 움직임 패턴도 기존 AI 그룹에 등록합니다.
    CHARGERS.update({"blood_ravager", "plague_stalker"})
    SHOOTERS.update({"void_caster", "thorn_witch"})
    FLYERS.update({"rift_wraith", "storm_harrier"})
    enemy_types["void_caster"]["shot_color"] = (190, 90, 255)
    enemy_types["thorn_witch"]["shot_color"] = (125, 235, 85)
    GOLD_VALUE.update({
        "void_caster": 8, "blood_ravager": 7, "iron_sentinel": 10, "rift_wraith": 6,
        "plague_stalker": 8, "storm_harrier": 7, "crystal_brute": 11, "thorn_witch": 8,
    })

    # ----- 2) 지역별 등장표에 신규 일반 몬스터 추가 -----
    _NEW_MOB_POOL_ADDITIONS = {
        # 0번 무한 모드와 1번 던전은 같은 풀을 공유하므로 1번만 추가합니다.
        1: [("blood_ravager", 3, 1800), ("void_caster", 2, 2400),
            ("iron_sentinel", 2, 3300), ("rift_wraith", 2, 3900)],
        2: [("rift_wraith", 3, 1500), ("storm_harrier", 3, 2400),
            ("iron_sentinel", 2, 3300)],
        3: [("blood_ravager", 3, 1500), ("plague_stalker", 3, 2400),
            ("thorn_witch", 2, 3300)],
        4: [("rift_wraith", 3, 1200), ("void_caster", 3, 2100),
            ("iron_sentinel", 2, 3000)],
        5: [("blood_ravager", 3, 1500), ("storm_harrier", 3, 2400),
            ("crystal_brute", 2, 3300)],
        6: [("plague_stalker", 4, 1200), ("thorn_witch", 3, 2100),
            ("rift_wraith", 2, 3000)],
        7: [("void_caster", 3, 600), ("plague_stalker", 3, 900),
            ("storm_harrier", 3, 1500), ("crystal_brute", 2, 2100),
            ("thorn_witch", 2, 2700)],
        8: [("crystal_brute", 4, 900), ("void_caster", 3, 1500),
            ("rift_wraith", 3, 2100), ("iron_sentinel", 2, 3000)],
        9: [("storm_harrier", 4, 600), ("thorn_witch", 3, 1200),
            ("void_caster", 3, 1800), ("crystal_brute", 2, 2700)],
    }
    for _mob_stage, _mob_entries in _NEW_MOB_POOL_ADDITIONS.items():
        _mob_stage_data = STAGES.get(_mob_stage)
        if not _mob_stage_data:
            continue
        _mob_pool = _mob_stage_data.get("pool")
        if not isinstance(_mob_pool, list):
            continue
        _mob_existing = {entry[0] for entry in _mob_pool if isinstance(entry, (tuple, list)) and entry}
        for _mob_entry in _mob_entries:
            if _mob_entry[0] not in _mob_existing:
                _mob_pool.append(_mob_entry)
                _mob_existing.add(_mob_entry[0])

    # ----- 3) 일반 몬스터 체력 곡선을 한 단계 더 올립니다 -----
    # 8단계 패치가 있으면 그 패치의 함수만 교체하므로 체력이 중복 곱셈되지 않습니다.
    def _new_regular_mob_hp_factor():
        _mob_frames = max(0, int(globals().get("survive_frames", 0)))
        _mob_stage = int(globals().get("cur_stage", 0))
        _mob_stage_index = max(1, _mob_stage)
        if _mob_stage <= 0:
            _mob_stage_factor = 1.82 + min(1.05, (_mob_frames / (60 * 75)) * 0.18)
        else:
            _mob_stage_factor = 1.82 + 0.20 * (_mob_stage_index - 1)
        _mob_time_factor = 1.0 + min(0.95, (_mob_frames / (60 * 105)) * 0.20)
        return _mob_stage_factor * _mob_time_factor

    if callable(globals().get("_hard_enemy_hp_factor")):
        # 기존 8단계 make_enemy 래퍼가 이 함수를 사용하므로 새 곡선이 바로 적용됩니다.
        _hard_enemy_hp_factor = _new_regular_mob_hp_factor
    else:
        _MOBS_OLD_MAKE_ENEMY = make_enemy
        def make_enemy(kind, pos):
            _mob_enemy = _MOBS_OLD_MAKE_ENEMY(kind, pos)
            _mob_factor = _new_regular_mob_hp_factor()
            _mob_enemy["hp"] = max(1, int(math.ceil(_mob_enemy.get("hp", 1) * _mob_factor)))
            _mob_enemy["max_hp"] = _mob_enemy["hp"]
            _mob_enemy["regular_mob_hp_boost"] = True
            return _mob_enemy

    print("[9단계] 신규 몬스터 8종과 일반 몬스터 체력 상향 적용 완료")
# ============================================================
# [10단계] 신규 스킬 10종 + 공격/보조 슬롯 7칸 + 혼합 조합 스킬 3개 제한
#          + 일반 몬스터/보스 추가 강화
# 붙여 넣는 위치: 마지막 `while running:` 바로 위
# 1~9단계 패치는 지우지 말고, 이 코드 전체를 한 번만 붙여 넣으세요.
# ============================================================
if not globals().get("_STAGE10_PATCH_APPLIED", False):
    _STAGE10_PATCH_APPLIED = True

    # --------------------------------------------------------
    # 1) 새 스킬 10종: 공격 5개 + 보조 5개
    # --------------------------------------------------------
    _STAGE10_SKILLS = {
        # 공격 스킬
        "화염 사슬": {
            "desc": "가까운 적 사이로 불꽃을\n연쇄시켜 태워요", "max": 5,
            "color": (255, 125, 65),
            "icon": (BLAST_PIXELS, {"r": (235, 55, 35), "o": (255, 145, 50), "y": (255, 235, 135)}),
            "prev": lambda lv: f"연쇄 {3 + lv}명 · 피해 {78 + 8 * lv}%"
        },
        "빙결 창": {
            "desc": "전방을 꿰뚫는 얼음 창으로\n적을 느리게 해요", "max": 5,
            "color": (115, 210, 255),
            "icon": (FROST_PIXELS, FROST_COLORS),
            "prev": lambda lv: f"관통 피해 {75 + 10 * lv}% · 감속 강화"
        },
        "그림자 베기": {
            "desc": "주변을 넓게 베어\n모여든 적을 공격해요", "max": 5,
            "color": (185, 125, 255),
            "icon": (SWORD_PIXELS, {"l": (190, 135, 255), "w": (245, 225, 255), "g": (120, 70, 190), "b": (45, 25, 80)}),
            "prev": lambda lv: f"범위 {109 + 9 * lv} · 피해 {74 + 9 * lv}%"
        },
        "균열 폭발": {
            "desc": "적이 모인 지점에\n차원의 폭발을 일으켜요", "max": 5,
            "color": (255, 95, 160),
            "icon": (BLAST_PIXELS, {"r": (190, 35, 100), "o": (255, 95, 160), "y": (255, 215, 245)}),
            "prev": lambda lv: f"폭발 반경 {88 + 8 * lv} · 피해 {116 + 16 * lv}%"
        },
        "폭풍 화살": {
            "desc": "여러 적을 동시에 조준해\n번개 화살을 날려요", "max": 5,
            "color": (125, 195, 255),
            "icon": (BOLT_PIXELS, {"y": (255, 230, 115), "w": (235, 250, 255)}),
            "prev": lambda lv: f"대상 {3 + lv}명 · 피해 {63 + 8 * lv}%"
        },
        # 보조 스킬
        "강철 의지": {
            "desc": "가끔 공격을 완전히 막고\n짧은 보호 효과를 얻어요", "max": 5,
            "color": (150, 195, 225),
            "icon": (SHIELD_PIXELS, {"d": (40, 65, 90), "s": (120, 185, 220), "l": (225, 250, 255)}),
            "prev": lambda lv: f"피해 무효 확률 {4 * (lv + 1)}% · 발동 대기 3.5초"
        },
        "전투 집중": {
            "desc": "모든 공격 피해가\n단계마다 4% 증가해요", "max": 5,
            "color": (255, 205, 105),
            "icon": (BOLT_PIXELS, {"y": (255, 205, 80), "w": (255, 250, 210)}),
            "prev": lambda lv: f"전체 피해 +{4 * (lv + 1)}%"
        },
        "응급 처치": {
            "desc": "일정 시간마다 체력을\n1 회복해요", "max": 5,
            "color": (125, 245, 160),
            "icon": (HEART_PIXELS, {"h": (80, 210, 125), "w": (215, 255, 225)}),
            "prev": lambda lv: f"회복 주기 {max(8, 14 - lv)}초 · HP +1"
        },
        "정찰자의 감각": {
            "desc": "경험치 구슬을 더 먼 곳에서\n끌어당겨요", "max": 5,
            "color": (135, 210, 255),
            "icon": (MAGNET_PIXELS, MAGNET_COLORS),
            "prev": lambda lv: f"구슬 흡수 범위 +{8 * (lv + 1)}"
        },
        "약탈자의 본능": {
            "desc": "적을 처치했을 때 얻는\n골드가 증가해요", "max": 5,
            "color": (255, 220, 100),
            "icon": (GEM_PIXELS, GEM_COLORS),
            "prev": lambda lv: f"골드 획득 +{6 * (lv + 1)}%"
        },
    }

    for _s10_name, _s10_data in _STAGE10_SKILLS.items():
        if _s10_name not in NEW_SKILLS:
            NEW_SKILLS[_s10_name] = _s10_data
        upgrades[_s10_name] = _s10_data["desc"]
        if _s10_name not in upgrade_names:
            upgrade_names.append(_s10_name)
        _s10_icon, _s10_colors = _s10_data["icon"]
        upgrade_style[_s10_name] = {
            "icon": make_sprite(_s10_icon, _s10_colors, 5),
            "color": _s10_data["color"],
        }
        small_icons[_s10_name] = pygame.transform.scale(upgrade_style[_s10_name]["icon"], (24, 24))

    ATTACK_SKILLS.update({"화염 사슬", "빙결 창", "그림자 베기", "균열 폭발", "폭풍 화살"})
    SUPPORT_SKILLS.update({"강철 의지", "전투 집중", "응급 처치", "정찰자의 감각", "약탈자의 본능"})
    SUPPORT_SKILLS.difference_update(ATTACK_SKILLS)
    ATTACK_SKILL_SLOTS = 7
    SUPPORT_SKILL_SLOTS = 7

    # --------------------------------------------------------
    # 2) 공격 스킬 + 보조 스킬을 합치는 진화 3개 추가
    #    기존 진화까지 합쳐 한 판에서 최대 3개까지만 획득 가능
    # --------------------------------------------------------
    _STAGE10_EVOLUTIONS = {
        "마력 폭주": {
            "skills": ("화염 사슬", "전투 집중"), "min_level": 3,
            "color": (255, 145, 80),
            "desc": "조합: 화염 사슬 연쇄 +2명, 피해 증가, 재사용 대기 감소",
            "preview": "화염 사슬 연쇄 +2 · 피해 x1.5 · 대기 -15%",
        },
        "그림자 군주": {
            "skills": ("그림자 베기", "강철 의지"), "min_level": 3,
            "color": (190, 135, 255),
            "desc": "조합: 그림자 베기의 범위와 피해가 크게 증가해요",
            "preview": "베기 범위 +35 · 피해 x1.5",
        },
        "빙하의 심장": {
            "skills": ("빙결 창", "응급 처치"), "min_level": 3,
            "color": (125, 225, 255),
            "desc": "조합: 빙결 창 피해가 증가하고 적을 더 오래 느리게 해요",
            "preview": "빙결 창 피해 x1.45 · 감속 지속 증가",
        },
    }
    for _s10_evo_name, _s10_evo_data in _STAGE10_EVOLUTIONS.items():
        if _s10_evo_name not in SKILL_EVOLUTIONS:
            SKILL_EVOLUTIONS[_s10_evo_name] = _s10_evo_data
        upgrades[_s10_evo_name] = SKILL_EVOLUTIONS[_s10_evo_name]["desc"]
        if _s10_evo_name not in upgrade_style:
            _s10_col = SKILL_EVOLUTIONS[_s10_evo_name]["color"]
            _s10_sprite = make_sprite(BLAST_PIXELS if _s10_evo_name == "마력 폭주" else STORM_PIXELS,
                                      {"r": _s10_col, "o": (255, 225, 190), "y": (255, 255, 240),
                                       "c": _s10_col, "w": (245, 250, 255)}, 5)
            upgrade_style[_s10_evo_name] = {"icon": _s10_sprite, "color": _s10_col}
            small_icons[_s10_evo_name] = pygame.transform.scale(_s10_sprite, (24, 24))

    _STAGE10_OLD_AVAILABLE_UPGRADES = available_upgrades
    def available_upgrades():
        _s10_pool = _STAGE10_OLD_AVAILABLE_UPGRADES()
        if len(skill_evolutions) >= 3:
            _s10_pool = [n for n in _s10_pool if n not in SKILL_EVOLUTIONS or n in skill_evolutions]
        return _s10_pool

    _STAGE10_OLD_APPLY_UPGRADE = apply_upgrade
    def apply_upgrade(name):
        global pickup_range, gold_mult
        if name in SKILL_EVOLUTIONS and name not in skill_evolutions and len(skill_evolutions) >= 3:
            show_toast("이번 판의 조합 스킬은 최대 3개예요", (255, 205, 120))
            return
        _s10_old_level = skill_levels.get(name, 0)
        _STAGE10_OLD_APPLY_UPGRADE(name)
        _s10_new_level = skill_levels.get(name, _s10_old_level)
        if _s10_new_level > _s10_old_level:
            _s10_added = _s10_new_level - _s10_old_level
            if name == "정찰자의 감각":
                pickup_range += 8 * _s10_added
            elif name == "약탈자의 본능":
                gold_mult += 0.06 * _s10_added

    # --------------------------------------------------------
    # 3) 전투 수치 강화: 일반 몬스터 체력/속도, 보스 체력/공격 속도
    # --------------------------------------------------------
    for _s10_kind_data in enemy_types.values():
        if not _s10_kind_data.get("stage10_speed_boost"):
            _s10_kind_data["speed"] = float(_s10_kind_data.get("speed", 1.0)) * 1.045
            _s10_kind_data["stage10_speed_boost"] = True

    _STAGE10_OLD_MAKE_ENEMY = make_enemy
    def make_enemy(kind, pos):
        _s10_enemy = _STAGE10_OLD_MAKE_ENEMY(kind, pos)
        if isinstance(_s10_enemy, dict) and not _s10_enemy.get("boss"):
            _s10_enemy["hp"] = max(1, int(math.ceil(float(_s10_enemy.get("hp", 1)) * 1.18)))
            _s10_enemy["max_hp"] = _s10_enemy["hp"]
            _s10_enemy["stage10_hp_boost"] = True
        return _s10_enemy

    _STAGE10_OLD_SPAWN_BOSS = spawn_boss
    def spawn_boss(kind, hp_scale=None, final=False):
        _s10_before_count = len(enemies)
        _s10_result = _STAGE10_OLD_SPAWN_BOSS(kind, hp_scale, final)
        _s10_boss = next((e for e in reversed(enemies[_s10_before_count:])
                          if isinstance(e, dict) and e.get("boss") and e.get("kind") == kind), None)
        if _s10_boss is not None:
            _s10_boss["hp"] = max(1, int(math.ceil(float(_s10_boss.get("hp", 1)) * 1.25)))
            _s10_boss["max_hp"] = _s10_boss["hp"]
            _s10_boss["cooldown"] = max(28, int(_s10_boss.get("cooldown", 60) * 0.90))
            _s10_boss["stage10_boss_boost"] = True
        return _s10_result

    _STAGE10_OLD_UPDATE_BOSS = update_boss
    def update_boss(e):
        _s10_old_cd = int(e.get("cooldown", 0)) if isinstance(e, dict) else 0
        _s10_shots_before = len(enemy_shots) if isinstance(globals().get("enemy_shots"), list) else 0
        _s10_result = _STAGE10_OLD_UPDATE_BOSS(e)
        if isinstance(e, dict):
            _s10_new_cd = int(e.get("cooldown", 0))
            # 공격 직후 새 쿨다운을 조금 줄여 보스가 더 자주 행동하도록 합니다.
            if _s10_new_cd > _s10_old_cd + 1:
                e["cooldown"] = max(25, int(_s10_new_cd * 0.90))
        _s10_shots = globals().get("enemy_shots", [])
        for _s10_shot in _s10_shots[_s10_shots_before:]:
            _s10_vel = _s10_shot.get("vel") if isinstance(_s10_shot, dict) else None
            if _s10_vel is not None:
                _s10_shot["vel"] = _s10_vel * 1.10
        return _s10_result

    # 전투 집중: 모든 기존·신규 공격 피해 +4%/단계
    _STAGE10_OLD_DAMAGE_ENEMY = damage_enemy
    def damage_enemy(e, dmg, quiet=False):
        _s10_focus_lv = int(skill_levels.get("전투 집중", 0)) if isinstance(globals().get("skill_levels"), dict) else 0
        if _s10_focus_lv > 0:
            dmg = float(dmg) * (1.0 + 0.04 * _s10_focus_lv)
        return _STAGE10_OLD_DAMAGE_ENEMY(e, dmg, quiet)

    # 강철 의지: 최대 20% 확률로 피해를 막습니다. 발동 후 3.5초 동안 재발동하지 않습니다.
    _STAGE10_OLD_HURT_PLAYER = hurt_player
    def hurt_player(damage=1):
        _s10_lv = int(skill_levels.get("강철 의지", 0)) if isinstance(globals().get("skill_levels"), dict) else 0
        _s10_xt = globals().get("xt")
        if (_s10_lv > 0 and isinstance(_s10_xt, dict) and not game_over
                and invuln_timer <= 0 and _s10_xt.get("stage10_guard_cd", 0) <= 0
                and random.random() < min(0.20, 0.04 * _s10_lv)):
            _s10_xt["stage10_guard_cd"] = 210
            rings.append({"pos": player_pos.copy(), "r": 82, "life": 16, "max": 16, "color": (150, 215, 255)})
            spawn_burst(player_pos, (155, 220, 255), 8)
            floaters.append({"pos": player_pos + pygame.Vector2(0, -28), "text": "BLOCK!",
                             "color": (160, 225, 255), "life": 42})
            return None
        return _STAGE10_OLD_HURT_PLAYER(damage)

    # --------------------------------------------------------
    # 4) 실제 공격 효과: 모든 피해·범위·재사용 대기는 스킬 단계에 따라 증가
    # --------------------------------------------------------
    def _stage10_alive_enemies():
        return [e for e in enemies if isinstance(e, dict) and e.get("hp", 0) > 0
                and "pos" in e and "kind" in e]

    def _stage10_add_arc(start, end, color=None):
        if not isinstance(xt, dict):
            return
        _s10_arcs = xt.setdefault("chain_arcs", [])
        if len(_s10_arcs) < 36:
            _s10_arcs.append({"a": start.copy(), "b": end.copy(), "life": 14, "max": 14,
                              "seed": random.randint(0, 2**30), "stage10_color": color})

    _STAGE10_OLD_FEATURE_UPDATE_ADDED_SKILLS = feature_update_added_skills
    def feature_update_added_skills():
        global player_hp
        _STAGE10_OLD_FEATURE_UPDATE_ADDED_SKILLS()
        if not isinstance(globals().get("xt"), dict):
            return
        # 프레임마다 보호·회복 타이머를 진행합니다.
        xt["stage10_guard_cd"] = max(0, int(xt.get("stage10_guard_cd", 0)) - 1)

        # 응급 처치: 8~14초마다 체력 1 회복. 만피일 때는 대기 완료 상태를 유지합니다.
        _s10_med_lv = int(skill_levels.get("응급 처치", 0))
        if _s10_med_lv > 0:
            _s10_med_cd = max(480, 900 - 60 * _s10_med_lv)
            xt["stage10_med_timer"] = min(_s10_med_cd, int(xt.get("stage10_med_timer", 0)) + 1)
            if xt["stage10_med_timer"] >= _s10_med_cd and player_hp < player_max_hp:
                player_hp = min(player_max_hp, player_hp + 1)
                xt["stage10_med_timer"] = 0
                floaters.append({"pos": player_pos + pygame.Vector2(0, -28), "text": "+HP",
                                 "color": (125, 245, 160), "life": 42})
                rings.append({"pos": player_pos.copy(), "r": 40, "life": 16, "max": 16,
                              "color": (125, 245, 160)})

        _s10_alive = _stage10_alive_enemies()
        if not _s10_alive:
            return

        # A. 화염 사슬: 가까운 적에서 시작해 주변 적에게 연쇄 피해와 화상을 줍니다.
        _s10_lv = int(skill_levels.get("화염 사슬", 0))
        if _s10_lv > 0:
            xt["stage10_fire_chain_cd"] = int(xt.get("stage10_fire_chain_cd", 0)) + 1
            _s10_evo = "마력 폭주" in skill_evolutions
            _s10_cd = max(145, 300 - 25 * _s10_lv)
            if _s10_evo:
                _s10_cd = max(125, int(_s10_cd * 0.85))
            _s10_chain_count = min(7, 2 + _s10_lv + (2 if _s10_evo else 0))
            if xt["stage10_fire_chain_cd"] >= _s10_cd:
                _s10_remaining = list(_s10_alive)
                _s10_first = min(_s10_remaining, key=lambda e: e["pos"].distance_to(player_pos))
                if _s10_first["pos"].distance_to(player_pos) <= 480:
                    xt["stage10_fire_chain_cd"] = 0
                    _s10_prev = player_pos.copy()
                    for _s10_hop in range(_s10_chain_count):
                        if not _s10_remaining:
                            break
                        _s10_target = (_s10_first if _s10_hop == 0 else
                                       min(_s10_remaining, key=lambda e: e["pos"].distance_to(_s10_prev)))
                        _s10_dist = _s10_target["pos"].distance_to(_s10_prev)
                        if _s10_hop > 0 and _s10_dist > 190:
                            break
                        _s10_tpos = _s10_target["pos"].copy()
                        _stage10_add_arc(_s10_prev, _s10_tpos, (255, 145, 70))
                        _s10_mult = (0.70 + 0.08 * _s10_lv) * (1.50 if _s10_evo else 1.0)
                        feature_damage("화염 사슬", _s10_target, projectile_damage * _s10_mult, quiet=True)
                        _s10_target["burn"] = max(_s10_target.get("burn", 0), 45 + 8 * _s10_lv)
                        _s10_target["burn_dmg"] = max(_s10_target.get("burn_dmg", 1), max(1, projectile_damage // 2))
                        spawn_burst(_s10_tpos, (255, 135, 60), 3)
                        _s10_remaining.remove(_s10_target)
                        _s10_prev = _s10_tpos
                    snd_zap.play()

        # B. 빙결 창: 긴 직선의 적을 관통하고 감속시킵니다.
        _s10_lv = int(skill_levels.get("빙결 창", 0))
        if _s10_lv > 0:
            xt["stage10_frost_spear_cd"] = int(xt.get("stage10_frost_spear_cd", 0)) + 1
            _s10_cd = max(145, 240 - 18 * _s10_lv)
            if xt["stage10_frost_spear_cd"] >= _s10_cd:
                _s10_target = min(_s10_alive, key=lambda e: e["pos"].distance_to(player_pos))
                _s10_dir = _s10_target["pos"] - player_pos
                if _s10_dir.length_squared() > 0 and _s10_dir.length() <= 500:
                    _s10_dir = _s10_dir.normalize()
                    xt["stage10_frost_spear_cd"] = 0
                    _s10_hit = []
                    for _s10_e in _s10_alive:
                        _s10_rel = _s10_e["pos"] - player_pos
                        _s10_along = _s10_rel.dot(_s10_dir)
                        _s10_cross = abs(_s10_dir.x * _s10_rel.y - _s10_dir.y * _s10_rel.x)
                        _s10_radius = float(enemy_types.get(_s10_e["kind"], {}).get("radius", 12))
                        if 0 <= _s10_along <= 520 and _s10_cross <= 24 + 2 * _s10_lv + _s10_radius:
                            _s10_hit.append((_s10_along, _s10_e))
                    for _s10_along, _s10_e in sorted(_s10_hit, key=lambda pair: pair[0])[:10]:
                        _s10_bonus = 1.45 if "빙하의 심장" in skill_evolutions else 1.0
                        feature_damage("빙결 창", _s10_e,
                                       projectile_damage * (0.65 + 0.10 * _s10_lv) * _s10_bonus, quiet=True)
                        _s10_e["slow"] = max(_s10_e.get("slow", 0),
                                               120 if "빙하의 심장" in skill_evolutions else 45 + 8 * _s10_lv)
                        spawn_burst(_s10_e["pos"], (130, 220, 255), 3)
                    rings.append({"pos": player_pos.copy(), "r": 125, "life": 14, "max": 14,
                                  "color": (125, 215, 255)})
                    snd_zap.play()

        # C. 그림자 베기: 가까운 적을 한 번에 베어냅니다.
        _s10_lv = int(skill_levels.get("그림자 베기", 0))
        if _s10_lv > 0:
            xt["stage10_shadow_slash_cd"] = int(xt.get("stage10_shadow_slash_cd", 0)) + 1
            _s10_evo = "그림자 군주" in skill_evolutions
            _s10_radius = 100 + 9 * _s10_lv + (35 if _s10_evo else 0)
            _s10_cd = max(150, 240 - 18 * _s10_lv)
            if xt["stage10_shadow_slash_cd"] >= _s10_cd:
                _s10_targets = [e for e in _s10_alive
                                if e["pos"].distance_to(player_pos) <= _s10_radius + enemy_types.get(e["kind"], {}).get("radius", 12)]
                if _s10_targets:
                    xt["stage10_shadow_slash_cd"] = 0
                    rings.append({"pos": player_pos.copy(), "r": _s10_radius, "life": 18, "max": 18,
                                  "color": (185, 120, 255)})
                    _s10_mult = (0.65 + 0.09 * _s10_lv) * (1.50 if _s10_evo else 1.0)
                    for _s10_e in _s10_targets[:18]:
                        feature_damage("그림자 베기", _s10_e, projectile_damage * _s10_mult, quiet=True)
                    spawn_burst(player_pos, (185, 125, 255), 12)
                    snd_zap.play()

        # D. 균열 폭발: 밀집된 적이 있는 위치에 범위 피해를 줍니다.
        _s10_lv = int(skill_levels.get("균열 폭발", 0))
        if _s10_lv > 0:
            xt["stage10_rift_blast_cd"] = int(xt.get("stage10_rift_blast_cd", 0)) + 1
            _s10_cd = max(190, 330 - 24 * _s10_lv)
            if xt["stage10_rift_blast_cd"] >= _s10_cd:
                _s10_near = sorted(_s10_alive, key=lambda e: e["pos"].distance_to(player_pos))[:min(8, len(_s10_alive))]
                _s10_target = random.choice(_s10_near)
                _s10_center = _s10_target["pos"].copy()
                _s10_radius = 80 + 8 * _s10_lv
                xt["stage10_rift_blast_cd"] = 0
                rings.append({"pos": _s10_center.copy(), "r": _s10_radius, "life": 20, "max": 20,
                              "color": (255, 90, 165)})
                for _s10_e in _s10_alive:
                    if _s10_e["pos"].distance_to(_s10_center) <= _s10_radius + enemy_types.get(_s10_e["kind"], {}).get("radius", 12):
                        feature_damage("균열 폭발", _s10_e, projectile_damage * (1.00 + 0.16 * _s10_lv), quiet=True)
                spawn_burst(_s10_center, (255, 105, 180), 9)
                snd_zap.play()

        # E. 폭풍 화살: 여러 표적을 독립적으로 조준합니다.
        _s10_lv = int(skill_levels.get("폭풍 화살", 0))
        if _s10_lv > 0:
            xt["stage10_storm_arrow_cd"] = int(xt.get("stage10_storm_arrow_cd", 0)) + 1
            _s10_cd = max(140, 240 - 20 * _s10_lv)
            if xt["stage10_storm_arrow_cd"] >= _s10_cd:
                _s10_targets = sorted(_s10_alive, key=lambda e: e["pos"].distance_to(player_pos))
                _s10_targets = [e for e in _s10_targets if e["pos"].distance_to(player_pos) <= 470][:(2 + _s10_lv)]
                if _s10_targets:
                    xt["stage10_storm_arrow_cd"] = 0
                    for _s10_e in _s10_targets:
                        _stage10_add_arc(player_pos, _s10_e["pos"], (125, 195, 255))
                        feature_damage("폭풍 화살", _s10_e, projectile_damage * (0.55 + 0.08 * _s10_lv), quiet=True)
                        spawn_burst(_s10_e["pos"], (145, 205, 255), 2)
                    snd_zap.play()

    # --------------------------------------------------------
    # 5) HUD: 공격·보조 스킬 각각 7칸을 겹치지 않게 표시합니다.
    # --------------------------------------------------------
    _STAGE10_OLD_DRAW_HUD = draw_hud
    def draw_hud():
        _STAGE10_OLD_DRAW_HUD()
        # 기존 5칸 배치를 덮고, 더 작은 슬롯으로 7+7칸을 좌우에 재배치합니다.
        _s10_top = HEIGHT - 88
        pygame.draw.rect(screen, (15, 18, 31), (0, _s10_top, WIDTH, 88))
        pygame.draw.line(screen, (76, 88, 125), (8, _s10_top), (WIDTH - 8, _s10_top), 2)
        _s10_groups = [
            ("공격", [n for n in upgrade_names if n in ATTACK_SKILLS and skill_levels.get(n, 0) > 0],
             (255, 150, 120), 12),
            ("보조", [n for n in upgrade_names if n in SUPPORT_SKILLS and skill_levels.get(n, 0) > 0],
             (130, 220, 240), 555),
        ]
        for _s10_label, _s10_names, _s10_col, _s10_x in _s10_groups:
            blit_text(screen, tiny_font, f"{_s10_label} {len(_s10_names)}/7", _s10_col,
                      (_s10_x + 2, HEIGHT - 78))
            for _s10_i, _s10_name in enumerate(_s10_names[:7]):
                _s10_xpos = _s10_x + _s10_i * 33
                _s10_slot = pygame.Rect(_s10_xpos, HEIGHT - 55, 29, 43)
                hud_panel(screen, _s10_slot, upgrade_style[_s10_name]["color"], n=3, bw=2)
                screen.blit(small_icons[_s10_name], (_s10_xpos + 2, HEIGHT - 52))
                blit_text(screen, tiny_font, str(skill_levels[_s10_name]), (255, 255, 255),
                          (_s10_xpos + 14, HEIGHT - 18), True)
        _s10_combo_text = f"조합 스킬 {len(skill_evolutions)}/3"
        blit_text(screen, tiny_font, _s10_combo_text, (235, 220, 155), (WIDTH // 2, HEIGHT - 78), True)
        if skill_evolutions:
            _s10_recent = sorted(skill_evolutions)
            _s10_line = ", ".join(_s10_recent)
            _s10_render = tiny_font.render(_s10_line, True, (195, 205, 225))
            if _s10_render.get_width() > 290:
                _s10_line = f"보유 조합 {len(skill_evolutions)}개"
                _s10_render = tiny_font.render(_s10_line, True, (195, 205, 225))
            screen.blit(_s10_render, _s10_render.get_rect(center=(WIDTH // 2, HEIGHT - 55)))

    print("[10단계] 신규 스킬 10종, 7+7 슬롯, 판당 조합 최대 3개 및 난이도 상향 적용 완료")
# ============================================================
# [11단계] 스킬바 크기 축소 패치
# 붙여 넣는 위치: 마지막 `while running:` 바로 위
# 10단계 패치는 삭제하지 말고, 이 패치만 추가하세요.
# ============================================================
if not globals().get("_STAGE11_COMPACT_SKILL_BAR_APPLIED", False):
    _STAGE11_COMPACT_SKILL_BAR_APPLIED = True

    # 10단계 스킬바만 다시 그리기 위해, 10단계가 저장해 둔 기존 HUD를 호출합니다.
    _stage11_base_draw_hud = globals().get("_STAGE10_OLD_DRAW_HUD")
    if not callable(_stage11_base_draw_hud):
        _stage11_base_draw_hud = draw_hud

    # 스킬 아이콘을 미리 축소해 매 프레임 이미지 변환을 반복하지 않습니다.
    _STAGE11_SMALL_ICONS = {}
    for _s11_name, _s11_icon in list(small_icons.items()):
        try:
            _STAGE11_SMALL_ICONS[_s11_name] = pygame.transform.smoothscale(_s11_icon, (15, 15))
        except Exception:
            _STAGE11_SMALL_ICONS[_s11_name] = _s11_icon

    def draw_hud():
        # 상단 HUD, 체력, 대시, 궁극기, 처치 수 등 기존 UI는 유지합니다.
        _stage11_base_draw_hud()

        # 이전 HUD가 그린 큰 스킬바의 윗부분을 월드 화면으로 복원합니다.
        # 그 아래는 작은 패널로 덮어서 기존 슬롯이 중복 표시되지 않게 합니다.
        _s11_bar_h = 50
        _s11_top = max(0, HEIGHT - _s11_bar_h)
        _s11_restore_top = max(0, HEIGHT - 84)
        _s11_restore_h = max(0, _s11_top - _s11_restore_top)
        if _s11_restore_h > 0:
            try:
                screen.blit(
                    world,
                    (0, _s11_restore_top),
                    pygame.Rect(0, _s11_restore_top, WIDTH, _s11_restore_h),
                )
            except Exception:
                pygame.draw.rect(
                    screen, (22, 24, 40),
                    (0, _s11_restore_top, WIDTH, _s11_restore_h)
                )

        pygame.draw.rect(screen, (15, 18, 31), (0, _s11_top, WIDTH, _s11_bar_h))
        pygame.draw.line(
            screen, (76, 88, 125), (6, _s11_top), (WIDTH - 6, _s11_top), 2
        )

        # 7칸씩 양쪽에 24픽셀 간격으로 배치합니다. 화면 가운데는 조합 표시용입니다.
        _s11_slot_step = 24
        _s11_slot_w = 22
        _s11_slot_h = 25
        _s11_group_width = 7 * _s11_slot_step - 2
        _s11_attack_x = 9
        _s11_support_x = max(_s11_attack_x + _s11_group_width + 8,
                             WIDTH - 9 - _s11_group_width)
        _s11_label_y = _s11_top + 8
        _s11_slot_y = _s11_top + 22

        _s11_groups = [
            ("공격", [n for n in upgrade_names
                      if n in ATTACK_SKILLS and skill_levels.get(n, 0) > 0],
             (255, 150, 120), _s11_attack_x),
            ("보조", [n for n in upgrade_names
                      if n in SUPPORT_SKILLS and skill_levels.get(n, 0) > 0],
             (130, 220, 240), _s11_support_x),
        ]

        for _s11_label, _s11_names, _s11_col, _s11_x in _s11_groups:
            blit_text(
                screen, tiny_font, f"{_s11_label} {len(_s11_names)}/7",
                _s11_col, (_s11_x + 1, _s11_label_y),
            )
            for _s11_i, _s11_name in enumerate(_s11_names[:7]):
                _s11_xpos = _s11_x + _s11_i * _s11_slot_step
                _s11_slot = pygame.Rect(
                    _s11_xpos, _s11_slot_y, _s11_slot_w, _s11_slot_h
                )
                _s11_color = upgrade_style.get(_s11_name, {}).get(
                    "color", (120, 150, 210)
                )
                hud_panel(screen, _s11_slot, _s11_color, n=3, bw=1)
                _s11_icon = _STAGE11_SMALL_ICONS.get(_s11_name)
                if _s11_icon is not None:
                    screen.blit(_s11_icon, (_s11_xpos + 3, _s11_slot_y + 1))
                else:
                    pygame.draw.circle(
                        screen, _s11_color,
                        (_s11_xpos + _s11_slot_w // 2, _s11_slot_y + 8), 4
                    )
                blit_text(
                    screen, tiny_font, str(skill_levels.get(_s11_name, 0)),
                    (255, 255, 255), (_s11_xpos + _s11_slot_w // 2, _s11_slot_y + 20), True
                )

        # 중앙의 조합 표시는 짧게 유지해 슬롯과 겹치지 않게 합니다.
        _s11_combo_count = len(skill_evolutions)
        blit_text(
            screen, tiny_font, f"조합 {_s11_combo_count}/3",
            (235, 220, 155), (WIDTH // 2, _s11_label_y), True
        )
        if _s11_combo_count:
            _s11_combo_name = sorted(skill_evolutions)[-1]
            _s11_combo_surf = tiny_font.render(_s11_combo_name, True, (195, 205, 225))
            _s11_max_combo_w = max(60, _s11_support_x - (_s11_attack_x + _s11_group_width) - 12)
            if _s11_combo_surf.get_width() > _s11_max_combo_w:
                _s11_combo_surf = tiny_font.render(f"조합 {_s11_combo_count}개 보유", True, (195, 205, 225))
            screen.blit(_s11_combo_surf, _s11_combo_surf.get_rect(center=(WIDTH // 2, _s11_top + 35)))

    print("[11단계] 스킬바를 50픽셀 높이로 축소하고 7+7 슬롯과 조합 표시를 유지합니다.")


# ============================================================
# [추가 스킬] 서리 파편 + 수호 결계 + 처형자의 표식
# 모든 신규 스킬은 카드/아이콘/단계 제한과 실제 전투 효과를 함께 등록합니다.
# ============================================================
if not globals().get("_SKILL_DIVERSITY_PATCH_APPLIED", False):
    _SKILL_DIVERSITY_PATCH_APPLIED = True
    _SKILL_DIVERSITY_SKILLS = {
        "서리 파편": {
            "desc": "가까운 적 여러 명에게\n얼음 파편을 날려 감속시켜요", "max": 5,
            "color": (125, 215, 255),
            "icon": (FROST_PIXELS, {"c": (105, 195, 255), "w": (230, 250, 255)}),
            "prev": lambda lv: f"대상 {2 + lv}명 · 피해 {52 + 7 * lv}% · 감속 강화",
        },
        "수호 결계": {
            "desc": "시간이 지나면 보호막을\n하나씩 회복해요", "max": 5,
            "color": (135, 225, 235),
            "icon": (SHIELD_PIXELS, {"d": (35, 95, 120), "s": (100, 210, 225), "l": (225, 255, 255)}),
            "prev": lambda lv: f"보호막 최대 {min(3, 1 + (lv + 1) // 2)}장 · 회복 주기 {max(6, 12 - lv)}초",
        },
        "처형자의 표식": {
            "desc": "강한 적에게 표식을 남겨\n표식 대상에게 추가 피해", "max": 5,
            "color": (255, 170, 115),
            "icon": (CRIT_PIXELS, {"o": (255, 130, 80), "y": (255, 235, 180)}),
            "prev": lambda lv: f"표식 대상 추가 피해 +{10 * (lv + 1)}% · 지속 {150 + 15 * (lv + 1)}프레임",
        },
    }
    for _div_name, _div_data in _SKILL_DIVERSITY_SKILLS.items():
        NEW_SKILLS[_div_name] = _div_data
        upgrades[_div_name] = _div_data["desc"]
        if _div_name not in upgrade_names:
            upgrade_names.append(_div_name)
        _div_icon = make_sprite(_div_data["icon"][0], _div_data["icon"][1], 5)
        upgrade_style[_div_name] = {"icon": _div_icon, "color": _div_data["color"]}
        small_icons[_div_name] = pygame.transform.scale(_div_icon, (24, 24))

    ATTACK_SKILLS.add("서리 파편")
    SUPPORT_SKILLS.update({"수호 결계", "처형자의 표식"})
    SUPPORT_SKILLS.difference_update(ATTACK_SKILLS)

    _SKILL_DIVERSITY_OLD_FEATURE_UPDATE = feature_update_added_skills
    def feature_update_added_skills():
        global shield_hp, player_hp
        _SKILL_DIVERSITY_OLD_FEATURE_UPDATE()
        if not isinstance(globals().get("xt"), dict):
            return

        _div_alive = [e for e in enemies if isinstance(e, dict) and e.get("hp", 0) > 0
                      and "pos" in e and "kind" in e]

        # 1) 서리 파편: 가까운 표적 여러 개를 관통하는 얼음 연쇄 공격.
        _div_frost_lv = int(skill_levels.get("서리 파편", 0))
        if _div_frost_lv > 0 and _div_alive:
            xt["diversity_frost_cd"] = int(xt.get("diversity_frost_cd", 0)) + 1
            _div_frost_cd = max(110, 210 - 18 * _div_frost_lv)
            if xt["diversity_frost_cd"] >= _div_frost_cd:
                _div_targets = sorted(_div_alive, key=lambda e: e["pos"].distance_to(player_pos))
                _div_targets = [e for e in _div_targets if e["pos"].distance_to(player_pos) <= 500][:(1 + _div_frost_lv)]
                if _div_targets:
                    xt["diversity_frost_cd"] = 0
                    _div_prev = player_pos.copy()
                    for _div_target in _div_targets:
                        _div_pos = _div_target["pos"].copy()
                        _stage10_add_arc(_div_prev, _div_pos, (125, 215, 255))
                        # 최대 레벨은 대상 6명 × 0.80배 피해로 제한합니다.
                        _div_damage = projectile_damage * (0.45 + 0.07 * _div_frost_lv)
                        feature_damage("서리 파편", _div_target, _div_damage, quiet=True)
                        _div_slow = 50 + 12 * _div_frost_lv
                        if _div_target.get("boss"):
                            _div_slow = max(12, _div_slow // 2)
                        _div_target["slow"] = max(_div_target.get("slow", 0), _div_slow)
                        spawn_burst(_div_pos, (145, 220, 255), 4)
                        _div_prev = _div_pos
                    rings.append({"pos": player_pos.copy(), "r": 86 + 7 * _div_frost_lv,
                                  "life": 14, "max": 14, "color": (125, 215, 255)})
                    snd_zap.play()

        # 2) 수호 결계: 정해진 간격으로 보호막을 회복합니다. 기존 보호막 처리 흐름을 사용합니다.
        _div_ward_lv = int(skill_levels.get("수호 결계", 0))
        if _div_ward_lv > 0:
            xt["diversity_ward_cd"] = int(xt.get("diversity_ward_cd", 0)) + 1
            _div_ward_period = max(360, 720 - 60 * _div_ward_lv)
            # 실제 최대 보호막 수: 1레벨 1장, 2~3레벨 2장, 4~5레벨 3장.
            _div_ward_cap = min(3, 1 + _div_ward_lv // 2)
            if xt["diversity_ward_cd"] >= _div_ward_period and shield_hp < _div_ward_cap:
                xt["diversity_ward_cd"] = 0
                shield_hp += 1
                rings.append({"pos": player_pos.copy(), "r": 54, "life": 18, "max": 18,
                              "color": (135, 225, 235)})
                spawn_burst(player_pos, (135, 225, 235), 8)
                floaters.append({"pos": player_pos + pygame.Vector2(0, -27), "text": "WARD +1",
                                 "color": (160, 240, 245), "life": 42})

        # 3) 처형자의 표식: 엘리트/보스를 우선 표식하고, 없으면 가장 가까운 적을 선택합니다.
        _div_mark_lv = int(skill_levels.get("처형자의 표식", 0))
        for _div_enemy in _div_alive:
            _div_timer = int(_div_enemy.get("diversity_mark_timer", 0))
            if _div_timer > 0:
                _div_enemy["diversity_mark_timer"] = _div_timer - 1
        if _div_mark_lv > 0 and _div_alive:
            xt["diversity_mark_cd"] = int(xt.get("diversity_mark_cd", 0)) + 1
            _div_mark_period = max(150, 300 - 20 * _div_mark_lv)
            if xt["diversity_mark_cd"] >= _div_mark_period:
                _div_priority = [e for e in _div_alive if e.get("boss") or e.get("elite")]
                _div_candidates = _div_priority or _div_alive
                _div_mark_target = min(_div_candidates, key=lambda e: e["pos"].distance_to(player_pos))
                _div_mark_target["diversity_mark_timer"] = 150 + 15 * _div_mark_lv
                xt["diversity_mark_cd"] = 0
                _div_mark_color = (255, 170, 115)
                rings.append({"pos": _div_mark_target["pos"].copy(), "r": 36, "life": 18, "max": 18,
                              "color": _div_mark_color})
                spawn_burst(_div_mark_target["pos"], _div_mark_color, 7)

    _SKILL_DIVERSITY_OLD_DAMAGE_ENEMY = damage_enemy
    def damage_enemy(e, dmg, quiet=False):
        _div_mark_lv = int(skill_levels.get("처형자의 표식", 0)) if isinstance(e, dict) else 0
        if _div_mark_lv > 0 and int(e.get("diversity_mark_timer", 0)) > 0:
            dmg = float(dmg) * (1.0 + 0.10 * _div_mark_lv)
        return _SKILL_DIVERSITY_OLD_DAMAGE_ENEMY(e, dmg, quiet)


def enemy_attack_damage(enemy):
    """일반 적 2, 엘리트 3, 미니 보스·메인 보스 4 피해를 반환합니다."""
    if not isinstance(enemy, dict):
        return 2
    if enemy.get("boss") or enemy.get("mini_boss") or enemy.get("final"):
        return 4
    if enemy.get("elite"):
        return 3
    return 2


# ============================================================
# [최종 점검] 추가 스킬 등록·카테고리·아이콘 연결 확인
# ============================================================
# 누락된 설명·아이콘·분류가 있으면 게임 진입 전에 원인을 알려 줍니다.
for _audit_skill in list(upgrade_names):
    if _audit_skill not in upgrades:
        raise RuntimeError(f"스킬 설명 누락: {_audit_skill}")
    if _audit_skill not in upgrade_style or _audit_skill not in small_icons:
        raise RuntimeError(f"스킬 아이콘 누락: {_audit_skill}")
    if (_audit_skill in ATTACK_SKILLS) == (_audit_skill in SUPPORT_SKILLS):
        raise RuntimeError(f"스킬 분류 누락 또는 중복: {_audit_skill}")
    if _audit_skill in NEW_SKILLS and not callable(NEW_SKILLS[_audit_skill].get("prev")):
        raise RuntimeError(f"스킬 단계 미리보기 누락: {_audit_skill}")
for _audit_evolution in SKILL_EVOLUTIONS:
    if _audit_evolution not in upgrades or _audit_evolution not in upgrade_style or _audit_evolution not in small_icons:
        raise RuntimeError(f"조합 스킬 등록 누락: {_audit_evolution}")

# UI와 실제 획득 제한을 동일하게 유지합니다.
ATTACK_SKILL_SLOTS = 7
SUPPORT_SKILL_SLOTS = 7
ATTACK_SKILL_MAX_LEVEL = 5
SUPPORT_SKILL_MAX_LEVEL = 5
if ATTACK_SKILLS & SUPPORT_SKILLS:
    raise RuntimeError("공격/보조 스킬이 동시에 분류되었습니다")
# ============================================================
# [15단계] 스킬 전면 교체: 공격 15 + 보조 15 + 합체 12
# ============================================================
if not globals().get("_STAGE15_APPLIED", False):
    _STAGE15_APPLIED = True
    S15_MAX = 5
    S15_POWER = 0.3  # 플레이어 레벨당 스킬 기본 피해 증가량 (밸런스 조절용)

    # 이름: (종류, 설명, 색, 도트, 도트색, 다음 단계 미리보기)
    S15_DEFS = {
        "마력탄": ("atk", "가장 가까운 적을 쫓는\n유도탄을 쏴요", (190, 140, 255), BOLT_PIXELS, {"y": (190, 140, 255)},
                lambda lv: f"피해 {int(100 * (0.8 + 0.2 * (lv + 1)))}% · 간격 {max(60, 130 - 12 * (lv + 1)) / 60:.1f}초"),
        "바람의 검기": ("atk", "전방 부채꼴로 검기를\n날려 적을 밀어내요", (170, 255, 225), CHEVRON_PIXELS, {"c": (170, 255, 225)},
                    lambda lv: f"사거리 {100 + 10 * (lv + 1)} · 피해 {int(100 * (0.9 + 0.18 * (lv + 1)))}%"),
        "화염 장막": ("atk", "내 주변에 불길 장판을\n깔아 지속 피해를 줘요", (255, 120, 40), BLAST_PIXELS,
                  {"r": (230, 60, 30), "o": (255, 150, 50), "y": (255, 230, 130)},
                  lambda lv: f"반경 {60 + 8 * (lv + 1)} · 틱 피해 {int(100 * (0.28 + 0.05 * (lv + 1)))}%"),
        "회전 톱니": ("atk", "날아갔다가 돌아오는\n톱니 부메랑", (80, 225, 205), BLADE_PIXELS, BLADE_COLORS,
                  lambda lv: f"피해 {int(100 * (0.9 + 0.18 * (lv + 1)))}% · 간격 {max(80, 170 - 14 * (lv + 1)) / 60:.1f}초"),
        "벼락 낙하": ("atk", "무작위 적에게 번개가\n떨어져 좁게 폭발해요", (255, 235, 110), STORM_PIXELS, {"c": (170, 180, 215), "y": (255, 230, 70)},
                  lambda lv: f"낙뢰 {1 + (lv + 1) // 2}발 · 피해 {int(100 * (1.2 + 0.22 * (lv + 1)))}%"),
        "수호의 방패": ("atk", "몸 주위를 도는 방패가\n적을 치고 탄을 막아요", (120, 170, 235), SHIELD_PIXELS, SHIELD_COLORS,
                    lambda lv: f"방패 {1 + (lv + 2) // 2}개 · 피해 {int(100 * (0.5 + 0.1 * (lv + 1)))}%"),
        "얼음 창": ("atk", "전방 일직선을 꿰뚫고\n적을 느리게 해요", (130, 210, 255), PIERCE_PIXELS, {"c": (150, 220, 255), "d": (110, 130, 180)},
                lambda lv: f"길이 {300 + 30 * (lv + 1)} · 피해 {int(100 * (0.9 + 0.18 * (lv + 1)))}%"),
        "연쇄 번개": ("atk", "맞은 적에서 주변으로\n번개가 튕겨요", (255, 240, 110), BOLT_PIXELS, {"y": (255, 240, 110)},
                  lambda lv: f"연쇄 {3 + lv}명 · 피해 {int(100 * (0.9 + 0.15 * (lv + 1)))}%"),
        "맹독 플라스크": ("atk", "독병을 던져 넓은\n독 장판을 만들어요", (130, 230, 90), DROP_PIXELS, {"r": (110, 210, 70), "w": (210, 255, 160)},
                    lambda lv: f"반경 {70 + 7 * (lv + 1)} · 틱 피해 {int(100 * (0.3 + 0.06 * (lv + 1)))}%"),
        "가시 덩굴": ("atk", "발밑에서 십자(+) 덩굴이\n솟아 적을 속박해요", (110, 220, 90), CRIT_PIXELS, {"o": (100, 200, 80), "y": (210, 255, 150)},
                  lambda lv: f"팔 길이 {90 + 10 * (lv + 1)} · 속박 {(40 + 8 * (lv + 1)) / 60:.1f}초"),
        "레이저 위성": ("atk", "하늘에서 수직 빔이\n내리꽂혀요", (255, 100, 150), SWORD_PIXELS,
                    {"l": (255, 110, 160), "w": (255, 225, 235), "g": (255, 170, 190), "b": (120, 40, 70)},
                    lambda lv: f"빔 {1 + (lv + 1 >= 3) + (lv + 1 >= 5)}줄 · 피해 {int(100 * (0.75 + 0.15 * (lv + 1)))}%x2"),
        "지진 해일": ("atk", "양옆에서 파도가 몰아쳐\n적을 중앙으로 몰아요", (110, 190, 255), DASH_PIXELS, {"w": (200, 235, 255), "c": (90, 160, 255)},
                  lambda lv: f"피해 {int(100 * (0.5 + 0.1 * (lv + 1)))}% · 간격 {max(150, 300 - 24 * (lv + 1)) / 60:.1f}초"),
        "마법 지뢰": ("atk", "지나간 자리에 지뢰를\n설치해요", (255, 120, 170), BLAST_PIXELS,
                  {"r": (190, 40, 100), "o": (255, 110, 170), "y": (255, 220, 240)},
                  lambda lv: f"반경 {58 + 6 * (lv + 1)} · 피해 {int(100 * (1.0 + 0.2 * (lv + 1)))}%"),
        "독박쥐 떼": ("atk", "무작위 방향으로 적을\n꿰뚫는 독박쥐 발사", (170, 120, 230), BAT_PIXELS, BAT_COLORS,
                  lambda lv: f"박쥐 {4 + lv}마리 · 피해 {int(100 * (0.5 + 0.1 * (lv + 1)))}% + 독"),
        "신성한 빛": ("atk", "주기적으로 화면 전체에\n빛의 심판을 내려요", (255, 235, 140), AURA_PIXELS, {"o": (255, 220, 110), "p": (255, 250, 215)},
                  lambda lv: f"피해 {int(100 * (0.8 + 0.2 * (lv + 1)))}% · 간격 {max(300, 720 - 60 * (lv + 1)) / 60:.0f}초"),
        # ---- 보조 ----
        "거인의 힘": ("sup", "기본 피해량이\n늘어요", (235, 85, 85), SWORD_PIXELS, SWORD_COLORS,
                  lambda lv: "기본 피해 +1 · 전체 피해 +5%"),
        "가벼운 깃털": ("sup", "기본 공격 속도와\n회전 속도가 빨라져요", (255, 200, 60), BOLT_PIXELS, BOLT_COLORS,
                   lambda lv: f"공격 간격 {max(8, fire_interval - 3)}프레임 · 회전 +8%"),
        "확장의 돋보기": ("sup", "공격 범위와 투사체\n크기가 커져요", (160, 220, 255), AURA_PIXELS, AURA_COLORS,
                    lambda lv: f"범위 +{10 * (lv + 1)}% (누적)"),
        "환영의 거울": ("sup", "투사체 발사 개수가\n늘어요", (200, 180, 255), MULTISHOT_PIXELS, {"y": (200, 180, 255)},
                   lambda lv: "투사체 +1" if (lv + 1) % 2 == 1 else "전체 피해 +5%"),
        "헤르메스의 신발": ("sup", "이동 속도가 빨라지고\n대시를 자주 써요", (110, 255, 170), DASH_PIXELS, DASH_COLORS,
                       lambda lv: "이동 +0.25 · 대시 대기 단축"),
        "시간의 모래시계": ("sup", "스킬 쿨타임이\n줄어요", (190, 160, 255), GEM_PIXELS, {"b": (190, 160, 255), "w": (240, 230, 255)},
                      lambda lv: f"쿨타임 약 {int(100 * (1 - 1 / (1 + 0.08 * (lv + 1))))}% 감소"),
        "생명의 부적": ("sup", "최대 체력이\n늘어요", (255, 110, 130), HEART_PIXELS, HEART_COLORS,
                   lambda lv: "최대 체력 +1" if (lv + 1) % 2 == 1 else "체력 1 회복"),
        "재생의 반지": ("sup", "시간이 지나면 체력이\n1씩 회복돼요", (120, 255, 150), HEART_PIXELS, {"h": (90, 220, 120), "w": (200, 255, 210)},
                   lambda lv: f"{max(480, 1000 - 110 * (lv + 1)) / 60:.0f}초마다 HP +1"),
        "자석 방울": ("sup", "아이템 획득 반경이\n넓어져요", (175, 125, 255), MAGNET_PIXELS, MAGNET_COLORS,
                  lambda lv: "줍기 범위 +22"),
        "지혜의 고서": ("sup", "획득 경험치량이\n늘어요", (130, 200, 255), GEM_PIXELS, GEM_COLORS,
                   lambda lv: "경험치 +10%"),
        "강철 갑옷": ("sup", "피격 피해가\n줄어들어요", (170, 190, 215), SHIELD_PIXELS, {"d": (50, 60, 80), "s": (150, 170, 200), "l": (230, 240, 255)},
                  lambda lv: f"피해 {0.4 * (lv + 1):.1f} 감소 (소수는 확률)"),
        "탐욕의 동전": ("sup", "골드 획득량이\n늘어요", (255, 215, 80), GEM_PIXELS, {"b": (255, 205, 70), "w": (255, 245, 190)},
                   lambda lv: "골드 +12%"),
        "흡혈 송곳니": ("sup", "처치 시 확률로\n체력이 회복돼요", (215, 55, 95), DROP_PIXELS, DROP_COLORS,
                   lambda lv: f"처치 시 {3 * (lv + 1)}% 확률 HP+1 (4초 대기)"),
        "가시 갑각": ("sup", "피격 시 주변 적에게\n반사 피해를 줘요", (255, 110, 110), SHIELD_PIXELS, {"d": (110, 30, 40), "s": (230, 90, 90), "l": (255, 200, 200)},
                  lambda lv: f"반사 피해 {int(100 * (1.0 + 0.35 * (lv + 1)))}%"),
        "저주의 해골": ("sup", "적이 늘고 강해지는 대신\n경험치를 더 얻어요", (170, 110, 220), CRIT_PIXELS, {"o": (170, 110, 220), "y": (235, 210, 255)},
                   lambda lv: f"적 수 +{10 * (lv + 1)}% 체력 +{8 * (lv + 1)}% 속도 +{6 * (lv + 1)}% / 경험치 +{12 * (lv + 1)}%"),
    }

    S15_EVOS = {
        "은하수 폭격": {"skills": ("마력탄", "환영의 거울"), "color": (170, 200, 255),
                    "desc": "조합: 화면 전체에 무작위\n유성우가 쏟아져요", "preview": "유성 4발+ · 화면 전체 폭격"},
        "진공 칼날": {"skills": ("바람의 검기", "시간의 모래시계"), "color": (170, 255, 225),
                  "desc": "조합: 쿨타임 없이 전방에\n회오리가 계속 생겨요", "preview": "0.3초마다 회오리 · 넉백"},
        "지옥불 영역": {"skills": ("화염 장막", "확장의 돋보기"), "color": (255, 80, 40),
                   "desc": "조합: 초대형 불길 장판\n적이 느려지고 더 아파해요", "preview": "범위 x1.8 · 감속 · 받는 피해 +20%"},
        "절대 영도의 창": {"skills": ("얼음 창", "거인의 힘"), "color": (140, 220, 255),
                    "desc": "조합: 초거대 관통 창\n지나간 자리에 빙판이 남아요", "preview": "폭 x2.4 · 피해 x1.6 · 빙판"},
        "칼날 폭풍": {"skills": ("수호의 방패", "가벼운 깃털"), "color": (110, 240, 220),
                  "desc": "조합: 방패가 톱니로 변해\n눈에 안 보일 속도로 돌아요", "preview": "톱니 +2 · 회전 x2.4 · 피해 x1.6"},
        "흡혈의 숲": {"skills": ("가시 덩굴", "재생의 반지"), "color": (130, 235, 110),
                  "desc": "조합: 덩굴이 남아있고 그 위에서\n죽은 적이 폭발·체력 회복", "preview": "덩굴 장판 유지 · 처치 폭발 · 회복"},
        "뇌전 폭풍": {"skills": ("벼락 낙하", "연쇄 번개"), "color": (255, 240, 130),
                  "desc": "조합: 내 주변에 번개가 떨어져\n전기 그물을 만들어요", "preview": "6곳 낙뢰 · 전기 그물 · 기절"},
        "궤도 폭격": {"skills": ("레이저 위성", "가벼운 깃털"), "color": (255, 120, 170),
                  "desc": "조합: 4줄기 빔이 내 주위를\n고속으로 회전해요", "preview": "빔 4줄기 상시 회전"},
        "대홍수": {"skills": ("지진 해일", "저주의 해골"), "color": (110, 200, 255),
                 "desc": "조합: 바라보는 방향으로\n파도가 계속 밀려나가요", "preview": "0.4초마다 파도 · 넉백"},
        "클러스터 지뢰": {"skills": ("마법 지뢰", "환영의 거울"), "color": (255, 160, 100),
                    "desc": "조합: 폭발 후 3개의 작은 지뢰가\n분열해 다시 터져요", "preview": "분열 폭발 3개"},
        "피의 축제": {"skills": ("독박쥐 떼", "흡혈 송곳니"), "color": (230, 80, 120),
                  "desc": "조합: 박쥐가 +2마리\n적중할 때마다 체력 회복", "preview": "박쥐 +2 · 6회 적중마다 HP+1"},
        "천상의 금고": {"skills": ("신성한 빛", "탐욕의 동전"), "color": (255, 220, 100),
                   "desc": "조합: 빛에 죽은 적이 폭발하고\n골드를 떨어뜨려요", "preview": "처치 폭발 · 골드 획득"},
    }

    # ----- 등록부 교체 -----
    for _reg in (upgrades, NEW_SKILLS, SKILL_SYNERGIES, SKILL_EVOLUTIONS, RUN_RELICS, ATTACK_SKILLS, SUPPORT_SKILLS):
        _reg.clear()
    upgrade_names[:] = []
    for _n, (_k, _desc, _col, _px, _pc, _pv) in S15_DEFS.items():
        upgrades[_n] = _desc
        upgrade_names.append(_n)
        (ATTACK_SKILLS if _k == "atk" else SUPPORT_SKILLS).add(_n)
        _spr = make_sprite(_px, _pc, 5)
        upgrade_style[_n] = {"icon": _spr, "color": _col}
        small_icons[_n] = pygame.transform.scale(_spr, (24, 24))
        if "_STAGE11_SMALL_ICONS" in globals():
            _STAGE11_SMALL_ICONS[_n] = pygame.transform.smoothscale(small_icons[_n], (15, 15))
    for _n, _d in S15_EVOS.items():
        SKILL_EVOLUTIONS[_n] = {"skills": _d["skills"], "synergy": "", "min_level": 3, "color": _d["color"],
                                "desc": _d["desc"], "preview": _d["preview"]}
        upgrades[_n] = _d["desc"]
        _spr = make_sprite(BLAST_PIXELS, {"r": _d["color"], "o": (255, 225, 190), "y": (255, 255, 240)}, 5)
        upgrade_style[_n] = {"icon": _spr, "color": _d["color"]}
        small_icons[_n] = pygame.transform.scale(_spr, (24, 24))
    ATTACK_SKILL_SLOTS = 7
    SUPPORT_SKILL_SLOTS = 7

    # ----- 판마다 초기화되는 상태 -----
    def _s15_fresh():
        return {"cd": {}, "t": 0, "fang_cd": 0, "vheal_cd": 0, "bheal_cd": 0, "regen": 0, "vheal": 0, "bheal": 0,
                "depth": 0, "holy": 0, "holy_on": False, "holy_gold": 0, "ang": 0.0, "bang": 0.0, "fire_r": 0,
                "missiles": [], "blasts": [], "webs": [], "orbit": [], "lines": [], "ice": [], "flasks": [],
                "zones": [], "vines": [], "beams": [], "obeams": [], "waves": [], "saws": [], "mines": [], "bats": []}

    S15 = _s15_fresh()
    _S15_OLD_RESET = reset_game

    def reset_game():
        global S15, projectile_radius
        _S15_OLD_RESET()
        S15 = _s15_fresh()
        projectile_radius = 5

    def frost_factor(lv):
        if "절대 영도의 창" in skill_evolutions:
            return 0.5
        return max(0.45, 0.75 - 0.06 * skill_levels.get("얼음 창", 0))

    # ----- 카드 선택 관련 -----
    def is_maxed(name):
        return skill_levels.get(name, 0) >= S15_MAX

    def available_upgrades():
        used_a = sum(1 for n in ATTACK_SKILLS if skill_levels.get(n, 0) > 0)
        used_s = sum(1 for n in SUPPORT_SKILLS if skill_levels.get(n, 0) > 0)
        res = []
        for n in upgrade_names:
            if is_maxed(n):
                continue
            if skill_levels.get(n, 0) > 0:
                res.append(n)
            elif n in ATTACK_SKILLS and used_a < ATTACK_SKILL_SLOTS:
                res.append(n)
            elif n in SUPPORT_SKILLS and used_s < SUPPORT_SKILL_SLOTS:
                res.append(n)
        if len(skill_evolutions) < 3:
            for name, data in SKILL_EVOLUTIONS.items():
                if name not in skill_evolutions and all(skill_levels.get(s, 0) >= data["min_level"] for s in data["skills"]):
                    res.append(name)
        return res

    def preview_text(name):
        if name in SKILL_EVOLUTIONS:
            return SKILL_EVOLUTIONS[name]["preview"]
        d = S15_DEFS.get(name)
        return d[5](skill_levels.get(name, 0)) if d else ""

    def apply_upgrade(name):
        global fire_interval, player_speed, pickup_range, player_max_hp, player_hp
        global xp_bonus, gold_mult, dmg_mult, projectile_damage, extra_shots, projectile_radius, dash_cd_max
        if name in SKILL_EVOLUTIONS:
            data = SKILL_EVOLUTIONS[name]
            if name in skill_evolutions or len(skill_evolutions) >= 3:
                return
            if not all(skill_levels.get(s, 0) >= data["min_level"] for s in data["skills"]):
                return
            skill_evolutions.add(name)
            show_toast(f"합체 완료!  {name}", data["color"])
            rings.append({"pos": player_pos.copy(), "r": 120, "life": 24, "max": 24, "color": data["color"]})
            spawn_burst(player_pos, data["color"], 24)
            add_shake(6)
            snd_level.play()
            return
        if name not in S15_DEFS or skill_levels.get(name, 0) >= S15_MAX:
            return
        new = skill_levels.get(name, 0) + 1
        skill_levels[name] = new
        if name == "거인의 힘":
            projectile_damage += 1
            dmg_mult += 0.05
        elif name == "가벼운 깃털":
            fire_interval = max(8, fire_interval - 3)
        elif name == "확장의 돋보기":
            projectile_radius = 5 + new
        elif name == "환영의 거울":
            if new % 2 == 1:
                extra_shots += 1
            else:
                dmg_mult += 0.05
        elif name == "헤르메스의 신발":
            player_speed = min(7.5, player_speed + 0.25)
            dash_cd_max = max(50, dash_cd_max - 6)
        elif name == "생명의 부적":
            if new % 2 == 1:
                player_max_hp += 1
            player_hp = min(player_max_hp, player_hp + 1)
        elif name == "자석 방울":
            pickup_range = min(260, pickup_range + 22)
        elif name == "지혜의 고서":
            xp_bonus += 0.10
        elif name == "탐욕의 동전":
            gold_mult += 0.12
        elif name == "저주의 해골":
            xp_bonus += 0.12

    # ----- 도우미 -----
    def _s15_lv(n):
        return skill_levels.get(n, 0)

    def _s15_evo(n):
        return n in skill_evolutions

    def _s15_A():
        return 1 + 0.10 * _s15_lv("확장의 돋보기")

    def _s15_mirror():
        return (_s15_lv("환영의 거울") + 1) // 2

    def _s15_base():
        return projectile_damage + S15_POWER * (level - 1)

    def _s15_alive():
        return [e for e in enemies if isinstance(e, dict) and e.get("hp", 0) > 0 and "pos" in e and "kind" in e]

    def _s15_rad(e):
        return enemy_types[e["kind"]]["radius"]

    def _s15_ready(key, period):
        c = min(period, S15["cd"].get(key, 0) + 1 + 0.08 * _s15_lv("시간의 모래시계"))
        S15["cd"][key] = c
        return c >= period

    def _s15_reset(key):
        S15["cd"][key] = 0

    def _s15_hit(name, e, mult):
        if e.get("hp", 0) > 0:
            feature_damage(name, e, max(1.0, _s15_base() * mult), True)

    def _s15_push(e, vec, dist):
        if e.get("boss") or vec.length() <= 0:
            return
        e["pos"] += vec.normalize() * dist

    def _s15_nearest(alive, pos, limit):
        best, bd = None, limit
        for e in alive:
            d = e["pos"].distance_to(pos)
            if d < bd:
                best, bd = e, d
        return best

    def _s15_heal():
        global player_hp
        if player_hp < player_max_hp:
            player_hp += 1
            floaters.append({"pos": player_pos + pygame.Vector2(0, -26), "text": "+HP",
                             "color": (120, 255, 140), "life": 40})
            return True
        return False

    def _s15_seg_dist(p, a, b):
        ab = b - a
        l2 = ab.length_squared()
        if l2 == 0:
            return p.distance_to(a)
        t = max(0.0, min(1.0, (p - a).dot(ab) / l2))
        return p.distance_to(a + ab * t)

    def _s15_in_cross(pos, v, pad):
        dx, dy = abs(pos.x - v["pos"].x), abs(pos.y - v["pos"].y)
        return (dx <= v["arm"] + pad and dy <= v["w"] + pad) or (dy <= v["arm"] + pad and dx <= v["w"] + pad)

    def _s15_blast(name, center, radius, mult, alive, color):
        if len(rings) < 60:
            rings.append({"pos": center.copy(), "r": radius, "life": 14, "max": 14, "color": color})
        spawn_burst(center, color, 6)
        n = 0
        for e in alive:
            if e.get("hp", 0) > 0 and e["pos"].distance_to(center) < radius + _s15_rad(e):
                _s15_hit(name, e, mult)
                n += 1
        return n

    def _s15_cone(name, tg, reach, half, mult, push, col, life, alive):
        ang = angle_of(tg["pos"] - player_pos)
        for e in alive:
            if e.get("hp", 0) <= 0:
                continue
            off = e["pos"] - player_pos
            d = off.length()
            if d <= reach + _s15_rad(e) and (d < 30 or abs(angle_diff(angle_of(off), ang)) <= half):
                _s15_hit(name, e, mult)
                _s15_push(e, off, push)
        slashes.append({"ang": ang, "half": half, "reach": reach, "life": life, "max": life, "col": col})

    def _s15_arc(a, b):
        arcs = xt.get("chain_arcs")
        if isinstance(arcs, list) and len(arcs) < 40:
            arcs.append({"a": a.copy(), "b": b.copy(), "life": 12, "max": 12, "seed": random.randint(0, 2 ** 30)})

    # ----- 처치 시 효과 (damage_enemy가 적을 쓰러뜨릴 때 한 번 불러요) -----
    def _s15_on_kill(e):
        global run_gold
        if S15["depth"] >= 3:
            return
        S15["depth"] += 1
        try:
            A = _s15_A()
            lv = _s15_lv("흡혈 송곳니")
            if lv and S15["fang_cd"] <= 0 and random.random() < 0.03 * lv:
                if _s15_heal():
                    S15["fang_cd"] = 240
            if _s15_evo("흡혈의 숲"):
                for v in S15["vines"]:
                    if v["t"] >= 20 and _s15_in_cross(e["pos"], v, _s15_rad(e)):
                        _s15_blast("흡혈의 숲", e["pos"], 52 * A, 0.7 + 0.1 * v["lv"], _s15_alive(), (140, 235, 110))
                        S15["vheal"] += 1
                        if S15["vheal"] >= 3 and S15["vheal_cd"] <= 0 and _s15_heal():
                            S15["vheal"] = 0
                            S15["vheal_cd"] = 150
                        break
            if S15["holy_on"] and _s15_evo("천상의 금고"):
                if S15["holy_gold"] < 40:
                    g = max(1, round(2 * gold_mult))
                    run_gold += g
                    S15["holy_gold"] += g
                    if len(floaters) < 50:
                        floaters.append({"pos": e["pos"] + pygame.Vector2(0, -16), "text": f"+{g}G",
                                         "color": (255, 220, 90), "life": 36})
                spawn_burst(e["pos"], (255, 215, 90), 6)
                _s15_blast("천상의 금고", e["pos"], 44 * A, 0.5, _s15_alive(), (255, 225, 110))
        finally:
            S15["depth"] -= 1

    _S15_OLD_DAMAGE = damage_enemy

    def damage_enemy(e, dmg, quiet=False):
        if isinstance(e, dict) and e.get("s15hell", 0) > 0:
            dmg = float(dmg) * 1.2  # 지옥불 영역: 방어력 감소
        r = _S15_OLD_DAMAGE(e, dmg, quiet)
        if isinstance(e, dict) and e.get("hp", 1) <= 0 and not e.get("s15dead"):
            e["s15dead"] = True
            _s15_on_kill(e)
        return r

    _S15_OLD_HURT = hurt_player

    def hurt_player(damage=1):
        if game_over or invuln_timer > 0:
            return _S15_OLD_HURT(damage)
        armor = _s15_lv("강철 갑옷")
        if armor:
            r = 0.4 * armor
            cut = int(r) + (1 if random.random() < r - int(r) else 0)
            damage = max(1, int(damage) - cut)
        hp0, sh0 = player_hp, shield_hp
        res = _S15_OLD_HURT(damage)
        thorn = _s15_lv("가시 갑각")
        if thorn and (player_hp < hp0 or shield_hp < sh0):
            rad = (110 + 10 * thorn) * _s15_A()
            if len(rings) < 60:
                rings.append({"pos": player_pos.copy(), "r": rad, "life": 14, "max": 14, "color": (255, 110, 110)})
            for e in _s15_alive():
                if e["pos"].distance_to(player_pos) < rad + _s15_rad(e):
                    _s15_hit("가시 갑각", e, 1.0 + 0.35 * thorn)
        return res

    _S15_OLD_MAKE_ENEMY = make_enemy

    def make_enemy(kind, pos):
        e = _S15_OLD_MAKE_ENEMY(kind, pos)
        lv = _s15_lv("저주의 해골")
        if lv and isinstance(e, dict) and not e.get("boss"):
            e["hp"] = max(1, int(math.ceil(e["hp"] * (1 + 0.08 * lv))))
            e["max_hp"] = e["hp"]
        return e

    # ----- 매 프레임 스킬 처리 (메인 루프가 이 이름으로 불러요) -----
    def feature_update_added_skills():
        global spawn_timer
        if not isinstance(globals().get("xt"), dict):
            return
        S15["t"] += 1
        t = S15["t"]
        alive = _s15_alive()
        A = _s15_A()
        feather = _s15_lv("가벼운 깃털")
        for k in ("fang_cd", "vheal_cd", "bheal_cd", "holy"):
            S15[k] = max(0, S15[k] - 1)
        for e in alive:
            for k in ("s15a", "s15c", "s15hell"):
                if e.get(k, 0) > 0:
                    e[k] -= 1

        # 재생의 반지
        lv = _s15_lv("재생의 반지")
        if lv:
            S15["regen"] = min(S15["regen"] + 1, 5000)
            if S15["regen"] >= max(480, 1000 - 110 * lv) and player_hp < player_max_hp:
                S15["regen"] = 0
                _s15_heal()

        # 저주의 해골: 더 많이, 더 빠르게 몰려와요
        lv = _s15_lv("저주의 해골")
        if lv and not any(e.get("boss") for e in alive) and not feature_boss_rush_active:
            if random.random() < 0.10 * lv:
                spawn_timer += 1
            if xt["freeze"] <= 0:
                for e in alive:
                    if (e.get("boss") or e["kind"] in SHOOTERS or e.get("feature_frozen", 0) > 0
                            or e.get("st", "chase") != "chase"):
                        continue
                    v = player_pos - e["pos"]
                    d = v.length()
                    if d > 1:
                        e["pos"] += v / d * min(enemy_speed * enemy_types[e["kind"]]["speed"], 3.6) * 0.06 * lv

        # 마력탄 (유도탄) + 은하수 폭격
        lv = _s15_lv("마력탄")
        if lv and alive and _s15_ready("missile", max(60, 130 - 12 * lv)):
            near = sorted([e for e in alive if e["pos"].distance_to(player_pos) < 520],
                          key=lambda e: e["pos"].distance_to(player_pos))
            if near:
                _s15_reset("missile")
                n = 1 + _s15_mirror()
                for i in range(n):
                    tg = near[i % len(near)]
                    a0 = angle_of(tg["pos"] - player_pos) + (i - (n - 1) / 2) * 16
                    S15["missiles"].append({"pos": player_pos.copy(), "vel": pygame.Vector2(6.5, 0).rotate(a0),
                                            "tgt": tg, "life": 150})
                snd_shoot.play()
        for m in S15["missiles"]:
            m["life"] -= 1
            tg = m["tgt"]
            if tg is None or tg.get("hp", 0) <= 0:
                tg = _s15_nearest(alive, m["pos"], 450)
                m["tgt"] = tg
            if tg is not None and m["vel"].length() > 0:
                cur = angle_of(m["vel"])
                diff = angle_diff(angle_of(tg["pos"] - m["pos"]), cur)
                m["vel"] = pygame.Vector2(m["vel"].length(), 0).rotate(cur + max(-7, min(7, diff)))
            m["pos"] += m["vel"]
            for e in alive:
                if e["hp"] > 0 and m["pos"].distance_to(e["pos"]) < _s15_rad(e) + 7 * A:
                    _s15_hit("마력탄", e, 0.8 + 0.2 * max(1, _s15_lv("마력탄")))
                    spawn_burst(m["pos"], (200, 150, 255), 4)
                    m["life"] = 0
                    break
        S15["missiles"] = [m for m in S15["missiles"] if m["life"] > 0 and -40 <= m["pos"].x <= WIDTH + 40
                           and -40 <= m["pos"].y <= HEIGHT + 40]
        if lv and _s15_evo("은하수 폭격") and _s15_ready("galaxy", max(110, 190 - 10 * lv)):
            _s15_reset("galaxy")
            for _ in range(4 + _s15_mirror()):
                S15["blasts"].append({"pos": pygame.Vector2(random.randint(50, WIDTH - 50), random.randint(110, HEIGHT - 90)),
                                      "t": -random.randint(0, 24), "delay": 26, "r": 46 * A, "mult": 0.7 + 0.1 * lv,
                                      "color": (170, 200, 255), "bolt": False, "name": "은하수 폭격"})

        # 바람의 검기 + 진공 칼날
        lv = _s15_lv("바람의 검기")
        if lv and alive:
            reach = (100 + 10 * lv) * A
            if _s15_ready("wind", max(70, 150 - 12 * lv)):
                tg = _s15_nearest(alive, player_pos, reach + 20)
                if tg:
                    _s15_reset("wind")
                    _s15_cone("바람의 검기", tg, reach, 40 + 3 * lv, 0.9 + 0.18 * lv, 38, (170, 255, 225), 10, alive)
                    snd_slash.play()
            if _s15_evo("진공 칼날") and _s15_ready("vacuum", 18):
                tg = _s15_nearest(alive, player_pos, reach * 0.85 + 20)
                if tg:
                    _s15_reset("vacuum")
                    _s15_cone("진공 칼날", tg, reach * 0.85, 36, 0.30 + 0.04 * lv, 14, (200, 255, 240), 6, alive)

        # 화염 장막 + 지옥불 영역
        lv = _s15_lv("화염 장막")
        S15["fire_r"] = 0
        if lv:
            evo = _s15_evo("지옥불 영역")
            r = (60 + 8 * lv) * A * (1.8 if evo else 1.0)
            S15["fire_r"] = r
            tick = (t % 30 == 0)
            for e in alive:
                if e["hp"] > 0 and e["pos"].distance_to(player_pos) < r + _s15_rad(e):
                    if tick:
                        _s15_hit("화염 장막", e, 0.28 + 0.05 * lv)
                    if evo and e["hp"] > 0:
                        e["s15hell"] = 20
                        e["slow"] = max(e.get("slow", 0), 20)

        # 회전 톱니 (부메랑)
        lv = _s15_lv("회전 톱니")
        if lv and alive and _s15_ready("saw", max(80, 170 - 14 * lv)):
            tg = _s15_nearest(alive, player_pos, 480)
            if tg and (tg["pos"] - player_pos).length() > 0:
                _s15_reset("saw")
                aim = (tg["pos"] - player_pos).normalize()
                n = 1 + (_s15_mirror() + 1) // 2
                for i in range(n):
                    S15["saws"].append({"pos": player_pos.copy(), "vel": aim.rotate((i - (n - 1) / 2) * 18) * 7.0,
                                        "t": 0, "ret": False, "h": {}})
                snd_shoot.play()
        for b in S15["saws"]:
            b["t"] += 1
            if not b["ret"]:
                b["pos"] += b["vel"]
                if b["t"] >= 34:
                    b["ret"] = True
            else:
                back = player_pos - b["pos"]
                if back.length() < 18:
                    b["t"] = 999
                else:
                    b["pos"] += back.normalize() * 9.5
            for e in alive:
                if (e["hp"] > 0 and b["t"] - b["h"].get(id(e), -99) >= 18
                        and b["pos"].distance_to(e["pos"]) < 16 * A + _s15_rad(e)):
                    b["h"][id(e)] = b["t"]
                    _s15_hit("회전 톱니", e, 0.9 + 0.18 * max(1, _s15_lv("회전 톱니")))
        S15["saws"] = [b for b in S15["saws"] if b["t"] < 200]

        # 벼락 낙하 + 뇌전 폭풍
        lv = _s15_lv("벼락 낙하")
        if lv and alive and _s15_ready("drop", max(55, 120 - 10 * lv)):
            cand = [e for e in alive if e["pos"].distance_to(player_pos) < 560]
            if cand:
                _s15_reset("drop")
                for tg in random.sample(cand, min(1 + lv // 2, len(cand))):
                    S15["blasts"].append({"pos": tg["pos"].copy(), "t": 0, "delay": 18, "r": (34 + 3 * lv) * A,
                                          "mult": 1.2 + 0.22 * lv, "color": (255, 235, 110), "bolt": True, "name": "벼락 낙하"})
                snd_zap.play()
        if lv and _s15_evo("뇌전 폭풍") and alive and _s15_ready("storm", max(100, 170 - 8 * lv)):
            if any(e["pos"].distance_to(player_pos) < 320 for e in alive):
                _s15_reset("storm")
                pts, base = [], random.uniform(0, 360)
                for i in range(6):
                    p = player_pos + pygame.Vector2(random.uniform(105, 190), 0).rotate(base + 60 * i)
                    p.x = max(30, min(WIDTH - 30, p.x))
                    p.y = max(100, min(HEIGHT - 60, p.y))
                    pts.append(p)
                    S15["blasts"].append({"pos": p.copy(), "t": -(i * 3), "delay": 16, "r": 38 * A,
                                          "mult": 0.8 + 0.12 * lv, "color": (255, 240, 130), "bolt": True, "name": "뇌전 폭풍"})
                S15["webs"].append({"pts": pts, "t": 0, "seed": random.randint(0, 2 ** 30), "mult": 0.5 + 0.08 * lv})
        for w in S15["webs"]:
            w["t"] += 1
            if w["t"] in (18, 28):
                pts = w["pts"]
                segs = [(pts[i], pts[(i + 1) % 6]) for i in range(6)] + [(pts[i], pts[(i + 2) % 6]) for i in range(6)]
                for e in alive:
                    if e["hp"] > 0 and any(_s15_seg_dist(e["pos"], a, b) < 14 * A + _s15_rad(e) for a, b in segs):
                        _s15_hit("뇌전 폭풍", e, w["mult"])
                        e["feature_frozen"] = max(e.get("feature_frozen", 0), 5 if e.get("boss") else 16)
        S15["webs"] = [w for w in S15["webs"] if w["t"] < 40]
        for b in S15["blasts"]:
            b["t"] += 1
            if b["t"] == b["delay"]:
                _s15_blast(b["name"], b["pos"], b["r"], b["mult"], _s15_alive(), b["color"])
                if b["bolt"]:
                    bolts.append({"pos": b["pos"].copy(), "life": 12, "seed": random.randint(0, 2 ** 30)})
                add_shake(2)
        S15["blasts"] = [b for b in S15["blasts"] if b["t"] < b["delay"]]

        # 수호의 방패 + 칼날 폭풍
        lv = _s15_lv("수호의 방패")
        S15["orbit"] = []
        if lv:
            saw = _s15_evo("칼날 폭풍")
            n = 1 + (lv + 1) // 2 + (2 if saw else 0)
            S15["ang"] = (S15["ang"] + 3.2 * (1 + 0.08 * feather) * (2.4 if saw else 1.0)) % 360
            orbit_r = 54 + 3 * lv + (12 if saw else 0)
            rad = (13 + (4 if saw else 0)) * A
            for i in range(n):
                a = S15["ang"] + 360.0 * i / n
                S15["orbit"].append((player_pos + pygame.Vector2(orbit_r, 0).rotate(a), a))
            for bp, a in S15["orbit"]:
                for e in alive:
                    if e["hp"] > 0 and e.get("s15a", 0) <= 0 and bp.distance_to(e["pos"]) < rad + _s15_rad(e):
                        e["s15a"] = 10 if saw else 26
                        _s15_hit("수호의 방패", e, (0.5 + 0.1 * lv) * (1.6 if saw else 1.0))
                        _s15_push(e, e["pos"] - bp, 12)
            if enemy_shots:
                enemy_shots[:] = [s for s in enemy_shots
                                  if not any(s["pos"].distance_to(bp) < rad + 8 for bp, _a in S15["orbit"])]

        # 얼음 창 + 절대 영도의 창
        lv = _s15_lv("얼음 창")
        if lv and alive and _s15_ready("lance", max(70, 150 - 12 * lv)):
            tg = _s15_nearest(alive, player_pos, 480)
            if tg and (tg["pos"] - player_pos).length() > 0:
                _s15_reset("lance")
                evo = _s15_evo("절대 영도의 창")
                d = (tg["pos"] - player_pos).normalize()
                length = 560 if evo else (300 + 30 * lv) * A
                width = (18 + 2 * lv) * A * (2.4 if evo else 1.0)
                mult = (0.9 + 0.18 * lv) * (1.6 if evo else 1.0)
                for e in alive:
                    rel = e["pos"] - player_pos
                    along = rel.dot(d)
                    cross = abs(d.x * rel.y - d.y * rel.x)
                    if 0 <= along <= length and cross <= width + _s15_rad(e):
                        _s15_hit("얼음 창", e, mult)
                        e["slow"] = max(e.get("slow", 0), 100 + 12 * lv)
                S15["lines"].append({"a": player_pos.copy(), "b": player_pos + d * length, "w": width, "life": 14})
                if evo:
                    for k in range(1, int(length // 70) + 1):
                        S15["ice"].append({"pos": player_pos + d * (70 * k), "r": 38 * A})
                    while len(S15["ice"]) > 12:
                        S15["ice"].pop(0)
                snd_zap.play()
        for ln in S15["lines"]:
            ln["life"] -= 1
        S15["lines"] = [ln for ln in S15["lines"] if ln["life"] > 0]
        if S15["ice"] and t % 10 == 0:
            for p in S15["ice"]:
                for e in alive:
                    if e["hp"] > 0 and e["pos"].distance_to(p["pos"]) < p["r"] + _s15_rad(e):
                        e["slow"] = max(e.get("slow", 0), 40)
                        if t % 30 == 0:
                            _s15_hit("절대 영도의 창", e, 0.2 + 0.03 * max(1, lv))

        # 연쇄 번개
        lv = _s15_lv("연쇄 번개")
        if lv and alive and _s15_ready("chain", max(60, 130 - 10 * lv)):
            first = _s15_nearest(alive, player_pos, 440)
            if first:
                _s15_reset("chain")
                remaining, prev = list(alive), player_pos.copy()
                for hop in range(2 + lv):
                    if not remaining:
                        break
                    tg = first if hop == 0 else min(remaining, key=lambda e: e["pos"].distance_to(prev))
                    if hop > 0 and tg["pos"].distance_to(prev) > 150 * A:
                        break
                    tp = tg["pos"].copy()
                    _s15_arc(prev, tp)
                    _s15_hit("연쇄 번개", tg, (0.9 + 0.15 * lv) * (0.75 ** hop))
                    spawn_burst(tp, (255, 240, 130), 3)
                    remaining.remove(tg)
                    prev = tp
                snd_zap.play()

        # 맹독 플라스크
        lv = _s15_lv("맹독 플라스크")
        if lv and alive and len(S15["zones"]) < 4 and _s15_ready("flask", max(110, 230 - 18 * lv)):
            cand = [e for e in alive if e["pos"].distance_to(player_pos) < 460]
            if cand:
                _s15_reset("flask")
                best, best_n = None, -1
                for e in random.sample(cand, min(20, len(cand))):
                    c = sum(1 for o in cand if o["pos"].distance_to(e["pos"]) < 80)
                    if c > best_n:
                        best, best_n = e, c
                S15["flasks"].append({"a": player_pos.copy(), "b": best["pos"].copy(), "t": 0, "lv": lv})
        for f in S15["flasks"]:
            f["t"] += 1
            if f["t"] >= 24:
                S15["zones"].append({"pos": f["b"].copy(), "life": 220 + 20 * f["lv"], "r": (70 + 7 * f["lv"]) * A,
                                     "mult": 0.3 + 0.06 * f["lv"]})
                spawn_burst(f["b"], (130, 230, 90), 8)
        S15["flasks"] = [f for f in S15["flasks"] if f["t"] < 24]
        for z in S15["zones"]:
            z["life"] -= 1
            if z["life"] % 30 == 0:
                for e in alive:
                    if e["hp"] > 0 and e["pos"].distance_to(z["pos"]) < z["r"] + _s15_rad(e):
                        _s15_hit("맹독 플라스크", e, z["mult"])
        S15["zones"] = [z for z in S15["zones"] if z["life"] > 0]

        # 가시 덩굴 + 흡혈의 숲
        lv = _s15_lv("가시 덩굴")
        if lv and alive and _s15_ready("vine", max(90, 190 - 16 * lv)):
            arm = (90 + 10 * lv) * A
            if any(e["pos"].distance_to(player_pos) < arm + 80 for e in alive):
                _s15_reset("vine")
                S15["vines"].append({"pos": player_pos.copy(), "t": 0, "arm": arm, "w": 22 * A, "lv": lv,
                                     "life": 20 + (150 if _s15_evo("흡혈의 숲") else 16)})
        for v in S15["vines"]:
            v["t"] += 1
            if v["t"] == 20:
                root = 40 + 8 * v["lv"]
                for e in alive:
                    if e["hp"] > 0 and _s15_in_cross(e["pos"], v, _s15_rad(e)):
                        _s15_hit("가시 덩굴", e, 0.8 + 0.15 * v["lv"])
                        e["feature_frozen"] = max(e.get("feature_frozen", 0), root // 3 if e.get("boss") else root)
                spawn_burst(v["pos"], (120, 220, 90), 8)
        S15["vines"] = [v for v in S15["vines"] if v["t"] < v["life"]]

        # 레이저 위성 + 궤도 폭격
        lv = _s15_lv("레이저 위성")
        if lv and alive and _s15_ready("sat", max(80, 170 - 14 * lv)):
            cand = [e for e in alive if -10 <= e["pos"].x <= WIDTH + 10]
            if cand:
                _s15_reset("sat")
                n = 1 + (lv >= 3) + (lv >= 5)
                for i, tg in enumerate(random.sample(cand, min(n, len(cand)))):
                    S15["beams"].append({"x": max(30, min(WIDTH - 30, tg["pos"].x)), "t": -i * 6,
                                         "w": (20 + 2 * lv) * A, "m": 0.75 + 0.15 * lv})
        for b in S15["beams"]:
            b["t"] += 1
            if b["t"] in (22, 28):
                for e in alive:
                    if e["hp"] > 0 and abs(e["pos"].x - b["x"]) < b["w"] + _s15_rad(e):
                        _s15_hit("레이저 위성", e, b["m"])
                if b["t"] == 22:
                    add_shake(2)
                    snd_zap.play()
        S15["beams"] = [b for b in S15["beams"] if b["t"] < 36]
        S15["obeams"] = []
        if lv and _s15_evo("궤도 폭격"):
            S15["bang"] = (S15["bang"] + 2.6 * (1 + 0.08 * feather)) % 360
            ends = [player_pos + pygame.Vector2(230 * A, 0).rotate(S15["bang"] + 90 * i) for i in range(4)]
            S15["obeams"] = ends
            for e in alive:
                if e["hp"] > 0 and e.get("s15c", 0) <= 0 and any(
                        _s15_seg_dist(e["pos"], player_pos, en) < 12 * A + _s15_rad(e) for en in ends):
                    e["s15c"] = 22
                    _s15_hit("궤도 폭격", e, 0.45 + 0.07 * lv)

        # 지진 해일 + 대홍수
        lv = _s15_lv("지진 해일")
        if lv and alive:
            if _s15_evo("대홍수"):
                if len(S15["waves"]) < 10 and _s15_ready("flood", 26):
                    _s15_reset("flood")
                    dr = -1 if facing_left else 1
                    S15["waves"].append({"x": player_pos.x + dr * 20.0, "dir": dr, "stop": (-40 if dr < 0 else WIDTH + 40),
                                         "w": 22 * A, "hit": set(), "mult": 0.35 + 0.05 * lv, "carry": False, "name": "대홍수"})
            elif _s15_ready("quake", max(150, 300 - 24 * lv)):
                if any(e["pos"].distance_to(player_pos) < 420 for e in alive):
                    _s15_reset("quake")
                    px = max(70, min(WIDTH - 70, player_pos.x))
                    for dr, x0, stop in ((1, -20.0, px - 55), (-1, WIDTH + 20.0, px + 55)):
                        S15["waves"].append({"x": x0, "dir": dr, "stop": stop, "w": 26 * A, "hit": set(),
                                             "mult": 0.5 + 0.1 * lv, "carry": True, "name": "지진 해일"})
                    snd_boss.play()
        for w in S15["waves"]:
            w["x"] += w["dir"] * (8.0 if not w["carry"] else 9.0)
            for e in alive:
                if e["hp"] <= 0 or not (0 <= e["pos"].y <= HEIGHT):
                    continue
                if abs(e["pos"].x - w["x"]) < w["w"] + _s15_rad(e):
                    first = id(e) not in w["hit"]
                    if first:
                        w["hit"].add(id(e))
                        _s15_hit(w["name"], e, w["mult"])
                    if w["carry"]:
                        _s15_push(e, pygame.Vector2(w["dir"], 0), 9.0)
                    elif first:
                        _s15_push(e, pygame.Vector2(w["dir"], 0), 38)
        S15["waves"] = [w for w in S15["waves"]
                        if not ((w["dir"] > 0 and w["x"] >= w["stop"]) or (w["dir"] < 0 and w["x"] <= w["stop"]))]

        # 마법 지뢰 + 클러스터 지뢰
        lv = _s15_lv("마법 지뢰")
        mines = S15["mines"]
        if lv:
            if _s15_ready("mine", max(70, 150 - 12 * lv)) and len(mines) < 3 + lv // 2:
                if not mines or min(m["pos"].distance_to(player_pos) for m in mines) > 40:
                    _s15_reset("mine")
                    mines.append({"pos": player_pos.copy(), "life": 900, "arm": 24})
            for m in mines:
                m["life"] -= 1
                m["arm"] -= 1
                if m["arm"] <= 0 and any(e["hp"] > 0 and e["pos"].distance_to(m["pos"]) < 28 + _s15_rad(e) for e in alive):
                    m["life"] = 0
                    r, mult = (58 + 6 * lv) * A, 1.0 + 0.2 * lv
                    _s15_blast("마법 지뢰", m["pos"], r, mult, alive, (255, 120, 170))
                    if _s15_evo("클러스터 지뢰"):
                        base = random.uniform(0, 360)
                        for k in range(3):
                            S15["blasts"].append({"pos": m["pos"] + pygame.Vector2(r * 0.9, 0).rotate(base + 120 * k),
                                                  "t": 0, "delay": 26, "r": r * 0.7, "mult": mult * 0.6,
                                                  "color": (255, 160, 100), "bolt": False, "name": "클러스터 지뢰"})
                    add_shake(3)
                    snd_hit.play()
            S15["mines"] = [m for m in mines if m["life"] > 0]

        # 독박쥐 떼 + 피의 축제
        lv = _s15_lv("독박쥐 떼")
        evo_bat = _s15_evo("피의 축제")
        if lv and alive and _s15_ready("bats", max(70, 140 - 12 * lv)):
            if any(e["pos"].distance_to(player_pos) < 450 for e in alive):
                _s15_reset("bats")
                for _ in range(3 + lv + _s15_mirror() + (2 if evo_bat else 0)):
                    S15["bats"].append({"pos": player_pos.copy(), "vel": pygame.Vector2(5.2, 0).rotate(random.uniform(0, 360)),
                                        "life": 110, "pierce": 3, "hit": set()})
                snd_shoot.play()
        for b in S15["bats"]:
            b["pos"] += b["vel"]
            b["life"] -= 1
            for e in alive:
                if e["hp"] > 0 and id(e) not in b["hit"] and b["pos"].distance_to(e["pos"]) < 10 * A + _s15_rad(e):
                    b["hit"].add(id(e))
                    _s15_hit("독박쥐 떼", e, 0.5 + 0.1 * max(1, _s15_lv("독박쥐 떼")))
                    if e["hp"] > 0:
                        e["feature_poison"] = max(e.get("feature_poison", 0), 120)
                        e["feature_poison_dmg"] = max(e.get("feature_poison_dmg", 0), max(1, int(_s15_base() * 0.25)))
                    if evo_bat:
                        S15["bheal"] += 1
                        if S15["bheal"] >= 6 and S15["bheal_cd"] <= 0 and _s15_heal():
                            S15["bheal"] = 0
                            S15["bheal_cd"] = 240
                    b["pierce"] -= 1
                    if b["pierce"] < 0:
                        b["life"] = 0
                        break
        S15["bats"] = [b for b in S15["bats"] if b["life"] > 0 and -40 <= b["pos"].x <= WIDTH + 40
                       and -40 <= b["pos"].y <= HEIGHT + 40]

        # 신성한 빛 + 천상의 금고
        lv = _s15_lv("신성한 빛")
        if lv and _s15_ready("holy", max(300, 720 - 60 * lv)):
            vis = [e for e in alive if 0 <= e["pos"].x <= WIDTH and 0 <= e["pos"].y <= HEIGHT]
            if vis:
                _s15_reset("holy")
                S15["holy"], S15["holy_on"], S15["holy_gold"] = 26, True, 0
                try:
                    for e in vis:
                        _s15_hit("신성한 빛", e, (0.8 + 0.2 * lv) * (0.5 if e.get("boss") else 1.0))
                finally:
                    S15["holy_on"] = False
                add_shake(5)
                snd_level.play()

    # ----- 그리기 -----
    _S15_BAT = pygame.transform.scale(bat_sprite, (26, 26))
    _S15_OLD_DRAW_WORLD = draw_world

    def draw_world():
        result = _S15_OLD_DRAW_WORLD()
        layer = hazard_layer
        layer.fill((0, 0, 0, 0))
        pc = (int(player_pos.x), int(player_pos.y))
        fr = S15.get("fire_r", 0)
        if fr > 0:
            col = (255, 60, 30) if _s15_evo("지옥불 영역") else (255, 120, 40)
            rr = int(fr * (1 + 0.03 * math.sin(frame_tick * 0.25)))
            pygame.draw.circle(layer, (*col, 48), pc, rr)
            pygame.draw.circle(layer, (*col, 170), pc, rr, 3)
        for z in S15["zones"]:
            a = min(1.0, z["life"] / 40)
            c = (int(z["pos"].x), int(z["pos"].y))
            pygame.draw.circle(layer, (120, 230, 90, int(60 * a)), c, int(z["r"]))
            pygame.draw.circle(layer, (170, 255, 130, int(160 * a)), c, int(z["r"]), 2)
        for p in S15["ice"]:
            c = (int(p["pos"].x), int(p["pos"].y))
            pygame.draw.circle(layer, (150, 220, 255, 60), c, int(p["r"]))
            pygame.draw.circle(layer, (210, 245, 255, 150), c, int(p["r"]), 2)
        for b in S15["blasts"]:
            if b["t"] >= 0:
                prog = b["t"] / b["delay"]
                c = (int(b["pos"].x), int(b["pos"].y))
                pygame.draw.circle(layer, (*b["color"], int(30 + 60 * prog)), c, int(b["r"]))
                pygame.draw.circle(layer, (*b["color"], 200), c, int(b["r"]), 2)
                pygame.draw.circle(layer, (255, 255, 255, 150), c, max(2, int(b["r"] * prog)), 1)
        for v in S15["vines"]:
            c = (int(v["pos"].x), int(v["pos"].y))
            arm, w = int(v["arm"]), int(v["w"])
            horiz, vert = (c[0] - arm, c[1] - w, arm * 2, w * 2), (c[0] - w, c[1] - arm, w * 2, arm * 2)
            if v["t"] < 20:
                a = int(35 + 70 * v["t"] / 20)
                for r_ in (horiz, vert):
                    pygame.draw.rect(layer, (255, 90, 70, a), r_)
                    pygame.draw.rect(layer, (255, 170, 150, 200), r_, 2)
            else:
                for r_ in (horiz, vert):
                    pygame.draw.rect(layer, (80, 190, 70, 150), r_)
                    pygame.draw.rect(layer, (170, 255, 130, 230), r_, 2)
                for k in range(-arm + 12, arm, 24):
                    pygame.draw.polygon(layer, (60, 160, 60, 235), [(c[0] + k - 5, c[1] + 6), (c[0] + k, c[1] - 14), (c[0] + k + 5, c[1] + 6)])
                    pygame.draw.polygon(layer, (60, 160, 60, 235), [(c[0] - 6, c[1] + k + 5), (c[0] + 14, c[1] + k), (c[0] - 6, c[1] + k - 5)])
        for b in S15["beams"]:
            if b["t"] < 0:
                continue
            x, w = int(b["x"]), int(b["w"])
            if b["t"] < 22:
                pygame.draw.rect(layer, (255, 80, 110, int(35 + 70 * b["t"] / 22)), (x - w, 0, w * 2, HEIGHT))
                pygame.draw.rect(layer, (255, 160, 180, 200), (x - w, 0, w * 2, HEIGHT), 2)
            elif b["t"] < 30:
                pygame.draw.rect(layer, (255, 90, 140, 170), (x - w, 0, w * 2, HEIGHT))
                pygame.draw.rect(layer, (255, 240, 245, 240), (x - w // 3, 0, max(2, w * 2 // 3), HEIGHT))
        for en in S15["obeams"]:
            pygame.draw.line(layer, (255, 80, 130, 90), pc, (int(en.x), int(en.y)), 22)
            pygame.draw.line(layer, (255, 235, 245, 230), pc, (int(en.x), int(en.y)), 5)
        for w in S15["waves"]:
            x, hw = int(w["x"]), int(w["w"])
            pygame.draw.rect(layer, (110, 190, 255, 85), (x - hw, 0, hw * 2, HEIGHT))
            pygame.draw.line(layer, (220, 245, 255, 220), (x, 0), (x, HEIGHT), 3)
        if S15["holy"] > 0:
            pygame.draw.rect(layer, (255, 245, 200, int(150 * S15["holy"] / 26)), (0, 0, WIDTH, HEIGHT))
        world.blit(layer, (0, 0))

        for m in S15["missiles"]:
            add_glow(world, glow_proj, m["pos"], 0.5)
            pygame.draw.circle(world, (190, 130, 255), (int(m["pos"].x), int(m["pos"].y)), 6)
            pygame.draw.circle(world, (255, 255, 255), (int(m["pos"].x), int(m["pos"].y)), 3)
        for ln in S15["lines"]:
            wd = int(max(4, ln["w"] * 0.7))
            pygame.draw.line(world, (120, 210, 255), ln["a"], ln["b"], wd)
            pygame.draw.line(world, (235, 250, 255), ln["a"], ln["b"], max(2, wd // 3))
        for b in S15["saws"]:
            add_glow(world, glow_gem, b["pos"], 0.7)
            draw_blade(world, b["pos"], frame_tick * 20)
        saw = _s15_evo("칼날 폭풍")
        for bp, a in S15["orbit"]:
            if saw:
                add_glow(world, glow_gem, bp, 0.8)
                draw_blade(world, bp, a)
            else:
                d = pygame.Vector2(1, 0).rotate(a)
                n_ = pygame.Vector2(-d.y, d.x)
                pts = [bp + d * 9, bp + n_ * 9 + d * 2, bp - d * 8 + n_ * 5, bp - d * 8 - n_ * 5, bp - n_ * 9 + d * 2]
                pygame.draw.polygon(world, (120, 170, 235), pts)
                pygame.draw.polygon(world, (225, 240, 255), pts, 2)
        for f in S15["flasks"]:
            pr = f["t"] / 24
            p = f["a"] + (f["b"] - f["a"]) * pr
            pygame.draw.circle(world, (40, 80, 30), (int(p.x), int(p.y - 60 * math.sin(math.pi * pr))), 8)
            pygame.draw.circle(world, (120, 230, 90), (int(p.x), int(p.y - 60 * math.sin(math.pi * pr))), 6)
        for m in S15["mines"]:
            c = (int(m["pos"].x), int(m["pos"].y))
            pygame.draw.circle(world, (30, 26, 36), c, 8)
            pygame.draw.circle(world, (120, 120, 140), c, 8, 2)
            pygame.draw.circle(world, (255, 70, 60) if (frame_tick // 15) % 2 == 0 else (120, 30, 30), c, 3)
        for b in S15["bats"]:
            world.blit(_S15_BAT, _S15_BAT.get_rect(center=(int(b["pos"].x), int(b["pos"].y))))
        for w in S15["webs"]:
            if w["t"] <= 30:
                rng = random.Random(w["seed"])
                pts = w["pts"]
                segs = [(pts[i], pts[(i + 1) % 6]) for i in range(6)] + [(pts[i], pts[(i + 2) % 6]) for i in range(6)]
                for a, b in segs:
                    mid = (a + b) / 2
                    if (b - a).length() > 0:
                        mid += pygame.Vector2(-(b - a).y, (b - a).x).normalize() * rng.randint(-10, 10)
                    pygame.draw.lines(world, (120, 150, 255), False, [a, mid, b], 5)
                    pygame.draw.lines(world, (235, 245, 255), False, [a, mid, b], 2)
        return result

    print("[15단계] 스킬 30종 + 합체 12종 적용 완료")
while running:
    theme_music_update()
    frame_tick += 1
    if toast_timer > 0:
        toast_timer -= 1
    if shop_results:
        shop_anim += 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()

        # 확장 콘텐츠 화면은 별도 메뉴 처리기로 관리합니다.
        if state == "features":
            feature_menu_event(event)
            continue

        # 궁극기 입력은 전투 중에만 받아요. 일시정지 중 Q 포기 기능은 그대로 둡니다.
        if state == "playing" and not game_over and event.type == pygame.KEYDOWN:
            if event.key == feature_settings["ult1_key"]:
                feature_use_ultimate(1)
                continue
            if event.key == feature_settings["ult2_key"]:
                feature_use_ultimate(2)
                continue

        if state == "altar_choice":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    resolve_altar(0)
                elif event.key == pygame.K_2:
                    resolve_altar(1)
                elif event.key == pygame.K_ESCAPE:
                    altar_used = True
                    altar_pos = None
                    state = "playing"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if ALTAR_CARD_RECTS[0].collidepoint(event.pos):
                    resolve_altar(0)
                elif ALTAR_CARD_RECTS[1].collidepoint(event.pos):
                    resolve_altar(1)
            continue

        # --- 첫 화면 / 스테이지 선택 / 업적 / 영구 강화 / 무기 상점 ---
        if state in ("title", "stage_select", "achv", "upgrade", "shop"):
            menu_event(event)
            continue

        # --- 게임오버 후: R 재시작 / N 다음 스테이지 / ESC 타이틀 ---
        if game_over and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                reset_game()
            elif event.key == pygame.K_n and stage_cleared and cur_stage in (1, 2, 3, 4, 5, 6, 8):
                # Stage 7 is the endless Abyss challenge, not a normal story stage.
                cur_stage = 8 if cur_stage == 6 else cur_stage + 1
                reset_game()
            elif event.key == pygame.K_ESCAPE:
                state = "title"

        # --- 일시정지: P 또는 ESC ---
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_p, pygame.K_ESCAPE) and not game_over:
            if state == "playing":
                state = "paused"
            elif state == "paused":
                state = "playing"

        # --- 일시정지 중 Q: 포기하고 지금까지 번 골드 받기 ---
        if state == "paused" and not game_over and event.type == pygame.KEYDOWN and event.key == pygame.K_q:
            state = "playing"
            end_game()

        # --- 레벨업 선택: 1/2/3 키 또는 마우스 클릭 (뜬 직후 12프레임은 입력 무시) ---
        if state == "level_up" and level_up_anim > 12:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    reroll_choices()
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    index = event.key - pygame.K_1
                    if index < len(choices):
                        apply_upgrade(choices[index])
                        state = "playing"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if REROLL_RECT.collidepoint(event.pos):
                    reroll_choices()
                else:
                    for index, card in enumerate(get_card_rects()):
                        if index < len(choices) and card.collidepoint(event.pos):
                            apply_upgrade(choices[index])
                            state = "playing"
                            break

    if state == "level_up":
        level_up_anim += 1

    # ========================================================
    # 게임 진행 (playing 상태일 때만 실행 = 멈춤은 이 블록을 건너뛰는 것)
    # ========================================================
    if state == "playing" and not game_over:
        feature_tick()
        # --- 시간 흐름 + 난이도 상승 ---
        boss_alive = any(e.get("boss") for e in enemies)
        if not boss_alive:
            survive_frames += 1
        if not boss_alive and survive_frames % 600 == 0:  # 10초마다
            spawn_interval = max(12, spawn_interval - 4)
            enemy_speed = min(3.0, enemy_speed + 0.1)
        enemy_hp = 3 + survive_frames // 3600 + cur_def["hp_add"]  # 1분마다 적 체력 +1 (스테이지가 높을수록 단단해요)
        if survive_frames % 60 == 0:
            check_achievements()  # 1초에 한 번 업적 확인

        # --- 타이머들 ---
        if invuln_timer > 0:
            invuln_timer -= 1
        if shake > 0:
            shake -= 1
        if hurt_flash > 0:
            hurt_flash -= 1
        blade_angle = (blade_angle + 4) % 360
        if banner_timer > 0:
            banner_timer -= 1
        if weapon_swing > 0:
            weapon_swing -= 1
        if combo_timer > 0:  # 2.5초 안에 못 잡으면 콤보가 끊겨요
            combo_timer -= 1
            if combo_timer == 0:
                combo = 0
        if shield_level and shield_hp < shield_level:  # 보호막이 천천히 다시 차올라요
            shield_timer += 1
            if shield_timer >= shield_regen(shield_level):
                shield_timer = 0
                shield_hp += 1
                rings.append({"pos": player_pos.copy(), "r": 60, "life": 12, "max": 12, "color": (120, 230, 240)})

        # --- 플레이어 이동 ---
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(0, 0)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            direction.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            direction.x += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            direction.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            direction.y += 1

        hero_walking = direction.length() > 0
        if direction.x != 0:
            facing_left = direction.x < 0  # 가는 방향을 바라봐요

        if direction.length() > 0:
            direction = direction.normalize()
        if dash_cd > 0:
            dash_cd -= 1
        if keys[feature_settings["dash_key"]] and dash_cd == 0 and dash_timer == 0 and direction.length() > 0:
            dash_timer = 10
            dash_dir = direction.copy()
            dash_cd = dash_cd_max
            snd_dash.play()
            dl = skill_levels.get("충격 대시", 0)
            if dl:
                rings.append({"pos": player_pos.copy(), "r": 100, "life": 14, "max": 14, "color": (255, 160, 70)})
                for o in enemies:
                    if o["pos"].distance_to(player_pos) < 100 + enemy_types[o["kind"]]["radius"]:
                        feature_damage("충격 대시", o, 2 * dl + 4, quiet=True)
            invuln_timer = max(invuln_timer, 14)  # 대시 중엔 무적
        if dash_timer > 0:
            dash_timer -= 1
            player_pos += dash_dir * 14
            ghosts.append({"pos": player_pos.copy(), "life": 14, "left": facing_left})  # 잔상
        else:
            player_pos += direction * player_speed

        player_pos.x = max(player_radius, min(WIDTH - player_radius, player_pos.x))
        player_pos.y = max(player_radius, min(HEIGHT - 48 - 30, player_pos.y))

        # --- 보스 등장 ---
        # 무한 모드: 1:30마다 오크 -> 드래곤 -> 골렘 순서 / 스테이지: 정해진 시각에 등장, 마지막 보스를 잡으면 클리어
        boss_alive = any(e.get("boss") for e in enemies)
        if cur_stage == 0:
            if survive_frames >= next_boss_frame and not boss_alive:
                if challenge:
                    # The Abyss challenge has its own themed boss rotation.
                    abyss_bosses = ("void_reaper", "abyss_hydra", "bog_witch", "void_reaper",
                                    "abyss_hydra", "sky_archon")
                    spawn_boss(abyss_bosses[boss_count % len(abyss_bosses)],
                               1.0 + 0.12 * (boss_count // len(abyss_bosses)))
                else:
                    spawn_boss(ENDLESS_BOSSES[boss_count % len(ENDLESS_BOSSES)])
                boss_alive = True
        else:
            bl = cur_def["bosses"]
            if stage_boss_idx < len(bl) and survive_frames >= bl[stage_boss_idx][1] and not boss_alive:
                b_kind, _bt, b_scale = bl[stage_boss_idx]
                stage_boss_idx += 1
                spawn_boss(b_kind, b_scale, stage_boss_idx == len(bl))
                boss_alive = True

        # --- 웨이브 이벤트: 현재 스테이지의 적들이 플레이어 둘레를 포위해요 ---
        if (not boss_alive and not altar_used and altar_pos is None
                and survive_frames >= altar_next_frame):
            altar_pos = pygame.Vector2(random.randint(100, WIDTH - 100),
                                       random.randint(150, HEIGHT - 100))
            banner_text = "고대 제단이 발견됐다!"
            banner_timer = 100
            banner_color = (240, 205, 110)
            banner_blink = False

        if not boss_alive and survive_frames >= next_wave_frame and not feature_boss_rush_active:
            next_wave_frame += 3600
            wave_pool = [(k, w) for k, w, t0 in cur_def["pool"] if survive_frames >= t0]
            for i in range(24):
                ring_pos = player_pos + pygame.Vector2(320, 0).rotate(360 * i / 24)
                kind = random.choices([k for k, _ in wave_pool], [w for _, w in wave_pool])[0]
                enemies.append(make_enemy(kind, ring_pos))
            banner_text = "포위당했다!"
            banner_timer = 120
            banner_color = (255, 170, 60)
            banner_blink = True
            snd_boss.play()

        # --- 스테이지 위험 구역: 고드름 / 용암이 예고 후 떨어져요 (적도 맞아요!) ---
        hz = cur_def["haz"]
        if hz and not boss_alive:
            meteor_timer += 1
            rate = max(int(hz["rate"] * 0.55), hz["rate"] - survive_frames // 300)  # 시간이 갈수록 잦아져요
            if meteor_timer >= rate:
                meteor_timer = random.randint(0, 30)
                if random.random() < 0.6:  # 대부분은 플레이어 근처를 노려요
                    mpos = player_pos + pygame.Vector2(random.uniform(-90, 90), random.uniform(-90, 90))
                else:
                    mpos = pygame.Vector2(random.randint(60, WIDTH - 60), random.randint(110, HEIGHT - 60))
                mpos.x = max(30, min(WIDTH - 30, mpos.x))
                mpos.y = max(100, min(HEIGHT - 30, mpos.y))
                meteors.append({"pos": mpos, "t": 0})
            for m in meteors:
                m["t"] += 1
                if m["t"] == METEOR_WARN:  # 쾅!
                    rings.append({"pos": m["pos"].copy(), "r": hz["r"] * 1.7, "life": 14, "max": 14, "color": hz["color"]})
                    spawn_burst(m["pos"], hz["color"], 10)
                    add_shake(4)
                    snd_hit.play()
                    if m["pos"].distance_to(player_pos) < hz["r"] + player_radius:
                        hurt_player()
                    for o in enemies:
                        if not o.get("boss") and o["pos"].distance_to(m["pos"]) < hz["r"] + enemy_types[o["kind"]]["radius"]:
                            feature_damage("오라", o, 8, quiet=True)
            meteors = [m for m in meteors if m["t"] < METEOR_WARN + 6]

        # --- 적 생성 (보스가 있는 동안은 절반 속도로 나와요) ---
        spawn_timer += 0 if boss_alive else 1
        if not boss_alive and spawn_timer >= spawn_interval and not feature_boss_rush_active:
            spawn_timer = 0
            side = random.choice(["top", "bottom", "left", "right"])
            if side == "top":
                pos = pygame.Vector2(random.randint(0, WIDTH), -20)
            elif side == "bottom":
                pos = pygame.Vector2(random.randint(0, WIDTH), HEIGHT + 20)
            elif side == "left":
                pos = pygame.Vector2(-20, random.randint(0, HEIGHT))
            else:
                pos = pygame.Vector2(WIDTH + 20, random.randint(0, HEIGHT))

            # 스테이지마다 나오는 적과 시작 시간이 달라요
            pool = [(k, w) for k, w, t0 in cur_def["pool"] if survive_frames >= t0]
            kind = random.choices([k for k, _ in pool], [w for _, w in pool])[0]
            if survive_frames >= 3600 and random.random() < 0.015:  # 1분이 지나면 가끔 엘리트가 나와요
                enemies.append(make_elite(kind, pos))
            else:
                enemies.append(make_enemy(kind, pos))

        # --- 자동 공격: 멀티샷이면 부채꼴로 여러 발 ---
        fire_timer += 1
        if fire_timer >= fire_interval and enemies:
            fire_timer = 0
            nearest = min(enemies, key=lambda e: e["pos"].distance_to(player_pos))
            aim = nearest["pos"] - player_pos
            if aim.length() > 0:
                aim = aim.normalize()
                shots = 1 + extra_shots
                for k in range(shots):
                    angle_offset = (k - (shots - 1) / 2) * 10  # 발마다 10도씩 벌어짐
                    projectiles.append({
                        "pos": player_pos.copy(),
                        "vel": aim.rotate(angle_offset) * projectile_speed,
                        "pierce": pierce_level,  # 앞으로 더 뚫을 수 있는 횟수
                        "hit": set(),            # 이미 맞힌 적 (같은 적을 두 번 때리지 않게)
                        "dead": False,
                    })
                snd_shoot.play()
                weapon_swing = 10  # 손에 든 무기를 휙 휘둘러요

        # --- 펫: 플레이어 곁을 돌며 가까운 적을 쏘고, 일부는 체력도 회복해 줘요 ---
        if pet_id:
            pw = WEAPONS[pet_id]
            pstar = weapon_stars.get(pet_id, 1)
            pet_pos += (player_pos + pygame.Vector2(38, 0).rotate(frame_tick * 2) - pet_pos) * 0.12
            pet_timer += 1
            if pet_timer >= max(20, int(pw["pcd"] * (1 - 0.08 * (pstar - 1)))) and enemies:
                pet_timer = 0
                ptgt = min(enemies, key=lambda e: e["pos"].distance_to(pet_pos))
                paim = ptgt["pos"] - pet_pos
                if paim.length() > 0:
                    paim = paim.normalize()
                    pn = pw["pshots"]
                    for k in range(pn):
                        projectiles.append({
                            "pos": pet_pos.copy(), "vel": paim.rotate((k - (pn - 1) / 2) * 12) * projectile_speed,
                            "pierce": 0, "hit": set(), "dead": False,
                            "dmg": max(1, int(projectile_damage * 0.5 * pw["pdmg"] * (1 + 0.2 * (pstar - 1)) + 0.5))})
            if pw.get("pheal"):
                pet_heal += 1
                if pet_heal >= pw["pheal"]:
                    pet_heal = 0
                    if player_hp < player_max_hp:
                        player_hp += 1
                        floaters.append({"pos": player_pos + pygame.Vector2(0, -26), "text": "+HP",
                                         "color": (120, 255, 140), "life": 40})

        # --- 투사체 이동 ---
        for p in projectiles:
            p["pos"] += p["vel"]
        projectiles = [
            p for p in projectiles
            if 0 <= p["pos"].x <= WIDTH and 0 <= p["pos"].y <= HEIGHT
        ]

        # --- 투사체와 적의 충돌 (관통이면 맞고도 계속 날아가요) ---
        for p in projectiles:
            for e in enemies:
                if e["hp"] <= 0 or id(e) in p["hit"]:
                    continue
                r = enemy_types[e["kind"]]["radius"]
                if p["pos"].distance_to(e["pos"]) < projectile_radius + r:
                    feature_damage("유성 파편" if p.get("source") == "comet_synergy" else "기본 투사체", e, p.get("dmg", projectile_damage))
                    if frost_level:
                        e["slow"] = 120  # 냉기: 2초 동안 느려져요
                    if blast_level:
                        explode(p["pos"])  # 폭발탄: 맞은 자리에서 터져요
                    p["hit"].add(id(e))
                    if p["pierce"] > 0:
                        p["pierce"] -= 1
                    else:
                        p["dead"] = True
                        break
        projectiles = [p for p in projectiles if not p["dead"]]

        # --- 번개: 2.5초마다 무작위 적에게 낙뢰 ---
        if lightning_level:
            lightning_timer += 1
            if lightning_timer >= 150 and enemies:
                lightning_timer = 0
                for e in random.sample(enemies, min(lightning_level, len(enemies))):
                    feature_damage("혜성", e, projectile_damage * 2 + 2)
                    bolts.append({"pos": e["pos"].copy(), "life": 12, "seed": random.randint(0, 2**30)})
                    spawn_burst(e["pos"], (255, 240, 120), 8)
                snd_zap.play()
                add_shake(4)

        # --- 오라: 주변 적에게 0.4초마다 지속 피해 ---
        if aura_level:
            aura_timer += 1
            if aura_timer >= 24:
                aura_timer = 0
                for e in enemies:
                    if e["pos"].distance_to(player_pos) < aura_radius(aura_level) + enemy_types[e["kind"]]["radius"]:
                        feature_damage("폭발탄", e, max(1, projectile_damage // 2), quiet=True)

        # --- 불꽃검: 가까운 적이 있으면 부채꼴로 베고, 맞은 적을 3초간 태워요 ---
        if flame_level:
            flame_timer += 1
            if flame_timer >= flame_cd(flame_level):
                reach = flame_reach(flame_level)
                near = [e for e in enemies if e["hp"] > 0 and
                        e["pos"].distance_to(player_pos) < reach + enemy_types[e["kind"]]["radius"]]
                if near:
                    flame_timer = 0
                    target = min(near, key=lambda e: e["pos"].distance_to(player_pos))
                    f_ang = angle_of(target["pos"] - player_pos)
                    f_half = flame_half(flame_level)
                    for e in near:
                        if abs(angle_diff(angle_of(e["pos"] - player_pos), f_ang)) <= f_half + 12:
                            feature_damage("불꽃검", e, flame_damage(flame_level), quiet=True)
                            spawn_burst(e["pos"], (255, 150, 40), 3)
                            if not e.get("boss"):
                                e["burn"] = 180
                                e["burn_dmg"] = flame_burn(flame_level)
                    flames.append({"ang": f_ang, "half": f_half, "reach": reach, "life": 16, "max": 16})
                    snd_flame.play()
                    add_shake(3)

        # --- 혜성 / 재생 (새 스킬) ---
        cl = skill_levels.get("혜성", 0)
        if cl:
            xt["comet"] += 1
            if xt["comet"] >= 210 and enemies:
                xt["comet"] = 0
                for ctgt in random.sample(enemies, min(cl, len(enemies))):
                    cp = ctgt["pos"].copy()
                    start = cp + pygame.Vector2(random.uniform(-55, 55), -150)
                    xt["comets"].append({"start": start, "pos": start.copy(), "target": cp, "t": 0})
                add_shake(4)
                snd_zap.play()
        for c in xt["comets"]:
            c["t"] += 1
            progress = min(1.0, c["t"] / 12)
            c["pos"] = c["start"] + (c["target"] - c["start"]) * progress
            if c["t"] == 12:
                cp = c["target"]
                comet_evolved = "유성 폭격" in skill_evolutions
                comet_radius = 108 if comet_evolved else 70
                rings.append({"pos": cp.copy(), "r": comet_radius, "life": 18, "max": 18,
                              "color": (255, 220, 120) if comet_evolved else (120, 190, 255)})
                spawn_burst(cp, (255, 230, 150) if comet_evolved else (175, 220, 255), 20 if comet_evolved else 12)
                for o in enemies:
                    if o["hp"] > 0 and o["pos"].distance_to(cp) < comet_radius + enemy_types[o["kind"]]["radius"]:
                        feature_damage("혜성", o, projectile_damage * (3.0 if comet_evolved else 2.0) + 2, quiet=True)
                if synergy_active("유성 파편"):
                    star_level = skill_levels.get("별빛 난사", 0)
                    shard_count = (5 + min(3, star_level // 2)) if comet_evolved else (2 + min(1, star_level // 3))
                    shard_damage = max(1, int(projectile_damage * (0.65 if comet_evolved else 0.45)))
                    for shard in range(shard_count):
                        angle = frame_tick * 7 + 360 * shard / shard_count
                        projectiles.append({"pos": cp.copy(),
                                            "vel": pygame.Vector2(projectile_speed * 0.8, 0).rotate(angle),
                                            "pierce": 0, "hit": set(), "dead": False,
                                            "dmg": shard_damage, "source": "comet_synergy"})
                add_shake(5)
        xt["comets"] = [c for c in xt["comets"] if c["t"] < 17]
        wave_level = skill_levels.get("화염 파동", 0)
        if wave_level:
            xt["wave"] += 1
            wave_cd = max(120, 270 - 30 * wave_level)
            if xt["wave"] >= wave_cd and enemies:
                xt["wave"] = 0
                wave_radius = 78 + 10 * wave_level
                rings.append({"pos": player_pos.copy(), "r": wave_radius, "life": 18, "max": 18,
                              "color": (255, 130, 55)})
                spawn_burst(player_pos, (255, 170, 70), 14)
                for e in enemies:
                    if e["hp"] > 0 and e["pos"].distance_to(player_pos) < wave_radius + enemy_types[e["kind"]]["radius"]:
                        feature_damage("화염 파동", e, projectile_damage * (0.7 + 0.1 * wave_level), quiet=True)
                snd_flame.play()

        soul_level = skill_levels.get("영혼 사슬", 0)
        if soul_level:
            xt["soul"] += 1
            soul_cd = max(150, 300 - 25 * soul_level)
            if xt["soul"] >= soul_cd and enemies:
                targets = [e for e in enemies if e["hp"] > 0]
                if targets:
                    xt["soul"] = 0
                    chain_count = 2 + soul_level + int(synergy_active("영혼 공명"))
                    if "영혼 폭주" in skill_evolutions:
                        chain_count += min(4, combo // 5)
                    previous = player_pos.copy()
                    for hop in range(min(chain_count, len(targets))):
                        target = min(targets, key=lambda e: e["pos"].distance_to(previous))
                        target_pos = target["pos"].copy()
                        if hop > 0 and target_pos.distance_to(previous) > 170:
                            break
                        xt["chain_arcs"].append({"a": previous.copy(), "b": target_pos.copy(),
                                                 "life": 12, "max": 12, "seed": random.randint(0, 2**30)})
                        rings.append({"pos": target_pos, "r": 34, "life": 10, "max": 10,
                                      "color": (175, 145, 255)})
                        soul_damage = (projectile_damage * (1.0 + 0.1 * soul_level)
                                       if hop == 0 else projectile_damage * 0.55)
                        if "영혼 폭주" in skill_evolutions:
                            soul_damage *= 1.0 + min(0.75, combo * 0.015)
                        feature_damage("영혼 사슬", target, soul_damage, quiet=True)
                        spawn_burst(target_pos, (190, 165, 255), 5)
                        targets.remove(target)
                        previous = target_pos
                    snd_zap.play()

        rl = skill_levels.get("재생", 0)
        if rl:
            xt["regen"] += 1
            if xt["regen"] >= 1150 - 150 * rl:
                xt["regen"] = 0
                if player_hp < player_max_hp:
                    player_hp += 1
                    floaters.append({"pos": player_pos + pygame.Vector2(0, -26), "text": "+HP",
                                     "color": (120, 255, 140), "life": 40})
            # --- 새 스킬: 별빛 난사 / 독 구름 / 시간 정지 ---
        stl = skill_levels.get("별빛 난사", 0)
        if stl:
            xt["star"] += 1
            if xt["star"] >= 200 - 15 * stl and enemies:
                xt["star"] = 0
                # 사방 발사는 최대 9발로 제한해 투사체 수가 과도하게 늘지 않게 합니다.
                n_star = 4 + stl
                base_a = random.uniform(0, 360)
                for i in range(n_star):
                    projectiles.append({"pos": player_pos.copy(),
                                        "vel": pygame.Vector2(projectile_speed, 0).rotate(base_a + 360 * i / n_star),
                                        "pierce": 1, "hit": set(), "dead": False,
                                        "dmg": max(1, int(projectile_damage * 0.65 + 0.5))})
                rings.append({"pos": player_pos.copy(), "r": 60, "life": 12, "max": 12, "color": (255, 235, 130)})
                snd_shoot.play()
        cdl = skill_levels.get("독 구름", 0)
        if cdl:
            xt["cloud"] += 1
            if xt["cloud"] >= 100:
                xt["cloud"] = 0
                cloud_radius = 38 + 6 * cdl
                if "서리독 병" in run_relics:
                    cloud_radius *= 1.2
                xt["clouds"].append({"pos": player_pos.copy(), "life": 220 + 20 * cdl, "r": cloud_radius})
            for c in xt["clouds"]:
                c["life"] -= 1
                for o in enemies:
                    dist_to_cloud = o["pos"].distance_to(c["pos"])
                    hit_radius = c["r"] + enemy_types[o["kind"]]["radius"]
                    if dist_to_cloud < hit_radius and c["life"] % 30 == 0:
                        # 중첩 구름의 지속 피해는 무기 피해의 20~32.5%로 낮춰 군집 적 상대 폭주를 막습니다.
                        feature_damage("독 구름", o, max(1, int(projectile_damage * (0.20 + 0.025 * cdl))), quiet=True)
                    if synergy_active("빙독 지대") and dist_to_cloud < hit_radius + 12:
                        slow_duration = 45 + 5 * skill_levels.get("냉기", 0)
                        if "서리독 병" in run_relics:
                            slow_duration += 15
                        o["slow"] = max(o.get("slow", 0), slow_duration)
            xt["clouds"] = [c for c in xt["clouds"] if c["life"] > 0]
        tml = skill_levels.get("시간 정지", 0)
        if tml:
            xt["time"] += 1
            if xt["time"] >= 960 - 100 * tml:
                xt["time"] = 0
                xt["freeze"] = 45 + 15 * tml
                rings.append({"pos": player_pos.copy(), "r": 420, "life": 18, "max": 18, "color": (140, 200, 255)})
                snd_level.play()
        if xt["freeze"] > 0:
            xt["freeze"] -= 1
        # --- 회전 칼날과 적의 충돌 ---
        for bpos, _ang in get_blade_positions():
            for e in enemies:
                if e["hp"] <= 0 or e["blade_cd"] > 0:
                    continue
                r = enemy_types[e["kind"]]["radius"]
                if bpos.distance_to(e["pos"]) < blade_radius + r:
                    # 칼날 약화: 데미지는 투사체의 절반(올림), 같은 적은 0.75초에 한 번만
                    feature_damage("회전 칼날", e, max(1, (projectile_damage + 1) // 2))
                    e["blade_cd"] = 45

        # --- 죽은 적 처리: 파편 + 구슬 + 드랍 (보스는 보상이 커요) ---
        spawned = []
        alive = []
        for e in enemies:
            if e["hp"] <= 0:
                kills += 1
                if not e.get("boss") and e.get("slow", 0) > 0:
                    spawn_evolved_poison_cloud(e["pos"])
                dbl = skill_levels.get("폭발탄", 0)
                if dbl and random.random() < 0.10 + 0.04 * dbl and len(rings) < 40:
                    blast_r = 56 + 8 * dbl
                    rings.append({"pos": e["pos"].copy(), "r": blast_r, "life": 12, "max": 12, "color": (255, 120, 170)})
                    spawn_burst(e["pos"], (255, 120, 170), 6)
                    for o in enemies:
                        if o is not e and o["hp"] > 0 and o["pos"].distance_to(e["pos"]) < blast_r + enemy_types[o["kind"]]["radius"]:
                            feature_damage("폭발탄", o, max(1, projectile_damage // 2 + dbl), quiet=True)
                mult = 3 if e.get("elite") else 1  # 장비 보상과 함께 주는 골드 배수
                run_gold += max(1, round(GOLD_VALUE.get(e["kind"], 1) * gold_mult)) * mult
                combo += 1  # 연속 처치 콤보
                combo_timer = 150
                best_combo = max(best_combo, combo)
                if combo % 25 == 0:  # 25콤보마다 보너스 골드
                    bonus = 5 * (combo // 25)
                    run_gold += bonus
                    floaters.append({"pos": player_pos + pygame.Vector2(0, -44), "text": f"COMBO {combo}!  +{bonus}G",
                                     "color": (255, 200, 80), "life": 60})
                if heal_every:  # 흡혈: 일정 수를 잡을 때마다 체력 1 회복
                    heal_progress += 1
                    if heal_progress >= heal_every:
                        heal_progress = 0
                        if player_hp < player_max_hp:
                            player_hp += 1
                            floaters.append({"pos": player_pos + pygame.Vector2(0, -26), "text": "+HP",
                                             "color": (120, 255, 140), "life": 40})
                if e.get("boss"):
                    run_bosses += 1
                    for _ in range(12 if e["kind"] == "orc" else 30):
                        gems.append(e["pos"] + pygame.Vector2(random.randint(-60, 60), random.randint(-60, 60)))
                    spawn_burst(e["pos"], enemy_types[e["kind"]]["color"], 40)
                    rings.append({"pos": e["pos"].copy(), "r": 150, "life": 14, "max": 14,
                                  "color": enemy_types[e["kind"]]["color"]})
                    player_hp = min(player_max_hp, player_hp + 1)  # 보스를 잡으면 체력 1 회복
                    shake = 14
                    banner_text = f"{BOSS_NAMES[e['kind']]} 처치!"
                    banner_timer = 120
                    banner_color = (255, 230, 120)
                    banner_blink = False
                    # 보상 상자: 화면 안쪽에 떨어뜨려요
                    chests.append(pygame.Vector2(max(40, min(WIDTH - 40, e["pos"].x)),
                                                 max(120, min(HEIGHT - 40, e["pos"].y))))
                    if e["kind"] == "dragon":
                        fires = []  # 드래곤이 쓰러지면 불도 꺼져요
                    if e.get("final") and cur_stage > 0:
                        stage_clear_pending = True  # 스테이지의 마지막 보스를 잡았어요!
                else:
                    gems.append(e["pos"].copy())
                    if e.get("elite"):  # 엘리트: 구슬을 더 주고 체력 하트가 자주 나와요
                        run_elites += 1
                        for _ in range(4):
                            gems.append(e["pos"] + pygame.Vector2(random.randint(-24, 24), random.randint(-24, 24)))
                        gear_pool = [wid for wid in ELITE_GEAR_IDS if wid not in weapon_stars]
                        if not gear_pool:
                            gear_pool = list(ELITE_GEAR_IDS)
                        drops.append({"pos": e["pos"].copy(), "kind": "elite_gear", "item": random.choice(gear_pool), "life": 600})
                        if can_offer_run_relic():
                            run_relic_offer_count += 1
                            drops.append({"pos": e["pos"] + pygame.Vector2(-18, -8),
                                          "kind": "run_relic", "life": 900})
                        if random.random() < 0.3:
                            drops.append({"pos": e["pos"].copy(), "kind": "heart", "life": 600})
                        floaters.append({"pos": e["pos"] + pygame.Vector2(0, -28), "text": "ELITE!",
                                         "color": (255, 210, 80), "life": 45})
                        spawn_burst(e["pos"], (255, 210, 80), 12)
                    elif random.random() < 0.03 + 0.02 * skill_levels.get("행운", 0):                
                        drops.append({"pos": e["pos"].copy(),
                                      "kind": random.choice(["heart", "magnet", "bomb"]), "life": 600})
                    spawn_burst(e["pos"], enemy_types[e["kind"]]["color"])
                    if e["kind"] == "jelly":
                        for _ in range(2):
                            off = pygame.Vector2(14, 0).rotate(random.uniform(0, 360))
                            spawned.append(make_enemy("mini", e["pos"] + off))
                    elif e["kind"] == "split_slime":
                        for _ in range(2):
                            off = pygame.Vector2(18, 0).rotate(random.uniform(0, 360))
                            spawned.append(make_enemy("mini", e["pos"] + off))
            else:
                alive.append(e)
        enemies = alive
        enemies.extend(spawned)

        # --- 스테이지 클리어: 마지막 보스가 쓰러졌어요 ---
        if stage_clear_pending:
            stage_clear_pending = False
            end_game(True)

        # --- 구슬 줍기: 범위 안에 들어오면 날아와서 붙어요 (경험 증가 카드 반영) ---
        xp_gain = 1 + 0.25 * xp_level + xp_bonus
        remaining = []
        for g in gems:
            d = g.distance_to(player_pos)
            if d < player_radius + 6:
                xp += xp_gain
                feature_record_event("gems", 1)
            else:
                if d < pickup_range:
                    g += (player_pos - g).normalize() * 7
                remaining.append(g)
        gems = remaining

        # --- 드랍 아이템: 닿으면 효과, 10초 지나면 사라져요 ---
        for d in drops:
            d["life"] -= 1
            if d["pos"].distance_to(player_pos) < player_radius + 12:
                d["life"] = 0
                if d["kind"] == "elite_gear":
                    wid = d["item"]
                    feature_discovered_items.add(wid)
                    if wid in weapon_stars:
                        if weapon_stars[wid] < MAX_STAR:
                            weapon_stars[wid] += 1
                            reward_text = f"{WEAPONS[wid]['name']} 강화  +{weapon_stars[wid]}성"
                        else:
                            run_gold += 150
                            reward_text = "정예 장비 최대 강화  +150G"
                    else:
                        weapon_stars[wid] = 1
                        reward_text = f"정예 장비 획득  {WEAPONS[wid]['name']}"
                    save_game()
                    floaters.append({"pos": player_pos + pygame.Vector2(0, -32), "text": reward_text,
                                     "color": (255, 220, 110), "life": 80})
                    snd_level.play()
                elif d["kind"] == "heart":
                    player_hp = min(player_max_hp, player_hp + 1)
                    floaters.append({"pos": player_pos + pygame.Vector2(0, -26), "text": "+HP",
                                     "color": (120, 255, 140), "life": 40})
                elif d["kind"] == "magnet":
                    xp += len(gems) * xp_gain  # 화면의 구슬을 전부 흡수
                    gems = []
                else:
                    for e in enemies:
                        if not e.get("boss"):
                            damage_enemy(e, 99)
                    rings.append({"pos": player_pos.copy(), "r": 420, "life": 14, "max": 14,
                                  "color": (255, 170, 70)})
                    add_shake(10)
        drops = [d for d in drops if d["life"] > 0]

        # --- 레벨업: 더 올릴 수 없는 카드는 빼고 3장을 뽑아요 ---
        if xp >= xp_to_next and not game_over:
            xp -= xp_to_next
            level += 1
            xp_to_next += 3
            available = available_upgrades()
            if available:
                choices = choose_upgrade_cards(available, 3)
                state = "level_up"
                level_up_anim = 0
                chest_mode = False
                snd_level.play()

        # --- 보상 상자: 닿으면 업그레이드 카드 3장 ---
        if state == "playing" and not game_over:
            for c in chests[:]:
                if c.distance_to(player_pos) < player_radius + 22:
                    chests.remove(c)
                    available = available_upgrades()
                    if available:
                        choices = choose_upgrade_cards(available, 3)
                        chest_mode = True
                        state = "level_up"
                        level_up_anim = 0
                        snd_level.play()
                    break

        # 확장 공격 스킬은 적 이동·충돌 계산 전에 갱신됩니다.
        feature_update_added_skills()

        # --- 적 이동 + 플레이어와 닿으면 체력 감소 (보스는 자기만의 행동을 해요) ---
        for e in enemies:
            t = enemy_types[e["kind"]]
            _enemy_shot_start = len(enemy_shots)
            if e.get("boss"):
                if xt["freeze"] <= 0 and e.get("feature_frozen", 0) <= 0:
                    update_boss(e)  # 보스도 빙결에 잠깐 멈추지만 면역처럼 오래 묶이지는 않아요.
            elif xt["freeze"] <= 0 and e.get("feature_frozen", 0) <= 0:  # 시간 정지/빙결 중엔 일반 적이 멈춰요
                speed = min(enemy_speed * t["speed"], 3.6)
                if e.get("slow", 0) > 0:
                    e["slow"] -= 1
                    speed *= frost_factor(frost_level)
                if e.get("feature_weaken", 0) > 0:
                    speed *= 0.75
                to_player = player_pos - e["pos"]
                dist = to_player.length()
                if dist > 0:
                    to_player /= dist
                    if e["kind"] in SHOOTERS:
                        update_mage(e, to_player, dist, speed)
                    elif e["kind"] in CHARGERS:
                        update_boar(e, to_player, dist, speed)
                    elif e["kind"] in FLYERS:
                        update_bat(e, to_player, dist, speed)
                    else:
                        e["pos"] += to_player * speed
            # 이번 적의 행동으로 새로 발사된 탄환에 공격자 등급을 기록합니다.
            _enemy_shot_damage = enemy_attack_damage(e)
            for _enemy_shot in enemy_shots[_enemy_shot_start:]:
                if isinstance(_enemy_shot, dict):
                    _enemy_shot["damage"] = _enemy_shot_damage
            if e.get("burn", 0) > 0:  # 불꽃검에 타는 중: 0.5초마다 피해
                e["burn"] -= 1
                if e["burn"] % 30 == 0:
                    damage_enemy(e, e.get("burn_dmg", 1), quiet=True)
                    spawn_burst(e["pos"], (255, 150, 50), 2)
            if e["flash"] > 0:
                e["flash"] -= 1
            if e["blade_cd"] > 0:
                e["blade_cd"] -= 1
            if e["pos"].distance_to(player_pos) < t["radius"] + player_radius - 2:
                # 공격 등급별 피해는 상태 이상과 관계없이 2 / 3 / 4로 고정합니다.
                hurt_player(enemy_attack_damage(e))

        # --- 바닥 위험 구역: 일반 2, 엘리트 3, 보스 4 피해 ---
        for f in fires:
            f["life"] -= 1
            if f["pos"].distance_to(player_pos) < 18 + player_radius:
                _fire_damage = 4 if f.get("boss") or f.get("mini_boss") else 3 if f.get("elite") else 2
                hurt_player(_fire_damage)
        fires = [f for f in fires if f["life"] > 0]
        # --- 마법사 구체 / 골렘 파편: 맞으면 피해, 회전 칼날로 막을 수 있어요 ---
        for s in enemy_shots:
            s["pos"] += s["vel"]
            s["life"] -= 1
            if s["pos"].distance_to(player_pos) < player_radius + 6:
                s["life"] = 0
                _shot_damage = s.get("damage")
                if not isinstance(_shot_damage, (int, float)):
                    _shot_damage = 4 if s.get("boss") or s.get("mini_boss") else 3 if s.get("elite") else 2
                hurt_player(_shot_damage)
            else:
                for bpos, _a in get_blade_positions():
                    if bpos.distance_to(s["pos"]) < blade_radius + 7:
                        s["life"] = 0
                        spawn_burst(s["pos"], (190, 120, 255), 4)
                        break
        enemy_shots = [s for s in enemy_shots if s["life"] > 0
                       and -20 <= s["pos"].x <= WIDTH + 20 and -20 <= s["pos"].y <= HEIGHT + 20]
        # --- 파편 / 데미지 숫자 / 번개·고리·잔상 효과 움직이기 ---
        for p in particles:
            p["pos"] += p["vel"]
            p["vel"] *= 0.92
            p["life"] -= 1
        particles = [p for p in particles if p["life"] > 0]
        for f in floaters:
            f["pos"].y -= 0.8
            f["life"] -= 1
        floaters = [f for f in floaters if f["life"] > 0]
        for fl in flames:  # 불꽃검이 지나간 자리에 불똥이 튀어요
            fk = 1 - fl["life"] / fl["max"]
            edge = player_pos + pygame.Vector2(fl["reach"] * random.uniform(0.6, 1.0), 0).rotate(
                fl["ang"] - fl["half"] + 2 * fl["half"] * min(1.0, fk * 1.5))
            spawn_burst(edge, random.choice([(255, 150, 40), (255, 210, 90)]), 1)
        for lst in (bolts, rings, ghosts, flames, xt["chain_arcs"]):
            for fx in lst:
                fx["life"] -= 1
            lst[:] = [fx for fx in lst if fx["life"] > 0]

    # ========================================================
    # 그리기
    # ========================================================
    if state == "title":
        draw_title()
    elif state == "features":
        draw_features_screen()
    elif state == "stage_select":
        draw_stage_select()
    elif state == "achv":
        draw_achv_screen()
    elif state == "upgrade":
        draw_upgrade_screen()
    elif state == "shop":
        draw_shop_screen()
    else:
        if (state == "playing" and not game_over and altar_pos is not None
                and not altar_used and player_pos.distance_to(altar_pos) <= player_radius + 26):
            state = "altar_choice"
        draw_world()
        ox, oy = 0, 0
        if shake > 0 and feature_settings.get("screen_shake", True):
            amp = max(1, shake // 3)
            ox, oy = random.randint(-amp, amp), random.randint(-amp, amp)
        screen.fill((0, 0, 0))
        screen.blit(world, (ox, oy))  # 월드만 흔들고, 아래 HUD는 가만히 있어요

        if hurt_flash > 0:
            flash_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_overlay.fill((255, 40, 40, hurt_flash * 12))
            screen.blit(flash_overlay, (0, 0))

        # 체력이 1칸 남으면 화면 가장자리가 붉게 두근거려요
        if player_hp == 1 and not game_over:
            low_hp_vig.set_alpha(int(150 + 100 * math.sin(frame_tick * 0.12)))
            screen.blit(low_hp_vig, (0, 0))

        draw_hud()

        if state == "altar_choice":
            draw_altar_choice()
        elif state == "level_up":
            draw_level_up()
        elif state == "paused":
            draw_pause()
        if game_over:
            draw_game_over()

    pygame.display.flip()
    clock.tick(60)

# 마지막 종료 시점에도 임무 진행도와 설정을 저장합니다.
try:
    save_game()
except Exception:
    pass
pygame.quit()
