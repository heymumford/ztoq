# API Tokens Configuration Guide

This document explains how to configure and use API tokens for connecting to Zephyr Scale and qTest.

## Overview

ZTOQ requires authentication with both Zephyr Scale and qTest APIs. For security and ease of use, the tool uses environment variables to store API tokens:

- `zephyr_access_token`: For Zephyr Scale API authentication
- `qtest_bearer_token`: For qTest API authentication

These tokens are used to authenticate API requests to each respective platform.

## Obtaining API Tokens

### Zephyr Scale API Token

1. Log in to your Zephyr Scale account
2. Navigate to your user profile settings
3. Select "API Keys" or "Access Tokens"
4. Create a new API token with appropriate permissions
   - Requires read access for migration
   - Name it something descriptive like "ZTOQ Migration Tool"
5. Copy the token value (note: you may only see it once)

### qTest Bearer Token

1. Log in to your qTest instance
2. Navigate to your user profile settings
3. Select "API & SDK" or similar section
4. Generate a new bearer token
   - Ensure it has appropriate permissions for your project
5. Copy the token value

Alternatively, you can use the `qtest_get_token.py` script to obtain a token:

```bash
python examples/qtest_get_token.py --base-url "https://company.qtestnet.com" --username "your_username" --output env
```

This will prompt for your password and output environment variables you can set for later use.

## Setting Up Environment Variables

### Linux/macOS

Add the tokens to your shell profile file (`.bashrc`, `.zshrc`, etc.):

```bash
# Zephyr and qTest API tokens
export zephyr_access_token="your_zephyr_token_here"
export qtest_bearer_token="your_qtest_token_here"
```

Then reload your profile:

```bash
source ~/.bashrc  # or ~/.zshrc
```

### Windows

Using PowerShell:

```powershell
# Set for current session
$env:zephyr_access_token = "your_zephyr_token_here"
$env:qtest_bearer_token = "your_qtest_token_here"

# To set permanently (system-wide)
[Environment]::SetEnvironmentVariable("zephyr_access_token", "your_zephyr_token_here", "User")
[Environment]::SetEnvironmentVariable("qtest_bearer_token", "your_qtest_token_here", "User")
```

### Using .env Files

For development or local use, you can create a `.env` file based on the provided `.env.example`:

1. Copy the example file: `cp .env.example .env`
2. Edit the `.env` file and add your tokens
3. Make sure the `.env` file is loaded by your environment or script

Note: **Never commit `.env` files containing real tokens to version control.**

## Understanding OAuth Bearer Token Format

qTest uses OAuth 2.0 Bearer token authentication, which follows this format:

```
Authorization: Bearer <token>
```

Important notes:
- The word "Bearer" must be capitalized properly according to the OAuth 2.0 specification
- There must be a space between "Bearer" and the token value
- When setting the `qtest_bearer_token` environment variable, use ONLY the token value itself, not the "Bearer" prefix

The ZTOQ library automatically adds the "Bearer" prefix with proper capitalization when making API requests.

## Verifying Your Tokens

You can verify that your tokens are correctly set up and working by using the provided verification scripts:

```bash
# Basic verification
python examples/verify_api_tokens.py

# Comprehensive qTest token check with domain format testing
python examples/qtest_check_connection.py

# Direct API check for qTest
python examples/qtest_direct_api_check.py
```

These scripts will:
1. Check if the environment variables are set
2. Attempt to connect to both APIs
3. Report if the tokens are valid and working correctly
4. Help you troubleshoot domain format issues

## Security Best Practices

1. **Never share your API tokens** - they provide direct access to your projects
2. **Don't hardcode tokens in source code**
3. Set appropriate expiration dates on tokens when available
4. Use tokens with the minimum necessary permissions
5. Rotate tokens periodically for improved security
6. For production deployments, use proper secrets management solutions

## Troubleshooting

If you encounter issues with your API tokens:

1. Ensure the token is correctly copied without extra spaces
2. Verify the token hasn't expired
3. Check that you have the necessary permissions in each system
4. Try regenerating a new token if needed
5. Check if there are any IP restrictions on your tokens

### Domain Format Issues

qTest instances can have different domain formats. Common domain formats include:

- `https://company.qtestnet.com` (most common)
- `https://company.qtest.com`
- `https://company.qtest.net`

If you're unsure about the correct domain, you can:

1. Run the connection checker script:
   ```bash
   python examples/qtest_check_connection.py --url "company" --token "your_token" --no-verify-ssl
   ```
   This will try multiple domain formats and report which ones work.

2. Look at the URL in your browser when logged into qTest and use that domain format.

3. Contact your qTest administrator for the correct API endpoint URL.

### SSL Certificate Issues

If you're encountering SSL certificate validation issues, you can use:

```bash
python examples/qtest_direct_api_check.py --url "company.qtestnet.com" --token "your_token" --no-verify-ssl
```

The `--no-verify-ssl` option disables SSL certificate verification, which can be useful in development environments or when working with self-signed certificates.

---

*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../LICENSE)*
