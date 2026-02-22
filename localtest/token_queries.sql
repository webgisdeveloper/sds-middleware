-- Quick Reference: Download Token SQL Queries
-- Use these for manual token management and debugging

-- ============================================================
-- TOKEN STATUS CHECKS
-- ============================================================

-- View all active tokens
SELECT 
    t.token_id,
    t.token,
    t.job_id,
    j.file_name,
    j.user_email,
    t.status,
    t.download_count,
    t.max_downloads,
    t.created_time,
    t.expires_at,
    TIMESTAMPDIFF(HOUR, NOW(), t.expires_at) AS hours_until_expiry,
    t.last_download_time,
    t.last_download_ip
FROM download_tokens t
JOIN user_jobs j ON t.job_id = j.job_id
WHERE t.status = 'active'
ORDER BY t.created_time DESC;

-- View tokens that should be expired (but status hasn't been updated)
SELECT 
    token_id,
    token,
    job_id,
    status,
    download_count,
    max_downloads,
    expires_at,
    CASE 
        WHEN expires_at < NOW() THEN 'Time expired'
        WHEN download_count >= max_downloads THEN 'Max downloads reached'
    END AS expiry_reason
FROM download_tokens
WHERE status = 'active'
AND (expires_at < NOW() OR download_count >= max_downloads);

-- View token statistics by status
SELECT 
    status,
    COUNT(*) AS count,
    AVG(download_count) AS avg_downloads,
    MIN(created_time) AS oldest_token,
    MAX(created_time) AS newest_token
FROM download_tokens
GROUP BY status;

-- ============================================================
-- TOKEN OPERATIONS
-- ============================================================

-- Mark specific token as expired
UPDATE download_tokens
SET status = 'expired'
WHERE token = 'YOUR_TOKEN_HERE';

-- Mark specific token as disabled
UPDATE download_tokens
SET status = 'disabled'
WHERE token = 'YOUR_TOKEN_HERE';

-- Reactivate a disabled token (if not expired)
UPDATE download_tokens
SET status = 'active'
WHERE token = 'YOUR_TOKEN_HERE'
AND expires_at > NOW()
AND download_count < max_downloads;

-- Batch mark all expired tokens
UPDATE download_tokens
SET status = 'expired'
WHERE status = 'active' 
AND (expires_at < NOW() OR download_count >= max_downloads);

-- Reset download count for a token (for testing)
UPDATE download_tokens
SET download_count = 0,
    last_download_time = NULL,
    last_download_ip = NULL
WHERE token = 'YOUR_TOKEN_HERE';

-- ============================================================
-- JOB-SPECIFIC TOKEN QUERIES
-- ============================================================

-- View all tokens for a specific job
SELECT 
    token_id,
    token,
    status,
    download_count,
    max_downloads,
    created_time,
    expires_at,
    last_download_time
FROM download_tokens
WHERE job_id = 123
ORDER BY created_time DESC;

-- Count tokens per job
SELECT 
    j.job_id,
    j.file_name,
    j.user_email,
    j.job_status,
    COUNT(t.token_id) AS token_count,
    SUM(CASE WHEN t.status = 'active' THEN 1 ELSE 0 END) AS active_tokens,
    SUM(t.download_count) AS total_downloads
FROM user_jobs j
LEFT JOIN download_tokens t ON j.job_id = t.job_id
GROUP BY j.job_id, j.file_name, j.user_email, j.job_status
HAVING token_count > 0
ORDER BY total_downloads DESC;

-- Find jobs with completed status but no tokens
SELECT 
    job_id,
    file_name,
    user_email,
    job_status,
    created_time
FROM user_jobs
WHERE job_status = 'completed'
AND job_id NOT IN (SELECT DISTINCT job_id FROM download_tokens)
ORDER BY created_time DESC;

-- ============================================================
-- CLEANUP OPERATIONS
-- ============================================================

-- Delete expired tokens older than 30 days
DELETE FROM download_tokens
WHERE status = 'expired'
AND created_time < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- Delete all tokens for cancelled/failed jobs
DELETE FROM download_tokens
WHERE job_id IN (
    SELECT job_id FROM user_jobs 
    WHERE job_status IN ('cancelled', 'failed')
);

-- Archive old tokens (move to history table - create table first)
-- CREATE TABLE download_tokens_history LIKE download_tokens;
INSERT INTO download_tokens_history
SELECT * FROM download_tokens
WHERE created_time < DATE_SUB(NOW(), INTERVAL 90 DAY);

-- Then delete archived tokens
DELETE FROM download_tokens
WHERE created_time < DATE_SUB(NOW(), INTERVAL 90 DAY);

-- ============================================================
-- MONITORING & ANALYTICS
-- ============================================================

-- Download activity by day (last 30 days)
SELECT 
    DATE(last_download_time) AS download_date,
    COUNT(*) AS download_count,
    COUNT(DISTINCT job_id) AS unique_jobs,
    COUNT(DISTINCT last_download_ip) AS unique_ips
FROM download_tokens
WHERE last_download_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(last_download_time)
ORDER BY download_date DESC;

-- Most downloaded files
SELECT 
    j.file_name,
    COUNT(DISTINCT t.token_id) AS token_count,
    SUM(t.download_count) AS total_downloads,
    MAX(t.last_download_time) AS last_download
FROM user_jobs j
JOIN download_tokens t ON j.job_id = t.job_id
GROUP BY j.file_name
ORDER BY total_downloads DESC
LIMIT 10;

-- Top downloading IPs
SELECT 
    last_download_ip,
    COUNT(*) AS download_count,
    COUNT(DISTINCT job_id) AS unique_jobs,
    MIN(last_download_time) AS first_download,
    MAX(last_download_time) AS last_download
FROM download_tokens
WHERE last_download_ip IS NOT NULL
GROUP BY last_download_ip
ORDER BY download_count DESC
LIMIT 20;

-- Token usage efficiency (how many downloads per token)
SELECT 
    download_count,
    COUNT(*) AS token_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM download_tokens), 2) AS percentage
FROM download_tokens
GROUP BY download_count
ORDER BY download_count;

-- Tokens expiring soon (next 24 hours)
SELECT 
    t.token,
    t.job_id,
    j.file_name,
    j.user_email,
    t.download_count,
    t.max_downloads,
    t.expires_at,
    TIMESTAMPDIFF(HOUR, NOW(), t.expires_at) AS hours_remaining
FROM download_tokens t
JOIN user_jobs j ON t.job_id = j.job_id
WHERE t.status = 'active'
AND t.expires_at BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 24 HOUR)
ORDER BY t.expires_at;

-- ============================================================
-- TESTING & DEBUGGING
-- ============================================================

-- Create a test token for a completed job
INSERT INTO download_tokens (token, job_id, status, download_count, max_downloads, created_time, expires_at)
SELECT 
    SUBSTRING(MD5(CONCAT(job_id, RAND())), 1, 32) AS token,
    job_id,
    'active' AS status,
    0 AS download_count,
    3 AS max_downloads,
    NOW() AS created_time,
    DATE_ADD(NOW(), INTERVAL 24 HOUR) AS expires_at
FROM user_jobs
WHERE job_status = 'completed'
LIMIT 1;

-- Simulate a download for testing
UPDATE download_tokens
SET download_count = download_count + 1,
    last_download_time = NOW(),
    last_download_ip = '192.168.1.100'
WHERE token = 'YOUR_TOKEN_HERE';

-- View token with job details
SELECT 
    t.*,
    j.user_email,
    j.file_name,
    j.job_status,
    j.job_size,
    j.download_url
FROM download_tokens t
JOIN user_jobs j ON t.job_id = j.job_id
WHERE t.token = 'YOUR_TOKEN_HERE';

-- ============================================================
-- MAINTENANCE PROCEDURES
-- ============================================================

-- Complete maintenance routine (run daily)
-- Step 1: Mark expired tokens
UPDATE download_tokens
SET status = 'expired'
WHERE status = 'active'
AND (expires_at < NOW() OR download_count >= max_downloads);

-- Step 2: Clean up old expired tokens (optional - older than 30 days)
DELETE FROM download_tokens
WHERE status = 'expired'
AND created_time < DATE_SUB(NOW(), INTERVAL 30 DAY);

-- Step 3: Generate report
SELECT 
    'Active Tokens' AS category,
    COUNT(*) AS count
FROM download_tokens
WHERE status = 'active'
UNION ALL
SELECT 
    'Expired Tokens' AS category,
    COUNT(*) AS count
FROM download_tokens
WHERE status = 'expired'
UNION ALL
SELECT 
    'Disabled Tokens' AS category,
    COUNT(*) AS count
FROM download_tokens
WHERE status = 'disabled'
UNION ALL
SELECT 
    'Tokens Expiring Today' AS category,
    COUNT(*) AS count
FROM download_tokens
WHERE status = 'active'
AND DATE(expires_at) = CURDATE();
