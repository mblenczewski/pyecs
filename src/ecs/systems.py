import abc
import random
import time

from math import cos, pi, sin
#from profilehooks import profile
from typing import Any, Callable, Dict, Iterator, Tuple, TypeVar

from ..common import *
from .components import *
from ..platform import *


## takes dt (seconds), manager (EcsManager instance), components
SystemAction = Callable[[float, Any, Iterator[Tuple[Component, ...]]], EcsContinuation]


class System(metaclass=abc.ABCMeta):
    """
    Defines the interface for a 'System', handling components of a single type.
    """
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, 'actions') and callable(subclass.actions) and
            hasattr(subclass, 'setup') and callable(subclass.setup) and
            hasattr(subclass, 'cleanup') and callable(subclass.cleanup)
        )

    
    @abc.abstractmethod
    def actions(self) -> Dict[SystemAction, Tuple[type, ...]]:
        """
        Returns a tuple containing the component types this system operates on.
        In other words, returns the component archetype of this system.
        """
        raise NotImplementedError


    @abc.abstractmethod
    def setup(self, manager: Any, screen: Screen):
        """
        Perform one-time initialisation of the system.
        """
        raise NotImplementedError


    @abc.abstractmethod
    def cleanup(self, manager: Any, screen: Screen):
        """
        Perform one-time cleanup of the system before shutdown.
        """
        raise NotImplementedError


class SystemBase:
    """
    Implements functionality common to each system.
    """
    def __hash__(self) -> int:
        return self.sid


@AutoId.system
class Render2DSystem(SystemBase):
    """
    System to handle rendering code.
    """
    def actions(self):
        return {
            self.process_active: (Transform2D, ScreenElement),
            self.process_stale: (StaleTag,),
        }


    def setup(self, manager, screen):
        self.screen = screen
        

    def process_active(self, dt, manager, components) -> EcsContinuation:
        for transform, element in components:
            coords = [None] * len(element.vertices)

            ## translate coords into screen space
            for i in range(len(element.vertices)):
                if i % 2 == 0:  ## even-indexed elements are x coords
                    coords[i] = element.vertices[i] + transform.px
                else:  ## odd-indexed elements are y coords
                    coords[i] = element.vertices[i] + transform.py

            self.screen.set_coords(element.handle, coords)

        self.screen.tick(dt, manager)

        return EcsContinuation.Continue

    
    def process_stale(self, dt, manager, components) -> EcsContinuation:
        for tag, in components:
            entity = tag.eid
            if (element := manager.fetch_component(entity, ScreenElement.cid)) is not None:
                self.screen.remove(element.handle)
            manager.destroy_entity(entity)

        return EcsContinuation.Continue


    def cleanup(self, manager, screen):
        pass


@AutoId.system
class Collider2DSystem(SystemBase):
    """
    System to flag colliding objects (right now we only process bullet collisions).
    """
    def actions(self):
        return {
            self.process: (Transform2D, Collider2D),
        }


    def setup(self, manager, screen):
        pass


    def do_intersect(self, transform_a, collider_a, transform_b, collider_b):
        if transform_a.px - collider_a.sx / 2 < transform_b.px + collider_b.sx / 2 and \
           transform_a.px + collider_a.sx / 2 > transform_b.px - collider_b.sx / 2 and \
           transform_a.py - collider_a.sy / 2 < transform_b.py + collider_b.sy / 2 and \
           transform_a.py + collider_a.sy / 2 > transform_b.py - collider_b.sy / 2:
            return True

        return False

    ## TODO: implement spatial hashing
    #@profile
    def process(self, dt, manager, components) -> EcsContinuation:
        for idx, (transform_a, collider_a) in enumerate(components):
            entity_a = transform_a.eid

            for transform_b, collider_b in components[idx:]:
                entity_b = transform_b.eid

                if entity_a == entity_b:
                    continue

                ## only register collisions between a bullet and non-bullet
                bullet_a = manager.fetch_component(entity_a, BulletTag.cid)
                bullet_b = manager.fetch_component(entity_b, BulletTag.cid)
                if (bullet_a is not None and bullet_b is not None) or \
                   (bullet_a is None and bullet_b is None):
                    continue

                bullet = entity_a if bullet_a is not None else entity_b
                other = entity_b if bullet_a is not None else entity_a

                if self.do_intersect(transform_a, collider_a, transform_b, collider_b):
                    ## TODO: consider splitting collision resolution into separate system?
                    #manager.register_component(entity_a, Collision(entity_b))
                    #manager.register_component(entity_b, Collision(entity_a))

                    if (lives := manager.fetch_component(other, Lives.cid)) is not None:
                        bullet_player_tag = manager.fetch_component(bullet, PlayerTag.cid)
                        bullet_enemy_tag = manager.fetch_component(bullet, EnemyTag.cid)
                        other_player_tag = manager.fetch_component(other, PlayerTag.cid)
                        other_enemy_tag = manager.fetch_component(other, EnemyTag.cid)

                        if bullet_player_tag != other_player_tag or \
                            bullet_enemy_tag != other_enemy_tag:
                            lives.count -= 1
                            manager.register_component(bullet, StaleTag())

        return EcsContinuation.Continue


    def cleanup(self, manager, screen):
        pass


@AutoId.system
class EdgeHarmSystem(SystemBase):
    """
    System to manage edge harm components.
    """
    def actions(self):
        return {
            self.process: (Transform2D, Collider2D, EdgeHarm),
        }


    def setup(self, manager, screen):
        pass


    def process(self, dt, manager, components) -> EcsContinuation:
        for transform, collider, edge_harm in components:
            entity = transform.eid
            dy = collider.sy // 2

            if edge_harm.py - dy < transform.py:
                target_lives = manager.fetch_component(edge_harm.target, Lives.cid)
                if target_lives is not None:
                    target_lives.count -= 1

                manager.register_component(entity, StaleTag())

        return EcsContinuation.Continue


    def cleanup(self, manager, screen):
        pass


@AutoId.system
class Physics2DSystem(SystemBase):
    """
    System to handle 2D physics.
    """
    def actions(self):
        return {
            self.process: (Transform2D, Velocity2D),
        }


    def setup(self, manager, screen):
        pass


    def process(self, dt, manager, components) -> EcsContinuation:
        for transform, velocity in components:
            transform.px += velocity.vx * dt
            transform.py += velocity.vy * dt

        return EcsContinuation.Continue


    def cleanup(self, manager, screen):
        pass


@AutoId.system
class UserInputSystem(SystemBase):
    """
    System to handle user input (keypresses).
    """
    def actions(self):
        return {
            self.process: (Transform2D, Collider2D, Velocity2D, UserInput),
        }


    def setup(self, manager, screen):
        ## the bits which should be set when the control event is raised
        self.input_masks = {
            'left': 0b00000001,
            'right': 0b00000010,
            'up': 0b00000100,
            'down': 0b00001000,
            'fire_primary': 0b00010000,
            'fire_secondary': 0b00100000,
            'menu': 0b01000000,
            'boss': 0b10000000,
        }

        ## the bits which should be unset when the control event is raised
        self.input_reset_masks = {
            'left': 0b11111101,
            'right': 0b11111110,
            'up': 0b11110111,
            'down': 0b11111011,
            'fire_primary': 0b11111111,
            'fire_secondary': 0b11111111,
            'menu': 0b11111111,
            'boss': 0b11111111,
        }

        ## maps a key to a control event
        self.controls = {
            'escape': 'menu',
            'space': 'boss',
            'a': 'left',
            'd': 'right',
            'w': 'up',
            's': 'down',
            'j': 'fire_primary',
            'k': 'fire_secondary',
        }

        ## Gradius is that you?!?
        self.completed_easter_egg = False
        self.easter_egg_idx = 0
        self.easter_egg = [
                'up',
                'up',
                'down',
                'down',
                'left',
                'right',
                'left',
                'right',
                'b',
                'a']
        
        ## the current input value
        self.input_bitmask = 0
        
        ## bitmask used to get the inverse input_mask
        self.inverse_bitmask = 0b11111111

        self.primary_cooldown = 0.15
        self.can_shoot_primary = True

        self.secondary_cooldown = 5
        self.can_shoot_secondary = True

        self.boss_key_cooldown = 0.2
        self.can_toggle_boss_key = True

        self.menu_key_cooldown = 0.2
        self.can_toggle_menu_key = True

        self.currently_paused = False
        self.pause_initiator = ''

        self.screen = screen
        self.screen.set_event_handler(f'<KeyPress>',
                lambda e: self.handle_key_pressed(e))
        self.screen.set_event_handler(f'<KeyRelease>',
                lambda e: self.handle_key_released(e))
        self.screen.set_proto_handler('WM_DELETE_WINDOW',
                lambda: self.handle_window_closed())
        self.screen.set_quit_handler(lambda: self.handle_window_closed())

        self.continuation = EcsContinuation.Continue


    def reset_boss_key(self):
        self.can_toggle_boss_key = True


    def reset_menu_key(self):
        self.can_toggle_menu_key = True


    def reset_primary(self):
        self.can_shoot_primary = True


    def reset_secondary(self):
        self.can_shoot_secondary = True


    def check_mask(self, event):
        return (self.input_bitmask & self.input_masks[event]) == self.input_masks[event]


    def process(self, dt, manager, components) -> EcsContinuation:
        e = self.input_bitmask

        for transform, collider, velocity, user_input in components:
            entity = transform.eid

            if self.completed_easter_egg:
                print('GAMER MOMENT')
                lives = manager.fetch_component(entity, Lives.cid)
                if lives is not None:
                    lives.count = 30
                    self.completed_easter_egg = False

            if self.check_mask('menu'):
                if self.can_toggle_menu_key:
                    if not self.currently_paused:
                        manager.pause()
                        self.currently_paused = True
                        self.pause_initiator = 'menu'
                    elif self.currently_paused and self.pause_initiator == 'menu':
                        manager.unpause()
                        self.currently_paused = False

                    ## allow 1 menu at one time
                    if self.pause_initiator == 'menu':
                        self.screen.toggle_menu()

                        self.can_toggle_menu_key = False
                        self.screen.do_after(self.menu_key_cooldown,
                                lambda: self.reset_menu_key())
            
            if self.check_mask('boss'):
                if self.can_toggle_boss_key:
                    if not self.currently_paused:
                        manager.pause()
                        self.currently_paused = True
                        self.pause_initiator = 'boss'
                    elif self.currently_paused and self.pause_initiator == 'boss':
                        manager.unpause()
                        self.currently_paused = False

                    ## allow 1 menu at one time
                    if self.pause_initiator == 'boss':
                        self.screen.toggle_boss_image()

                        self.can_toggle_boss_key = False
                        self.screen.do_after(self.boss_key_cooldown,
                                lambda: self.reset_boss_key())

            vx, vy = 0, 0
            if self.check_mask('left'):
                vx = -1
            if self.check_mask('right'):
                vx = 1
            if self.check_mask('up'):
                vy = -1
            if self.check_mask('down'):
                vy = 1

            ## we normalise the entities velocity vector to ensure that the
            ## entity cannot use diagonal movement to break the speed barrier
            magnitude = (vx * vx + vy * vy) ** 0.5
            if magnitude:
                vx = (vx / magnitude) * user_input.speed
                vy = (vy / magnitude) * user_input.speed
            else:
                vx *= user_input.speed
                vy *= user_input.speed

            ## clamp the user to the playing field
            dx, dy = collider.sx // 2, collider.sy // 2
            if transform.px < dx:
                transform.px += 1
                vx = 0
            elif WIDTH - dx < transform.px:
                transform.px -= 1
                vx = 0
            if transform.py < dy:
                transform.py += 1
                vy = 0
            elif HEIGHT - dy < transform.py:
                transform.py -= 1
                vy = 0

            ## actually assign the velocity
            velocity.vx = vx
            velocity.vy = vy

            if self.check_mask('fire_primary'):
                if self.can_shoot_primary:
                    manager.register_component(entity, FireLinearBulletEmitter())

                    self.can_shoot_primary = False
                    self.screen.do_after(self.primary_cooldown,
                            lambda: self.reset_primary())

            if self.check_mask('fire_secondary'):
                if self.can_shoot_secondary:
                    manager.register_component(entity, FireRadialBulletEmitter())

                    self.can_shoot_secondary = False
                    self.screen.do_after(self.secondary_cooldown,
                            lambda: self.reset_secondary())

        return self.continuation


    def move_next_code_elem(self, key):
        if self.easter_egg_idx == -1:  ## disallow multiple code inputs
            return

        if key != self.easter_egg[self.easter_egg_idx]:
            self.easter_egg_idx = 0
            return

        self.easter_egg_idx += 1

        if self.easter_egg_idx == len(self.easter_egg):
            self.easter_egg_idx = -1
            self.completed_easter_egg = True


    def handle_key_pressed(self, event):
        self.move_next_code_elem(event.keysym.lower())

        if event.keysym in self.controls:
            binding = self.controls[event.keysym]
        elif event.keysym.lower() in self.controls:
            binding = self.controls[event.keysym.lower()]
        else:
            return

        if binding in self.input_masks and binding in self.input_reset_masks:
            self.input_bitmask &= self.input_reset_masks[binding]
            self.input_bitmask |= self.input_masks[binding]


    def handle_key_released(self, event):
        if event.keysym in self.controls:
            binding = self.controls[event.keysym]
        elif event.keysym.lower() in self.controls:
            binding = self.controls[event.keysym.lower()]
        else:
            return

        if binding in self.input_masks and binding in self.input_reset_masks:
            self.input_bitmask &= self.inverse_bitmask ^ self.input_masks[binding]


    def handle_window_closed(self):
        self.continuation = EcsContinuation.Stop


    def cleanup(self, manager, screen):
        pass


@AutoId.system
class LifeSystem(SystemBase):
    """
    Clears dead entities.
    """
    def actions(self):
        return {
            self.process: (Lives,),
        }


    def setup(self, manager, screen):
        self.screen = screen
        self.continuation = EcsContinuation.Continue


    def process(self, dt, manager, components) -> EcsContinuation:
        player = -1
        score_delta = 0

        for lives, in components:
            entity = lives.eid
    
            player_tag = manager.fetch_component(entity, PlayerTag.cid)

            if player_tag is not None:
                player = entity

            if lives.count <= 0:
                if player_tag is not None:
                    manager.pause()
                    self.screen.set_tracked_entity(-1)

                    def callback():
                        self.continuation = EcsContinuation.Stop

                    self.screen.toggle_gameover(callback)

                if manager.fetch_component(entity, EnemyTag.cid):
                    score_delta += 1

                manager.register_component(entity, StaleTag())

        if player != -1:
            player_score = manager.fetch_component(player, Score.cid)
            player_score.count += score_delta

        return self.continuation


    def cleanup(self, manager, screen):
        pass


@AutoId.system
class LifespanSystem(SystemBase):
    """
    System to kill components that exceed their lifespan.
    """
    def actions(self):
        return {
            self.process: (Lifespan,),
        }


    def setup(self, manager, screen):
        pass


    def process(self, dt, manager, components) -> EcsContinuation:
        for lifespan, in components:
            entity = lifespan.eid

            lifespan.ttl -= dt

            if lifespan.ttl < 0:
                manager.register_component(entity, StaleTag())

        return EcsContinuation.Continue


    def cleanup(self, manager, screen):
        pass


@AutoId.system
class BulletEmitterSystem(SystemBase):
    """
    Controls entities with a bullet emitter.
    """
    def actions(self):
        return {
            self.process_linear: (Transform2D, Collider2D, LinearBulletEmitter),
            self.process_radial: (Transform2D, Collider2D, RadialBulletEmitter),
        }


    def setup(self, manager, screen):
        self.screen = screen


    def create_bullet(self, manager, bullet_transform, bullet_velocity, bullet_data):
        bullet = manager.create_entity()

        bullet_collider = Collider2D(
            bullet_data.bullet_size, bullet_data.bullet_size)

        bullet_screen_element = self.screen.draw_poly(
            bullet_data.bullet_vertices,
            fill=bullet_data.bullet_colours[bullet_data.bullet_colour_idx])

        bullet_data.bullet_colour_idx += 1
        bullet_data.bullet_colour_idx %= len(bullet_data.bullet_colours)

        bullet_sprite = ScreenElement(
            bullet_screen_element, bullet_data.bullet_vertices)

        ## ensure that bullets can travel the diagonal of the playfield at least
        lifespan = (((HEIGHT ** 2) + (WIDTH ** 2)) ** 0.5) / abs(bullet_data.bullet_speed)
        bullet_lifespan = Lifespan(lifespan)

        manager.register_component(bullet, bullet_transform)
        manager.register_component(bullet, bullet_collider)
        manager.register_component(bullet, bullet_velocity)
        manager.register_component(bullet, bullet_lifespan)
        manager.register_component(bullet, bullet_sprite)
        manager.register_component(bullet, BulletTag())

        return bullet


    def process_linear(self, dt, manager, components) -> EcsContinuation:
        if dt == 0:  ## dont shoot when paused
            return EcsContinuation.Continue

        for transform, collider, emitter in components:
            entity = transform.eid
            
            if (tag := manager.fetch_component(entity, FireLinearBulletEmitter.cid)) is None:
                continue

            manager.deregister_component(entity, tag.cid)

            bullet_transform = Transform2D(transform.px, transform.py, 0)

            vx, vy = 0, emitter.data.bullet_speed

            bullet_velocity = Velocity2D(vx, vy) 

            bullet = self.create_bullet(
                manager, bullet_transform, bullet_velocity, emitter.data)

            if manager.fetch_component(entity, PlayerTag.cid) is not None:
                manager.register_component(bullet, PlayerTag())
            elif manager.fetch_component(entity, EnemyTag.cid) is not None:
                manager.register_component(bullet, EnemyTag())

        return EcsContinuation.Continue


    def process_radial(self, dt, manager, components) -> EcsContinuation:
        if dt == 0:  ## dont shoot when paused
            return EcsContinuation.Continue

        for transform, collider, emitter in components:
            entity = transform.eid

            if (tag := manager.fetch_component(entity, FireRadialBulletEmitter.cid)) is None:
                continue

            manager.deregister_component(entity, tag.cid)

            sweep_increment = 2 * pi / emitter.bullet_count 

            bullet_data = emitter.data

            for n in range(emitter.bullet_count):
                bullet_transform = Transform2D(transform.px, transform.py, 0)

                theta = emitter.bullet_arc_offset + (n * sweep_increment)

                ## Clockwise Rotation matrix:
                ## [  cos0 sin0 ] [ x ] = [  x*cos0 + y*sin0 ]
                ## [ -sin0 cos0 ] [ y ]   [ -x*sin0 + y*cos0 ]
                ## Since we only have a 1-dimensional 'speed', we assign it to
                ## 'y' (completely arbitrarily) and then calculate the [vx vy]
                ## vector for the rotated projectile (we assume x = 0)
                vx, vy = sin(theta), cos(theta)

                speed = emitter.data.bullet_speed
                bullet_velocity = Velocity2D(vx * speed, vy * speed)

                bullet = self.create_bullet(
                    manager, bullet_transform, bullet_velocity, bullet_data)

                if manager.fetch_component(entity, PlayerTag.cid) is not None:
                    manager.register_component(bullet, PlayerTag())
                elif manager.fetch_component(entity, EnemyTag.cid) is not None:
                    manager.register_component(bullet, EnemyTag())

        return EcsContinuation.Continue


    def cleanup(self, manager, screen):
        pass


@AutoId.system
class SpawnerSystem(SystemBase):
    """
    Manages all of the spawners in the game.
    """
    def actions(self):
        return {
            self.process: (Spawner,),
        }


    def setup(self, manager, screen):
        self.screen = screen
        self.cooldowns = {}


    def process(self, dt, manager, components) -> EcsContinuation:
        for spawner, in components:
            entity = spawner.eid
            cooldown_remaining = self.cooldowns.get(entity, 0)

            cooldown_remaining -= dt
            if cooldown_remaining <= 0:
                cooldown_remaining, (spawn_px, spawn_py) = next(spawner.spawn_generator)
                new_entity = spawner.instantiate((spawn_px, spawn_py), manager, self.screen)
            
            self.cooldowns[entity] = cooldown_remaining

        return EcsContinuation.Continue


    def cleanup(self, manager, screen):
        pass


@AutoId.system
class EnemyEmitterSystem(SystemBase):
    """
    Manages enemies with bullet emitters.
    """
    def actions(self):
        return {
            self.process: (EnemyEmitterCooldown,),
        }


    def setup(self, manager, screen):
        self.cooldowns = {}


    def process(self, dt, manager, components) -> EcsContinuation:
        for emitter_cooldown, in components:
            entity = emitter_cooldown.eid

            remaining_cooldown = self.cooldowns.get(entity, 0)

            remaining_cooldown -= dt
            if remaining_cooldown <= 0:
                manager.register_component(entity, FireLinearBulletEmitter())
                manager.register_component(entity, FireRadialBulletEmitter())

                remaining_cooldown = random.randint(
                        emitter_cooldown.min_cooldown, emitter_cooldown.max_cooldown)

            self.cooldowns[entity] = remaining_cooldown
            
        return EcsContinuation.Continue


    def cleanup(self, manager, screen):
        pass

