---
name: eliza-fleet/deployment
description: SSH enablement and deployment workflows for multi-machine Eliza setup
version: 1.0.0
---

# Multi-Machine Eliza SSH Deployment

## Step 1: Install SSH Server (Run as Administrator)

```powershell
# Install OpenSSH Server
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# Start SSH service
Start-Service sshd

# Set to auto-start on boot
Set-Service -Name sshd -StartupType Automatic

# Open firewall port 22
New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server' -Enabled True `
  -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22

# Verify it's running
Get-Service sshd
```

## Step 2: Configure Key Authentication

### On Primary PC (your ThinkPad):
```powershell
# Get your public key
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub"
```

Copy the output (this is your public key).

### On Target PC (run as Administrator):
```powershell
# Create .ssh directory
New-Item -ItemType Directory -Path "$env:USERPROFILE\.ssh" -Force

# Paste your public key (replace with actual key)
$pubkey = "YOUR_PUBLIC_KEY_HERE"
Set-Content -Path "$env:USERPROFILE\.ssh\authorized_keys" -Value $pubkey

# Set proper permissions (correct syntax)
icacls "$env:USERPROFILE\.ssh" /inheritance:r
icacls "$env:USERPROFILE\.ssh" /grant "$env:USERNAME:(OI)(CI)F"
icacls "$env:USERPROFILE\.ssh\authorized_keys" /inheritance:r
icacls "$env:USERPROFILE\.ssh\authorized_keys" /grant "$env:USERNAME:(OI)(CI)F"

# Restart SSH service to load new keys
Restart-Service sshd
```

## Step 3: Test Connection

From your primary PC:
```bash
ssh -o StrictHostKeyChecking=no -o BatchMode=yes user@target-ip hostname
```

Where:
- `user` = your Windows username (typically `pc` or `moadeeb`)
- `target-ip` = the Tailscale IP (100.90.0.100 for Lenovo, etc.)