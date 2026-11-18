// Lanzador multiplataforma de los hooks de itostack (capa 1: falla cerrado por diseño).
// Uso en hooks.json:  node "${CLAUDE_PLUGIN_ROOT}/hooks/lanzar.mjs" <hook.py> <cerrado|abierto> <Evento>
//
// 1. Busca un Python que funcione de verdad: ITOSTACK_PYTHON (exclusivo si se define); si no,
//    py -3 → python → python3 en Windows, o python3 → python en Linux/macOS. Descarta el alias
//    de la Microsoft Store (sale con 9009 o 49 sin ejecutar nada).
// 2. Si el hook termina bien, reenvía su salida tal cual.
// 3. Si el hook truena, excede el tiempo o no hay intérprete:
//    - modo «cerrado» (guardias PreToolUse): DENIEGA la acción. Una guardia que no evalúa no autoriza.
//    - modo «abierto» (inicio, correcciones, cierre): deja pasar y avisa por stderr.
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, isAbsolute, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const [, , script = '', modo = 'cerrado', evento = 'PreToolUse'] = process.argv;
const dirHooks = dirname(fileURLToPath(import.meta.url));
const ruta = isAbsolute(script) ? script : join(dirHooks, script);
const LIMITE_MS = 15000;

let entrada = '';
try {
  entrada = readFileSync(0, 'utf-8');
} catch {
  entrada = '';
}

function candidatos() {
  const explicito = process.env.ITOSTACK_PYTHON;
  if (explicito) {
    if (existsSync(explicito)) return [[explicito, []]];
    const [comando, ...resto] = explicito.trim().split(/\s+/);
    return [[comando, resto]];
  }
  return process.platform === 'win32'
    ? [['py', ['-3']], ['python', []], ['python3', []]]
    : [['python3', []], ['python', []]];
}

function ultimaLinea(texto) {
  const lineas = (texto || '').trim().split(/\r?\n/).filter(Boolean);
  return (lineas[lineas.length - 1] || 'sin detalle').slice(0, 240);
}

function esAliasOAusente(resultado) {
  if (resultado.error && resultado.error.code === 'ENOENT') return true;
  if (resultado.status === 9009 || resultado.status === 49) return true;
  return /Python was not found|Microsoft Store|No installed Python|no se encontr[óo] Python/i.test(resultado.stderr || '');
}

function fallar(detalle) {
  if (modo === 'cerrado' && evento === 'PreToolUse') {
    process.stdout.write(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'deny',
        permissionDecisionReason:
          `itostack: la guardia ${script} no pudo evaluar (${detalle}). Falla cerrado: acción bloqueada. ` +
          'Verifica que exista Python 3.10+ (python3, python o py -3) o define ITOSTACK_PYTHON.',
      },
    }));
  } else {
    process.stderr.write(`itostack: hook ${script} omitido (${detalle})\n`);
  }
  process.exit(0);
}

if (!existsSync(ruta)) fallar(`no existe ${ruta}`);

let ultimoDetalle = 'no se encontró un intérprete de Python';
for (const [comando, argumentos] of candidatos()) {
  const resultado = spawnSync(comando, [...argumentos, ruta], {
    input: entrada,
    encoding: 'utf-8',
    timeout: LIMITE_MS,
    windowsHide: true,
    env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8', CLAUDE_PLUGIN_ROOT: process.env.CLAUDE_PLUGIN_ROOT || dirname(dirHooks) },
  });
  if (esAliasOAusente(resultado)) {
    ultimoDetalle = `intérprete «${[comando, ...argumentos].join(' ')}» no disponible`;
    continue;
  }
  if (resultado.error) fallar(`${resultado.error.code || resultado.error.message}`);
  if (resultado.status === 0) {
    if (resultado.stdout) process.stdout.write(resultado.stdout);
    if (resultado.stderr) process.stderr.write(resultado.stderr);
    process.exit(0);
  }
  fallar(`salió con código ${resultado.status}: ${ultimaLinea(resultado.stderr)}`);
}
fallar(ultimoDetalle);
