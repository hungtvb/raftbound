#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '== glTF geometry, weights and color preservation =='
python3 assets/tests/validate_A06.py
python3 assets/tests/validate_A07.py
echo '== JS game and GPU-mock integration =='
(cd game && npm test)
echo '== Syntax =='
python3 -m py_compile assets/src/build_survivor_A07.py assets/src/build_skinned_survivor_A07.py assets/blender/finish_A07.py
node --check game/survival-rules.js
node --check game/game.js
node --check game/glb-loader.js
echo 'PASS: all AUTOMATED tests (NOT a browser or Blender render acceptance).'
