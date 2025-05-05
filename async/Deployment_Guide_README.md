# Deployment Overview

Our SDS instances are hosted on Intelligent Infrastructure (II) VMs and run under an unprivileged user account. To set up a new SDS instance, we collaborate with the RCS team to configure the required components on an II VM.

## Components to Be Set Up by the RCS Team

### 1. **Apache httpd**
Apache httpd serves as the download server for hosting collections pulled from SDA for users to download. Typically, httpd's download location is configured at:

```plaintext
/var/www/html/staging
```

### 2. **RabbitMQ**

RabbitMQ acts as the messaging queue for communication between the API server and workers.

##### Verification
After RabbitMQ installation, the RCS team is advised to verify that RabbitMQ is running properly and listening on the intended interfaces using the following command:

```bash
sudo rabbitmq-diagnostics listeners
```

##### Expected Output:

```plaintext
Interface: [::], port: 15672, protocol: http, purpose: HTTP API
Interface: [::], port: 25672, protocol: clustering, purpose: inter-node and CLI tool communication
Interface: [::], port: 5672, protocol: amqp, purpose: AMQP 0-9-1 and AMQP 1.0
```

##### Debugging Access
For debugging and troubleshooting, RCS team grants sudo access to the `rabbitmqctl` command is preferred.


##### Optional: RabbitMQ Admin Web Portal
To enable the RabbitMQ admin web portal, the RCS team should run the following commands. In this example, the admin username is `sdsadmin`. The password should be shared with the RDS team via IU secure data transfer.

```bash
sudo rabbitmqctl add_user sdsadmin <admin_password>
sudo rabbitmqctl set_user_tags sdsadmin administrator
# Enable the management web UI service
sudo rabbitmq-plugins enable rabbitmq_management
```

### 3. **Python**
SDS middleware is written in Python. A recent Python release must be installed to serve as the middleware runtime.

### 4. **Mail SMTP Server**
The SDS middleware relies on `postfix` as the SMTP server to send user notification emails. Ensure `postfix` is installed and properly configured.

### 5. **SSL Certificate**
SSL certificates must be installed to enable TLS for secure data transfer. Certificate and key files should be in pem format.

### 6. **Network-Mounted Filesystem**
SDS collections consume significant storage space. A large NFS (specific size depends on the SDS application) should be mounted on the II VM to host collections pulled from SDA.

##### Symbolic Link
A symbolic link should be created so the NFS can be accessed by `httpd` and SDS workers. For example, if the NFS is mounted under `/volume-mnt-point` and httpd serves at `/var/www/html/staging`, the symbolic link can be created as follows:

```bash
/var/www/html/staging -> /volume-mnt-point/staging/
```

### 7. **Network Ports**
The RCS team must ensure the following network ports are properly configured and accessible:

1. **HTTPD Port (`443`)**:  
   This port is used for secure communication with the HTTP server.

2. **API Server Port**:  
   This corresponds to the `port` parameter specified in the middleware configuration file. In most cases, this is set to `8080`.

After configuring the ports, the RCS team should:

- Conduct a security scan to ensure there are no vulnerabilities.
- Collaborate with the firewall management team to make both ports publicly accessible, both within and outside the IU network.

### Notes
- **System Services:** Both `httpd` and `rabbitmq` should be registered as `systemctl` daemon services to launch automatically on II VM restarts.
- **Postfix Configuration:** Ensure `postfix` is configured to avoid the `[External]` flag in emails sent through it.

## Components to Be Set Up by the SDS Team

### Application-Specific Configuration File

An application-specific configuration file (e.g., `sds.cfg`) must be created to include application and environment-specific settings.  

You can download a template from the following link:  
[SDS Configuration File Template](sds.cfg)

### 1. **HSI Utility**
The SDS team needs to download the OS-specific HSI utility, which SDS workers use to pull data from the IU SDA service. Refer to the [IU SDA Service Documentation](https://servicenow.iu.edu/kb?id=kb_article_view&sysparm_article=KB0024406) for more details. Additionally, see this IU KB article on how to download HSI: [Use HSI to access your SDA account at IU](https://servicenow.iu.edu/kb?id=kb_article_view&sysparm_article=KB0022463).

In your SDS configuration file, set the following `hsi_bin_path` parameter to the specific location where you have HSI installed:

```plaintext
hsi_bin_path=</path/to/your/hsi/binary>
```

### 2. **SDA User Account Keytab File**
For authentication, install the Kerberos Keytab file and configure the following parameters in your SDS configuration file:

```plaintext
hsi_keytab_path=</path/to/keytab/file>
hsi_user=<keytab user name>
```
You can leave the firewall flag enabled and use the default timeout threshold of 3300 seconds:

```plaintext
firewall_flag=on
timeout_in_secs=3300
```

### 3. **Rabbitmq Related Configs**
You can use the following RabbitMQ-related configuration parameters as default settings:

```plaintext
message_broker_host=localhost
message_broker_port=5672
work_queue=task_queue
```

### 4. **Job Request Configuration**
Use `same_job_minimum_interval_in_min` to prevent repeated job requests for the same collection. Additionally, configure the `black_list` parameter to blacklist specific accounts (e.g., bot accounts such as `siscan@iu.edu`).

```plaintext
# Prevent users from submitting the same job multiple times in a short interval
same_job_minimum_interval_in_min=360 
black_list=</path/to/black/list/file>
```

### 5. **Certificate Configuration**
Set the following parameters according to your specific certificate settings. Ensure the `use_ssl` flag is enabled.

```plaintext
use_ssl=on
cert_file=</path/to/certificate/file>
key_file=</path/to/private/key/file>
ssl_hostname=<CBRI II VM hostname>
```

### 6. **Worker Configuration**
Customize the following worker-related settings as necessary. Adjust `staging_usage_threshold_in_gb` based on the size of the mounted NFS drive. Leave `smtp_server` as `localhost`.

```plaintext
staging_dir=/var/www/html/staging
smtp_server=localhost
email_sender=noreply.sds@iu.edu
contact_email=rdsadmin@iu.edu
http_download_server=https://<CBRI II VM hostname>/staging
# Discard jobs when storage level reaches this threshold
staging_usage_threshold_in_gb=950
```

### 7. **Database and Job Table Configuration**
Set database and job table parameters as shown below:

```plaintext
[database]
host=<db hostname>
user=<db username>
password=<db password>
db=<db name>
job_table=userjobs
```

### 8. **Log File Paths**
Configure log file paths using the following parameters:

```plaintext
[logging]
api_log_file=<path/to/api/log>
worker_log_file=<path/to/worker/log>
```

### 8. **Install Python Dependencies**
Install the required Python modules using `pip`:

```bash
pip install mysql-connector-python pandas pika tornado requests
```

### 9. **Pull SDS Code and Maintenance Tool Scripts**
Pull the SDS code from RDS GitHub [SDS Middleware](https://github.com/indiana-university/sds-middleware/tree/master/middleware/async), or copy the existing SDS application code from an II VM as a starting point. Maintenance tool scripts are available in the repository under the `maintenance_tools` folder.


> ⚠️ **Warning**: Maintenance tools can be reused for a new SDS middleware deployment. However, certain paths within the shell scripts may be specific to the II VM environment. Update these environment-specific paths as needed before executing the scripts. For example, you may need to update `SCRIPT_PATH` in `launch_web_screen_session.sh` and `launch_worker_screen_session.sh`.

> ⚠️ **Warning**: Update the API server and worker python code to use the actual configuration file name. Modify the following line in your code as required:

```python
if __name__ == '__main__':

    CONFIG_FILENAME = </path/to/your/config/file>
```

If your configuration file is named `sds.cfg` and placed in the same folder as `async_api_server.py` and `worker.py`, you can skip the code editing step.

**Note:** In [SDS Middleware](https://github.com/indiana-university/sds-middleware/tree/master/middleware/async), the Python filename for the API server is `async_api_server.py`. For existing SDS applications on II VMs, it may be named differently. For example, on `rdsisdp@rds-sds-prod.uits.iu.edu`, where SDS ISDP is deployed, the API server Python file is `async_mrda_isdp_dev.py`.

### 9. **Set Up a Cron Job for the Housekeeping Service**
To automate the cleanup of the staging area, follow these steps:

#### Step 1: Update the `staging_area_clean.sh` Script
Pull the `staging_area_clean.sh` script from this repository under the `house_keeper` folder. Update the script with your specific CBRI II VM configurations. Use the script located at `/home/rdsisdp/workspace/mrda/isdp/async/staging_area_clean.sh` on `rdsisdp@rds-sds-prod.uits.iu.edu` as a reference.

Example snippet to update:

```bash
SCRIPT="<path/to/house_keeper.py>"
DATA_ROOT="<path/to/staging/area>" # Path to the staging area, e.g., "/volume-mnt-point/staging"
TTL_IN_MIN=1440 # Time to live (TTL), set to 1 day
WHITE_LIST="<path/to/white/list/file>" # Path to the whitelist file, e.g., "ISDPmetadatafilenamesforwhitelist.csv"

</path/to/python/binary> $SCRIPT --dataroot $DATA_ROOT --ttl_in_min $TTL_IN_MIN --white_list $WHITE_LIST
```

#### Step 2: Install the Cron Job
To schedule the `staging_area_clean.sh` script to run at regular intervals (e.g., every 10 minutes):

1. Open the crontab editor:
```bash
crontab -e
```

2. Add the following line to the cron table, updating `</path/to/staging_area_clean.sh>` and `</path/to/log/file>` with your specific paths:
```plaintext
*/10 * * * * </path/to/staging_area_clean.sh> >> </path/to/log/file>
```

3. Save and exit the editor. (For `vi` as the default editor, press `:` followed by `x` and hit Enter to save changes and exit.)

Once set up, the housekeeping service will automatically clean the staging area based on the defined TTL and whitelist configurations.

### 10. **Launch Services**

You can use the scripts in the `maintenance_tools` folder to launch API and worker services.

**Note:** For the API server, `async_api_server.py` in [SDS Middleware](https://github.com/indiana-university/sds-middleware/tree/master/middleware/async) listens on `https://<hostname>:<port>/sds?p=<path/to/SDA/archive>&uid=<user_email_addr>`. For existing SDS applications on II VMs, the web API server may listen on a different subpath. For example, on `rdsisdp@rds-sds-prod.uits.iu.edu`, where SDS ISDP is deployed, the API server (`async_mrda_isdp_dev.py`) listens on `https://<hostname>:<port>/isdp?`. You can customize `async_api_server.py` to configure a different listening subpath based on your preference.




