# Google Calendar OAuth Setup Guide

This guide explains how to fix the "Error 400: redirect_uri_mismatch" when connecting Google Calendar integration.

## The Problem

When connecting Google Calendar integration, you may see this error:

```
Error 400: redirect_uri_mismatch
You can't sign in to this app because it doesn't comply with Google's OAuth 2.0 policy.
Request details: redirect_uri=http://localhost:8090/admin/api/v1/oauth/callback/google_calendar
```

This happens when the redirect URI in your Google Cloud Console doesn't match the one ProtoBox is using.

## The Solution

You need to register the correct redirect URI in your Google Cloud Console.

### Step 1: Get Your Redirect URI

ProtoBox uses this redirect URI format:
```
{MCP_SERVER_URL}/admin/api/v1/integrations/oauth/callback/google_calendar
```

For local development, this is:
```
http://localhost:8090/admin/api/v1/integrations/oauth/callback/google_calendar
```

For production, this would be:
```
https://your-domain.com/admin/api/v1/integrations/oauth/callback/google_calendar
```

### Step 2: Configure Google Cloud Console

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Select your project** (or create one if you haven't already)
3. **Enable Google Calendar API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"
4. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Web application"
   - Give it a name (e.g., "ProtoBox MCP Server")
5. **Configure Authorized Redirect URIs**:
   - In the "Authorized redirect URIs" section, add:
     ```
     http://localhost:8090/admin/api/v1/integrations/oauth/callback/google_calendar
     ```
   - For production, also add your production domain:
     ```
     https://your-domain.com/admin/api/v1/integrations/oauth/callback/google_calendar
     ```
6. **Save the credentials**
7. **Copy the Client ID and Client Secret**

### Step 3: Configure ProtoBox Environment Variables

Add these environment variables to `.env`:

```bash
# Required for Google Calendar OAuth
GOOGLE_CLIENT_ID="your-client-id-from-step-2"
GOOGLE_CLIENT_SECRET="your-client-secret-from-step-2"

# Set your server URL (for production)
MCP_SERVER_URL="http://localhost:8090"  # For development
# MCP_SERVER_URL="https://your-domain.com"  # For production
```

### Step 4: Restart Your Backend

After updating the environment variables, restart your backend:

```bash
make stop
make backend
```

### Step 5: Test the Integration

1. Go to your ProtoBox frontend
2. Navigate to Integrations
3. Try connecting Google Calendar
4. The OAuth flow should now work correctly

## Common Issues

### Issue 1: Wrong Redirect URI

**Error**: `redirect_uri_mismatch`  
**Solution**: Ensure the redirect URI in Google Cloud Console exactly matches what ProtoBox is using.

### Issue 2: Missing Environment Variables

**Error**: OAuth2 credentials not configured  
**Solution**: Make sure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in `.env`.

### Issue 3: API Not Enabled

**Error**: Google Calendar API has not been used  
**Solution**: Enable the Google Calendar API in Google Cloud Console.

## Security Notes

1. **Never commit credentials to git**: Always use environment variables from `.env` or your secret manager
2. **Use HTTPS in production**: Only use `http://localhost` for local development
3. **Restrict your OAuth client**: In Google Cloud Console, you can restrict which domains can use your OAuth client
4. **Monitor usage**: Keep track of your API usage in Google Cloud Console

## Testing OAuth Flow

You can test the OAuth flow by:

1. **Check the authorization URL**: Visit the connect integration endpoint to get the OAuth URL
2. **Follow the flow**: Click through to Google, authorize the application
3. **Verify callback**: You should be redirected back to ProtoBox with a success message
4. **Check integration status**: The integration should show as "Connected"

## Environment-Specific Configuration

### Development (localhost:8090)
```
GOOGLE_CLIENT_ID="dev-client-id"
GOOGLE_CLIENT_SECRET="dev-client-secret"
MCP_SERVER_URL="http://localhost:8090"
```

Redirect URI: `http://localhost:8090/admin/api/v1/integrations/oauth/callback/google_calendar`

### Production 
```
GOOGLE_CLIENT_ID="prod-client-id"  
GOOGLE_CLIENT_SECRET="prod-client-secret"
MCP_SERVER_URL="https://your-domain.com"
```

Redirect URI: `https://your-domain.com/admin/api/v1/integrations/oauth/callback/google_calendar`

## Troubleshooting Commands

Check if Google Calendar integration is properly configured:
```bash
# Check if environment variables are set
grep GOOGLE .env

# Test the connect endpoint
make api ENDPOINT="/admin/api/v1/workspaces/{workspace_id}/integrations/google_calendar/connect" METHOD="POST"

# Check backend logs for OAuth errors
make blogs | grep -i oauth
```