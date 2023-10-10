# Short protocol
## For each wavelength:

0. Calibration
1. IVg Off all the chip  
2. IVg On after 1 min On, 7.5 $\mu W$
3. 10 minutes wait since LED Off
4. IVg Off, find DP 
5. It + DP, Sequence Power

        for power in Powers:
            It DP + 2
6. Vg Off, find DP
7. It - DP, Sequence gate -> Sequence Power

        for gate in [-2,-15]:
            for power in Powers:
            It DP + gate
8. IVg Off all the chip  