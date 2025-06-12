# Direct Keycloak Authentication Changes

This document describes the changes made to implement direct Keycloak authentication without redirecting users away from the application.

## Changes Made

### 1. KeycloakService Enhancement
- **File**: `app/services/keycloak_service.py`
- **New Method**: `authenticate_with_password(username, password)`
- **Purpose**: Authenticates users directly against Keycloak using the Resource Owner Password Credentials Grant flow
- **Benefits**: 
  - Users stay within the application
  - No external redirects to Keycloak login page
  - Seamless authentication experience

### 2. Authentication Route Updates
- **File**: `app/routes/auth.py`
- **New Function**: `handle_keycloak_login()`
- **Changes**: Modified the login route to use direct authentication instead of OAuth2 redirect flow
- **Features**:
  - Processes username/password from the login form
  - Authenticates against Keycloak directly
  - Creates/updates users in the local database
  - Maintains session tokens for further API calls

### 3. Login Template Updates
- **File**: `app/templates/auth/login.html`
- **Changes**: Updated the Keycloak login section to show username/password form instead of a redirect button
- **Improvements**:
  - Better UX with familiar login form
  - Clearer labeling for institutional credentials
  - Added placeholder text for guidance

## How It Works

1. **User Input**: Users enter their CRUB institutional username and password
2. **Direct Authentication**: The app calls Keycloak's token endpoint with user credentials
3. **Token Exchange**: If authentication succeeds, Keycloak returns access and refresh tokens
4. **User Info**: The app retrieves user information from Keycloak using the access token
5. **Role Mapping**: Keycloak roles are mapped to application roles (admin, depto_estudiantes, evaluador, lector)
6. **Local User**: User is created or updated in the local database
7. **Session**: User is logged into the Flask application with appropriate dashboard redirect

## Configuration

The authentication method is controlled by the `USE_KEYCLOAK` environment variable:
- `USE_KEYCLOAK=true`: Uses direct Keycloak authentication
- `USE_KEYCLOAK=false`: Uses local authentication

## Security Considerations

- **Resource Owner Password Credentials Grant**: This flow requires the client to handle user credentials directly
- **Token Storage**: Access and refresh tokens are stored in the Flask session
- **HTTPS Required**: This authentication method should only be used over HTTPS in production
- **Client Configuration**: Ensure the Keycloak client is configured to allow the "Direct Access Grants" flow

## Keycloak Client Configuration

Make sure your Keycloak client has the following settings:
- **Access Type**: `confidential`
- **Direct Access Grants Enabled**: `ON`
- **Standard Flow Enabled**: `ON` (for backward compatibility)
- **Valid Redirect URIs**: Set appropriately for your domain

## Benefits of This Approach

1. **Better User Experience**: Users don't leave the application during login
2. **Consistent UI**: Login form matches the application's design
3. **Reduced Complexity**: No need to handle OAuth2 callback routes for basic authentication
4. **Faster Login**: Eliminates redirect round-trips
5. **Mobile Friendly**: Works better on mobile devices without external browser redirects

## Fallback Mechanism

If Keycloak authentication fails for any reason, the system provides helpful error messages and falls back gracefully. The original callback-based authentication can still be implemented alongside this method if needed.
