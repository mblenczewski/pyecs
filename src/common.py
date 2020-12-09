import json
import os

from enum import Enum


WIDTH, HEIGHT = 500, 800

HELP_CONTENTS = (
                'Controls:\n'
                'w: move player ship up\n'
                'a: move player ship left\n'
                's: move player ship down\n'
                'd: move player ship right\n'
                'j: primary attack\n'
                'k: secondary attack\n'
                'Escape: pause menu\n'
                'Space: boss key'
                )

BOSS_KEY_IMAGE_FPATH = 'assets/out/boss_image_v2.gif'
SCORE_FPATH = 'scores.scr'

STATE_FPATH = 'state.stt'


def gamestate_is_valid(state):
    if state is None or \
        state.get('score', None) is None or state.get('lives', None) is None:
        return False

    return True


def pack_gamestate(score, lives):
    if score is None or lives is None:
        return None

    return {'score': int(score), 'lives': int(lives)}


def load_gamestate(fpath):
    if not os.path.isfile(fpath):
        return None

    try:
        with open(fpath, 'r') as f:
            serialised = f.read()
            d = json.loads(serialised)

            score = d.get('score', None)
            lives = d.get('lives', None)

            return pack_gamestate(score, lives)

    except Exception as err:
        print(err)

    return None


def save_gamestate(fpath, score, lives):
    with open(fpath, 'w') as f:
        serialised = json.dumps(pack_gamestate(score, lives))
        f.write(f'{serialised}\n')


BLACK = '#000000'
WHITE = '#ffffff'
RED = '#ff0000'
YELLOW = '#ffff00'
GREEN = '#00ff00'
CYAN = '#00ffff'
BLUE = '#0000ff'
MAGENTA = '#ff00ff'

#SEVERITY = 2 ## turns off no messages
#SEVERITY = 1 ## turns off debug messages
#SEVERITY = 0 ## turns off debug and warning messages
SEVERITY = -1 ## turns off all messages


def debug(msg):
    if SEVERITY >= 2:
        print(f'DEBUG: {msg}')


def warn(msg):
    if SEVERITY >= 1:
        print(f'WARNING: {msg}')


def critical(msg):
    if SEVERITY >= 0:
        print(f'!!!CRITICAL!!!: {msg}')


class AutoId:
    """
    Implements a stateful decorator to assign each decorated class a unique id.
    """
    _component_id = 0
    _system_id = 0


    @classmethod
    def component(cls, wrapped_cls):
        wrapped_cls.cid = cls._component_id
        cls._component_id += 1

        return wrapped_cls


    @classmethod
    def system(cls, wrapped_cls):
        wrapped_cls.sid = cls._system_id
        cls._system_id += 1

        return wrapped_cls


class EcsContinuation(Enum):
    """
    Whether the ECS system should continue to the next iteration or stop.
    """
    Stop = 0
    Continue = 1

