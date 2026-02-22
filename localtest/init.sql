USE my_app_db;

-- Create the table (if not exists)
CREATE TABLE IF NOT EXISTS user_jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    job_status ENUM('submitted', 'processing', 'completed', 'failed', 'cancelled') DEFAULT 'submitted',
    job_size BIGINT,
    file_name VARCHAR(255),
    token VARCHAR(10) UNIQUE,
    download_url TEXT,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Seed 10 random entries
INSERT INTO user_jobs (user_email, job_status, job_size, file_name, token, download_url, created_time)
SELECT 
    CONCAT('user', FLOOR(RAND() * 100), '@example.com'),
    ELT(FLOOR(1 + (RAND() * 5)), 'submitted', 'processing', 'completed', 'failed', 'cancelled'),
    FLOOR(100000 + (RAND() * 9000000)), -- Random size between 100KB and 9MB
    ELT(FLOOR(1 + (RAND() * 20)), 
        '2007HendricksCo_Metadata.zip', '2008AllenCoOrthophotography_Metadata.zip', 
        '20162020_StatewideElevation_Metadata.zip', '2016_StatewideElevation_Metadata.zip', 
        '2017_StatewideElevation_Metadata.zip', '2018_StatewideElevation_Metadata.zip', 
        '2019_StatewideElevation_Metadata.zip', '2020_StatewideElevation_Metadata.zip', 
        'BigOaks2003_Metadata.zip', 'BradfordWoods2002_Metadata.zip', 
        'CampAtterbury2010_Metadata.zip', 'CityOfBloomingtonHistoricalPhotos_Metadata.zip', 
        'DearbornCounty2005_metadata.zip', 'DearbornCountyContours2005_Metadata.zip', 
        'HistoricalWayneCounty_Metadata.zip', 'IMPOOrthos2007_Metadata.zip', 
        'in_2011_GibsonPosey_metadata.zip', 'IN_daviess_cty_2009_ortho_metadata.zip', 
        'IN_dearborn_county_2008orthos_metadata.zip', 'IndianaDunes2005_Metadata.zip'
    ),
    SUBSTRING(MD5(RAND()), 1, 10),
    CONCAT('https://storage.googleapis.com/download/', FLOOR(RAND() * 1000)),
    TIMESTAMP(DATE_SUB(NOW(), INTERVAL FLOOR(RAND() * 30) DAY) + INTERVAL FLOOR(RAND() * 86400) SECOND)
FROM 
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 
     UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) AS temp
LIMIT 10;

-- Create download_tokens table for managing secure file downloads
CREATE TABLE IF NOT EXISTS download_tokens (
    token_id INT AUTO_INCREMENT PRIMARY KEY,
    token VARCHAR(64) UNIQUE NOT NULL,
    job_id INT NOT NULL,
    status ENUM('active', 'disabled', 'expired') DEFAULT 'active',
    download_count INT DEFAULT 0,
    max_downloads INT DEFAULT 3,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_download_time TIMESTAMP NULL,
    last_download_ip VARCHAR(45) NULL,
    FOREIGN KEY (job_id) REFERENCES user_jobs(job_id) ON DELETE CASCADE,
    INDEX idx_token (token),
    INDEX idx_job_id (job_id),
    INDEX idx_status (status),
    INDEX idx_expires_at (expires_at)
) COMMENT='Table for managing download tokens with expiration and usage limits';

-- Seed download tokens (create tokens for completed jobs)
INSERT INTO download_tokens (token, job_id, status, download_count, created_time, expires_at, last_download_time, last_download_ip)
SELECT 
    SUBSTRING(MD5(CONCAT(job_id, RAND())), 1, 32) AS token,
    job_id,
    CASE 
        WHEN RAND() < 0.1 THEN 'disabled'
        WHEN RAND() < 0.3 THEN 'expired'
        ELSE 'active'
    END AS status,
    FLOOR(RAND() * 5) AS download_count,
    created_time AS created_time,
    TIMESTAMP(created_time + INTERVAL 24 HOUR) AS expires_at,
    CASE 
        WHEN RAND() < 0.6 THEN TIMESTAMP(created_time + INTERVAL FLOOR(RAND() * 20) HOUR)
        ELSE NULL
    END AS last_download_time,
    CASE 
        WHEN RAND() < 0.6 THEN CONCAT(
            FLOOR(1 + RAND() * 254), '.', 
            FLOOR(1 + RAND() * 254), '.', 
            FLOOR(1 + RAND() * 254), '.', 
            FLOOR(1 + RAND() * 254)
        )
        ELSE NULL
    END AS last_download_ip
FROM user_jobs
WHERE job_status = 'completed'
LIMIT 10;

