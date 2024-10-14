"""
Module that includes the classes for the instruments used in the experiments.
It also includes some base procedures that can be used to build more complex
procedures.
"""
import sys
import serial
import time
import logging
from typing import TypeVar, Dict
import bendev.exceptions
import numpy as np
import asyncio
import threading

import bendev
from pymeasure.adapters import FakeAdapter
from pymeasure.instruments import Instrument
from pymeasure.instruments.keithley import Keithley2450
from pymeasure.adapters import SerialAdapter
from pymeasure.instruments.thorlabs import ThorlabsPM100USB
from pymeasure.instruments.validators import truncated_range, strict_discrete_set

from .utils import SONGS

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
    def __init__(self, cls: AnyInstrument = Instrument, adapter: str = None, name: str = None, includeSCPI=False, **kwargs):
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

                    help_str += f"\tfget: '{attr.fget.__defaults__[0]}', fset: '{attr.fset.__defaults__[0]}', values={attr.fget.__defaults__[1]}\n\n"

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
            instrument = cls(adapter, **kwargs)
            log.debug(f"Connected to {cls.__name__} via {instrument.adapter}")
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

        try:
            instrument = self.setup_adapter(cls, adapter, **kwargs)
            if name in self.instances:
                log.info(f"Instrument '{name}' already exists.")
            else:
                self.instances[name] = instrument
                log.debug(f"Instrument '{name}' connected.")
            return self.instances[name]

        except Exception as e:
            log.error(f"Failed to connect to instrument '{name}': {e}")
            raise

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


class Keithley2450(Keithley2450):
    buffer_name: str = "defbuffer1"
    buffer_modes = ['CONT', 'ONCE']

    def __init__(self, adapter: str, name: str = None, includeSCPI=False, **kwargs):
        super().__init__(
            adapter, name or "Keithley 2450 SourceMeter", includeSCPI=includeSCPI, **kwargs
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

    def get_data(self):
        """Returns the latest timestamp and data from the buffer."""
        data = self.ask(f':READ? "{self.buffer_name}", REL, READ')
        return data

    def get_time(self):
        """Returns the latest timestamp from the buffer."""
        time = float(self.ask(f':READ? "{self.buffer_name}", REL')[:-1])
        return time

    def shutdown(self):
        for freq, t in SONGS['triad']:
            self.beep(freq, t)
            time.sleep(t)

        super().shutdown()


class TENMA(Instrument):
    """This class implements the communication with a TENMA instrument. It is
    a subclass of Pymeasure's Instrument class.
    """
    current = Instrument.control(
        "ISET1?", "ISET1:%.2f", """Sets the current in Amps.""",
        validator=truncated_range,
        values=[0, 1]
    )

    voltage = Instrument.control(
        "VSET1?", "VSET1:%.2f", """Sets the voltage in Volts.""",
        validator=truncated_range,
        values=[-60., 60.]
    )

    output = Instrument.control(
        "OUT1?", "OUT1:%d", """Sets the output state.""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True
    )

    timeout = Instrument.control(
        "Timeout?", "Timeout %d", """Sets the timeout in seconds."""
    )

    def __init__(self, adapter: str, name: str = None, includeSCPI=False, **kwargs):
        """Initializes the TENMA power supply instrument.

        :param adapter: The adapter to use for the communication.
        :param name: The name of the instrument.
        :param includeSCPI: Whether to include the SCPI commands in the help.
        :param kwargs: Additional keyword arguments to pass to the Instrument class
        """
        super().__init__(
            adapter, name or "TENMA Power Supply", includeSCPI=includeSCPI, **kwargs
        )

    def ramp_to_voltage(self, vg_end: float, vg_step=0.1, step_time=0.05):
        """Sets the voltage to vg_end with a ramp in V/s.

        :param vg_end: The voltage to ramp to in Volts.
        :param vg_step: The step size in Volts.
        :param step_time: The time between steps in seconds.
        """
        v = self.voltage
        while abs(vg_end - v) > vg_step:
            v += np.sign(vg_end - v) * vg_step
            self.voltage = v
            time.sleep(step_time)
        self.voltage = vg_end

    def apply_voltage(self, voltage, current=0.05, timeout=1.):
        """
        Configures the TENMA to apply a source voltage, after setting the
        compliance current and timeout.

        :param voltage: The voltage to apply in Volts.
        :param current: The compliance current in Amps.
        :param timeout: The timeout in seconds.
        """
        self.timeout = timeout
        self.current = current
        time.sleep(0.1)
        self.ramp_to_voltage(voltage)

    def shutdown(self):
        """
        Safely shutdowns the TENMA, setting the voltage to 0 and turning off
        the output.
        """
        self.ramp_to_voltage(0.)
        self.output = False
        super().shutdown()


class Bentham(Instrument):
    """Communication with the Bentham (TLS120Xe) light source using
    the PyMeasure Instrument class. Replaces the adapter with a
    bendev.Device object for the communication.
    """
    wavelength_range = [280., 1100.]

    goto = Instrument.control(
        ":MONO:GOTO?", ":MONO:GOTO? %.1f",
        """Sets new targets for all components of the monochromator and if
        successful triggers the move to the new wavelength.""",
        validator=truncated_range,
        values=wavelength_range,
    )

    wavelength = Instrument.control(
        ":MONO:WAVE?", ":MONO:WAVE %.1f",
        """Sets the wavelength in nm. Gets the current and target wavelengths in nm.""",
        validator=truncated_range,
        values=wavelength_range,
    )

    filt = Instrument.control(
        ":MONO:FILT?", ":MONO:FILT:WAVE %.1f",
        """Gets the current position of the filter wheel. Sets the filter wheel
        to a position matching the target wavelength.""",
        validator=truncated_range,
        values=wavelength_range,
    )

    bandwidth = Instrument.measurement(
        ":BAND?", """Reads the bandwidth of the current wavelength in nm."""
    )

    move = Instrument.measurement(
        ":MONO:MOVE", """Moves the monochromator to the specified wavelength."""
    )

    at_target = Instrument.measurement(
        ":OUTP:ATT?", """Checks if the monochromator is at the target wavelength."""
    )

    output = Instrument.control(
        ":OUTP?", ":OUTP %d", """Sets the output state.""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True
    )

    lamp = Instrument.control(
        ":LAMP?", ":LAMP %d", """Sets the lamp state.""",
        validator=strict_discrete_set,
        values={True: 1, False: 0},
        map_values=True
    )

    source_current = Instrument.control(
        ":SOUR:CURR?", ":SOUR:CURR %.2f", """Sets the source current in Amps.""",
        validator=truncated_range,
        values=[0., 7.2]
    )

    source_voltage = Instrument.control(
        ":SOUR:VOLT?", ":SOUR:VOLT %.2f", """Sets the source voltage in Volts.""",
        validator=truncated_range,
        values=[0., 15.]
    )

    current = Instrument.measurement(":CURR?", """Reads the current in Amps.""")

    photocurrent = Instrument.measurement(":PD?", """Reads the photocurrent in Amps.""")

    voltage = Instrument.measurement(":VOLT?", """Reads the voltage in Volts.""")

    power = Instrument.measurement(":POW?", """Reads the power in Watts.""")

    resistance = Instrument.measurement(":RES?", """Reads the resistance in Ohms.""")

    def __init__(self, adapter: str = None, name: str = None, includeSCPI=False, **kwargs):
        """Initializes the Bentham light source instrument.

        :param adapter: The adapter to use for the communication. If the adapter
            is a string or None, it replaces it with a bendev.Device object.
            Other instruments can use a self.adapter = None. However, this
            class will first try to connect to an available USB device.
        :param name: The name of the instrument.
        :param includeSCPI: Whether to include the SCPI commands in the help.
            Pymeasure instruments should have a default value of False.
        :param kwargs: Additional keyword arguments to pass to the Instrument class.
        """
        temp_adapter = None if isinstance(adapter, str) else adapter
        super().__init__(
            temp_adapter,
            name or "Bentham TLS120Xe",
            includeSCPI=includeSCPI, **kwargs
        )

        if isinstance(adapter, str) or adapter is None:
            try:
                self.adapter = bendev.Device(adapter)

            except bendev.exceptions.ExternalDeviceNotFound:
                if adapter is not None:
                    raise
        self.write("SYST:REM")

    def set_wavelength(self, wavelength: float, timeout: float = 10.):
        """Sets the wavelength to the specified value."""
        self.write(":MONO:FILT 1")
        self.move
        self.wavelength = wavelength
        self.filt = wavelength
        self.move

    def read(self, timeout: float = 0, read_interval: float = 0.05) -> str:
            return self.adapter.read(timeout, read_interval)

    def query(self, command, timeout: float = 0, read_interval: float = 0.05) -> str:
        return self.adapter.query(command, timeout, read_interval)

    def shutdown(self):
        self.adapter.close()
        super().shutdown()

    def reconnect(self):
        self.adapter.reconnect()

class PT100SerialSensor(Instrument):
    """Instrument class for the PT100 temperature sensor using PyMeasure's SerialAdapter."""

    def __init__(self, port, name="PT100 Sensor", baudrate=115200, timeout=0.15, **kwargs):
        """
        Initializes the PT100 sensor connected via serial communication.

        :param port: The serial port where the Arduino is connected (e.g., '/dev/ttyACM0').
        :param name: The name of the instrument.
        :param baudrate: The baud rate for serial communication (default: 115200).
        :param timeout: Read timeout in seconds (default: 0.05 seconds).
        :param kwargs: Additional keyword arguments.
        """
        adapter = SerialAdapter(port, baudrate=baudrate, timeout=timeout)
        # Remove 'includeSCPI' from kwargs if it exists
        kwargs.pop('includeSCPI', None)
        super().__init__(
            adapter,
            name=name,
            includeSCPI=False,
            write_termination='\n',
            read_termination='\r\n',
            **kwargs
        )
        log.info(f"{self.name} initialized on port {port} at {baudrate} baud.")
        self.clock = np.nan
        self.plate_temp = np.nan
        self.ambient_temp = np.nan
        self.data = (self.plate_temp, self.ambient_temp, self.clock)
        self.timeout = timeout  # Store the timeout in the class
        self._stop_thread = False
        self._thread = threading.Thread(target=self._get_meas)
        self._thread.daemon = True
        self._thread.start()

    def _get_meas(self):
        try:
            while not self._stop_thread:
                result = self.read_temperature()
                if result:
                    self.plate_temp, self.ambient_temp, self.clock = result
                    self.data = result
                # Very short sleep to prevent CPU overload
                time.sleep(0.001)  # Sleep for 1 millisecond
        except Exception as e:
            log.critical(f"{self.name} measurement thread failed: {e}")

    def read_temperature(self):
        """
        Reads the temperature from the PT100 sensor.

        :return: (clock, plate_temp, ambient_temp) or None if error
        """
        self.write('R')
        line = ''
        start_time = time.time()
        while True:
            # Read available data without blocking
            data = self.adapter.connection.read_all().decode('ascii', errors='ignore')
            if data:
                line += data
                if '\r\n' in line:
                    line = line.strip()
                    break
            if time.time() - start_time > self.timeout:
                return None
            time.sleep(0.001)  # Sleep briefly to prevent CPU overload
        if line == "ERROR":
            log.error("Fault detected in temperature sensor.")
            return None
        try:
            clock, plate, ambient = line.split(",")
            clock = int(clock)
            plate = float(plate)
            ambient = float(ambient)
            return plate, ambient, clock
        except ValueError:
            return None

    def shutdown(self):
        """
        Safely shuts down the serial connection.
        """
        self._stop_thread = True
        self._thread.join()
        self.adapter.disconnect()
        super().shutdown()
        log.info(f"{self.name} serial connection closed.")