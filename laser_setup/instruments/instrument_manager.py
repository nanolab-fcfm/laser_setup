import sys
import logging
from typing import TypeVar, Dict

from pymeasure.adapters import FakeAdapter
from pymeasure.instruments import Instrument

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
        cls: AnyInstrument = Instrument,
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
        self.instances: Dict[str, AnyInstrument] = {}

    def __repr__(self) -> str:
        return f"InstrumentManager({self.instances})"

    @staticmethod
    def help(cls: AnyInstrument, return_str = False) -> str:
        """Returns all available controls and measurements for the given
        instrument class. For each control and measurement, it shows the
        description, command sent to the instrument, and the values that
        can be set (either a range or a list of values).

        :param cls: The instrument class to get the help from.
        :param return_str: Whether to return the help string or print it.
        """
        help_str = f"Available controls and measurements for {cls.__name__} (not including methods):\n"
        for name in dir(cls):
            try:
                attr = getattr(cls, name)
                if isinstance(attr, property):
                    if attr.fset.__doc__ is None:
                        help_str += f"    {name} (measurement): {attr.__doc__} \n"
                    else:
                        help_str += f"    {name} (control): {attr.__doc__} \n"

                    help_str += 12*" " + f"fget: '{attr.fget.__defaults__[0]}', fset: '{attr.fset.__defaults__[0]}', values={attr.fget.__defaults__[1]}\n\n"

            except Exception:
                continue

        return help_str if return_str else print(help_str)


    @staticmethod
    def setup_adapter(cls: AnyInstrument, adapter: str, **kwargs) -> AnyInstrument:
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
            instrument: AnyInstrument = cls(adapter, **kwargs)
        except Exception as e:
            if '-d' in sys.argv or '--debug' in sys.argv:
                log.warning(f"Could not connect to {cls.__name__}: {e} Using FakeAdapter.")
                instrument = cls(FakeAdapter(), **kwargs)
            else:
                raise

        return instrument

    def connect(
        self, cls: AnyInstrument, adapter: str = None, name: str = None, **kwargs
    ) -> AnyInstrument | None:
        """Connects to an instrument and saves it in the dictionary.

        :param cls: The instrument class to set up.
        :param adapter: The adapter to use for the communication. If None, the result
            depends on the instrument class.
        :param name: The name of the instrument. If None, it uses the class name
            and adapter.
        :param kwargs: Additional keyword arguments to pass to the instrument class.
        """
        if name is None:
            name = f"{cls.__name__}/{adapter}"

        if name not in self.instances:
            try:
                instrument = self.setup_adapter(cls, adapter, **kwargs)
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
