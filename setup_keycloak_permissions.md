# Keycloak Setup Guide for Equivalencias App

## Current Issue
The `equivalencias-app` client in Keycloak lacks the necessary permissions to access user data via the Admin REST API. This prevents the application from retrieving users with the `evaluador` role.

## Required Keycloak Configuration

### 1. Client Configuration
Ensure the client `equivalencias-app` has the following settings:

**Basic Settings:**
- Client ID: `equivalencias-app`
- Client Protocol: `openid-connect`
- Access Type: `confidential`
- Service Accounts Enabled: `ON`
- Authorization Enabled: `ON` (optional, but recommended)

### 2. Service Account Roles
The client's service account needs these roles to access the Admin REST API:

**Navigate to:** Clients → equivalencias-app → Service Account Roles

**Add these Client Roles from `realm-management`:**
- `view-users` - To view user information
- `view-clients` - To get client UUID for role queries
- `query-users` - To query users by various criteria
- `view-realm` - To access realm information
- `manage-users` (optional) - If you need to modify user data

### 3. Required Client Roles
Make sure these roles exist in your client:

**Navigate to:** Clients → equivalencias-app → Roles

Create these roles if they don't exist:
- `admin`
- `depto-estudiantes` 
- `evaluador`
- `lector`

### 4. User Role Assignment
For testing, ensure you have users with the `evaluador` role:

**Navigate to:** Users → [Select User] → Role Mappings → Client Roles → equivalencias-app

Assign the `evaluador` role to test users.

## Verification Steps

After making these changes:

1. Run the test script: `python test_keycloak.py`
2. Look for successful client UUID retrieval
3. Verify that evaluador users are found
4. Check that roles are properly mapped

## Troubleshooting

### Common Issues:

**403 Forbidden Errors:**
- Service account lacks proper realm-management roles
- Solution: Add the roles listed above

**Empty User Lists:**
- No users have the required client roles assigned
- Solution: Assign `evaluador` role to test users

**Token Issues:**
- Client secret may be incorrect
- Client may not have service accounts enabled
- Solution: Verify client configuration

### Environment Variables
Ensure these are set correctly:
```
KEYCLOAK_SERVER_URL=https://huayca.crub.uncoma.edu.ar/auth
KEYCLOAK_REALM=CRUB
KEYCLOAK_CLIENT_ID=equivalencias-app
KEYCLOAK_CLIENT_SECRET=[your-client-secret]
KEYCLOAK_REDIRECT_URI=http://127.0.0.1:5000/auth/callback
```

## Expected Results After Setup

After proper configuration, the test should show:
- ✅ Client UUID retrieved successfully
- ✅ Evaluador users found from Keycloak
- ✅ Role mapping working correctly
- ✅ Local database synced with Keycloak data
