#!/bin/sh
set -eu

CONTAINER_NAME="${SYSML_KERNEL_CONTAINER:-sysml-kernel-container}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
HELPER_SCRIPT="${SYSML_HELPER_SCRIPT:-${SCRIPT_DIR}/../apiserver/process_sysml.py}"

if [ "$#" -eq 0 ]; then
  echo "No SysML input files were provided." >&2
  exit 2
fi

if [ ! -f "$HELPER_SCRIPT" ]; then
  echo "SysML helper script not found: $HELPER_SCRIPT" >&2
  exit 2
fi

SYSML_CONTENT=$(cat -- "$@")

docker cp "$HELPER_SCRIPT" "$CONTAINER_NAME:/tmp/process_sysml.py"
printf '%s\n' "$SYSML_CONTENT" | docker exec -i \
  "$CONTAINER_NAME" \
  conda run --no-capture-output -n sysml python /tmp/process_sysml.py
