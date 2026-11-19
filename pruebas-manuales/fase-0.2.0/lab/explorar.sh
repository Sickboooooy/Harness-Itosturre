#!/usr/bin/env bash
# Exploración de `claude plugin eval` en el laboratorio (como «lab», por stdin). Solo casos de desarrollo con datos
# sintéticos (fixtures FICT-*), nunca holdout; siempre --no-publish; sin credenciales (se espera una falla de
# infraestructura «sin sesión» y se observa cómo se reporta). Limpieza segura del temporal: se listan los enlaces, se
# borran los enlaces SIN seguirlos y luego el resto con --one-file-system; se verifica que los destinos sigan intactos.
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"
SALIDA=~/exploracion
rm -rf "$SALIDA" && mkdir -p "$SALIDA"
echo "== versión"; claude --version </dev/null
echo "== ayuda (opciones de privacidad y salida)"
claude plugin eval --help </dev/null 2>&1 | grep -E -- '--no-publish|--publish-report|--output-dir|--keep-temp|--json|--judge-model|--ablation' | sed 's/^/  /'

echo "== corrida sin credenciales (caso de desarrollo, datos sintéticos)"
antes=$(ls -d /tmp/claude-eval-* 2>/dev/null | sort)
claude plugin eval ~/itostack --case "verificar-cita.pass-exacto" --runs 1 --ablation none --scaffold --keep-temp \
  --no-publish --trust-plugin --allow-tools Bash Write Edit --model claude-haiku-5-5 --max-cost-usd 1 \
  --output-dir "$SALIDA" --json "$SALIDA/resultado.json" --report "$SALIDA/informe.html" </dev/null > "$SALIDA/salida.txt" 2>&1
codigo=$?
echo "  código de salida: $codigo"
sed 's/^/  | /' "$SALIDA/salida.txt" | head -20
python3 - "$SALIDA/resultado.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
corrida = d["cases"][0]["arms"]["with"][0]
print(f"  partial={d['partial']} partialReason={d.get('partialReason')!r} score={corrida['score']} turns={corrida['turns']} error={corrida['error'][:120]!r}")
print(f"  graders={[(g['name'], g['passed'], g['explanation'][:50]) for g in corrida['graders']]}")
print(f"  tracePath={corrida['tracePath']!r}")
PY

echo "== mensajes completos"
python3 - "$SALIDA/resultado.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
corrida = d["cases"][0]["arms"]["with"][0]
print("  error:", corrida["error"])
for g in corrida["graders"]:
    print(f"  grader {g['name']}: passed={g['passed']} scored={g['scored']} withOnly={g['withOnly']} · {g['explanation'][:160]}")
PY

echo "== temporal conservado (solo inspección; lo borra limpiar.sh)"
despues=$(ls -d /tmp/claude-eval-* 2>/dev/null | sort)
nuevo=$(comm -13 <(echo "$antes") <(echo "$despues") | head -1)
if [ -z "$nuevo" ]; then
  echo "  no quedó temporal"
else
  echo "  temporal: $nuevo · modos: $(stat -c '%A' "$nuevo") y sealed $(stat -c '%A' "$nuevo/sealed" 2>/dev/null)"
  find -P "$nuevo" -xdev -type d -exec chmod u+rwx {} + 2>/dev/null
  find -P "$nuevo" -xdev -type d -exec chmod u+rwx {} + 2>/dev/null
  find -P "$nuevo" -xdev -maxdepth 4 | sed "s|$nuevo|  .|" | head -60
  echo "  enlaces simbólicos (ruta -> destino):"
  find -P "$nuevo" -xdev -type l -printf '    %p -> %l\n' | sed "s|$nuevo|.|"
  echo "  montajes dentro del temporal:"
  grep " $nuevo" /proc/mounts | sed 's/^/    /' || echo "    ninguno"
  echo "  primeras líneas de out/trace.jsonl:"
  head -c 600 "$nuevo/out/trace.jsonl" 2>/dev/null | sed 's/^/    /'; echo
fi
