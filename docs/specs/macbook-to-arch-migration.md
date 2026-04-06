# MacBook M5 to Arch Linux Migration Plan

Source: m5air (macOS, 100.116.37.95)
Target: carbonx1 (Arch Linux, 100.78.19.23)
Transport: Tailscale (rsync over SSH)

Decision pending. This plan exists so the move can happen in under
an hour if you decide to return the MacBook.

**Migration script:** `scripts/migrate.py` — Python, dry-run by default, full
manifest logging to `~/.migration/`. Replaces the bash snippets below (kept
for reference).

```bash
python scripts/migrate.py                     # dry-run: see what would happen
python scripts/migrate.py --execute           # live transfer
python scripts/migrate.py --execute --resume  # resume after failure
python scripts/migrate.py --verify            # post-transfer checksums
```

## Inventory

### Must migrate (source of truth)

| What                   | Size   | Location               | Git? |
|------------------------|--------|------------------------|------|
| halo                   | 906 MB | ~/code/halo            | yes  |
| thepit                 | 3.7 GB | ~/code/thepit          | yes  |
| dotfiles               | 368 KB | ~/code/dotfiles        | yes  |
| maclaw                 | 341 MB | ~/code/maclaw          | yes  |
| jobsworth              | 177 MB | ~/code/jobsworth       | yes  |
| hermes state           | 1.1 GB | ~/.hermes              | yes  |
| SSH keys               | 24 KB  | ~/.ssh                 | no   |
| himalaya config        | 4 KB   | ~/.config/himalaya     | no   |
| Claude Code config     | ~50 KB | ~/.claude              | no   |
| git global config      | ~2 KB  | ~/.gitconfig           | no   |
| GPG keys               | varies | ~/.gnupg               | no   |
| obsidian vault         | 52 KB  | ~/Documents/vault      | no   |
| cookies.txt (watchctl) | ~10 KB | ~/code/halo/cookies.txt| no   |

### Should migrate (useful but recoverable)

| What                   | Size   | Git? | Notes                   |
|------------------------|--------|------|-------------------------|
| sortie-pi              | 261 MB | yes  | push to remote first    |
| pidgeon + swarm        | 110 MB | yes  | push to remote first    |
| codecrafters           | 7 MB   | no   | fresh start is fine     |
| other git repos        | ~200MB | yes  | push all, clone on Arch |

### Also migrate (strip artefacts first)

| What                   | Raw    | Stripped | Notes                   |
|------------------------|--------|----------|-------------------------|
| dormant/               | 4.9 GB | ~1-2 GB  | strip node_modules/.venv|
| recent/                | 4.9 GB | ~1-2 GB  | strip node_modules/.venv|

### Skip (recoverable)

| What                   | Size   | Why skip                    |
|------------------------|--------|-----------------------------|
| chrome-debug-profile   | 2.0 GB | rebuild from login          |
| hermes-agent venv      | 750 MB | reinstall on target         |
| hermes checkpoints     | 214 MB | session cache, regenerates  |
| node_modules anywhere  | varies | npm install                 |
| .venv anywhere         | varies | uv sync                     |
| __pycache__ anywhere   | varies | regenerates                 |

### Option B: SSD dump

If bandwidth is a concern, skip rsync entirely:
```bash
# Plug in SSD, mount at /Volumes/MIGRATE
DEST=/Volumes/MIGRATE/m5air-backup

rsync -avz --progress \
    --exclude=node_modules --exclude=.venv --exclude=__pycache__ \
    --exclude=.next --exclude=.turbo --exclude=target \
    --exclude=chrome-debug-profile \
    ~/code/ $DEST/code/

rsync -avz --progress \
    --exclude=hermes-agent/venv --exclude=checkpoints \
    --exclude=browser_screenshots --exclude=sandboxes \
    ~/.hermes/ $DEST/hermes/

rsync -avz ~/.ssh ~/.config/himalaya ~/Documents/vault $DEST/config/
```
Then plug SSD into the x1 and rsync locally. Faster, no bandwidth dependency.

## Pre-flight (run on macOS before transfer)

```bash
# 1. Push all git repos to remotes
cd ~/code && for d in */; do
    if [ -d "$d/.git" ]; then
        echo "=== $d ==="
        cd "$d"
        git push --all origin 2>&1 | tail -1
        cd ..
    fi
done

# 2. Push hermes state
cd ~/.hermes && git add -A && git commit -m "pre-migration snapshot" && git push

# 3. Verify SSH keys are backed up
tar czf /tmp/ssh-backup.tar.gz ~/.ssh

# 4. Export brew list for reference
brew list --formula > /tmp/brew-formulas.txt
brew list --cask > /tmp/brew-casks.txt

# 5. List uv-installed tools
uv tool list > /tmp/uv-tools.txt
```

## Migration Script

```bash
#!/bin/bash
# Run from macOS. Requires tailscale SSH access to carbonx1.
set -euo pipefail

TARGET="carbonx1"  # tailscale hostname
REMOTE_USER="mrkai"
REMOTE_HOME="/home/$REMOTE_USER"

RSYNC_OPTS="-avz --progress --exclude=node_modules --exclude=.venv --exclude=__pycache__ --exclude=.next --exclude=.turbo --exclude=target"

echo "=== SSH keys and config ==="
rsync $RSYNC_OPTS ~/.ssh/ $TARGET:$REMOTE_HOME/.ssh/
rsync $RSYNC_OPTS ~/.config/himalaya/ $TARGET:$REMOTE_HOME/.config/himalaya/

echo "=== Core repos ==="
for repo in halo thepit dotfiles maclaw jobsworth; do
    echo "--- $repo ---"
    rsync $RSYNC_OPTS ~/code/$repo/ $TARGET:$REMOTE_HOME/code/$repo/
done

echo "=== Secondary repos ==="
for repo in sortie-pi pidgeon pidgeon-swarm coldcase darkfactorio leash nine-bells noopit runnerboy superpowers; do
    echo "--- $repo ---"
    rsync $RSYNC_OPTS ~/code/$repo/ $TARGET:$REMOTE_HOME/code/$repo/
done

echo "=== Hermes state (excluding venv and checkpoints) ==="
rsync $RSYNC_OPTS \
    --exclude=hermes-agent/venv \
    --exclude=checkpoints \
    --exclude=browser_screenshots \
    --exclude=sandboxes \
    ~/.hermes/ $TARGET:$REMOTE_HOME/.hermes/

echo "=== Obsidian vault ==="
rsync $RSYNC_OPTS ~/Documents/vault/ $TARGET:$REMOTE_HOME/Documents/vault/

echo "=== Reference files ==="
scp /tmp/brew-formulas.txt $TARGET:$REMOTE_HOME/
scp /tmp/uv-tools.txt $TARGET:$REMOTE_HOME/

echo "=== Done. Total transferred. ==="
```

## Post-flight (run on Arch)

```bash
# 1. Install system deps (pacman equivalents of brew)
sudo pacman -S --needed \
    python python-pip uv \
    nodejs npm \
    git gh \
    docker docker-compose \
    bat eza fzf ripgrep \
    openssh gnupg \
    aerc himalaya \
    base-devel

# 1b. AUR packages (requires yay or paru)
yay -S --needed \
    google-chrome-stable \
    claude-code

# 2. Install hermes agent
cd ~/.hermes/hermes-agent
python -m venv venv
source venv/bin/activate
pip install -e .

# 3. Set up all Python repos
for repo in halo thepit maclaw jobsworth; do
    cd ~/code/$repo && uv sync && cd ~
done

# 3b. Reinstall uv tools from reference list
cat ~/.migration/references/uv-tools.txt | awk '{print $1}' | xargs -I{} uv tool install {}

# 4. Verify hermes
hermes --version

# 5. Set up hermes gateway (systemd instead of launchctl)
cat > ~/.config/systemd/user/hermes-gateway.service << 'EOF'
[Unit]
Description=Hermes Telegram Gateway
After=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/.hermes/hermes-agent
ExecStart=%h/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main gateway run --replace
Restart=on-failure
RestartSec=10
EnvironmentFile=%h/.hermes/.env

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable hermes-gateway
systemctl --user start hermes-gateway

# 6. Verify tailscale
tailscale status

# 7. Fix SSH permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_*
chmod 644 ~/.ssh/*.pub

# 8. Test git access
gh auth status
git clone --dry-run git@github.com:rickhallett/halo.git /dev/null 2>&1 || echo "fix SSH keys"

# 9. Verify halo tools
cd ~/code/halo && uv run memctl stats
cd ~/code/halo && uv run trackctl domains
cd ~/code/halo && uv run nightctl graph
```

## macOS-to-Arch differences

| macOS                   | Arch equivalent             | Notes                    |
|-------------------------|-----------------------------|--------------------------|
| launchctl               | systemd --user              | gateway service above    |
| osascript/JXA           | N/A                         | no Apple Notes on Linux  |
| Apple Notes             | Obsidian or flat files      | switch note target       |
| Keychain                | gnome-keyring or pass       | for OAuth tokens         |
| brew                    | pacman + yay (AUR)          | most packages available  |
| /Applications/Chrome    | google-chrome-stable (AUR)  | CDP works identically    |
| ~/Library/Caches        | ~/.cache                    | XDG paths                |
| pbcopy/pbpaste          | xclip or wl-copy            | clipboard                |
| open                    | xdg-open                    | open files/URLs          |

## Things that won't work on Arch

- Apple Notes JXA (gainz-note.py). Replace with Obsidian notes
  or plain markdown rendered to terminal.
- iMessage (imsg CLI). Not available on Linux.
- FindMy. Use web interface or phone.
- Spotlight/mdfind. Use ripgrep.
- macOS Keychain for OAuth. Use gnome-keyring, pass, or env vars.

## Estimated transfer time

Core repos + hermes (rsync, ~6 GB excluding skipped):
- Over Tailscale (WireGuard): 10-20 min depending on bandwidth
- Post-flight setup: 20-30 min

Total: under an hour if nothing goes wrong.

## Confidence check

Before wiping macOS, verify on Arch:
1. `hermes` responds in terminal
2. Telegram gateway sends and receives
3. `uv run memctl stats` returns a non-zero note count
4. `git push` works from halo
5. `trackctl streak movement` shows your streak
6. Chrome CDP works on port 9222
