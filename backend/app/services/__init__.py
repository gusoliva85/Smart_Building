"""Logica de negocio pura: sin HTTP y sin ORM.

Es la convencion central del proyecto. Cada regla no trivial se escribe y se
prueba aca ANTES de modelar la tabla que la usa, de modo que se pueda probar
con pytest en milisegundos y sin fixtures.

Un servicio no importa modelos: recibe lo que necesita por duck typing (pide
\"algo que tenga .prioridad\", no un Reclamo). La unica excepcion son las pocas
funciones que por su naturaleza necesitan consultar la base; esas reciben una
Session por parametro y se documentan como excepcion en su propio archivo.
"""
