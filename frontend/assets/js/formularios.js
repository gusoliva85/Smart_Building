/* ============================================================================
   formularios.js — Comportamiento comun a TODO formulario del proyecto.

   Tres cosas, las tres nacidas de un problema real:

     1. Enter avanza de campo en vez de enviar, salvo en el ultimo. Se creo
        un edificio a medio cargar porque Enter en un campo intermedio envio
        el formulario entero. Quien carga datos usa Enter como separador,
        igual que en una planilla, y la pantalla tiene que acompanar eso.

     2. El toggle de mostrar/ocultar de los campos de contrasenia.

     3. La marca de error de un campo. El aviso del backend aparecia arriba
        del formulario y, en un formulario largo en telefono, no se veia: la
        persona apretaba "Crear edificio" y no pasaba nada visible. Ahora el
        error se marca EN el campo y la pantalla lleva el foco hasta el.

   SE ENGANCHA SOLO. Las dos cosas trabajan por delegacion en `document`, asi
   que funcionan igual en un formulario que ya estaba en el HTML y en uno que
   se inserta despues (el modal de alta, por ejemplo). Ninguna pantalla llama
   nada a mano, y no hay que acordarse de reinicializar nada al redibujar.

   No depende de config.js ni de api.js: no habla con el backend.
   ========================================================================== */

(function () {
  'use strict';

  /* Los dos iconos del toggle, como contenido INTERIOR de un <svg> ya
     existente: trazo, viewBox 24x24, extremos redondeados, como todo icono
     del proyecto. Se exponen en window.Formularios para que cualquier
     pantalla que necesite el mismo dibujo use este y no lo redibuje. */

  /* Ojo abierto: la contrasenia esta OCULTA, y el boton invita a mostrarla. */
  var ICONO_OJO =
    '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/>' +
    '<circle cx="12" cy="12" r="3"/>';

  /* Ojo tachado: la contrasenia esta VISIBLE, y el boton invita a ocultarla. */
  var ICONO_OJO_TACHADO =
    '<path d="M10.6 5.2A9.9 9.9 0 0 1 12 5c6.4 0 10 7 10 7a18.6 18.6 0 0 1-2.2 3.1"/>' +
    '<path d="M6.6 6.7A18.3 18.3 0 0 0 2 12s3.6 7 10 7a9.6 9.6 0 0 0 4.2-.9"/>' +
    '<path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>' +
    '<path d="M3 3l18 18"/>';

  /* Tipos de <input> que no son un campo para escribir: Enter sobre ellos
     tiene que hacer lo de siempre (enviar), no avanzar. */
  var TIPOS_NO_NAVEGABLES = ['submit', 'button', 'reset', 'image', 'hidden'];

  /* ------------------------------------------------- Enter avanza de campo -- */

  /**
   * Los campos de un formulario en el orden en que se recorren, ya filtrados.
   *
   * getClientRects() y NO offsetParent para descartar los invisibles: un
   * campo dentro de un contenedor con position:fixed —todo modal del
   * proyecto— tiene offsetParent nulo aunque se vea perfecto, y con ese
   * criterio la lista de un modal saldria vacia.
   */
  function camposNavegables(formulario) {
    return Array.prototype.filter.call(
      formulario.querySelectorAll('input, select, textarea'),
      function (campo) {
        if (campo.disabled || campo.readOnly) return false;
        if (TIPOS_NO_NAVEGABLES.indexOf(campo.type) !== -1) return false;
        return campo.getClientRects().length > 0;
      }
    );
  }

  function alPresionarTecla(evento) {
    if (evento.key !== 'Enter') return;

    /* Con un modificador apretado Enter significa otra cosa (Ctrl+Enter para
       enviar es una convencion extendida); no se intercepta. */
    if (evento.ctrlKey || evento.metaKey || evento.altKey || evento.shiftKey) return;

    var campo = evento.target;
    if (!campo || !campo.tagName) return;

    /* En un textarea Enter es un salto de linea y nada mas. */
    if (campo.tagName === 'TEXTAREA') return;
    if (campo.tagName !== 'INPUT' && campo.tagName !== 'SELECT') return;
    if (TIPOS_NO_NAVEGABLES.indexOf(campo.type) !== -1) return;

    var formulario = campo.form;
    if (!formulario) return;

    var lista = camposNavegables(formulario);
    var posicion = lista.indexOf(campo);

    /* En el ultimo campo Enter SI envia: es el atajo que la gente espera, y
       ahi el formulario ya esta completo. Si el campo no esta en la lista
       (quedo oculto entre medio), tampoco se toca nada. */
    if (posicion === -1 || posicion === lista.length - 1) return;

    evento.preventDefault();
    lista[posicion + 1].focus();
  }

  /* --------------------------------------------- Mostrar/ocultar contrasenia -- */

  function pintarToggle(boton, visible) {
    /* Se le pisa el innerHTML al <svg> interno, NUNCA al <button>.
       Un <button> es HTML, no SVG: su parser no reconoce <path> ni <circle>
       como elementos SVG reales fuera de un tag <svg>, los deja como
       elementos desconocidos invisibles, y el icono desaparece al primer
       clic. Fue un bug real. */
    var svg = boton.querySelector('svg');
    if (svg) svg.innerHTML = visible ? ICONO_OJO_TACHADO : ICONO_OJO;

    /* Con enie: esto no es un comentario de codigo, es la frase que lee en voz
       alta un lector de pantalla. El resto del archivo va sin acentos porque
       es codigo; los textos que escucha o lee una persona, nunca. */
    boton.setAttribute(
      'aria-label',
      visible ? 'Ocultar contraseña' : 'Mostrar contraseña'
    );
  }

  function campoDelToggle(boton) {
    var contenedor = boton.closest('.campo-password-wrap');
    return contenedor ? contenedor.querySelector('input') : null;
  }

  function alternarVisibilidad(boton) {
    var campo = campoDelToggle(boton);
    if (!campo) return;

    var mostrar = campo.type === 'password';

    /* Cambiar el type del input mueve el cursor al final. Se guarda la
       posicion antes y se restaura despues, para que alguien que toco el ojo
       en medio de la palabra siga escribiendo donde estaba. */
    var desde = campo.selectionStart;
    var hasta = campo.selectionEnd;

    campo.type = mostrar ? 'text' : 'password';
    pintarToggle(boton, mostrar);

    /* El foco vuelve al campo: el usuario toco el ojo para seguir
       escribiendo, no para quedarse en el boton. */
    campo.focus();
    try {
      if (desde !== null && hasta !== null) campo.setSelectionRange(desde, hasta);
    } catch (error) {
      /* Algun navegador no deja leer/escribir la seleccion segun el type.
         Perder la posicion del cursor no justifica cortar el toggle. */
    }
  }

  function alHacerClic(evento) {
    var destino = evento.target;
    if (!destino || !destino.closest) return;

    var boton = destino.closest('.campo-password-toggle');
    if (boton) alternarVisibilidad(boton);
  }

  /* Crea el boton del ojo en todo .campo-password-wrap que no lo tenga.

     POR QUE LO GENERA EL JAVASCRIPT Y NO LO ESCRIBE CADA HTML. La regla del
     proyecto es que TODO campo de contrasenia lleva el toggle, sin excepciones.
     Si el boton se escribe a mano, esa regla depende de que nadie se olvide
     ocho lineas de SVG, y el dia que alguien las olvida no falla nada: queda
     un campo de contrasenia sin forma de verla, que es justamente la clase de
     cosa que no se nota hasta que un usuario se queja.

     Generandolo, la regla pasa a cumplirse por construccion: alcanza con
     envolver el input en .campo-password-wrap. Ese envoltorio hace falta igual
     para el CSS, asi que no se agrega nada que no estuviera.

     Es idempotente: si el boton ya existe —porque un HTML lo trae escrito— no
     se duplica. */
  function crearTogglesFaltantes(raiz) {
    var contenedores = (raiz || document).querySelectorAll('.campo-password-wrap');

    Array.prototype.forEach.call(contenedores, function (contenedor) {
      if (contenedor.querySelector('.campo-password-toggle')) return;
      if (!contenedor.querySelector('input')) return;

      var boton = document.createElement('button');
      /* type="button" explicito: un <button> dentro de un <form> es submit por
         defecto, asi que sin esto tocar el ojo enviaria el formulario. */
      boton.type = 'button';
      boton.className = 'campo-password-toggle';
      boton.setAttribute('aria-label', 'Mostrar contraseña');

      /* El <svg> va vacio: lo llena pintarToggle, que es el unico lugar que
         sabe que icono corresponde a cada estado. */
      boton.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
        'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" ' +
        'aria-hidden="true"></svg>';

      contenedor.appendChild(boton);
    });
  }

  /* Sincroniza cada toggle con el type real de su campo. Importa porque el
     navegador restaura valores al volver atras, y porque asi el HTML de una
     pantalla puede nacer con el campo visible sin que el icono mienta.

     Primero crea los que falten: de otro modo un campo insertado despues
     —todo modal del proyecto— quedaria sin boton hasta que alguien lo escriba
     a mano. */
  function sincronizarToggles(raiz) {
    crearTogglesFaltantes(raiz);

    var botones = (raiz || document).querySelectorAll('.campo-password-toggle');
    Array.prototype.forEach.call(botones, function (boton) {
      var campo = campoDelToggle(boton);
      if (campo) pintarToggle(boton, campo.type !== 'password');
    });
  }

  /* ================================================================= */
  /* 3. LA MARCA DE ERROR DE UN CAMPO                                   */
  /* ================================================================= */

  /* El problema que resuelve, dicho por el usuario: el aviso del backend
     aparecia arriba del formulario y, en un formulario largo en telefono,
     **nunca se veia**. Apretaba "Crear edificio" y no pasaba nada visible.

     Ahora el error se marca en el campo: borde critico, anillo, una cruz
     adentro y la frase debajo. Y la pantalla lleva el foco al primero, que es
     lo que resuelve el caso del telefono — no hay que buscar nada.

     La frase la manda el backend. Desde `F1-T29` cada error de validacion
     viene con un objeto `campos` —`{"cp": "El código postal necesita al menos
     3 caracteres."}`— asi que esta funcion no redacta nada: solo lo ubica
     donde corresponde.

     SE ENGANCHA SOLO: la estructura (el envoltorio que posiciona la cruz, la
     cruz, el parrafo) la crea el JavaScript, igual que el ojo de las
     contrasenias. Un formulario no necesita mas que tener sus campos dentro de
     un `.campo` con su `name`. Si hubiera que escribirla a mano en cada HTML,
     la regla dependeria de que nadie se olvide — y olvidarse no falla, deja un
     campo sin marcar, que es el bug que esto viene a arreglar. */

  var ICONO_ALERTA =
    '<circle cx="12" cy="12" r="9"/>' +
    '<path d="M12 8v4M12 16h.01"/>';

  var ICONO_CRUZ = '<path d="M6 6l12 12M18 6L6 18"/>';

  function svgChico(contenido, ancho) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
           'stroke-width="' + ancho + '" stroke-linecap="round" ' +
           'stroke-linejoin="round" aria-hidden="true">' + contenido + '</svg>';
  }

  /* El control de un campo, buscado por `name` y, si no, por `data-campo`.

     Los dos hacen falta: los formularios escritos en el HTML usan `name`, y el
     modal generico de la estructura arma sus campos desde una descripcion y
     los marca con `data-campo`. */
  function controlDe(formulario, nombre) {
    if (!formulario || !nombre) return null;
    return (
      formulario.querySelector('[name="' + nombre + '"]') ||
      formulario.querySelector('[data-campo="' + nombre + '"]')
    );
  }

  /* El `.campo` que contiene a ese control. Es donde va la clase de error. */
  function bloqueDe(control) {
    return control && control.closest ? control.closest('.campo') : null;
  }

  /* Envuelve el control para poder posicionar la cruz, si no lo esta ya.

     Hace falta un contenedor con `position:relative` y no se puede usar el
     `.campo`, que tiene el label adentro: la cruz quedaria centrada entre el
     label y el campo. */
  function asegurarEnvoltorio(control) {
    var padre = control.parentNode;
    if (padre && padre.classList && padre.classList.contains('campo-control')) {
      return padre;
    }
    if (padre && padre.classList && padre.classList.contains('campo-password-wrap')) {
      /* El campo de contrasenia ya tiene su propio envoltorio posicionado y el
         boton del ojo ocupa la derecha: ahi no se agrega la cruz. */
      return padre;
    }
    var envoltorio = document.createElement('div');
    envoltorio.className = 'campo-control';
    padre.insertBefore(envoltorio, control);
    envoltorio.appendChild(control);
    return envoltorio;
  }

  function marcarUnCampo(formulario, nombre, frase) {
    var control = controlDe(formulario, nombre);
    if (!control) return null;

    var bloque = bloqueDe(control);
    if (!bloque) return null;

    var envoltorio = asegurarEnvoltorio(control);
    bloque.classList.add('con-error');

    /* La cruz, solo si el envoltorio no tiene ya algo a la derecha (el ojo de
       una contrasenia). */
    if (
      !envoltorio.querySelector('.campo-marca') &&
      !envoltorio.querySelector('.campo-password-toggle')
    ) {
      var marca = document.createElement('span');
      marca.className = 'campo-marca';
      marca.innerHTML = svgChico(ICONO_CRUZ, 2.4);
      envoltorio.appendChild(marca);
    }

    /* El parrafo con la frase. Se reusa si ya existe, asi dos errores seguidos
       en el mismo campo no acumulan dos parrafos. */
    var aviso = bloque.querySelector('.campo-error');
    if (!aviso) {
      aviso = document.createElement('p');
      aviso.className = 'campo-error';
      aviso.innerHTML = svgChico(ICONO_ALERTA, 2.2) + '<span></span>';
      bloque.appendChild(aviso);
    }
    aviso.querySelector('span').textContent = frase;

    /* Para quien usa un lector de pantalla, la relacion entre el campo y su
       error tiene que estar declarada: sin esto el aviso se lee como un texto
       suelto en algun lugar de la pagina. */
    if (!aviso.id) {
      aviso.id =
        'error-de-' + nombre.replace(/[^a-zA-Z0-9_-]/g, '-') + '-' +
        Math.random().toString(36).slice(2, 7);
    }
    control.setAttribute('aria-invalid', 'true');
    control.setAttribute('aria-describedby', aviso.id);

    return control;
  }

  function limpiarUnCampo(bloque) {
    bloque.classList.remove('con-error');

    var marca = bloque.querySelector('.campo-marca');
    if (marca) marca.parentNode.removeChild(marca);

    var aviso = bloque.querySelector('.campo-error');
    if (aviso) aviso.parentNode.removeChild(aviso);

    var controles = bloque.querySelectorAll('input, select, textarea');
    Array.prototype.forEach.call(controles, function (control) {
      control.removeAttribute('aria-invalid');
      control.removeAttribute('aria-describedby');
    });
  }

  /**
   * Borra todas las marcas de error de un formulario.
   *
   * Se llama al empezar a guardar: si no, un campo que se corrigio seguiria
   * marcado al lado de otro que sigue mal.
   */
  function limpiarErrores(formulario) {
    if (!formulario) return;
    var bloques = formulario.querySelectorAll('.campo.con-error');
    Array.prototype.forEach.call(bloques, limpiarUnCampo);
  }

  /**
   * Marca los campos que el backend rechazo.
   *
   * @param {HTMLFormElement} formulario
   * @param {object} campos `{nombre_del_campo: "la frase"}` — es tal cual lo
   *   que devuelve el backend en el campo `campos` de un error.
   * @returns {number} cuantos campos se pudieron marcar. Quien llama lo usa
   *   para decidir si ademas muestra el aviso general: un error que no
   *   corresponde a ningun campo visible —"ya existe un edificio con ese
   *   nombre", un fallo de red— no se puede marcar en ninguna parte y tiene
   *   que seguir mostrandose arriba.
   */
  function marcarErrores(formulario, campos) {
    limpiarErrores(formulario);
    if (!formulario || !campos) return 0;

    var primero = null;
    var marcados = 0;

    Object.keys(campos).forEach(function (nombre) {
      var control = marcarUnCampo(formulario, nombre, campos[nombre]);
      if (!control) return;
      marcados += 1;
      if (!primero) primero = control;
    });

    /* EL FOCO AL PRIMERO, y es lo que resuelve el caso del telefono: el
       formulario puede ser mas largo que la pantalla, asi que no alcanza con
       marcar el campo — hay que llevar a la persona hasta el.

       `scrollIntoView` con `block:'center'` y no `'nearest'`: dentro de un
       modal con scroll propio, `nearest` deja el campo pegado al borde y el
       aviso de abajo queda cortado. */
    if (primero) {
      var bloque = bloqueDe(primero);
      if (bloque && bloque.scrollIntoView) {
        bloque.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      try {
        primero.focus({ preventScroll: true });
      } catch (error) {
        primero.focus();
      }
    }

    return marcados;
  }

  /* La marca se borra en cuanto la persona toca ese campo.

     Sin esto, el campo queda en rojo mientras se lo esta corrigiendo, que es
     justo el momento en que el rojo molesta y no informa. Va por delegacion,
     asi funciona tambien en los campos que se insertan despues. */
  function alEscribir(evento) {
    var control = evento.target;
    if (!control || !control.closest) return;
    var bloque = control.closest('.campo.con-error');
    if (bloque) limpiarUnCampo(bloque);
  }

  /* ------------------------------------------------------------- arranque -- */

  document.addEventListener('keydown', alPresionarTecla);
  document.addEventListener('click', alHacerClic);
  document.addEventListener('input', alEscribir);
  document.addEventListener('change', alEscribir);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { sincronizarToggles(); });
  } else {
    sincronizarToggles();
  }

  window.Formularios = {
    ICONO_OJO: ICONO_OJO,
    ICONO_OJO_TACHADO: ICONO_OJO_TACHADO,
    /* La marca de error por campo. Toda pantalla que guarde un formulario la
       usa: `marcarErrores(formulario, error.campos)` y, si devuelve 0, muestra
       el aviso general porque ese error no es de ningun campo. */
    marcarErrores: marcarErrores,
    limpiarErrores: limpiarErrores,
    /* Para el caso en que una pantalla inserte un campo de contrasenia y
       quiera dejar el icono coherente sin esperar al primer clic. El toggle
       ya funciona sin llamar esto. */
    sincronizarToggles: sincronizarToggles,
    crearTogglesFaltantes: crearTogglesFaltantes,
    camposNavegables: camposNavegables
  };
}());
