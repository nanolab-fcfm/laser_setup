### Protocolo de calibración de potencia LEDs
#### Actualizado al 27-07-2023
---

1. Conectar el powermeter (equipo rojo de thorlabs).
2. Encontrar el adaptador del powermeter.
    + Correr el siguiente código:
    ```
    import pyvisa

    rm = pyvisa.ResourceManager()
    print(rm.list_resources())
    ```
    + Ver en _config.ini_ que el adaptador de power_meter sea el correcto.
3. Ubicar el sensor del powermeter debajo del lente, asegurandose que toda la luz del LED quede dentro del circulo interno del sensor.
4. Para cada longitud que se quiera calibrar hacer:
    + Seleccionar longitud en el powermeter apretando el botón $\lambda$ y seleccionando con OK.
    + Correr el programa de calibración `python -m Scripts.calibrate_laser`

#### Observaciones
+ Asegurarse que haya poca luz, bajar luz de las pantalles de pcs, no encender celulares, ver que la cortina esté bien cerrada.
+ El sensor hay que ubicarlo a la misma distancia en que se ubican las muestras para que la calibración sea correcta.
+ Es normal que las curvas queden planas para voltajes menores a 0.1 [V], pues es el umbral en que se prenden los LEDs.
