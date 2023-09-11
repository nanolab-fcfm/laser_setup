### Protocolo de mediciones con LED
#### Actualizado al 14-08-2023
---

Deltas respecto al DP: -30, -15, -2, +2 [V] 
> -30 y -15 es solo para comparar contra muestra sin ALD

### Importante: Para los chips Miguel 8 y 9. Antes y despúes de medir con Luz se debe medir todo el chip.

0. Tener LEDs calibrados para obtener voltajes para una potencia dada.
1. IVg apagado.
2. Prender LED por 5 minutos.
3. IVg prendido.
4. IVg apagado de inmediato.
5. Esperar 30 minutos.
6. IVg apagado y encontrar DP.
    + En caso de haber dos DP, usar el promedio.
7. It para Vg = DP + Delta elegido.
8. IVg apagado.
9. Esperar 30 minutos.
10. IVg apagado

#### Observaciones:
+ Luego de correr `setup_adapters` cerciorarse con el primer IVg que las tenmas estén bien configuradas.
+ Se recomienda no prender el LED hasta después del primer IVg apagado, ajustando el foco y posición con 0.1 [V] en la tenma_laser sólo antes del paso 2. Sacar una foto de esto para calcular la potencia efectiva. 


LED Calibrations for Tom Setup

| $\lambda$ (nM) | Voltage at $10\mu W$ (V) | Voltage at $15\mu W$ (V) | Voltage at $20\mu W$ (V) |
|:--------------:|:------------------------:|:------------------------:|:------------------------:|
|       625      |           2.66           |           3.90           |           n.a.           |
|       565      |           1.65           |           2.51           |           3.41           |
|       505      |           1.74           |           2.60           |           3.51           |
|       455      |           1.34           |           1.96           |           2.60           |
