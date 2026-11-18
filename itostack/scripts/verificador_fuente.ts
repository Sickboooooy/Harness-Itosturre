// Observa una fuente oficial y entrega lo que vio, con evidencia. No decide veredictos:
// eso lo hace scripts/nucleo/veredicto.py. Uso (normalmente vía verificar.py):
//   node --experimental-strip-types verificador_fuente.ts tesis --registro 2025432 --salida DIR [--fixture f.json]
//   node --experimental-strip-types verificador_fuente.ts url --url https://www.dof.gob.mx/... --salida DIR
import { readFile } from 'node:fs/promises';
import type { BrowserContext } from 'playwright';
import { abrirNavegador, visitarConEvidencia, type Visita } from './lib/navegador_forense.ts';

const HERRAMIENTA = 'itostack-verificador/0.1.0';
const DOMINIOS_DEFECTO = ['sjf2.scjn.gob.mx', 'sjf.scjn.gob.mx', 'www.dof.gob.mx', 'dof.gob.mx', 'www.diputados.gob.mx', 'diputados.gob.mx'];

interface EntradaFixture {
  estado_http?: number;
  json?: unknown;
  html?: string;
  estado_html?: number;
  abortar?: string;
}

interface Fixture {
  tesis?: Record<string, EntradaFixture>;
  urls?: Record<string, EntradaFixture>;
}

function leerArgumentos(argv: string[]): Record<string, string> {
  const resultado: Record<string, string> = {};
  for (let i = 0; i < argv.length; i++) {
    const actual = argv[i];
    if (actual.startsWith('--')) {
      const siguiente = argv[i + 1];
      if (siguiente === undefined || siguiente.startsWith('--')) resultado[actual.slice(2)] = 'true';
      else {
        resultado[actual.slice(2)] = siguiente;
        i++;
      }
    } else if (!resultado._tipo) resultado._tipo = actual;
  }
  return resultado;
}

const AVISO_FIXTURE = '<div style="background:#b00020;color:#fff;padding:8px;font:bold 16px sans-serif">FIXTURE — DATOS FICTICIOS DE PRUEBA, NO SON CRITERIOS REALES</div>';

async function instalarFixture(contexto: BrowserContext, fixture: Fixture, base: string, rutaDetalle: string, rutaApi: string): Promise<void> {
  const prefijoApi = base + rutaApi.split('{registro}')[0];
  await contexto.route('**/*', async (ruta) => {
    const url = ruta.request().url();
    for (const [registro, entrada] of Object.entries(fixture.tesis ?? {})) {
      const urlDetalle = base + rutaDetalle.replace('{registro}', registro);
      const urlApi = base + rutaApi.replace('{registro}', registro);
      if (url !== urlDetalle && url !== urlApi) continue;
      if (entrada.abortar) return ruta.abort(entrada.abortar);
      if (url === urlApi) {
        const cuerpo = entrada.json === undefined ? '' : JSON.stringify(entrada.json, null, 2);
        return ruta.fulfill({ status: entrada.estado_http ?? 200, contentType: 'application/json; charset=utf-8', body: cuerpo });
      }
      const html = entrada.html ?? `<html><body><app-root>SJF</app-root></body></html>`;
      return ruta.fulfill({ status: entrada.estado_html ?? 200, contentType: 'text/html; charset=utf-8', body: html.replace('<body>', `<body>${AVISO_FIXTURE}`) });
    }
    for (const [direccion, entrada] of Object.entries(fixture.urls ?? {})) {
      if (url !== direccion) continue;
      if (entrada.abortar) return ruta.abort(entrada.abortar);
      const html = (entrada.html ?? '<html><body></body></html>').replace('<body>', `<body>${AVISO_FIXTURE}`);
      return ruta.fulfill({ status: entrada.estado_http ?? 200, contentType: 'text/html; charset=utf-8', body: html });
    }
    if (url.startsWith(prefijoApi)) {
      return ruta.fulfill({ status: 404, contentType: 'application/json; charset=utf-8', body: JSON.stringify({ mensaje: 'No se encontró' }) });
    }
    if (url.startsWith(base)) {
      return ruta.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: `<html><body>${AVISO_FIXTURE}<app-root>SJF</app-root></body></html>` });
    }
    // En modo fixture nada sale a la red.
    return ruta.abort('blockedbyclient');
  });
}

const CANDIDATOS: Record<string, string[]> = {
  rubro: ['rubro', 'titulo', 'rubrotesis'],
  registro: ['registrodigital', 'registro', 'ius', 'numeroregistro', 'idtesis'],
  clave: ['clavetesis', 'clave', 'numerotesis', 'numtesis', 'tesis'],
  epoca: ['epoca', 'epocadescripcion', 'descepoca', 'nombreepoca'],
  instancia: ['instancia', 'instanciadescripcion', 'organojurisdiccional', 'organoemisor', 'organo', 'sala'],
  tipo: ['tipotesis', 'tipodescripcion', 'tipojurisprudencia', 'tipo'],
  fecha_publicacion: ['fechapublicacion', 'fechapublicacionsemanario', 'fecha'],
  materia: ['materias', 'materia'],
  fuente: ['fuente', 'fuentedescripcion'],
  texto: ['texto', 'textotesis', 'contenido'],
};

const ETIQUETAS_PAGINA: Record<string, RegExp> = {
  registro: /Registro digital:\s*([0-9A-Z-]+)/i,
  instancia: /Instancia:\s*([^\n]+)/i,
  epoca: /\b([A-Za-zÁÉÍÓÚáéíóú]+)\s+Época\b/,
  clave: /Tesis:\s*([^\n]+)/i,
  tipo: /Tipo:\s*(Jurisprudencia|Aislada)/i,
  fuente: /Fuente:\s*([^\n]+)/i,
  materia: /Materia\(s\):\s*([^\n]+)/i,
};

function claveNormalizada(clave: string): string {
  return clave.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function aplanar(valor: unknown, salida: Map<string, string>, profundidad = 0): void {
  if (profundidad > 4 || valor === null || valor === undefined) return;
  if (Array.isArray(valor)) {
    if (valor.every((v) => typeof v === 'string')) return;
    for (const elemento of valor.slice(0, 1)) aplanar(elemento, salida, profundidad + 1);
    return;
  }
  if (typeof valor !== 'object') return;
  for (const [clave, interno] of Object.entries(valor as Record<string, unknown>)) {
    const llave = claveNormalizada(clave);
    if (typeof interno === 'string' || typeof interno === 'number') {
      if (!salida.has(llave)) salida.set(llave, String(interno));
    } else if (Array.isArray(interno) && interno.length && interno.every((v) => typeof v === 'string')) {
      if (!salida.has(llave)) salida.set(llave, interno.join('; '));
    } else {
      aplanar(interno, salida, profundidad + 1);
    }
  }
}

function extraerDatos(cuerpoApi: string | null, textoPagina: string, registroSolicitado: string) {
  const datos: Record<string, string> = {};
  const origen: Record<string, string> = {};
  let jsonValido = false;
  if (cuerpoApi && cuerpoApi.trim()) {
    try {
      const planos = new Map<string, string>();
      aplanar(JSON.parse(cuerpoApi), planos);
      jsonValido = true;
      for (const [campo, nombres] of Object.entries(CANDIDATOS)) {
        const encontrado = nombres.find((nombre) => planos.has(nombre) && String(planos.get(nombre)).trim());
        if (encontrado) {
          datos[campo] = String(planos.get(encontrado)).trim();
          origen[campo] = `api:${encontrado}`;
        }
      }
    } catch {
      jsonValido = false;
    }
  }
  for (const [campo, patron] of Object.entries(ETIQUETAS_PAGINA)) {
    if (datos[campo]) continue;
    const coincidencia = textoPagina.match(patron);
    if (coincidencia) {
      datos[campo] = campo === 'epoca' ? `${coincidencia[1]} Época` : coincidencia[1].trim();
      origen[campo] = 'pagina';
    }
  }
  if (!datos.registro && datos.rubro) {
    datos.registro = registroSolicitado;
    origen.registro = 'solicitud';
  }
  return { datos, origen, jsonValido };
}

function cuerpoVacio(cuerpo: string | null): boolean {
  const limpio = (cuerpo ?? '').trim();
  return limpio === '' || limpio === 'null' || limpio === '{}' || limpio === '[]';
}

async function verificarTesis(args: Record<string, string>, contexto: BrowserContext, dominios: string[], limite: number) {
  const registro = (args.registro ?? '').trim().toUpperCase();
  const modoFixture = Boolean(args.fixture);
  const formatoValido = /^\d{1,7}$/.test(registro) || (modoFixture && /^FICT-\d{4}$/.test(registro));
  const base = (args.base ?? 'https://sjf2.scjn.gob.mx').replace(/\/$/, '');
  const rutaDetalle = args['ruta-detalle'] ?? '/detalle/tesis/{registro}';
  const rutaApi = args['ruta-api'] ?? '/services/sjftesismicroservice/api/public/tesis/{registro}';
  const salidaBase = {
    tipo: 'tesis',
    identificador: registro,
    modo_fuente: modoFixture ? 'fixture' : 'real',
    herramienta: HERRAMIENTA,
  };
  if (!formatoValido) {
    return { ...salidaBase, consultado: false, motivo_no_consulta: `registro digital con formato inválido: «${registro}»`, visitas: [] };
  }
  const pagina = await contexto.newPage();
  const detalle = await visitarConEvidencia(pagina, base + rutaDetalle.replace('{registro}', registro), args.salida, 'detalle', {
    dominios, timeoutMs: limite, esperarTexto: 'Registro digital',
  });
  const api = await visitarConEvidencia(pagina, base + rutaApi.replace('{registro}', registro), args.salida, 'api', {
    dominios, timeoutMs: limite, guardarCuerpo: true,
  });
  const portalDisponible = api.estado_http !== null && api.estado_http < 500 && api.error === null;
  const noEncontrado = portalDisponible && (api.estado_http === 404 || (api.estado_http === 200 && cuerpoVacio(api.cuerpo)));
  const { datos, origen, jsonValido } = extraerDatos(api.estado_http === 200 ? api.cuerpo : null, detalle.texto, registro);
  const visitas: Omit<Visita, 'texto' | 'cuerpo'>[] = [detalle, api].map(({ texto: _t, cuerpo: _c, ...resto }) => resto);
  return {
    ...salidaBase,
    consultado: true,
    portal_disponible: portalDisponible,
    error_portal: api.error ?? (api.estado_http !== null && api.estado_http >= 500 ? `HTTP ${api.estado_http}` : null),
    no_encontrado: noEncontrado,
    estructura_reconocida: Boolean(datos.rubro),
    json_valido: jsonValido,
    datos_oficiales: datos,
    origen_datos: origen,
    visitas,
  };
}

async function verificarUrl(args: Record<string, string>, contexto: BrowserContext, dominios: string[], limite: number) {
  const url = args.url ?? '';
  const salidaBase = { tipo: 'url', identificador: url, modo_fuente: args.fixture ? 'fixture' : 'real', herramienta: HERRAMIENTA };
  let host = '';
  try {
    host = new URL(url).hostname;
  } catch {
    return { ...salidaBase, consultado: false, motivo_no_consulta: `URL inválida: «${url}»`, visitas: [] };
  }
  if (!dominios.includes(host)) {
    return { ...salidaBase, consultado: false, motivo_no_consulta: `dominio fuera de la lista oficial: ${host}`, visitas: [] };
  }
  const pagina = await contexto.newPage();
  const visita = await visitarConEvidencia(pagina, url, args.salida, 'fuente', { dominios, timeoutMs: limite });
  const titulo = await pagina.title().catch(() => '');
  const { texto, cuerpo: _c, ...resto } = visita;
  return {
    ...salidaBase,
    consultado: true,
    portal_disponible: visita.estado_http !== null && visita.estado_http < 500 && visita.error === null,
    error_portal: visita.error,
    estado_http: visita.estado_http,
    estructura_reconocida: visita.ok,
    datos_oficiales: { titulo, texto: texto.slice(0, 20000) },
    visitas: [resto],
  };
}

async function principal(): Promise<void> {
  const args = leerArgumentos(process.argv.slice(2));
  if (!args.salida) throw new Error('falta --salida DIR');
  const dominios = args.dominios ? args.dominios.split(',').map((d) => d.trim()).filter(Boolean) : DOMINIOS_DEFECTO;
  const limite = Number(args['timeout-ms'] ?? 45000);
  const navegador = await abrirNavegador(args.ejecutable, args.canal);
  try {
    const contexto = await navegador.newContext({ locale: 'es-MX', viewport: { width: 1366, height: 900 } });
    if (args.fixture) {
      const fixture = JSON.parse(await readFile(args.fixture, 'utf-8')) as Fixture;
      await instalarFixture(
        contexto,
        fixture,
        (args.base ?? 'https://sjf2.scjn.gob.mx').replace(/\/$/, ''),
        args['ruta-detalle'] ?? '/detalle/tesis/{registro}',
        args['ruta-api'] ?? '/services/sjftesismicroservice/api/public/tesis/{registro}',
      );
    }
    const resultado = args._tipo === 'url'
      ? await verificarUrl(args, contexto, dominios, limite)
      : await verificarTesis(args, contexto, dominios, limite);
    process.stdout.write(JSON.stringify(resultado, null, 2) + '\n');
  } finally {
    await navegador.close();
  }
}

principal().catch((error) => {
  process.stderr.write(`verificador_fuente: ${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(3);
});
