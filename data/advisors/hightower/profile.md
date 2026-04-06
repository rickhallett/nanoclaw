# Hightower -- Kai Profile
Status: DISCOVERY PHASE

## K8s Operational Experience (as of 2026-04-06)
- Built halo-fleet cluster from scratch on VKE (Vultr)
- Single node: vc2-2c-4gb, 2 CPU, 4GB RAM
- Running: 7 advisor pods, memctl-authority, NATS JetStream, NFS server, Argo CD
- Survived: NFS mount failures, PodSecurity rejections, Argo drift, NATS consumer orphans
- Wrote and passed 66 fleet integration tests including chaos engineering (pod murder, concurrent stress)
- Lessons documented: docs/d2/k8s-fleet-lessons-learned.md (16 items)

## Known Strengths
- Can build and deploy from YAML (proven by the fleet)
- Understands event sourcing / CQRS pattern (NATS → projection.db)
- NFS single-writer architecture (solved the distributed memory problem)
- Argo CD GitOps workflow (selfHeal, prune, sync)

## Known Gaps
- Diagnostic speed under pressure (untested)
- CKA exam domains (formal coverage unknown)
- Network policies (not yet deployed)
- Ingress / TLS (not yet configured — using port-forward)
- Helm (used for monitoring values but not core fleet)
- etcd operations (managed by VKE, never touched directly)
- Multi-node scheduling, affinity, taints/tolerations (single node)

## CKA Readiness
(to be assessed during discovery)

## Session log
