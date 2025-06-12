# Generic Keycloak Integration Guide - Role-Based User Management System

## Overview

This document describes a generic Keycloak integration pattern for web applications requiring authentication, role-based authorization, and user assignment management. The system supports both local authentication (fallback) and Keycloak-based authentication, making it suitable for various project types including academic systems, project management tools, task assignment platforms, and administrative applications.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Web App       │    │    Keycloak      │    │   Local Database   │
│   (Flask/Any)   │    │                  │    │                     │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────────┐ │
│ │Auth Routes  │◄┼────┤ │OAuth2/OIDC   │ │    │ │User Model       │ │
│ └─────────────┘ │    │ │Endpoints     │ │    │ │- Local Users    │ │
│                 │    │ └──────────────┘ │    │ │- Keycloak Users │ │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ └─────────────────┘ │
│ │Keycloak     │◄┼────┤ │Admin REST    │ │    │                     │
│ │Service      │ │    │ │API           │ │    │                     │
│ └─────────────┘ │    │ └──────────────┘ │    │                     │
│                 │    │                  │    │                     │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │                     │
│ │Assignment   │◄┼────┤ │Client Roles  │ │    │                     │
│ │Service      │ │    │ │- admin       │ │    │                     │
│ └─────────────┘ │    │ │- manager     │ │    │                     │
│                 │    │ │- worker      │ │    │                     │
└─────────────────┘    │ │- viewer      │ │    └─────────────────────┘
                       │ └──────────────┘ │
                       └──────────────────┘
```

## 1. Authentication Flow

### 1.1 OAuth2/OIDC Flow

```python
# Generic authentication flow sequence:
1. User clicks "Login" → /auth/login (POST)
2. App redirects to Keycloak authorization endpoint
3. User authenticates in Keycloak
4. Keycloak redirects to callback URL with authorization code
5. App exchanges code for access token → /auth/callback
6. App gets user info using access token
7. App maps Keycloak roles to application roles
8. App creates/updates local user record
9. User is logged into application session
```

### 1.2 Key Components

#### Generic Authentication Route (Framework Agnostic Pseudocode)
```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    use_keycloak = get_config('USE_KEYCLOAK', False)
    
    if request.method == 'POST':
        if use_keycloak:
            # Redirect to Keycloak
            keycloak_service = KeycloakService()
            auth_url = keycloak_service.get_auth_url()
            return redirect(auth_url)
        else:
            # Local authentication fallback
            return handle_local_login()

@app.route('/callback')
def callback():
    """Handle Keycloak OAuth callback"""
    code = request.args.get('code')
    
    # Exchange code for token
    keycloak_service = KeycloakService()
    token = keycloak_service.exchange_code_for_token(code)
    
    # Get user info
    user_info = keycloak_service.get_user_info(token)
    
    # Map roles (customize this for your app)
    app_role = keycloak_service.map_keycloak_roles_to_app_roles(user_info)
    
    # Create/update user in your system
    user = User.create_or_update_from_keycloak(user_info, user_info.get('sub'), app_role)
    
    # Login user in your session system
    login_user(user)
    return redirect_to_dashboard(user)
```

## 2. Role-Based Authorization

### 2.1 Role Mapping

The system maps Keycloak client roles to application roles (customize these for your specific needs):

```python
# Generic Keycloak Service - Role Mapping
def map_keycloak_roles_to_app_roles(self, user_info):
    """Map Keycloak roles to application roles - CUSTOMIZE FOR YOUR APP"""
    app_role = 'viewer'  # Default role
    
    resource_access = user_info.get('resource_access', {})
    client_access = resource_access.get(self.client_id, {})
    client_roles = client_access.get('roles', [])
    
    # Role priority (highest to lowest) - CUSTOMIZE THESE
    if 'admin' in client_roles:
        app_role = 'admin'
    elif 'manager' in client_roles:
        app_role = 'manager'
    elif 'worker' in client_roles or 'contributor' in client_roles:
        app_role = 'worker'
    else:
        app_role = 'viewer'  # Default
    
    return app_role
```

### 2.2 Generic Role Hierarchy Examples

#### Example 1: Project Management System
```
admin (Full system access)
├── Can manage all projects
├── Can manage all users
├── Can assign/unassign team members
└── Can view all reports

manager (Project/Team manager)
├── Can create/manage assigned projects
├── Can assign workers to tasks
├── Can view team performance
└── Can approve/reject work

worker (Team member/contributor)
├── Can view assigned tasks/projects
├── Can update task status
├── Can submit work/reports
└── Can communicate with team

viewer (Read-only access)
└── Can view public projects/reports
```

#### Example 2: Academic/Educational System
```
admin (System administrator)
├── Can manage all courses/users
├── Can assign instructors to courses
├── Can view all data/reports
└── Can configure system settings

instructor (Course instructor)
├── Can manage assigned courses
├── Can grade student work
├── Can view student progress
└── Can communicate with students

student (Course participant)
├── Can view enrolled courses
├── Can submit assignments
├── Can view grades/feedback
└── Can participate in discussions

auditor (Read-only observer)
└── Can view course materials/progress
```

#### Example 3: Task Assignment System
```
admin (System administrator)
├── Can manage all tasks/users
├── Can assign specialists to tasks
├── Can view all analytics
└── Can configure workflows

coordinator (Task coordinator)
├── Can create/manage task batches
├── Can assign tasks to specialists
├── Can monitor progress
└── Can approve completed work

specialist (Task performer)
├── Can view assigned tasks
├── Can update task status
├── Can submit completed work
└── Can communicate with coordinators

observer (Monitoring role)
└── Can view task progress/reports
```

## 3. Generic User Assignment Management System

### 3.1 Assignment Service Architecture

The generic `AssignmentService` class handles all user assignment operations, integrating both Keycloak and local database. This can be adapted for any system that needs to assign users to tasks, projects, cases, etc.

```python
class AssignmentService:
    """Generic service for managing user assignments to tasks/projects/items"""
    
    def __init__(self, worker_role='worker'):
        # Configure for your app's worker role name
        self.worker_role = worker_role
        self.keycloak_enabled = all([
            get_config('KEYCLOAK_SERVER_URL'),
            get_config('KEYCLOAK_REALM'),
            get_config('KEYCLOAK_CLIENT_ID'),
            get_config('KEYCLOAK_CLIENT_SECRET')
        ])
        
        if self.keycloak_enabled:
            self.keycloak_service = KeycloakService()
```

### 3.2 Generic User Synchronization

#### Automatic Sync Pattern
```python
def get_all_workers(self):
    """Get all workers, preferring Keycloak data when available"""
    if self.keycloak_enabled and self.keycloak_service:
        try:
            # Get workers from Keycloak and sync to local DB
            workers = self.keycloak_service.get_users_by_role(self.worker_role)
            return self.sync_workers_to_local_db(workers)
        except Exception as e:
            print(f"ERROR: Keycloak failed, falling back to local DB: {e}")
    
    # Fallback to local database
    return User.query.filter_by(role=self.worker_role).all()

def sync_workers_to_local_db(self, keycloak_workers):
    """Sync Keycloak workers to local database"""
    local_workers = []
    
    for worker_data in keycloak_workers:
        # Check if user exists locally
        user = User.query.filter_by(keycloak_id=worker_data['id']).first()
        if not user:
            user = User.query.filter_by(email=worker_data.get('email')).first()
        
        if not user and worker_data.get('email'):
            # Create new user
            user = User(
                username=worker_data.get('username', worker_data.get('email')),
                email=worker_data.get('email'),
                first_name=worker_data.get('firstName', ''),
                last_name=worker_data.get('lastName', ''),
                role=self.worker_role,
                keycloak_id=worker_data['id'],
                is_keycloak_user=True
            )
            db.session.add(user)
        elif user:
            # Update existing user
            user.keycloak_id = worker_data['id']
            user.is_keycloak_user = True
            user.role = self.worker_role
            # Update other fields as needed
        
        if user:
            local_workers.append(user)
    
    try:
        db.session.commit()
        return local_workers
    except Exception as e:
        db.session.rollback()
        raise e
```

### 3.3 Generic Keycloak Admin API Integration

#### Service Account Setup (Same for any application)
The application uses a service account to access Keycloak's Admin REST API:

```python
def get_admin_token(self):
    """Get admin token for API access"""
    data = {
        'grant_type': 'client_credentials',
        'client_id': self.client_id,
        'client_secret': self.client_secret
    }
    
    response = requests.post(self.token_url, data=data)
    return response.json() if response.status_code == 200 else None
```

#### Required Keycloak Client Roles (Universal)
The service account needs these roles in `realm-management`:
- `view-users` - To view user information
- `view-clients` - To get client UUID for role queries
- `query-users` - To query users by various criteria
- `view-realm` - To access realm information

#### Fetching Users by Role (Generic Pattern)
```python
def get_users_by_role(self, role_name):
    """Get users by client role from Keycloak - Generic implementation"""
    admin_token = self.get_admin_token()
    client_uuid = self.get_client_uuid(admin_token['access_token'])
    
    url = f"{self.server_url}/admin/realms/{self.realm}/clients/{client_uuid}/roles/{role_name}/users"
    headers = {
        'Authorization': f"Bearer {admin_token['access_token']}",
        'Content-Type': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else []
```

## 4. Generic Assignment System

### 4.1 Workload-Based Assignment Pattern

This pattern can be adapted for any system that needs to distribute work fairly among users:

```python
def get_workers_with_workload(self, auto_sync=True):
    """Get all workers with their current workload - Generic pattern"""
    # Auto-sync workers from Keycloak if enabled and requested
    if auto_sync and self.keycloak_enabled and self.keycloak_service:
        try:
            print("DEBUG: Auto-syncing workers from Keycloak")
            self.sync_all_workers()
        except Exception as e:
            print(f"WARNING: Auto-sync failed, continuing with local data: {str(e)}")
    
    workers = self.get_all_workers()
    workers_with_workload = []
    
    for worker in workers:
        # Count assigned active items (customize the query for your model)
        workload = WorkItem.query.filter(
            WorkItem.assigned_user_id == worker.id,
            WorkItem.status.in_(['pending', 'in_progress'])  # Customize statuses
        ).count()
        
        workers_with_workload.append({
            'worker': worker,
            'workload': workload,
            'total_assigned': WorkItem.query.filter_by(assigned_user_id=worker.id).count()
        })
    
    # Sort by workload (ascending) so workers with less work appear first
    workers_with_workload.sort(key=lambda x: x['workload'])
    
    return workers_with_workload

def suggest_worker_for_assignment(self):
    """Suggest a worker based on current workload"""
    workers_with_workload = self.get_workers_with_workload()
    
    if workers_with_workload:
        # Return worker with least workload
        return workers_with_workload[0]['worker']
    
    return None
```

### 4.2 Generic Assignment Operations

#### Assign User to Item
```python
def assign_user_to_item(self, item_id, user_id):
    """Generic assignment operation - Customize for your models"""
    item = WorkItem.query.get(item_id)  # Replace with your model
    user = self.get_user_by_id(user_id)
    
    if not item:
        return False, "Item not found"
    
    if not user:
        return False, "User not found"
    
    try:
        item.assigned_user_id = user.id
        # Change status if needed (customize for your workflow)
        if item.status == 'pending':
            item.status = 'assigned'
        
        db.session.commit()
        return True, f"User {user.first_name} {user.last_name} assigned successfully"
    except Exception as e:
        db.session.rollback()
        return False, f"Error assigning user: {str(e)}"

def unassign_user_from_item(self, item_id):
    """Generic unassignment operation - Customize for your models"""
    item = WorkItem.query.get(item_id)  # Replace with your model
    
    if not item:
        return False, "Item not found"
    
    try:
        item.assigned_user_id = None
        # Optionally change status back (customize for your workflow)
        if item.status == 'assigned' and not item.has_started_work():
            item.status = 'pending'
        
        db.session.commit()
        return True, "User unassigned successfully"
    except Exception as e:
        db.session.rollback()
        return False, f"Error unassigning user: {str(e)}"
```

### 4.3 Generic Assignment Interface Patterns

#### Admin Interface Pattern
```python
# Generic admin route for managing assignments
@app.route('/admin/manage_assignments')
@login_required
@admin_required
def manage_assignments():
    """Admin view for managing user assignments and workload"""
    assignment_service = AssignmentService()
    
    # Get workers with workload information
    workers_with_workload = assignment_service.get_workers_with_workload()
    
    # Get all items (customize for your model)
    all_items = WorkItem.query.all()
    
    # Get unassigned items
    unassigned_items = WorkItem.query.filter(
        WorkItem.assigned_user_id.is_(None),
        WorkItem.status.in_(['pending', 'ready'])  # Customize statuses
    ).all()
    
    return render_template('admin/manage_assignments.html', 
                         workers_with_workload=workers_with_workload,
                         unassigned_items=unassigned_items,
                         all_items=all_items)

@app.route('/admin/assign_user', methods=['POST'])
@login_required
@admin_required
def assign_user():
    """Admin endpoint to assign user to item"""
    assignment_service = AssignmentService()
    item_id = request.form.get('item_id')
    user_id = request.form.get('user_id')
    
    if not item_id:
        flash('Item ID required', 'danger')
        return redirect(url_for('admin.manage_assignments'))
    
    if user_id:
        success, message = assignment_service.assign_user_to_item(item_id, user_id)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    else:
        success, message = assignment_service.unassign_user_from_item(item_id)
        if success:
            flash(message, 'info')
        else:
            flash(message, 'danger')
    
    return redirect(url_for('admin.manage_assignments'))
```

#### Manager Interface Pattern
```python
# Generic manager route for assignments
@app.route('/manager/items')
@login_required
@manager_required
def list_items():
    """Manager view for items with assignment capabilities"""
    assignment_service = AssignmentService()
    
    # Get fresh worker data for assignments
    workers_with_workload = assignment_service.get_workers_with_workload()
    
    # Get items (customize filtering for your needs)
    items = WorkItem.query.filter_by(manager_id=current_user.id).all()
    
    return render_template('manager/list_items.html', 
                         items=items, 
                         workers_with_workload=workers_with_workload)

@app.route('/manager/auto_assign/<int:item_id>', methods=['POST'])
@login_required
@manager_required
def auto_assign_worker(item_id):
    """Auto-assign worker based on workload"""
    assignment_service = AssignmentService()
    suggested_worker = assignment_service.suggest_worker_for_assignment()
    
    if suggested_worker:
        success, message = assignment_service.assign_user_to_item(item_id, suggested_worker.id)
        if success:
            flash(f"Auto-assigned to {suggested_worker.first_name} {suggested_worker.last_name}", 'success')
        else:
            flash(message, 'danger')
    else:
        flash("No workers available for assignment", 'warning')
    
    return redirect(url_for('manager.list_items'))
```

## 5. Generic Database Integration

### 5.1 Generic User Model Extensions

Your user model should support both local and Keycloak users (adapt field names to your conventions):

```python
class User(db.Model):  # Or UserMixin, depending on your framework
    # ... existing fields ...
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=True)  # Nullable for Keycloak users
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    
    # Keycloak integration fields (ADD THESE)
    keycloak_id = db.Column(db.String(100), unique=True, nullable=True)
    is_keycloak_user = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Optional: role-specific fields
    department = db.Column(db.String(100))  # For organization
    employee_id = db.Column(db.String(20), unique=True)  # For identification
    
    @classmethod
    def create_or_update_from_keycloak(cls, keycloak_user, keycloak_id, app_role):
        """Create or update user from Keycloak data - CUSTOMIZE FOR YOUR FIELDS"""
        user = cls.query.filter_by(keycloak_id=keycloak_id).first()
        
        if not user:
            # Check if user exists by email
            user = cls.query.filter_by(email=keycloak_user.get('email')).first()
            if user:
                # Update existing user with Keycloak data
                user.keycloak_id = keycloak_id
                user.is_keycloak_user = True
            else:
                # Create new user - CUSTOMIZE FIELD MAPPING
                user = cls(
                    username=keycloak_user.get('preferred_username', keycloak_user.get('email')),
                    email=keycloak_user.get('email'),
                    first_name=keycloak_user.get('given_name', ''),
                    last_name=keycloak_user.get('family_name', ''),
                    role=app_role,
                    keycloak_id=keycloak_id,
                    is_keycloak_user=True
                )
                db.session.add(user)
        
        # Always update role to match Keycloak - IMPORTANT!
        user.role = app_role
        user.last_login = datetime.now()
        
        # Update other fields as needed - CUSTOMIZE
        user.first_name = keycloak_user.get('given_name', user.first_name)
        user.last_name = keycloak_user.get('family_name', user.last_name)
        user.email = keycloak_user.get('email', user.email)
        
        db.session.commit()
        return user
```

### 5.2 Generic Work Item Model

Adapt this pattern for your specific domain (tasks, tickets, cases, projects, etc.):

```python
class WorkItem(db.Model):  # Rename to your domain: Task, Ticket, Case, Project, etc.
    """Generic model for items that can be assigned to users"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending', nullable=False)
    priority = db.Column(db.String(20), default='medium')
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    due_date = db.Column(db.DateTime, nullable=True)
    
    # Assignment fields
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Adjust table name
    assigned_user = db.relationship('User', backref='assigned_items')
    
    # Optional: creator/manager tracking
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def has_started_work(self):
        """Check if work has been started on this item"""
        # Customize based on your workflow
        return self.status not in ['pending', 'assigned']
```

### 5.3 Generic Synchronization Strategy

The system maintains both Keycloak and local user records:
- **Keycloak users**: Authoritative source for authentication and roles
- **Local users**: Cache for performance and offline capability
- **Hybrid approach**: Local admin users for development/emergency access

```python
# Generic sync pattern
def sync_users_from_keycloak(role_name):
    """Generic function to sync users of a specific role from Keycloak"""
    try:
        keycloak_service = KeycloakService()
        keycloak_users = keycloak_service.get_users_by_role(role_name)
        
        synced_users = []
        for user_data in keycloak_users:
            user = User.create_or_update_from_keycloak(
                user_data, 
                user_data['id'], 
                role_name
            )
            synced_users.append(user)
        
        print(f"Successfully synced {len(synced_users)} {role_name} users from Keycloak")
        return synced_users
    except Exception as e:
        print(f"Error syncing {role_name} users: {str(e)}")
        return []
```

## 6. Generic Environment Configuration

### 6.1 Required Environment Variables (Customize values for your setup)

```bash
# Keycloak Configuration - CUSTOMIZE THESE VALUES
KEYCLOAK_SERVER_URL=https://your-keycloak-server.domain.com/auth
KEYCLOAK_REALM=your-realm-name
KEYCLOAK_CLIENT_ID=your-app-client-id
KEYCLOAK_CLIENT_SECRET=your-client-secret-here
KEYCLOAK_REDIRECT_URI=https://your-app.domain.com/auth/callback

# Feature Toggle
USE_KEYCLOAK=true

# Optional: Custom role configuration
DEFAULT_USER_ROLE=viewer
WORKER_ROLE_NAME=worker
MANAGER_ROLE_NAME=manager
ADMIN_ROLE_NAME=admin
```

### 6.2 Generic Keycloak Client Configuration

#### Basic Settings (Same for any application)
- **Client ID**: `your-app-name` (e.g., `task-manager`, `project-tracker`)
- **Client Protocol**: `openid-connect`
- **Access Type**: `confidential`
- **Service Accounts Enabled**: `ON`
- **Valid Redirect URIs**: `https://your-app.domain.com/auth/callback`

#### Client Roles (Customize for your application)
Create these roles in your client (examples for different app types):

**Generic Roles:**
- `admin` - Full system access
- `manager` - Management/coordination role  
- `worker` - Primary work role
- `viewer` - Read-only access

**Project Management Example:**
- `admin`, `project-manager`, `team-member`, `stakeholder`

**Task Assignment Example:**
- `admin`, `coordinator`, `specialist`, `observer`

**Academic Example:**
- `admin`, `instructor`, `student`, `auditor`

#### Service Account Roles (Universal - don't change these)
Assign these roles from `realm-management` to the service account:
- `view-users`
- `view-clients`
- `query-users`
- `view-realm`

## 7. Error Handling and Fallbacks

### 7.1 Graceful Degradation

The system implements multiple fallback mechanisms:

```python
# If Keycloak is unavailable, fall back to local authentication
def get_all_evaluadores(self):
    if self.keycloak_enabled and self.keycloak_service:
        try:
            return self.keycloak_service.get_evaluadores()
        except Exception as e:
            print(f"Keycloak failed: {e}, falling back to local DB")
    
    return Usuario.query.filter_by(rol='evaluador').all()
```

### 7.2 Configuration Validation

```python
def get_service_status(self):
    """Get detailed service status information"""
    status = {
        'configured': all([self.server_url, self.realm, self.client_id, self.client_secret]),
        'available': False,
        'can_access_users': False,
        'error': None
    }
    
    # Test connectivity and permissions
    if status['configured']:
        try:
            admin_token = self.get_admin_token()
            if admin_token:
                status['available'] = True
                evaluadores = self.get_users_by_role('evaluador')
                status['can_access_users'] = True
                status['evaluador_count'] = len(evaluadores)
        except Exception as e:
            status['error'] = str(e)
    
    return status
```

## 8. Security Considerations

### 8.1 Token Management
- Access tokens stored in Flask session
- Refresh tokens used for token renewal
- Automatic token validation before API calls

### 8.2 Role Security
- Role assignments managed in Keycloak only
- Local role caching with periodic sync
- Role-based route protection using decorators

### 8.3 API Security
- Service account with minimal required permissions
- Secure client secret management
- HTTPS required for production

## 9. Testing and Monitoring

### 9.1 Test Script
The included `test_keycloak.py` script validates:
- Keycloak connectivity
- Service account permissions
- Evaluator synchronization
- Role mapping

### 9.2 Monitoring
- Service status endpoint
- Sync operation logging
- Error tracking for authentication failures

## 10. Implementation Checklist for New Projects

To integrate this Keycloak system into another project:

### 10.1 Backend Setup
- [ ] Install required dependencies: `python-keycloak`, `requests`
- [ ] Create `KeycloakService` class with OAuth2/OIDC methods
- [ ] Create `EvaluadorService` class for user management
- [ ] Add Keycloak fields to User model
- [ ] Implement authentication routes with callback handling
- [ ] Add role-based decorators for route protection

### 10.2 Keycloak Configuration
- [ ] Create new client in Keycloak realm
- [ ] Configure client with service account enabled
- [ ] Create required client roles
- [ ] Assign service account permissions
- [ ] Configure redirect URIs

### 10.3 Frontend Integration
- [ ] Update login templates for Keycloak
- [ ] Add evaluator management interfaces
- [ ] Implement assignment/unassignment forms
- [ ] Add sync buttons and status indicators

### 10.4 Testing
- [ ] Test authentication flow
- [ ] Verify role mapping
- [ ] Test evaluator synchronization
- [ ] Validate assignment operations
- [ ] Test fallback scenarios

This comprehensive integration provides a robust, scalable solution for authentication and evaluator management that can be adapted to similar academic or administrative systems.
