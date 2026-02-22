"""
Operations console API endpoints for monitoring and managing system operations.
"""
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import HTMLResponse
from typing import Optional
from pydantic import BaseModel
import os
from pathlib import Path

from app.core.ops_auth import (
    verify_ops_code,
    create_ops_session,
    verify_ops_session,
    invalidate_ops_session
)
from app.core.config import settings

router = APIRouter(prefix="/ops", tags=["operations"])


# Request/Response Models
class LoginRequest(BaseModel):
    secret_code: str


class LoginResponse(BaseModel):
    success: bool
    session_token: Optional[str] = None
    message: str


class StorageInfo(BaseModel):
    caches_size_gb: float
    jobs_size_gb: float
    total_size_gb: float
    threshold_gb: float
    usage_percentage: float
    status: str  # 'green', 'orange', 'red'


def verify_session(session_token: Optional[str]) -> None:
    """Verify operations session or raise HTTPException."""
    if not session_token:
        raise HTTPException(status_code=401, detail="No session token provided")
    
    if not verify_ops_session(session_token):
        raise HTTPException(status_code=401, detail="Invalid or expired session")


def get_directory_size(directory: Path) -> float:
    """Calculate total size of a directory in GB."""
    if not directory.exists():
        print(f"Warning: Directory does not exist: {directory}")
        return 0.0
    
    total_size = 0
    file_count = 0
    try:
        for item in directory.rglob('*'):
            if item.is_file():
                try:
                    total_size += item.stat().st_size
                    file_count += 1
                except (OSError, PermissionError) as e:
                    print(f"Warning: Cannot access file {item}: {e}")
        print(f"Calculated size for {directory}: {file_count} files, {total_size} bytes ({total_size / (1024 ** 3):.4f} GB)")
    except Exception as e:
        print(f"Error calculating size for {directory}: {e}")
    
    # Convert bytes to GB
    return total_size / (1024 ** 3)


@router.post("/login", response_model=LoginResponse)
async def ops_login(request: LoginRequest):
    """
    Authenticate operations user with secret code.
    Returns a session token if successful.
    """
    if verify_ops_code(request.secret_code):
        session_token = create_ops_session()
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
async def ops_logout(session_token: Optional[str] = Header(None, alias="X-Session-Token")):
    """Logout and invalidate the operations session."""
    if session_token:
        invalidate_ops_session(session_token)
    return {"success": True, "message": "Logged out successfully"}


@router.get("/storage-info", response_model=StorageInfo)
async def get_storage_info(session_token: Optional[str] = Header(None, alias="X-Session-Token")):
    """
    Get storage usage information for caches and jobs folders.
    Requires valid operations session.
    """
    verify_session(session_token)
    
    try:
        # Get the project root directory
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent
        
        # Get storage directories
        storages_dir = project_root / "storages"
        caches_dir = storages_dir / "caches"
        jobs_dir = storages_dir / "jobs"
        
        # Debug logging
        print(f"Storage info request - Project root: {project_root}")
        print(f"  Storages dir: {storages_dir} (exists: {storages_dir.exists()})")
        print(f"  Caches dir: {caches_dir} (exists: {caches_dir.exists()})")
        print(f"  Jobs dir: {jobs_dir} (exists: {jobs_dir.exists()})")
        
        # Calculate sizes
        caches_size = get_directory_size(caches_dir)
        jobs_size = get_directory_size(jobs_dir)
        total_size = caches_size + jobs_size
        
        # Get threshold from settings
        threshold_gb = float(settings.worker.staging_usage_threshold_in_gb)
        
        # Calculate usage percentage
        usage_percentage = (total_size / threshold_gb * 100) if threshold_gb > 0 else 0
        
        # Determine status color
        if usage_percentage < 50:
            status = "green"
        elif usage_percentage < 90:
            status = "orange"
        else:
            status = "red"
        
        return StorageInfo(
            caches_size_gb=round(caches_size, 2),
            jobs_size_gb=round(jobs_size, 2),
            total_size_gb=round(total_size, 2),
            threshold_gb=threshold_gb,
            usage_percentage=round(usage_percentage, 2),
            status=status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving storage info: {str(e)}")


@router.get("/", response_class=HTMLResponse)
async def ops_console_page():
    """Serve the operations console HTML page."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Operations Console</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #20c997 0%, #28a745 100%);
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
            background: linear-gradient(135deg, #20c997 0%, #28a745 100%);
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
            border-color: #20c997;
        }
        
        .submit-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #20c997 0%, #28a745 100%);
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
        
        .tabs {
            display: flex;
            border-bottom: 2px solid #e0e0e0;
            background: #f8f9fa;
        }
        
        .tab {
            padding: 15px 30px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
            font-weight: 500;
            color: #666;
        }
        
        .tab:hover {
            background: #e9ecef;
        }
        
        .tab.active {
            color: #20c997;
            border-bottom-color: #20c997;
            background: white;
        }
        
        .content {
            padding: 30px;
            overflow-y: auto;
            flex: 1;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .storage-card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 20px;
        }
        
        .storage-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .storage-title {
            font-size: 20px;
            font-weight: 600;
            color: #333;
        }
        
        .refresh-btn {
            background: #20c997;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        
        .refresh-btn:hover {
            background: #28a745;
        }
        
        .refresh-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .storage-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .stat-item {
            background: white;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #20c997;
        }
        
        .stat-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: 600;
            color: #333;
        }
        
        .stat-unit {
            font-size: 14px;
            color: #999;
            margin-left: 4px;
        }
        
        .progress-section {
            margin-top: 25px;
        }
        
        .progress-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-weight: 500;
            color: #555;
        }
        
        .progress-bar-container {
            width: 100%;
            height: 40px;
            background: #e0e0e0;
            border-radius: 20px;
            overflow: hidden;
            position: relative;
        }
        
        .progress-bar {
            height: 100%;
            transition: width 0.5s ease, background 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 14px;
        }
        
        .progress-bar.green {
            background: linear-gradient(90deg, #20c997 0%, #28a745 100%);
        }
        
        .progress-bar.orange {
            background: linear-gradient(90deg, #fd7e14 0%, #ffc107 100%);
        }
        
        .progress-bar.red {
            background: linear-gradient(90deg, #dc3545 0%, #e74c3c 100%);
        }
        
        .status-legend {
            display: flex;
            gap: 20px;
            margin-top: 15px;
            font-size: 12px;
            color: #666;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .legend-color {
            width: 16px;
            height: 16px;
            border-radius: 3px;
        }
        
        .legend-color.green {
            background: #28a745;
        }
        
        .legend-color.orange {
            background: #fd7e14;
        }
        
        .legend-color.red {
            background: #dc3545;
        }
        
        .hidden {
            display: none;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        
        .last-updated {
            text-align: right;
            font-size: 12px;
            color: #999;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Login View -->
        <div id="loginView">
            <div class="header">
                <h1>🔧 Operations Console</h1>
            </div>
            <div class="login-container">
                <h2>Operations Authentication</h2>
                <form class="login-form" id="loginForm">
                    <div class="form-group">
                        <label for="secretCode">Secret Code</label>
                        <input type="password" id="secretCode" name="secretCode" required 
                               placeholder="Enter operations secret code">
                    </div>
                    <button type="submit" class="submit-btn">Login</button>
                    <div class="error-message" id="loginError"></div>
                </form>
            </div>
        </div>
        
        <!-- Operations Console View -->
        <div id="consoleView" class="hidden">
            <div class="header">
                <h1>📊 Operations Dashboard</h1>
                <button class="logout-btn" onclick="logout()">Logout</button>
            </div>
            
            <div class="tabs">
                <div class="tab active" onclick="switchTab('storage')">
                    💾 Storage Management
                </div>
            </div>
            
            <div class="content">
                <!-- Storage Management Tab -->
                <div id="storageTab" class="tab-content active">
                    <div class="storage-card">
                        <div class="storage-header">
                            <div class="storage-title">Storage Usage Monitor</div>
                            <button class="refresh-btn" id="refreshBtn" onclick="loadStorageInfo()">
                                🔄 Refresh
                            </button>
                        </div>
                        
                        <div id="storageContent" class="loading">
                            Loading storage information...
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let sessionToken = null;
        let lastUpdateTime = null;
        
        // Login form handler
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const secretCode = document.getElementById('secretCode').value;
            const errorDiv = document.getElementById('loginError');
            
            try {
                const response = await fetch('/ops/login', {
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
                    await loadStorageInfo();
                } else {
                    errorDiv.textContent = data.message;
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.textContent = 'Login failed: ' + error.message;
                errorDiv.style.display = 'block';
            }
        });
        
        // Load storage information
        async function loadStorageInfo() {
            const refreshBtn = document.getElementById('refreshBtn');
            const storageContent = document.getElementById('storageContent');
            
            refreshBtn.disabled = true;
            refreshBtn.textContent = '🔄 Loading...';
            
            try {
                const response = await fetch('/ops/storage-info', {
                    headers: {
                        'X-Session-Token': sessionToken
                    }
                });
                
                if (response.status === 401) {
                    logout();
                    return;
                }
                
                const data = await response.json();
                lastUpdateTime = new Date();
                renderStorageInfo(data);
            } catch (error) {
                storageContent.innerHTML = 
                    '<div class="error-message" style="display:block">Error loading storage info: ' + 
                    error.message + '</div>';
            } finally {
                refreshBtn.disabled = false;
                refreshBtn.textContent = '🔄 Refresh';
            }
        }
        
        // Render storage information
        function renderStorageInfo(data) {
            const storageContent = document.getElementById('storageContent');
            
            const html = `
                <div class="storage-stats">
                    <div class="stat-item">
                        <div class="stat-label">Caches Folder</div>
                        <div class="stat-value">
                            ${data.caches_size_gb}
                            <span class="stat-unit">GB</span>
                        </div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Jobs Folder</div>
                        <div class="stat-value">
                            ${data.jobs_size_gb}
                            <span class="stat-unit">GB</span>
                        </div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Total Usage</div>
                        <div class="stat-value">
                            ${data.total_size_gb}
                            <span class="stat-unit">GB</span>
                        </div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Threshold</div>
                        <div class="stat-value">
                            ${data.threshold_gb}
                            <span class="stat-unit">GB</span>
                        </div>
                    </div>
                </div>
                
                <div class="progress-section">
                    <div class="progress-label">
                        <span>Storage Usage</span>
                        <span><strong>${data.usage_percentage}%</strong> of threshold</span>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar ${data.status}" style="width: ${Math.min(data.usage_percentage, 100)}%">
                            ${data.usage_percentage}%
                        </div>
                    </div>
                    
                    <div class="status-legend">
                        <div class="legend-item">
                            <div class="legend-color green"></div>
                            <span>Good (&lt; 50%)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color orange"></div>
                            <span>Warning (50-90%)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color red"></div>
                            <span>Critical (&gt; 90%)</span>
                        </div>
                    </div>
                    
                    <div class="last-updated">
                        Last updated: ${lastUpdateTime.toLocaleString()}
                    </div>
                </div>
            `;
            
            storageContent.innerHTML = html;
        }
        
        // Switch between tabs
        function switchTab(tabName) {
            // Update tab buttons
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => tab.classList.remove('active'));
            event.target.classList.add('active');
            
            // Update tab content
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.classList.remove('active'));
            document.getElementById(tabName + 'Tab').classList.add('active');
        }
        
        // Logout
        async function logout() {
            if (sessionToken) {
                try {
                    await fetch('/ops/logout', {
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
            lastUpdateTime = null;
            document.getElementById('loginView').classList.remove('hidden');
            document.getElementById('consoleView').classList.add('hidden');
            document.getElementById('secretCode').value = '';
            document.getElementById('loginError').style.display = 'none';
        }
        
        // Auto-refresh every 30 seconds when on storage tab
        setInterval(() => {
            if (sessionToken && document.getElementById('storageTab').classList.contains('active')) {
                loadStorageInfo();
            }
        }, 30000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)
