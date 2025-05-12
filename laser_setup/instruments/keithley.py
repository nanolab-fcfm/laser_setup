import logging
import time

from pymeasure.instruments.keithley import Keithley2450 as _Keithley2450
from pymeasure.instruments.keithley import Keithley6517B  # noqa: F401

log = logging.getLogger(__name__)

# Songs for the Keithley to play when it's done with a measurement :)
SONGS: dict[str, list[tuple[float, float]]] = {
    'triad': [(6/4*1000, 0.25), (5/4*1000, 0.25), (1000, 0.25)],
    'A': [(440, 0.2)]
}


class Keithley2450(_Keithley2450):
    buffer_name: str = "defbuffer1"
    buffer_modes = ['CONT', 'ONCE']

    def __init__(self, adapter: str, name: str = None, **kwargs):
        super().__init__(
            adapter, name or "Keithley 2450 SourceMeter", **kwargs
        )

    def make_buffer(
        self, name: str = 'IVBuffer', size: int = 1_000_000, mode: str = None,
    ):
        """Creates a buffer with the given name and size. Sets the fill mode.

        :param name: The name of the buffer.
        :param size: The size of the buffer.
        :param mode: The fill mode of the buffer. Default is 'CONT'.
        """
        if mode is None:
            mode = self.buffer_modes[0]
        elif mode not in self.buffer_modes:
            log.error(f"Invalid buffer mode: {mode}")
            return

        self.write(f':TRACe:MAKE "{name}", {int(size)}')
        self.buffer_name = name
        self.write(f'TRACe:FILL:MODE {mode}')

    def clear_buffer(self, name: str = None):
        """Clears the buffer with the given name. If no name is given, it clears
        the default buffer.

        :param name: The name of the buffer to clear.
        """
        if name is None:
            name = self.buffer_name
        self.write(f':TRACe:CLEar "{name}"')

    def get_data(self) -> list[float]:
        """Returns the latest timestamp and data from the buffer."""
        res = str(self.ask(f':READ? "{self.buffer_name}", REL, READ'))
        data_list = res.removesuffix('\n').split(',')
        return list(map(float, data_list))

    def get_time(self) -> float:
        """Returns the latest timestamp from the buffer."""
        time = float(self.ask(f':READ? "{self.buffer_name}", REL')[:-1])
        return time

    def shutdown(self):
        for freq, t in SONGS['triad']:
            if freq != 0:
                self.beep(freq, t)

            time.sleep(t)

        super().shutdown()
