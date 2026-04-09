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
- 2026-04-07 (PROJECT RIPPERDOC): Hightower's domain is now PRIMARY. Kai has declared DevOps/infra/SRE as his identity and career axis. CKA certification via Udemy bootcamp, 30 min/day. K8s clusters "like Factorio" — systems thinking, resource optimisation, debugging under pressure. The halosphere moves to local linux box — real infrastructure, not cloud abstractions. This is Hightower's moment: every CKA drill, every kubectl invocation, every etcd backup/restore, every NetworkPolicy written by hand builds the muscle memory that survives interview scrutiny. No copilot. No agents. Hands on keys. nvim as the universal interface. The 6-month window is enough for CKA + AWS SA if the daily practice holds. Hightower is no longer in discovery phase — he is in active coaching.
