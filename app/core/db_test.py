"""
Database connection testing utilities.
Tests MySQL database connectivity using configuration settings.
"""
import pymysql
from typing import Dict, Any


def test_mysql_connection(host: str, user: str, password: str, db: str, port: int = 3306) -> Dict[str, Any]:
    """
    Test MySQL database connection with provided credentials.
    
    Args:
        host: Database host
        user: Database username
        password: Database password
        db: Database name
        port: Database port (default: 3306)
    
    Returns:
        Dictionary with connection test results including success status and details
    """
    result = {
        "success": False,
        "message": "",
        "details": {}
    }
    
    connection = None
    try:
        # Attempt to connect to the database
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=db,
            port=port,
            connect_timeout=5  # 5 second timeout
        )
        
        # Get database version and other info
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()[0]
            
            cursor.execute("SELECT USER()")
            current_user = cursor.fetchone()[0]
        
        result["success"] = True
        result["message"] = "Database connection successful!"
        result["details"] = {
            "mysql_version": version,
            "connected_database": current_db,
            "connected_user": current_user,
            "host": host,
            "port": port
        }
        
    except pymysql.MySQLError as e:
        result["success"] = False
        result["message"] = f"MySQL Error: {str(e)}"
        result["details"] = {
            "error_code": e.args[0] if e.args else None,
            "error_message": str(e),
            "host": host,
            "port": port,
            "user": user,
            "database": db
        }
    except Exception as e:
        result["success"] = False
        result["message"] = f"Connection Error: {str(e)}"
        result["details"] = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "host": host,
            "port": port
        }
    finally:
        if connection:
            connection.close()
    
    return result


def test_database_from_config(config: Dict[str, str]) -> Dict[str, Any]:
    """
    Test database connection using configuration dictionary.
    
    Args:
        config: Dictionary containing database configuration (host, user, password, db)
    
    Returns:
        Dictionary with connection test results
    """
    try:
        host = config.get("host", "localhost")
        user = config.get("user", "")
        password = config.get("password", "")
        db = config.get("db", "")
        
        # Handle port if specified
        port = 3306
        if "port" in config:
            try:
                port = int(config["port"])
            except (ValueError, TypeError):
                port = 3306
        
        return test_mysql_connection(host, user, password, db, port)
    except Exception as e:
        return {
            "success": False,
            "message": f"Configuration error: {str(e)}",
            "details": {}
        }
