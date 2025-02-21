import logging
import bendev.exceptions

import bendev
from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import truncated_range, strict_discrete_set

log = logging.getLogger(__name__)


class Bentham(Instrument):
    """Communication with the Bentham (TLS120Xe) light source using
    the PyMeasure Instrument class. Replaces the adapter with a
    bendev.Device object for the communication.
    """
    wavelength_range = [280., 1100.]

    mono = Instrument.control(
        ":MONO?", ":MONO %.1f",
        """Sets the monochromator to the specified wavelength. Gets the current
        and target wavelengths in nm.""",
        validator=truncated_range,
        values=wavelength_range,
    )

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
                self.adapter = bendev.Device(serial_number=adapter)

            except bendev.exceptions.ExternalDeviceNotFound:
                if adapter is not None:
                    raise
        self.write("SYST:REM")

    def set_wavelength(self, wavelength: float, timeout: float = 10.):
        """Sets the wavelength to the specified value."""
        self.mono = wavelength
        self.move
        self.filt = wavelength
        self.move

    def read(self, timeout: float = 0, read_interval: float = 0.05) -> str:
        return self.adapter.read(timeout, read_interval)

    def query(self, command, timeout: float = 0, read_interval: float = 0.05) -> str:
        return self.adapter.query(command, timeout, read_interval)

    def shutdown(self):
        self.lamp = False
        self.reboot()
        self.adapter.close()
        super().shutdown()

    def reboot(self):
        self.adapter.write("SYSTEM:REBOOT")

    def reconnect(self):
        self.adapter.reconnect()
