set -u
T=5961922b9a309055a75bc7302e5c852c5c51d59c
D="devpath-notification-svc devpath-ai-svc devpath-lcs-svc devpath-community-svc devpath-learning-svc devpath-sandbox-svc devpath-platform-svc devpath-gateway"
echo "### $(date -u +%T) node"; uptime
echo "### deployments"; sudo kubectl -n devpath get deploy $D -o custom-columns=NAME:.metadata.name,PAUSED:.spec.paused,REPLICAS:.spec.replicas,READY:.status.readyReplicas,UPDATED:.status.updatedReplicas,AVAILABLE:.status.availableReplicas,GEN:.metadata.generation,OBS:.status.observedGeneration,SP_PERIOD:.spec.template.spec.containers[0].startupProbe.periodSeconds
echo "### paused count: $(sudo kubectl -n devpath get deploy $D -o jsonpath='{range .items[*]}{.spec.paused}{"\n"}{end}' | grep -c true)"
echo "### active RS per deployment (expect 1 each)"; sudo kubectl -n devpath get rs -o custom-columns=OWNER:.metadata.ownerReferences[0].name,DESIRED:.spec.replicas | grep -E 'notification-svc|ai-svc|lcs-svc|community-svc|learning-svc|sandbox-svc|platform-svc|gateway' | awk '$2>0{c[$1]++} END{for(k in c) print k, c[k]}' | sort
echo "### pods (all)"; sudo kubectl -n devpath get pods -o custom-columns=NAME:.metadata.name,PHASE:.status.phase,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,STARTED:.status.startTime,SP:.spec.containers[0].startupProbe.periodSeconds
echo "### argo apps"; sudo kubectl -n argocd get applications -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status,REV:.status.sync.revision
echo "### apps at target: $(sudo kubectl -n argocd get applications -o jsonpath='{range .items[*]}{.status.sync.revision}{"\n"}{end}' | grep -c $T) / 16"
echo "### fence SA live + managers"; sudo kubectl -n devpath get sa devpath-migration-fence -o jsonpath='{.imagePullSecrets}'; echo; sudo kubectl -n devpath get sa devpath-migration-fence --show-managed-fields -o json | python3 -c "import json,sys; o=json.load(sys.stdin); print([(m['manager'], m['operation'], m.get('time')) for m in o['metadata'].get('managedFields',[]) if 'f:imagePullSecrets' in json.dumps(m.get('fieldsV1',{}))])"
echo "### recent warnings (30m)"; sudo kubectl -n devpath get events --field-selector type=Warning --sort-by=.lastTimestamp 2>/dev/null | tail -8
