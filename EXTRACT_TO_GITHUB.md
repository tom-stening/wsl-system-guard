# Extract To GitHub Repository

This directory is structured as a standalone project and can be published as its
own repository.

## 1. Create the new repository

Create an empty repository named `wsl-system-guard` under your GitHub account.

## 2. Copy project contents

From this OmniPrompt repository root:

```bash
mkdir -p /tmp/wsl-system-guard
rsync -a --delete wsl-system-guard/ /tmp/wsl-system-guard/
cd /tmp/wsl-system-guard
```

## 3. Initialize git and push

```bash
git init
git add .
git commit -m "Initial standalone WSL System Guard"
git branch -M main
git remote add origin git@github.com:tom-stening/wsl-system-guard.git
git push -u origin main
```

## 4. Consume from other repos

Install in any repo:

```bash
python3 -m pip install --user git+https://github.com/tom-stening/wsl-system-guard.git
```

Then run install script from the cloned source, or provide your own systemd
service that executes:

```bash
python3 -m wsl_system_guard.daemon --config ~/.config/wsl-system-guard/config.json
```
