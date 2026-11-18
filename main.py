import asyncio
import pygame
import random
import math
import sys
import json
import os

# ============================================================
# SPACE SHURIKEN
# Dieu khien:
# Chuot       : Di chuyen
# Chuot trai  : Ban dan
# Chuot phai  : Su dung ten lua
# P           : Tam dung / choi tiep
# ESC         : Thoat (hoac ve menu khi dang tam dung)
# ============================================================

pygame.init()

W, H = 480, 720
FPS = 60

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("SPACE SHURIKEN")
clock = pygame.time.Clock()

# ==================== MAU SAC ====================

WHITE = (240, 245, 255)
BLUE = (35, 210, 255)
LIGHT_BLUE = (140, 245, 255)
RED = (255, 55, 85)
ORANGE = (255, 145, 65)
YELLOW = (255, 220, 80)
DARK = (4, 8, 25)
PURPLE = (130, 65, 170)

font_s = pygame.font.SysFont("consolas", 13, bold=True)
font_m = pygame.font.SysFont("consolas", 20, bold=True)
font_l = pygame.font.SysFont("consolas", 36, bold=True)


def clamp(v, low, high):
    return max(low, min(high, v))


def draw_text(msg, x, y, font=font_s, color=WHITE, center=False):
    img = font.render(str(msg), True, color)
    rect = img.get_rect()

    if center:
        rect.center = (int(x), int(y))
    else:
        rect.topleft = (int(x), int(y))

    screen.blit(img, rect)


def draw_bar(x, y, w, h, ratio, color):
    pygame.draw.rect(screen, (25, 35, 60), (x, y, w, h))
    pygame.draw.rect(
        screen, color,
        (x, y, int(w * clamp(ratio, 0, 1)), h)
    )
    pygame.draw.rect(screen, WHITE, (x, y, w, h), 1)


def draw_button(label, rect, selected=False, color=BLUE):
    mouse = pygame.mouse.get_pos()
    hovered = rect.collidepoint(mouse)
    fill = (18, 55, 92) if hovered else (8, 28, 58)
    if selected:
        fill = (18, 75, 105)
    border = LIGHT_BLUE if hovered or selected else color
    pygame.draw.rect(screen, fill, rect, border_radius=9)
    pygame.draw.rect(screen, border, rect, 2, border_radius=9)
    draw_text(label, rect.centerx, rect.centery, font_m,
              YELLOW if selected else WHITE, True)


# ==================== SAO NEN ====================

class Star:
    def __init__(self):
        self.x = random.randrange(W)
        self.y = random.randrange(H)
        self.speed = random.uniform(15, 65)
        self.radius = random.choice([1, 1, 1, 2])

    def update(self, dt):
        self.y += self.speed * dt

        if self.y > H:
            self.y = -5
            self.x = random.randrange(W)

    def draw(self):
        pygame.draw.circle(
            screen, (75, 100, 155),
            (int(self.x), int(self.y)), self.radius
        )


# ==================== HIEU UNG NO ====================

class Explosion:
    def __init__(self, x, y, size, color, duration=0.5):
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.life = duration
        self.max_life = duration

        self.particles = []

        for _ in range(max(10, int(size * 0.65))):
            a = random.random() * math.tau
            speed = random.uniform(40, 150)

            self.particles.append([
                math.cos(a) * speed,
                math.sin(a) * speed,
                random.uniform(2, 5)
            ])

    def update(self, dt):
        self.life -= dt
        return self.life > 0

    def draw(self):
        elapsed = self.max_life - self.life
        ratio = max(0, self.life / self.max_life)

        radius = int(self.size * (1-ratio))

        pygame.draw.circle(
            screen, self.color,
            (int(self.x), int(self.y)),
            max(1, radius), 2
        )

        for vx, vy, r in self.particles:
            px = int(self.x + vx * elapsed)
            py = int(self.y + vy * elapsed)

            pygame.draw.circle(
                screen, self.color,
                (px, py), max(1, int(r * ratio))
            )


# ==================== DAN ====================

class Bullet:
    def __init__(self, x, y, vx, vy, damage, friendly):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.friendly = friendly
        self.radius = 4 if friendly else 5
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

        if (
            self.x < -30 or self.x > W+30
            or self.y < -40 or self.y > H+40
        ):
            self.alive = False

    def draw(self):
        color = BLUE if self.friendly else RED

        pygame.draw.circle(
            screen, color,
            (int(self.x), int(self.y)),
            self.radius+2
        )

        pygame.draw.circle(
            screen, WHITE,
            (int(self.x), int(self.y)),
            2
        )


# ==================== NGUOI CHOI ====================

class Player:
    BULLET_COUNT = [1, 2, 3, 3, 4, 5, 6]
    SPREAD = [0, 5, 8, 17, 21, 25, 29]

    def __init__(self):
        self.x = W/2
        self.y = H-85

        self.radius = 15
        self.speed = 13

        self.lives = 5
        self.level = 1
        self.damage = 10

        self.score = 0
        self.next_life = 20000
        self.next_missile = 10000

        self.missiles = 0
        self.invulnerable = 0
        self.fire_timer = 0

    def update(self, dt, mouse_pos):
        mx, my = mouse_pos

        # Di chuyen muot theo chuot
        factor = min(1, self.speed * dt)

        self.x += (mx-self.x) * factor
        self.y += (my-self.y) * factor

        self.x = clamp(self.x, 22, W-22)
        self.y = clamp(self.y, 55, H-35)

        self.invulnerable = max(0, self.invulnerable-dt)
        self.fire_timer = max(0, self.fire_timer-dt)

    def shoot(self, bullets):
        if self.fire_timer > 0:
            return

        self.fire_timer = 0.15

        # Gioi han chi so theo cap dan cuoi cung de Power Level tang vo han
        index = min(self.level-1, len(self.BULLET_COUNT)-1)
        count = self.BULLET_COUNT[index]
        spread = self.SPREAD[index]

        for i in range(count):
            angle = 0 if count == 1 else (
                -spread + 2*spread*i/(count-1)
            )

            rad = math.radians(angle)

            bullets.append(
                Bullet(
                    self.x, self.y-18,
                    math.sin(rad)*560,
                    -560*math.cos(rad),
                    self.damage, True
                )
            )

    def add_score(self, amount):
        self.score += amount

        while self.score >= self.next_life:
            self.lives += 1
            self.next_life += 20000

        while self.score >= self.next_missile:
            self.missiles = min(5, self.missiles+1)
            self.next_missile += 10000

    def draw(self):
        if self.invulnerable > 0:
            if int(self.invulnerable*12) % 2 == 0:
                return

        x, y = int(self.x), int(self.y)

        # La chan
        if self.invulnerable > 0:
            pygame.draw.circle(
                screen, LIGHT_BLUE, (x,y), 29, 2
            )

        # Than may bay
        pygame.draw.polygon(
            screen, BLUE,
            [
                (x,y-25),
                (x-18,y+17),
                (x,y+9),
                (x+18,y+17)
            ]
        )

        pygame.draw.polygon(
            screen, (5,35,80),
            [
                (x,y-15),
                (x-6,y+9),
                (x+6,y+9)
            ]
        )

        pygame.draw.circle(screen, WHITE, (x,y-5), 3)


# ==================== QUAI ====================

class Enemy:
    DATA = {
        "basic": (13, 30, 55, 100, RED),
        "medium": (19, 90, 38, 200, ORANGE),

        # Quái bay ngang đã được giảm tốc độ
        "sweeper": (20, 145, 75, 300, (255,170,65)),

        # Quái tím giảm HP từ 220 xuống 195
        "diver": (21, 195, 70, 320, PURPLE),

        "mini": (30, 450, 32, 500, (255,100,70)),
        "boss": (49, 4500, 0, 2000, (255,55,120))
    }

    def __init__(self, kind, hp_scale=1, x=None, y=-50,
                 chain=False, boss_family=False, direction=None,
                 hp_override=None):

        self.kind = kind
        r, hp, speed, score, color = self.DATA[kind]
        self.chain = chain
        self.boss_family = boss_family

        if chain:
            hp *= 1.55
            speed *= 1.15
            score = int(score * 1.5)

        self.radius = r

        # HP tối đa là HP ban đầu khi quái được sinh ra.
        if hp_override is not None:
            self.max_hp = max(1, int(hp_override))
        else:
            self.max_hp = max(1, int(hp*hp_scale))

        self.hp = self.max_hp
        self.speed = speed
        self.score = score
        self.color = color

        self.x = float(x if x is not None else random.randint(35,W-35))
        self.y = float(y)
        self.alive = True

        self.age = random.random()*5
        self.fire_timer = random.uniform(.8, 1.6)

        self.direction = direction if direction is not None else random.choice([-1, 1])

        self.laser_direction = random.choice([-1, 1])
        self.laser_warning = 0
        self.laser_cooldown = random.uniform(1.4, 2.2)

        # Giữ vị trí và hướng bay của quái bay ngang
        self.sweeper_respawn_count = 0

    def shoot_at_player(self, player, bullets, count, speed, spread=0):
        angle = math.atan2(player.y-self.y, player.x-self.x)

        for i in range(count):
            a = angle + (i-(count-1)/2)*spread

            bullets.append(Bullet(
                self.x, self.y, math.cos(a)*speed,
                math.sin(a)*speed, 1, False
            ))

    def update(self, dt, player, bullets, lasers=None):
        self.age += dt
        self.fire_timer -= dt

        if self.kind == "basic":
            self.y += self.speed*dt

        elif self.kind == "medium":
            # Quái cam di chuyển ngang NGAY TỪ KHI XUẤT HIỆN
            self.y += self.speed*dt
            self.x += math.sin(self.age*1.5)*25*dt
            self.x += (1 if player.x > self.x else -1)*12*dt
            self.x = clamp(self.x, 25, W-25)

        elif self.kind == "sweeper":
            # Quái bay ngang chậm hơn.
            self.x += self.direction*self.speed*dt

            # Giữ độ cao, không tiếp tục rơi xuống dưới.
            # Khi ra khỏi màn hình sẽ xuất hiện lại phía đối diện.
            if self.x < -40 or self.x > W+40:
                self.sweeper_respawn_count += 1

                self.direction = random.choice([-1, 1])

                if self.direction == 1:
                    self.x = -35
                else:
                    self.x = W+35

                self.y = random.randint(35, H//2)

                # Không thay đổi self.hp hoặc self.max_hp.
                # Quái trở lại với lượng máu còn lại trước đó.

        elif self.kind == "diver":
            # Quái tím luôn đi từ phía trên xuống dưới.
            self.y += self.speed*dt

            # Không tự ý đổi hướng sang trái/phải.
            self.laser_cooldown -= dt

            if (
                self.laser_cooldown <= 0
                and self.y > 70
                and lasers is not None
            ):
                # Chọn phía có khoảng trống rộng hơn.
                space_left = self.x
                space_right = W-self.x

                if space_left > space_right:
                    self.laser_direction = -1
                else:
                    self.laser_direction = 1

                lasers.append(
                    HorizontalEnemyLaser(self, self.laser_direction)
                )

                self.laser_cooldown = random.uniform(2.8, 3.5)

        elif self.kind == "mini":
            target_y = 125 + 25*math.sin(self.age)
            self.y += clamp(target_y-self.y, -self.speed*dt, self.speed*dt)
            self.x += (player.x-self.x)*min(1,0.2*dt)
            self.x = clamp(self.x,45,W-45)

        elif self.kind == "boss":
            self.y += clamp(115-self.y,-70*dt,70*dt)
            self.x = W/2 + math.sin(self.age*.6)*110

        # ==================== BAN DAN ====================

        if self.fire_timer <= 0 and self.y > 15:

            if self.kind == "basic":
                self.shoot_at_player(player,bullets,1,125)
                self.fire_timer = random.uniform(1.9,2.5)

            elif self.kind == "medium":
                # Quái cam bắn 2 viên đạn
                self.shoot_at_player(player,bullets,2,135,.15)
                self.fire_timer = random.uniform(1.7,2.3)

            elif self.kind == "sweeper":
                # Quái bay ngang chỉ bắn 2 viên đạn.
                # Giảm tần suất bắn so với trước.
                self.shoot_at_player(player,bullets,2,165,.32)
                self.fire_timer = random.uniform(1.3,1.65)

            elif self.kind == "mini":
                self.shoot_at_player(player,bullets,3,155,.23)
                self.fire_timer = 1.35

            elif self.kind == "boss":
                self.shoot_at_player(player,bullets,5,175,.30)
                self.fire_timer = 1.15

            # Quái tím không bắn đạn.
            # Nó chỉ sử dụng laser ngang.

        if self.kind in ("basic","medium","diver") and self.y > H+50:
            self.alive = False

        if self.kind == "sweeper" and self.y > H+50:
            self.alive = False

    def draw(self):
        x,y,r = int(self.x),int(self.y),self.radius

        if self.kind == "boss":
            pygame.draw.polygon(screen,(100,20,70),[
                (x,y-50),(x-55,y-8),(x-40,y+35),
                (x,y+22),(x+40,y+35),(x+55,y-8)])
            pygame.draw.polygon(screen,self.color,[
                (x,y-40),(x-40,y-7),(x-29,y+25),
                (x,y+14),(x+29,y+25),(x+40,y-7)])
            pygame.draw.circle(screen,YELLOW,(x,y-5),8)
            draw_text("DREADNOUGHT",W//2,43,font_s,(255,150,180),True)
            draw_bar(160,60,160,8,self.hp/self.max_hp,RED)

        elif self.kind == "mini":
            pygame.draw.polygon(screen,self.color,[
                (x,y-30),(x-30,y+18),(x,y+7),(x+30,y+18)])
            pygame.draw.circle(screen,YELLOW,(x,y-4),5)
            draw_bar(x-r,y+r+7,r*2,5,self.hp/self.max_hp,RED)

        elif self.kind in ("sweeper", "diver"):
            # Thiet ke rieng cho hai loai quai co vua moi
            if self.kind == "sweeper":
                points = [(x-25,y-10),(x-10,y-19),(x+24,y-8),
                          (x+15,y+12),(x-18,y+12)]
                pygame.draw.polygon(screen,(115,55,20),points)
                pygame.draw.polygon(screen,self.color,
                    [(x-19,y-8),(x-7,y-14),(x+18,y-6),
                     (x+10,y+8),(x-14,y+8)])
                pygame.draw.circle(screen,YELLOW,(x,y),4)
                pygame.draw.line(screen,WHITE,(x-18,y+13),(x+18,y+13),2)
            else:
                nose_x = x + self.direction*27
                pygame.draw.polygon(screen,(55,35,100),[
                    (nose_x,y),(x-self.direction*17,y-17),
                    (x-self.direction*12,y+17)])
                pygame.draw.polygon(screen,self.color,[
                    (nose_x,y),(x-self.direction*12,y-11),
                    (x-self.direction*9,y+11)])
                pygame.draw.circle(screen,LIGHT_BLUE,(x,y),4)

            draw_bar(x-r,y+r+7,r*2,5,self.hp/self.max_hp,self.color)

        else:
            pygame.draw.polygon(screen,self.color,[
                (x,y-r),(x-r,y+r//2),(x,y+5),(x+r,y+r//2)])
            pygame.draw.circle(screen,WHITE,(x,y-2),3)

            if self.kind == "medium":
                draw_bar(x-r,y+r+7,r*2,5,self.hp/self.max_hp,ORANGE)


class HorizontalEnemyLaser:
    """Laser ngang co 0,5 giay canh bao truoc khi kich hoat."""

    def __init__(self, enemy, direction):
        self.enemy = enemy
        self.direction = direction
        self.warning_time = 0.5
        self.fire_time = 0.30
        self.elapsed = 0

    def update(self, dt):
        self.elapsed += dt
        return self.elapsed < self.warning_time + self.fire_time

    def hits(self, player):
        if not self.enemy.alive or self.elapsed < self.warning_time:
            return False

        if self.elapsed >= self.warning_time + self.fire_time:
            return False

        on_firing_side = (
            player.x <= self.enemy.x if self.direction < 0
            else player.x >= self.enemy.x
        )

        return on_firing_side and abs(player.y-self.enemy.y) < 12

    def draw(self):
        if not self.enemy.alive:
            return

        y = int(self.enemy.y)

        if self.elapsed < self.warning_time:
            # Duong canh bao nhap nhay trong nua giay
            if int(self.elapsed*18) % 2 == 0:
                end_x = 0 if self.direction < 0 else W

                pygame.draw.line(screen,(255,150,90),
                    (int(self.enemy.x),y),(end_x,y),2)

                pygame.draw.circle(screen,YELLOW,
                    (int(self.enemy.x),y),self.enemy.radius+8,2)

        elif self.elapsed < self.warning_time+self.fire_time:
            end_x = 0 if self.direction < 0 else W

            pygame.draw.line(screen,RED,
                (int(self.enemy.x),y),(end_x,y),9)

            pygame.draw.line(screen,WHITE,
                (int(self.enemy.x),y),(end_x,y),3)


# ==================== VAT PHAM ====================

class PowerUp:
    def __init__(self,x,y):
        self.x = x
        self.y = y
        self.alive = True
        self.speed = 65
        self.angle = 0

    def update(self,dt):
        self.y += self.speed*dt
        self.angle += dt*4

        if self.y > H+20:
            self.alive = False

    def draw(self):
        x,y = int(self.x),int(self.y)

        pygame.draw.circle(screen,BLUE,(x,y),14,2)
        pygame.draw.circle(screen,LIGHT_BLUE,(x,y),5)

        draw_text("P",x,y-7,font_s,WHITE,True)


# ==================== TEN LUA ====================

class Missile:
    def __init__(self,x,y):
        self.x = x
        self.y = y
        self.life = .55

    def update(self,dt):
        self.life -= dt
        self.y -= 220*dt
        return self.life > 0

    def draw(self):
        x,y = int(self.x),int(self.y)

        pygame.draw.polygon(
            screen,LIGHT_BLUE,
            [(x,y-14),(x-8,y+9),(x+8,y+9)]
        )

        pygame.draw.line(
            screen,BLUE,(x,y+9),(x,y+22),4
        )

        pygame.draw.circle(screen,BLUE,(x,y+20),5)


# ==================== LASER BOSS ====================

class BossLaser:
    def __init__(self,boss):
        self.boss = boss
        self.elapsed = 0
        self.angle = random.random()*math.tau

        # Trinh tu:
        # Canh bao -> ban 5 tia -> nghi -> xoay 5 tia cham hon
        # -> nghi -> tia don quet ngang.
        self.warning_time = 1.0
        self.fire_time = 0.35
        self.delay_time = 0.25

        # Tang thoi gian quay de chùm 5 tia quay cham hon.
        self.rotate_time = 1.75

        # Delay sau khi quay xong.
        self.after_rotate_delay = 0.5

        # Tia don quet ngang giu toc do cu.
        self.single_sweep_time = 1.75

        self.total_time = (
            self.warning_time
            + self.fire_time
            + self.delay_time
            + self.rotate_time
            + self.after_rotate_delay
            + self.single_sweep_time
        )

        self.rotation = math.radians(random.choice([-35,35]))
        self.sweep_angle = math.radians(55)

    def update(self,dt):
        self.elapsed += dt
        return self.elapsed < self.total_time

    def phase(self):
        if self.elapsed < self.warning_time:
            return "warning"

        if self.elapsed < self.warning_time+self.fire_time:
            return "fire"

        if self.elapsed < self.warning_time+self.fire_time+self.delay_time:
            return "delay"

        rotate_start = (
            self.warning_time+self.fire_time+self.delay_time
        )

        if self.elapsed < rotate_start+self.rotate_time:
            return "rotate"

        delay_start = rotate_start+self.rotate_time

        if self.elapsed < delay_start+self.after_rotate_delay:
            return "after_rotate_delay"

        return "single_sweep"

    def current_rotation(self):
        start = self.warning_time+self.fire_time+self.delay_time

        progress = clamp(
            (self.elapsed-start)/self.rotate_time,0,1
        )

        return self.rotation*progress

    def current_sweep_angle(self):
        start = (
            self.warning_time
            + self.fire_time
            + self.delay_time
            + self.rotate_time
            + self.after_rotate_delay
        )

        progress = clamp(
            (self.elapsed-start)/self.single_sweep_time,0,1
        )

        return self.angle-self.sweep_angle/2+self.sweep_angle*progress

    def line_hits_player(self,player,angle):
        dx = player.x-self.boss.x
        dy = player.y-self.boss.y

        ux,uy = math.cos(angle),math.sin(angle)

        along = dx*ux+dy*uy
        across = abs(dx*uy-dy*ux)

        return 0 <= along <= 700 and across < 12

    def hits(self,player):
        if not self.boss.alive:
            return False

        phase = self.phase()

        if phase == "fire":
            for i in range(5):
                if self.line_hits_player(
                    player,self.angle+i*math.tau/5
                ):
                    return True

        elif phase == "rotate":
            rotation = self.current_rotation()

            for i in range(5):
                if self.line_hits_player(
                    player,self.angle+i*math.tau/5+rotation
                ):
                    return True

        elif phase == "single_sweep":
            return self.line_hits_player(
                player,self.current_sweep_angle()
            )

        return False

    def draw(self):
        if not self.boss.alive:
            return

        phase = self.phase()

        if phase in ("warning","fire","rotate"):
            rotation = (
                self.current_rotation()
                if phase == "rotate" else 0
            )

            for i in range(5):
                a = self.angle+i*math.tau/5+rotation

                x2 = self.boss.x+math.cos(a)*700
                y2 = self.boss.y+math.sin(a)*700

                if phase == "warning":
                    for d in range(0,700,20):
                        px = self.boss.x+math.cos(a)*d
                        py = self.boss.y+math.sin(a)*d

                        pygame.draw.circle(
                            screen,(255,100,130),
                            (int(px),int(py)),2
                        )

                elif phase in ("fire","rotate"):
                    width = 5 if phase == "fire" else 6

                    pygame.draw.line(
                        screen,RED,
                        (self.boss.x,self.boss.y),
                        (x2,y2),width
                    )

        elif phase == "single_sweep":
            a = self.current_sweep_angle()

            x2 = self.boss.x+math.cos(a)*700
            y2 = self.boss.y+math.sin(a)*700

            pygame.draw.line(
                screen,RED,
                (self.boss.x,self.boss.y),
                (x2,y2),6
            )


# ==================== CAU HINH / BANG XEP HANG ====================

SCORE_FILE = "space_shuriken_scores.json"

DIFFICULTIES = {
    "DE": {"hp": 0.78, "spawn": 1.5, "group": 2, "label": "DE"},
    "TRUNG BINH": {"hp": 1.0, "spawn": 1.25, "group": 3, "label": "TRUNG BINH"},
    "KHO": {"hp": 1.25, "spawn": 1.0, "group": 4, "label": "KHO"},
}


def load_scores():
    try:
        with open(SCORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []

    except (OSError, ValueError):
        return []


def save_score(name, score, difficulty):
    scores = load_scores()

    scores.append({
        "name": name[:12],
        "score": int(score),
        "difficulty": difficulty
    })

    scores.sort(
        key=lambda x: x.get("score", 0),
        reverse=True
    )

    try:
        with open(SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                scores[:50], f,
                ensure_ascii=False, indent=2
            )

    except OSError:
        pass


# ==================== GAME ====================

class Game:
    def __init__(self, difficulty="TRUNG BINH", player_name="PLAYER"):
        self.difficulty = difficulty
        self.player_name = player_name or "PLAYER"

        self.stars = [Star() for _ in range(90)]
        self.player = Player()

        self.player_bullets = []
        self.enemy_bullets = []
        self.enemies = []
        self.items = []
        self.effects = []
        self.lasers = []
        self.missiles = []

        self.wave = 1
        self.wave_time = 30

        self.wave_banner = 0
        self.spawn_timer = 0.8
        self.special_spawned = False
        self.support_timer = 1.8
        self.sky_drop_timer = 30
        self.powerup_cooldown = 0

        # Quái tím xuất hiện theo chu kỳ cố định.
        self.diver_spawn_timer = 8.0

        self.hp_scale = DIFFICULTIES[self.difficulty]["hp"]
        self.laser_timer = 4

        self.shockwave = 0
        self.state = "menu"
        self.score_saved = False

        self.menu_buttons = {}
        self.over_buttons = {}
        self.pause_buttons = {}

        self.leader_button = pygame.Rect(145, 565, 190, 42)

    def start(self):
        difficulty, name = self.difficulty, self.player_name
        self.__init__(difficulty, name)
        self.state = "playing"

    # HP boss theo wave, dùng để tính HP tối đa của mini boss.
    def calculate_boss_hp(self, boss_wave):
        scale = (
            self.hp_scale
            * (1 + max(0,boss_wave-1)*0.035)
        )

        return max(1,int(4500*scale))

    def calculate_mini_hp(self, next_boss_wave):
        # HP mini boss = 50% HP tối đa boss ở wave kế tiếp.
        return max(
            1,
            int(self.calculate_boss_hp(next_boss_wave)*0.50)
        )

    def spawn_enemy(
        self,kind=None,x=None,y=-50,chain=False,
        boss_family=False,direction=None,hp_override=None
    ):

        if kind is None:
            # Giảm thêm 10% xác suất quái bay ngang so với mức hiện tại.
            # Quái tím không nằm trong nhóm sinh ngẫu nhiên.
            chance_quai_moi = min(
                (.24+self.wave*.012)*0.5*0.7,
                .48
            )

            if random.random() < chance_quai_moi:
                kind = "sweeper"

            elif random.random() < .20:
                kind = "medium"

            else:
                kind = "basic"

        scale = (
            self.hp_scale
            * (1 + max(0,self.wave-1)*0.035)
        )

        if chain:
            scale *= 1.12

        if kind == "boss":
            enemy = Enemy(
                "boss",scale,W/2,-75,
                chain=chain,
                boss_family=boss_family,
                hp_override=hp_override
            )

        elif kind == "mini":
            if hp_override is None:
                next_boss_wave = (
                    (self.wave//10+1)*10
                    if self.wave % 10 != 0
                    else self.wave+10
                )

                hp_override = self.calculate_mini_hp(
                    next_boss_wave
                )

            enemy = Enemy(
                "mini",scale,
                x if x is not None else random.randint(70,W-70),
                y if y != -50 else -60,
                chain=chain,
                boss_family=boss_family,
                hp_override=hp_override
            )

        elif kind == "sweeper":
            # Quái bay ngang xuất hiện ở độ cao ngẫu nhiên
            # từ giữa màn hình trở lên.
            if x is None:
                direction = random.choice([-1,1])

                if direction == 1:
                    x = -35
                else:
                    x = W+35

                y = random.randint(35,H//2)

            enemy = Enemy(
                kind,scale,x,y,
                chain,boss_family,direction,
                hp_override
            )

        elif kind == "diver":
            # Quái tím luôn sinh từ phía trên màn hình.
            if x is None:
                x = random.randint(35,W-35)

            y = -50

            enemy = Enemy(
                kind,scale,x,y,
                chain,boss_family,direction,
                hp_override
            )

        else:
            enemy = Enemy(
                kind,scale,x,y,
                chain,boss_family,direction,
                hp_override
            )

        self.enemies.append(enemy)
        return enemy

    def try_spawn_powerup(self, x, y, chance):
        # Tat ca nguon vat pham dung chung gioi han 1 vat pham moi 60 giay
        if self.powerup_cooldown > 0:
            return

        if random.random() < chance:
            self.items.append(PowerUp(x,y))
            self.powerup_cooldown = 60

    def kill_enemy(self,e):
        if not e.alive:
            return

        e.alive = False
        self.player.add_score(e.score)

        settings = {
            "basic":(16,RED,.3),
            "medium":(24,ORANGE,.4),
            "sweeper":(28,(255,170,65),.45),
            "diver":(30,PURPLE,.45),
            "mini":(45,ORANGE,.7),
            "boss":(100,(255,80,150),1.0)
        }

        size,color,duration = settings[e.kind]

        self.effects.append(
            Explosion(e.x,e.y,size,color,duration)
        )

        chance = {
            "basic":.075,
            "medium":.10,
            "sweeper":.10,
            "diver":.10,
            "mini":.15,
            "boss":.20
        }[e.kind]

        self.try_spawn_powerup(e.x,e.y,chance)

        # Mini boss bị tiêu diệt chỉ sinh quái cam và quái bay ngang.
        if e.kind == "mini":
            family = (
                e.boss_family
                or (self.wave % 10 == 9)
            )

            self.effects.append(
                Explosion(e.x,e.y,75,(255,210,90),.65)
            )

            # Hai quái con xuất hiện ngay tại vị trí mini boss phát nổ.
            for _ in range(2):
                kind = random.choice(["medium","sweeper"])

                direction = random.choice([-1,1])

                spawn_x = e.x + random.uniform(-12,12)
                spawn_y = e.y + random.uniform(-12,12)

                self.spawn_enemy(
                    kind,
                    x=spawn_x,
                    y=spawn_y,
                    chain=True,
                    boss_family=family,
                    direction=direction
                )

        # Các quái thuộc chuỗi phát nổ tiếp tục tách ra
        # cho đến khi chỉ còn quái cơ bản.
        elif e.kind in ("medium","sweeper","diver") and e.chain:
            for i in range(4):
                offset_x = random.randint(-35,35)
                offset_y = random.randint(-25,25)

                self.spawn_enemy(
                    "basic",
                    x=clamp(e.x+offset_x,25,W-25),
                    y=e.y+offset_y,
                    chain=True,
                    boss_family=e.boss_family
                )

        # Boss từ wave 20 trở đi sinh hai mini boss khi chết.
        elif e.kind == "boss":
            # Cập nhật HP scale trước khi tính HP mini boss
            # của boss ở wave tiếp theo.
            self.hp_scale *= (
                1.22+min(.20,self.player.level*.015)
            )

            if self.wave >= 20:
                next_boss_wave = (
                    (self.wave//10+1)*10
                )

                mini_hp = self.calculate_mini_hp(
                    next_boss_wave
                )

                # Hai mini boss xuất hiện ngay tại vị trí boss phát nổ.
                self.spawn_enemy(
                    "mini",
                    x=e.x-18,
                    y=e.y,
                    chain=True,
                    boss_family=True,
                    hp_override=mini_hp
                )

                self.spawn_enemy(
                    "mini",
                    x=e.x+18,
                    y=e.y,
                    chain=True,
                    boss_family=True,
                    hp_override=mini_hp
                )

    def player_explosion_damage(self, x, y):
        # Vu no cua may bay gay sat thuong len quai o gan
        explosion_radius = 115
        explosion_damage = max(100, self.player.damage*8)

        self.effects.append(
            Explosion(x,y,explosion_radius,BLUE,.65)
        )

        for e in self.enemies[:]:
            if not e.alive:
                continue

            distance = math.hypot(e.x-x,e.y-y)

            if distance <= explosion_radius+e.radius:
                e.hp -= explosion_damage

                self.effects.append(
                    Explosion(e.x,e.y,25,ORANGE,.3)
                )

                if e.hp <= 0:
                    self.kill_enemy(e)

    def take_hit(self):
        p = self.player

        if p.invulnerable > 0 or self.state != "playing":
            return

        # May bay no ngay khi trung dan, laser hoac va cham
        self.player_explosion_damage(p.x,p.y)

        p.lives -= 1

        # Mat mang: Power Level con mot nua, lam tron xuong, toi thieu 1
        p.level = max(1,p.level//2)
        p.damage = 10+(p.level-1)*2

        if p.lives <= 0:
            self.state = "gameover"

        else:
            p.x = W/2
            p.y = H-35
            p.invulnerable = 5
            self.enemy_bullets.clear()

    def use_missile(self):
        if self.player.missiles > 0:
            self.player.missiles -= 1

            self.missiles.append(
                Missile(self.player.x,self.player.y-20)
            )

    def missile_explosion(self):
        self.shockwave = .65

        # Sóng xung kích xóa toàn bộ đạn của quái.
        self.enemy_bullets.clear()

        alive_enemies = [
            e for e in self.enemies if e.alive
        ]

        if not alive_enemies:
            return

        # Tìm quái có HP tối đa lớn nhất tại thời điểm nổ.
        strongest_enemy = max(
            alive_enemies,
            key=lambda e: e.max_hp
        )

        highest_max_hp = strongest_enemy.max_hp

        # Ưu tiên hệ số theo loại quái đặc biệt còn sống.
        has_boss = any(
            e.kind == "boss" and e.alive
            for e in alive_enemies
        )

        has_mini = any(
            e.kind == "mini" and e.alive
            for e in alive_enemies
        )

        if has_boss:
            damage_ratio = 0.10

        elif has_mini:
            damage_ratio = 0.20

        else:
            damage_ratio = 0.75

        damage = max(
            1,
            int(highest_max_hp*damage_ratio)
        )

        # Tất cả quái còn sống nhận cùng lượng sát thương.
        for e in alive_enemies:
            e.hp -= damage

            self.effects.append(
                Explosion(e.x,e.y,25,BLUE,.35)
            )

            if e.hp <= 0:
                self.kill_enemy(e)

        self.enemies = [
            e for e in self.enemies if e.alive
        ]

    def update(self,dt):
        # Khi tam dung, ca man choi va sao nen deu dung yen.
        if self.state == "paused":
            return

        for s in self.stars:
            s.update(dt)

        if self.state != "playing":
            return

        self.powerup_cooldown = max(
            0,self.powerup_cooldown-dt
        )

        self.shockwave = max(0,self.shockwave-dt)

        self.player.update(
            dt,pygame.mouse.get_pos()
        )

        # Giu chuot trai de ban
        if pygame.mouse.get_pressed()[0]:
            self.player.shoot(self.player_bullets)

        # Banner Wave chi hien thi, khong dung game va khong khoa dieu khien
        self.wave_banner = max(0, self.wave_banner-dt)

        self.wave_time -= dt
        self.spawn_timer -= dt
        self.sky_drop_timer -= dt

        # Quái tím xuất hiện theo chu kỳ, không phụ thuộc
        # vào nhóm quái sinh ngẫu nhiên.
        self.diver_spawn_timer -= dt

        if self.diver_spawn_timer <= 0:
            if self.wave_time > 0:
                self.spawn_enemy(
                    "diver",
                    x=random.randint(35,W-35),
                    y=-50
                )

            self.diver_spawn_timer = 9.0

        # Moi 60 giay co 10% co hoi vat pham roi tu tren troi
        if self.sky_drop_timer <= 0:
            self.try_spawn_powerup(
                random.randint(25,W-25),-15,0.10
            )

            self.sky_drop_timer = 60

        # Boss wave: boss va quai ho tro xuat hien den khi het thoi gian.
        # Sau do van tiep tuc goi ho tro neu con boss/chuoi boss-family.
        if self.wave % 10 == 0:

            if not self.special_spawned and self.spawn_timer <= 0:
                self.spawn_enemy(
                    "boss",
                    boss_family=True
                )

                self.special_spawned = True
                self.support_timer = 1.8

            family_alive = any(
                e.alive and e.boss_family
                for e in self.enemies
            )

            if (
                self.special_spawned
                and (self.wave_time > 0 or family_alive)
            ):
                self.support_timer -= dt

                if self.support_timer <= 0:
                    amount = random.randint(1,2)

                    for _ in range(amount):
                        self.spawn_enemy(
                            "medium" if random.random()<.30 else "basic"
                        )

                    self.support_timer = (
                        1.9*DIFFICULTIES[self.difficulty]["spawn"]
                    )

        # Wave truoc boss: hai mini boss tach nhau sang hai ben.
        elif self.wave % 10 == 9:

            if not self.special_spawned and self.spawn_timer <= 0:
                next_boss_wave = self.wave+1

                mini_hp = self.calculate_mini_hp(
                    next_boss_wave
                )

                self.spawn_enemy(
                    "mini",
                    x=105,
                    y=-60,
                    hp_override=mini_hp
                )

                self.spawn_enemy(
                    "mini",
                    x=W-105,
                    y=-60,
                    hp_override=mini_hp
                )

                self.special_spawned = True
                self.support_timer = 1.8

            if self.special_spawned and self.wave_time > 0:
                self.support_timer -= dt

                if self.support_timer <= 0:
                    amount = random.randint(1,2)

                    for _ in range(amount):
                        self.spawn_enemy(
                            "medium" if random.random()<.30 else "basic"
                        )

                    self.support_timer = (
                        1.9*DIFFICULTIES[self.difficulty]["spawn"]
                    )

        # Wave thuong: quai xuat hien cham hon
        elif self.wave_time > 0 and self.spawn_timer <= 0:
            group = DIFFICULTIES[self.difficulty]["group"]
            amount = random.randint(1, group)

            for _ in range(amount):
                self.spawn_enemy()

            interval = (
                max(0.72,1.65-self.wave*.025)
                * DIFFICULTIES[self.difficulty]["spawn"]
            )

            self.spawn_timer = interval

        # Cap nhat dan
        for b in self.player_bullets+self.enemy_bullets:
            b.update(dt)

        for e in self.enemies:
            e.update(
                dt,
                self.player,
                self.enemy_bullets,
                self.lasers
            )

        for item in self.items:
            item.update(dt)

        self.effects = [
            fx for fx in self.effects if fx.update(dt)
        ]

        self.lasers = [
            l for l in self.lasers if l.update(dt)
        ]

        self.player_bullets = [
            b for b in self.player_bullets if b.alive
        ]

        self.enemy_bullets = [
            b for b in self.enemy_bullets if b.alive
        ]

        self.items = [
            p for p in self.items if p.alive
        ]

        # Boss laser
        boss = next(
            (e for e in self.enemies if e.kind=="boss"),
            None
        )

        if boss:
            self.laser_timer -= dt

            if self.laser_timer <= 0:
                self.lasers.append(
                    BossLaser(boss)
                )

                self.laser_timer = 4.8

        else:
            self.laser_timer = 4

        # Ten lua
        for m in self.missiles[:]:
            if not m.update(dt):
                self.missiles.remove(m)
                self.missile_explosion()

        # Dan nguoi va quai
        for b in self.player_bullets:
            if not b.alive:
                continue

            for e in self.enemies:
                if (
                    e.alive
                    and math.hypot(b.x-e.x,b.y-e.y)
                    < e.radius+b.radius
                ):
                    e.hp -= b.damage
                    b.alive = False

                    if e.hp <= 0:
                        self.kill_enemy(e)

                    break

        # Dan dich va nguoi choi
        for b in self.enemy_bullets:
            if (
                b.alive
                and math.hypot(
                    b.x-self.player.x,
                    b.y-self.player.y
                ) < self.player.radius+b.radius
            ):
                b.alive = False
                self.take_hit()
                break

        # Laser boss va laser quai tím
        for l in self.lasers:
            if l.hits(self.player):
                self.take_hit()
                break

        # Va cham than may bay: may bay no ngay va vu no sat thuong quai xung quanh
        if self.player.invulnerable <= 0:
            for e in self.enemies:
                if (
                    e.alive
                    and math.hypot(
                        e.x-self.player.x,
                        e.y-self.player.y
                    ) < e.radius+self.player.radius
                ):
                    self.take_hit()
                    break

        # Nhat vat pham
        for item in self.items:
            if (
                item.alive
                and math.hypot(
                    item.x-self.player.x,
                    item.y-self.player.y
                ) < 27
            ):
                item.alive = False

                self.player.level += 1

                self.player.damage = (
                    10+(self.player.level-1)*2
                )

                self.effects.append(
                    Explosion(
                        self.player.x,self.player.y,
                        25,BLUE,.4
                    )
                )

        self.enemies = [
            e for e in self.enemies if e.alive
        ]

        self.player_bullets = [
            b for b in self.player_bullets if b.alive
        ]

        self.enemy_bullets = [
            b for b in self.enemy_bullets if b.alive
        ]

        # Hoan thanh wave:
        # Phai tieu diet tat ca quai con ton tai,
        # bao gom ca cac the he quai sinh ra tu vu no.
        family_alive = any(
            e.alive and e.boss_family
            for e in self.enemies
        )

        if (
            self.wave_time <= 0
            and not self.enemies
            and not family_alive
        ):
            self.wave += 1

            self.wave_banner = 1.8
            self.special_spawned = False
            self.spawn_timer = 0.25
            self.support_timer = 1.8
            self.wave_time = 30

            self.lasers.clear()

    # ==================== GIAO DIEN ====================

    def draw_background(self):
        screen.fill(DARK)

        pygame.draw.circle(
            screen,(10,12,38),
            (W//2,H//2),180
        )

        for s in self.stars:
            s.draw()

    def draw_hud(self):
        pygame.draw.rect(
            screen,(7,17,45),
            (8,8,135,48),border_radius=7
        )

        draw_text("SCORE",16,13,font_s,BLUE)

        draw_text(
            f"{self.player.score:07d}",
            16,29,font_m,WHITE
        )

        pygame.draw.rect(
            screen,(7,17,45),
            (W-112,8,104,48),border_radius=7
        )

        draw_text("LIFE",W-103,13,font_s,BLUE)

        draw_text(
            "♥ "*min(8,self.player.lives),
            W-103,29,font_m,RED
        )

        draw_text(
            f"MISSILE: {self.player.missiles}/5",
            12,64,font_s,YELLOW
        )

        draw_text(
            f"POWER LV.{self.player.level}",
            W-125,64,font_s,BLUE
        )

        draw_text(
            f"WAVE {self.wave:02d}",
            W//2,20,font_m,WHITE,True
        )

    def draw(self):
        self.draw_background()

        for item in self.items:
            item.draw()

        for b in self.player_bullets+self.enemy_bullets:
            b.draw()

        for e in self.enemies:
            e.draw()

        for l in self.lasers:
            l.draw()

        for m in self.missiles:
            m.draw()

        for fx in self.effects:
            fx.draw()

        self.player.draw()

        # Song xung kich ten lua
        if self.shockwave > 0:
            radius = int(
                (1-self.shockwave/.65)*520
            )

            pygame.draw.circle(
                screen,BLUE,
                (W//2,H//2),
                max(1,radius),5
            )

            pygame.draw.rect(
                screen,(20,120,255),
                (0,0,W,H),3
            )

        self.draw_hud()

        if self.wave_banner > 0 and self.state=="playing":
            draw_text(
                f"WAVE {self.wave}",
                W//2,H//2-20,
                font_l,LIGHT_BLUE,True
            )

        if self.state=="menu":
            pygame.draw.rect(
                screen,(3,8,28),
                (25,125,W-50,485),
                border_radius=18
            )

            pygame.draw.rect(
                screen,BLUE,
                (25,125,W-50,485),
                2,border_radius=18
            )

            draw_text("SPACE",W//2,165,font_l,BLUE,True)
            draw_text("WAR",W//2,205,font_l,WHITE,True)

            draw_text(
                "TEN NGUOI CHOI:",
                W//2,255,font_s,WHITE,True
            )

            draw_text(
                self.player_name + (
                    "_" if int(pygame.time.get_ticks()/400)%2==0 else ""
                ),
                W//2,280,font_m,LIGHT_BLUE,True
            )

            draw_text(
                "CHON DO KHO",
                W//2,325,font_m,YELLOW,True
            )

            self.menu_buttons = {
                "DE": pygame.Rect(48,350,112,42),
                "TRUNG BINH": pygame.Rect(174,350,132,42),
                "KHO": pygame.Rect(320,350,112,42),
                "PLAY": pygame.Rect(105,425,270,52),
                "LEADER": pygame.Rect(105,495,270,45)
            }

            for key,rect in self.menu_buttons.items():
                label = {
                    "DE":"DE",
                    "TRUNG BINH":"TRUNG BINH",
                    "KHO":"KHO",
                    "PLAY":"CHOI GAME",
                    "LEADER":"BANG XEP HANG"
                }[key]

                draw_button(
                    label,
                    rect,
                    selected=(key==self.difficulty),
                    color=YELLOW if key in (
                        "DE","TRUNG BINH","KHO"
                    ) else BLUE
                )

            draw_text(
                "GO TEN: NHAP TRUC TIEP",
                W//2,565,font_s,(150,180,220),True
            )

            draw_text(
                "CHUOT: DI CHUYEN | TRAI: BAN | PHAI: TEN LUA",
                W//2,590,font_s,(150,180,220),True
            )

        elif self.state=="leaderboard":
            pygame.draw.rect(
                screen,(3,8,28),
                (25,75,W-50,570),
                border_radius=18
            )

            pygame.draw.rect(
                screen,BLUE,
                (25,75,W-50,570),
                2,border_radius=18
            )

            draw_text(
                "BANG XEP HANG",
                W//2,115,font_l,YELLOW,True
            )

            rows = load_scores()[:10]

            if not rows:
                draw_text(
                    "CHUA CO DU LIEU",
                    W//2,205,font_m,WHITE,True
                )

            for i,row in enumerate(rows):
                label = (
                    f"{i+1:02d}. "
                    f"{row.get('name','PLAYER')[:12]:12} "
                    f"{row.get('score',0):07d}"
                )

                draw_text(
                    label,W//2,175+i*34,
                    font_s,WHITE,True
                )

            self.leader_button = pygame.Rect(
                135,570,210,48
            )

            draw_button(
                "QUAY LAI MENU",
                self.leader_button
            )

        elif self.state=="gameover":
            if not getattr(self,"score_saved",False):
                save_score(
                    self.player_name,
                    self.player.score,
                    self.difficulty
                )

                self.score_saved = True

            pygame.draw.rect(
                screen,(3,8,28),
                (35,205,W-70,340),
                border_radius=16
            )

            pygame.draw.rect(
                screen,RED,
                (35,205,W-70,340),
                2,border_radius=16
            )

            draw_text(
                "GAME OVER",
                W//2,250,font_l,RED,True
            )

            draw_text(
                f"SCORE: {self.player.score}",
                W//2,305,font_m,WHITE,True
            )

            self.over_buttons = {
                "REPLAY":pygame.Rect(85,355,310,48),
                "MENU":pygame.Rect(85,420,310,48),
                "LEADER":pygame.Rect(85,485,310,48)
            }

            draw_button(
                "CHOI LAI",
                self.over_buttons["REPLAY"]
            )

            draw_button(
                "VE MENU",
                self.over_buttons["MENU"]
            )

            draw_button(
                "BANG XEP HANG",
                self.over_buttons["LEADER"],
                color=YELLOW
            )

        elif self.state=="paused":
            # Lop toi giu nguyen hinh anh tran dau ben duoi menu tam dung.
            overlay = pygame.Surface(
                (W,H),
                pygame.SRCALPHA
            )

            overlay.fill((0,0,0,175))
            screen.blit(overlay,(0,0))

            panel = pygame.Rect(
                45,245,W-90,230
            )

            pygame.draw.rect(
                screen,(3,8,28),
                panel,border_radius=18
            )

            pygame.draw.rect(
                screen,BLUE,
                panel,2,border_radius=18
            )

            draw_text(
                "TAM DUNG",
                W//2,290,font_l,YELLOW,True
            )

            draw_text(
                "NHAN P DE CHOI TIEP",
                W//2,330,font_s,LIGHT_BLUE,True
            )

            self.pause_buttons = {
                "CONTINUE": pygame.Rect(90,370,300,48),
                "MENU": pygame.Rect(90,435,300,48)
            }

            draw_button(
                "CHOI TIEP",
                self.pause_buttons["CONTINUE"]
            )

            draw_button(
                "VE MENU CHINH",
                self.pause_buttons["MENU"],
                color=YELLOW
            )


# ==================== CHUONG TRINH CHINH ====================

async def main():
    game = Game()
    running = True

    while running:
        dt = min(clock.tick(FPS)/1000,0.04)

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:

                # P: tam dung khi dang choi, P hoac ENTER: choi tiep.
                if game.state == "playing" and event.key == pygame.K_p:
                    game.state = "paused"

                elif game.state == "paused":
                    if event.key in (
                        pygame.K_p,
                        pygame.K_RETURN
                    ):
                        game.state = "playing"

                    elif event.key == pygame.K_ESCAPE:
                        game.state = "menu"

                elif event.key == pygame.K_ESCAPE:
                    if game.state == "leaderboard":
                        game.state = "menu"

                    else:
                        running = False

                elif game.state == "menu":
                    if event.key == pygame.K_BACKSPACE:
                        game.player_name = game.player_name[:-1]

                    elif (
                        event.unicode.isprintable()
                        and event.unicode.strip()
                        and len(game.player_name) < 12
                    ):
                        game.player_name += event.unicode.upper()

            elif event.type == pygame.MOUSEBUTTONDOWN:

                if event.button == 3:
                    if game.state == "playing":
                        game.use_missile()

                elif event.button == 1:
                    pos = event.pos

                    if game.state == "menu":
                        for difficulty in (
                            "DE","TRUNG BINH","KHO"
                        ):
                            rect = game.menu_buttons.get(
                                difficulty
                            )

                            if rect and rect.collidepoint(pos):
                                game.difficulty = difficulty
                                break

                        else:
                            if (
                                game.menu_buttons.get("PLAY")
                                and game.menu_buttons["PLAY"].collidepoint(pos)
                            ):
                                game.start()

                            elif (
                                game.menu_buttons.get("LEADER")
                                and game.menu_buttons["LEADER"].collidepoint(pos)
                            ):
                                game.state = "leaderboard"

                    elif game.state=="gameover":
                        if (
                            game.over_buttons.get("REPLAY")
                            and game.over_buttons["REPLAY"].collidepoint(pos)
                        ):
                            game.start()

                        elif (
                            game.over_buttons.get("MENU")
                            and game.over_buttons["MENU"].collidepoint(pos)
                        ):
                            game.state = "menu"

                        elif (
                            game.over_buttons.get("LEADER")
                            and game.over_buttons["LEADER"].collidepoint(pos)
                        ):
                            game.state = "leaderboard"

                    elif game.state=="leaderboard":
                        if game.leader_button.collidepoint(pos):
                            game.state = "menu"

                    elif game.state=="paused":
                        if (
                            game.pause_buttons.get("CONTINUE")
                            and game.pause_buttons["CONTINUE"].collidepoint(pos)
                        ):
                            game.state = "playing"

                        elif (
                            game.pause_buttons.get("MENU")
                            and game.pause_buttons["MENU"].collidepoint(pos)
                        ):
                            game.state = "menu"

        game.update(dt)
        game.draw()

        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())