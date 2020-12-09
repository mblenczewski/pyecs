#!/bin/sh

OUT_FILE="game.zip"

[ -f "${OUT_FILE}" ] && rm "${OUT_FILE}"

[ -d ./__pycache__/ ] && rm -rf ./__pycache__/
[ -d ./assets/__pycache__/ ] && rm -rf ./assets/__pycache__/
[ -d ./src/__pycache__/ ] && rm -rf ./src/__pycache__/
[ -d ./src/ecs/__pycache__/ ] && rm -rf ./src/ecs/__pycache__/

zip "${OUT_FILE}" -r *
