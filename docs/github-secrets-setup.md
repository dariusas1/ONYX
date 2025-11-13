# GitHub Secrets Configuration for ONYX CI/CD

This document lists all required GitHub secrets for the ONYX CI/CD pipeline to function properly.

## Required Secrets

### Deployment Secrets

| Secret Name | Description | Example |
|-------------|-------------|----------|
| `VPS_HOST_STAGING` | Hostname or IP address for staging VPS | `staging.example.com` or `192.168.1.100` |
| `VPS_HOST_PRODUCTION` | Hostname or IP address for production VPS | `example.com` or `192.168.1.200` |
| `VPS_USER` | SSH username for VPS access | `deploy` or `ubuntu` |
| `SSH_PRIVATE_KEY` | Private SSH key for VPS access | `-----BEGIN OPENSSH PRIVATE KEY-----...` |

### Optional Secrets

| Secret Name | Description | Example |
|-------------|-------------|----------|
| `SLACK_WEBHOOK_URL` | Slack webhook for deployment notifications | `https://hooks.slack.com/services/...` |

## Setup Instructions

### 1. Generate SSH Key Pair

```bash
# Generate new SSH key pair
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/onyx_deploy

# This creates:
# - Private key: ~/.ssh/onyx_deploy (add to SSH_PRIVATE_KEY secret)
# - Public key: ~/.ssh/onyx_deploy.pub (add to VPS authorized_keys)
```

### 2. Configure VPS Access

```bash
# On each VPS (staging and production), add the public key:
mkdir -p ~/.ssh
echo "PUBLIC_KEY_CONTENT" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh

# Ensure the user can run Docker commands:
sudo usermod -aG docker $VPS_USER
```

### 3. Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret from the table above

### 4. Configure Environment Protection

For production deployments, GitHub environments are used with manual approval:

1. Go to Settings → Environments
2. Create environment named "production"
3. Configure protection rules:
   - Require reviewers
   - Add team members who can approve deployments
   - Set timeout (optional)

## Security Notes

- Use a dedicated deploy user with minimal permissions
- Restrict SSH key usage to specific IP addresses if possible
- Rotate SSH keys regularly
- Use GitHub's environment protection rules for production
- Never commit secrets to the repository

## Testing the Configuration

After setting up secrets, test the deployment by:

1. Push to `dev` branch → Should auto-deploy to staging
2. Create PR to `main` → Should build and test but not deploy
3. Merge to `main` → Should require manual approval, then deploy to production

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   - Verify VPS_HOST is correct
   - Check SSH private key format
   - Ensure public key is in authorized_keys on VPS

2. **Docker Permission Denied**
   - Add deploy user to docker group on VPS
   - Restart SSH session after group change

3. **Health Check Failed**
   - Verify nginx is running on VPS
   - Check firewall settings
   - Ensure SSL certificates are valid (for HTTPS)

### Debug Mode

To debug deployment issues, you can temporarily add debug steps to the workflow:

```yaml
- name: Debug deployment
  run: |
    echo "VPS_HOST: $VPS_HOST"
    echo "VPS_USER: $VPS_USER"
    ssh -o StrictHostKeyChecking=no -i $HOME/.ssh/deploy_key $VPS_USER@$VPS_HOST "docker ps"
```