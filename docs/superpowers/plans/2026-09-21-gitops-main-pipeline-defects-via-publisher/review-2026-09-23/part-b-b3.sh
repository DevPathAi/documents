set -u
D="devpath-notification-svc devpath-ai-svc devpath-lcs-svc devpath-community-svc devpath-learning-svc devpath-sandbox-svc devpath-platform-svc devpath-gateway"
for a in devpath-ai-svc devpath-lcs-svc devpath-community-svc devpath-learning-svc devpath-sandbox-svc devpath-platform-svc devpath-gateway; do
  sudo kubectl -n devpath rollout pause deployment/$a
  sudo kubectl -n argocd annotate application $a argocd.argoproj.io/refresh=hard --overwrite >/dev/null
done
sleep 20
echo "### $(date -u +%T) deployments"; sudo kubectl -n devpath get deploy $D -o custom-columns=NAME:.metadata.name,PAUSED:.spec.paused,READY:.status.readyReplicas,UPDATED:.status.updatedReplicas,GEN:.metadata.generation,OBS:.status.observedGeneration
echo "### argo apps (8)"; for a in $D; do printf '%-26s sync=%s health=%s reconciledAt=%s\n' "$a" "$(sudo kubectl -n argocd get application $a -o jsonpath='{.status.sync.status}')" "$(sudo kubectl -n argocd get application $a -o jsonpath='{.status.health.status}')" "$(sudo kubectl -n argocd get application $a -o jsonpath='{.status.reconciledAt}')"; done
echo "### pods restarts"; sudo kubectl -n devpath get pods -o custom-columns=NAME:.metadata.name,PHASE:.status.phase,RESTARTS:.status.containerStatuses[*].restartCount | grep -E 'notification-svc|ai-svc|lcs-svc|community-svc|learning-svc|sandbox-svc|platform-svc|gateway'
echo "### paused count: $(sudo kubectl -n devpath get deploy $D -o jsonpath='{range .items[*]}{.spec.paused}{"\n"}{end}' | grep -c true)"
