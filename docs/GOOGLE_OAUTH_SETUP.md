# Google OAuth Setup Guide

## Quick Setup (5 minutes)

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable Google Calendar API:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Calendar API"
   - Click and Enable it

4. Create OAuth 2.0 Credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Web application"
   - Name: "ProtoBox Development"
   - Add Authorized redirect URIs:
     ```
     http://localhost:8090/admin/api/v1/oauth/callback/google_calendar
     http://localhost:3000/api/oauth/callback/google_calendar
     ```
   - Click "Create"
   - Copy the Client ID and Client Secret

### 2. Set credentials in `.env`

Run the setup script:
```bash
./scripts/setup-google-oauth.sh
```

Or manually set them:
```bash
# Set for dev_test environment
echo GOOGLE_CLIENT_ID="your-client-id" >> .env
echo GOOGLE_CLIENT_SECRET="your-client-secret" >> .env

# Also set for dev environment
echo GOOGLE_CLIENT_ID="your-client-id" >> .env
echo GOOGLE_CLIENT_SECRET="your-client-secret" >> .env
```

### 3. Restart the Server

```bash
make restart
```

### 4. Test the Integration

1. Go to http://localhost:3000
2. Navigate to Integrations
3. Click "Connect" on Google Calendar
4. You should now see the real Google OAuth consent screen
5. Authorize the app
6. The integration should connect successfully

## Troubleshooting

### Still seeing demo OAuth?
- Check credentials are set: `grep GOOGLE .env`
- Ensure server was restarted after setting credentials
- Clear browser cache/cookies

### OAuth Error "redirect_uri_mismatch"?
- Double-check the redirect URIs in Google Console match exactly
- No trailing slashes
- Include both localhost:8090 and localhost:3000 versions

### 400 Bad Request?
- Ensure Google Calendar API is enabled in your project
- Check that credentials are from the same project where API is enabled

## Production Setup

For production, use your domain instead of localhost:
- `https://protobox.example.com/admin/api/v1/oauth/callback/google_calendar`
- `https://dashboard.example.com/api/oauth/callback/google_calendar`