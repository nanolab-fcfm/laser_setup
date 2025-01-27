import logging
import random
import sys
import time
from typing import Dict, TypeVar
from uuid import uuid4

from pymeasure.adapters import FakeAdapter
from pymeasure.instruments import Instrument
from pymeasure.instruments.fakes import FakeInstrument

log = logging.getLogger(__name__)
AnyInstrument = TypeVar('AnyInstrument', bound=Instrument)


class PendingInstrument(Instrument):
    """A placeholder for an instrument that is pending initialization.

    This class holds the configuration for an instrument that will be connected
    and initialized at a later stage. It allows for the deferred setup of instruments,
    enabling dynamic and flexible instrument management within procedures.

    :param cls: The class of the instrument to be initialized.
    :param adapter: The adapter string for the instrument connection.
    :param name: The name of the instrument.
    :param includeSCPI: Flag indicating whether to include SCPI commands.
    :param kwargs: Additional keyword arguments for instrument configuration.
    """
    def __init__(
        self,
        cls: type[AnyInstrument] = Instrument,
        adapter: str = None,
        name: str = None,
        includeSCPI=False,
        **kwargs
    ):
        self.config = {
            'cls': cls,
            'adapter': adapter,
            'name': name,
            'includeSCPI': includeSCPI,
            **kwargs
        }

    def __repr__(self) -> str:
        return f"PendingInstrument({self.config})"


class InstrumentManager:
    """Manages multiple instruments at the same time using a dictionary to store them.
    Instruments can persist between multiple instances of procedures. It also emits
    signals when an instrument is connected, shutdown, or when all instruments are
    shutdown.

    :method connect: Connects to an instrument and saves it in the instances dictionary.
    :method setup_adapter: Returns an instance of the given instrument class.
    :method shutdown: Safely shuts down the instrument with the given name.
    :method shutdown_all: Safely shuts down all instruments.
    """
    def __init__(self):
        super().__init__()
        self.instances: Dict[str, type[AnyInstrument]] = {}

    def __repr__(self) -> str:
        return f"InstrumentManager({self.instances})"

    @staticmethod
    def help(cls: type[AnyInstrument], return_str=False) -> str:
        """Returns all available controls and measurements for the given
        instrument class. For each control and measurement, it shows the
        description, command sent to the instrument, and the values that
        can be set (either a range or a list of values).

        :param cls: The instrument class to get the help from.
        :param return_str: Whether to return the help string or print it.
        """
        help_str = "Available controls and measurements for "\
            f"{cls.__name__} (not including methods):\n"

        for name in dir(cls):
            try:
                attr = getattr(cls, name)
                if isinstance(attr, property):
                    if attr.fset.__doc__ is None:
                        help_str += f"    {name} (measurement): {attr.__doc__} \n"
                    else:
                        help_str += f"    {name} (control): {attr.__doc__} \n"

                    help_str += 12*" " + \
                        f"fget: '{attr.fget.__defaults__[0]}', " \
                        f"fset: '{attr.fset.__defaults__[0]}', " \
                        f"values={attr.fget.__defaults__[1]}\n\n"

            except Exception:
                continue

        return help_str if return_str else print(help_str)

    @staticmethod
    def setup_adapter(cls: type[AnyInstrument], adapter: str, **kwargs) -> AnyInstrument:
        """Sets up the adapter for the given instrument class. If the setup fails,
        it raises an exception, unless debug mode is enabled (-d flag), in which
        case it replaces the adapter with a FakeAdapter. Returns the instrument
        without saving it in the dictionary.

        :param cls: The instrument class to set up.
        :param adapter: The adapter to use for the communication.
        :param kwargs: Additional keyword arguments to pass to the instrument class.
        :return: The instrument object.
        """
        try:
            instrument: AnyInstrument = cls(adapter=adapter, **kwargs)
        except Exception as e:
            if '-d' in sys.argv or '--debug' in sys.argv:
                log.warning(f"Could not connect to {cls.__name__}: {e} Using DebugInstrument.")
                instrument = DebugInstrument(**kwargs)
            else:
                raise

        return instrument

    def connect(
        self,
        cls: type[AnyInstrument],
        adapter: str | None = None,
        name: str | None = '',
        includeSCPI: bool | None = False,
        **kwargs
    ) -> AnyInstrument:
        """Connects to an instrument and saves it in the dictionary.

        :param cls: The instrument class to set up.
        :param adapter: The adapter to use for the communication. If None, the result
            depends on the instrument class.
        :param name: The name of the instrument. If '', it uses the class name
            and adapter. If None, it uses the default name.
        :param includeSCPI: Flag indicating whether to include SCPI commands. If None,
            it uses the default value.
        :param kwargs: Additional keyword arguments to pass to the instrument class.
        """
        if name == '':
            name = f"{cls.__name__}/{adapter}"

        if name not in self.instances:
            if name is not None:
                kwargs['name'] = name
            else:
                name = uuid4().hex

            if includeSCPI is not None:
                kwargs['includeSCPI'] = includeSCPI

            try:
                instrument = self.setup_adapter(cls, adapter=adapter, **kwargs)
                self.instances[name] = instrument
                log.debug(f"Connected '{name}' as {cls.__name__} via {instrument.adapter}")

            except Exception as e:
                log.error(f"Failed to connect to instrument '{name}': {e}")
                raise

        else:
            log.info(f"Instrument '{name}' already exists.")

        return self.instances[name]

    def shutdown(self, name: str):
        """Safely shuts down the instrument with the given name.

        :param name: The name of the instrument to shutdown.
        """
        try:
            _ = self.instances[name]
        except KeyError:
            log.error(f"Instrument '{name}' not found.")
            return

        try:
            if not isinstance(self.instances[name].adapter, FakeAdapter):
                self.instances[name].shutdown()
            del self.instances[name]
            log.debug(f"Instrument '{name}' was shut down.")
        except Exception as e:
            log.error(f"Error shutting down instrument '{name}': {e}")

    def shutdown_all(self):
        """Safely shuts down all instruments."""
        if not self.instances:
            log.info("No instruments to shut down")
            return

        log.info("Shutting down all instruments.")
        for name in list(self.instances):
            self.shutdown(name)


class DebugInstrument(FakeInstrument):
    """Debug instrument class useful for testing.

    Overrides properties and methods for multiple instrument types, returning
    random data.
    """
    wait_for: float = 0.01

    # meter
    source_voltage: float = 0.
    _func = lambda *args, **kwargs: None  # noqa: E731
    measure_current = _func
    make_buffer = _func
    reset = _func
    enable_source = _func
    clear_buffer = _func

    # tenma
    output: bool = False

    # power meter
    wavelength: float = 0.
    sensor_name: str = 'sensor'

    def __init__(self, name="Debug instrument", **kwargs):
        super().__init__(name=name, **kwargs)
        self._tstart = 0.
        self._voltage = 0.
        self._current = 0.
        self._units = {'voltage': 'V',
                       'output_voltage': 'V',
                       'time': 's',
                       'wave': 'a.u.'}

    def get_time(self):
        """Return the time since the instrument was instantiated."""
        return time.time() - self._tstart

    @property
    def voltage(self):
        """Measure the voltage."""
        time.sleep(self.wait_for)
        return random.uniform(1e-3, 1e-1)

    @voltage.setter
    def voltage(self, value):
        """Set the voltage."""
        self._voltage = value

    @property
    def current(self):
        """Measure the current."""
        time.sleep(self.wait_for)
        return random.uniform(1e-9, 1e-6)

    @current.setter
    def current(self, value):
        """Set the current."""
        self._current = value

    @property
    def power(self):
        """Measure the power."""
        time.sleep(self.wait_for)
        return random.uniform(1e-9, 1e-6)

    def apply_voltage(self, value):
        """Apply a voltage."""
        self.voltage = value

    def ramp_to_voltage(self, value):
        """Ramp to a voltage."""
        self.voltage = value

    def __repr__(self):
        return "<DebugAdapter>"
