USE my_app_db;

-- Create the table (if not exists)
CREATE TABLE IF NOT EXISTS user_jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    job_status ENUM('submitted', 'processing', 'completed', 'failed', 'cancelled') DEFAULT 'submitted',
    job_size BIGINT,
    file_name VARCHAR(255),
    token VARCHAR(10) UNIQUE NOT NULL,
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

