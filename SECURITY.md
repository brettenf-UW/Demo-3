# Security Configuration

## Setting Up Credentials for Public Repository

This project is configured to securely handle sensitive credentials so it can be safely shared as a public repository. Follow these steps to set up the necessary credentials:

### Initial Setup

1. Create the `.secrets` directory and place your credentials:

```bash
mkdir -p .secrets
```

2. Add your credentials to `.secrets/.env` file with the following format:

```
# Environment variables for the scheduler application
# NEVER commit this file to version control

# Anthropic API key for Claude
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Gurobi license credentials
GUROBI_WLSACCESSID=your_wls_access_id_here
GUROBI_WLSSECRET=your_wls_secret_here
GUROBI_LICENSEID=your_license_id_here
```

3. Generate your credentials by running:

```bash
./setup_credentials.sh
```

### Security Measures

- The `.secrets` directory and all credential files are excluded from git in `.gitignore`
- Sensitive keys are not hardcoded in the codebase
- Docker container gets credentials via environment variables
- The `gurobi.lic` file is generated from a template using environment variables

### For New Contributors

If you are a new contributor to this project:

1. Request the necessary credentials from the project administrator
2. Follow the setup instructions above
3. DO NOT commit any credential files or modify the `.gitignore` to include them
4. Always run `./setup_credentials.sh` before running the Docker container

### Credential Rotation

If you need to rotate credentials:

1. Update the `.secrets/.env` file with new values
2. Run `./setup_credentials.sh` to regenerate the credential files
3. Test the application to ensure everything works with the new credentials