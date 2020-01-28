import machine
import utime
import songs  # song list
import _thread
from rtttl import RTTTL  # rtttl parser


class Buzzer:
    def __init__(self, pin, volume=900):
        """
        Initialize the pwm pin for controlling the buzzer.
        It should be a passive active low piezo buzzer.
        :param pin: int; the pwm pin number
        :param volume: int; the duty cycle of the pwm.  higher the duty cycle, higher the volume of the buzzer
        """
        self.buz = machine.PWM(machine.Pin(pin), duty=0, freq=440)
        self.volume = volume
        self.tones = {
            # define frequency for each tone
            'C4': 262,
            'CS4': 277,
            'D4': 294,
            'DS4': 311,
            'E4': 330,
            'F4': 349,
            'FS4': 370,
            'G4': 392,
            'GS4': 415,
            'A4': 440,
            'AS4': 466,
            'B4': 494,
            'C5': 523,
            'CS5': 554,
            'D5': 587,
            'DS5': 622,
            'E5': 659,
            'F5': 698,
            'FS5': 740,
            'G5': 784,
            'GS5': 831,
            'A5': 880,
            'AS5': 932,
            'B5': 988,
        }
        self.tone1 = ['A5', 'B5', 'C5', 'B5', 'C5', 'D5', 'C5', 'D5', 'E5', 'D5', 'E5', 'E5']
        self.tone2 = ['G5', 'C5', 'G5', 'C5']
        self.tone3 = ['E5', 0, 'E5', 0, 'E5']
        self.mute = False
        self.is_playing = False
        self.song = None

    def play_tone(self, freq, msec):
        """
        play the tune by its freq and tempo
        :param freq: int; frequency of the tune
        :param msec: float; tempo
        :return: None
        """
        # print('freq = {:6.1f} msec = {:6.1f}'.format(freq, msec))
        if freq > 0:
            self.buz.freq(int(freq))
            self.buz.duty(int(self.volume))
        utime.sleep_ms(int(msec * 0.9))
        self.buz.duty(0)
        utime.sleep_ms(int(msec * 0.1))

    def play(self, tune):
        """
        parse the tune to be play
        :param tune: tuple; the tune of the song
        :return: None
        """
        try:
            for freq, msec in tune.notes():
                if not self.mute:
                    self.is_playing = True
                    self.play_tone(freq, msec)
                else:
                    self.play_tone(0, 0)
                    self.is_playing = False
                    self.mute = False
                    break
            self.is_playing = False
            self.mute = False
        except KeyboardInterrupt:
            self.play_tone(0, 0)

    def play_song(self, search):
        """
        play a song stored in songs.py
        :param search: string; song name listed in songs.py
        :return: None
        """
        while self.is_playing:
            self.mute = True
        else:
            self.mute = False
        # play song in a new thread (non-blocking)
        # _thread.stack_size(16 * 1024)  # set stack size to avoid runtime error
        # play_tone = _thread.start_new_thread(self.play, (RTTTL(songs.find(search)),))
        self.play(RTTTL(songs.find(search)))
        self.song = None

    def activate(self, song):
        self.song = song
