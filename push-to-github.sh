#!/usr/bin/env bash
# Push this repo to github.com/polarpoint-io/tenable-mcp as a PUBLIC repo
# using your SSH keys.
#
# Requirements on your Mac:
#   - gh CLI (for creating the remote repo) - `brew install gh`
#   - gh is authenticated - run `gh auth status` to check, `gh auth login` if not
#   - Your SSH key is added to GitHub (https://github.com/settings/keys)
#
# Usage:
#   cd /path/to/pytenable-mcp
#   bash push-to-github.sh
#
# You can override the org / repo / branch via env vars:
#   GH_ORG=polarpoint-io GH_REPO=tenable-mcp BRANCH=main bash push-to-github.sh

set -euo pipefail

GH_ORG="${GH_ORG:-polarpoint-io}"
GH_REPO="${GH_REPO:-tenable-mcp}"
BRANCH="${BRANCH:-main}"
SSH_URL="git@github.com:${GH_ORG}/${GH_REPO}.git"

log() { printf '\033[1;34m[push]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[push] error:\033[0m %s\n' "$*" >&2; exit 1; }

# 0. Sanity: we're in a git repo with at least one commit on BRANCH
[ -d .git ] || die "Run this from the root of the pytenable-mcp repo."
git rev-parse --verify "${BRANCH}" >/dev/null 2>&1 \
  || die "Branch '${BRANCH}' does not exist locally."

# 1. SSH auth check
log "Checking SSH access to github.com..."
if ! ssh -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new git@github.com 2>&1 \
     | grep -qE "successfully authenticated|Hi .*!"; then
  die "SSH auth to github.com failed. Add your public key at https://github.com/settings/keys and retry."
fi
log "SSH auth OK."

# 2. gh availability + auth check (used to create the repo under the org)
if ! command -v gh >/dev/null 2>&1; then
  die "gh CLI not found. Install with 'brew install gh' or create the repo via the web UI and re-run with GH_SKIP_CREATE=1."
fi
if ! gh auth status >/dev/null 2>&1; then
  die "gh is not authenticated. Run 'gh auth login' and retry."
fi

# 3. Create the repo under the org (public) if it doesn't already exist
if gh repo view "${GH_ORG}/${GH_REPO}" >/dev/null 2>&1; then
  log "Repo ${GH_ORG}/${GH_REPO} already exists on GitHub - skipping creation."
else
  log "Creating public repo ${GH_ORG}/${GH_REPO}..."
  gh repo create "${GH_ORG}/${GH_REPO}" \
    --public \
    --description "MCP server exposing Tenable.io via pyTenable" \
    --disable-wiki
fi

# 4. Configure SSH remote 'origin' (replace if already set)
if git remote get-url origin >/dev/null 2>&1; then
  log "Setting existing 'origin' remote to ${SSH_URL}"
  git remote set-url origin "${SSH_URL}"
else
  log "Adding 'origin' remote -> ${SSH_URL}"
  git remote add origin "${SSH_URL}"
fi

# 5. Push
log "Pushing ${BRANCH} to origin..."
git push -u origin "${BRANCH}"

log "Done. View at https://github.com/${GH_ORG}/${GH_REPO}"
