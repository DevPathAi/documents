set -u
A="$1"
echo "### $(date -u +%T) resume $A"
OLD_POD="$(sudo kubectl -n devpath get pods -l app=$A -o jsonpath='{.items[0].metadata.name}')"
sudo kubectl -n devpath rollout resume deployment/$A
sudo kubectl -n devpath rollout status deployment/$A --timeout=6m; RC=$?
echo "rollout rc=$RC at $(date -u +%T)"
echo "### pods"; sudo kubectl -n devpath get pods -l app=$A -o custom-columns=NAME:.metadata.name,PHASE:.status.phase,READY:.status.containerStatuses[0].ready,RESTARTS:.status.containerStatuses[0].restartCount,STARTED:.status.startTime,SP:.spec.containers[0].startupProbe.periodSeconds
NEW_POD="$(sudo kubectl -n devpath get pods -l app=$A --field-selector=status.phase=Running -o jsonpath='{.items[?(@.metadata.name!="'"$OLD_POD"'")].metadata.name}' | awk '{print $1}')"
echo "old=$OLD_POD new=$NEW_POD"
echo "### deploy"; sudo kubectl -n devpath get deploy $A -o custom-columns=NAME:.metadata.name,PAUSED:.spec.paused,READY:.status.readyReplicas,UPDATED:.status.updatedReplicas,AVAILABLE:.status.availableReplicas,GEN:.metadata.generation,OBS:.status.observedGeneration
echo "### argo"; printf 'sync=%s health=%s\n' "$(sudo kubectl -n argocd get application $A -o jsonpath='{.status.sync.status}')" "$(sudo kubectl -n argocd get application $A -o jsonpath='{.status.health.status}')"
echo "### node load"; uptime
if [ $RC -ne 0 ]; then echo "!!! ROLLOUT FAILED for $A - re-pausing and scaling the new RS to 0"; sudo kubectl -n devpath rollout pause deployment/$A; NEWRS="$(sudo kubectl -n devpath get rs -o custom-columns=NAME:.metadata.name,OWNER:.metadata.ownerReferences[0].name,CREATED:.metadata.creationTimestamp --sort-by=.metadata.creationTimestamp | awk -v o=$A '$2==o{n=$1} END{print n}')"; echo "newest RS=$NEWRS"; sudo kubectl -n devpath scale rs/$NEWRS --replicas=0; sudo kubectl -n devpath get pods -l app=$A -o wide; exit 1; fi
