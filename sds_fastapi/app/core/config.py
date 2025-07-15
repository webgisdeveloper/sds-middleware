import configparser
import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebServerSettings(BaseSettings):
    url_base_path: str = "/"
    debug_level: str = "DEBUG"
    port: int = 8080
    env: str = "dev"
    use_ssl: str = "on"
    cert_file: str = "</path/to/fullchain.pem>"
    key_file: str = "</path/to/privkey.pem>"
    ssl_hostname: str = "<hostname>"
    client_secret: str = "<your-client-secret-here>"


class SdsSyncSettings(BaseSettings):
    hsi_bin_path: str = "</path/to/hpss/bin/hsi>"
    hsi_keytab_path: str = "</path/to/xxx.keytab>"
    hsi_user: str = "<hsi username>"
    firewall_flag: str = "on"
    timeout_in_secs: int = 3300


class SdsAsyncSettings(BaseSettings):
    message_broker_host: str = "localhost"
    message_broker_port: int = 5672
    work_queue: str = "isdp_task_queue"
    same_job_minimum_interval_in_min: int = 360
    black_list: str = "</path/to/black_list.txt>"


class WorkerSettings(BaseSettings):
    staging_dir: str = "/var/www/html/staging"
    smtp_server: str = "localhost"
    email_sender: str = "noreply.sds@iu.edu"
    contact_email: str = "rdsadmin@iu.edu"
    http_download_server: str = "https://<hostname>/staging"
    staging_usage_threshold_in_gb: int = 950


class DatabaseSettings(BaseSettings):
    host: str = "<db_host>"
    user: str = "<db_username>"
    password: str = "<db_password>"
    db: str = "<db_name>"
    job_table: str = "userjobs"


class LoggingSettings(BaseSettings):
    api_log_file: str = "</path/to/api.log>"
    worker_log_file: str = "</path/to/worker.log>"


class Settings(BaseSettings):
    webserver: WebServerSettings
    sds_sync: SdsSyncSettings
    sds_async: SdsAsyncSettings
    worker: WorkerSettings
    database: DatabaseSettings
    logging: LoggingSettings

    @classmethod
    def from_config_file(cls, config_file: str = "sds.cfg"):
        config = configparser.ConfigParser()
        current_file = Path(__file__).resolve()
        current_dir = current_file.parent
        config_file_path = current_dir / config_file
        with open(config_file_path) as fh:
            config.read_file(fh)            
        return cls(
            webserver=WebServerSettings(**dict(config['webserver'])),
            sds_sync=SdsSyncSettings(**dict(config['sds_sync'])),
            sds_async=SdsAsyncSettings(**dict(config['sds_async'])),
            worker=WorkerSettings(**dict(config['worker'])),
            database=DatabaseSettings(**dict(config['database'])),
            logging=LoggingSettings(**dict(config['logging']))
        )


# Create global settings instance
settings = Settings.from_config_file()
