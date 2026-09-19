#!/usr/bin/env python3
"""Schiller Skip — neon stone-skip arcade for ElbowOS."""
import argparse, math, os, random, subprocess, sys

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "SCHILLER SKIP"
HANDLE = "x.com/ElbowOS"
PAL = {
    "bg": (4, 10, 22),
    "deep": (2, 18, 28),
    "abyss": (1, 6, 14),
    "teal": (32, 210, 196),
    "cyan": (72, 255, 232),
    "gold": (255, 206, 72),
    "amber": (255, 148, 48),
    "violet": (168, 92, 255),
    "pink": (255, 88, 176),
    "ice": (230, 252, 255),
    "dim": (70, 110, 130),
    "white": (255, 252, 245),
}


def irides(t, phase=0.0):
    k = 0.5 + 0.5 * math.sin(t * 0.11 + phase)
    r = int(80 + 140 * k + 35 * math.sin(t * 0.07 + 1.2))
    g = int(160 + 80 * math.sin(t * 0.09 + phase))
    b = int(200 + 55 * math.cos(t * 0.08 + phase * 0.6))
    return (max(40, min(255, r)), max(80, min(255, g)), max(120, min(255, b)))


class Game:
    def __init__(self, auto=False):
        self.auto = auto
        self.t = self.score = self.skips = self.combo = 0
        self.flash = 0
        self.aim = -1.15
        self.cool = 0
        self.stones = []
        self.sparks = []
        self.ripples = []
        self.lanterns = []
        self.motes = [
            (random.randrange(W), random.randrange(H), random.randint(1, 3),
             random.choice((PAL["teal"], PAL["gold"], PAL["violet"], PAL["pink"])))
            for _ in range(70)
        ]
        self.waves = [random.uniform(0, 6.28) for _ in range(14)]
        for i in range(7):
            self._spawn_lantern(H * 0.22 + i * 170)
        self.pier_y = H - 260

    def _spawn_lantern(self, y=None):
        y = -40 if y is None else y
        self.lanterns.append({
            "x": random.uniform(140, W - 140),
            "y": y,
            "r": random.uniform(18, 26),
            "ph": random.random() * 6.28,
            "hue": random.choice((0.0, 1.7, 3.4)),
        })

    def _burst(self, x, y, col, n=16):
        for _ in range(n):
            a = random.random() * 6.283
            s = random.uniform(2.2, 10)
            self.sparks.append([x, y, math.cos(a) * s, math.sin(a) * s, 18, col])

    def _throw(self):
        if self.cool > 0:
            return
        spd = 22
        vx = math.cos(self.aim) * spd
        vy = math.sin(self.aim) * spd
        self.stones.append({
            "x": W * 0.5, "y": self.pier_y - 20,
            "vx": vx, "vy": vy, "life": 220, "spin": 0.0, "skips": 0,
        })
        self.cool = 18
        self._burst(W * 0.5, self.pier_y - 20, PAL["gold"], 10)

    def _water_y(self, x, band):
        base = 340 + band * 92
        return base + math.sin(self.t * 0.07 + self.waves[band] + x * 0.008) * 22

    def autoplay(self):
        target = -1.05 + 0.18 * math.sin(self.t * 0.05)
        if self.lanterns:
            nearest = min(self.lanterns, key=lambda L: L["y"] if L["y"] > 200 else 9999)
            dx = nearest["x"] - W * 0.5
            target = math.atan2(-16, dx * 0.08 + (40 if dx >= 0 else -40)) - 0.35
            target = max(-1.45, min(-0.72, target))
        self.aim += (target - self.aim) * 0.18
        if self.cool == 0 and self.t % 28 == 4:
            self._throw()

    def step(self, keys=None):
        self.t += 1
        self.flash = max(0, self.flash - 1)
        self.cool = max(0, self.cool - 1)
        if self.auto:
            self.autoplay()
        elif keys is not None:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.aim -= 0.045
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.aim += 0.045
            self.aim = max(-1.55, min(-0.55, self.aim))
            if self.cool == 0 and (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]):
                self._throw()
        for L in self.lanterns:
            L["y"] += 2.4
            L["x"] += math.sin(self.t * 0.04 + L["ph"]) * 1.4
            L["x"] = max(80, min(W - 80, L["x"]))
        self.lanterns = [L for L in self.lanterns if L["y"] < H - 180]
        while len(self.lanterns) < 7:
            self._spawn_lantern()
        live = []
        for s in self.stones:
            s["vy"] += 0.62
            s["x"] += s["vx"]
            s["y"] += s["vy"]
            s["spin"] += 0.28
            s["life"] -= 1
            if s["x"] < 30 or s["x"] > W - 30:
                s["vx"] *= -0.82
                s["x"] = max(30, min(W - 30, s["x"]))
            skipped = False
            if s["vy"] > 2:
                for b in range(14):
                    wy = self._water_y(s["x"], b)
                    if abs(s["y"] - wy) < 16:
                        s["vy"] = -abs(s["vy"]) * 0.78 - 3.2
                        s["vx"] *= 0.96
                        s["y"] = wy - 18
                        s["skips"] += 1
                        self.skips += 1
                        self.combo = min(20, self.combo + 1)
                        self.score += 12 + self.combo * 4
                        self.flash = 3
                        self.ripples.append([s["x"], wy, 8, 28, irides(self.t, b)])
                        self._burst(s["x"], wy, irides(self.t, s["spin"]), 12)
                        skipped = True
                        break
            hit = None
            for L in self.lanterns:
                if (s["x"] - L["x"]) ** 2 + (s["y"] - L["y"]) ** 2 < (L["r"] + 16) ** 2:
                    hit = L
                    break
            if hit:
                self.score += 40 + self.combo * 8
                self.combo = min(20, self.combo + 2)
                self.flash = 6
                self._burst(hit["x"], hit["y"], irides(self.t, hit["hue"]), 22)
                self.lanterns.remove(hit)
            if s["life"] > 0 and s["y"] < H - 120 and (s["skips"] < 8 or s["vy"] < 18):
                live.append(s)
            elif s["y"] >= H - 120:
                self.combo = 0
                self.ripples.append([s["x"], H - 200, 10, 22, PAL["violet"]])
        self.stones = live
        nxt = []
        for r in self.ripples:
            r[2] += 7
            r[3] -= 1
            if r[3] > 0:
                nxt.append(r)
        self.ripples = nxt
        keep = []
        for sp in self.sparks:
            sp[0] += sp[2]
            sp[1] += sp[3]
            sp[3] += 0.18
            sp[4] -= 1
            if sp[4] > 0:
                keep.append(sp)
        self.sparks = keep

    def draw(self, surf, font, small, mid):
        for y in range(0, H, 6):
            k = y / H
            col = (int(4 + 8 * k), int(10 + 28 * k), int(22 + 36 * k))
            pygame.draw.rect(surf, col, (0, y, W, 6))
        for i, (x, y, r, col) in enumerate(self.motes):
            yy = (y + int(self.t * 0.9 + i)) % H
            pygame.draw.circle(surf, col, (x, yy), r)
        for b in range(14):
            pts = []
            for x in range(0, W + 24, 24):
                pts.append((x, int(self._water_y(x, b))))
            shade = 40 + (b % 3) * 18
            pygame.draw.lines(surf, (8, shade, 70 + b * 6), False, pts, 3)
            glow = irides(self.t, b * 0.4)
            pygame.draw.lines(surf, glow, False, [(p[0], p[1] - 3) for p in pts], 1)
        for r in self.ripples:
            pygame.draw.circle(surf, r[4], (int(r[0]), int(r[1])), int(r[2]), 2)
        for L in self.lanterns:
            col = irides(self.t, L["hue"])
            pygame.draw.circle(surf, col, (int(L["x"]), int(L["y"])), int(L["r"] + 6))
            pygame.draw.circle(surf, PAL["ice"], (int(L["x"]), int(L["y"])), int(L["r"] - 4))
            pygame.draw.circle(surf, col, (int(L["x"]), int(L["y"]) - 2), 5)
        pygame.draw.rect(surf, (18, 28, 36), (0, self.pier_y, W, H - self.pier_y))
        pygame.draw.rect(surf, PAL["teal"], (0, self.pier_y, W, 6))
        for i in range(9):
            pygame.draw.rect(surf, (28, 44, 52), (70 + i * 110, self.pier_y + 10, 18, 80))
        ax = W * 0.5 + math.cos(self.aim) * 160
        ay = self.pier_y - 20 + math.sin(self.aim) * 160
        pygame.draw.line(surf, PAL["gold"], (W * 0.5, self.pier_y - 20), (ax, ay), 4)
        pygame.draw.circle(surf, PAL["gold"], (int(ax), int(ay)), 8)
        pygame.draw.circle(surf, PAL["teal"], (int(W * 0.5), int(self.pier_y - 20)), 22)
        pygame.draw.circle(surf, PAL["ice"], (int(W * 0.5 - 6), int(self.pier_y - 26)), 6)
        for s in self.stones:
            col = irides(self.t, s["spin"])
            pygame.draw.circle(surf, col, (int(s["x"]), int(s["y"])), 16)
            pygame.draw.circle(surf, PAL["white"], (int(s["x"]), int(s["y"])), 9)
            ox = s["x"] + math.cos(s["spin"]) * 7
            oy = s["y"] + math.sin(s["spin"]) * 7
            pygame.draw.circle(surf, col, (int(ox), int(oy)), 4)
        for sp in self.sparks:
            pygame.draw.circle(surf, sp[5], (int(sp[0]), int(sp[1])), max(2, sp[4] // 4))
        if self.flash:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((72, 255, 232, 10 * self.flash))
            surf.blit(veil, (0, 0))
        banner = pygame.Surface((W, 150), pygame.SRCALPHA)
        banner.fill((2, 8, 16, 214))
        surf.blit(banner, (0, 0))
        surf.blit(font.render(TITLE, True, PAL["cyan"]), (40, 18))
        surf.blit(small.render(HANDLE, True, PAL["pink"]), (40, 88))
        sc = font.render(f"{self.score:05d}", True, PAL["gold"])
        surf.blit(sc, (W - 48 - sc.get_width(), 18))
        meta = small.render(f"SKIPS {self.skips}   COMBO {self.combo}", True, PAL["ice"])
        surf.blit(meta, (W - 48 - meta.get_width(), 90))
        hint = "A / D aim   SPACE skip" if not self.auto else "AUTO SCHILLER"
        foot = small.render(hint, True, PAL["dim"])
        surf.blit(foot, foot.get_rect(center=(W * 0.5, H - 48)))


def record(path):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    pygame.font.init()
    surf = pygame.Surface((W, H))
    font = pygame.font.SysFont("DejaVu Sans", 58, bold=True)
    mid = pygame.font.SysFont("DejaVu Sans", 48, bold=True)
    small = pygame.font.SysFont("DejaVu Sans", 34, bold=True)
    g = Game(auto=True)
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    frames = FPS * 15
    try:
        for _ in range(frames):
            g.step()
            g.draw(surf, font, small, mid)
            proc.stdin.write(pygame.image.tostring(surf, "RGB"))
        proc.stdin.close()
        err = proc.stderr.read()
        rc = proc.wait(timeout=60)
    except Exception:
        proc.kill()
        raise
    if rc != 0:
        raise RuntimeError(err.decode("utf-8", "ignore")[-800:])
    print("wrote", path)


def play():
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("DejaVu Sans", 58, bold=True)
    mid = pygame.font.SysFont("DejaVu Sans", 48, bold=True)
    small = pygame.font.SysFont("DejaVu Sans", 34, bold=True)
    g = Game(auto=False)
    run = True
    while run:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                run = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                run = False
        g.step(pygame.key.get_pressed())
        g.draw(screen, font, small, mid)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record", action="store_true")
    p.add_argument("--play", action="store_true")
    p.add_argument("--out", default="/home/workdir/artifacts/schiller_skip_ElbowOS.mp4")
    a = p.parse_args()
    if a.record or not a.play:
        record(a.out)
        if a.play:
            play()
    else:
        play()


if __name__ == "__main__":
    main()
