// "Dar ojos al agente": recorre una ruta del mapa de funcionalidades sobre la app local en ejecución
// y devuelve lo observado con capturas. No decide el veredicto (lo hace verificar.py app).
//   node --experimental-strip-types evidencia_web.ts --base http://127.0.0.1:5000 --spec ruta.json --salida DIR
import { readFile } from 'node:fs/promises';
import { abrirNavegador, capturar, HOSTS_LOCALES, visitarConEvidencia, type ArchivoEvidencia } from './lib/navegador_forense.ts';

interface Paso {
  accion: 'ir' | 'clic' | 'llenar' | 'presionar' | 'esperar_texto' | 'esperar_selector' | 'captura';
  ruta?: string;
  selector?: string;
  valor?: string;
  texto?: string;
  tecla?: string;
  etiqueta?: string;
  timeout_ms?: number;
}

interface Spec {
  nombre: string;
  pasos: Paso[];
}

interface ResultadoPaso {
  indice: number;
  accion: string;
  selector?: string;
  ok: boolean;
  fallo: 'selector_ausente' | 'expectativa' | 'navegacion' | 'error' | null;
  detalle: string | null;
}

function leerArgumentos(argv: string[]): Record<string, string> {
  const resultado: Record<string, string> = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) {
      resultado[argv[i].slice(2)] = argv[i + 1] ?? '';
      i++;
    }
  }
  return resultado;
}

async function principal(): Promise<void> {
  const args = leerArgumentos(process.argv.slice(2));
  const base = (args.base ?? '').replace(/\/$/, '');
  const spec = JSON.parse(await readFile(args.spec, 'utf-8')) as Spec;
  const salida = args.salida;
  const limite = Number(args['timeout-ms'] ?? 10000);
  const host = (() => {
    try {
      return new URL(base).hostname;
    } catch {
      return '';
    }
  })();
  if (!HOSTS_LOCALES.includes(host)) throw new Error(`la verificación de app solo opera sobre localhost, no sobre «${base}»`);

  const navegador = await abrirNavegador(args.ejecutable, args.canal);
  const errores_consola: string[] = [];
  const errores_pagina: string[] = [];
  const solicitudes_fallidas: string[] = [];
  const pasos: ResultadoPaso[] = [];
  const archivos: ArchivoEvidencia[] = [];
  let app_alcanzable = false;
  try {
    const contexto = await navegador.newContext({ locale: 'es-MX', viewport: { width: 1280, height: 860 } });
    const pagina = await contexto.newPage();
    pagina.on('console', (mensaje) => {
      // El navegador pide /favicon.ico por su cuenta; su 404 no es un error de la app.
      if (mensaje.type() === 'error' && !mensaje.location().url.endsWith('/favicon.ico')) errores_consola.push(mensaje.text());
    });
    pagina.on('pageerror', (error) => errores_pagina.push(error.message));
    pagina.on('requestfailed', (solicitud) => solicitudes_fallidas.push(`${solicitud.method()} ${solicitud.url()}: ${solicitud.failure()?.errorText ?? ''}`));
    pagina.on('response', (respuesta) => {
      if (respuesta.status() >= 500) solicitudes_fallidas.push(`HTTP ${respuesta.status()} ${respuesta.url()}`);
    });

    try {
      await pagina.request.get(base + '/', { timeout: limite });
      app_alcanzable = true;
    } catch {
      app_alcanzable = false;
    }

    if (app_alcanzable) {
      for (const [posicion, paso] of spec.pasos.entries()) {
        const indice = posicion + 1;
        const espera = paso.timeout_ms ?? limite;
        const registro: ResultadoPaso = { indice, accion: paso.accion, selector: paso.selector, ok: true, fallo: null, detalle: null };
        try {
          if (paso.accion === 'ir') {
            const visita = await visitarConEvidencia(pagina, base + (paso.ruta ?? '/'), salida, `paso-${indice}-ir`, {
              dominios: HOSTS_LOCALES, timeoutMs: espera,
            });
            archivos.push(...visita.archivos);
            if (!visita.ok) Object.assign(registro, { ok: false, fallo: 'navegacion', detalle: visita.error ?? `HTTP ${visita.estado_http}` });
          } else if (paso.accion === 'clic' || paso.accion === 'llenar') {
            const objetivo = pagina.locator(paso.selector ?? '').first();
            const visible = await objetivo.waitFor({ state: 'visible', timeout: espera }).then(() => true, () => false);
            if (!visible) Object.assign(registro, { ok: false, fallo: 'selector_ausente', detalle: `no existe o no es visible: ${paso.selector}` });
            else if (paso.accion === 'clic') await objetivo.click();
            else await objetivo.fill(paso.valor ?? '');
          } else if (paso.accion === 'presionar') {
            await pagina.keyboard.press(paso.tecla ?? 'Enter');
          } else if (paso.accion === 'esperar_texto') {
            const aparecio = await pagina.getByText(paso.texto ?? '').first().waitFor({ state: 'visible', timeout: espera }).then(() => true, () => false);
            if (!aparecio) Object.assign(registro, { ok: false, fallo: 'expectativa', detalle: `no apareció el texto «${paso.texto}»` });
          } else if (paso.accion === 'esperar_selector') {
            const aparecio = await pagina.locator(paso.selector ?? '').first().waitFor({ state: 'visible', timeout: espera }).then(() => true, () => false);
            if (!aparecio) Object.assign(registro, { ok: false, fallo: 'expectativa', detalle: `no apareció el elemento ${paso.selector}` });
          } else if (paso.accion === 'captura') {
            const captura = await capturar(pagina, salida, paso.etiqueta ?? `paso-${indice}`);
            if (captura) archivos.push(captura);
          }
        } catch (error) {
          Object.assign(registro, { ok: false, fallo: 'error', detalle: error instanceof Error ? error.message.split('\n')[0] : String(error) });
        }
        pasos.push(registro);
        if (!registro.ok) {
          const captura = await capturar(pagina, salida, `fallo-paso-${indice}`);
          if (captura) archivos.push(captura);
          break;
        }
      }
      const final = await capturar(pagina, salida, 'final');
      if (final) archivos.push(final);
    }
  } finally {
    await navegador.close();
  }

  const resultado = {
    tipo: 'app',
    identificador: spec.nombre,
    modo_fuente: 'real',
    herramienta: 'itostack-evidencia-web/0.1.0',
    base,
    app_alcanzable,
    pasos,
    errores_consola,
    errores_pagina,
    solicitudes_fallidas,
    visitas: [{ etiqueta: spec.nombre, url: base, archivos }],
  };
  process.stdout.write(JSON.stringify(resultado, null, 2) + '\n');
}

principal().catch((error) => {
  process.stderr.write(`evidencia_web: ${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(3);
});
