# Solar Assistant SSH Authentication Information

## Default SSH Credentials
- **Username**: `solar-assistant`
- **Password**: `solar123`

## SSH Configuration Details (from image analysis)

### SSH Server Configuration (`/etc/ssh/sshd_config.d/10-security.conf`)
```
Port 22
AcceptEnv no
X11Forwarding no
PermitRootLogin no
PasswordAuthentication yes
PubkeyAuthentication yes
AllowUsers solar-assistant
```

### Key Points:
1. **Password authentication is enabled** - This explains why you're getting a publickey error. The system is configured to accept both password and public key authentication.
2. **Only the `solar-assistant` user can SSH** - The `AllowUsers` directive restricts SSH access to only this user.
3. **Root login is disabled** - You cannot SSH directly as root.
4. **Both password and public key authentication are enabled** - You can use either method.

## How to Connect via SSH

1. **Using password authentication**:
   ```bash
   ssh solar-assistant@<solar-assistant-ip>
   # When prompted, enter password: solar123
   ```

2. **To become root after login**:
   ```bash
   sudo su -
   ```

## Important Notes

- SSH is automatically disabled after the initial setup when you click "Accept and agree" in the web interface
- To re-enable SSH access:
  1. Navigate to the "Configuration" tab in the web interface
  2. Select "Configure local access"
  3. Select the SSH access option and save

## Password Hash Found in Image
The password hash for the solar-assistant user in `/etc/shadow`:
```
$y$j9T$lCmZ0wn/LxORwnbmF4Cvv1$A4xhU5sVHyGt7DDa5YI1.ZDVBQO.hD.wvngWkZ5zvEB
```
This is a yescrypt hash that corresponds to the password "solar123".

## Warning
SolarAssistant is designed to be configured via the web interface. Configuration via SSH or installation of additional applications can stop SolarAssistant from working correctly or cause unexpected errors.