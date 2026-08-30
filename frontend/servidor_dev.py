"""
Servidor estático de desarrollo para el frontend, con la caché del
navegador desactivada a propósito.

`python -m http.server` no manda ningún header de Cache-Control, así
que el navegador aplica su propia heurística de caché y a veces
reusa una copia vieja de un .js o .css en vez de pedirla de nuevo al
servidor — incluso haciendo Ctrl+F5 en algunos casos (por ejemplo,
con una página restaurada desde el "back-forward cache" del
navegador, que es exactamente lo que puede pasar al volver a entrar
a una pantalla como usuarios.html después de haber estado ahí en una
sesión anterior). Mientras el proyecto está en desarrollo y los
archivos cambian todo el tiempo, eso es justo lo que no se quiere:
por eso este servidor le agrega a CADA respuesta "no la guardes en
caché, pedila de nuevo la próxima vez".

Uso: `python servidor_dev.py [puerto]` (default 8090) — ver
README.md (raíz del proyecto) para el resto de los pasos manuales de arranque.
"""

import contextlib
import http.server
import socket


class ManejadorSinCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


# Copiado tal cual del propio `python -m http.server` (ver
# `Lib/http/server.py`, bloque `__main__`): sin este truco, el
# servidor elige UNA sola familia de direcciones (en muchas máquinas,
# IPv6) y "127.0.0.1" deja de funcionar — solo entraría por
# "localhost"/"::1". `IPV6_V6ONLY=0` hace que el mismo socket IPv6
# acepte también conexiones IPv4, que es el comportamiento normal que
# ya se esperaba (http://127.0.0.1:8090/...), igual que el resto del
# proyecto asume en `api.js` (API_BASE_URL).
class ServidorDualStack(http.server.ThreadingHTTPServer):
    def server_bind(self):
        with contextlib.suppress(Exception):
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


if __name__ == "__main__":
    import sys

    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    http.server.test(HandlerClass=ManejadorSinCache, ServerClass=ServidorDualStack, port=puerto)
