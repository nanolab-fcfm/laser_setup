"""
Plays a song on the Keithley 2450 meter.
"""
import time
import sys
from pymeasure.instruments.keithley import Keithley2450
from lib.utils import SONGS
from lib import config

def play_song(song: str):
    if not song in SONGS:
        raise ValueError(f"Song {song} not found in lib.devices.SONGS")
    K = Keithley2450(config['Adapters']['keithley2450'])
    for freq, t in SONGS[song]:
        K.beep(freq, t)
        time.sleep(t)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        song = sys.argv[1]
    else:
        song = 'washing'
    play_song(song)
