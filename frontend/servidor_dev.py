"""Servidor estatico de desarrollo para el frontend de SMART Building.

    python servidor_dev.py          -> http://127.0.0.1:8090
    python servidor_dev.py 9000     -> otro puerto

No necesita el entorno virtual del backend: usa solo la libreria estandar.
Levanta en una terminal aparte de la del backend; son dos procesos distintos
(ver README.md).

POR QUE NO ALCANZA CON `python -m http.server`
----------------------------------------------
Por el cache. El servidor de la libreria estandar manda cabeceras que hacen
que el navegador se quede con la copia vieja de un CSS o un JS, y entonces se
edita un archivo, se recarga, no cambia nada, y se van veinte minutos
depurando un problema que no existe. Este servidor desactiva el cache de
forma explicita en cada respuesta.
"""

import mimetypes
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PUERTO_POR_DEFECTO = 8090
DIRECTORIO = Path(__file__).resolve().parent

# En Windows, los tipos MIME salen del registro del sistema, asi que dependen
# de la maquina: hay instalaciones donde .js vuelve como "text/plain" y el
# navegador se niega a ejecutarlo. Se fuerzan los que usa el proyecto para que
# el servidor se comporte igual en cualquier maquina.
for extension, tipo in {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
}.items():
    mimetypes.add_type(tipo, extension)


class ServidorDev(ThreadingHTTPServer):
    """Servidor que SI se niega a arrancar si el puerto ya esta ocupado.

    ThreadingHTTPServer trae allow_reuse_address activado, que en Linux y
    macOS solo permite reutilizar un puerto en TIME_WAIT. En Windows, en
    cambio, deja atar un puerto que otro proceso ya tiene escuchando: se
    levantan dos servidores sobre el mismo puerto y cada peticion cae en
    cualquiera de los dos, al azar. El sintoma es desconcertante — se edita
    un archivo, se recarga y a veces cambia y a veces no, justo lo que este
    servidor existe para evitar.

    Desactivarlo en Windows hace que el segundo intento falle con un error
    claro, que es lo que corresponde.
    """

    allow_reuse_address = os.name != "nt"
    daemon_threads = True


class ManejadorSinCache(SimpleHTTPRequestHandler):
    """Sirve el frontend y prohibe explicitamente el cacheo."""

    def end_headers(self):
        # no-store es el que de verdad importa: le dice al navegador que ni
        # siquiera guarde la respuesta. Los otros dos son para intermediarios
        # y navegadores viejos que ignoran no-store.
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, formato, *args):
        # El log por defecto es ruidoso y repite fecha completa en cada linea.
        sys.stdout.write(f"  {self.log_date_time_string()}  {formato % args}\n")


def main() -> int:
    puerto = PUERTO_POR_DEFECTO
    if len(sys.argv) > 1:
        try:
            puerto = int(sys.argv[1])
        except ValueError:
            print(f"Puerto invalido: {sys.argv[1]!r}. Uso: python servidor_dev.py [puerto]")
            return 2

    manejador = partial(ManejadorSinCache, directory=str(DIRECTORIO))

    try:
        servidor = ServidorDev(("127.0.0.1", puerto), manejador)
    except OSError as error:
        # El caso habitual: quedo otra instancia levantada de antes.
        print(f"No se pudo abrir el puerto {puerto}: {error}")
        print("Probablemente ya haya un servidor corriendo ahi.")
        print(f"Cerralo, o levanta este en otro puerto:  python servidor_dev.py {puerto + 1}")
        return 1

    print(f"Frontend de SMART Building servido desde {DIRECTORIO}")
    print(f"  http://127.0.0.1:{puerto}/index.html")
    print("  Cache desactivado: cada recarga trae los archivos frescos.")
    print("  Ctrl+C para detener.\n")

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
