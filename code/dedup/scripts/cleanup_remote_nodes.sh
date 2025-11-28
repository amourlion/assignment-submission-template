#!/bin/bash

# Cleanup script for remote Hadoop nodes (hadoop002, hadoop003 by default)
# Removes experiment artifacts and monitoring data to free space in user scope.
# Usage: ./cleanup_remote_nodes.sh [--deep] [node1 node2 ...]
#   --deep : also clear ~/.m2/repository on remote nodes (can be large)

set -euo pipefail

DEFAULT_NODES=("hadoop002" "hadoop003")
DEEP=0
NODES=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --deep)
            DEEP=1
            shift
            ;;
        *)
            NODES+=("$1")
            shift
            ;;
    esac
done

if [[ ${#NODES[@]} -eq 0 ]]; then
    NODES=("${DEFAULT_NODES[@]}")
fi

TARGETS=(
    "~/monitoring"
    "~/MRApplication/reduce-startup/metrics"
    "~/MRApplication/reduce-startup/system_metrics"
    "~/MRApplication/reduce-startup/other_node_monitoring"
    "~/MRApplication/reduce-startup/input-*"
    "~/MRApplication/reduce-startup/target"
    "/tmp/hadoop-*"
)

echo "=== Remote cleanup starting ==="
echo "Nodes: ${NODES[*]}"
echo "Deep cleanup (remove ~/.m2/repository): $([[ $DEEP -eq 1 ]] && echo YES || echo NO)"
echo

for node in "${NODES[@]}"; do
    echo "---- ${node} ----"
    ssh "$node" bash -lc "set -e; echo 'Before:'; df -h /; echo;"
    
    ssh "$node" bash -lc "
        set -e
        cleaned=0
        for path in ${TARGETS[*]}; do
            if ls \$path >/dev/null 2>&1; then
                rm -rf \$path
                echo \"Removed \$path\"
                cleaned=1
            else
                echo \"Skip (not found): \$path\"
            fi
        done
        if [[ $DEEP -eq 1 ]]; then
            if [ -d ~/.m2/repository ]; then
                rm -rf ~/.m2/repository
                echo 'Removed ~/.m2/repository'
                cleaned=1
            else
                echo 'Skip (not found): ~/.m2/repository'
            fi
        fi
        if [[ \$cleaned -eq 0 ]]; then
            echo 'No targets removed on this node.'
        fi
    "
    
    ssh "$node" bash -lc "echo; echo 'After:'; df -h /; echo"
done

echo "=== Remote cleanup completed ==="
