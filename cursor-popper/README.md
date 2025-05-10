Cursor Popper

A precision-based reflex game built in Python, where players click to pop bubbles while dodging a speed-adaptive chaser ball. It features real-time input tracking, escalating difficulty, and dynamic motion mechanics that test your reaction speed under pressure.

------

## Gameplay

- Pop as many bubbles as you can by clicking them.
- Dodge the red ball — if it touches your cursor, you explode.
- Gain points, boost speed, and survive as long as possible.
- The smaller the bubble, the more points you get.
- The more bubbles you pop, the faster the red ball gets.
- Two game modes:
  - **Normal**: Chill mode.
  - **Hardcore**: Miss a bubble and it’s game over. Good luck.

------

## Controls

- **Mouse**: Move cursor, click to pop bubbles and restart after exploding.
- **M key**: Mute/unmute sounds.
- **ESC**: Pause/unpause or exit.
- **Space**: Restart after exploding.

------

## Features

- Dynamic particle effects
- Sound and mute toggle
- Mode switching
- Score saving (local JSON file)
- Bubble types (regular + golden)
- Full pause/resume system
- Polished movement and collision system

------

## Requirements

- Python 3.8+
- `pygame` library

Install pygame with:
```bash
pip install pygame
