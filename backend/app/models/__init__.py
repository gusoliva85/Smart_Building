"""Importar este paquete registra TODOS los modelos en `Base.metadata`.

Es lo que necesita `Base.metadata.create_all()` para crear cualquier tabla
que todavía no exista en la base real — sin este import centralizado,
`create_all()` solo crea las tablas de los modelos que alguna otra parte
del código ya haya importado por su cuenta (fue exactamente el bug que
apareció al probar el alta de edificio contra la base real: `usuarios`
existía porque `seed.py` la importaba, pero `edificios`/`pisos`/... no,
porque nada las había importado todavía en ese proceso).

Cada modelo nuevo que se agregue en una fase futura se suma acá una vez,
y automáticamente queda disponible para `main.py` y `seed.py` sin tocarlos.
"""

from app.models.usuario import Usuario  # noqa: F401
from app.models.usuario_edificio import UsuarioEdificio  # noqa: F401
from app.models.edificio import Cochera, Departamento, Edificio, EspacioComun, Piso  # noqa: F401
from app.models.gasto import Gasto  # noqa: F401
from app.models.expensa import Expensa, ExpensaDetalle  # noqa: F401
from app.models.pago import Pago  # noqa: F401
