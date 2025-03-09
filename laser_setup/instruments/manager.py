import inspect
import logging
import random
import time
from typing import Generic, Iterator, Optional, TypeVar, cast

from pymeasure.adapters import Adapter, FakeAdapter
from pymeasure.instruments import Instrument
from pymeasure.instruments.fakes import FakeInstrument

log = logging.getLogger(__name__)
T = TypeVar('T', bound=Instrument)


class InstrumentProxy(Generic[T]):
    """A proxy for an instrument that is pending initialization.

    This class holds the configuration for an instrument that will be connected
    and initialized at a later stage. It behaves like the actual instrument class
    for type checking purposes, but defers initialization until connect() is called.
    """
    def __init__(
        self,
        instrument_class: type[T],
        adapter: Optional[str | int | Adapter] = None,
        name: Optional[str] = None,
        includeSCPI: bool = False,
        **kwargs
    ):
        """Initializes the InstrumentProxy.

        :param instrument_class: The class of the instrument to be initialized.
        :param adapter: The adapter to be used for the instrument.
        :param name: The name of the instrument.
        :param includeSCPI: Flag indicating whether to include SCPI commands.
        :param kwargs: Additional keyword arguments for instrument configuration.
        """
        self.instrument_class = instrument_class
        self.adapter = adapter
        self.name = name
        self.includeSCPI = includeSCPI
        self.kwargs = kwargs
        self._instance_id = None

    def __repr__(self) -> str:
        return f"InstrumentProxy({self.instrument_class.__name__}, {self.adapter})"


class InstrumentManager:
    """Manages multiple instruments at the same time using a dictionary to store them.
    Instruments can persist between multiple instances of procedures. The manager
    can connect to and shut down instruments.

    The manager should be created as a class attribute in every procedure
    class, so that the instruments are shared between all instances of only that
    procedure.

    To use the manager, first queue the instruments in the procedure class, then
    call the connect_all method whenever you want to connect to the instruments.

    Example:

        class MyProcedure(BaseProcedure):
            instruments = InstrumentManager()
            meter: Keithley2450 = instruments.queue(Keithley2450, 'COM4')

            param = Parameter("Example parameter", default="foo")

            def startup(self):
                instruments.connect_all(self)

            def execute(self):
                ...

            def shutdown(self):
                instruments.shutdown_all()
    """
    id_template = "{instrument.__name__}/{adapter}"

    def __init__(self):
        """Initializes the InstrumentManager."""
        self.instrument_dict: dict[str, Instrument] = {}

    @staticmethod
    def help(instrument_class: type[Instrument], return_str=False) -> str | None:
        """Returns all available controls and measurements for the given
        instrument class. For each control and measurement, it shows the
        description, command sent to the instrument, and the values that
        can be set (either a range or a list of values).

        :param instrument: The instrument class to get the help from.
        :param return_str: Whether to return the help string or print it.
        """
        help_str = "Available controls and measurements for "\
            f"{instrument_class.__name__} (excluding methods):\n\n"

        for name, attr in inspect.getmembers(instrument_class, lambda x: isinstance(x, property)):
            help_str += InstrumentManager._get_property_help(attr, name)

        return help_str if return_str else print(help_str)

    def queue(
        self,
        instrument_class: type[T],
        adapter: Optional[str | int | Adapter] = None,
        name: Optional[str] = None,
        includeSCPI: bool = False,
        **kwargs
    ) -> T:
        """Queue an instrument for later connection.

        Returns a proxy that acts like the instrument for type checking purposes.
        The actual connection will be established when connect_all() is called.

        :param instrument_class: The instrument class to set up.
        :param adapter: The adapter to use for the communication.
        :param name: The name of the instrument.
        :param includeSCPI: Flag indicating whether to include SCPI commands.
        :param kwargs: Additional keyword arguments to pass to the instrument class.
        :return: A proxy object that represents the queued instrument.
        """
        proxy = InstrumentProxy(
            instrument_class=instrument_class,
            adapter=adapter,
            name=name,
            includeSCPI=includeSCPI,
            **kwargs
        )

        instance_id = self.id_template.format(instrument=instrument_class, adapter=adapter)
        proxy._instance_id = instance_id
        return cast(T, proxy)

    @staticmethod
    def setup_adapter(
        instrument_class: type[T],
        adapter: Optional[str | int | Adapter] = None,
        debug: bool = False,
        **kwargs
    ) -> T | 'DebugInstrument':
        """Sets up the adapter for the given instrument class. If the setup fails,
        it raises an exception, unless debug mode is enabled (-d flag), in which
        case it replaces the adapter with a FakeAdapter. Returns the instrument
        without saving it in the dictionary.

        :param instrument: The instrument class to set up.
        :param adapter: The adapter to use for the communication.
        :param debug: Flag indicating whether to use the DebugInstrument as a fallback.
        :param kwargs: Additional keyword arguments to pass to the instrument class.
        :return: The instrument object or a DebugInstrument if debug=True and connection fails.
        """
        try:
            instance = instrument_class(adapter=adapter, **kwargs)
        except Exception as e:
            if debug:
                log.warning(
                    f"Could not connect to {instrument_class.__name__}: {e} Using DebugInstrument."
                )
                instance = DebugInstrument(**kwargs)
            else:
                raise

        return instance

    def connect_all(self, obj: any, debug: bool = False) -> None:
        """Connects all InstrumentProxy instances in the given object.

        Searches for all InstrumentProxy attributes in the object and connects them,
        replacing the proxy with the actual instrument instance.

        :param obj: The object to search for InstrumentProxy instances.
        :param debug: Flag indicating whether to use debug mode for connection errors.
        """
        all_attrs: dict = vars(obj.__class__) | vars(obj)
        for key, attr in all_attrs.items():
            if isinstance(attr, InstrumentProxy):
                instrument = self.connect(
                    instrument_class=attr.instrument_class,
                    adapter=attr.adapter,
                    name=attr.name,
                    includeSCPI=attr.includeSCPI,
                    _instance_id=attr._instance_id,
                    debug=debug,
                    **attr.kwargs
                )
                setattr(obj, key, instrument)

    def connect(
        self,
        instrument_class: type[T],
        adapter: Optional[str | int | Adapter] = None,
        name: Optional[str] = None,
        includeSCPI: bool = False,
        _instance_id: Optional[str] = None,
        debug: bool = False,
        **kwargs
    ) -> T | 'DebugInstrument':
        """Connects to an instrument and saves it in the dictionary.

        Core method for establishing connections to instruments. If the instrument
        is already connected, it returns the existing instance.

        :param instrument_class: The instrument class to set up.
        :param adapter: The adapter to use for the communication.
        :param name: The name of the instrument.
        :param includeSCPI: Flag indicating whether to include SCPI commands.
        :param _instance_id: A unique identifier. If not provided, it uses the class name
            and adapter.
        :param debug: Flag indicating whether to use debug mode if connection fails.
        :param kwargs: Additional keyword arguments to pass to the instrument class.
        :return: The instrument instance or DebugInstrument if debug=True and connection fails.
        """
        if not _instance_id:
            _instance_id = self.id_template.format(instrument=instrument_class, adapter=adapter)

        if _instance_id not in self:
            if name is not None:
                kwargs['name'] = name

            kwargs['includeSCPI'] = includeSCPI

            try:
                instance = self.setup_adapter(
                    instrument_class, adapter=adapter, debug=debug, **kwargs
                )
                self[_instance_id] = instance
                log.debug(
                    f"Connected '{_instance_id}' as {instrument_class.__name__} "
                    f"via {instance.adapter}"
                )
            except Exception as e:
                log.error(f"Failed to connect to instrument '{_instance_id}': {e}")
                raise
        else:
            log.debug(f"Using existing instrument '{_instance_id}'")

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

    @staticmethod
    def _get_property_help(attr: property, name: str) -> str:
        """Returns the help string for a property."""
        # property_types = ("property", "control", "measurement", "setting")

        if not attr.fget.__qualname__.startswith("CommonBase.control.<locals>"):
            prop_type = "property"

        elif attr.fset.__defaults__[0] is None:
            # property doesn't have set_command
            prop_type = "measurement"

        elif attr.fget.__defaults__[0] is None:
            # property doesn't have get_command
            prop_type = "setting"

        else:
            prop_type = "control"

        help_str = f"## {name} ({prop_type}):"
        if docstring := inspect.getdoc(attr):
            help_str += f"\n{docstring.strip()}"

        if prop_type in ("measurement", "control"):
            help_str += f"\n\nGetter: '{attr.fget.__defaults__[0]}'"

        if prop_type in ("setting", "control"):
            help_str += f"\n\nSetter: '{attr.fset.__defaults__[0]}'" \
                        f"\n\nValues: {attr.fset.__defaults__[2]}"

        help_str += "\n\n"
        return help_str

    def items(self) -> Iterator[tuple[str, Instrument]]:
        return self.instrument_dict.items()

    def __getitem__(self, key: str) -> Instrument:
        return self.instrument_dict[key]

    def __setitem__(self, key: str, value: Instrument):
        if key in self:
            raise KeyError(f"Instrument '{key}' already exists. Cannot overwrite.")
        else:
            self.instrument_dict[key] = value

    def __delitem__(self, key: str):
        del self.instrument_dict[key]

    def __contains__(self, key: str) -> bool:
        return key in self.instrument_dict

    def __iter__(self) -> Iterator[str]:
        return iter(self.instrument_dict)

    def __bool__(self) -> bool:
        return bool(self.instrument_dict)

    def __len__(self) -> int:
        return len(self.instrument_dict)

    def __repr__(self) -> str:
        return f"InstrumentManager({self.instrument_dict})"


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

    def apply_voltage(self, value=0., **kwargs):
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
