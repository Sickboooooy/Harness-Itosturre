// Única puerta de salida hacia portales oficiales: cada visita deja captura, HTML, texto y SHA-256.
// La regla IT001 del lint prohíbe page.goto() hacia dominios oficiales fuera de este módulo.
import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { chromium, type Browser, type Page } from 'playwright';

export interface ArchivoEvidencia {
  tipo: 'captura' | 'html' | 'texto' | 'json';
  ruta: string;
  sha256: string;
  bytes: number;
}

export interface Visita {
  etiqueta: string;
  url: string;
  url_final: string | null;
  estado_http: number | null;
  marca_tiempo: string;
  ok: boolean;
  error: string | null;
  archivos: ArchivoEvidencia[];
  texto: string;
  cuerpo: string | null;
}

export interface OpcionesVisita {
  dominios: string[];
  timeoutMs?: number;
  esperarTexto?: string;
  guardarCuerpo?: boolean;
}

export const HOSTS_LOCALES = ['127.0.0.1', 'localhost', '::1', '[::1]'];

export async function abrirNavegador(ejecutable?: string | null, canal?: string | null): Promise<Browser> {
  const opciones: { headless: boolean; executablePath?: string; channel?: string } = { headless: true };
  if (ejecutable) opciones.executablePath = ejecutable;
  else if (canal) opciones.channel = canal;
  return chromium.launch(opciones);
}

export function hostPermitido(url: string, dominios: string[]): boolean {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return dominios.some((dominio) => host === dominio.toLowerCase());
  } catch {
    return false;
  }
}

export async function guardar(
  dir: string,
  nombre: string,
  contenido: Buffer | string,
  tipo: ArchivoEvidencia['tipo'],
): Promise<ArchivoEvidencia> {
  await mkdir(dir, { recursive: true });
  const ruta = resolve(join(dir, nombre));
  const datos = typeof contenido === 'string' ? Buffer.from(contenido, 'utf-8') : contenido;
  await writeFile(ruta, datos);
  return { tipo, ruta, sha256: createHash('sha256').update(datos).digest('hex'), bytes: datos.length };
}

export async function capturar(page: Page, dir: string, etiqueta: string): Promise<ArchivoEvidencia | null> {
  try {
    return await guardar(dir, `${etiqueta}.png`, await page.screenshot({ fullPage: true }), 'captura');
  } catch {
    return null;
  }
}

function mensajeDe(error: unknown): string {
  return error instanceof Error ? error.message.split('\n')[0] : String(error);
}

export async function visitarConEvidencia(
  page: Page,
  url: string,
  dir: string,
  etiqueta: string,
  opciones: OpcionesVisita,
): Promise<Visita> {
  if (!hostPermitido(url, opciones.dominios)) {
    throw new Error(`Dominio no permitido para visita forense: ${url}`);
  }
  const limite = opciones.timeoutMs ?? 45000;
  const marca_tiempo = new Date().toISOString();
  let estado_http: number | null = null;
  let error: string | null = null;
  let cuerpo: string | null = null;
  const archivos: ArchivoEvidencia[] = [];

  try {
    const respuesta = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: limite });
    estado_http = respuesta ? respuesta.status() : null;
    await page.waitForLoadState('networkidle', { timeout: Math.min(limite, 15000) }).catch(() => undefined);
    if (opciones.esperarTexto) {
      await page.getByText(opciones.esperarTexto).first().waitFor({ timeout: Math.min(limite, 15000) }).catch(() => undefined);
    }
    if (respuesta && opciones.guardarCuerpo) {
      cuerpo = (await respuesta.body()).toString('utf-8');
      archivos.push(await guardar(dir, `${etiqueta}.respuesta.txt`, cuerpo, 'json'));
    }
  } catch (falla) {
    error = mensajeDe(falla);
  }

  const captura = await capturar(page, dir, etiqueta);
  if (captura) archivos.push(captura);
  else error = error ?? 'no se pudo tomar la captura de pantalla';

  let texto = '';
  try {
    archivos.push(await guardar(dir, `${etiqueta}.html`, await page.content(), 'html'));
    texto = await page.evaluate(() => (document.body ? document.body.innerText : ''));
    archivos.push(await guardar(dir, `${etiqueta}.txt`, texto, 'texto'));
  } catch {
    // La captura ya documenta lo que se vio; sin HTML no se inventa nada.
  }

  const ok = error === null && estado_http !== null && estado_http < 400 && captura !== null;
  return { etiqueta, url, url_final: page.url() || null, estado_http, marca_tiempo, ok, error, archivos, texto, cuerpo };
}
