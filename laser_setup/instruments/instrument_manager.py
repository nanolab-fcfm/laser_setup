import logging
import random
import time
from types import SimpleNamespace
from typing import TypeVar, Iterator

from pymeasure.adapters import Adapter, FakeAdapter
from pymeasure.instruments import Instrument
from pymeasure.instruments.fakes import FakeInstrument

log = logging.getLogger(__name__)
AnyInstrument = TypeVar('AnyInstrument', bound=Instrument)


class PendingInstrument(SimpleNamespace, Instrument):
    """A placeholder for an instrument that is pending initialization.

    This class holds the configuration for an instrument that will be connected
    and initialized at a later stage. It allows for the deferred setup of instruments,
    enabling dynamic and flexible instrument management within procedures.
    """
    def __init__(
        self,
        instrument: type[AnyInstrument] = Instrument,
        adapter: str | int | Adapter | None = None,
        name: str | None = None,
        includeSCPI: bool = False,
        _instance_id: str | None = None,
        **kwargs
    ):
        """Initializes the PendingInstrument.

        :param instrument: The class of the instrument to be initialized.
        :param adapter: The adapter to be used for the instrument.
        :param name: The name of the instrument.
        :param includeSCPI: Flag indicating whether to include SCPI commands.
        :param _instance_id: A unique identifier used by the instrument manager. If not
            provided, it is generated automatically.
        :param kwargs: Additional keyword arguments for instrument configuration.
        """
        super().__init__(
            instrument=instrument,
            adapter=adapter,
            name=name,
            includeSCPI=includeSCPI,
            _instance_id=_instance_id,
            **kwargs
        )


class InstrumentManager:
    """Manages multiple instruments at the same time using a dictionary to store them.
    Instruments can persist between multiple instances of procedures. The manager
    can connect to and shut down instruments.

    :method help: Prints or returns all available controls and measurements for the
        given instrument class.
    :method connect: Connects to an instrument and saves it in the instances dictionary.
    :method setup_adapter: Returns an instance of the given instrument class.
    :method shutdown: Safely shuts down the instrument with the given name.
    :method shutdown_all: Safely shuts down all instruments.
    """
    id_template = "{instrument.__name__}/{adapter}"

    def __init__(self):
        self.instances: dict[str, Instrument] = {}

    @staticmethod
    def help(instrument: type[Instrument], return_str=False) -> str | None:
        """Returns all available controls and measurements for the given
        instrument class. For each control and measurement, it shows the
        description, command sent to the instrument, and the values that
        can be set (either a range or a list of values).

        :param instrument: The instrument class to get the help from.
        :param return_str: Whether to return the help string or print it.
        """
        help_str = "Available controls and measurements for "\
            f"{instrument.__name__} (not including methods):\n\n"

        for name in dir(instrument):
            attr = getattr(instrument, name)
            if isinstance(attr, property):
                prop_type = "control" if attr.fset.__doc__ else "measurement"
                attr_doc = f"{attr.__doc__.strip()}" if attr.__doc__ else ""
                help_str += f"{name} ({prop_type}): {attr_doc}\n\n"
                if attr.fget.__module__ == 'pymeasure.instruments.common_base' and \
                   attr.fget.__defaults__ is not None and \
                   attr.fset.__defaults__ is not None:
                    help_str += 8*" " + \
                        f"fget='{attr.fget.__defaults__[0]}', " \
                        f"fset='{attr.fset.__defaults__[0]}', " \
                        f"values={attr.fget.__defaults__[1]}\n\n"

        return help_str if return_str else print(help_str)

    @staticmethod
    def setup_adapter(
        instrument: type[AnyInstrument],
        adapter: str | None = None,
        debug: bool = False,
        **kwargs
    ) -> AnyInstrument | 'DebugInstrument':
        """Sets up the adapter for the given instrument class. If the setup fails,
        it raises an exception, unless debug mode is enabled (-d flag), in which
        case it replaces the adapter with a FakeAdapter. Returns the instrument
        without saving it in the dictionary.

        :param instrument: The instrument class to set up.
        :param adapter: The adapter to use for the communication.
        :param debug: Flag indicating whether to use the DebugInstrument as a fallback.
        :param kwargs: Additional keyword arguments to pass to the instrument class.
        :return: The instrument object.
        """
        try:
            instance = instrument(adapter=adapter, **kwargs)
        except Exception as e:
            if debug:
                log.warning(
                    f"Could not connect to {instrument.__name__}: {e} Using DebugInstrument."
                )
                instance = DebugInstrument(**kwargs)
            else:
                raise

        return instance

    def connect(
        self,
        instrument: type[AnyInstrument],
        adapter: str | None,
        name: str | None = None,
        includeSCPI: bool | None = False,
        _instance_id: str | None = None,
        **kwargs
    ) -> AnyInstrument | 'DebugInstrument' | Instrument:
        """Connects to an instrument and saves it in the dictionary.

        :param instrument: The instrument class to set up.
        :param adapter: The adapter to use for the communication. If None, the result
            depends on the instrument class.
        :param name: The name of the instrument.
        :param includeSCPI: Flag indicating whether to include SCPI commands. If None,
            it uses the default value.
        :param _instance_id: A unique identifier. If not provided, it uses the class name
            and adapter.
        :param kwargs: Additional keyword arguments to pass to the instrument class.
        """
        if not _instance_id:
            _instance_id = self.id_template.format(instrument=instrument, adapter=adapter)

        if _instance_id not in self:
            if name is not None:
                kwargs['name'] = name

            if includeSCPI is not None:
                kwargs['includeSCPI'] = includeSCPI

            try:
                instance = self.setup_adapter(instrument, adapter=adapter, **kwargs)
                self[_instance_id] = instance
                log.debug(
                    f"Connected '{_instance_id}' as {instrument.__name__} via {instance.adapter}"
                )

            except Exception as e:
                log.error(f"Failed to connect to instrument '{_instance_id}': {e}")
                raise

        else:
            log.info(f"Instrument '{_instance_id}' already exists.")

        return self[_instance_id]

    def shutdown(self, instance_id: str):
        """Safely shuts down the instrument with the given id.

        :param instance_id: The id of the instrument to shutdown.
        """
        if instance_id not in self:
            log.warning(f"Instrument '{instance_id}' not found for shutdown.")
            return

        try:
            if not isinstance(self[instance_id].adapter, FakeAdapter):
                self[instance_id].shutdown()
            del self[instance_id]
            log.debug(f"Instrument '{instance_id}' was shut down.")
        except Exception as e:
            log.error(f"Error shutting down instrument '{instance_id}': {e}")

    def shutdown_all(self):
        """Safely shuts down all instruments."""
        if not self:
            log.info("No instruments to shut down")
            return

        log.info("Shutting down all instruments.")
        for instance_id in list(self):
            self.shutdown(instance_id)

    def items(self) -> Iterator[tuple[str, Instrument]]:
        return self.instances.items()

    def __getitem__(self, key: str) -> Instrument:
        return self.instances[key]

    def __setitem__(self, key: str, value: Instrument):
        if key in self:
            raise KeyError(f"Instrument '{key}' already exists. Cannot overwrite.")
        else:
            self.instances[key] = value

    def __delitem__(self, key: str):
        del self.instances[key]

    def __contains__(self, key: str) -> bool:
        return key in self.instances

    def __iter__(self) -> Iterator[str]:
        return iter(self.instances)

    def __bool__(self) -> bool:
        return bool(self.instances)

    def __len__(self) -> int:
        return len(self.instances)

    def __repr__(self) -> str:
        return f"InstrumentManager({self.instances})"


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

    # Clicker
    CT: int = 0
    TT: int = 0
    gone: bool = False

    def __init__(self, name="Debug instrument", **kwargs):
        super().__init__(name=name, **kwargs)
        self._tstart = time.time()
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

    @property
    def data(self):
        """Temperature data."""
        return random.uniform(15., 25.), random.uniform(15., 25.), self.get_time()

    def set_target_temperature(self, value):
        """Set the target temperature."""
        self.TT = int(value)
        self.gone = False

    def go(self):
        """Go."""
        self.gone = True

    def __repr__(self):
        return "<DebugInstrument>"
