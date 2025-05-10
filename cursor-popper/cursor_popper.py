import pygame
import random
import math
import sys
import json
import os
import time

# Initialize
pygame.init()
pygame.mixer.init()  # Initialize the mixer for audio
screen = pygame.display.set_mode((800, 800))
clock = pygame.time.Clock()

# Constants
CENTER = (400, 400)
ARENA_RADIUS = 350
CURSOR_RADIUS = 5
IMMUNITY_DURATION = 2000  # 2 seconds of immunity in milliseconds

# Audio setup
try:
    bubble_pop_sound = pygame.mixer.Sound('bubble-pop.wav')
    bounce_sound = pygame.mixer.Sound('bounce.wav')
    audio_muted = False
except Exception as e:
    print(f"Error loading audio files: {e}")
    # Create silent sounds as fallbacks
    bubble_pop_sound = pygame.mixer.Sound(buffer=bytearray(88200))  # 1 second of silence (44100Hz * 2 channels)
    bounce_sound = pygame.mixer.Sound(buffer=bytearray(88200))
    audio_muted = True

# Function to play sound with mute check
def play_sound(sound, volume=1.0):
    if not audio_muted:
        sound.set_volume(volume)
        sound.play()

# Error handling - creates a log file for errors
def log_error(error_message):
    try:
        with open("game_error_log.txt", "a") as log_file:
            log_file.write(f"{pygame.time.get_ticks()}: {error_message}\n")
    except Exception as e:
        print(f"Failed to log error: {e}")

# Score system with error handling
class ScoreManager:
    def __init__(self):
        self.normal_score = 0
        self.hardcore_score = 0
        self.normal_best_score = 0
        self.hardcore_best_score = 0
        self.scores_file = "scores.json"
        self.load_scores()

    def load_scores(self):
        try:
            if os.path.exists(self.scores_file):
                with open(self.scores_file, "r") as file:
                    data = json.load(file)
                    self.normal_best_score = data.get("normal_best", 0)
                    self.hardcore_best_score = data.get("hardcore_best", 0)
        except Exception as e:
            log_error(f"Failed to load scores: {e}")

    def save_scores(self):
        try:
            with open(self.scores_file, "w") as file:
                json.dump({
                    "normal_best": self.normal_best_score,
                    "hardcore_best": self.hardcore_best_score
                }, file)
        except Exception as e:
            log_error(f"Failed to save scores: {e}")

    def update_score(self, points, mode):
        try:
            if mode == 'Normal':
                self.normal_score += points
                if self.normal_score > self.normal_best_score:
                    self.normal_best_score = self.normal_score
                    self.save_scores()
                return self.normal_score
            else:  # Hardcore mode
                self.hardcore_score += points
                if self.hardcore_score > self.hardcore_best_score:
                    self.hardcore_best_score = self.hardcore_score
                    self.save_scores()
                return self.hardcore_score
        except Exception as e:
            log_error(f"Error updating score: {e}")
            return 0

    def get_current_score(self, mode):
        return self.normal_score if mode == 'Normal' else self.hardcore_score

    def get_best_score(self, mode):
        return self.normal_best_score if mode == 'Normal' else self.hardcore_best_score

    def reset_current_score(self, mode):
        try:
            if mode == 'Normal':
                self.normal_score = 0
            else:
                self.hardcore_score = 0
        except Exception as e:
            log_error(f"Error resetting score: {e}")

# Create score manager
score_manager = ScoreManager()

# Chaser ball
chaser = {
    'x': 400,
    'y': 400,
    'vx': 0,
    'vy': 0,
    'speed': 1,
    'immunity_end': 0,  # Timestamp when immunity ends
    'last_bounce_time': 0  # To prevent multiple bounce sounds in a short period
}

particles = []
pops = []
exploded = False
paused = False
started = False
choosing_mode = True
pause_start_time = 0  # Track when pause started

# Bubbles
bubbles = []
explode = False
BUBBLE_SPAWN_TIME = 1000  # every second
last_spawn = 0
BUBBLE_LIFESPAN = 5000  # 5 seconds
bubble_spawn_count = 0
next_golden_spawn = random.randint(15, 25)

# Score
font = pygame.font.SysFont(None, 48)
small_font = pygame.font.SysFont(None, 46)
tiny_font = pygame.font.SysFont(None, 30)

# Modes
mode = 'Normal'  # or 'Hardcore'
mode_button_rect = pygame.Rect(630, 740, 150, 40)
normal_button_rect = pygame.Rect(250, 400, 300, 60)
hardcore_button_rect = pygame.Rect(250, 500, 300, 60)
mute_button_rect = pygame.Rect(20, 740, 100, 40)

# Trails
trail_particles = []

# AI control
auto_control = False

def reset_game():
    global chaser, particles, exploded, bubbles, last_spawn, pops, bubble_spawn_count, next_golden_spawn
    try:
        current_time = pygame.time.get_ticks()
        chaser = {
            'x': 400,
            'y': 400,
            'vx': 0,
            'vy': 0,
            'speed': 1.5,
            'immunity_end': current_time + IMMUNITY_DURATION,  # Set immunity for 2 seconds
            'last_bounce_time': 0
        }
        particles = []
        pops = []
        exploded = False
        bubbles = []
        last_spawn = current_time
        score_manager.reset_current_score(mode)
        bubble_spawn_count = 0
        next_golden_spawn = random.randint(15, 25)
    except Exception as e:
        log_error(f"Error in reset_game: {e}")

# Game loop
running = True
while running:
    try:
        current_time = pygame.time.get_ticks()
        screen.fill((30, 30, 30))

        # Draw arena
        pygame.draw.circle(screen, (50, 50, 50), CENTER, ARENA_RADIUS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()

                # Check for mute button click
                if mute_button_rect.collidepoint(mx, my):
                    audio_muted = not audio_muted
                    # Play a test sound when unmuting to confirm
                    if not audio_muted:
                        play_sound(bubble_pop_sound, 0.3)
                    continue

                # Unpause when clicking inside the arena
                if paused:
                    dx = mx - CENTER[0]
                    dy = my - CENTER[1]
                    if math.hypot(dx, dy) <= ARENA_RADIUS:
                        # Calculate how long the game was paused and adjust timers
                        pause_duration = current_time - pause_start_time
                        # Adjust immunity end time
                        if chaser['immunity_end'] > 0:
                            chaser['immunity_end'] += pause_duration
                        # Adjust bubble spawn times
                        last_spawn += pause_duration
                        # Adjust bubble lifespans
                        for bubble in bubbles:
                            bubble['spawn_time'] += pause_duration

                        paused = False
                        continue  # Skip the rest of the event handling while paused

                if choosing_mode:
                    if normal_button_rect.collidepoint(mx, my):
                        mode = 'Normal'
                        choosing_mode = False
                        started = True
                        reset_game()
                    elif hardcore_button_rect.collidepoint(mx, my):
                        mode = 'Hardcore'
                        choosing_mode = False
                        started = True
                        reset_game()
                else:
                    if exploded:
                        dx = mx - CENTER[0]
                        dy = my - CENTER[1]
                        if math.hypot(dx, dy) <= ARENA_RADIUS:
                            reset_game()
                            started = True

                    if started and not exploded:
                        for bubble in bubbles[:]:
                            if math.hypot(bubble['x'] - mx, bubble['y'] - my) < bubble['radius']:
                                bubbles.remove(bubble)
                                points = (30 - bubble['radius']) // 2
                                score_manager.update_score(points, mode)
                                boost = (30 - bubble['radius']) / 30 * 0.5
                                chaser['speed'] += boost
                                if bubble['golden']:
                                    chaser['speed'] *= 0.7

                                # Play pop sound
                                play_sound(bubble_pop_sound)

                                for _ in range(10):
                                    angle = random.uniform(0, 2 * math.pi)
                                    speed = random.uniform(1, 3)
                                    pops.append({
                                        'x': bubble['x'],
                                        'y': bubble['y'],
                                        'vx': math.cos(angle) * speed,
                                        'vy': math.sin(angle) * speed,
                                        'life': 30,
                                        'color': (255, 215, 0) if bubble['golden'] else (0, 200, 255)
                                    })

                    elif mode_button_rect.collidepoint(mx, my):
                        mode = 'Hardcore' if mode == 'Normal' else 'Normal'

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and exploded:
                    reset_game()
                    started = True

                if event.key == pygame.K_ESCAPE:
                    if exploded:
                        pygame.quit()
                        sys.exit()
                    elif started:
                        if not paused:
                            pause_start_time = current_time  # Record when we paused
                        paused = not paused

                # Mute/unmute with M key
                if event.key == pygame.K_m:
                    audio_muted = not audio_muted
                    if not audio_muted:
                        play_sound(bubble_pop_sound, 0.3)

        if choosing_mode:
            title = font.render("Choose a Mode", True, (255, 255, 255))
            screen.blit(title, (400 - title.get_width() // 2, 250))

            pygame.draw.rect(screen, (70, 70, 70), normal_button_rect)
            pygame.draw.rect(screen, (150, 0, 0), hardcore_button_rect)

            normal_text = font.render("Normal Mode", True, (255, 255, 255))
            hardcore_text = font.render("Hardcore Mode", True, (255, 255, 255))

            screen.blit(normal_text, (normal_button_rect.centerx - normal_text.get_width() // 2, normal_button_rect.centery - normal_text.get_height() // 2))
            screen.blit(hardcore_text, (hardcore_button_rect.centerx - hardcore_text.get_width() // 2, hardcore_button_rect.centery - hardcore_text.get_height() // 2))

            # Draw mute button
            pygame.draw.rect(screen, (60, 60, 60), mute_button_rect)
            mute_text = tiny_font.render("Sound: " + ("OFF" if audio_muted else "ON"), True, (255, 255, 255))
            screen.blit(mute_text, (mute_button_rect.centerx - mute_text.get_width() // 2, mute_button_rect.centery - mute_text.get_height() // 2))
            mute_button_rect.width = max(mute_button_rect.width, mute_text.get_width() + 10)
            mute_button_rect.height = max(mute_button_rect.height, mute_text.get_height() + 10)


            pygame.display.flip()
            clock.tick(60)
            continue

        if paused:
            pause_text = font.render("PAUSED", True, (255, 255, 255))
            screen.blit(pause_text, (400 - pause_text.get_width() // 2, 400 - pause_text.get_height() // 2))

            pygame.draw.rect(screen, (60, 60, 60), mute_button_rect)
            mute_text = tiny_font.render("Sound: " + ("OFF" if audio_muted else "ON"), True, (255, 255, 255))
            screen.blit(mute_text, (mute_button_rect.centerx - mute_text.get_width() // 2, mute_button_rect.centery - mute_text.get_height() // 2))
            mute_button_rect.width = max(mute_button_rect.width, mute_text.get_width() + 10)
            mute_button_rect.height = max(mute_button_rect.height, mute_text.get_height() + 10)

            # Draw everything in its paused state
            # Draw bubbles
            for bubble in bubbles:
                color = (255, 215, 0) if bubble['golden'] else (0, 200, 255)
                pygame.draw.circle(screen, color, (int(bubble['x']), int(bubble['y'])), bubble['radius'], 2)

            # Draw chaser ball if game started and not exploded
            if started and not exploded:
                # Check if currently immune and flash the chaser ball
                is_immune = current_time < chaser['immunity_end']
                if is_immune:
                    # Flash every 200ms during immunity
                    if (current_time // 200) % 2 == 0:
                        chaser_color = (255, 200, 200)  # Lighter red during immunity
                    else:
                        chaser_color = (255, 50, 50)  # Normal red
                else:
                    chaser_color = (255, 50, 50)  # Normal red

                pygame.draw.circle(screen, chaser_color, (int(chaser['x']), int(chaser['y'])), 30)

            # Draw particles
            for p in particles:
                pygame.draw.circle(screen, p['color'], (int(p['x']), int(p['y'])), p['radius'])

            # Draw pop particles
            for p in pops:
                pygame.draw.circle(screen, p['color'], (int(p['x']), int(p['y'])), 2)

            # Draw trail particles
            for p in trail_particles:
                alpha = max(0, min(255, int(p['life'] / 30 * 255)))
                surface = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
                pygame.draw.circle(surface, (*p['color'], alpha), (p['size'], p['size']), p['size'])
                screen.blit(surface, (p['x'] - p['size'], p['y'] - p['size']))

            # Draw cursor
            if started:
                mx, my = pygame.mouse.get_pos()
                pygame.draw.circle(screen, (255, 255, 255), (mx, my), CURSOR_RADIUS)

            # Display scores during pause
            if started:
                current_score = score_manager.get_current_score(mode)
                best_score = score_manager.get_best_score(mode)

                score_text = font.render(f"Score: {current_score}", True, (255, 255, 255))
                best_text = font.render(f"Best: {best_score}", True, (255, 255, 0))
                mode_score_text = small_font.render(f"{mode} Mode", True, (200, 200, 200))

                screen.blit(score_text, (30, 30))
                screen.blit(best_text, (800 - best_text.get_width() - 30, 30))
                screen.blit(mode_score_text, (400 - mode_score_text.get_width() // 2, 30))

            # Mode switch button
            pygame.draw.rect(screen, (150, 0, 0) if mode == 'Hardcore' else (70, 70, 70), mode_button_rect)
            mode_text = small_font.render(mode, True, (255, 255, 255))
            screen.blit(mode_text, (mode_button_rect.centerx - mode_text.get_width() // 2, mode_button_rect.centery - mode_text.get_height() // 2))

            # Draw mute button
            pygame.draw.rect(screen, (60, 60, 60), mute_button_rect)
            mute_text = tiny_font.render("Sound: " + ("OFF" if audio_muted else "ON"), True, (255, 255, 255))
            screen.blit(mute_text, (mute_button_rect.centerx - mute_text.get_width() // 2, mute_button_rect.centery - mute_text.get_height() // 2))

            pygame.display.flip()
            clock.tick(60)
            continue

        # Mouse position (real or AI)
        if not exploded:

            pygame.draw.rect(screen, (60, 60, 60), mute_button_rect)
            mute_text = tiny_font.render("Sound: " + ("OFF" if audio_muted else "ON"), True, (255, 255, 255))
            screen.blit(mute_text, (mute_button_rect.centerx - mute_text.get_width() // 2, mute_button_rect.centery - mute_text.get_height() // 2))
            mute_button_rect.width = max(mute_button_rect.width, mute_text.get_width() + 10)
            mute_button_rect.height = max(mute_button_rect.height, mute_text.get_height() + 10)

            if auto_control and bubbles:
                closest = min(bubbles, key=lambda b: math.hypot(b['x'] - chaser['x'], b['y'] - chaser['y']))
                mx, my = closest['x'], closest['y']
            else:
                mx, my = pygame.mouse.get_pos()

        # Lock cursor inside arena
        if started and not exploded and not paused:
            dx = mx - CENTER[0]
            dy = my - CENTER[1]
            dist = math.hypot(dx, dy)
            if dist > ARENA_RADIUS - CURSOR_RADIUS:
                angle = math.atan2(dy, dx)
                mx = CENTER[0] + math.cos(angle) * (ARENA_RADIUS - CURSOR_RADIUS)
                my = CENTER[1] + math.sin(angle) * (ARENA_RADIUS - CURSOR_RADIUS)
                if not auto_control:
                    pygame.mouse.set_pos((int(mx), int(my)))

        # Bubble spawning
        if started and not exploded and current_time - last_spawn > BUBBLE_SPAWN_TIME:
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, ARENA_RADIUS - 30)
            bx = CENTER[0] + math.cos(angle) * radius
            by = CENTER[1] + math.sin(angle) * radius

            is_golden = False
            bubble_spawn_count += 1
            if bubble_spawn_count >= next_golden_spawn:
                is_golden = True
                bubble_spawn_count = 0
                next_golden_spawn = random.randint(15, 25)

            bubbles.append({
                'x': bx,
                'y': by,
                'vx': random.uniform(-1.0, 1.0) if is_golden else random.uniform(-0.5, 0.5),
                'vy': random.uniform(-1.0, 1.0) if is_golden else random.uniform(-0.5, 0.5),
                'radius': random.randint(8, 12) if is_golden else random.randint(10, 25),
                'spawn_time': current_time,
                'golden': is_golden,
                'last_bounce_time': 0  # To prevent multiple bounce sounds in a short period
            })
            last_spawn = current_time

        # Update chaser ball
        if started and not exploded and not paused:
            dx = mx - chaser['x']
            dy = my - chaser['y']
            dist = math.hypot(dx, dy)

            if dist != 0:
                dx /= dist
                dy /= dist

            chaser['vx'] += dx * 0.6
            chaser['vy'] += dy * 0.6
            chaser['vx'] *= 0.95
            chaser['vy'] *= 0.95
            chaser['x'] += chaser['vx'] * chaser['speed']
            chaser['y'] += chaser['vy'] * chaser['speed']

            # Bounce off walls
            dx = chaser['x'] - CENTER[0]
            dy = chaser['y'] - CENTER[1]
            dist = math.hypot(dx, dy)

            # Add trail particle after updating chaser's position
            trail_particles.append({
                'x': chaser['x'],
                'y': chaser['y'],
                'life': 30,  # Set the lifespan for the trail
                'color': (255, 255, 255),  # Color of the trail (white)
                'size': random.randint(2, 4),  # Size of the trail particles
            })

            # Limit the number of trail particles to avoid memory issues
            if len(trail_particles) > 100:
                trail_particles.pop(0)

            if dist > ARENA_RADIUS - 20:
                nx = dx / dist
                ny = dy / dist
                dot = chaser['vx'] * nx + chaser['vy'] * ny
                chaser['vx'] -= 2 * dot * nx
                chaser['vy'] -= 2 * dot * ny
                chaser['x'] = CENTER[0] + nx * (ARENA_RADIUS - 20)
                chaser['y'] = CENTER[1] + ny * (ARENA_RADIUS - 20)

                # Play bounce sound with cooldown to prevent sound spam
                if current_time - chaser['last_bounce_time'] > 200:  # 200ms cooldown
                    play_sound(bounce_sound, 0.3)
                    chaser['last_bounce_time'] = current_time

            # Check immunity before collision detection
            is_immune = current_time < chaser['immunity_end']

            # Cursor collision (only if not immune)
            if not is_immune and math.hypot(chaser['x'] - mx, chaser['y'] - my) < 20:
                exploded = True
                # Pop all bubbles visually when exploding
                for bubble in bubbles:
                    for _ in range(10):
                        angle = random.uniform(0, 2 * math.pi)
                        speed = random.uniform(1, 3)
                        pops.append({
                            'x': bubble['x'],
                            'y': bubble['y'],
                            'vx': math.cos(angle) * speed,
                            'vy': math.sin(angle) * speed,
                            'life': 30,
                            'color': (255, 215, 0) if bubble['golden'] else (0, 200, 255)
                        })

                    # Play pop sound for each bubble (with volume scaling to avoid being too loud)
                    play_sound(bubble_pop_sound, min(0.5, 1.0 / max(1, len(bubbles) / 5)))

                bubbles.clear()

                for _ in range(300):
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(2, 5)
                    particles.append({
                        'x': chaser['x'],
                        'y': chaser['y'],
                        'vx': math.cos(angle) * speed,
                        'vy': math.sin(angle) * speed,
                        'radius': random.randint(2, 4),
                        'color': (random.randint(150, 255), random.randint(50, 255), random.randint(50, 255)),
                        'last_bounce_time': 0  # Track last bounce time for sound cooldown
                    })

        # Update pop particles
        for p in pops[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            if p['life'] <= 0:
                pops.remove(p)

        # Update bubbles
        for bubble in bubbles[:]:
            bubble['x'] += bubble['vx']
            bubble['y'] += bubble['vy']

            dx = bubble['x'] - CENTER[0]
            dy = bubble['y'] - CENTER[1]
            dist = math.hypot(dx, dy)
            if dist > ARENA_RADIUS - bubble['radius']:
                angle = math.atan2(dy, dx)
                bubble['x'] = CENTER[0] + math.cos(angle) * (ARENA_RADIUS - bubble['radius'])
                bubble['y'] = CENTER[1] + math.sin(angle) * (ARENA_RADIUS - bubble['radius'])
                bubble['vx'] *= -1
                bubble['vy'] *= -1

                # Play bounce sound with cooldown to prevent sound spam
                if current_time - bubble.get('last_bounce_time', 0) > 300:  # 300ms cooldown
                    play_sound(bounce_sound, 0.2)
                    bubble['last_bounce_time'] = current_time

            if current_time - bubble['spawn_time'] > BUBBLE_LIFESPAN:
                for _ in range(10):
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(1, 3)
                    pops.append({
                        'x': bubble['x'],
                        'y': bubble['y'],
                        'vx': math.cos(angle) * speed,
                        'vy': math.sin(angle) * speed,
                        'life': 30,
                        'color': (255, 215, 0) if bubble['golden'] else (0, 200, 255)
                    })

                # Play pop sound
                play_sound(bubble_pop_sound)

                bubbles.remove(bubble)

                if mode == 'Hardcore':
                    # Check immunity before game over in hardcore mode
                    is_immune = current_time < chaser['immunity_end']
                    if not is_immune:
                        exploded = True
                        # Pop all bubbles visually when exploding
                        for bubble in bubbles:
                            for _ in range(10):
                                angle = random.uniform(0, 2 * math.pi)
                                speed = random.uniform(1, 3)
                                pops.append({
                                    'x': bubble['x'],
                                    'y': bubble['y'],
                                    'vx': math.cos(angle) * speed,
                                    'vy': math.sin(angle) * speed,
                                    'life': 30,
                                    'color': (255, 215, 0) if bubble['golden'] else (0, 200, 255)
                                })

                            # Play pop sound (with volume scaling)
                            play_sound(bubble_pop_sound, min(0.5, 1.0 / max(1, len(bubbles) / 5)))

                        bubbles.clear()

                        for _ in range(300):
                            angle = random.uniform(0, 2 * math.pi)
                            speed = random.uniform(2, 5)
                            particles.append({
                                'x': chaser['x'],
                                'y': chaser['y'],
                                'vx': math.cos(angle) * speed,
                                'vy': math.sin(angle) * speed,
                                'radius': random.randint(2, 4),
                                'color': (random.randint(150, 255), random.randint(50, 255), random.randint(50, 255)),
                                'last_bounce_time': 0
                            })

        # Draw everything
        for p in pops:
            pygame.draw.circle(screen, p['color'], (int(p['x']), int(p['y'])), 2)

        for bubble in bubbles:
            color = (255, 215, 0) if bubble['golden'] else (0, 200, 255)
            pygame.draw.circle(screen, color, (int(bubble['x']), int(bubble['y'])), bubble['radius'], 2)

        if started and not exploded and not paused:
            # Check if currently immune and flash the chaser ball
            is_immune = current_time < chaser['immunity_end']
            if is_immune:
                # Flash every 200ms (approximately)
                if (current_time // 200) % 2 == 0:
                    chaser_color = (255, 200, 200)  # Lighter red during immunity
                else:
                    chaser_color = (255, 50, 50)  # Normal red
            else:
                chaser_color = (255, 50, 50)  # Normal red

            pygame.draw.circle(screen, chaser_color, (int(chaser['x']), int(chaser['y'])), 30)

        if exploded:

            pygame.draw.rect(screen, (60, 60, 60), mute_button_rect)
            mute_text = tiny_font.render("Sound: " + ("OFF" if audio_muted else "ON"), True, (255, 255, 255))
            screen.blit(mute_text, (mute_button_rect.centerx - mute_text.get_width() // 2, mute_button_rect.centery - mute_text.get_height() // 2))
            mute_button_rect.width = max(mute_button_rect.width, mute_text.get_width() + 10)
            mute_button_rect.height = max(mute_button_rect.height, mute_text.get_height() + 10)

            for p in particles:
                pygame.draw.circle(screen, p['color'], (int(p['x']), int(p['y'])), p['radius'])

                p['x'] += p['vx']
                p['y'] += p['vy']
                p['vx'] *= 0.995
                p['vy'] *= 0.995

                # Ensure particles stay inside the arena
                dx = p['x'] - CENTER[0]
                dy = p['y'] - CENTER[1]
                dist = math.hypot(dx, dy)

                # Check if the particle is outside the arena boundary
                if dist > ARENA_RADIUS - p['radius']:
                    # Clamp the particle to the boundary (keep it within the arena)
                    angle = math.atan2(dy, dx)
                    p['x'] = CENTER[0] + math.cos(angle) * (ARENA_RADIUS - p['radius'])
                    p['y'] = CENTER[1] + math.sin(angle) * (ARENA_RADIUS - p['radius'])

                    # Reflect the particle's velocity off the boundary (bounce effect)
                    normal_angle = angle  # Angle of the normal at the boundary
                    normal_vector = pygame.math.Vector2(math.cos(normal_angle), math.sin(normal_angle))

                    # Reflect the velocity by calculating the dot product and flipping the velocity along the normal
                    velocity = pygame.math.Vector2(p['vx'], p['vy'])
                    velocity_reflection = velocity - 2 * velocity.dot(normal_vector) * normal_vector

                    # Apply the reflected velocity to the particle
                    p['vx'], p['vy'] = velocity_reflection.x, velocity_reflection.y

                    # Slow down the particle as it hits the boundary (reduce speed)
                    p['vx'] *= 0.5
                    p['vy'] *= 0.5

                    # Play bounce sound with cooldown
                    if not hasattr(p, 'last_bounce_time') or current_time - p.get('last_bounce_time', 0) > 500:
                        # Only play the sound occasionally to prevent sound spam
                        if random.random() < 0.05:  # 5% chance to play sound on bounce
                            play_sound(bounce_sound, 0.1)
                            p['last_bounce_time'] = current_time

        if started:
            pygame.draw.circle(screen, (255, 255, 255), (mx, my), CURSOR_RADIUS)

        if started:
            # Display appropriate scores
            current_score = score_manager.get_current_score(mode)
            best_score = score_manager.get_best_score(mode)

            score_text = font.render(f"Score: {current_score}", True, (255, 255, 255))
            best_text = font.render(f"Best: {best_score}", True, (255, 255, 0))
            mode_score_text = small_font.render(f"{mode} Mode", True, (200, 200, 200))

            screen.blit(score_text, (30, 30))
            screen.blit(best_text, (800 - best_text.get_width() - 30, 30))
            screen.blit(mode_score_text, (400 - mode_score_text.get_width() // 2, 30))

        # Mode switch button
        pygame.draw.rect(screen, (150, 0, 0) if mode == 'Hardcore' else (70, 70, 70), mode_button_rect)
        mode_text = small_font.render(mode, True, (255, 255, 255))
        screen.blit(mode_text, (mode_button_rect.centerx - mode_text.get_width() // 2, mode_button_rect.centery - mode_text.get_height() // 2))

        if exploded:
            text = font.render("Press 'SPACE' or click on screen to Play Again", True, (255, 255, 255))
            screen.blit(text, (400 - text.get_width() // 2, 400 - text.get_height() // 2))

        # Update and draw the trail particles
        for p in trail_particles[:]:
            p['life'] -= 1  # Decrease the life of the particle
            if p['life'] <= 0:
                trail_particles.remove(p)  # Remove particle if its life ends
                continue

            # Fade the trail by reducing the size and adjusting the alpha
            alpha = max(0, min(255, int(p['life'] / 30 * 255)))  # Fade based on life
            surface = pygame.Surface((p['size'] * 2, p['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*p['color'], alpha), (p['size'], p['size']), p['size'])
            screen.blit(surface, (p['x'] - p['size'], p['y'] - p['size']))

        pygame.display.flip()
        clock.tick(60)

    except Exception as e:
        log_error(f"Critical game error: {e}")
        print(f"An error occurred: {e}")
        # Try to recover
        try:
            reset_game()
        except:
            pass

# Save scores before exiting
score_manager.save_scores()
pygame.quit()