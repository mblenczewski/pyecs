import abc

from dataclasses import dataclass
from typing import Any, Callable, Generator, List, Tuple

from ..common import *


class Component(metaclass=abc.ABCMeta):
    """
    Defines the interface for a 'Component', with a unique id.
    """
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, 'cid') and type(subclass.cid) is type(int)
        )

    @abc.abstractmethod
    def cid(self) -> int:
        """
        Returns a unique id for this component class.
        """
        raise NotImplementedError


class ComponentBase:
    """
    Implements functionality common to each component.
    """
    def __hash__(self) -> int:
        return self.cid


@dataclass
@AutoId.component
class Transform2D(ComponentBase):
    """
    Holds the position (pixels), rotation (radians).
    """
    px: float
    py: float
    theta: float


@dataclass
@AutoId.component
class Collider2D(ComponentBase):
    """
    Holds the size of the AABB in the x and y planes.
    """
    sx: float
    sy: float


@dataclass
@AutoId.component
class Collision(ComponentBase):
    """
    Stores a collision between 2 entities.
    """
    colliding_entity: int


@dataclass
@AutoId.component
class Velocity2D(ComponentBase):
    """
    Holds the velocity (pixels per second) of an entity.
    """
    vx: float
    vy: float


@dataclass
@AutoId.component
class ScreenElement(ComponentBase):
    """
    Holds a handle to some screen element.
    """
    handle: int
    vertices: List[int]


@dataclass
@AutoId.component
class StaleTag(ComponentBase):
    """
    Marks an entity as being stale, and marks it to be be disposed of.
    """
    pass


@dataclass
@AutoId.component
class EdgeHarm(ComponentBase):
    """
    Harms a given entity once it reaches the given y-coordinate.
    """
    target: int
    py: int


@dataclass
@AutoId.component
class UserInput(ComponentBase):
    """
    Receives input from peripherals.
    """
    speed: int


@dataclass
@AutoId.component
class Score(ComponentBase):
    """
    Stores the current score that an entity has accrued.
    """
    count: int


@dataclass
@AutoId.component
class Lives(ComponentBase):
    """
    Stores the number of lives that a given entitiy has.
    """
    count: int


@dataclass
@AutoId.component
class Lifespan(ComponentBase):
    """
    Gives an entity a finite lifespan, after which it gets destroyed.
    """
    ttl: float


@dataclass
@AutoId.component
class PlayerTag(ComponentBase):
    """
    Marks an entity as a player.
    """
    pass


@dataclass
@AutoId.component
class EnemyTag(ComponentBase):
    """
    Marks an entity as an enemy.
    """
    pass


@dataclass
class BulletData:
    """
    Common bullet data.
    """
    bullet_size: int
    bullet_speed: int
    bullet_vertices: List[int]
    bullet_colours: List[str]
    bullet_colour_idx: int


@dataclass
@AutoId.component
class BulletTag(ComponentBase):
    """
    Marks an entity as a bullet.
    """
    pass


@dataclass
@AutoId.component
class LinearBulletEmitter(ComponentBase):
    """
    Emits bullets in a straight line.
    """
    data: BulletData
    direction: int


@dataclass
@AutoId.component
class FireLinearBulletEmitter(ComponentBase):
    """
    Used to emit a bullet from a linear emitter.
    """
    pass


@dataclass
@AutoId.component
class RadialBulletEmitter(ComponentBase):
    """
    Emits bullets in an arc.
    """
    data: BulletData
    
    bullet_count: int
    bullet_arc_offset: float ## in radians


@dataclass
@AutoId.component
class FireRadialBulletEmitter(ComponentBase):
    """
    Used to emit a bullet from a radial emitter.
    """
    pass


@dataclass
@AutoId.component
class Spawner(ComponentBase):
    """
    Holds information for an entity spawner.
    """
    spawn_generator: Generator[Tuple[float, Tuple[int, int]], None, None]
    instantiate: Callable[[Tuple[int, int], Any, Any], int]


@dataclass
@AutoId.component
class EnemyEmitterCooldown(ComponentBase):
    """
    Gives an enemy bullet emitter a cooldown.
    """
    min_cooldown: float
    max_cooldown: float

