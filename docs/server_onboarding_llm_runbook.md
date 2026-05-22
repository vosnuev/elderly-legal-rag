# LLM Runbook: Tailscale + SSH + VS Code Remote SSH + Codex

이 문서는 LLM이 팀원 PC에서 서버 개발 환경 접속을 안내하거나 점검할 때 사용하는 실행용 절차서다. 목적은 각 팀원이 Tailscale VPN으로 `owenfed` 서버에 접근하고, SSH 공개키 인증을 설정한 뒤, VS Code Remote SSH에서 서버 프로젝트를 열어 Codex IDE extension을 사용할 수 있게 하는 것이다.

## Fixed Inputs

- Server target: `owenfed`
- Connection path: user PC -> Tailscale VPN -> OpenSSH on `owenfed`
- Tailscale sharing method: owner sent Tailscale machine/share invite by email
- Server account initial password: owner-provided temporary password
- Required first-login action: change the initial password immediately
- Required after server login: run `gh auth login`
- Codex reference: OpenAI Codex IDE extension works in VS Code-compatible editors and can be installed from the Visual Studio Code Marketplace.

## User Accounts

| Name | Email | Server username |
|---|---|---|
| 김지효 | jjeoe_0317@gmail.com | `jjeoe_0317` |
| 송윤경 | na2ppn26450@gmail.com | `alice123` |
| 전하영 | vosnuevo@gmail.com | `vosnuevo` |
| 양도영 | dyking99@naver.com | `dyking99` |

## LLM Operating Rules

- First identify the user's client OS: Windows, macOS, or Linux.
- Never ask the user to paste a private key. Only the `.pub` public key may be shown or copied.
- Treat the owner-provided temporary password as a bootstrap credential. Instruct the user to change it with `passwd` after the first successful SSH login.
- Prefer key-based SSH after the initial password login.
- If `owenfed` does not resolve, ask the server owner for the Tailscale IPv4 address and use it as `HostName`.
- If a command fails, collect the exact error text, current OS, username, and whether Tailscale shows `owenfed` online before proceeding.

## High-Level Flow

1. Confirm the team member accepted the Tailscale invite sent to their email.
2. Install and sign in to Tailscale on the team member's PC.
3. Confirm the server is reachable through Tailscale.
4. SSH into `owenfed` once using the temporary password.
5. Change the server password.
6. Generate an SSH key on the user's PC if one does not already exist.
7. Add the public key to `~/.ssh/authorized_keys` on the server.
8. Verify passwordless SSH.
9. Add a VS Code SSH host entry.
10. Connect with VS Code Remote SSH.
11. Install or enable Codex IDE extension in VS Code and sign in.
12. Run `gh auth login` on the server.

## Automation Feasibility

The setup can be partially automated, but not fully automated end-to-end without unsafe password handling or user-account authorization bypasses.

### Safe to automate

- Detect whether the user is on Windows PowerShell, Windows CMD, macOS Terminal, or Linux Terminal.
- Check whether `tailscale`, `ssh`, `scp`, and `ssh-keygen` are available.
- Run `tailscale status` and `tailscale ping owenfed`.
- Create the local `.ssh` directory.
- Generate an SSH key if `id_ed25519.pub` does not already exist.
- Upload the public key to the server and append it to `~/.ssh/authorized_keys`.
- Create or append a VS Code Remote SSH host entry.
- Verify key-based SSH with `ssh -o PreferredAuthentications=publickey`.

### Requires user interaction

- Accepting the Tailscale invite from email.
- Installing Tailscale if it is not already installed.
- Signing in to Tailscale.
- Accepting the first SSH host fingerprint prompt.
- Entering the initial server password.
- Running `passwd` and choosing a new server password.
- Choosing an SSH key passphrase, if the user wants one.
- Signing in to the Codex IDE extension.
- Running `gh auth login`, because it requires browser or device-code authorization.
- Logging in to Linear MCP or other MCP tools that require OAuth.

### Do not automate

- Do not store the initial password value in a script.
- Do not use `sshpass` or similar tools for this onboarding flow.
- Do not copy, print, upload, or request the private key file `id_ed25519`.
- Do not disable host key checking globally.
- Do not make forwarded ports public unless the owner explicitly asks for it.

### Recommended automation boundary

Use a helper script only after the user has:

1. Accepted the Tailscale share invite.
2. Installed and signed in to Tailscale.
3. Confirmed `tailscale ping owenfed` works, or received the Tailscale IP from the owner.
4. Completed the first SSH login and changed the initial password with `passwd`.

After that point, key generation, public-key registration, SSH config creation, and verification can be automated safely.

## Automation Templates

Use these templates only after replacing placeholders. If `owenfed` does not resolve, pass the Tailscale IP as the host name.

### Windows PowerShell helper

Save as `setup-owenfed-ssh.ps1` or paste into PowerShell after editing the values at the top.

```powershell
$ServerUser = "<username>"
$UserEmail = "<user-email>"
$ServerHost = "owenfed" # or the Tailscale IP
$HostAlias = "owenfed-$ServerUser"

$ErrorActionPreference = "Stop"
$SshDir = Join-Path $env:USERPROFILE ".ssh"
$KeyPath = Join-Path $SshDir "id_ed25519"
$PubPath = "$KeyPath.pub"
$ConfigPath = Join-Path $SshDir "config"

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
  throw "ssh is not available. Install Windows OpenSSH Client or VS Code with Remote SSH prerequisites."
}
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
  throw "scp is not available. Install Windows OpenSSH Client."
}
if (-not (Get-Command ssh-keygen -ErrorAction SilentlyContinue)) {
  throw "ssh-keygen is not available. Install Windows OpenSSH Client."
}

if (Get-Command tailscale -ErrorAction SilentlyContinue) {
  tailscale status
  tailscale ping $ServerHost
} else {
  Write-Warning "tailscale command was not found. Confirm Tailscale is installed and signed in through the GUI."
}

New-Item -ItemType Directory -Force -Path $SshDir | Out-Null

if (-not (Test-Path $PubPath)) {
  ssh-keygen -t ed25519 -C $UserEmail -f $KeyPath
}

Write-Host "This step may ask for the server password once or twice. Use the password you set after the first login."
scp $PubPath "${ServerUser}@${ServerHost}:/tmp/${ServerUser}.pub"
$RemoteCmd = "mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && (grep -qxF -f /tmp/${ServerUser}.pub ~/.ssh/authorized_keys || cat /tmp/${ServerUser}.pub >> ~/.ssh/authorized_keys) && rm /tmp/${ServerUser}.pub && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
ssh "${ServerUser}@${ServerHost}" $RemoteCmd

if (-not (Test-Path $ConfigPath)) {
  New-Item -ItemType File -Force -Path $ConfigPath | Out-Null
}

if (-not (Select-String -Path $ConfigPath -Pattern "^Host\s+$HostAlias$" -Quiet)) {
  Add-Content -Path $ConfigPath -Value @"

Host $HostAlias
  HostName $ServerHost
  User $ServerUser
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
"@
}

ssh -o PreferredAuthentications=publickey "${ServerUser}@${ServerHost}" "echo ssh-publickey-ok"
Write-Host "Done. In VS Code, connect to Remote-SSH host: $HostAlias"
```

### Windows CMD helper

CMD automation is more fragile than PowerShell. Prefer PowerShell if possible. Use this only when the user specifically needs Command Prompt.

```bat
@echo off
set SERVER_USER=<username>
set USER_EMAIL=<user-email>
set SERVER_HOST=owenfed
set HOST_ALIAS=owenfed-%SERVER_USER%
set SSH_DIR=%USERPROFILE%\.ssh
set KEY_PATH=%SSH_DIR%\id_ed25519
set CONFIG_PATH=%SSH_DIR%\config

where ssh >nul 2>nul || (echo ssh is not available & exit /b 1)
where scp >nul 2>nul || (echo scp is not available & exit /b 1)
where ssh-keygen >nul 2>nul || (echo ssh-keygen is not available & exit /b 1)

if not exist "%SSH_DIR%" mkdir "%SSH_DIR%"

where tailscale >nul 2>nul
if %ERRORLEVEL%==0 (
  tailscale status
  tailscale ping %SERVER_HOST%
) else (
  echo tailscale command was not found. Confirm Tailscale is installed and signed in through the GUI.
)

if not exist "%KEY_PATH%.pub" (
  ssh-keygen -t ed25519 -C "%USER_EMAIL%" -f "%KEY_PATH%"
)

echo This step may ask for the server password once or twice. Use the password you set after the first login.
scp "%KEY_PATH%.pub" %SERVER_USER%@%SERVER_HOST%:/tmp/%SERVER_USER%.pub
ssh %SERVER_USER%@%SERVER_HOST% "mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && (grep -qxF -f /tmp/%SERVER_USER%.pub ~/.ssh/authorized_keys || cat /tmp/%SERVER_USER%.pub >> ~/.ssh/authorized_keys) && rm /tmp/%SERVER_USER%.pub && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"

findstr /R /C:"^Host %HOST_ALIAS%$" "%CONFIG_PATH%" >nul 2>nul
if errorlevel 1 (
  >> "%CONFIG_PATH%" echo.
  >> "%CONFIG_PATH%" echo Host %HOST_ALIAS%
  >> "%CONFIG_PATH%" echo   HostName %SERVER_HOST%
  >> "%CONFIG_PATH%" echo   User %SERVER_USER%
  >> "%CONFIG_PATH%" echo   IdentityFile C:\Users\%USERNAME%\.ssh\id_ed25519
  >> "%CONFIG_PATH%" echo   IdentitiesOnly yes
)

ssh -o PreferredAuthentications=publickey %SERVER_USER%@%SERVER_HOST% "echo ssh-publickey-ok"
echo Done. In VS Code, connect to Remote-SSH host: %HOST_ALIAS%
```

### macOS/Linux Bash helper

Save as `setup-owenfed-ssh.sh`, then run `chmod +x setup-owenfed-ssh.sh`.

```bash
#!/usr/bin/env bash
set -euo pipefail

SERVER_USER="${1:?Usage: ./setup-owenfed-ssh.sh <username> <email> [host]}"
USER_EMAIL="${2:?Usage: ./setup-owenfed-ssh.sh <username> <email> [host]}"
SERVER_HOST="${3:-owenfed}"
HOST_ALIAS="owenfed-${SERVER_USER}"
SSH_DIR="${HOME}/.ssh"
KEY_PATH="${SSH_DIR}/id_ed25519"
CONFIG_PATH="${SSH_DIR}/config"

command -v ssh >/dev/null || { echo "ssh is not available"; exit 1; }
command -v scp >/dev/null || { echo "scp is not available"; exit 1; }
command -v ssh-keygen >/dev/null || { echo "ssh-keygen is not available"; exit 1; }

if command -v tailscale >/dev/null; then
  tailscale status
  tailscale ping "${SERVER_HOST}"
else
  echo "tailscale command was not found. Confirm Tailscale is installed and signed in."
fi

mkdir -p "${SSH_DIR}"
chmod 700 "${SSH_DIR}"

if [ ! -f "${KEY_PATH}.pub" ]; then
  ssh-keygen -t ed25519 -C "${USER_EMAIL}" -f "${KEY_PATH}"
fi

echo "This step may ask for the server password once or twice. Use the password you set after the first login."
scp "${KEY_PATH}.pub" "${SERVER_USER}@${SERVER_HOST}:/tmp/${SERVER_USER}.pub"
ssh "${SERVER_USER}@${SERVER_HOST}" "mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && (grep -qxF -f /tmp/${SERVER_USER}.pub ~/.ssh/authorized_keys || cat /tmp/${SERVER_USER}.pub >> ~/.ssh/authorized_keys) && rm /tmp/${SERVER_USER}.pub && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"

touch "${CONFIG_PATH}"
chmod 600 "${CONFIG_PATH}"

if ! grep -qE "^Host[[:space:]]+${HOST_ALIAS}$" "${CONFIG_PATH}"; then
  cat >> "${CONFIG_PATH}" <<EOF

Host ${HOST_ALIAS}
  HostName ${SERVER_HOST}
  User ${SERVER_USER}
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
EOF
fi

ssh -o PreferredAuthentications=publickey "${SERVER_USER}@${SERVER_HOST}" "echo ssh-publickey-ok"
echo "Done. In VS Code, connect to Remote-SSH host: ${HOST_ALIAS}"
```

Example:

```bash
./setup-owenfed-ssh.sh jjeoe_0317 jjeoe_0317@gmail.com
./setup-owenfed-ssh.sh alice123 na2ppn26450@gmail.com 100.x.y.z
```

## Step 1: Determine Client OS

Ask the user:

```text
현재 PC가 Windows인가요, macOS인가요, Linux인가요?
```

Then follow the matching section below.

## Step 2: Tailscale Setup

### Windows

1. Install Tailscale for Windows.
2. Sign in with the email that received the share invite.
3. Open PowerShell and verify:

```powershell
tailscale status
tailscale ping owenfed
```

If `tailscale` is not recognized, use the Tailscale GUI first or reopen PowerShell after installation.

### macOS

1. Install Tailscale for macOS.
2. Sign in with the email that received the share invite.
3. Open Terminal and verify:

```bash
tailscale status
tailscale ping owenfed
```

### Linux

1. Install Tailscale using the distribution package instructions.
2. Sign in with the email that received the share invite.
3. Verify:

```bash
tailscale status
tailscale ping owenfed
```

## Step 3: First SSH Login

Replace `<username>` with the user's server username.

```bash
ssh <username>@owenfed
```

Expected first password:

```text
Use the owner-provided temporary password.
```

Immediately change the password:

```bash
passwd
```

If `ssh <username>@owenfed` fails because the name does not resolve, ask the owner for the Tailscale IP of `owenfed`, then use:

```bash
ssh <username>@<tailscale-ip>
```

## Step 4: Generate SSH Key on User PC

### Windows PowerShell

Use PowerShell when possible. It handles `$env:USERPROFILE` cleanly and is the recommended Windows path in this runbook.

Check whether a key already exists:

```powershell
Test-Path "$env:USERPROFILE\.ssh\id_ed25519.pub"
```

If it returns `False`, create one:

```powershell
ssh-keygen -t ed25519 -C "<user-email>"
```

Accept the default path. A passphrase is recommended, but optional for a bootcamp/shared lab environment if the user understands the tradeoff.

Show the public key only if needed:

```powershell
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub"
```

### Windows CMD

Use CMD only when the user specifically opens Command Prompt instead of PowerShell.

Check whether a key already exists:

```bat
if exist "%USERPROFILE%\.ssh\id_ed25519.pub" (echo key exists) else (echo no key)
```

If there is no key:

```bat
ssh-keygen -t ed25519 -C "<user-email>"
```

Show the public key only if needed:

```bat
type "%USERPROFILE%\.ssh\id_ed25519.pub"
```

### macOS/Linux Terminal

Check whether a key already exists:

```bash
test -f ~/.ssh/id_ed25519.pub && echo "key exists" || echo "no key"
```

If there is no key:

```bash
ssh-keygen -t ed25519 -C "<user-email>"
```

Accept the default path. A passphrase is recommended, but optional for a bootcamp/shared lab environment if the user understands the tradeoff.

Show the public key only if needed:

```bash
cat ~/.ssh/id_ed25519.pub
```

## Step 5: Install Public Key on Server

### Windows PowerShell

Use password authentication one last time:

```powershell
scp "$env:USERPROFILE\.ssh\id_ed25519.pub" <username>@owenfed:/tmp/<username>.pub
ssh <username>@owenfed "mkdir -p ~/.ssh && cat /tmp/<username>.pub >> ~/.ssh/authorized_keys && rm /tmp/<username>.pub && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
```

### Windows CMD

Use password authentication one last time:

```bat
scp "%USERPROFILE%\.ssh\id_ed25519.pub" <username>@owenfed:/tmp/<username>.pub
ssh <username>@owenfed "mkdir -p ~/.ssh && cat /tmp/<username>.pub >> ~/.ssh/authorized_keys && rm /tmp/<username>.pub && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
```

### macOS/Linux Terminal

Preferred:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub <username>@owenfed
```

Fallback if `ssh-copy-id` is unavailable:

```bash
cat ~/.ssh/id_ed25519.pub | ssh <username>@owenfed 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys'
```

## Step 6: Verify Passwordless SSH

### Windows PowerShell

```powershell
ssh -o PreferredAuthentications=publickey <username>@owenfed
```

### Windows CMD

```bat
ssh -o PreferredAuthentications=publickey <username>@owenfed
```

### macOS/Linux Terminal

```bash
ssh -o PreferredAuthentications=publickey <username>@owenfed
```

Success means the user reaches the server shell without entering the server password. A local key passphrase prompt is acceptable if the user set one.

## Step 7: VS Code Remote SSH

Install VS Code and the Microsoft Remote - SSH extension.

Create or edit the SSH config file:

- Windows PowerShell: `$env:USERPROFILE\.ssh\config`
- Windows CMD: `%USERPROFILE%\.ssh\config`
- macOS/Linux: `~/.ssh/config`

Add:

```sshconfig
Host owenfed-<username>
  HostName owenfed
  User <username>
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
```

For Windows, `IdentityFile ~/.ssh/id_ed25519` usually works in OpenSSH config. If VS Code fails to find the key, use the absolute path:

```sshconfig
IdentityFile C:\Users\<windows-user>\.ssh\id_ed25519
```

If `owenfed` does not resolve through MagicDNS, replace `HostName owenfed` with the Tailscale IP.

In VS Code:

1. Open Command Palette.
2. Run `Remote-SSH: Connect to Host...`.
3. Select `owenfed-<username>`.
4. Open the project directory on the server.

## Step 8: Codex IDE Extension

OpenAI's current docs state that Codex can be used through an IDE extension in VS Code-compatible editors. Install the Codex IDE extension from the Visual Studio Code Marketplace, then sign in with the user's ChatGPT account or API key when prompted.

In a Remote SSH window:

1. Confirm the Codex icon appears in the VS Code sidebar.
2. If VS Code asks whether to install the extension locally or on SSH target, choose the option that makes the Codex panel available while the remote workspace is open.
3. If the extension does not appear after installation, restart VS Code and reconnect to `owenfed-<username>`.

## Step 9: GitHub CLI Authentication on Server

Run this inside the SSH session or VS Code remote terminal:

```bash
gh auth status
gh auth login
```

Recommended choices unless the project requires otherwise:

- GitHub.com
- HTTPS for Git operations if users are new to SSH Git auth
- Browser/device-code login when running inside SSH

After login:

```bash
gh auth status
git config --global user.name "<github-name-or-real-name>"
git config --global user.email "<user-email>"
```

## Troubleshooting

### Tailscale cannot see `owenfed`

Check:

```bash
tailscale status
tailscale ping owenfed
```

Likely causes:

- User did not accept the invite.
- User signed in with a different email.
- Server owner shared the wrong machine or revoked sharing.
- MagicDNS is unavailable; use the Tailscale IP instead.

### SSH asks for password after key setup

Check local key path:

```bash
ssh -v <username>@owenfed
```

On the server:

```bash
ls -ld ~/.ssh
ls -l ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

### VS Code Remote SSH fails

Check terminal SSH first:

```bash
ssh <username>@owenfed
```

If terminal SSH works but VS Code fails, re-check the VS Code SSH config path and `IdentityFile` path.

### Codex extension does not work in remote window

Check:

- The user is signed in to Codex with a supported ChatGPT account or API key.
- The extension is enabled in the active VS Code window.
- The remote workspace is trusted.
- VS Code has been restarted after extension installation.

## Completion Criteria

The setup is complete only when all checks pass:

- `tailscale ping owenfed` succeeds, or SSH succeeds using the Tailscale IP.
- `ssh -o PreferredAuthentications=publickey <username>@owenfed` works.
- VS Code opens a Remote SSH window connected to `owenfed-<username>`.
- A server project folder opens in VS Code.
- Codex IDE extension is visible and signed in.
- `gh auth status` succeeds on the server.
