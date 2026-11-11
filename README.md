# Space Invaders - CC3501, Tarea 2

Minijuego 3D desarrollado sobre el template de la tarea. Incluye los requisitos
del enunciado y ambos extras: pausa y encendido/apagado del foco.

## Ejecución

Se necesita Python 3.11 o posterior y soporte de OpenGL 3.3.
Abra una terminal en esta carpeta y use un entorno con las bibliotecas del curso.
Si necesita instalarlas, ejecute:

```text
python -m pip install -r requirements.txt
python tarea2.py
```

También puede usar el proyecto original con `uv run tarea2.py` si tiene uv.
Los recursos se buscan respecto a los archivos del programa, por lo que también
se puede ejecutar tarea2.py indicando su ruta desde otra carpeta.

## Controles

| Tecla | Acción |
| --- | --- |
| A / flecha izquierda | Mover la nave hacia la izquierda |
| D / flecha derecha | Mover la nave hacia la derecha |
| Espacio | Disparar una bala |
| C | Alternar cámara de seguimiento y cámara cenital fija |
| P | Pausar o reanudar: se congelan nave, enemigos y balas; no se dispara |
| F | Encender o apagar el foco de la nave |
| R | Reiniciar la partida |
| Esc | Cerrar el juego |

Se gana al eliminar los 32 enemigos. Se pierde cuando cualquiera alcanza la línea
de la nave. Cada enemigo eliminado suma 100 puntos. Al terminar, se puede reiniciar
con R. La pausa no bloquea el cambio de cámara ni el interruptor del foco.

## Requisitos implementados

- Cámara en perspectiva que sigue a la nave y cámara ortográfica cenital fija.
- Nave con textura, limitada al intervalo X = [-6, 6].
- Cuatro grupos de ocho enemigos, en filas sobre el plano XZ, con cuatro sprites
  distintos del atlas original. Toda la formación se mueve entre X = -10 y 10;
  al alcanzar un extremo avanza hacia +Z y cambia de sentido.
- Balas texturizadas que nacen en la posición de la nave y viajan hacia -Z a
  velocidad constante. Una colisión elimina la bala y el primer enemigo alcanzado.
  Las balas que sobrepasan Z = -15 se eliminan.
- Foco desde la nave hacia (0, 0, -1), con producto punto y transición smoothstep
  entre 0.94 y 0.985. Se envía la posición de la nave al shader en cada dibujo.
- Luz direccional hacia (0, -1, 0), con componentes ambiental y difusa de Lambert.
- Transparencia del atlas, prueba de profundidad y descarte de píxeles transparentes.
- Ambos extras del enunciado. Además: puntaje, victoria, derrota y reinicio.

La simulación usa pasos de 1/120 s y velocidades en unidades por segundo.
El tiempo de un bloqueo de más de 0.25 s se limita para evitar un salto grande.
Las colisiones revisan el segmento recorrido por cada bala, para evitar que
atraviese un enemigo entre dos actualizaciones.

El PDF exige cuatro grupos aunque un comentario del template mencionaba dos.
Las balas se crean en la nave, siguiendo la sección 2.4 y el parámetro
ship_position de shoot; la mención a la cámara en la lista de funciones es
inconsistente con ese requisito principal.

## Archivos principales

- `tarea2.py`: ventana, escena, cámaras, controles, simulación y texto en pantalla.
- `invaders.py`: inicialización, movimiento, disparos, colisiones y estado de partida.
- `tarea2.frag`: texturas e iluminación.
- `tarea2.vert`: shader original, sin modificaciones.
- `atlas.png`, `utils/`, `grafica/`, `shaders/`: recursos y módulos originales.
- `tests/test_game.py`: pruebas de integración con ventana oculta y OpenGL real.
- `DECLARACION_USO_IA.txt`: alcance de la asistencia de IA, para revisar y
  adaptar al formato de declaración que indique el curso.

No se añadieron bibliotecas ajenas al template. requirements.txt es solamente
el subconjunto necesario para ejecutar este juego; pyproject.toml y uv.lock
conservan el entorno original del curso.

## Verificación

Desde esta carpeta:

```text
python -m unittest discover -s tests -v
```

Las pruebas requieren un contexto OpenGL, aunque no muestran una ventana.
Comprueban formación y texturas, controles, límites, rebotes, independencia de FPS,
colisiones, eliminación de balas, pausa, cámaras, victoria, derrota, reinicio y
el efecto del foco sobre los píxeles renderizados.

## Entrega

Entregar esta carpeta completa comprimida, sin entornos virtuales ni cachés.
Incluir la declaración de uso de IA con los datos y el formato que solicite el curso.
