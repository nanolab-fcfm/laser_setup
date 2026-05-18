import logging
import time

from pymeasure.experiment import FloatParameter

from .VVg import VVg, voltage_sweep_ramp

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class VVgCooldown(VVg):
    """This procedure runs multiple VVg sweeps with an "inter-sweep wait" between them, where the Keithley and Tenmas are shut down."""

    name = "V vs Vg (Cooldown)"

    inter_sweep_wait = FloatParameter(
        "Inter-sweep wait", units="s", default=60.0, minimum=0.0
    )

    INPUTS = VVg.INPUTS + ["inter_sweep_wait"]

    def startup(self):
        self.connect_instruments()
        self._initialize_instruments()

    def _initialize_instruments(self) -> None:
        self.meter.reset()
        self.meter.make_buffer()
        self.meter.apply_current(compliance_voltage=self.Vrange * 1.1 or 0.1)
        self.meter.measure_voltage(
            voltage=self.Vrange, nplc=self.NPLC, auto_range=not bool(self.Vrange)
        )

        self.tenma_neg.apply_voltage(0.0)
        self.tenma_pos.apply_voltage(0.0)
        self.tenma_laser.apply_voltage(0.0)

        self.meter.enable_source()
        time.sleep(0.5)
        self.tenma_neg.output = True
        self.tenma_pos.output = True
        self.tenma_laser.output = True
        time.sleep(1.0)

    def _prepare_sweep(self) -> None:
        self.meter.clear_buffer()
        self.meter.source_current = self.ids

        if self.laser_toggle:
            self.tenma_laser.voltage = self.laser_v
            log.info(
                f"Laser is ON. Sleeping for {self.burn_in_t} seconds to let the current stabilize."
            )
            time.sleep(self.burn_in_t)

    def _shutdown_between_sweeps(self) -> None:
        log.info("Shutting down instruments between sweeps")

        try:
            self.meter.source_current = 0.0
        except Exception as exc:
            log.warning("Failed to zero Keithley source current: %s", exc)

        try:
            self.meter.disable_source()
        except Exception:
            pass

        for supply in (self.tenma_neg, self.tenma_pos, self.tenma_laser):
            try:
                supply.apply_voltage(0.0)
                supply.output = False
            except Exception:
                pass

    def execute(self):
        log.info(f"Starting the measurement with {self.n_sweeps} sweep(s)")

        self.vg_ramp = voltage_sweep_ramp(self.vg_start, self.vg_end, self.vg_step)
        total_points = len(self.vg_ramp) * self.n_sweeps

        type(self).DATA[0] = list(self.vg_ramp)

        t_start = time.time()

        for sweep_num in range(self.n_sweeps):
            if self.should_stop():
                log.warning("Measurement aborted")
                break

            self._prepare_sweep()
            log.info(f"Starting sweep {sweep_num + 1} of {self.n_sweeps}")

            for i, vg in enumerate(self.vg_ramp):
                if self.should_stop():
                    log.warning("Measurement aborted")
                    break

                point_index = sweep_num * len(self.vg_ramp) + i
                self.emit("progress", 100 * point_index / total_points)

                self.tenma_neg.voltage = -vg * (vg < 0)
                self.tenma_pos.voltage = vg * (vg >= 0)

                time.sleep(self.step_time)

                _, voltage = self.meter.get_data()
                elapsed_time = time.time() - t_start
                temperature_data = self.temperature_sensor.data

                type(self).DATA[1].append(voltage)
                self.emit(
                    "results",
                    dict(
                        zip(
                            self.DATA_COLUMNS,
                            [
                                vg,
                                type(self).DATA[1][-1],
                                elapsed_time,
                                *temperature_data,
                                sweep_num + 1,
                            ],
                        )
                    ),
                )

            if self.should_stop():
                break

            if sweep_num < self.n_sweeps - 1:
                self._shutdown_between_sweeps()
                if self.inter_sweep_wait > 0:
                    log.info(
                        f"Waiting {self.inter_sweep_wait} seconds before the next sweep."
                    )
                    time.sleep(self.inter_sweep_wait)
                self._initialize_instruments()
