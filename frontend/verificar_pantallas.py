# -*- coding: utf-8 -*-
"""Verificacion estatica de las pantallas. Se corre a mano, sin dependencias.

    python verificar_pantallas.py              # todas las pantallas
    python verificar_pantallas.py financiero   # una sola
    python verificar_pantallas.py --probar     # se prueba a si mismo

============================================================================
PARA QUE SIRVE
============================================================================

Para los errores de frontend que **no fallan**: no hay excepcion, no hay nada
en la consola, la pantalla simplemente se ve mal. Son los mas caros, porque hay
que darse cuenta mirando, y el que los escribio es el que menos los ve.

Los siete chequeos salieron de errores reales de este proyecto. Tres de ellos
los cometi en la misma pantalla, el mismo dia, y son el mismo error de fondo:
**usar una clase por su nombre sin leer el CSS.**

  1. Toda clase usada esta definida en `components.css`. Una clase inventada no
     falla: no se ve.
  2. Todo `window.Modulo.metodo()` existe de verdad en el modulo que lo expone.
  3. Todo `#id` y `[data-...]` que busca el JS existe en el HTML.
  4. **Ninguna clase se usa sola si en las pantallas aprobadas va siempre
     acompaniada.** `.boton-secundario` es un MODIFICADOR sobre
     `.boton-primario`; sola no tiene ningun estilo de base. Lo mismo
     `.icon-btn-sm` sobre `.icon-btn`, y `.modal` necesita `.shell` para tener
     superficie. **Este chequeo encontro un tercer boton mal que no habia
     visto, y despues un boton de cerrar que no estaba escrito como los otros.**
  5. Hay tantos lugares que abren un modal como modales declarados. Un
     `.modal-backdrop` nace en `opacity:0; pointer-events:none`: sin la clase
     `.abierto` se abre invisible y sin recibir clics. Era "el boton que no hace
     nada".
  6. Un `.boton-primario` fuera de un formulario lleva `.boton-chico` o un
     contenedor que lo encoja. Nace con `width:100%`, asi que sin eso queda del
     ancho de la pantalla. Era "el boton ENORME".
  7. Las clases que son listas (`list-style`, contador) se usan en `<ol>` o
     `<ul>`. `.bloque-lista` parece un encabezado por el nombre y es una lista
     numerada.

============================================================================
LO QUE NO HACE
============================================================================

No reemplaza abrir la pantalla en el navegador. No sabe nada de como se ve, de
los dos temas, de los tres anchos ni de la consola: el checklist de pantalla
nueva (seccion 12 del Documento de Frontend) sigue siendo a mano. Esto ataja la
clase de error que se puede ver sin ejecutar nada.

============================================================================
EL MODO --probar, Y POR QUE EXISTE
============================================================================

Un verificador que no se prueba es un verificador que dice que todo esta bien.
**Cuatro de estos chequeos no funcionaron en alguna de sus versiones** y lo
descubrio este modo, no el navegador: dos por expresiones regulares mal
escritas, uno por confundir una clase base con su modificador, y uno por
preguntar "¿aparece alguna vez?" cuando la pantalla ya tenia dos modales.

Los bugs se inyectan en memoria: no se toca ningun archivo del proyecto.
"""

import io
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))

# Las pantallas de referencia: su markup ya se reviso en el navegador y se
# aprobo, asi que define que combinaciones de clases son las correctas. **El
# chequeo 4 aprende de aca y no de una lista escrita a mano.**
APROBADAS = ['usuarios.html', 'edificios.html']

# Cada pantalla con su JavaScript. Una pantalla puede tener mas de un archivo.
PANTALLAS = {
    'usuarios': ('usuarios.html', ['usuarios.js']),
    'edificios': ('edificios.html', ['edificios.js', 'edificio-detalle.js']),
    'financiero': ('financiero.html', ['financiero.js']),
}

# Los modulos compartidos y su archivo, para el chequeo 2.
MODULOS = {
    'Api': 'api.js',
    'Cargando': 'cargando.js',
    'Confirmar': 'confirmar.js',
    'Copiar': 'copiar.js',
    'Formularios': 'formularios.js',
    'Layout': 'layout.js',
    'Mapa': 'mapa.js',
    'Moneda': 'moneda.js',
    'MontoInput': 'monto-input.js',
    'Tema': 'theme.js',
    'ViewSwitch': 'view-switch.js',
}


def leer(ruta):
    return io.open(os.path.join(AQUI, ruta), encoding='utf-8').read()


def sin_comentarios_css(texto):
    return re.sub(r'/\*.*?\*/', '', texto, flags=re.S)


def sin_comentarios_js(texto):
    return re.sub(r'/\*.*?\*/', '', texto, flags=re.S)


def atributos_de_clase(html, js):
    """Los atributos `class` del HTML y los que el JS escribe con innerHTML.

    Del JS se toma **solo la parte literal**: el markup que arma una pantalla
    suele ser `class="fila-hija ' + (algo ? 'a' : 'b') + '"`, y leer eso entero
    daba como "clases" los pedazos de la expresion (`?`, `:`, `===`). Eran
    todos falsos positivos, y una herramienta que grita en falso se deja de
    mirar. Se corta en la primera comilla simple o en el primer `+`.
    """
    encontrados = re.findall(r'class="([^"]+)"', html)

    for crudo in re.findall(r'class=\\?"([^"\\]*)', js):
        corte = len(crudo)
        for marca in ("'", '+'):
            donde = crudo.find(marca)
            if donde != -1:
                corte = min(corte, donde)
        literal = crudo[:corte].strip()
        if literal:
            encontrados.append(literal)

    return encontrados


def clases_de(atributos):
    sueltas = set()
    for atributo in atributos:
        for clase in atributo.split():
            if clase:
                sueltas.add(clase)
    return sueltas


# ===========================================================================
# LOS CHEQUEOS
#
# Cada uno recibe texto y devuelve una lista de problemas. Trabajan sobre
# cadenas y no sobre archivos: asi el modo --probar puede inyectar un bug en
# memoria **sin tocar ningun archivo del proyecto**.
# ===========================================================================


def chequeo_1_clases_definidas(html, js, css):
    definidas = set(re.findall(r'\.([a-z][a-z0-9-]*)', sin_comentarios_css(css)))
    usadas = clases_de(atributos_de_clase(html, sin_comentarios_js(js)))
    faltan = sorted(c for c in usadas if c not in definidas)
    if faltan:
        return ['clases usadas y NO definidas en components.css: %s' % faltan]
    return []


def chequeo_2_modulos(js, fuentes_de_modulos):
    problemas = []
    limpio = sin_comentarios_js(js)

    for modulo, fuente in sorted(fuentes_de_modulos.items()):
        usados = sorted(set(
            re.findall(r'window\.' + modulo + r'\.([A-Za-z_]+)', limpio)
        ))
        if not usados:
            continue

        inicio = fuente.find('window.' + modulo + ' = {')
        if inicio == -1:
            problemas.append('no se pudo leer la interfaz de window.%s' % modulo)
            continue

        # Se recorren las llaves a mano: el objeto de `Api` tiene funciones
        # adentro, asi que una expresion regular no greedy corta en la primera
        # funcion y una greedy se pasa de largo.
        desde = fuente.index('{', inicio)
        nivel = 0
        for fin in range(desde, len(fuente)):
            if fuente[fin] == '{':
                nivel += 1
            elif fuente[fin] == '}':
                nivel -= 1
                if nivel == 0:
                    break

        plano = fuente[desde + 1:fin]
        while re.search(r'\{[^{}]*\}', plano):
            plano = re.sub(r'\{[^{}]*\}', '', plano)
        expuesto = set(re.findall(r'([A-Za-z_]+)\s*:', plano))

        for metodo in usados:
            if metodo not in expuesto:
                problemas.append(
                    'usa window.%s.%s y el modulo no lo expone (expone: %s)'
                    % (modulo, metodo, sorted(expuesto))
                )
    return problemas


def chequeo_3_dom(html, js):
    problemas = []
    limpio = sin_comentarios_js(js)

    ids = set(re.findall(r'id="([^"]+)"', html))
    for ident in sorted(set(re.findall(r"\$\('#([a-z0-9-]+)'\)", limpio))):
        if ident not in ids:
            problemas.append('busca #%s y no esta en el HTML' % ident)

    # Los `data-` del HTML y tambien los que el JS escribe: muchos selectores
    # apuntan a filas que el propio JS dibuja.
    datos = set(re.findall(r'(data-[a-z-]+)', html))
    datos |= set(re.findall(r'(data-[a-z-]+)=', limpio))
    for dato in sorted(set(re.findall(r"\[(data-[a-z-]+)[\]=]", limpio))):
        if dato not in datos:
            problemas.append('busca [%s] y no esta en el HTML' % dato)

    return problemas


def companias_aprobadas(htmls_aprobados):
    """Con quien aparece SIEMPRE cada clase en las pantallas ya aprobadas."""
    siempre_con = {}
    for fuente in htmls_aprobados:
        fuente = re.sub(r'<!--.*?-->', '', fuente, flags=re.S)
        for atributo in re.findall(r'class="([^"]+)"', fuente):
            combo = set(atributo.split())
            for clase in combo:
                otras = combo - {clase}
                if clase in siempre_con:
                    siempre_con[clase] &= otras
                else:
                    siempre_con[clase] = set(otras)
    return siempre_con


def chequeo_4_clases_con_compania(html, js, siempre_con):
    problemas = []
    for atributo in atributos_de_clase(html, sin_comentarios_js(js)):
        clases = set(atributo.split())
        for clase in clases:
            for obligatoria in sorted(siempre_con.get(clase, set())):
                # **Una base no depende de su modificador.** Si la obligatoria
                # se llama como la otra mas un sufijo (`icon-btn-sm` sobre
                # `icon-btn`), es un modificador: que en las pantallas
                # aprobadas aparezcan siempre juntas no significa que la base
                # no pueda usarse sola en otro tamanio.
                if obligatoria.startswith(clase + '-'):
                    continue
                if obligatoria not in clases:
                    problemas.append(
                        '.%s se usa sola, pero en las pantallas aprobadas va '
                        'SIEMPRE con .%s (en: class="%s")'
                        % (clase, obligatoria, atributo[:55])
                    )
    return problemas


def chequeo_5_modal_se_abre_con_clase(html, js):
    if 'modal-backdrop' not in html:
        return []

    problemas = []
    limpio = sin_comentarios_js(js)

    # **Se cuenta, no se busca una sola vez.**
    #
    # Preguntar si la clase aparece "alguna vez" deja pasar el modal que se
    # olvido cuando hay dos, y eso lo descubrio el modo --probar al agregar el
    # segundo modal. Pedir el id exacto en la llamada tampoco sirve:
    # `edificios.js` guarda el elemento en una variable
    # (`pantalla.modal.classList.add(...)`) y daba dos falsos positivos.
    #
    # Contar funciona con los dos estilos: si el HTML declara tres modales,
    # tienen que haber al menos tres lugares que los abran.
    cuantos = len(re.findall(r'<div[^>]*modal-backdrop[^>]*>', html))
    aperturas = len(re.findall(r"classList\.add\('abierto'\)", limpio))

    if aperturas < cuantos:
        problemas.append(
            'el HTML declara %d modal(es) y el JS los abre en %d lugar(es): '
            'alguno va a abrirse invisible, porque .modal-backdrop nace en '
            'opacity:0 y se abre con la clase .abierto' % (cuantos, aperturas)
        )

    for etiqueta in re.findall(r'<div[^>]*modal-backdrop[^>]*>', html):
        if re.search(r'\shidden[\s>]', etiqueta):
            problemas.append(
                'un .modal-backdrop tiene `hidden`: este componente se muestra '
                'con la clase .abierto, y el hidden hace creer que alcanza con '
                'quitarlo'
            )

    return problemas


def chequeo_6_ancho_del_boton(html, css):
    limpio = sin_comentarios_css(css)
    ancho_auto = re.findall(r'\.([a-z-]+) \.boton-primario\{[^}]*width:auto', limpio)

    problemas = []
    for m in re.finditer(r'class="(boton-primario[a-z0-9 -]*)"', html):
        clases = set(m.group(1).split())
        if 'boton-chico' in clases:
            continue

        divs = re.findall(r'<div class="([a-z0-9 -]+)"', html[:m.start()])
        if not divs:
            continue
        contenedor = divs[-1].split()[0]

        # En un formulario o en la fila de acciones de un modal, el ancho
        # completo es lo correcto.
        if any(p in contenedor for p in ('form', 'modal', 'acciones')):
            continue

        if contenedor not in ancho_auto:
            problemas.append(
                'hay un .boton-primario sin .boton-chico dentro de .%s, y no '
                'existe la regla ".%s .boton-primario{width:auto}": va a '
                'ocupar todo el ancho' % (contenedor, contenedor)
            )
    return problemas


def chequeo_7_clases_de_lista(html, css):
    limpio = sin_comentarios_css(css)
    problemas = []

    # El cuerpo de la regla y nada mas, hasta su `}`. Cortar N caracteres a
    # partir del nombre se metia en las reglas siguientes: `.bloque-nota` salia
    # marcada como lista porque `.bloque-lista` esta justo debajo.
    for clase, cuerpo in re.findall(r'\.([a-z][a-z0-9-]*)\{([^}]*)\}', limpio):
        if 'counter-reset' not in cuerpo and 'list-style' not in cuerpo:
            continue
        for m in re.finditer(r'<(\w+)[^>]*class="([^"]*)"', html):
            if clase in m.group(2).split() and m.group(1) not in ('ol', 'ul'):
                problemas.append(
                    '.%s se usa en un <%s> y es una lista (tiene list-style o '
                    'contador): su contenido va en <li>, y un <div> con esta '
                    'clase queda en columna' % (clase, m.group(1))
                )
    return problemas


# ===========================================================================
# CORRER
# ===========================================================================


def verificar(html, js, css, fuentes, siempre_con):
    problemas = []
    problemas += chequeo_1_clases_definidas(html, js, css)
    problemas += chequeo_2_modulos(js, fuentes)
    problemas += chequeo_3_dom(html, js)
    problemas += chequeo_4_clases_con_compania(html, js, siempre_con)
    problemas += chequeo_5_modal_se_abre_con_clase(html, js)
    problemas += chequeo_6_ancho_del_boton(html, css)
    problemas += chequeo_7_clases_de_lista(html, css)
    return problemas


def cargar():
    css = leer('assets/css/components.css')
    fuentes = {m: leer('assets/js/' + a) for m, a in MODULOS.items()}
    siempre_con = companias_aprobadas([leer(p) for p in APROBADAS])
    return css, fuentes, siempre_con


def fuentes_de(nombre):
    archivo, scripts = PANTALLAS[nombre]
    html = leer(archivo)
    js = '\n'.join(leer('assets/js/' + s) for s in scripts)
    return html, js


def main(argumentos):
    if '--probar' in argumentos:
        return probarse()

    css, fuentes, siempre_con = cargar()
    pedidas = [a for a in argumentos if not a.startswith('-')] or sorted(PANTALLAS)

    total = 0
    for nombre in pedidas:
        if nombre not in PANTALLAS:
            print('no conozco la pantalla %r. Conozco: %s'
                  % (nombre, ', '.join(sorted(PANTALLAS))))
            return 2

        html, js = fuentes_de(nombre)
        problemas = verificar(html, js, css, fuentes, siempre_con)
        total += len(problemas)

        if problemas:
            print('%s: %d problema(s)' % (nombre, len(problemas)))
            for p in problemas:
                print('  - %s' % p)
        else:
            print('%s: ok' % nombre)

    return 1 if total else 0


# ===========================================================================
# PROBARSE
# ===========================================================================

CASOS = [
    ('una clase inventada', 'html',
     'class="lista-filas"', 'class="lista-de-gastos-linda"'),
    ('un metodo que el modulo no expone', 'js',
     'window.Moneda.pesos(', 'window.Moneda.formatearPesos('),
    ('un id que no existe', 'js',
     "$('#lista-gastos')", "$('#listado-gastos')"),
    ('el modal sin .shell', 'html',
     'class="modal modal-formulario shell"', 'class="modal modal-formulario"'),
    ('el cancelar sin .boton-primario', 'html',
     'class="boton-primario boton-secundario"', 'class="boton-secundario"'),
    ('el icono sin .icon-btn', 'js',
     'class="icon-btn icon-btn-sm" ', 'class="icon-btn-sm" '),
    ('un modal con hidden', 'html',
     '<div class="modal-backdrop" id="modal-gasto">',
     '<div class="modal-backdrop" id="modal-gasto" hidden>'),
    ('un modal que nadie abre', 'js',
     "$('#modal-expensa').classList.add('abierto');",
     "mostrar($('#modal-expensa'), true);"),
    ('el agregar sin .boton-chico', 'html',
     'class="boton-primario boton-chico"', 'class="boton-primario"'),
    ('un encabezado con .bloque-lista', 'html',
     '<div class="bloque-cabecera">', '<div class="bloque-lista">'),
]


def probarse():
    css, fuentes, siempre_con = cargar()
    html_ok, js_ok = fuentes_de('financiero')

    if verificar(html_ok, js_ok, css, fuentes, siempre_con):
        print('la pantalla financiero YA tiene problemas: arreglalos antes de '
              'probar el verificador')
        return 2

    fallos = 0
    for nombre, donde, bueno, malo in CASOS:
        html, js = html_ok, js_ok
        fuente = html if donde == 'html' else js

        if bueno not in fuente:
            print('%-38s *** no se encontro el texto a cambiar ***' % nombre)
            fallos += 1
            continue

        if donde == 'html':
            html = html.replace(bueno, malo, 1)
        else:
            js = js.replace(bueno, malo, 1)

        if verificar(html, js, css, fuentes, siempre_con):
            print('%-38s lo atrapa' % nombre)
        else:
            print('%-38s *** SE LE ESCAPA ***' % nombre)
            fallos += 1

    print()
    print('%d de %d casos atrapados' % (len(CASOS) - fallos, len(CASOS)))
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
