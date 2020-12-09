import tkinter as tk

from base64 import b64encode
from typing import List, Optional

from .common import *
from .ecs.components import Lives, Score


__all__ = ['Screen']


def load_image(fpath, **kwargs) -> Optional[tk.PhotoImage]:
    try:
        with open(fpath, 'rb') as f:
            data = f.read()
            return tk.PhotoImage(data=b64encode(data), **kwargs)
    except Exception as err:
        critical(err)
        return None


class Screen():
    """
    Abstraction over the raw tkinter canvas.
    """
    def __init__(self, root, **kwargs):
        self.root = root
        self.canvas = tk.Canvas(root,
                width=WIDTH,
                height=HEIGHT,
                bg=BLACK,
                **kwargs)
        self.canvas.pack()

        self.fps = self.canvas.create_text(
                5, 5, anchor='nw', fill=WHITE)
        self.objects = self.canvas.create_text(
                5, 20, anchor='nw', fill=WHITE)
        self.score = self.canvas.create_text(
                WIDTH - 5, 5, anchor='ne', fill=WHITE)
        self.lives = self.canvas.create_text(
                WIDTH - 5, 20, anchor='ne', fill=WHITE)

        self._tracked_entity = -1
        self._tracked_score = 0
        self._tracked_lives = 0
        self.player_name = 'John Doe'

        self.boss_image = self.canvas.create_image(1, 1, anchor='nw', 
            state='hidden', tags='boss-key-img')
        self.boss_image_shown = False

        self.boss_image_data = load_image(BOSS_KEY_IMAGE_FPATH)
        if self.boss_image_data is not None:
            debug('Loaded boss-key image')
            self.update(self.boss_image, image=self.boss_image_data)

        self.menu_shown = False

        self.menu_bg = self.canvas.create_rectangle(
                WIDTH * 0.25, HEIGHT * 0.25,
                WIDTH * 0.75, HEIGHT * 0.75,
                fill=BLACK, state='hidden', tags='menu')

        menu_title_fontsize = 13
        self.menu_title = self.canvas.create_text(
                WIDTH * 0.5, HEIGHT * 0.25 + menu_title_fontsize,
                text='Paused', font=menu_title_fontsize, anchor='center', 
                fill=WHITE, state='hidden', tags='menu')

        self.menu_quit_btn_callback = lambda: None
        self.menu_quit_btn = self.canvas.create_window(
                WIDTH * 0.3, HEIGHT * 0.3,
                width=WIDTH * 0.4, height=20,
                window=tk.Button(self.canvas, text='Quit', bg=RED,
                    command=lambda: self.menu_quit_btn_callback()),
                anchor='nw', state='hidden', tag='menu')

        self.menu_save_btn_callback = lambda: self.save_state()
        self.menu_save_btn = self.canvas.create_window(
                WIDTH * 0.3, HEIGHT * 0.3 + 30,
                width=WIDTH * 0.4, height=20,
                window=tk.Button(self.canvas, text='Save', bg=RED,
                    command=lambda: self.menu_save_btn_callback()),
                anchor='nw', state='hidden', tag='menu')

        self.controls_text = self.canvas.create_text(
                WIDTH * 0.3, HEIGHT * 0.4,
                width=WIDTH * 0.4, text=HELP_CONTENTS, fill=WHITE,
                anchor='nw', state='hidden', tag='menu')


    def tick(self, dt: float, manager):
        if self._tracked_entity != -1:
            self._tracked_lives = manager.fetch_component(
                    self._tracked_entity, Lives.cid).count
            self._tracked_score = manager.fetch_component(
                    self._tracked_entity, Score.cid).count

            self.canvas.itemconfig(self.score,
                    text=f'SCORE: {self._tracked_score:9}')
            self.canvas.itemconfig(self.lives,
                    text=f'LIVES: {self._tracked_lives:9}')

        if dt != 0:
            self.canvas.itemconfig(self.fps, text=f'FPS: {1/dt:9.3f}')

        self.canvas.itemconfig(self.objects,
                text=f'OBJ: {len(manager.entities):9}')

        self.root.update()


    def set_tracked_entity(self, entity):
        self._tracked_entity = entity


    def get_score(self):
        return self._tracked_score


    def get_lives(self):
        return self._tracked_lives


    def get_name(self):
        return self.player_name


    def draw_text(self, x, y, content, **kwargs):
        return self.canvas.create_text(x, y, text=content, **kwargs)


    def draw_image(self, x, y, **kwargs):
        return self.canvas.create_image(x, y, **kwargs)


    def draw_poly(self, vertices: List[int], **kwargs):
        return self.canvas.create_polygon(*vertices, **kwargs)


    def rect_vertices(self, sx, sy):
        x0, y0 = -(sx // 2), -(sy // 2)
        x1, y1 = sx // 2, sy // 2

        return [
            x0, y0,
            x1, y0,
            x1, y1,
            x0, y1
        ]


    def raise_tag(self, tag):
        self.canvas.tag_raise(tag)


    def lower_tag(self, tag):
        self.canvas.tag_lower(tag)


    def update(self, handle, *args, **kwargs):
        self.canvas.itemconfig(handle, *args, **kwargs)


    def get_coords(self, handle, **kwargs):
        return self.canvas.coords(handle)


    def set_coords(self, handle, coords: List[int], **kwargs):
        self.canvas.coords(handle, *coords, **kwargs)


    def remove(self, handle):
        self.canvas.delete(handle)


    def remove_all(self):
        self.canvas.delete(tk.ALL)


    def set_event_handler(self, event, handler):
        self.root.bind(event, handler)


    def set_proto_handler(self, protocol, handler):
        self.root.protocol(protocol, handler)


    def set_quit_handler(self, callback):
        self.menu_quit_btn_callback = callback


    def do_after(self, seconds, callback):
        self.canvas.after(int(seconds * 1000), callback)


    def save_state(self):
        save_gamestate(STATE_FPATH, self._tracked_score, self._tracked_lives)


    def toggle_boss_image(self):
        self.raise_tag('boss-key-img')
        if self.boss_image_shown:
            self.update(self.boss_image, state='hidden')
            self.boss_image_shown = False
        else:
            self.update(self.boss_image, state='normal')
            self.boss_image_shown = True


    def toggle_menu(self):
        self.raise_tag('menu')

        menu_elements = self.canvas.find_withtag('menu')

        if self.menu_shown:
            for element in menu_elements:
                self.update(element, state='hidden')

            self.menu_shown = False
        else:
            for element in menu_elements:
                self.update(element, state='normal')

            self.menu_shown = True


    def toggle_gameover(self, finished_callback):
        self.draw_text(WIDTH / 2, HEIGHT / 2, 'GAME OVER', font='20', fill=RED,
                anchor='center')

        highscore_window = tk.Toplevel(self.root)
        highscore_window.title('Enter your name')

        name_variable = tk.StringVar()
        name_variable.set(self.player_name)

        name_entry = tk.Entry(highscore_window, textvariable=name_variable)
        name_entry.pack()

        def submit():
            self.player_name = name_variable.get()
            finished_callback()

        finish_btn = tk.Button(highscore_window, text='Submit', command=submit)
        finish_btn.pack()


    def destroy(self):
        self.root.destroy()

