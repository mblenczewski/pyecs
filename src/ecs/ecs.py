import time

from dataclasses import dataclass
from pprint import pprint
from typing import Any, Dict, Generator, Iterable, List, Optional, Set, Tuple

from ..common import *
from .components import *
from .systems import *


def flatten_archetype(archetype):
    return tuple(map(lambda c: c.cid, archetype))


class EcsManager:
    """
    Manages an ECS game loop.
    """
    def __init__(self):
        ## the current entity id value. Used to ensure each created entity
        ## has a unique id. Increments whenever a new entity is added
        self.__entity_id = 0

        ## holds all currently registered entities, indexed by entity id
        self.entities = set()

        ## holds hashmaps of system action archetypes, indexed by system action
        ## Is indexed by registered systems
        self.systems = {}

        ## holds hashmaps of component sets, indexed by the id of the entity 
        ## the components belong to. Is indexed by component archetype
        self.archetypes = {}

        ## holds hashmaps of components, indexed by the id of the entity the
        ## component belongs to. Is indexed by the cid of the component held in 
        ## said hashmap
        self.components = {}

        ## the rate at which time flows
        self._deltatime = 1


    def register_system(self, system: System):
        """
        Registers a system for a component type. If the system is already 
        registered then this function is a no-op.
        """
        debug(f'Registering system type {system}')

        if system not in self.systems:
            self.systems[system] = {}

            for action, action_archetype in system.actions().items():
                archetype = flatten_archetype(action_archetype)
                self.systems[system][action] = archetype

                if archetype not in self.archetypes:
                    debug(f'New archetype encountered: {archetype}')
                    self.archetypes[archetype] = {}


    def deregister_system(self, system: System):
        """
        Deregisters the given system.
        """
        debug(f'Deregistering system type {system}')

        if (actionset := self.systems.pop(system, None)) is None:
            return

        for action, action_archetype in actionset.items():
            for _, other_actionset in self.systems.items():
                if action_archetype in other_actionset.values():
                    break
            else:
                ## if no other systems have the same archetype, we can remove
                ## the archetype from the map
                self.archetypes.pop(action_archetype, None)
                debug(f'Deregistered stale archetype: {action_archetype}')


    def create_entity(self) -> int:
        """
        Creates and starts tracking a new entity. Returns the created entity, 
        which can then have components registered on itself.
        """
        ## we create a new entity and assign it a unique postincremented id
        entity = self.__entity_id
        self.__entity_id += 1

        ## we start tracking the entity
        self.entities.add(entity)

        return entity


    def register_component(self, entity: int, component: Component) -> Component:
        """
        Registers the given component for the given entity. The entity will 
        have the component added to the list of processed components. If the 
        entity already had a component of the same type registered, the old 
        component will be returned. Otherwise, the newly set component will be 
        returned.
        """
        if entity not in self.entities:
            critical(f'UNKNOWN ENTITY: {entity}')
            raise ValueError('Attempted to register component for unknown entity')

        component_type = component.cid
        debug(f'Registering component type {component_type} for entity {entity}')

        ## link the component and entity, so that we can later retrieve the
        ## currently operated upon entity from a given component
        component.eid = entity

        ## if no component of the given type has yet been registered
        if component_type not in self.components:
            debug(f'New component type: {component_type}')
            self.components[component_type] = {}  ## create a hashmap for it

        old_component = self.components[component_type].pop(entity, None)

        ## no component of given type registered for the given entity
        if old_component is None:
            ## register the new component
            self.components[component_type][entity] = component

            ## we need to add the entity to any archetypes that need it
            for archetype, bucket in self.archetypes.items():
                if entity in bucket:
                    ## dont add entity to bucket twice to keep debug log clear
                    continue

                values = [None] * len(archetype)
                for idx, component_type in enumerate(archetype):
                    if (component_type not in self.components or
                        entity not in self.components[component_type]):
                        ## component type not registered, or entity doesnt
                        ## have the necessary component registered component
                        break
                    values[idx] = self.components[component_type][entity]
                else:
                    ## by adding the components to the archetype bucket, we can
                    ## iterate through only the components we need when dealing 
                    ## with the archetype later
                    bucket[entity] = tuple(values)
                    debug(f'Adding entity {entity} to archetype bucket: {archetype}')

            ## return the registered component
            return component

        warn(f'Entity {entity} has existing component of type {component_type}!')

        ## component already exists, so replace it and return old value
        self.components[component_type][entity] = component
        return old_component


    def fetch_component(self, entity: int, component_type: int) -> Optional[Component]:
        """
        Returns the component of the given type, which was registered for the 
        given entity, if one exists. Otherwise, this method returns None.
        """
        if entity not in self.entities:
            critical(f'UNKNOWN ENTITY: {entity}')
            raise ValueError('Attempted to fetch component for unknown entity')

        if component_type not in self.components:
            return None

        if entity not in self.components[component_type]:
            return None

        return self.components[component_type][entity]


    def deregister_component(self, entity: int, component_type: int) -> Optional[Component]:
        """
        Deregisters the given component type for the given entity. The entity 
        will have its component removed from the list of processed components, 
        and the component will be returned. If no such component is registered, 
        this method will return None.
        """
        if entity not in self.entities:
            critical(f'UNKNOWN ENTITY: {entity}')
            raise ValueError('Attempted to deregister component for unknown entity')

        if self.fetch_component(entity, component_type) is not None:
            debug(f'Deregistering component type {component_type} for entity {entity}')
            ## we need to deregister any stale component sets for this entity
            ## from any archetypes where they were registered
            for archetype, bucket in self.archetypes.items():
                if component_type in archetype and entity in bucket:
                    value = bucket.pop(entity)

            ## we return the old component that we just removed
            return self.components[component_type].pop(entity)

        return None


    def destroy_entity(self, entity: int) -> List[Component]:
        """
        Removes an entity from the tracked entities list. It will no longer be 
        processed. Also removes the components associated with that entity.
        This method returns a list of all components that were registered for 
        the given entity.
        """
        if entity not in self.entities:
            critical(f'UNKNOWN ENTITY: {entity}')
            raise ValueError('Attempted to destroy unknown entity')

        registered_components = []
        for component_type, components in self.components.items():
            ## if the entity had a component of the given type registered
            ## we add it to the list of components to return
            if entity in components:
                registered_components.append(components[entity])

        ## we unregister all of our registered components
        for component in registered_components:
            self.deregister_component(entity, component.cid)

        ## actually stop tracking the entity
        self.entities.remove(entity)

        return registered_components


    def fetch_archetype(self, archetype: Tuple[type, ...]) -> Optional[Iterable[Tuple[type, ...]]]:
        """
        Fetch all component sets for the given archetype and return them.
        """
        if archetype not in self.archetypes:
            warn(f'Tried to fetch unknown archetype {archetype}!')
            return None

        return self.archetypes[archetype].values()


    def get_deltatime(self):
        return self._deltatime


    def pause(self):
        self._deltatime = 0


    def unpause(self):
        self._deltatime = 1


def setup(manager: EcsManager, screen: Screen):
    """
    Performs one-time initialisation for all registered systems.
    """
    for system, _ in manager.systems.items():
        debug(f'Performing setup for system {system}')
        system.setup(manager, screen)


def cleanup(manager: EcsManager, screen: Screen):
    """
    Performs one-time cleanup for all registered systems.
    """
    for system, _ in manager.systems.items():
        debug(f'Performing cleanup for system {system}')
        system.cleanup(manager, screen)

    pending_systems = [s for s in manager.systems.keys()]
    for system in pending_systems:
        manager.deregister_system(system)

    pending_entities = [e for e in manager.entities]
    for entity in pending_entities:
        manager.destroy_entity(entity)


def process(manager: EcsManager):
    """
    Processes systems until an EcsContinuation.Stop is returned.
    """
    if len(manager.systems) == 0:
        warn(f'No systems have been registered!')
        return

    last_tick_time = time.time()
    while True:
        current_tick_time = time.time()
        dt = (current_tick_time - last_tick_time) * manager.get_deltatime()

        for archetype, component_sets in manager.archetypes.items():
            for system, actionset in manager.systems.items():
                for action, action_archetype in actionset.items():
                    if archetype != action_archetype:
                        continue

                    components = list(component_sets.values())
                    if action(dt, manager, components) == EcsContinuation.Stop:
                        debug(f'System action {action} stopped ECS')
                        return

        last_tick_time = current_tick_time

