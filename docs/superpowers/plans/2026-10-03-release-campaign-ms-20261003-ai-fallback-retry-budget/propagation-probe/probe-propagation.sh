#!/usr/bin/env bash
# Cloudflare Pages 별칭 전파 시간 실측 — 같은 경로·다른 내용 파일이 배포 완료 뒤 언제 새 내용으로 바뀌는가.
# 운영(production 브랜치)은 건드리지 않는다. preview 브랜치 별칭에만 배포한다.
S="C:/Users/deepe/AppData/Local/Temp/claude/D--workspace-dpa/6bdcecb2-65fb-46e8-9905-61b454c3b121/scratchpad"
D="$S/probe-dist"; LOG="$S/probe-propagation.log"
BRANCH="probe-prop-1006"
URL="https://$BRANCH.devpath-home-page.pages.dev/.well-known/devpath-release/propagation-probe.json"
TRIALS="${1:-4}"; POLL_SECONDS="${2:-75}"

rm -rf "$D"; cp -r "$S/dist-master" "$D"
mkdir -p "$D/.well-known/devpath-release"
: > "$LOG"
for n in $(seq 1 "$TRIALS"); do
  printf '{"seq":%d}\n' "$n" > "$D/.well-known/devpath-release/propagation-probe.json"
  t0=$(date +%s%3N)
  npx --yes wrangler@4.146.0 pages deploy "$D" --project-name devpath-home-page --branch "$BRANCH" --commit-dirty=true > "$S/probe-deploy-$n.log" 2>&1
  rc=$?; t1=$(date +%s%3N)
  echo "# trial $n deploy rc=$rc took_ms=$((t1 - t0))" >> "$LOG"
  [ "$rc" -ne 0 ] && { tail -5 "$S/probe-deploy-$n.log" >> "$LOG"; break; }
  end=$((t1 + POLL_SECONDS * 1000))
  while [ "$(date +%s%3N)" -lt "$end" ]; do
    now=$(date +%s%3N)
    out=$(curl -4 -s -m 5 -D - -A "devpath-landing-canary/2" "$URL" | tr -d '\r')
    code=$(printf '%s\n' "$out" | head -1 | awk '{print $2}')
    ray=$(printf '%s\n' "$out" | grep -i '^cf-ray:' | awk '{print $2}')
    body=$(printf '%s\n' "$out" | tail -1 | cut -c1-40)
    echo "$n $((now - t1)) ${code:-ERR} ${ray:-none} $body" >> "$LOG"
    sleep 0.25
  done
done
echo "# done" >> "$LOG"
