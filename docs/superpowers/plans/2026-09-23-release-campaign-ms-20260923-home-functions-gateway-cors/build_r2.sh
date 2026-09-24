#!/usr/bin/env bash
# Build the ET13 web/admin evidence distributions locally at the rebuilt main SHA with the CI-pinned Flutter 3.44.1,
# exactly as .github/workflows/et13-evidence.yml does, so run_provenance_r2.py can bind them to the raw build marker.
# Usage: build_r2.sh <coords-r2.json>
set -euo pipefail
export MSYS_NO_PATHCONV=1 PYTHONUTF8=1
COORDS="$1"
SHA="$(py -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8'))['frontend_sha'])" "$COORDS")"
WT="$(py -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8'))['worktree'])" "$COORDS")"
FLUTTER_HOME="D:/workspace/dpa/.worktrees/_tools/flutter-3.44.1"
FLUTTER="$FLUTTER_HOME/bin/flutter.bat"   # absolute: Git Bash PATH lookup ignores the D:/ prefix and finds C:/tools/flutter (3.47.2)
REPO="D:/workspace/dpa/devpath-frontend"
test -n "$SHA" && test "$SHA" != "None"
git -C "$REPO" fetch -q origin main
test "$(git -C "$REPO" rev-parse origin/main)" = "$SHA"
if [ ! -d "$WT" ]; then git -C "$REPO" worktree add --detach "$WT" "$SHA"; fi
cd "$WT"
test "$(git rev-parse HEAD)" = "$SHA"
test -z "$(git status --porcelain=v1 --untracked-files=no)"
"$FLUTTER" --version --machine | grep -q '"frameworkVersion": "3.44.1"'
"$FLUTTER" --version --machine | grep -q '"frameworkRevision": "924134a44c189315be2148659913dda1671cbe99"'
"$FLUTTER" --version --machine | grep -q '"dartSdkVersion": "3.12.1"'
"$FLUTTER" pub get --enforce-lockfile
rm -rf build/et13/build
for app in web admin; do
  ( cd "apps/$app" && "$FLUTTER" build web --release --no-pub --no-web-resources-cdn --no-tree-shake-icons \
      --target lib/et13_evidence_main.dart --dart-define=ET13_SOURCE_SHA="$SHA" --output "$WT/build/et13/build/$app" )
  sha256sum "build/et13/build/$app/main.dart.js"
done
echo "expected (raw marker):"
py -c "import json,sys;c=json.load(open(sys.argv[1],encoding='utf-8'));r=c.get('raw_review',{});print(r.get('web_main_dart_js_sha256'),'web');print(r.get('admin_main_dart_js_sha256'),'admin')" "$COORDS"
