#!/usr/bin/env python3
"""Capture unmodified fixture Preferences in a real RenPy SDK process.

Copies the source fixture and adds a test-only screenshot/exit harness there.
The original fixture and player package are never edited.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HARNESS = '''# TEST ONLY: not distributed to players.
label before_main_menu:
    $ renpy.show_screen("preferences")
    $ renpy.pause(0.2, hard=True)
    $ renpy.screenshot(__import__("os").environ["LN_BASELINE_SCREENSHOT"])
    $ renpy.quit()
    return
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--renpy', required=True)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--display')
    args = parser.parse_args()
    folder = Path(args.workspace).resolve()
    target = folder / 'Fixture original sin paquete'
    if target.exists():
        raise ValueError('Choose a fresh workspace; baseline target already exists')
    shutil.copytree(ROOT / 'next_fixtures/native_slot_game', target)
    (target / 'game/zz_baseline_capture.rpy').write_text(HARNESS, encoding='utf-8')
    screenshot = folder / 'preferences_before_fixture.png'
    env = os.environ.copy()
    env.update(SDL_AUDIODRIVER='dummy', RENPY_RENDERER='sw',
               LN_BASELINE_SCREENSHOT=str(screenshot))
    if args.display:
        env.update(DISPLAY=args.display, SDL_VIDEODRIVER='x11')
    result = subprocess.run([str(Path(args.renpy).resolve()), str(target),
                             '--savedir', str(folder / 'separate_test_saves')],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=60)
    (folder / 'baseline_engine.log').write_bytes(result.stdout)
    if result.returncode or not screenshot.is_file():
        raise RuntimeError('Baseline capture failed; inspect baseline_engine.log')
    print('Controlled fixture only; real RenPy process:', screenshot)


if __name__ == '__main__':
    main()
