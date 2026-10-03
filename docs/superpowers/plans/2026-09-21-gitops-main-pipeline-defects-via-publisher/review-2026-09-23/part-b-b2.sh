set -u
A=devpath-notification-svc
echo "### $(date -u +%T) pause $A"; sudo kubectl -n devpath rollout pause deployment/$A
echo "### $(date -u +%T) hard refresh"; sudo kubectl -n argocd annotate application $A argocd.argoproj.io/refresh=hard --overwrite
obs() { printf '%s paused=%s sync=%s health=%s reconciledAt=%s refreshAnno=%s pod=%s\n' "$(date -u +%T)" \
  "$(sudo kubectl -n devpath get deploy $A -o jsonpath='{.spec.paused}')" \
  "$(sudo kubectl -n argocd get application $A -o jsonpath='{.status.sync.status}')" \
  "$(sudo kubectl -n argocd get application $A -o jsonpath='{.status.health.status}')" \
  "$(sudo kubectl -n argocd get application $A -o jsonpath='{.status.reconciledAt}')" \
  "$(sudo kubectl -n argocd get application $A -o jsonpath='{.metadata.annotations.argocd\.argoproj\.io/refresh}')" \
  "$(sudo kubectl -n devpath get pods -l app=$A -o jsonpath='{range .items[*]}{.metadata.name}:{.status.containerStatuses[0].restartCount}{" "}{end}' 2>/dev/null)"; }
obs
for i in 1 2 3 4 5 6; do sleep 15; obs; done
echo "### final"; sudo kubectl -n devpath get deploy $A -o custom-columns=NAME:.metadata.name,PAUSED:.spec.paused,READY:.status.readyReplicas,GEN:.metadata.generation,OBS:.status.observedGeneration
sudo kubectl -n argocd get application $A -o jsonpath='{.status.operationState.phase} {.status.operationState.finishedAt}'; echo
