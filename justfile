# Halo root justfile — deploy pipeline via Mutagen + Ryzen
# Mac is HQ. Ryzen is the worker. Mutagen keeps them in sync.

set dotenv-load := true

ryzen := "ryzen32"
remote_dir := "~/code/halo"
registry := "localhost:5000"
image := "halo:dev"
namespace := "halo-fleet"

# List available commands
default:
    @just --list

# ── Mutagen ────────────────────────────────────────────

# Show Mutagen sync status
sync-status:
    mutagen sync list

# Flush pending changes (block until Ryzen is up-to-date)
sync-flush:
    mutagen sync flush halo

# Pause sync
sync-pause:
    mutagen sync pause halo

# Resume sync
sync-resume:
    mutagen sync resume halo

# ── Track DB sync (rare — only when metrics change) ───

# Push track DBs to Ryzen (these are excluded from Mutagen)
sync-trackdbs:
    scp store/track_*.db {{ryzen}}:{{remote_dir}}/store/

# ── Build ──────────────────────────────────────────────

# Build the fleet image on the Ryzen (local disk, fast)
build:
    just sync-flush
    ssh {{ryzen}} "cd {{remote_dir}} && docker build -t {{registry}}/{{image}} ."

# Build and push to Ryzen's local registry
build-push:
    just build
    ssh {{ryzen}} "docker push {{registry}}/{{image}}"

# ── Deploy ─────────────────────────────────────────────

# Full deploy: sync → build → push → apply manifests → rollout restart
deploy:
    just build-push
    ssh {{ryzen}} "cd {{remote_dir}} && sudo kubectl apply -f infra/k8s/fleet/"
    ssh {{ryzen}} "sudo kubectl rollout restart deploy -n {{namespace}}"

# Rollout restart only (image already built)
restart:
    ssh {{ryzen}} "sudo kubectl rollout restart deploy -n {{namespace}}"

# Check fleet pod status
pods:
    ssh {{ryzen}} "sudo kubectl get pods -n {{namespace}} -o wide"

# Watch fleet pods (live)
watch:
    ssh {{ryzen}} "sudo kubectl get pods -n {{namespace}} -w"

# Fleet pod logs (pass advisor name, e.g. just logs musashi)
logs advisor:
    ssh {{ryzen}} "sudo kubectl logs -n {{namespace}} -l halo/advisor={{advisor}} --tail=50 -f"

# ── Halos overlay image ───────────────────────────────

# Build just the halos overlay image (fast iteration on Python code)
build-halos:
    just sync-flush
    ssh {{ryzen}} "cd {{remote_dir}} && docker build -f Dockerfile.halos -t {{registry}}/halo-halos:latest ."

# Build and push halos overlay
build-push-halos:
    just build-halos
    ssh {{ryzen}} "docker push {{registry}}/halo-halos:latest"

# ── Diagnostics ───────────────────────────────────────

# SSH into the Ryzen
ssh:
    ssh {{ryzen}}

# Run a remote command on the Ryzen
remote *cmd:
    ssh {{ryzen}} "{{cmd}}"

# Check what's on the Ryzen's local registry
registry-list:
    ssh {{ryzen}} "curl -s http://localhost:5000/v2/_catalog | python3 -m json.tool"
