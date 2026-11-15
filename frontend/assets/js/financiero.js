/* ============================================================================
   financiero.js — la pantalla financiera (F2-T17)

   **Un archivo, dos audiencias, y el rol decide cual corre.** La vista de
   gestion es el modulo completo con sus pestañas; la del residente es "Mi
   cuenta" (`F2-T22`), que no comparte con la otra ni un pedido al backend.
   El reparto esta en `arrancar()`, al final: es el unico lugar donde se mira
   el rol, y de ahi en adelante cada rama es independiente.

   De las cinco pestañas de gestion falta Fondos, que es `F2-T21` y cambia un
   `false` por `true` en la tabla de abajo.

   ============================================================================
   LA TABLA DE PESTAÑAS — MISMO PATRON QUE LA TABLA ACCESOS DE layout.js
   ============================================================================

   Declara las cinco pestañas del modulo, para que el archivo se lea como el
   plan completo, y **dibuja solo las construidas**.

   Es la resolucion de una contradiccion real del Roadmap: `F2-T17` pide "el
   selector que organiza todo el modulo (Gastos / Expensas / Pagos / Deudores /
   Fondos) con la primera pestaña funcional", y la seccion 1.3 prohibe las
   pantallas con secciones vacias o deshabilitadas de funcionalidad futura. Una
   pestaña "Fondos" que al tocarla no muestra nada es exactamente lo que esa
   regla prohibe.

   Con el `construida` se cumplen las dos cosas, y es el mecanismo que el
   proyecto ya usa para el menu lateral.

   ============================================================================
   ESTA PANTALLA NO SUMA PLATA. NUNCA.
   ============================================================================

   Todos los totales vienen calculados del backend. El total de un periodo es
   el numero que despues se reparte entre las unidades, asi que tiene que salir
   del mismo lugar del que va a salir la expensa: dos sumas hechas en dos lados
   distintos son dos numeros que algun dia no coinciden.

   `moneda.js` formatea para mostrar y nada mas.
   ========================================================================= */

(function () {
  'use strict';

  var PESTANIAS = [
    { id: 'gastos',    etiqueta: 'Gastos',    construida: true  },  /* F2-T17 */
    { id: 'expensas',  etiqueta: 'Expensas',  construida: true  },  /* F2-T18 */
    { id: 'pagos',     etiqueta: 'Pagos',     construida: true  },  /* F2-T19 */
    { id: 'deudores',  etiqueta: 'Deudores',  construida: true  },  /* F2-T20 */
    { id: 'fondos',    etiqueta: 'Fondos',    construida: false }   /* F2-T21 */
  ];

  /* Los dos roles que entran a la vista de gestion.

     Se le pasan a `Layout.montar`, que es quien resuelve el porton: si el rol
     no esta en la lista, monta el esqueleto, explica por que no puede entrar y
     **no resuelve la promesa**, asi que nada de esta pantalla se dibuja encima
     del mensaje. Por eso aca no hay ningun `if` de permisos: una pantalla que
     resuelve sus propios permisos es una pantalla que algun dia los resuelve
     distinto que las demas.

     El residente NO entra por aca: tiene su propia rama y su propia lista. */
  var ROLES_DE_GESTION = ['admin_general', 'admin_consorcio'];

  /* Los dos roles que ven "Mi cuenta" (`F2-T22`).

     **Un administrador que ademas es propietario de una unidad no entra por
     aca**, y es a proposito: su rol le abre el modulo completo, y desde la
     vista de gestion ve su propia unidad en Deudores y su propio pago en la
     cola de conciliacion. Darle las dos vistas en la misma pantalla seria
     tener que elegir cual se dibuja primero sin ningun criterio para hacerlo.
     Es el caso del administrador que vive en el edificio, el mismo que la
     regla de `F2-T07` ya tiene en cuenta por el otro lado: puede cargar su
     pago, pero no conciliarlo el mismo. */
  var ROLES_DE_MI_CUENTA = ['propietario', 'inquilino'];

  /* Cuantos años hacia atras ofrece el filtro. Tres alcanza: un consorcio
     consulta el año en curso y el anterior, y el tercero es para el que esta
     cerrando un ejercicio viejo. */
  var ANIOS_HACIA_ATRAS = 2;

  var estado = {
    rol: null,
    edificioId: null,
    rubros: [],          /* el catalogo que sirve el backend */
    editando: null,      /* el id del gasto que se esta editando, o null */
    ultimoFoco: null,    /* a donde vuelve el foco al cerrar el modal */
    expensas: [],        /* las liquidaciones, para no volver a pedirlas */
    cola: [],            /* los pagos pendientes de conciliar (F2-T19) */
    deudores: [],        /* las unidades con deuda (F2-T20) */
    rechazando: null,    /* el pago que el modal de rechazo tiene cargado */

    /* --- solo la rama del residente (F2-T22) --- */
    cuentas: [],         /* mis unidades con su estado de cuenta */
    unidadId: null,      /* la unidad que se esta mirando */
    liquidaciones: [],   /* las expensas publicadas de esa unidad */
    misPagos: [],        /* los pagos que cargue, de todas mis unidades */
    medios: []           /* el catalogo de medios de pago */
  };

  /* --------------------------------------------------------------- utiles -- */

  function $(selector) { return document.querySelector(selector); }

  function mostrar(elemento, visible) {
    if (elemento) elemento.hidden = !visible;
  }

  function texto(elemento, valor) {
    if (elemento) elemento.textContent = valor;
  }

  /* Un error se muestra DONDE ocurrio la accion: el de la pantalla arriba de
     todo, el del listado arriba de la lista que no se pudo traer, el del
     formulario adentro del modal. Es la regla del proyecto y la razon por la
     que hay tres contenedores y no uno. */
  function mostrarError(prefijo, mensaje) {
    var caja = $('#error-' + prefijo);
    texto(caja && caja.querySelector('[data-texto-error-' + prefijo + ']'), mensaje || '');
    mostrar(caja, !!mensaje);
  }

  function escapar(texto) {
    return String(texto == null ? '' : texto)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function svg(contenido) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
           'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" ' +
           'aria-hidden="true">' + contenido + '</svg>';
  }

  var ICONO_EDITAR = '<path d="M12 20h9"/>' +
    '<path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>';
  var ICONO_BORRAR = '<path d="M3 6h18"/>' +
    '<path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/>';

  var ICONO_VER = '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/>' +
    '<circle cx="12" cy="12" r="3"/>';
  var ICONO_REGENERAR = '<path d="M3 12a9 9 0 0 1 15.5-6.3L21 8"/>' +
    '<path d="M21 3v5h-5"/>' +
    '<path d="M21 12a9 9 0 0 1-15.5 6.3L3 16"/>' +
    '<path d="M3 21v-5h5"/>';
  var ICONO_PUBLICAR = '<path d="M12 19V5"/><path d="M5 12l7-7 7 7"/>';
  /* El comprobante: una hoja con una esquina doblada. No un clip, que es el
     icono universal de "adjuntar un archivo" — y acá no se adjunta nada, se
     abre un enlace a algo que vive afuera (ver 1.4 del Documento General). */
  var ICONO_COMPROBANTE = '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>' +
    '<path d="M14 3v5h5"/>';

  /* ----------------------------------------------------- las pestañas -- */

  function construirPestanias() {
    var caja = $('#pestanias-financiero');
    var construidas = PESTANIAS.filter(function (p) { return p.construida; });

    /* Con una sola pestaña construida el selector no se dibuja: un selector de
       una opcion no es un selector, es un titulo que parece un boton. Aparece
       solo cuando hay a donde ir. */
    if (construidas.length < 2) {
      mostrar(caja, false);
      mostrar(document.querySelector('[data-panel="' + construidas[0].id + '"]'), true);
      return;
    }

    caja.innerHTML = construidas.map(function (p, i) {
      return '<button type="button"' + (i === 0 ? ' class="activo"' : '') +
             ' data-vista="' + p.id + '">' + escapar(p.etiqueta) + '</button>';
    }).join('');

    mostrar(caja, true);
    mostrar(document.querySelector('[data-panel="' + construidas[0].id + '"]'), true);

    /* El clic cambia de panel. El indicador deslizante, el teclado y el
       aria-selected los maneja view-switch.js, que se engancha solo: esta
       pantalla solo escucha para mostrar y ocultar. */
    caja.addEventListener('click', function (evento) {
      var boton = evento.target.closest('button[data-vista]');
      if (!boton) return;

      PESTANIAS.forEach(function (p) {
        mostrar(document.querySelector('[data-panel="' + p.id + '"]'),
                p.id === boton.getAttribute('data-vista'));
      });
    });
  }

  /* --------------------------------------------------- el edificio activo -- */

  /* El edificio viaja en la URL. Leerlo de ahi —y no de una variable— es lo
     que hace que F5 no te saque del edificio en el que estabas. */
  function edificioDeLaUrl() {
    var valor = new URLSearchParams(window.location.search).get('edificio');
    var numero = parseInt(valor, 10);
    return numero > 0 ? numero : null;
  }

  function irAlEdificio(id) {
    var url = new URL(window.location.href);
    url.searchParams.set('edificio', id);
    /* `replaceState` y no `pushState`: cambiar de edificio con el selector no
       es navegar, y si cada cambio dejara una entrada en el historial el boton
       de atras recorreria la lista de edificios en vez de volver de donde
       vino. */
    window.history.replaceState({}, '', url);
    estado.edificioId = id;
  }

  function construirSelectorDeEdificios(edificios) {
    var campo = $('#campo-edificio');
    var selector = $('#selector-edificio');

    selector.innerHTML = edificios.map(function (e) {
      return '<option value="' + e.id + '">' + escapar(e.nombre) + '</option>';
    }).join('');

    selector.value = String(estado.edificioId);

    /* Con un solo edificio el selector no se muestra: elegir entre una opcion
       no es elegir, y ocupa una fila de la cabecera para nada. Le pasa a todo
       Administrador de Consorcio. */
    mostrar(campo, edificios.length > 1);

    /* **Al cambiar de edificio se recargan TODAS las pestañas, no la que está
       a la vista.** Hasta `F2-T19` esto solo recargaba los gastos, y el
       resultado era que el listado de liquidaciones seguía mostrando las del
       edificio anterior: en una pestaña que no se está mirando, un dato viejo
       no se nota hasta que alguien lo lee como propio del edificio nuevo. En
       una pantalla de plata eso es grave — y con la cola de pagos lo sería más,
       porque los botones de conciliar estarían apuntando a pagos de otro
       consorcio (el backend los rechazaría con un 404, pero recién al tocarlos).

       Se limpian además los avisos de éxito y error: pertenecen a lo que se
       hizo en el edificio anterior. */
    selector.addEventListener('change', function () {
      irAlEdificio(parseInt(selector.value, 10));

      mostrarError('gastos', '');
      mostrarError('expensas', '');
      mostrarError('pagos', '');
      mostrarError('deudores', '');
      mostrar($('#exito-expensas'), false);
      mostrar($('#exito-pagos'), false);

      cargarGastos();
      cargarExpensas();
      cargarPagos();
      cargarDeudores();
    });
  }

  /* ------------------------------------------------------- los filtros -- */

  function construirFiltros() {
    var hoy = new Date();
    var anioActual = hoy.getFullYear();

    var anios = [];
    for (var i = 0; i <= ANIOS_HACIA_ATRAS; i++) anios.push(anioActual - i);

    $('#filtro-anio').innerHTML = anios.map(function (a) {
      return '<option value="' + a + '">' + a + '</option>';
    }).join('');

    /* "Todo el año" es una opcion real y no un hueco: al cerrar un ejercicio se
       mira el año entero, y el backend ya acepta el año sin mes. */
    $('#filtro-mes').innerHTML =
      '<option value="">Todo el año</option>' +
      window.Moneda.MESES.map(function (nombre, indice) {
        var numero = indice + 1;
        return '<option value="' + numero + '">' +
               nombre.charAt(0).toUpperCase() + nombre.slice(1) + '</option>';
      }).join('');

    /* El filtro arranca en el mes actual, que es lo que alguien viene a mirar
       el 99% de las veces. */
    $('#filtro-anio').value = String(anioActual);
    $('#filtro-mes').value = String(hoy.getMonth() + 1);

    $('#filtros-gastos').addEventListener('change', cargarGastos);
  }

  function construirSelectoresDeRubro() {
    /* El catalogo lo sirve el backend. La pantalla **no tiene su propia copia**
       de la lista de rubros: una copia en JavaScript es la que queda vieja el
       dia que se agregue un rubro, y el sintoma seria un desplegable al que le
       falta una opcion sin que nada falle. */
    var opciones = estado.rubros.map(function (r) {
      return '<option value="' + escapar(r.nombre) + '">' +
             escapar(r.etiqueta) + '</option>';
    }).join('');

    $('#filtro-rubro').innerHTML = '<option value="">Todos los rubros</option>' + opciones;
    $('#gasto-rubro').innerHTML = opciones;

    actualizarAyudaDeRubro();
  }

  /* La descripcion del rubro elegido, abajo del desplegable. El catalogo la
     trae y sirve justo cuando alguien duda entre "mantenimiento" y
     "ascensores": la diferencia esta escrita, y ponerla a la vista evita que
     el mismo gasto se cargue en dos rubros distintos segun quien lo cargue. */
  function actualizarAyudaDeRubro() {
    var elegido = $('#gasto-rubro').value;
    var rubro = estado.rubros.filter(function (r) { return r.nombre === elegido; })[0];
    texto($('[data-ayuda-rubro]'), rubro ? rubro.descripcion : '');
  }

  /* --------------------------------------------------------- el listado -- */

  function filtrosActuales() {
    var parametros = new URLSearchParams();
    parametros.set('anio', $('#filtro-anio').value);

    var mes = $('#filtro-mes').value;
    if (mes) parametros.set('mes', mes);

    var rubro = $('#filtro-rubro').value;
    if (rubro) parametros.set('rubro', rubro);

    return parametros.toString();
  }

  function periodoElegido() {
    var mes = $('#filtro-mes').value;
    var anio = $('#filtro-anio').value;
    if (!mes) return 'todo ' + anio;
    return window.Moneda.periodoLargo(
      (mes.length === 1 ? '0' + mes : mes) + '/' + anio
    );
  }

  function htmlDeGasto(gasto) {
    /* El rubro va como `.chip` y no como `.pill`: las pills son el semaforo de
       cuatro estados del edificio, y un rubro contable no es un estado. */
    return '' +
      '<div class="fila-lista content-glass" data-gasto="' + gasto.id + '">' +
        '<div class="fila-lista-dato">' +
          '<b>' + window.Moneda.pesos(gasto.monto) + '</b>' +
          '<span>' + window.Moneda.fecha(gasto.fecha) +
            (gasto.descripcion ? ' · ' + escapar(gasto.descripcion) : '') +
          '</span>' +
        '</div>' +
        '<div class="fila-lista-acciones">' +
          '<span class="chip">' + escapar(gasto.rubro_etiqueta) + '</span>' +
          '<div class="fila-lista-botones">' +
            /* `icon-btn icon-btn-sm`, las dos: la segunda solo cambia el
               tamanio — el borde, el fondo, la sombra y el hover estan todos en
               `.icon-btn`. Es como lo escribe usuarios.js. */
            '<button type="button" class="icon-btn icon-btn-sm" ' +
                    'data-editar="' + gasto.id + '" ' +
                    'aria-label="Editar este gasto" title="Editar">' +
              svg(ICONO_EDITAR) +
            '</button>' +
            '<button type="button" class="icon-btn icon-btn-sm" ' +
                    'data-borrar="' + gasto.id + '" ' +
                    'aria-label="Borrar este gasto" title="Borrar">' +
              svg(ICONO_BORRAR) +
            '</button>' +
          '</div>' +
        '</div>' +
      '</div>';
  }

  function pintarTotal(datos) {
    var caja = $('#total-gastos');

    /* Sin gastos no se muestra un total de cero: cero y "no hay nada" son dos
       cosas distintas, y en una pantalla de plata confundirlas es como se lee
       un hueco como un mes sin gastos cuando lo que falta es cargarlos. */
    if (!datos.cantidad) {
      mostrar(caja, false);
      return;
    }

    texto(caja.querySelector('[data-total-titulo]'),
          'Total de ' + periodoElegido());
    texto(caja.querySelector('[data-total-monto]'), window.Moneda.pesos(datos.total));

    var cuantos = datos.cantidad === 1 ? '1 gasto' : datos.cantidad + ' gastos';
    caja.querySelector('[data-total-chips]').innerHTML =
      '<span class="chip">' + cuantos + '</span>';

    mostrar(caja, true);
  }

  function pintarGastos(datos) {
    var lista = $('#lista-gastos');

    if (!datos.cantidad) {
      /* El vacio explica que hacer, no dice "no hay datos". Un listado vacio
         que no sugiere el siguiente paso es una pantalla que parece rota. */
      lista.innerHTML =
        '<p class="lista-vacia">No hay gastos cargados en ' + periodoElegido() +
        '. Cargá el primero con el botón de arriba.</p>';
      return;
    }

    lista.innerHTML = datos.gastos.map(htmlDeGasto).join('');
  }

  function cargarGastos() {
    if (!estado.edificioId) return;

    var lista = $('#lista-gastos');
    lista.innerHTML = window.Cargando.html();
    mostrarError('gastos', '');
    mostrar($('#total-gastos'), false);

    return window.Api
      .get('/edificios/' + estado.edificioId + '/gastos?' + filtrosActuales())
      .then(function (datos) {
        pintarTotal(datos);
        pintarGastos(datos);
      })
      .catch(function (error) {
        lista.innerHTML = '';
        mostrarError('gastos', error.message);
      });
  }

  /* ----------------------------------------------------------- el modal -- */

  function abrirModal(gasto) {
    /* A donde vuelve el foco al cerrar. Sin esto, al cerrar con Escape el foco
       se va al <body> y el siguiente Tab arranca desde el principio de la
       pagina. */
    estado.ultimoFoco = document.activeElement;
    estado.editando = gasto ? gasto.id : null;

    var formulario = $('#formulario-gasto');
    window.Formularios.limpiarErrores(formulario);
    mostrar($('[data-aviso-gasto]'), false);

    texto($('#titulo-modal-gasto'), gasto ? 'Editar gasto' : 'Cargar gasto');
    texto($('[data-sub-modal-gasto]'), gasto
      ? 'Se corrige lo que esté mal. Lo que no cambies queda como está.'
      : 'Un gasto del consorcio en este período.');
    texto($('[data-guardar-gasto]'), gasto ? 'Guardar cambios' : 'Guardar gasto');

    if (gasto) {
      $('#gasto-rubro').value = gasto.rubro;
      window.MontoInput.escribir($('#gasto-monto'), gasto.monto);
      $('#gasto-fecha').value = gasto.fecha;
      $('#gasto-descripcion').value = gasto.descripcion || '';
    } else {
      formulario.reset();
      /* La fecha arranca en el mes que se esta mirando y no en hoy: quien
         filtra marzo y carga un gasto esta cargando un gasto de marzo. Es el
         dia 1 porque es el unico dia que existe en todos los meses. */
      var mes = $('#filtro-mes').value || String(new Date().getMonth() + 1);
      $('#gasto-fecha').value =
        $('#filtro-anio').value + '-' + (mes.length === 1 ? '0' + mes : mes) + '-01';
    }

    actualizarAyudaDeRubro();

    /* **Se abre con la clase, no con `hidden`.** El componente nace en
       `opacity:0; pointer-events:none` para poder aparecer con una transicion,
       asi que quitarle `hidden` no lo muestra: queda invisible y sin recibir
       clics. Era el bug por el que el boton "no hacia nada". */
    $('#modal-gasto').classList.add('abierto');
    $('#gasto-rubro').focus();
  }

  function cerrarModal() {
    $('#modal-gasto').classList.remove('abierto');
    estado.editando = null;
    if (estado.ultimoFoco && estado.ultimoFoco.focus) estado.ultimoFoco.focus();
  }

  function modalAbierto() {
    return $('#modal-gasto').classList.contains('abierto');
  }

  function cuerpoDelFormulario() {
    var cuerpo = {
      rubro: $('#gasto-rubro').value,
      /* El valor crudo, con punto decimal y sin separadores de miles. Mandar
         el texto del input tal cual convertiria "1.234" en mil doscientos
         treinta y cuatro pesos... o en uno con veintitres centavos. */
      monto: window.MontoInput.valorDe($('#gasto-monto')),
      fecha: $('#gasto-fecha').value
    };

    var descripcion = $('#gasto-descripcion').value.trim();
    /* En el alta, una descripcion vacia no se manda; en la edicion si, porque
       ahi `null` significa "borrala" y no mandarla significa "dejala como
       esta". Es la diferencia que hace que el PATCH sea un PATCH. */
    if (descripcion) cuerpo.descripcion = descripcion;
    else if (estado.editando) cuerpo.descripcion = null;

    return cuerpo;
  }

  function guardar(evento) {
    evento.preventDefault();

    var formulario = $('#formulario-gasto');
    var boton = $('[data-guardar-gasto]');
    window.Formularios.limpiarErrores(formulario);
    mostrar($('[data-aviso-gasto]'), false);
    boton.disabled = true;

    var base = '/edificios/' + estado.edificioId + '/gastos';
    var cuerpo = cuerpoDelFormulario();

    var pedido = estado.editando
      ? window.Api.patch(base + '/' + estado.editando, cuerpo)
      : window.Api.post(base, cuerpo);

    pedido
      .then(function (gasto) {
        /* El aviso del gasto que llega tarde: se guardo bien, pero no va a
           entrar en una liquidacion ya publicada. El modal queda abierto para
           que se lea, porque cerrarlo haria desaparecer el aviso en el mismo
           gesto. */
        if (gasto && gasto.aviso) {
          texto($('[data-texto-aviso-gasto]'), gasto.aviso);
          mostrar($('[data-aviso-gasto]'), true);
          estado.editando = gasto.id;
          texto($('#titulo-modal-gasto'), 'Gasto guardado');
          texto($('[data-guardar-gasto]'), 'Guardar cambios');
        } else {
          cerrarModal();
        }
        return cargarGastos();
      })
      .catch(function (error) {
        /* `marcarErrores` pinta en rojo cada campo que el backend señalo y
           devuelve cuantos encontro. Si no encontro ninguno, el error no es de
           un campo —un 403, un fallo de red— y se muestra en el resumen. */
        var marcados = window.Formularios.marcarErrores(formulario, error.campos);
        if (!marcados) {
          var resumen = formulario.querySelector('[data-resumen-errores]');
          texto(resumen, error.message);
          mostrar(resumen, true);
        }
      })
      .then(function () { boton.disabled = false; });
  }

  /* ---------------------------------------------------------- las bajas -- */

  function borrar(id) {
    var fila = document.querySelector('[data-gasto="' + id + '"]');
    var monto = fila ? fila.querySelector('b').textContent : '';

    /* El dialogo del sistema, nunca un `confirm()` del navegador. Y el texto
       dice QUE se borra, con su monto: "¿Borrar el gasto?" obliga a cerrar el
       dialogo para ir a mirar cual era. */
    window.Confirmar.pedir({
      titulo: 'Borrar este gasto',
      mensaje: 'Se va a borrar el gasto de ' + monto + '. No se puede deshacer.',
      textoAccion: 'Borrar gasto'
      /* `destructiva` no se manda: el valor por defecto ya es true, que es lo
         que deja el boton en rojo. */
    }).then(function (confirmado) {
      if (!confirmado) return;

      return window.Api
        .borrar('/edificios/' + estado.edificioId + '/gastos/' + id)
        .then(cargarGastos)
        .catch(function (error) {
          /* El error de una baja va arriba de la lista: es donde estaba la
             fila que no se pudo borrar. Y acá es donde aparece el candado del
             período ya publicado. */
          mostrarError('gastos', error.message);
        });
    });
  }


  /* =========================================================================
     LA PESTAÑA DE EXPENSAS (F2-T18)
     =========================================================================

     Dos acciones y un detalle de solo lectura: generar la liquidacion de un
     periodo, publicarla, y mirar como quedo.

     =========================================================================
     DOS BOTONES Y NO UNO, Y LA REGLA QUE LOS SEPARA
     =========================================================================

     **Regenerar** aparece solo mientras la expensa esta en borrador.
     **Publicar** es el acto que la vuelve visible para los residentes, arranca
     el vencimiento y cierra la regeneracion para siempre.

     El Roadmap decia "el boton de regenerar aparece solo en la ultima". Esa
     regla cambio en `F2-T05`: la ultima puede llevar quince dias publicada y
     con la mitad del edificio pagando. Lo que vale es si se publico.

     Y la pantalla **no deduce la regla**: el servidor manda
     `se_puede_regenerar` en cada fila. Si la pantalla lo calculara del estado,
     tendria una copia de la regla que algun dia ofrece un boton que el backend
     va a rechazar.

     =========================================================================
     EL 409 SE CONTESTA CON EL MODAL DEL SISTEMA
     =========================================================================

     Cuando ya hay un borrador del periodo, el backend responde 409 con el
     texto de la pregunta —que incluye por cuanto era la que se reemplaza— y
     `api.js` lo convierte en `error.necesitaConfirmacion`. Esta pantalla no
     escribe la pregunta: muestra la del servidor, que es el que sabe que se va
     a pisar. Es el mismo mecanismo del atajo de coeficientes.

     **Y por eso no hay un "modo confirmacion" en el formulario**, que es como
     lo describia el Roadmap. Con el modal, la pregunta se contesta en el acto:
     no queda un estado intermedio colgado que haya que reiniciar si alguien
     cambia el mes. La salvedad del Roadmap —"si cambia un dato, el estado de
     confirmacion se reinicia"— deja de hacer falta porque ese estado no
     existe. Nunca un `confirm()` del navegador, que esta prohibido.
     ====================================================================== */

  function periodoDeGeneracion() {
    var mes = $('#generar-mes').value;
    return {
      anio: parseInt($('#generar-anio').value, 10),
      mes: parseInt(mes, 10),
      texto: window.Moneda.periodoLargo(
        (mes.length === 1 ? '0' + mes : mes) + '/' + $('#generar-anio').value
      )
    };
  }

  function construirFiltrosDeExpensas() {
    /* Los mismos anios que el filtro de gastos, copiados de su desplegable, y
       los meses de la misma lista: dos listas de meses escritas por separado
       son dos listas que algun dia dicen cosas distintas. Aca no hay opcion
       "todo el anio": una liquidacion es siempre de un mes. */
    $('#generar-anio').innerHTML = $('#filtro-anio').innerHTML;
    $('#generar-mes').innerHTML = window.Moneda.MESES.map(function (nombre, i) {
      return '<option value="' + (i + 1) + '">' +
             nombre.charAt(0).toUpperCase() + nombre.slice(1) + '</option>';
    }).join('');

    var hoy = new Date();
    $('#generar-anio').value = String(hoy.getFullYear());
    $('#generar-mes').value = String(hoy.getMonth() + 1);
  }

  /* El estado de una liquidacion va como `.chip` y NO como `.pill`.

     Las pills son el semaforo de cuatro estados del edificio —una unidad en
     deuda, un activo por vencer— y eso es una regla de negocio sobre el estado
     real del edificio. El estado de un documento contable no es eso: usar el
     amarillo del semaforo para "borrador" seria gastar en una etiqueta un
     color que significa "hay algo que atender en el edificio".

     Lo que si avisa de un borrador sin publicar es el `.mensaje-aviso` de
     arriba de la pestania, que es donde corresponde: no es una etiqueta, es
     algo que hay que hacer. */
  function htmlDeExpensa(expensa) {
    var acciones = [
      '<button type="button" class="icon-btn icon-btn-sm" ' +
              'data-ver-expensa="' + expensa.id + '" ' +
              'aria-label="Ver el detalle de la liquidación de ' +
              expensa.periodo + '" title="Ver detalle">' +
        svg(ICONO_VER) +
      '</button>'
    ];

    if (expensa.se_puede_regenerar) {
      acciones.push(
        '<button type="button" class="icon-btn icon-btn-sm" ' +
                'data-regenerar="' + expensa.periodo + '" ' +
                'aria-label="Regenerar la liquidación de ' + expensa.periodo +
                '" title="Regenerar con los gastos de ahora">' +
          svg(ICONO_REGENERAR) +
        '</button>',
        '<button type="button" class="icon-btn icon-btn-sm" ' +
                'data-publicar="' + expensa.id + '" ' +
                'aria-label="Publicar la liquidación de ' + expensa.periodo +
                '" title="Publicar: la ven los residentes">' +
          svg(ICONO_PUBLICAR) +
        '</button>'
      );
    }

    var cuantas = expensa.cantidad_unidades === 1
      ? '1 unidad'
      : expensa.cantidad_unidades + ' unidades';

    return '' +
      '<div class="fila-lista content-glass" data-expensa="' + expensa.id + '">' +
        '<div class="fila-lista-dato">' +
          '<b>' + escapar(window.Moneda.periodoLargo(expensa.periodo)) + '</b>' +
          '<span>' + window.Moneda.pesos(expensa.total) + ' · ' + cuantas +
            (expensa.publicada_en
              ? ' · publicada el ' + window.Moneda.fecha(expensa.publicada_en)
              : '') +
          '</span>' +
        '</div>' +
        '<div class="fila-lista-acciones">' +
          '<span class="chip">' +
            (expensa.estado === 'borrador' ? 'En borrador' : 'Publicada') +
          '</span>' +
          '<div class="fila-lista-botones">' + acciones.join('') + '</div>' +
        '</div>' +
      '</div>';
  }

  function pintarExpensas(liquidaciones) {
    var lista = $('#lista-expensas');

    if (!liquidaciones.length) {
      lista.innerHTML =
        '<p class="lista-vacia">Todavía no hay liquidaciones de este edificio. ' +
        'Generá la del mes con el bloque de arriba.</p>';
      mostrar($('#aviso-borrador'), false);
      return;
    }

    lista.innerHTML = liquidaciones.map(htmlDeExpensa).join('');

    /* El aviso del borrador sin publicar. Se nombra el periodo y no se dice
       "hay una liquidacion en borrador": sin el periodo hay que ir a buscar
       cual. */
    var borradores = liquidaciones.filter(function (e) {
      return e.estado === 'borrador';
    });

    if (!borradores.length) {
      mostrar($('#aviso-borrador'), false);
      return;
    }

    var periodos = borradores.map(function (e) {
      return window.Moneda.periodoLargo(e.periodo);
    }).join(', ');

    texto($('[data-texto-aviso-borrador]'),
      borradores.length === 1
        ? 'La liquidación de ' + periodos + ' está en borrador: los residentes ' +
          'todavía no la ven y el vencimiento no empezó a correr. Publicala ' +
          'cuando esté lista.'
        : 'Hay ' + borradores.length + ' liquidaciones en borrador (' + periodos +
          '): los residentes no las ven y el vencimiento no empezó a correr.');
    mostrar($('#aviso-borrador'), true);
  }

  function cargarExpensas() {
    if (!estado.edificioId) return;

    var lista = $('#lista-expensas');
    lista.innerHTML = window.Cargando.html();
    mostrarError('expensas', '');

    return window.Api
      .get('/edificios/' + estado.edificioId + '/expensas')
      .then(function (liquidaciones) {
        estado.expensas = liquidaciones;
        pintarExpensas(liquidaciones);
      })
      .catch(function (error) {
        lista.innerHTML = '';
        mostrarError('expensas', error.message);
      });
  }

  /* ------------------------------------------------------------- generar -- */

  function avisarExito(mensaje) {
    texto($('[data-texto-exito-expensas]'), mensaje);
    mostrar($('#exito-expensas'), true);
  }

  function generar() {
    var periodo = periodoDeGeneracion();
    var boton = $('#boton-generar');

    mostrarError('expensas', '');
    mostrar($('#exito-expensas'), false);
    boton.disabled = true;

    function pedir(confirmar) {
      return window.Api.post('/edificios/' + estado.edificioId + '/expensas', {
        anio: periodo.anio,
        mes: periodo.mes,
        confirmar: confirmar
      });
    }

    function listo(expensa) {
      avisarExito(
        'Se generó la liquidación de ' + periodo.texto + ' por ' +
        window.Moneda.pesos(expensa.total) + ', repartida entre ' +
        expensa.cantidad_unidades + ' unidades. Queda en borrador: ' +
        'publicala para que la vean los residentes.'
      );
      return cargarExpensas();
    }

    pedir(false)
      .then(listo, function (error) {
        /* El 400 trae el motivo util —"faltan coeficientes en 3 unidades", "no
           hay gastos cargados en 11/2026"— y se muestra tal cual: cualquier
           texto propio seria menos preciso. */
        if (!error.necesitaConfirmacion) {
          mostrarError('expensas', error.message);
          return;
        }

        return window.Confirmar.pedir({
          titulo: 'Reemplazar el borrador de ' + periodo.texto,
          mensaje: error.message,
          textoAccion: 'Confirmar y regenerar'
        }).then(function (confirmo) {
          if (!confirmo) return;
          return pedir(true).then(listo, function (segundo) {
            mostrarError('expensas', segundo.message);
          });
        });
      })
      .then(function () { boton.disabled = false; });
  }

  /* Regenerar desde la fila es exactamente generar el mismo periodo: el
     backend ya sabe que hay un borrador y pide confirmacion. Asi que se
     reutiliza el flujo en vez de escribir otro, y de paso los dos caminos
     muestran la misma pregunta, porque es la misma. */
  function regenerar(periodo) {
    var partes = String(periodo).split('/');
    $('#generar-mes').value = String(parseInt(partes[0], 10));
    $('#generar-anio').value = partes[1];
    generar();
  }

  /* ------------------------------------------------------------ publicar -- */

  function publicar(id) {
    var expensa = (estado.expensas || []).filter(function (e) {
      return e.id === id;
    })[0];
    if (!expensa) return;

    var largo = window.Moneda.periodoLargo(expensa.periodo);

    /* **La confirmacion dice que es irreversible, porque lo es.** Publicar no
       se puede deshacer: lo que habria que deshacer no esta en la base, esta en
       la cabeza de los propietarios que ya anotaron cuanto tienen que pagar. Un
       dialogo que no lo diga convierte una decision en un clic. */
    window.Confirmar.pedir({
      titulo: 'Publicar la liquidación de ' + largo,
      mensaje:
        'Desde que la publiques, los residentes la ven, empieza a correr el ' +
        'vencimiento y podés recibir pagos. No se puede deshacer ni volver a ' +
        'generar: un error que aparezca después se corrige en la liquidación ' +
        'siguiente.',
      textoAccion: 'Publicar',
      /* No es destructiva: no borra nada. El boton va con el acento y no en
         rojo, que es para lo que destruye. */
      destructiva: false
    }).then(function (confirmo) {
      if (!confirmo) return;

      mostrarError('expensas', '');
      mostrar($('#exito-expensas'), false);

      return window.Api
        .post('/edificios/' + estado.edificioId + '/expensas/' + id + '/publicar', {})
        .then(function () {
          avisarExito(
            'Se publicó la liquidación de ' + largo + '. Ya la ven los ' +
            'residentes y pueden cargar sus pagos.'
          );
          return cargarExpensas();
        })
        .catch(function (error) {
          mostrarError('expensas', error.message);
        });
    });
  }

  /* --------------------------------------------------------- el detalle -- */

  function htmlDeRubro(linea, total) {
    /* La proporcion de cada rubro se calcula aca, y es la unica cuenta que esta
       pantalla hace con plata. No contradice la regla: no es un monto, es un
       porcentaje para leer de un vistazo, y redondearlo no mueve un centavo de
       nada. Todos los montos siguen saliendo del backend. */
    var parte = Number(linea.monto);
    var sobre = Number(total);
    var porcentaje = sobre > 0 ? Math.round((parte / sobre) * 100) : 0;

    return '' +
      '<div class="fila-lista content-glass">' +
        '<div class="fila-lista-dato">' +
          '<b>' + escapar(linea.rubro_etiqueta) + '</b>' +
          '<span>' + porcentaje + '% del total del período</span>' +
        '</div>' +
        '<div class="fila-lista-acciones">' +
          '<span class="chip">' + window.Moneda.pesos(linea.monto) + '</span>' +
        '</div>' +
      '</div>';
  }

  function htmlDeUnidadLiquidada(unidad) {
    /* El recargo y el saldo a favor se muestran **solo si existen**. Una linea
       que diga "recargo $0,00" en las veinte unidades de un edificio al dia es
       ruido que tapa justamente la que si tiene recargo. */
    var detalles = ['coeficiente ' + window.Moneda.numero(unidad.coeficiente) + '%'];

    if (Number(unidad.recargo_mora) > 0) {
      detalles.push('recargo ' + window.Moneda.pesos(unidad.recargo_mora));
    }
    if (Number(unidad.saldo_a_favor_aplicado) > 0) {
      detalles.push('saldo a favor ' +
                    window.Moneda.pesos(unidad.saldo_a_favor_aplicado));
    }

    return '' +
      '<div class="fila-lista content-glass">' +
        '<div class="fila-lista-dato">' +
          '<b>' + escapar(unidad.identificador) + '</b>' +
          '<span>' + detalles.join(' · ') + '</span>' +
        '</div>' +
        '<div class="fila-lista-acciones">' +
          '<span class="chip">' + window.Moneda.pesos(unidad.total_a_pagar) +
          '</span>' +
        '</div>' +
      '</div>';
  }

  function verExpensa(id) {
    mostrarError('expensas', '');

    return window.Api
      .get('/edificios/' + estado.edificioId + '/expensas/' + id)
      .then(function (expensa) {
        var largo = window.Moneda.periodoLargo(expensa.periodo);

        texto($('#titulo-modal-expensa'), 'Liquidación de ' + largo);
        texto($('[data-sub-modal-expensa]'),
          expensa.estado === 'borrador'
            ? 'En borrador: todavía no la ven los residentes.'
            : 'Publicada el ' + window.Moneda.fecha(expensa.publicada_en) + '.');

        texto($('[data-expensa-total]'), window.Moneda.pesos(expensa.total));
        $('[data-expensa-chips]').innerHTML =
          '<span class="chip">' + expensa.detalle.length +
            (expensa.detalle.length === 1 ? ' rubro' : ' rubros') + '</span>' +
          '<span class="chip">' + expensa.cantidad_unidades + ' unidades</span>';

        $('[data-expensa-rubros]').innerHTML = expensa.detalle.map(
          function (linea) { return htmlDeRubro(linea, expensa.total); }
        ).join('');

        /* **La nota que explica por que los dos totales pueden no coincidir.**
           Es la primera pregunta que se hace alguien mirando esta pantalla, y
           sin la explicacion parece un error de cuentas. */
        var sumaDeUnidades = expensa.unidades.reduce(function (acum, u) {
          return acum + Number(u.total_a_pagar);
        }, 0);
        var hayDiferencia = Math.abs(sumaDeUnidades - Number(expensa.total)) > 0.005;

        texto($('[data-nota-reparto]'), hayDiferencia
          ? 'La suma de lo que paga cada unidad no da el total del período, y ' +
            'está bien: el total son los gastos del consorcio, y lo que paga ' +
            'cada unidad incluye además su recargo por mora y le descuenta su ' +
            'saldo a favor, que son cuentas de esa unidad.'
          : 'La suma de lo que paga cada unidad da exactamente el total del ' +
            'período.');

        $('[data-expensa-unidades]').innerHTML =
          expensa.unidades.map(htmlDeUnidadLiquidada).join('');

        $('#modal-expensa').classList.add('abierto');
        $('[data-cerrar-expensa]').focus();
      })
      .catch(function (error) {
        mostrarError('expensas', error.message);
      });
  }

  function cerrarModalExpensa() {
    $('#modal-expensa').classList.remove('abierto');
  }

  function engancharExpensas() {
    $('#boton-generar').addEventListener('click', generar);

    document.querySelectorAll('[data-cerrar-expensa]').forEach(function (boton) {
      boton.addEventListener('click', cerrarModalExpensa);
    });

    $('#modal-expensa').addEventListener('click', function (evento) {
      if (evento.target === $('#modal-expensa')) cerrarModalExpensa();
    });

    /* Delegacion, igual que en gastos: el listado se redibuja con innerHTML
       despues de cada generacion y de cada publicacion. */
    $('#lista-expensas').addEventListener('click', function (evento) {
      var ver = evento.target.closest('[data-ver-expensa]');
      if (ver) {
        verExpensa(parseInt(ver.getAttribute('data-ver-expensa'), 10));
        return;
      }

      var rehacer = evento.target.closest('[data-regenerar]');
      if (rehacer) {
        regenerar(rehacer.getAttribute('data-regenerar'));
        return;
      }

      var publicarla = evento.target.closest('[data-publicar]');
      if (publicarla) {
        publicar(parseInt(publicarla.getAttribute('data-publicar'), 10));
      }
    });
  }

  /* =========================================================================
     LA PESTAÑA DE PAGOS (F2-T19)
     =========================================================================

     Dos bloques: la cola de lo que hay que decidir y el historial de lo que ya
     se decidio. Misma particion que `usuarios.html` entre las cuentas que
     esperan aprobacion y las que ya tienen rol, y por la misma razon — no son
     dos entidades, son los mismos pagos en un estado que pide una decision.

     =========================================================================
     DOS PEDIDOS Y NO UNO, PORQUE EL TOTAL LO CALCULA EL SERVIDOR
     =========================================================================

     El endpoint devuelve `cantidad` y `total` del filtro que se le pidio. Si
     la pantalla trajera todos los pagos y los partiera en dos listas, los dos
     totales habria que sumarlos en JavaScript — y entonces serian el total de
     lo que se dibujo y no el del filtro, que es justo lo que el backend evita.
     Asi que la cola se pide con `estado=pendiente` y el historial con el
     estado que elija el desplegable. Cada lista trae su propio total.

     **Y por eso el filtro del historial no tiene un "todos"**: no es un estado
     del backend, asi que no tendria total propio. Los dos valores que ofrece
     son los dos estados reales en los que termina un pago.

     =========================================================================
     CONFIRMAR PREGUNTA CON EL MODAL DEL SISTEMA; RECHAZAR NECESITA OTRO
     =========================================================================

     Las dos acciones piden confirmacion porque ninguna se puede deshacer: un
     pago conciliado no se vuelve a conciliar, y si se confirmo por equivocacion
     lo que corresponde es registrar el movimiento que lo corrige, no reescribir
     el historial. Pero no usan el mismo componente:

     - **Confirmar** usa `Confirmar.pedir()`: no hay nada que escribir.
     - **Rechazar** usa un modal de formulario propio, porque el backend exige
       el motivo y `Confirmar.pedir()` solo devuelve si o no. Un `prompt()` del
       navegador esta prohibido en todo el proyecto.

     =========================================================================
     QUIEN CARGO UN PAGO NO LO CONCILIA, Y ESO NO LO DECIDE LA PANTALLA
     =========================================================================

     El servidor manda `puedo_conciliarlo` por fila. La pantalla no sabe la
     regla —el caso real es el administrador que vive en el edificio y carga su
     propia expensa— y si la supiera tendria una copia que algun dia no
     coincide con la del backend. Cuando viene en `false` no se dibujan los
     botones **y se explica por que**: un par de botones que faltan sin
     explicacion se lee como una pantalla a medio cargar.
     ====================================================================== */

  function construirFiltroDeEstado() {
    /* Los dos estados terminales, con la etiqueta en plural porque titulan una
       lista. No se escriben los valores a mano en el HTML para que esta lista y
       la del backend se lean juntas desde un solo lugar. */
    $('#filtro-estado-pago').innerHTML =
      '<option value="confirmado">Confirmados</option>' +
      '<option value="rechazado">Rechazados</option>';
  }

  function estadoDelHistorico() {
    return $('#filtro-estado-pago').value || 'confirmado';
  }

  /* Los datos secundarios de un pago, que son los que permiten cotejarlo
     contra el extracto del banco: de que unidad es, de que periodo, como se
     pago y cuando. La fecha que importa es la del pago y no la de la carga —se
     paga el 10 y se sube el comprobante el 12— asi que va primero. */
  function detallesDelPago(pago) {
    return [
      'unidad ' + pago.identificador,
      window.Moneda.periodoLargo(pago.periodo),
      pago.medio_pago_etiqueta,
      'pagado el ' + window.Moneda.fecha(pago.fecha)
    ];
  }

  function botonDeComprobante(pago) {
    /* Sin comprobante no se dibuja un boton deshabilitado: no hay nada que
       abrir, y un boton gris invita a preguntarse que le falta a la pantalla.
       La ausencia se dice en el texto de la fila. */
    if (!pago.comprobante_url) return '';

    /* `rel="noopener noreferrer"` no es decorativo: el enlace lo escribio el
       residente y apunta afuera del sistema, asi que la pestaña que se abre no
       tiene por que poder tocar esta. */
    return '<a class="icon-btn icon-btn-sm" href="' + escapar(pago.comprobante_url) +
           '" target="_blank" rel="noopener noreferrer" ' +
           'aria-label="Abrir el comprobante del pago de la unidad ' +
           escapar(pago.identificador) + ' en una pestaña nueva" ' +
           'title="Ver el comprobante">' + svg(ICONO_COMPROBANTE) + '</a>';
  }

  /* Cuantos dias lleva esperando un pago. **`cargado_en` y `fecha` son dos
     datos distintos y el backend los separa a proposito**: se paga el 10 y se
     sube el comprobante el 12. En una cola de trabajo lo que importa es desde
     cuando esta esperando una respuesta, que es `cargado_en`.

     Se compara solo la parte de la fecha para no depender de la zona horaria:
     `creado_en` viaja sin zona (ver la deuda anotada en `F13-T01`), asi que una
     cuenta con horas podria dar un dia de diferencia segun el huso. */
  function diasEsperando(cargadoEn) {
    if (!cargadoEn) return null;

    var partes = String(cargadoEn).slice(0, 10).split('-');
    if (partes.length !== 3) return null;

    var cargado = Date.UTC(partes[0], partes[1] - 1, partes[2]);
    var hoy = new Date();
    var hoyUtc = Date.UTC(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());

    var dias = Math.round((hoyUtc - cargado) / 86400000);
    return dias < 0 ? null : dias;
  }

  function esperaDelPago(pago) {
    var dias = diasEsperando(pago.cargado_en);
    if (dias === null) return '';
    if (dias === 0) return 'avisó hoy';
    if (dias === 1) return 'esperando desde ayer';
    return 'esperando ' + dias + ' días';
  }

  function htmlDePagoDeLaCola(pago) {
    var detalles = detallesDelPago(pago);

    var espera = esperaDelPago(pago);
    if (espera) detalles.push(espera);

    if (!pago.comprobante_url) {
      /* Se dice con palabras y no con un hueco. Un pago sin comprobante se
         puede confirmar igual —el extracto del banco es la fuente de verdad,
         no el papel que subio el residente— pero quien concilia tiene que
         saber que no hay nada para mirar antes de abrir el home banking. */
      detalles.push('sin comprobante');
    }

    var acciones = [botonDeComprobante(pago)];

    if (pago.puedo_conciliarlo) {
      acciones.push(
        '<button type="button" class="boton-primario boton-secundario boton-chico" ' +
                'data-rechazar="' + pago.id + '" ' +
                'aria-label="Rechazar el pago de la unidad ' +
                escapar(pago.identificador) + '">Rechazar</button>',
        '<button type="button" class="boton-primario boton-chico" ' +
                'data-confirmar="' + pago.id + '" ' +
                'aria-label="Confirmar el pago de la unidad ' +
                escapar(pago.identificador) + '">Confirmar</button>'
      );
    } else {
      /* **La explicacion va en la fila y no arriba de la lista**, porque el
         caso real es mezclado: el administrador que vive en el edificio carga
         su propia expensa y concilia la de sus vecinos, asi que en la misma
         cola hay filas con botones y filas sin. Un aviso general arriba no
         diria cual es cual, y dos filas identicas donde una tiene botones y la
         otra no se lee como una pantalla a medio cargar.

         No es un boton deshabilitado: no hay nada que habilitar nunca para esta
         persona, y un gris que no se puede cambiar invita a buscarle el modo. */
      acciones.push(
        '<span class="chip">Lo cargaste vos: lo revisa otro administrador</span>'
      );
    }

    /* `.fila-lista.pendiente` — borde completo y sombra del mismo color, con el
       **acento de marca y no el naranja del semaforo**. El semaforo son cuatro
       estados del edificio y el naranja significa "mantenimiento en curso": un
       pago sin conciliar no es un estado del edificio. Es la misma decision que
       la fila de una cuenta sin aprobar. */
    return '' +
      '<article class="fila-lista content-glass pendiente" data-pago="' + pago.id + '">' +
        '<div class="fila-lista-dato">' +
          '<b>' + window.Moneda.pesos(pago.monto) + '</b>' +
          '<span>' + escapar(detalles.join(' · ')) + '</span>' +
        '</div>' +
        '<div class="fila-lista-acciones">' +
          /* La ranura `.fila-lista-estado` queda anclada al dato y el aspecto
             lo pone `.rol-badge`, que es su companera en las pantallas
             aprobadas: es una etiqueta neutra de clasificacion, igual que el
             rol de un usuario. Un `.chip` suelto aca no es lo mismo — el chip
             lleva un dato dentro de las acciones, no la etiqueta de la fila. */
          '<span class="fila-lista-estado rol-badge">Lo cargó ' +
            escapar(pago.cargado_por) +
          '</span>' +
          '<div class="fila-lista-botones">' + acciones.join('') + '</div>' +
        '</div>' +
      '</article>';
  }

  function htmlDePagoConciliado(pago) {
    var detalles = detallesDelPago(pago);

    if (pago.conciliado_en) {
      detalles.push(
        (pago.estado === 'confirmado' ? 'confirmado' : 'rechazado') + ' el ' +
        window.Moneda.fecha(pago.conciliado_en) +
        (pago.conciliado_por ? ' por ' + pago.conciliado_por : '')
      );
    }

    /* **El motivo del rechazo se muestra, y es la mitad del valor de rechazar.**
       Guardado y no mostrado seria un dato que nadie sabe de donde salio; y
       quien concilia necesita leerlo para responderle al residente que llama. */
    if (pago.motivo_rechazo) {
      detalles.push('motivo: ' + pago.motivo_rechazo);
    }

    return '' +
      '<article class="fila-lista content-glass" data-pago="' + pago.id + '">' +
        '<div class="fila-lista-dato">' +
          '<b>' + window.Moneda.pesos(pago.monto) + '</b>' +
          '<span>' + escapar(detalles.join(' · ')) + '</span>' +
        '</div>' +
        '<div class="fila-lista-acciones">' +
          /* Neutra a proposito: el estado de un pago NO es el semaforo del
             edificio. Un `.pill` verde para "confirmado" gastaria en una
             etiqueta administrativa el color que significa "no hay nada que
             atender en el edificio". */
          '<span class="fila-lista-estado rol-badge">' +
            (pago.estado === 'confirmado' ? 'Confirmado' : 'Rechazado') +
          '</span>' +
          '<div class="fila-lista-botones">' + botonDeComprobante(pago) + '</div>' +
        '</div>' +
      '</article>';
  }

  function pintarCola(datos) {
    var seccion = $('#seccion-cola');
    var caja = $('#total-cola');

    /* El bloque entero desaparece cuando no hay nada que conciliar, en vez de
       mostrar un "no hay pagos pendientes". Un encabezado con un vacio debajo
       ocupa todos los dias el lugar de algo que hay que atender, y la cola
       vacia es el estado normal de un consorcio al dia. */
    if (!datos.cantidad) {
      mostrar(seccion, false);
      mostrar(caja, false);
      return;
    }

    texto(caja.querySelector('[data-cola-monto]'), window.Moneda.pesos(datos.total));
    caja.querySelector('[data-cola-chips]').innerHTML =
      '<span class="chip">' +
        (datos.cantidad === 1 ? '1 pago' : datos.cantidad + ' pagos') +
      '</span>';
    mostrar(caja, true);

    texto($('[data-contador-cola]'), String(datos.cantidad));

    /* Cada fila explica si se puede conciliar o no, en `htmlDePagoDeLaCola`:
       la cola puede ser mezclada y un aviso general no diria cual es cual. */
    $('#lista-cola').innerHTML = datos.pagos.map(htmlDePagoDeLaCola).join('');

    mostrar(seccion, true);
  }

  function pintarHistorico(datos) {
    var lista = $('#lista-historico');
    var cuantos = datos.cantidad;

    texto($('[data-contador-historico]'), String(cuantos));

    if (!cuantos) {
      lista.innerHTML =
        '<p class="lista-vacia">' +
        (estadoDelHistorico() === 'confirmado'
          ? 'Todavía no hay pagos confirmados en este edificio.'
          : 'No hay pagos rechazados, que es la situación deseable.') +
        '</p>';
      return;
    }

    lista.innerHTML = datos.pagos.map(htmlDePagoConciliado).join('');
  }

  function cargarPagos() {
    if (!estado.edificioId) return;

    var base = '/edificios/' + estado.edificioId + '/pagos?estado=';
    $('#lista-historico').innerHTML = window.Cargando.html();
    mostrarError('pagos', '');

    /* Los dos pedidos van juntos y no uno tras otro: son independientes, y en
       serie la pestaña tarda el doble en estar completa. */
    return Promise
      .all([
        window.Api.get(base + 'pendiente'),
        window.Api.get(base + estadoDelHistorico())
      ])
      .then(function (respuestas) {
        estado.cola = respuestas[0].pagos;
        pintarCola(respuestas[0]);
        pintarHistorico(respuestas[1]);
      })
      .catch(function (error) {
        $('#lista-historico').innerHTML = '';
        mostrarError('pagos', error.message);
      });
  }

  function avisarExitoDePago(mensaje) {
    texto($('[data-texto-exito-pagos]'), mensaje);
    mostrar($('#exito-pagos'), true);
  }

  function pagoDeLaCola(id) {
    return (estado.cola || []).filter(function (p) { return p.id === id; })[0];
  }

  /* ------------------------------------------------------------ confirmar -- */

  function confirmarPago(id) {
    var pago = pagoDeLaCola(id);
    if (!pago) return;

    window.Confirmar.pedir({
      titulo: 'Confirmar el pago de la unidad ' + pago.identificador,
      mensaje:
        'Son ' + window.Moneda.pesos(pago.monto) + ' de ' +
        window.Moneda.periodoLargo(pago.periodo) + '. Al confirmarlo baja la ' +
        'deuda de esa unidad y el residente lo ve como acreditado. No se puede ' +
        'deshacer: si después aparece un error, se corrige con otro movimiento ' +
        'y no reescribiendo este.',
      textoAccion: 'Confirmar el pago',
      /* No destruye nada, así que el botón va con el acento y no en rojo. Lo
         que sí es, y el texto lo dice, es irreversible. */
      destructiva: false
    }).then(function (confirmo) {
      if (!confirmo) return;
      return conciliar(id, 'confirmado', null,
        'Se confirmó el pago de ' + window.Moneda.pesos(pago.monto) +
        ' de la unidad ' + pago.identificador + '. La deuda ya quedó al día.');
    });
  }

  /* -------------------------------------------------------------- rechazar -- */

  function abrirModalDeRechazo(id) {
    var pago = pagoDeLaCola(id);
    if (!pago) return;

    estado.rechazando = id;
    estado.ultimoFoco = document.activeElement;

    texto($('[data-sub-modal-rechazo]'),
      window.Moneda.pesos(pago.monto) + ' de la unidad ' + pago.identificador +
      ', ' + window.Moneda.periodoLargo(pago.periodo) + '.');

    var formulario = $('#formulario-rechazo');
    var campo = $('#rechazo-motivo');
    campo.value = '';
    window.Formularios.limpiarErrores(formulario);
    /* El resumen se busca DENTRO del formulario y no con un selector global:
       hay tres en esta pantalla —el del gasto, el del rechazo— y el selector
       suelto agarra el primero del documento, que es el del otro modal. */
    mostrar(formulario.querySelector('[data-resumen-errores]'), false);

    $('#modal-rechazo').classList.add('abierto');
    campo.focus();
  }

  function cerrarModalDeRechazo() {
    $('#modal-rechazo').classList.remove('abierto');
    estado.rechazando = null;

    /* El foco vuelve a donde estaba, salvo que ese boton ya no exista: la fila
       se redibuja despues de conciliar, asi que el boton que abrio el modal se
       fue con el HTML viejo. */
    if (estado.ultimoFoco && document.contains(estado.ultimoFoco)) {
      estado.ultimoFoco.focus();
    }
    estado.ultimoFoco = null;
  }

  function modalDeRechazoAbierto() {
    return $('#modal-rechazo').classList.contains('abierto');
  }

  function rechazar(evento) {
    evento.preventDefault();

    var id = estado.rechazando;
    var pago = pagoDeLaCola(id);
    if (!pago) return;

    var motivo = $('#rechazo-motivo').value.trim();
    var boton = $('#boton-rechazar');

    boton.disabled = true;

    /* El motivo no se valida acá además del backend: el esquema ya exige el
       largo mínimo y devuelve el problema por campo, que es lo que
       `marcarErrores` necesita para pintar el campo y llevarle el foco. Una
       segunda validación en la pantalla sería una copia de la regla con su
       propio texto, capaz de decir algo distinto del servidor. */
    conciliar(id, 'rechazado', motivo,
      'Se rechazó el pago de ' + window.Moneda.pesos(pago.monto) +
      ' de la unidad ' + pago.identificador + '. El residente ve el motivo en ' +
      'su cuenta y puede volver a cargarlo.',
      $('#formulario-rechazo')
    ).then(function (salioBien) {
      boton.disabled = false;
      if (salioBien) cerrarModalDeRechazo();
    });
  }

  /* ------------------------------------------------- el pedido compartido -- */

  /* Las dos acciones son el mismo PATCH con otro estado, así que son una sola
     función: la validación del backend es la misma tabla de transiciones, y dos
     funciones serían dos lugares donde recordar que hay que recargar la lista.

     Devuelve una promesa con `true` o `false` —salió bien o no— y nunca
     rechaza: quien la llama necesita decidir si cierra el modal, y un `reject`
     lo obligaría a un `catch` que no distingue "lo rechazó el servidor" de "se
     rompió algo". */
  function conciliar(id, nuevoEstado, motivo, mensajeDeExito, formulario) {
    mostrarError('pagos', '');
    mostrar($('#exito-pagos'), false);

    var cuerpo = { estado: nuevoEstado };
    if (motivo) cuerpo.motivo = motivo;

    return window.Api
      .patch('/edificios/' + estado.edificioId + '/pagos/' + id, cuerpo)
      .then(function () {
        avisarExitoDePago(mensajeDeExito);

        /* **Se recargan las tres cosas que el pago movió, y no solo la lista.**
           Un pago confirmado cambia la cola, el historial y —porque baja la
           deuda— lo que van a mostrar Deudores y los reportes. Las dos
           pestañas que existen hoy se piden de nuevo; refrescar desde lo que ya
           estaba en memoria mostraría el saldo viejo, que es un bug real que ya
           pasó en la iteración anterior. */
        return cargarPagos().then(function () { return true; });
      })
      .catch(function (error) {
        /* **El error va donde ocurrió la acción, y con el modal abierto eso es
           dentro del modal.** Mandarlo arriba de la lista lo dejaría detrás del
           velo: la persona aprieta "Rechazar el pago", no pasa nada visible, y
           el aviso aparece recién cuando cierra. Es el mismo bug que ya se
           arregló en el alta de edificios.

           Primero se intenta marcar el campo —un motivo demasiado corto es un
           error de campo y el backend lo manda con su nombre— y si el error no
           es de ningún campo, va al resumen del formulario. */
        if (formulario) {
          if (!window.Formularios.marcarErrores(formulario, error.campos)) {
            var resumen = formulario.querySelector('[data-resumen-errores]');
            texto(resumen, error.message);
            mostrar(resumen, true);
          }
          return false;
        }

        mostrarError('pagos', error.message);
        return false;
      });
  }

  function engancharPagos() {
    $('#filtro-estado-pago').addEventListener('change', cargarPagos);

    document.querySelectorAll('[data-cerrar-rechazo]').forEach(function (boton) {
      boton.addEventListener('click', cerrarModalDeRechazo);
    });

    $('#formulario-rechazo').addEventListener('submit', rechazar);

    /* El clic en el velo cierra el modal de rechazo. Es un formulario de un
       solo campo corto, así que no hay un alta a medio tipear que perder — que
       es la razón por la que el modal del gasto sí se queda abierto. */
    $('#modal-rechazo').addEventListener('click', function (evento) {
      if (evento.target === $('#modal-rechazo')) cerrarModalDeRechazo();
    });

    /* Delegación en los dos contenedores, igual que en usuarios: las listas se
       reemplazan enteras con innerHTML después de cada conciliación, así que un
       listener por fila se iría con el HTML viejo. */
    $('#lista-cola').addEventListener('click', function (evento) {
      var aceptar = evento.target.closest('[data-confirmar]');
      if (aceptar) {
        confirmarPago(parseInt(aceptar.getAttribute('data-confirmar'), 10));
        return;
      }

      var negar = evento.target.closest('[data-rechazar]');
      if (negar) {
        abrirModalDeRechazo(parseInt(negar.getAttribute('data-rechazar'), 10));
      }
    });
  }

  /* =========================================================================
     LA PESTAÑA DE DEUDORES (F2-T20)
     =========================================================================

     Consume `F2-T11` tal cual, sin una sola linea de backend nueva, y es de
     **solo lectura siempre**: la unica forma de que una deuda baje es conciliar
     su pago. Un boton de "marcar como pagado" aca seria una forma de saldar
     deuda sin que entre plata.

     =========================================================================
     ES LA PRIMERA PANTALLA DONDE EL SEMAFORO APARECE DE VERDAD
     =========================================================================

     En Gastos y en Expensas los estados van como `.chip` neutro, y esta
     anotado por que: un rubro contable y el estado de un documento contable no
     son estados del edificio. **Una unidad en deuda si lo es.** Es exactamente
     el amarillo y el rojo que la Fase 5 va a pintar en el Dashboard Visual.

     Dos reglas que eso trae, y ninguna es opcional:

     1. **La severidad la manda el backend** (`ok`, `warn`, `crit`), no se
        deduce de los meses. Si esta pantalla la calculara, el Dashboard Visual
        y esta podrian pintar la misma unidad de colores distintos — y el
        calculo vive en `services/deudores.py` justamente para que no pase.
     2. **El color nunca comunica solo.** La fila lleva el borde completo y la
        sombra del estado (`.s-warn` / `.s-crit`, nunca un borde izquierdo de
        3 px) **y** la `.pill` con los meses escritos al lado. El amarillo y el
        naranja del semaforo estan a ΔE 6,3 en deuteranopia, asi que el color
        es un refuerzo y no el dato.

     =========================================================================
     DOS NUMEROS Y NO UNO
     =========================================================================

     `saldo` es todo lo que la unidad debe; `vencido` es solo la parte atrasada,
     que es la que decide el color. Van los dos porque responden preguntas
     distintas: cuanto hay que cobrarle, y que tan mal esta. Y el filtro existe
     por lo mismo: una unidad que debe el mes corriente todavia en termino
     aparece con saldo y con cero meses de atraso — hay que cobrarle, pero no es
     una deudora.
     ====================================================================== */

  var SEVERIDADES = {
    ok:   { clase: '',       pill: 'ok'   },
    warn: { clase: 's-warn', pill: 'warn' },
    crit: { clase: 's-crit', pill: 'crit' }
  };

  function construirFiltroDeDeudores() {
    /* "Todas las que deben" primero porque es la pregunta mas frecuente del
       administrador —a quien le tengo que cobrar— y porque el filtro de
       atrasadas esconde unidades que si deben. Un filtro que esconde datos no
       puede ser el valor por defecto. */
    $('#filtro-deudores').innerHTML =
      '<option value="">Todas las que deben</option>' +
      '<option value="1">Solo las atrasadas</option>';
  }

  function soloVencidos() {
    return $('#filtro-deudores').value === '1';
  }

  /* El texto del atraso. Nunca es solo un numero: "2" al lado de un monto no
     dice si son meses, periodos o dias. */
  function textoDelAtraso(deudor) {
    if (deudor.meses_de_atraso === 0) return 'en término';
    if (deudor.meses_de_atraso === 1) return '1 mes de atraso';
    return deudor.meses_de_atraso + ' meses de atraso';
  }

  function htmlDeDeudor(deudor) {
    var severidad = SEVERIDADES[deudor.severidad] || SEVERIDADES.ok;

    /* A quien hay que llamar. El backend manda los dos nombres justamente para
       que la pantalla de cobranza no obligue a abrir la ficha de cada unidad.
       El inquilino va primero cuando existe: en Argentina las expensas
       ordinarias las paga de hecho el inquilino (Documento General, 3.1). */
    var quien = [];
    if (deudor.inquilino) quien.push('inquilino ' + deudor.inquilino);
    if (deudor.propietario) quien.push('propietario ' + deudor.propietario);
    if (!quien.length) quien.push('sin ocupantes asignados');

    var secundarios = [
      'piso ' + deudor.piso_numero,
      quien.join(' · ')
    ];

    /* Lo vencido se nombra **solo cuando es distinto del saldo**. Cuando son
       iguales —el caso normal de una unidad atrasada— repetir el mismo numero
       con otra etiqueta hace dudar de cual de los dos es el que hay que
       cobrar. */
    if (Number(deudor.vencido) > 0 &&
        Number(deudor.vencido) !== Number(deudor.saldo)) {
      secundarios.push('vencido ' + window.Moneda.pesos(deudor.vencido));
    }

    if (deudor.periodo_mas_viejo) {
      secundarios.push('desde ' +
        window.Moneda.periodoLargo(deudor.periodo_mas_viejo));
    }

    return '' +
      '<article class="fila-lista content-glass ' + severidad.clase + '" ' +
               'data-deudor="' + deudor.departamento_id + '">' +
        '<div class="fila-lista-dato">' +
          '<b>' + escapar(deudor.identificador) + ' · ' +
            window.Moneda.pesos(deudor.saldo) + '</b>' +
          '<span>' + escapar(secundarios.join(' · ')) + '</span>' +
        '</div>' +
        '<div class="fila-lista-acciones">' +
          '<span class="fila-lista-estado pill ' + severidad.pill + '">' +
            escapar(textoDelAtraso(deudor)) +
          '</span>' +
          '<div class="fila-lista-botones">' +
            '<button type="button" class="icon-btn icon-btn-sm" ' +
                    'data-ver-deudor="' + deudor.departamento_id + '" ' +
                    'aria-label="Ver los períodos impagos de la unidad ' +
                    escapar(deudor.identificador) + '" ' +
                    'title="Ver los períodos impagos">' +
              svg(ICONO_VER) +
            '</button>' +
          '</div>' +
        '</div>' +
      '</article>';
  }

  function pintarDeudores(datos) {
    var lista = $('#lista-deudores');
    var caja = $('#total-deudores');

    texto($('[data-contador-deudores]'), String(datos.cantidad_deudores));

    if (!datos.cantidad_deudores) {
      mostrar(caja, false);
      /* El vacío de esta pantalla es una buena noticia y se dice como tal. Un
         "no hay datos" haría dudar de si el cálculo corrió. */
      lista.innerHTML =
        '<p class="lista-vacia">' +
        (soloVencidos()
          ? 'Ninguna unidad está atrasada. Las que deben el mes corriente ' +
            'todavía están en término: cambiá el filtro para verlas.'
          : 'Ninguna unidad debe nada en este edificio. El consorcio está al día.') +
        '</p>';
      return;
    }

    texto(caja.querySelector('[data-deudores-monto]'),
          window.Moneda.pesos(datos.total));

    var chips = [
      '<span class="chip">' +
        datos.cantidad_deudores +
        (datos.cantidad_deudores === 1 ? ' unidad de ' : ' unidades de ') +
        datos.cantidad_unidades +
      '</span>'
    ];

    /* Lo vencido va en su propio chip y con el color del semáforo, porque es
       el número que decide si el edificio tiene un problema de cobranza. */
    if (Number(datos.total_vencido) > 0) {
      chips.push('<span class="pill crit">' +
        window.Moneda.pesos(datos.total_vencido) + ' vencido</span>');
    }

    caja.querySelector('[data-deudores-chips]').innerHTML = chips.join('');
    mostrar(caja, true);

    /* **No se reordena acá.** El orden es una regla de negocio —primero la que
       debe desde hace más tiempo— y la resuelve el servicio. Un `sort` en el
       navegador sería una segunda versión de esa regla. */
    lista.innerHTML = datos.deudores.map(htmlDeDeudor).join('');
  }

  function cargarDeudores() {
    if (!estado.edificioId) return;

    var lista = $('#lista-deudores');
    lista.innerHTML = window.Cargando.html();
    mostrarError('deudores', '');

    var ruta = '/edificios/' + estado.edificioId + '/deudores' +
               (soloVencidos() ? '?solo_vencidos=true' : '');

    return window.Api
      .get(ruta)
      .then(function (datos) {
        estado.deudores = datos.deudores;
        pintarDeudores(datos);
      })
      .catch(function (error) {
        lista.innerHTML = '';
        mostrarError('deudores', error.message);
      });
  }

  /* ------------------------------------------------ el detalle del deudor -- */

  /* Una línea por período impago, con el prorrateo y el recargo **separados**.
     Es la regla de `F2-T11`: es un solo saldo, pero un número único más grande
     de lo esperado hace creer que el sistema se equivocó, y eso es la llamada
     telefónica que esta pantalla existe para evitar. */
  function htmlDePeriodoImpago(periodo) {
    var partes = ['expensa ' + window.Moneda.pesos(periodo.monto_expensa)];

    if (Number(periodo.recargo_mora) > 0) {
      partes.push('recargo ' + window.Moneda.pesos(periodo.recargo_mora));
    }
    if (Number(periodo.saldo_a_favor_aplicado) > 0) {
      partes.push('saldo a favor ' +
                  window.Moneda.pesos(periodo.saldo_a_favor_aplicado));
    }

    return '' +
      '<div class="fila-lista content-glass">' +
        '<div class="fila-lista-dato">' +
          '<b>' + escapar(window.Moneda.periodoLargo(periodo.periodo)) + '</b>' +
          '<span>' + partes.join(' · ') + '</span>' +
        '</div>' +
        '<div class="fila-lista-acciones">' +
          '<span class="chip">' + window.Moneda.pesos(periodo.total_a_pagar) +
          '</span>' +
        '</div>' +
      '</div>';
  }

  function verDeudor(departamentoId) {
    var deudor = (estado.deudores || []).filter(function (d) {
      return d.departamento_id === departamentoId;
    })[0];
    if (!deudor) return;

    mostrarError('deudores', '');
    estado.ultimoFoco = document.activeElement;

    /* Las liquidaciones de la unidad salen del endpoint que ya existe para
       "Mi cuenta" (`F2-T06`), que un administrador puede llamar. No hace falta
       backend nuevo: lo que esta pantalla agrega es cruzarlas con la lista de
       periodos impagos que trajo el deudor. */
    return window.Api
      .get('/edificios/' + estado.edificioId +
           '/departamentos/' + departamentoId + '/expensas')
      .then(function (liquidaciones) {
        var impagos = deudor.periodos_impagos || [];
        var delDeudor = liquidaciones.filter(function (l) {
          return impagos.indexOf(l.periodo) !== -1;
        });

        texto($('#titulo-modal-deudor'), 'Unidad ' + deudor.identificador);
        texto($('[data-sub-modal-deudor]'),
          'Piso ' + deudor.piso_numero + ' · ' + textoDelAtraso(deudor) + '.');

        texto($('[data-deudor-saldo]'), window.Moneda.pesos(deudor.saldo));

        var chips = [
          '<span class="chip">' + impagos.length +
            (impagos.length === 1 ? ' período impago' : ' períodos impagos') +
          '</span>'
        ];
        if (Number(deudor.vencido) > 0) {
          chips.push('<span class="chip">' +
            window.Moneda.pesos(deudor.vencido) + ' vencido</span>');
        }
        $('[data-deudor-chips]').innerHTML = chips.join('');

        /* **La nota dice de dónde sale cada número y cuál es el que manda.**
           Las líneas de abajo son lo que se liquidó en cada período; si la
           unidad pagó una parte, eso no se ve período por período y sí se ve
           en el saldo de arriba. Decirlo evita que alguien sume las líneas y
           crea que el saldo está mal. */
        texto($('[data-nota-deudor]'),
          'Cada línea es lo que se le liquidó en ese período, con el recargo ' +
          'por mora separado del prorrateo. Si hubo un pago parcial, la ' +
          'diferencia está en el saldo de arriba, que es el número que hay ' +
          'que cobrar.');

        $('[data-deudor-periodos]').innerHTML = delDeudor.length
          ? delDeudor.map(htmlDePeriodoImpago).join('')
          : '<p class="lista-vacia">No se encontraron las liquidaciones de ' +
            'estos períodos. El saldo de arriba sigue siendo el correcto.</p>';

        $('#modal-deudor').classList.add('abierto');
        $('[data-cerrar-deudor]').focus();
      })
      .catch(function (error) {
        mostrarError('deudores', error.message);
      });
  }

  function cerrarModalDeudor() {
    $('#modal-deudor').classList.remove('abierto');

    if (estado.ultimoFoco && document.contains(estado.ultimoFoco)) {
      estado.ultimoFoco.focus();
    }
    estado.ultimoFoco = null;
  }

  function modalDeudorAbierto() {
    return $('#modal-deudor').classList.contains('abierto');
  }

  function engancharDeudores() {
    $('#filtro-deudores').addEventListener('change', cargarDeudores);

    document.querySelectorAll('[data-cerrar-deudor]').forEach(function (boton) {
      boton.addEventListener('click', cerrarModalDeudor);
    });

    /* Solo lectura, así que cierra tocando el velo: no hay nada a medio tipear
       que perder, al contrario del modal de un gasto. */
    $('#modal-deudor').addEventListener('click', function (evento) {
      if (evento.target === $('#modal-deudor')) cerrarModalDeudor();
    });

    $('#lista-deudores').addEventListener('click', function (evento) {
      var ver = evento.target.closest('[data-ver-deudor]');
      if (ver) {
        verDeudor(parseInt(ver.getAttribute('data-ver-deudor'), 10));
      }
    });
  }

  /* --------------------------------------------------------- el arranque -- */

  function engancharEventos() {
    $('#boton-nuevo-gasto').addEventListener('click', function () { abrirModal(null); });
    $('#formulario-gasto').addEventListener('submit', guardar);
    $('#gasto-rubro').addEventListener('change', actualizarAyudaDeRubro);

    document.querySelectorAll('[data-cerrar-gasto]').forEach(function (boton) {
      boton.addEventListener('click', cerrarModal);
    });

    /* El clic en el fondo cierra el modal; el clic adentro no. Sin el chequeo
       del target, cualquier clic dentro del formulario lo cerraria. */
    $('#modal-gasto').addEventListener('click', function (evento) {
      if (evento.target === $('#modal-gasto')) cerrarModal();
    });

    document.addEventListener('keydown', function (evento) {
      if (evento.key !== 'Escape' || window.Confirmar.abierto()) return;
      if (modalAbierto()) cerrarModal();
      if ($('#modal-expensa').classList.contains('abierto')) cerrarModalExpensa();
      if (modalDeRechazoAbierto()) cerrarModalDeRechazo();
      if (modalDeudorAbierto()) cerrarModalDeudor();
    });

    /* **Delegacion y no un listener por fila.** El listado se redibuja con
       innerHTML en cada filtro y en cada guardado: los listeners de las filas
       viejas se van con el HTML, y engancharlos de nuevo cada vez es la forma
       de terminar con botones que no responden. */
    $('#lista-gastos').addEventListener('click', function (evento) {
      var editar = evento.target.closest('[data-editar]');
      if (editar) {
        var id = parseInt(editar.getAttribute('data-editar'), 10);
        window.Api
          .get('/edificios/' + estado.edificioId + '/gastos?' + filtrosActuales())
          .then(function (datos) {
            var gasto = datos.gastos.filter(function (g) { return g.id === id; })[0];
            if (gasto) abrirModal(gasto);
          })
          .catch(function (error) { mostrarError('gastos', error.message); });
        return;
      }

      var borrarlo = evento.target.closest('[data-borrar]');
      if (borrarlo) borrar(parseInt(borrarlo.getAttribute('data-borrar'), 10));
    });
  }


  /* =========================================================================
     MI CUENTA DEL RESIDENTE (F2-T22)
     =========================================================================

     La otra audiencia del archivo. Hasta esta tarea el residente no entraba:
     `Layout.montar` le cerraba la puerta porque adentro no habia nada para el.
     Ahora el porton acepta los cuatro roles y es el rol el que decide que rama
     corre — `arrancarGestion` o `arrancarMiCuenta`— y las dos ramas no
     comparten ni un pedido al backend.

     =========================================================================
     NINGUNA RUTA DE ESTA RAMA PIDE UN EDIFICIO
     =========================================================================

     `/mis-unidades` y `/mis-pagos` resuelven todo desde el token. El residente
     no tiene por que saber en que edificio esta su unidad dentro del sistema,
     ni cual es el id de su piso: entra, ve lo que debe, y paga. El unico
     endpoint que si lleva el edificio en la ruta es el de las liquidaciones de
     la unidad (`F2-T06`), y el id sale de la propia cuenta que ya trajo
     `/mis-unidades` — nunca de la URL.

     Por eso esta rama **no toca `estado.edificioId` ni el `?edificio=` de la
     URL**: ese parametro es de la vista de gestion, donde cambiar de edificio
     es una accion real.

     =========================================================================
     LOS TRES NUMEROS DEL SALDO VAN SEPARADOS, Y ES UNA REGLA DEL MODULO
     =========================================================================

     `deuda`, `pendiente_de_confirmar` y `saldo_a_favor` llegan por separado y
     se muestran por separado (`F2-T08`). Netearlos en la pantalla mezclaria
     plata verificada con plata declarada, que es la distincion que todo el
     modulo financiero existe para mantener: **lo pendiente no baja la deuda**,
     pero se muestra, porque si no el residente ve su saldo intacto y vuelve a
     pagar.

     Y los tres montos de la liquidacion tambien van separados (decidido el
     2026-11-13): lo que le toca de los gastos, el recargo por lo que
     arrastraba y el saldo a favor aplicado. Un solo total no le permite
     entender por que este mes le vino distinto, y es ahi donde llama por
     telefono.

     =========================================================================
     EL SEMAFORO NO APARECE ACA, Y NO ES UN OLVIDO
     =========================================================================

     En Deudores (`F2-T20`) la fila lleva `.pill` con el color del estado, y
     esta bien: la severidad la calcula `services/deudores.py` y la manda. Aca
     **no hay severidad en la respuesta**, asi que pintar una expensa impaga de
     rojo seria calcular el color en el navegador — lo unico que la regla de
     esa tarea prohibe, porque entonces el Dashboard Visual y esta pantalla
     podrian pintar la misma unidad de colores distintos.

     Asi que el estado de cada periodo se dice con palabras en una `.rol-badge`
     neutra. Si alguna vez el backend manda la severidad del residente, esto
     pasa a `.pill` y se saca esta nota.
     ====================================================================== */

  var SECCIONES = [
    { id: 'cuenta',   etiqueta: 'Mi cuenta' },
    { id: 'expensas', etiqueta: 'Mis expensas' },
    { id: 'pagos',    etiqueta: 'Mis pagos' }
  ];

  /* ------------------------------------------------- las tres secciones -- */

  function construirSecciones() {
    var caja = $('#secciones-mi-cuenta');

    caja.innerHTML = SECCIONES.map(function (s, i) {
      return '<button type="button"' + (i === 0 ? ' class="activo"' : '') +
             ' data-seccion-ir="' + s.id + '">' + escapar(s.etiqueta) + '</button>';
    }).join('');

    mostrar(caja, true);
    mostrar(document.querySelector('[data-seccion="cuenta"]'), true);

    /* Mismo reparto que en gestion: la piel —el indicador deslizante, el
       teclado, el aria-selected— la maneja view-switch.js, que se engancha
       solo. Aca solo se muestra y se oculta el panel. */
    caja.addEventListener('click', function (evento) {
      var boton = evento.target.closest('button[data-seccion-ir]');
      if (!boton) return;

      SECCIONES.forEach(function (s) {
        mostrar(document.querySelector('[data-seccion="' + s.id + '"]'),
                s.id === boton.getAttribute('data-seccion-ir'));
      });
    });
  }

  /* ---------------------------------------------------- la unidad activa -- */

  function cuentaActiva() {
    return (estado.cuentas || []).filter(function (c) {
      return c.departamento_id === estado.unidadId;
    })[0] || null;
  }

  function construirSelectorDeUnidades() {
    var campo = $('#campo-unidad');
    var selector = $('#selector-unidad');

    selector.innerHTML = estado.cuentas.map(function (c) {
      /* El nombre del edificio va en la etiqueta porque un propietario puede
         tener unidades en dos consorcios distintos, y "1A" sin el edificio no
         alcanza para distinguirlas. */
      return '<option value="' + c.departamento_id + '">' +
             escapar(c.identificador + ' · ' + c.edificio_nombre) + '</option>';
    }).join('');

    selector.value = String(estado.unidadId);

    /* **Con una sola unidad el selector no se muestra.** Es la regla que pide
       la tarea y es mas fuerte que la del selector de edificio: el inquilino
       tiene una unidad y nunca tiene nada que elegir, y hacerle elegir entre
       una opcion es pedirle que confirme un dato que ya sabemos. */
    mostrar(campo, estado.cuentas.length > 1);

    selector.addEventListener('change', function () {
      estado.unidadId = parseInt(selector.value, 10);
      mostrarError('cuenta', '');
      mostrar($('#exito-cuenta'), false);
      cargarUnidad();
    });
  }

  /* ------------------------------------------------------------ el saldo -- */

  function pintarSaldo(cuenta) {
    var caja = $('#total-mi-cuenta');

    /* **"Al dia" lo decide el backend y no una comparacion de acá.**
       `esta_al_dia` sale de `services/pagos.py`, que es el mismo lugar del que
       sale el calculo de deudores: preguntar `deuda > 0` en el navegador es
       escribir la regla por segunda vez, y el dia que el servicio decida que
       una diferencia de centavos no cuenta, esta pantalla seguiria diciendo
       que debe. */
    texto(caja.querySelector('[data-cuenta-titulo]'),
          cuenta.esta_al_dia ? 'Estás al día' : 'Lo que debés hoy');
    texto(caja.querySelector('[data-cuenta-monto]'),
          window.Moneda.pesos(cuenta.deuda));

    var chips = [];

    /* **Lo pendiente de confirmar se nombra siempre que exista, incluso si la
       deuda ya quedo en cero.** Es el caso en que mas falta hace: alguien que
       informo todo lo que debia ve "$0,00" y cree que ya esta cerrado, cuando
       en realidad la administracion todavia no lo verifico. */
    if (Number(cuenta.pendiente_de_confirmar) > 0) {
      chips.push('<span class="chip">' +
        window.Moneda.pesos(cuenta.pendiente_de_confirmar) +
        ' informado, sin confirmar</span>');
    }
    if (Number(cuenta.saldo_a_favor) > 0) {
      chips.push('<span class="chip">' +
        window.Moneda.pesos(cuenta.saldo_a_favor) + ' a tu favor</span>');
    }
    if (estado.cuentas.length > 1) {
      chips.push('<span class="chip">unidad ' + escapar(cuenta.identificador) +
                 '</span>');
    }

    /* En que calidad figura esta persona en esa unidad. Va siempre: es el dato
       que explica por que el inquilino ve la expensa y por que el propietario
       la ve igual aunque no viva ahi, y un vinculo mal cargado es una de las
       cosas que mas llamadas genera. Verlo escrito permite reclamarlo. */
    chips.push('<span class="chip">como ' + escapar(cuenta.vinculo) + '</span>');

    caja.querySelector('[data-cuenta-chips]').innerHTML = chips.join('');
    mostrar(caja, true);
  }

  /* ----------------------------------------- el aviso del saldo a favor -- */

  /* El periodo de `cuenta.periodos` que corresponde a una liquidacion. Son dos
     respuestas distintas del backend —una trae lo liquidado, la otra lo pagado—
     y se cruzan por `expensa_id`, que es la clave que las dos traen. */
  function periodoDeLaCuenta(cuenta, expensaId) {
    return (cuenta.periodos || []).filter(function (p) {
      return p.expensa_id === expensaId;
    })[0] || null;
  }

  function pintarAvisoDeSaldoAFavor(cuenta, liquidacion) {
    var aviso = $('#aviso-saldo-a-favor');

    if (!liquidacion || !(Number(liquidacion.saldo_a_favor_aplicado) > 0)) {
      mostrar(aviso, false);
      return;
    }

    var periodo = periodoDeLaCuenta(cuenta, liquidacion.expensa_id);
    var falta = periodo ? Number(periodo.saldo) : 0;

    /* **El caso que genera el problema real**, y el unico que merece un aviso
       destacado: el saldo a favor se aplico pero NO alcanzo. Quien pago por
       adelantado cree que esta cubierto y no vuelve a mirar hasta que le
       reclaman. Si alcanzo, no hay nada que avisar: la linea de la liquidacion
       ya lo dice. */
    if (!(falta > 0)) {
      mostrar(aviso, false);
      return;
    }

    texto($('[data-texto-aviso-saldo]'),
      'Se aplicaron ' + window.Moneda.pesos(liquidacion.saldo_a_favor_aplicado) +
      ' de tu saldo a favor a la expensa de ' +
      window.Moneda.periodoLargo(liquidacion.periodo) + ', y no alcanzó: ' +
      'quedan ' + window.Moneda.pesos(falta) + ' por pagar.');
    mostrar(aviso, true);
  }

  /* --------------------------------------------- los datos para pagar -- */

  function pintarDatosDeCobro(cuenta) {
    var hay = !!(cuenta.cbu || cuenta.alias_cbu);

    /* Se escriben con `textContent` y sin enmascarar: son los datos de cobro
       del consorcio, no de una persona, y lo que la gente hace con ellos es
       copiarlos y pegarlos en la app del banco. Enmascarar un CBU que hay que
       copiar lo volveria inservible. */
    texto($('#cbu-del-consorcio'), cuenta.cbu || '—');
    texto($('#alias-del-consorcio'), cuenta.alias_cbu || '—');

    mostrar($('#datos-de-cobro'), hay);
    mostrar($('#sin-datos-de-cobro'), !hay);
  }

  /* --------------------------------------------- la expensa del periodo -- */

  function filaDeMonto(etiqueta, explicacion, monto, signo) {
    return '' +
      '<div class="fila-lista content-glass">' +
        '<div class="fila-lista-dato">' +
          '<b>' + escapar(etiqueta) + '</b>' +
          '<span>' + escapar(explicacion) + '</span>' +
        '</div>' +
        '<div class="fila-lista-acciones">' +
          '<span class="chip">' + (signo || '') + window.Moneda.pesos(monto) +
          '</span>' +
        '</div>' +
      '</div>';
  }

  function pintarMiExpensa(cuenta) {
    var liquidacion = (estado.liquidaciones || [])[0] || null;
    var bloqueRubros = $('#bloque-rubros-mi-expensa');

    if (!liquidacion) {
      texto($('[data-titulo-mi-expensa]'), 'Expensa del período');
      texto($('[data-nota-mi-expensa]'), '');
      $('#lista-mi-expensa').innerHTML =
        '<p class="lista-vacia"><b>Todavía no hay ninguna expensa publicada ' +
        'para tu unidad</b>Cuando la administración publique la del mes, ' +
        'aparece acá con el detalle de en qué se gastó.</p>';
      mostrar(bloqueRubros, false);
      return;
    }

    texto($('[data-titulo-mi-expensa]'),
      'Expensa de ' + window.Moneda.periodoLargo(liquidacion.periodo));
    texto($('[data-nota-mi-expensa]'),
      'Publicada el ' + window.Moneda.fecha(liquidacion.publicada_en) +
      '. Tu coeficiente es ' + window.Moneda.numero(liquidacion.coeficiente) +
      '% del gasto del consorcio.');

    /* **Las tres lineas de la decision del 2026-11-13.** El recargo y el saldo
       a favor se muestran **solo si existen**: una linea que diga "recargo
       $0,00" todos los meses es ruido que tapa justamente el mes en que si
       hubo recargo. */
    var filas = [
      filaDeMonto('Gastos del mes que te tocan',
                  'tu parte del total del consorcio, por coeficiente',
                  liquidacion.monto_expensa)
    ];

    if (Number(liquidacion.recargo_mora) > 0) {
      filas.push(filaDeMonto('Recargo por mora',
        'por lo que quedó impago de períodos anteriores',
        liquidacion.recargo_mora));
    }
    if (Number(liquidacion.saldo_a_favor_aplicado) > 0) {
      /* El signo menos escrito: es lo unico de la lista que RESTA, y sin el
         signo las tres lineas se leen como tres cosas que se suman y el total
         no cierra. */
      filas.push(filaDeMonto('Saldo a favor aplicado',
        'de lo que habías pagado de más',
        liquidacion.saldo_a_favor_aplicado, '− '));
    }

    filas.push(filaDeMonto('Total a pagar',
      'lo que te quedó esta liquidación', liquidacion.total_a_pagar));

    /* Lo pagado y lo que falta, solo cuando hay algo pagado: en un periodo
       recien publicado estas dos lineas dirian "$0,00" y "el total otra vez". */
    var periodo = periodoDeLaCuenta(cuenta, liquidacion.expensa_id);
    if (periodo && Number(periodo.pagado_confirmado) > 0) {
      filas.push(filaDeMonto('Ya pagaste y está confirmado',
        'verificado por la administración contra el banco',
        periodo.pagado_confirmado));
      filas.push(filaDeMonto('Te queda por pagar de este período',
        Number(periodo.pendiente_de_confirmar) > 0
          ? 'sin contar lo que informaste y todavía no está confirmado'
          : 'según lo que está confirmado hasta hoy',
        periodo.saldo));
    }

    $('#lista-mi-expensa').innerHTML = filas.join('');

    /* La apertura por rubro: son los gastos del EDIFICIO y no los suyos, asi
       que el porcentaje de cada rubro se calcula sobre el total del edificio.
       `htmlDeRubro` es el mismo que usa el detalle de una liquidacion en la
       vista de gestion — el residente y el administrador leen la misma apertura
       con el mismo formato, que es parte de que los dos hablen del mismo
       documento. */
    texto($('[data-nota-rubros-mi-expensa]'),
      'El consorcio gastó ' + window.Moneda.pesos(liquidacion.total_edificio) +
      ' en ' + window.Moneda.periodoLargo(liquidacion.periodo) +
      '. Esto es el total del edificio, y a tu unidad le toca el ' +
      window.Moneda.numero(liquidacion.coeficiente) + '%.');

    $('#lista-rubros-mi-expensa').innerHTML = liquidacion.detalle.map(
      function (linea) { return htmlDeRubro(linea, liquidacion.total_edificio); }
    ).join('');

    mostrar(bloqueRubros, liquidacion.detalle.length > 0);
  }

  /* ------------------------------------------- el historial de expensas -- */

  /* Lo que dice la etiqueta de estado de un periodo. **En palabras y no en
     color** (ver la nota de arriba): la severidad no viaja en esta respuesta,
     asi que deducir un color aca seria calcularlo en el navegador. */
  function estadoDelPeriodo(periodo) {
    if (!periodo) return 'Sin datos de pago';
    if (periodo.esta_pago) return 'Pagada';
    if (Number(periodo.pendiente_de_confirmar) > 0) {
      return 'Informado, sin confirmar';
    }
    return 'Pendiente de pago';
  }

  function htmlDeMiExpensa(liquidacion, cuenta) {
    var periodo = periodoDeLaCuenta(cuenta, liquidacion.expensa_id);

    var detalles = ['total ' + window.Moneda.pesos(liquidacion.total_a_pagar)];
    if (Number(liquidacion.recargo_mora) > 0) {
      detalles.push('incluye ' + window.Moneda.pesos(liquidacion.recargo_mora) +
                    ' de recargo');
    }
    if (Number(liquidacion.saldo_a_favor_aplicado) > 0) {
      detalles.push('menos ' +
                    window.Moneda.pesos(liquidacion.saldo_a_favor_aplicado) +
                    ' de saldo a favor');
    }
    if (periodo && Number(periodo.saldo) > 0) {
      detalles.push('te falta ' + window.Moneda.pesos(periodo.saldo));
    }

    return '' +
      '<article class="fila-lista content-glass">' +
        '<div class="fila-lista-dato">' +
          '<b>' + escapar(window.Moneda.periodoLargo(liquidacion.periodo)) +
          '</b>' +
          '<span>' + escapar(detalles.join(' · ')) + '</span>' +
        '</div>' +
        '<div class="fila-lista-acciones">' +
          '<span class="fila-lista-estado rol-badge">' +
            escapar(estadoDelPeriodo(periodo)) +
          '</span>' +
          '<div class="fila-lista-botones">' +
            '<button type="button" class="icon-btn icon-btn-sm" ' +
                    'data-ver-mi-expensa="' + liquidacion.expensa_id + '" ' +
                    'aria-label="Ver en qué se gastó ' +
                    escapar(window.Moneda.periodoLargo(liquidacion.periodo)) +
                    '" title="Ver el detalle">' + svg(ICONO_VER) + '</button>' +
          '</div>' +
        '</div>' +
      '</article>';
  }

  function pintarMisExpensas(cuenta) {
    var lista = $('#lista-mis-expensas');
    var cuantas = (estado.liquidaciones || []).length;

    texto($('[data-contador-mis-expensas]'), String(cuantas));

    if (!cuantas) {
      lista.innerHTML =
        '<p class="lista-vacia"><b>Todavía no hay expensas publicadas para tu ' +
        'unidad</b>Una liquidación en borrador no se muestra: el monto puede ' +
        'cambiar hasta que la administración la publique.</p>';
      return;
    }

    lista.innerHTML = estado.liquidaciones.map(function (l) {
      return htmlDeMiExpensa(l, cuenta);
    }).join('');
  }

  /* -------------------------------------------------------- mis pagos -- */

  function htmlDeMiPago(pago) {
    var detalles = [
      window.Moneda.periodoLargo(pago.periodo),
      pago.medio_pago_etiqueta,
      'pagado el ' + window.Moneda.fecha(pago.fecha)
    ];

    /* La unidad solo si tiene mas de una: en el caso normal es el mismo dato
       repetido en todas las filas. */
    if (estado.cuentas.length > 1) {
      detalles.push('unidad ' + pago.identificador);
    }

    var etiquetas = {
      pendiente: 'Esperando confirmación',
      confirmado: 'Confirmado',
      rechazado: 'Rechazado'
    };

    /* `.pendiente` es el borde completo con el **acento de marca**, no el
       naranja del semaforo: un pago sin conciliar no es un estado del
       edificio. Misma decision que la fila de la cola de conciliacion. */
    var clase = pago.estado === 'pendiente' ? ' pendiente' : '';

    return '' +
      '<article class="fila-lista content-glass' + clase + '">' +
        '<div class="fila-lista-dato">' +
          '<b>' + window.Moneda.pesos(pago.monto) + '</b>' +
          '<span>' + escapar(detalles.join(' · ')) + '</span>' +
          /* **El texto lo arma el servidor, y en el rechazo trae el motivo
             adentro.** La pantalla no lo compone a partir del estado: tres
             pantallas traduciendo el mismo estado a palabras son tres textos
             que algun dia dicen cosas distintas. */
          '<span>' + escapar(pago.mensaje) + '</span>' +
        '</div>' +
        '<div class="fila-lista-acciones">' +
          '<span class="fila-lista-estado rol-badge">' +
            escapar(etiquetas[pago.estado] || pago.estado) +
          '</span>' +
          '<div class="fila-lista-botones">' + botonDeComprobante(pago) +
          '</div>' +
        '</div>' +
      '</article>';
  }

  function pintarMisPagos() {
    var lista = $('#lista-mis-pagos');

    /* Solo los de la unidad que se esta mirando. El endpoint devuelve los de
       todas mis unidades en un solo pedido —son los pagos de una persona, no la
       cola de un consorcio— y filtrar aca evita un pedido por cada cambio de
       unidad en el selector. */
    var mios = (estado.misPagos || []).filter(function (p) {
      return p.departamento_id === estado.unidadId;
    });

    texto($('[data-contador-mis-pagos]'), String(mios.length));

    if (!mios.length) {
      lista.innerHTML =
        '<p class="lista-vacia"><b>Todavía no informaste ningún pago</b>' +
        'Cuando transfieras, avisalo acá: la administración lo confirma contra ' +
        'el movimiento del banco y recién entonces baja tu saldo.</p>';
      return;
    }

    lista.innerHTML = mios.map(htmlDeMiPago).join('');
  }

  /* ----------------------------------------------- el detalle de un mes -- */

  function verMiExpensa(expensaId) {
    var liquidacion = (estado.liquidaciones || []).filter(function (l) {
      return l.expensa_id === expensaId;
    })[0];
    if (!liquidacion) return;

    estado.ultimoFoco = document.activeElement;

    var largo = window.Moneda.periodoLargo(liquidacion.periodo);

    texto($('#titulo-modal-mi-expensa'), 'Expensa de ' + largo);
    texto($('[data-sub-mi-expensa]'),
      'Publicada el ' + window.Moneda.fecha(liquidacion.publicada_en) + '.');

    texto($('[data-mi-expensa-total]'),
      window.Moneda.pesos(liquidacion.total_a_pagar));

    var chips = ['<span class="chip">coeficiente ' +
                 window.Moneda.numero(liquidacion.coeficiente) + '%</span>'];
    if (Number(liquidacion.recargo_mora) > 0) {
      chips.push('<span class="chip">recargo ' +
                 window.Moneda.pesos(liquidacion.recargo_mora) + '</span>');
    }
    if (Number(liquidacion.saldo_a_favor_aplicado) > 0) {
      chips.push('<span class="chip">− ' +
                 window.Moneda.pesos(liquidacion.saldo_a_favor_aplicado) +
                 ' de saldo a favor</span>');
    }
    $('[data-mi-expensa-chips]').innerHTML = chips.join('');

    texto($('[data-nota-mi-expensa-modal]'),
      'El consorcio gastó ' + window.Moneda.pesos(liquidacion.total_edificio) +
      ' en ' + largo + ', y a tu unidad le toca el ' +
      window.Moneda.numero(liquidacion.coeficiente) + '%.');

    $('[data-mi-expensa-rubros]').innerHTML = liquidacion.detalle.map(
      function (linea) { return htmlDeRubro(linea, liquidacion.total_edificio); }
    ).join('');

    $('#modal-mi-expensa').classList.add('abierto');
    $('[data-cerrar-mi-expensa]').focus();
  }

  function cerrarModalMiExpensa() {
    $('#modal-mi-expensa').classList.remove('abierto');
    if (estado.ultimoFoco && estado.ultimoFoco.focus) estado.ultimoFoco.focus();
  }

  function modalMiExpensaAbierto() {
    return $('#modal-mi-expensa').classList.contains('abierto');
  }

  /* ----------------------------------------------- informar un pago -- */

  /* Hoy, en la zona del reloj de quien mira, como "2026-11-15".
     **`new Date()` sin argumentos y armada a mano**, nunca
     `new Date().toISOString()`: el ISO esta en UTC y en Argentina (UTC-3) de
     21:00 a medianoche devuelve el dia siguiente. Es la misma trampa que
     `moneda.js` evita partiendo el texto en vez de parsear la fecha. */
  function hoyLocal() {
    var hoy = new Date();
    var mes = hoy.getMonth() + 1;
    var dia = hoy.getDate();
    return hoy.getFullYear() + '-' +
           (mes < 10 ? '0' + mes : mes) + '-' +
           (dia < 10 ? '0' + dia : dia);
  }

  function saldoDelPeriodo(cuenta, expensaId) {
    var periodo = periodoDeLaCuenta(cuenta, expensaId);
    return periodo ? Number(periodo.saldo) : 0;
  }

  function construirSelectorDePeriodos(cuenta) {
    var selector = $('#pago-periodo');

    selector.innerHTML = (estado.liquidaciones || []).map(function (l) {
      var falta = saldoDelPeriodo(cuenta, l.expensa_id);
      var etiqueta = window.Moneda.periodoLargo(l.periodo) +
        (falta > 0 ? ' — te falta ' + window.Moneda.pesos(falta)
                   : ' — pagada');
      return '<option value="' + l.expensa_id + '">' + escapar(etiqueta) +
             '</option>';
    }).join('');

    /* **Arranca en el periodo impago mas viejo**, no en el mas reciente. Es el
       orden en que se cobra una deuda y el que evita el caso molesto: pagar el
       mes corriente y seguir figurando como deudor por uno de hace tres meses.
       `liquidaciones` viene del backend de la mas nueva a la mas vieja, asi que
       el mas viejo con saldo es el ultimo que cumple. */
    var impagos = (estado.liquidaciones || []).filter(function (l) {
      return saldoDelPeriodo(cuenta, l.expensa_id) > 0;
    });
    if (impagos.length) {
      selector.value = String(impagos[impagos.length - 1].expensa_id);
    }
  }

  function prellenarMonto(cuenta) {
    var expensaId = parseInt($('#pago-periodo').value, 10);
    var falta = saldoDelPeriodo(cuenta, expensaId);

    /* Se prellena con lo que falta de ese periodo porque es lo que paga la
       enorme mayoria: el monto exacto de la expensa. Es un valor por defecto y
       no una imposicion — el campo se edita, y un pago parcial o de mas se
       acepta igual. */
    if (falta > 0) window.MontoInput.escribir($('#pago-monto'), falta);
    else $('#pago-monto').value = '';
  }

  function abrirModalDePago() {
    var cuenta = cuentaActiva();
    if (!cuenta) return;

    if (!(estado.liquidaciones || []).length) {
      /* Sin ninguna liquidacion publicada no hay contra que pagar: el backend
         exige `expensa_id`. Se dice y no se abre un formulario con un
         desplegable vacio, que es la pantalla que parece rota. */
      mostrarError('cuenta',
        'Todavía no hay ninguna expensa publicada para tu unidad, así que no ' +
        'hay nada contra qué informar un pago. Cuando la administración ' +
        'publique la del mes, el botón funciona.');
      return;
    }

    estado.ultimoFoco = document.activeElement;

    var formulario = $('#formulario-informar-pago');
    window.Formularios.limpiarErrores(formulario);
    formulario.reset();

    construirSelectorDePeriodos(cuenta);
    prellenarMonto(cuenta);
    $('#pago-fecha').value = hoyLocal();

    $('#modal-informar-pago').classList.add('abierto');
    $('#pago-periodo').focus();
  }

  function cerrarModalDePago() {
    $('#modal-informar-pago').classList.remove('abierto');
    if (estado.ultimoFoco && estado.ultimoFoco.focus) estado.ultimoFoco.focus();
  }

  function modalDePagoAbierto() {
    return $('#modal-informar-pago').classList.contains('abierto');
  }

  function cuerpoDelPago() {
    var cuerpo = {
      expensa_id: parseInt($('#pago-periodo').value, 10),
      /* El valor crudo, con punto decimal y sin separadores de miles. Mandar
         el texto del input tal cual convertiria "1.234" en mil doscientos
         treinta y cuatro pesos... o en uno con veintitres centavos. */
      monto: window.MontoInput.valorDe($('#pago-monto')),
      fecha: $('#pago-fecha').value,
      medio_pago: $('#pago-medio').value,
      /* **La unidad va explicita siempre que haya mas de una.** El backend la
         resuelve solo cuando hay una sola, y con dos contesta "elegi una
         unidad": mandarla desde aca es lo que hace que el selector de arriba
         signifique algo. */
      departamento_id: estado.unidadId
    };

    var comprobante = $('#pago-comprobante').value.trim();
    if (comprobante) cuerpo.comprobante_url = comprobante;

    return cuerpo;
  }

  function informarPago(evento) {
    evento.preventDefault();

    var formulario = $('#formulario-informar-pago');
    var boton = $('[data-guardar-pago]');
    window.Formularios.limpiarErrores(formulario);
    mostrar($('#exito-cuenta'), false);
    boton.disabled = true;

    window.Api
      .post('/mis-pagos', cuerpoDelPago())
      .then(function (pago) {
        cerrarModalDePago();

        /* **El mensaje que muestra la pantalla es el del servidor**, que es el
           que explica que el saldo no se movio todavia. Sin ese aviso, el
           residente ve su saldo intacto y vuelve a pagar — y entonces hay dos
           pagos del mismo mes esperando conciliacion. */
        texto($('[data-texto-exito-cuenta]'), pago.mensaje);
        mostrar($('#exito-cuenta'), true);

        return cargarUnidad();
      })
      .catch(function (error) {
        var marcados = window.Formularios.marcarErrores(formulario, error.campos);
        if (!marcados) {
          /* **El error va DENTRO del modal**, en el resumen del formulario. Si
             fuera a la caja de la pantalla quedaria detras del velo, y la
             persona veria un formulario que no hace nada. Es un bug que ya
             paso dos veces en este proyecto. */
          var resumen = formulario.querySelector('[data-resumen-errores]');
          texto(resumen, error.message);
          mostrar(resumen, true);
        }
      })
      .then(function () { boton.disabled = false; });
  }

  /* ------------------------------------------------------------ la carga -- */

  /* Todo lo que depende de la unidad elegida. Se llama al arrancar, al cambiar
     de unidad en el selector y despues de informar un pago.

     **Los dos pedidos van juntos y no uno tras otro.** Son independientes, y en
     serie la pantalla tarda el doble en estar completa. El de `/mis-unidades`
     se repite aca a proposito: informar un pago cambia
     `pendiente_de_confirmar`, asi que el estado de cuenta en memoria quedo
     viejo — refrescar el saldo desde el cache muestra el valor anterior, que es
     el bug que el Roadmap ya anoto para `F2-T21`. */
  function cargarUnidad() {
    var cuenta = cuentaActiva();
    if (!cuenta) return;

    $('#lista-mi-expensa').innerHTML = window.Cargando.html();
    mostrarError('cuenta', '');

    return Promise
      .all([
        window.Api.get('/mis-unidades'),
        window.Api.get('/edificios/' + cuenta.edificio_id +
                       '/departamentos/' + cuenta.departamento_id + '/expensas'),
        window.Api.get('/mis-pagos')
      ])
      .then(function (respuestas) {
        estado.cuentas = respuestas[0];
        estado.liquidaciones = respuestas[1];
        estado.misPagos = respuestas[2];

        var fresca = cuentaActiva();
        if (!fresca) return;

        pintarSaldo(fresca);
        pintarAvisoDeSaldoAFavor(fresca, (estado.liquidaciones || [])[0] || null);
        pintarDatosDeCobro(fresca);
        pintarMiExpensa(fresca);
        pintarMisExpensas(fresca);
        pintarMisPagos();
      })
      .catch(function (error) {
        $('#lista-mi-expensa').innerHTML = '';
        mostrarError('cuenta', error.message);
      });
  }

  function engancharMiCuenta() {
    $('#formulario-informar-pago').addEventListener('submit', informarPago);

    $('#pago-periodo').addEventListener('change', function () {
      var cuenta = cuentaActiva();
      if (cuenta) prellenarMonto(cuenta);
    });

    /* Los dos botones de "Informar un pago" —el de Mi cuenta y el de Mis
       pagos— son el mismo gesto, asi que van por delegacion y con un atributo
       en vez de dos ids y dos listeners. */
    document.addEventListener('click', function (evento) {
      if (!evento.target.closest) return;

      if (evento.target.closest('[data-informar-pago]')) {
        abrirModalDePago();
        return;
      }
      if (evento.target.closest('[data-cerrar-informar]')) {
        cerrarModalDePago();
        return;
      }
      if (evento.target.closest('[data-cerrar-mi-expensa]')) {
        cerrarModalMiExpensa();
        return;
      }

      var ver = evento.target.closest('[data-ver-mi-expensa]');
      if (ver) verMiExpensa(parseInt(ver.getAttribute('data-ver-mi-expensa'), 10));
    });

    /* El modal de solo lectura cierra tocando el velo; el del formulario no.
       Es la misma regla del resto de la pantalla: donde hay algo a medio
       tipear, un clic al costado no puede tirarlo. */
    $('#modal-mi-expensa').addEventListener('click', function (evento) {
      if (evento.target === $('#modal-mi-expensa')) cerrarModalMiExpensa();
    });

    document.addEventListener('keydown', function (evento) {
      if (evento.key !== 'Escape') return;
      if (modalDePagoAbierto()) cerrarModalDePago();
      else if (modalMiExpensaAbierto()) cerrarModalMiExpensa();
    });
  }

  function arrancarMiCuenta() {
    /* El titulo y el subtitulo de la pantalla: es la misma pagina y el rol
       decide que dice. Quien entra a ver lo que debe y lee "Todo lo del mes se
       carga aca" cree que esta en la pantalla del administrador. */
    texto($('[data-titulo-vista]'), 'Mi cuenta');
    texto($('[data-sub-vista]'),
      'Lo que debés, en qué se gastó el mes y los datos para transferir. ' +
      'Avisás tu pago acá y la administración lo confirma contra el banco.');

    return Promise
      .all([
        window.Api.get('/mis-unidades'),
        window.Api.get('/pagos/medios')
      ])
      .then(function (respuestas) {
        estado.cuentas = respuestas[0];
        estado.medios = respuestas[1];

        /* Un residente sin ninguna unidad asignada no es un error: la
           administracion todavia no lo vinculo. Va como aviso, no como la caja
           roja, y el resto de la pantalla no se dibuja porque no hay nada que
           dibujar. */
        if (!estado.cuentas.length) {
          mostrar($('#aviso-sin-unidades'), true);
          return;
        }

        estado.unidadId = estado.cuentas[0].departamento_id;

        $('#pago-medio').innerHTML = estado.medios.map(function (m) {
          return '<option value="' + escapar(m.nombre) + '">' +
                 escapar(m.etiqueta) + '</option>';
        }).join('');

        construirSelectorDeUnidades();
        construirSecciones();
        engancharMiCuenta();

        return cargarUnidad();
      });
  }

  /* Lo que queda cuando la pantalla no puede existir: el mensaje arriba y
     nada mas. Apaga las dos ramas, porque cual estaba dibujada depende del rol
     y este corte es el mismo para los cuatro. */
  function sinAcceso(mensaje) {
    mostrar($('#pestanias-financiero'), false);
    mostrar($('#secciones-mi-cuenta'), false);
    PESTANIAS.forEach(function (p) {
      mostrar(document.querySelector('[data-panel="' + p.id + '"]'), false);
    });
    SECCIONES.forEach(function (sec) {
      mostrar(document.querySelector('[data-seccion="' + sec.id + '"]'), false);
    });
    mostrarError('pantalla', mensaje);
  }

  function arrancarGestion() {
    return Promise
      .resolve()
      .then(function () {
        /* Las dos cosas que la pantalla necesita antes de poder dibujar nada:
           sobre que edificios trabaja esta persona, y cual es el catalogo de
           rubros. Van juntas en vez de una tras otra porque son
           independientes: en serie, la pantalla tarda el doble en aparecer. */
        return Promise.all([
          window.Api.get('/edificios'),
          window.Api.get('/gastos/rubros')
        ]);
      })
      .then(function (respuestas) {
        if (!respuestas) return;

        var edificios = respuestas[0];
        estado.rubros = respuestas[1];

        if (!edificios.length) {
          sinAcceso(
            'Todavía no hay ningún edificio cargado. El módulo financiero ' +
            'trabaja sobre un edificio, así que primero hay que crear uno.'
          );
          return;
        }

        /* Si la URL trae un edificio que esta persona no administra, se cae al
           primero de los suyos en vez de mostrar un 404: el enlace puede venir
           de otra persona con otra cartera, y eso no es un error de quien lo
           abrio. */
        var deLaUrl = edificioDeLaUrl();
        var existe = edificios.some(function (e) { return e.id === deLaUrl; });
        irAlEdificio(existe ? deLaUrl : edificios[0].id);

        construirSelectorDeEdificios(edificios);
        construirPestanias();
        construirFiltros();
        construirSelectoresDeRubro();
        construirFiltrosDeExpensas();
        construirFiltroDeEstado();
        construirFiltroDeDeudores();
        engancharEventos();
        engancharExpensas();
        engancharPagos();
        engancharDeudores();

        /* Las cuatro pestanias se cargan juntas y no al tocarlas. Son pedidos
           chicos, y asi las tres cosas que no hay que ir a buscar aparecen desde
           el momento en que se entra: el aviso del borrador sin publicar, la
           cola de pagos esperando conciliacion y quien debe. Las tres son plata
           quieta. */
        return Promise.all([
          cargarGastos(), cargarExpensas(), cargarPagos(), cargarDeudores()
        ]);
      });
  }

  /* ----------------------------------------------------- el reparto por rol -- */

  /* **El unico lugar del archivo donde se mira el rol.**

     `Layout.montar` hace tres cosas antes de devolver el usuario: manda al
     login si no hay sesion, dibuja el esqueleto —sidebar, topbar, backdrop— y
     resuelve el porton de roles. Si el rol no esta en la lista, su promesa no
     se resuelve y nada de lo que sigue corre.

     La lista que se le pasa son los cuatro roles juntos, y la eleccion de rama
     la hace esta funcion. Hacerlo con dos llamadas a `montar` no se puede: la
     primera que rechaza ya dibujo el "esta pantalla no es para tu rol". */
  function arrancar() {
    return window.Layout
      .montar({ roles: ROLES_DE_GESTION.concat(ROLES_DE_MI_CUENTA) })
      .then(function (usuario) {
        estado.rol = usuario.rol;

        return ROLES_DE_MI_CUENTA.indexOf(usuario.rol) !== -1
          ? arrancarMiCuenta()
          : arrancarGestion();
      })
      .catch(function (error) {
        sinAcceso(error.message);
      });
  }

  document.addEventListener('DOMContentLoaded', arrancar);
}());
