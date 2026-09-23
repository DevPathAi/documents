set -u
D="devpath-notification-svc devpath-ai-svc devpath-lcs-svc devpath-community-svc devpath-learning-svc devpath-sandbox-svc devpath-platform-svc devpath-gateway"
echo "### node"; uptime; nproc; date -u
echo "### deployments"; sudo kubectl -n devpath get deploy $D -o custom-columns=NAME:.metadata.name,PAUSED:.spec.paused,REPLICAS:.spec.replicas,READY:.status.readyReplicas,UPDATED:.status.updatedReplicas,GEN:.metadata.generation,OBS:.status.observedGeneration,STARTUPPROBE:.spec.template.spec.containers[0].startupProbe.periodSeconds
echo "### replicasets (owned by the 8)"; sudo kubectl -n devpath get rs -o custom-columns=NAME:.metadata.name,OWNER:.metadata.ownerReferences[0].name,DESIRED:.spec.replicas,READY:.status.readyReplicas | grep -E 'notification-svc|ai-svc|lcs-svc|community-svc|learning-svc|sandbox-svc|platform-svc|gateway'
echo "### pods"; sudo kubectl -n devpath get pods -o custom-columns=NAME:.metadata.name,PHASE:.status.phase,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,STARTED:.status.startTime
echo "### argo applications"; sudo kubectl -n argocd get applications -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status,REV:.status.sync.revision,AUTO:.spec.syncPolicy.automated
echo "### applicationset ignoreApplicationDifferences"; sudo kubectl -n argocd get applicationset devpath-services -o jsonpath='{.spec.ignoreApplicationDifferences}'; echo
echo "### argocd-cm timeout.reconciliation"; sudo kubectl -n argocd get cm argocd-cm -o jsonpath='{.data.timeout\.reconciliation}'; echo "(empty = default 180s)"
echo "### fence SA imagePullSecrets"; sudo kubectl -n devpath get sa devpath-migration-fence -o jsonpath='{.imagePullSecrets}'; echo
echo "### notification app syncPolicy"; sudo kubectl -n argocd get application devpath-notification-svc -o jsonpath='{.spec.syncPolicy}'; echo
