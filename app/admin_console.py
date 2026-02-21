"""
Admin console API endpoints for managing system configuration.
"""
from fastapi import APIRouter, HTTPException, Header, Response
from fastapi.responses import HTMLResponse
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from app.core.admin_auth import (
    verify_admin_code,
    create_admin_session,
    verify_admin_session,
    invalidate_admin_session
)
from app.core.config_manager import (
    get_config_structure,
    read_config_file,
    update_config_file,
    backup_config_file,
    validate_config_updates
)
from app.core.db_test import test_database_from_config
from app.core.hsi_test import test_hsi_from_config

router = APIRouter(prefix="/admin", tags=["admin"])


# Request/Response Models
class LoginRequest(BaseModel):
    secret_code: str


class LoginResponse(BaseModel):
    success: bool
    session_token: Optional[str] = None
    message: str


class ConfigUpdateRequest(BaseModel):
    updates: Dict[str, Dict[str, str]]


class ConfigUpdateResponse(BaseModel):
    success: bool
    message: str
    backup_file: Optional[str] = None
    errors: List[str] = []


def verify_session(session_token: Optional[str]) -> None:
    """Verify admin session or raise HTTPException."""
    if not session_token:
        raise HTTPException(status_code=401, detail="No session token provided")
    
    if not verify_admin_session(session_token):
        raise HTTPException(status_code=401, detail="Invalid or expired session")


@router.post("/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    """
    Authenticate admin user with secret code.
    Returns a session token if successful.
    """
    if verify_admin_code(request.secret_code):
        session_token = create_admin_session()
        return LoginResponse(
            success=True,
            session_token=session_token,
            message="Login successful"
        )
    else:
        return LoginResponse(
            success=False,
            message="Invalid secret code"
        )


@router.post("/logout")
async def admin_logout(session_token: Optional[str] = Header(None, alias="X-Session-Token")):
    """Logout and invalidate the admin session."""
    if session_token:
        invalidate_admin_session(session_token)
    return {"success": True, "message": "Logged out successfully"}


@router.get("/config")
async def get_config(session_token: Optional[str] = Header(None, alias="X-Session-Token")):
    """
    Get the current configuration structure with all fields.
    Requires valid admin session.
    """
    verify_session(session_token)
    
    try:
        config_structure = get_config_structure()
        return {
            "success": True,
            "config": config_structure
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading configuration: {str(e)}")


@router.get("/config/raw")
async def get_config_raw(session_token: Optional[str] = Header(None, alias="X-Session-Token")):
    """
    Get the raw configuration as a dictionary.
    Requires valid admin session.
    """
    verify_session(session_token)
    
    try:
        config_data = read_config_file()
        return {
            "success": True,
            "config": config_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading configuration: {str(e)}")


@router.post("/config/update", response_model=ConfigUpdateResponse)
async def update_config(
    request: ConfigUpdateRequest,
    session_token: Optional[str] = Header(None, alias="X-Session-Token")
):
    """
    Update configuration fields.
    Creates a backup before updating.
    Requires valid admin session.
    """
    verify_session(session_token)
    
    # Validate updates
    validation_errors = validate_config_updates(request.updates)
    if validation_errors:
        return ConfigUpdateResponse(
            success=False,
            message="Validation failed",
            errors=validation_errors
        )
    
    try:
        # Create backup before updating
        backup_path = backup_config_file()
        
        # Apply updates
        success = update_config_file(request.updates)
        
        if success:
            return ConfigUpdateResponse(
                success=True,
                message="Configuration updated successfully",
                backup_file=str(backup_path)
            )
        else:
            return ConfigUpdateResponse(
                success=False,
                message="Failed to update configuration"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating configuration: {str(e)}")


@router.post("/test-database")
async def test_database_connection(session_token: Optional[str] = Header(None, alias="X-Session-Token")):
    """
    Test the database connection using current configuration.
    Requires valid admin session.
    """
    verify_session(session_token)
    
    try:
        config_data = read_config_file()
        
        if "database" not in config_data:
            raise HTTPException(status_code=400, detail="Database configuration section not found")
        
        db_config = config_data["database"]
        result = test_database_from_config(db_config)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "message": f"Error testing database connection: {str(e)}",
            "details": {}
        }


@router.post("/test-hsi")
async def test_hsi_binary(session_token: Optional[str] = Header(None, alias="X-Session-Token")):
    """
    Test the HSI binary using current configuration.
    Requires valid admin session.
    """
    verify_session(session_token)
    
    try:
        config_data = read_config_file()
        
        if "sds_sync" not in config_data:
            raise HTTPException(status_code=400, detail="SDS Sync configuration section not found")
        
        sds_sync_config = config_data["sds_sync"]
        result = test_hsi_from_config(sds_sync_config)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "message": f"Error testing HSI binary: {str(e)}",
            "details": {}
        }


@router.get("/", response_class=HTMLResponse)
async def admin_console_page():
    """Serve the admin console HTML page."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Admin Console</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 1200px;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            border-radius: 12px 12px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 24px;
            font-weight: 600;
        }
        
        .logout-btn {
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 8px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .logout-btn:hover {
            background: rgba(255,255,255,0.3);
        }
        
        .login-container {
            padding: 60px 40px;
            text-align: center;
        }
        
        .login-container h2 {
            color: #333;
            margin-bottom: 30px;
            font-size: 28px;
        }
        
        .login-form {
            max-width: 400px;
            margin: 0 auto;
        }
        
        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }
        
        .form-group label {
            display: block;
            color: #555;
            margin-bottom: 8px;
            font-weight: 500;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .submit-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .submit-btn:hover {
            transform: translateY(-2px);
        }
        
        .error-message {
            background: #fee;
            color: #c33;
            padding: 12px;
            border-radius: 6px;
            margin-top: 20px;
            display: none;
        }
        
        .success-message {
            background: #efe;
            color: #3c3;
            padding: 12px;
            border-radius: 6px;
            margin-top: 20px;
            display: none;
        }
        
        .config-container {
            padding: 30px;
            overflow-y: auto;
            flex: 1;
        }
        
        .section {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
            cursor: pointer;
            user-select: none;
        }
        
        .section-header:hover {
            opacity: 0.8;
        }
        
        .section-title {
            font-size: 20px;
            color: #667eea;
            font-weight: 600;
            margin: 0;
        }
        
        .toggle-btn {
            background: #667eea;
            color: white;
            border: none;
            border-radius: 50%;
            width: 28px;
            height: 28px;
            font-size: 18px;
            line-height: 1;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.3s, background 0.3s;
        }
        
        .toggle-btn:hover {
            background: #764ba2;
            transform: scale(1.1);
        }
        
        .toggle-btn.collapsed {
            transform: rotate(0deg);
        }
        
        .section-content {
            display: block;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }
        
        .section-content.collapsed {
            display: none;
        }
        
        .field-group {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 10px;
            margin-bottom: 15px;
            align-items: center;
        }
        
        .field-label {
            font-weight: 500;
            color: #555;
        }
        
        .field-input {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            width: 100%;
        }
        
        .field-input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .action-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 30px;
            border-top: 1px solid #e0e0e0;
            background: #f8f9fa;
            border-radius: 0 0 12px 12px;
        }
        
        .save-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .save-btn:hover {
            transform: translateY(-2px);
        }
        
        .save-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .test-db-btn {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
            margin-right: 10px;
        }
        
        .test-db-btn:hover {
            transform: translateY(-2px);
        }
        
        .test-db-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
        }
        
        .info-message {
            background: #e3f2fd;
            color: #1976d2;
            padding: 12px;
            border-radius: 6px;
            margin-top: 20px;
            display: none;
        }
        
        .hidden {
            display: none;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        
        @media (max-width: 768px) {
            .field-group {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Login View -->
        <div id="loginView">
            <div class="header">
                <h1>🔐 System Admin Console</h1>
            </div>
            <div class="login-container">
                <h2>Admin Authentication</h2>
                <form class="login-form" id="loginForm">
                    <div class="form-group">
                        <label for="secretCode">Secret Code</label>
                        <input type="password" id="secretCode" name="secretCode" required 
                               placeholder="Enter admin secret code">
                    </div>
                    <button type="submit" class="submit-btn">Login</button>
                    <div class="error-message" id="loginError"></div>
                </form>
            </div>
        </div>
        
        <!-- Admin Console View -->
        <div id="consoleView" class="hidden">
            <div class="header">
                <h1>⚙️ System Configuration Manager</h1>
                <button class="logout-btn" onclick="logout()">Logout</button>
            </div>
            <div class="config-container" id="configContainer">
                <div class="loading">Loading configuration...</div>
            </div>
            <div class="action-bar">
                <div>
                    <div class="success-message" id="saveSuccess"></div>
                    <div class="error-message" id="saveError"></div>
                    <div class="info-message" id="testInfo"></div>
                </div>
                <div class="button-group">
                    <button class="test-db-btn" id="testHsiBtn" onclick="testHsiBinary()">
                        📦 Test HSI
                    </button>
                    <button class="test-db-btn" id="testDbBtn" onclick="testDatabaseConnection()">
                        🔌 Test Database
                    </button>
                    <button class="save-btn" id="saveBtn" onclick="saveConfiguration()">
                        💾 Save Changes
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let sessionToken = null;
        let currentConfig = null;
        
        // Login form handler
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const secretCode = document.getElementById('secretCode').value;
            const errorDiv = document.getElementById('loginError');
            
            try {
                const response = await fetch('/admin/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ secret_code: secretCode })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    sessionToken = data.session_token;
                    document.getElementById('loginView').classList.add('hidden');
                    document.getElementById('consoleView').classList.remove('hidden');
                    await loadConfiguration();
                } else {
                    errorDiv.textContent = data.message;
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.textContent = 'Login failed: ' + error.message;
                errorDiv.style.display = 'block';
            }
        });
        
        // Load configuration
        async function loadConfiguration() {
            try {
                const response = await fetch('/admin/config', {
                    headers: {
                        'X-Session-Token': sessionToken
                    }
                });
                
                if (response.status === 401) {
                    logout();
                    return;
                }
                
                const data = await response.json();
                currentConfig = data.config;
                renderConfiguration(data.config);
            } catch (error) {
                document.getElementById('configContainer').innerHTML = 
                    '<div class="error-message" style="display:block">Error loading configuration: ' + 
                    error.message + '</div>';
            }
        }
        
        // Render configuration UI
        function renderConfiguration(config) {
            const container = document.getElementById('configContainer');
            container.innerHTML = '';
            
            config.forEach(section => {
                const sectionDiv = document.createElement('div');
                sectionDiv.className = 'section';
                
                // Create section header with toggle button
                const headerDiv = document.createElement('div');
                headerDiv.className = 'section-header';
                
                const titleDiv = document.createElement('div');
                titleDiv.className = 'section-title';
                titleDiv.textContent = `[${section.section}]`;
                headerDiv.appendChild(titleDiv);
                
                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'toggle-btn';
                toggleBtn.innerHTML = '+';
                toggleBtn.onclick = (e) => {
                    e.stopPropagation();
                    toggleSection(sectionDiv);
                };
                headerDiv.appendChild(toggleBtn);
                
                headerDiv.onclick = () => toggleSection(sectionDiv);
                sectionDiv.appendChild(headerDiv);
                
                // Create section content container
                const contentDiv = document.createElement('div');
                contentDiv.className = 'section-content collapsed';
                
                section.fields.forEach(field => {
                    const fieldGroup = document.createElement('div');
                    fieldGroup.className = 'field-group';
                    
                    const label = document.createElement('div');
                    label.className = 'field-label';
                    label.textContent = field.key;
                    fieldGroup.appendChild(label);
                    
                    const input = document.createElement('input');
                    input.className = 'field-input';
                    input.type = field.type === 'password' ? 'password' : 'text';
                    input.value = field.value;
                    input.dataset.section = section.section;
                    input.dataset.key = field.key;
                    fieldGroup.appendChild(input);
                    
                    contentDiv.appendChild(fieldGroup);
                });
                
                sectionDiv.appendChild(contentDiv);
                container.appendChild(sectionDiv);
            });
        }
        
        // Toggle section collapse/expand
        function toggleSection(sectionDiv) {
            const content = sectionDiv.querySelector('.section-content');
            const toggleBtn = sectionDiv.querySelector('.toggle-btn');
            
            if (content.classList.contains('collapsed')) {
                content.classList.remove('collapsed');
                toggleBtn.innerHTML = '−';
            } else {
                content.classList.add('collapsed');
                toggleBtn.innerHTML = '+';
            }
        }
        
        // Save configuration
        async function saveConfiguration() {
            const saveBtn = document.getElementById('saveBtn');
            const errorDiv = document.getElementById('saveError');
            const successDiv = document.getElementById('saveSuccess');
            
            errorDiv.style.display = 'none';
            successDiv.style.display = 'none';
            saveBtn.disabled = true;
            
            // Collect all input values
            const inputs = document.querySelectorAll('.field-input');
            const updates = {};
            
            inputs.forEach(input => {
                const section = input.dataset.section;
                const key = input.dataset.key;
                
                if (!updates[section]) {
                    updates[section] = {};
                }
                updates[section][key] = input.value;
            });
            
            try {
                const response = await fetch('/admin/config/update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Session-Token': sessionToken
                    },
                    body: JSON.stringify({ updates })
                });
                
                if (response.status === 401) {
                    logout();
                    return;
                }
                
                const data = await response.json();
                
                if (data.success) {
                    successDiv.textContent = data.message + 
                        (data.backup_file ? ` (Backup: ${data.backup_file})` : '');
                    successDiv.style.display = 'block';
                    setTimeout(() => {
                        successDiv.style.display = 'none';
                    }, 5000);
                } else {
                    errorDiv.textContent = data.message + 
                        (data.errors.length > 0 ? ': ' + data.errors.join(', ') : '');
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.textContent = 'Error saving configuration: ' + error.message;
                errorDiv.style.display = 'block';
            } finally {
                saveBtn.disabled = false;
            }
        }
        
        // Test HSI binary
        async function testHsiBinary() {
            const testHsiBtn = document.getElementById('testHsiBtn');
            const errorDiv = document.getElementById('saveError');
            const successDiv = document.getElementById('saveSuccess');
            const infoDiv = document.getElementById('testInfo');
            
            errorDiv.style.display = 'none';
            successDiv.style.display = 'none';
            infoDiv.style.display = 'none';
            testHsiBtn.disabled = true;
            testHsiBtn.textContent = '🔄 Testing...';
            
            try {
                const response = await fetch('/admin/test-hsi', {
                    method: 'POST',
                    headers: {
                        'X-Session-Token': sessionToken
                    }
                });
                
                if (response.status === 401) {
                    logout();
                    return;
                }
                
                const data = await response.json();
                
                if (data.success) {
                    successDiv.textContent = '✅ ' + data.message;
                    successDiv.style.display = 'block';
                    
                    // Show HSI details
                    if (data.details.hsi_bin_path) {
                        let detailsHtml = `<strong>HSI Binary Details:</strong><br>Path: ${data.details.hsi_bin_path}<br>`;
                        if (data.details.permissions) {
                            detailsHtml += `Permissions: ${data.details.permissions}<br>`;
                        }
                        if (data.details.file_size) {
                            detailsHtml += `Size: ${(data.details.file_size / 1024).toFixed(2)} KB<br>`;
                        }
                        if (data.details.version_info) {
                            detailsHtml += `Info: ${data.details.version_info}`;
                        }
                        infoDiv.innerHTML = detailsHtml;
                        infoDiv.style.display = 'block';
                    }
                    
                    setTimeout(() => {
                        successDiv.style.display = 'none';
                        infoDiv.style.display = 'none';
                    }, 10000);
                } else {
                    errorDiv.innerHTML = `<strong>❌ ${data.message}</strong>`;
                    if (data.details.error_message) {
                        errorDiv.innerHTML += `<br><small>${data.details.error_message}</small>`;
                    } else if (!data.details.configured) {
                        errorDiv.innerHTML += `<br><small>Please configure hsi_bin_path in the [sds_sync] section</small>`;
                    }
                    errorDiv.style.display = 'block';
                    
                    setTimeout(() => {
                        errorDiv.style.display = 'none';
                    }, 10000);
                }
            } catch (error) {
                errorDiv.textContent = '❌ Error testing HSI binary: ' + error.message;
                errorDiv.style.display = 'block';
            } finally {
                testHsiBtn.disabled = false;
                testHsiBtn.textContent = '📦 Test HSI';
            }
        }
        
        // Test database connection
        async function testDatabaseConnection() {
            const testDbBtn = document.getElementById('testDbBtn');
            const errorDiv = document.getElementById('saveError');
            const successDiv = document.getElementById('saveSuccess');
            const infoDiv = document.getElementById('testInfo');
            
            errorDiv.style.display = 'none';
            successDiv.style.display = 'none';
            infoDiv.style.display = 'none';
            testDbBtn.disabled = true;
            testDbBtn.textContent = '🔄 Testing...';
            
            try {
                const response = await fetch('/admin/test-database', {
                    method: 'POST',
                    headers: {
                        'X-Session-Token': sessionToken
                    }
                });
                
                if (response.status === 401) {
                    logout();
                    return;
                }
                
                const data = await response.json();
                
                if (data.success) {
                    let detailsText = '';
                    if (data.details.mysql_version) {
                        detailsText = ` (MySQL ${data.details.mysql_version})`;
                    }
                    successDiv.textContent = '✅ ' + data.message + detailsText;
                    successDiv.style.display = 'block';
                    
                    // Show connection details
                    if (data.details.connected_database) {
                        infoDiv.innerHTML = `
                            <strong>Connection Details:</strong><br>
                            Database: ${data.details.connected_database}<br>
                            User: ${data.details.connected_user}<br>
                            Host: ${data.details.host}:${data.details.port}
                        `;
                        infoDiv.style.display = 'block';
                    }
                    
                    setTimeout(() => {
                        successDiv.style.display = 'none';
                        infoDiv.style.display = 'none';
                    }, 10000);
                } else {
                    errorDiv.innerHTML = `<strong>❌ ${data.message}</strong>`;
                    if (data.details.error_message) {
                        errorDiv.innerHTML += `<br><small>${data.details.error_message}</small>`;
                    }
                    errorDiv.style.display = 'block';
                    
                    setTimeout(() => {
                        errorDiv.style.display = 'none';
                    }, 10000);
                }
            } catch (error) {
                errorDiv.textContent = '❌ Error testing database: ' + error.message;
                errorDiv.style.display = 'block';
            } finally {
                testDbBtn.disabled = false;
                testDbBtn.textContent = '🔌 Test Database';
            }
        }
        
        // Logout
        async function logout() {
            if (sessionToken) {
                try {
                    await fetch('/admin/logout', {
                        method: 'POST',
                        headers: {
                            'X-Session-Token': sessionToken
                        }
                    });
                } catch (error) {
                    console.error('Logout error:', error);
                }
            }
            
            sessionToken = null;
            document.getElementById('loginView').classList.remove('hidden');
            document.getElementById('consoleView').classList.add('hidden');
            document.getElementById('secretCode').value = '';
            document.getElementById('loginError').style.display = 'none';
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)
