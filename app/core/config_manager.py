"""
Configuration file management utilities.
Handles reading, parsing, and updating the sds.cfg configuration file.
"""
import configparser
import os
from pathlib import Path
from typing import Dict, Any, List
from collections import OrderedDict


def get_config_file_path() -> Path:
    """Get the absolute path to the sds.cfg file."""
    current_file = Path(__file__).resolve()
    current_dir = current_file.parent
    return current_dir / "sds.cfg"


def read_config_file() -> Dict[str, Dict[str, str]]:
    """
    Read and parse the sds.cfg configuration file.
    Returns a dictionary with sections as keys and their settings as nested dictionaries.
    """
    config = configparser.ConfigParser()
    config_path = get_config_file_path()
    
    with open(config_path, 'r') as fh:
        config.read_file(fh)
    
    # Convert to regular dict for JSON serialization
    result = OrderedDict()
    for section in config.sections():
        result[section] = OrderedDict()
        for key, value in config.items(section):
            result[section][key] = value
    
    return dict(result)


def get_config_structure() -> List[Dict[str, Any]]:
    """
    Get the configuration structure with field metadata.
    Returns a list of sections with their fields.
    """
    config_data = read_config_file()
    structure = []
    
    for section_name, section_data in config_data.items():
        section_info = {
            "section": section_name,
            "fields": []
        }
        
        for key, value in section_data.items():
            field_info = {
                "key": key,
                "value": value,
                "type": infer_field_type(value)
            }
            section_info["fields"].append(field_info)
        
        structure.append(section_info)
    
    return structure


def infer_field_type(value: str) -> str:
    """Infer the type of a configuration value."""
    if value.lower() in ['true', 'false', 'on', 'off', 'yes', 'no']:
        return "boolean"
    try:
        int(value)
        return "integer"
    except ValueError:
        pass
    try:
        float(value)
        return "float"
    except ValueError:
        pass
    if "password" in value.lower() or "secret" in value.lower():
        return "password"
    return "string"


def update_config_file(updates: Dict[str, Dict[str, str]]) -> bool:
    """
    Update the sds.cfg configuration file with new values.
    
    Args:
        updates: Dictionary with sections as keys and their updated settings
        
    Returns:
        True if successful, False otherwise
    """
    try:
        config = configparser.ConfigParser()
        config_path = get_config_file_path()
        
        # Read existing configuration
        with open(config_path, 'r') as fh:
            config.read_file(fh)
        
        # Apply updates
        for section, fields in updates.items():
            if not config.has_section(section):
                config.add_section(section)
            
            for key, value in fields.items():
                config.set(section, key, str(value))
        
        # Write back to file
        with open(config_path, 'w') as fh:
            config.write(fh)
        
        return True
    except Exception as e:
        print(f"Error updating config file: {e}")
        return False


def backup_config_file() -> Path:
    """
    Create a backup of the current configuration file.
    Returns the path to the backup file.
    """
    from datetime import datetime
    
    config_path = get_config_file_path()
    backup_dir = config_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"sds.cfg.backup_{timestamp}"
    
    import shutil
    shutil.copy2(config_path, backup_path)
    
    return backup_path


def validate_config_updates(updates: Dict[str, Dict[str, str]]) -> List[str]:
    """
    Validate configuration updates before applying them.
    Returns a list of validation errors (empty if valid).
    """
    errors = []
    config = configparser.ConfigParser()
    config_path = get_config_file_path()
    
    with open(config_path, 'r') as fh:
        config.read_file(fh)
    
    for section, fields in updates.items():
        if not config.has_section(section):
            errors.append(f"Section '{section}' does not exist in configuration")
            continue
        
        for key, value in fields.items():
            if not config.has_option(section, key):
                errors.append(f"Key '{key}' does not exist in section '{section}'")
            
            # Basic type validation
            if key in ['port', 'message_broker_port', 'timeout_in_secs', 
                      'same_job_minimum_interval_in_min', 'staging_usage_threshold_in_gb']:
                try:
                    int(value)
                except ValueError:
                    errors.append(f"'{key}' must be an integer, got '{value}'")
    
    return errors
