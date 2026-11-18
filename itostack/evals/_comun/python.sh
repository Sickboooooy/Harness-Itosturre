# Selecciona un Python 3.10+ que funcione de verdad (se usa con `source`).
# En Windows, python3 suele ser el alias de la Microsoft Store: existe pero no ejecuta nada.
# Respeta PY o ITOSTACK_PYTHON si ya vienen definidos.
if [ -z "${PY:-}" ] && [ -n "${ITOSTACK_PYTHON:-}" ]; then
  PY="$ITOSTACK_PYTHON"
fi
if [ -z "${PY:-}" ]; then
  for candidato in python3 python "py -3"; do
    if $candidato -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1; then
      PY="$candidato"
      break
    fi
  done
fi
if [ -z "${PY:-}" ]; then
  echo "itostack: no se encontró Python 3.10+ (python3, python o py -3)" >&2
  exit 3
fi
export PY PYTHONUTF8=1 PYTHONIOENCODING=utf-8
