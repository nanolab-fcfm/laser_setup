# Short protocol
## For each wavelength:

0. IVg Off all the chip 
1. Calibration, find led voltage for 2.5, 5.0, 7.5 and 10.0 $\mu W$
2. IVg On after 1 min On, 7.5 $\mu W$
3. 10 minutes wait since LED Off
4. IVg Off, find DP 
5. It + DP, Sequence Power

        for gate in [4, 15]:
            for power in Powers:
                It DP + gate
6. Vg Off, find DP
7. It - DP, Sequence gate -> Sequence Power

        for gate in [-4, -15]:
            for power in Powers:
                It DP + gate
8. IVg Off all the chip  