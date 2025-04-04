"""Manages adapter connections to instruments."""
import logging
from pathlib import Path
from typing import Mapping

import pyvisa

from ..config import CONFIG, save_yaml
from ..config.defaults import DefaultPaths, InstrumentConfig

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def get_idn(adapter: str, rm: pyvisa.ResourceManager) -> str | None:
    """Returns the IDN of the device connected to the adapter.
    If no device is connected, returns None.
    """
    try:
        res = rm.open_resource(adapter)
        try:
            return res.query('*IDN?')[:-1]
        except pyvisa.Error as e:
            log.error(f"Error querying *IDN? from {adapter}: {e}")
            return
        finally:
            res.close()
    except pyvisa.VisaIOError as e:
        log.error(f"Visa IO Error: {e}")
        return


def match_idn(
    idn: str, devices: Mapping[str, InstrumentConfig], strict=True
) -> str | None:
    """Checks for matching IDN strings for all device.IDN
    in the devices dictionary.
    If strict is True, checks for exact match. Otherwise, checks for
    substring match.

    :param idn: IDN string to match against
    :param devices: Dictionary of devices to match against
    :param strict: If True, checks for exact match. Otherwise, checks for
        substring match.
    :return: The key of the matching device in the devices dictionary, or None
        if no match is found.
    """

    def match(idn: str, device_idn: str) -> bool:
        if strict:
            return idn == device_idn
        else:
            return idn in device_idn or device_idn in idn

    for key, device in devices.items():
        if match(idn, device.IDN):
            return key

    return None


def setup(parent=None, visa_library: str = '') -> None:
    save_path = Path(CONFIG.Dir.instruments_file)
    if save_path == DefaultPaths.instruments:
        log.error(
            "Cannot save to default instruments file. "
            "Define a config[Dir][instruments_file] in your config file."
        )

    save_path.parent.mkdir(parents=True, exist_ok=True)

    rm = pyvisa.ResourceManager(visa_library=visa_library)
    resources = rm.list_resources()
    devices = CONFIG.instruments
    missing_ports = []
    missing_devices = [*devices]

    for res in resources:
        if not (idn := get_idn(res, rm)):
            log.warning(f"No device found at {res}.")
            missing_ports.append(res)
            continue

        if not (key := match_idn(idn, devices, False)):
            log.info(f"Device with IDN '{idn}' exists in port '{res}' but is not in config.")
            missing_ports.append(res)
            continue

        devices[key].adapter = res
        missing_devices.remove(key)
        log.info(f"Device {key} found at {res}.")

    log.info(f"Missing devices: {missing_devices}")
    log.info(f"Missing ports: {missing_ports}")
    log.info(f"Saving instrument configuration to {save_path}.")
    save_yaml(devices, save_path)
