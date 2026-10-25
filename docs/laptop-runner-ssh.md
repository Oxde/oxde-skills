# Laptop runner: SSH access for Claude

The second laptop runs Hermes and the cron jobs. Claude works from Mark's main Mac on the same
Wi-Fi. This gives Claude a shell on the laptop so jobs can be registered and watched instead of
debugged blind. Git stays the source of truth; the laptop pulls.

## One-time setup (Mark, on the laptop)

1. Turn on Remote Login: System Settings → General → Sharing → Remote Login → on.
   Restrict to the user that runs Hermes.
2. Find the hostname: `scutil --get LocalHostName` (for example `marks-air`). The address is
   then `marks-air.local`.

## One-time setup (Mark, on the main Mac)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/laptop-runner -C "claude-laptop-runner" -N ""
```

```bash
ssh-copy-id -i ~/.ssh/laptop-runner.pub <user>@<hostname>.local
```

Add to `~/.ssh/config`:

```
Host laptop
  HostName <hostname>.local
  User <user>
  IdentityFile ~/.ssh/laptop-runner
  IdentitiesOnly yes
```

Check: `ssh laptop 'hermes --version && ls ~/.hermes'`.

## What Claude does over SSH

- `git -C ~/oxde-skills pull` to bring the branch over.
- `hermes cron list`, `hermes cron add ...`, `hermes cron run <id>` to register and test jobs.
- Read logs and `feedctl stats`.
- Never: edit `~/.hermes` secrets, change Hermes auth, or run anything that publishes.

## Why not Tailscale or a public port

Same Wi-Fi and `.local` names are enough. If the laptop moves networks later, Tailscale is the
next step; nothing in this guide changes except `HostName`.
