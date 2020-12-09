#!/usr/bin/env python3

"""
UoM COMP16321 Coursework 2

This coursework is split into multiple parts, because i could not deal with a
single python file that would be like 2000 lines long. The general structure
is as follows:
    - main.py : initialises the game, does serialisation / deserialisation,
                and also starts the main menu.
    - assets/ : stores game related assets such as the boss-key image
    - src/    : stores the games source code
        - common.py   : Stores global variables, functions common to the
                        rest of the games modules, and a few miscellaneous 
                        utility classes and functions.
        - platform.py : Provides a wrapper around the tkinter canvas, called 
                        "Screen". This wrapper implemented a bunch of GUI
                        related functionality, and is a singleton class.

        - ecs/        : Stores the Entity-Component-System source code
            - ecs.py        : Stores the implementation of the ECS manager,
                              which allows for the registration of systems,
                              the creation of entities, and the registration
                              of components on said entities. It also provides
                              methods to setup, process, and cleanup an ECS.
            - components.py : Stores all the components in use by the game.
                              Provides a "formal virtual interface" that should
                              be implemented by all components.
            - systems.py    : Stores all the systems in use by the game.
                              Provides a "formal virtual interface" that should
                              be implemented by all systems.
"""

import os
import random
import tkinter as tk

import src
import src.ecs.ecs as ecs
import src.ecs.components as components
import src.ecs.systems as systems
import src.platform as platform

from math import pi

from src.common import *


def run(root, starting_score=0, starting_lives=5):
    screen = platform.Screen(root)

    manager = ecs.EcsManager()

    ## register all systems that will be used in the game
    manager.register_system(systems.Render2DSystem())
    manager.register_system(systems.Collider2DSystem())
    manager.register_system(systems.EdgeHarmSystem())
    manager.register_system(systems.Physics2DSystem())
    manager.register_system(systems.UserInputSystem())
    manager.register_system(systems.LifeSystem())
    manager.register_system(systems.LifespanSystem())
    manager.register_system(systems.BulletEmitterSystem())
    manager.register_system(systems.SpawnerSystem())
    manager.register_system(systems.EnemyEmitterSystem())

    ## create player
    player = manager.create_entity()
    manager.register_component(player, components.PlayerTag())
    screen.set_tracked_entity(player)

    player_vertices = [-5, 10, 0, -10, 5, 10, 0, 5]
    player_sprite = screen.draw_poly(player_vertices, fill=CYAN, tag='player')
    manager.register_component(player, components.Transform2D(WIDTH / 2,
        HEIGHT / 2, 0))
    manager.register_component(player, components.Collider2D(10, 20))
    manager.register_component(player, components.Velocity2D(0, 0))
    manager.register_component(player, components.UserInput(220))
    manager.register_component(player, components.ScreenElement(player_sprite,
        player_vertices))

    manager.register_component(player, components.Score(starting_score))
    manager.register_component(player, components.Lives(starting_lives))
    player_bullet_data = components.BulletData(
        bullet_size=10,
        bullet_speed=-270,
        bullet_vertices=[-5, 0, 0, 5, 5, 0, 0, -5],
        bullet_colours=[CYAN],
        bullet_colour_idx=0)
    manager.register_component(player, components.LinearBulletEmitter(
        data=player_bullet_data, direction=-1))
    manager.register_component(player, components.RadialBulletEmitter(
        data=player_bullet_data, bullet_count=48, bullet_arc_offset=0))

    ## create enemy spawner
    enemy_spawner = manager.create_entity()

    enemy_patterns = [
        'loner',
        'column',
        'row_ltr',
        'row_rtl',
    ]

    enemy_size = 20
    enemy_padding = enemy_size / 2

    def next_spawn():
        while True:
            next_pattern = random.choice(enemy_patterns)
            pattern_cooldown = 1

            min_enemies, max_enemies = 2, 3

            player_score = screen.get_score()
            if player_score > 100:
                min_enemies, max_enemies = 4, 5
            if player_score > 150:
                min_enemies, max_enemies = 6, 7
            if player_score > 200:
                pattern_cooldown = 0.75

            base_px = random.randint(enemy_size, WIDTH - enemy_size)
            enemy_count = random.randint(min_enemies, max_enemies)

            if next_pattern == 'loner':
                yield (pattern_cooldown, (base_px, enemy_size))

            elif next_pattern == 'column':
                for i in range(enemy_count):
                    yield (0.25, (base_px, enemy_size))
                yield (pattern_cooldown, (base_px, enemy_size))

            elif next_pattern == 'row_ltr':
                max_px = enemy_count * (enemy_size + enemy_padding) + enemy_size
                base_px = random.randint(enemy_size, WIDTH - max_px)
                curr_px = base_px
                for i in range(enemy_count):
                    yield (0.05, (curr_px, enemy_size))
                    curr_px += enemy_size + enemy_size / 2
                yield (pattern_cooldown, (curr_px, enemy_size))

            elif next_pattern == 'row_rtl':
                min_px = enemy_count * (enemy_size + enemy_padding) + enemy_size
                base_px = random.randint(min_px, WIDTH - enemy_size)
                curr_px = base_px
                for i in range(enemy_count):
                    yield (0.05, (curr_px, enemy_size))
                    curr_px -= enemy_size + enemy_size / 2
                yield (pattern_cooldown, (curr_px, enemy_size))


    def create_enemy(spawn_location, manager, screen):
        e = manager.create_entity()
        manager.register_component(e, components.EnemyTag())

        enemy_speed = 130
        shooter_chance = 0.125
        min_shooter_cooldown, max_shooter_cooldown = 2, 3
        heavy_chance = 0

        player_score = screen.get_score()
        if player_score > 100:
            shooter_chance = 0.25
            min_shooter_cooldown = 1
            heavy_chance = 0.05

        if player_score > 150:
            shooter_chance = 0.5
            heavy_chance = 0.075

        if player_score > 200:
            max_shooter_cooldown = 2
            heavy_chance = 0.1

        enemy_l_wing = [-3, 0, -5, 0, -7, 7, -10, 0]
        enemy_r_wing = [10, 0, 7, 7, 5, 0, 3, 0]
        enemy_vertices = [*enemy_l_wing, -7, -3, 7, -3, *enemy_r_wing, 0, 15]

        sx, sy = 16, 25
        px, py = spawn_location
        vx, vy = 0, enemy_speed

        manager.register_component(e, components.Transform2D(px, py, 0))
        manager.register_component(e, components.Collider2D(sx, sy))
        manager.register_component(e, components.Velocity2D(vx, vy))
        manager.register_component(e, components.EdgeHarm(player,
            HEIGHT + 2 * sy))

        ## have some enemies shoot bullets we have to dodge
        if random.random() <= shooter_chance:
            enemy_bullet_data = components.BulletData(
                bullet_size=10,
                bullet_speed=180,
                bullet_vertices=[-5, 0, 0, 5, 5, 0, 0, -5],
                bullet_colours=[RED],
                bullet_colour_idx=0)

            manager.register_component(e, components.EnemyEmitterCooldown(
                min_shooter_cooldown, max_shooter_cooldown))
            if random.randint(0, 1) == 1:
                manager.register_component(e, components.LinearBulletEmitter(
                    data=enemy_bullet_data, direction=1))
            else:
                manager.register_component(e, components.RadialBulletEmitter(
                    data=enemy_bullet_data, bullet_count=4,
                    bullet_arc_offset=pi / 4))

        ## have some enemies have 2 lives
        if random.random() <= heavy_chance:
            sprite = screen.draw_poly(enemy_vertices, fill=MAGENTA)
            manager.register_component(e, components.ScreenElement(sprite,
                enemy_vertices))
            manager.register_component(e, components.Lives(2))
        else:
            sprite = screen.draw_poly(enemy_vertices, fill=YELLOW)
            manager.register_component(e, components.ScreenElement(sprite,
                enemy_vertices))
            manager.register_component(e, components.Lives(1))


    manager.register_component(enemy_spawner, components.Spawner(next_spawn(),
        create_enemy))

    ## make player visible
    screen.raise_tag(player_sprite)

    ## start processing the game
    ecs.setup(manager, screen)
    ecs.process(manager)
    ecs.cleanup(manager, screen)

    player_score = screen.get_score()
    player_name = screen.get_name()

    screen.destroy()
    return (player_name, player_score)


def load_scores(fpath):
    scores = {}

    if not os.path.isfile(fpath):
        return {}

    with open(fpath, 'r') as f:
        for line in f:
            segments = line.rsplit(',')
            name, score = segments[0], int(segments[1].strip())
            scores[name] = score

    return scores


def save_scores(fpath, scores):
    with open(fpath, 'w') as f:
        for name, score in scores.items():
            f.write(f'{name},{score}\n')


def main():
    root = tk.Tk()
    root.title('Bullet Purgatory')
    root.protocol('WM_DELETE_WINDOW', lambda: root.destroy())

    menu_elements = []

    def disable_menu():
        for element in menu_elements:
            element.config(state='disabled')


    def enable_menu():
        for element in menu_elements:
            element.config(state='normal')


    def start_game(starting_score=0, starting_lives=5):
        disable_menu()
        
        game_window = tk.Toplevel(root)
        game_window.title('Bullet Purgatory')

        scores = load_scores(SCORE_FPATH)
        name, score = run(game_window, starting_score, starting_lives)
        scores[name] = max(score, scores.get(name, 0))

        entries, highscores = len(scores), {}
        for _ in range(entries if entries < 10 else 10):
            keyfunc = lambda t: t[1]
            highest_scoring = max(scores.items(), key=keyfunc)[0]

            highscores[highest_scoring] = scores.pop(highest_scoring)

        save_scores(SCORE_FPATH, highscores)

        enable_menu()

        root.protocol('WM_DELETE_WINDOW', lambda: root.destroy())


    start_btn = tk.Button(root, text='Start Game', command=start_game)
    start_btn.pack()
    menu_elements.append(start_btn)

    def show_leaderboard():
        highscores = load_scores(SCORE_FPATH)
        
        leaderboard_window = tk.Toplevel(root)
        leaderboard_window.title('Bullet Purgatory Leaderboard')

        header = tk.Label(leaderboard_window, text='FORMAT: <name> : <score>')
        header.pack()
        for name, score in highscores.items():
            label = tk.Label(leaderboard_window, text=f'{name} : {score}')
            label.pack()

        close_btn = tk.Button(leaderboard_window, text='Close Leaderboard',
                command=leaderboard_window.destroy)
        close_btn.pack()


    leaderboard_btn = tk.Button(root, text='Show Leaderboard',
            command=show_leaderboard)
    leaderboard_btn.pack()
    menu_elements.append(leaderboard_btn)

    def load_game():
        state = load_gamestate(STATE_FPATH)

        if gamestate_is_valid(state):
            start_game(state['score'], state['lives'])
        else:
            start_game()


    load_game_btn = tk.Button(root, text='Load Game', command=load_game)
    load_game_btn.pack()
    menu_elements.append(load_game_btn)

    def show_help():
        help_window = tk.Toplevel(root)
        help_window.title('Bullet Purgatory Help (psst. Gradius called ;^))')

        contents = tk.Label(help_window, text=HELP_CONTENTS)
        contents.pack()

        close_btn = tk.Button(help_window, text='Close Help',
                command=help_window.destroy)
        close_btn.pack()


    show_help_btn = tk.Button(root, text='Show Help', command=show_help)
    show_help_btn.pack()
    menu_elements.append(show_help_btn)

    root.mainloop()


if __name__ == '__main__':
    main() 

