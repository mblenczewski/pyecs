#!/usr/bin/env python3

from os import listdir, mkdir
from os.path import isdir, isfile, join
from PIL import Image
from shutil import rmtree

from src.common import HEIGHT, WIDTH


BASE_DIR = './assets'
OUT_DIR = join(BASE_DIR, 'out')


def main():
    if isdir(OUT_DIR):
        rmtree(OUT_DIR)

    mkdir(OUT_DIR)

    for fpath in (join(BASE_DIR, f) for f in listdir(BASE_DIR) if isfile(join(BASE_DIR, f))):
        fname = fpath.rsplit('/', 1)[-1].rsplit('.', 1)[0]

        print(f'Fpath: {fpath}, Fname: {fname}')
        print(f'Target size: {WIDTH}x{HEIGHT}')

        image = Image.open(fpath)

        resized = image.resize((WIDTH, HEIGHT))

        resized.save(join(OUT_DIR, f'{fname}.gif'), format='GIF', save_all=True)


if __name__ == '__main__':
    main()

