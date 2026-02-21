docker exec -it $(docker ps -qf "name=db") mysql -u dbtester -psupersecret my_app_db -e "SELECT job_id, user_email, job_status, file_name FROM user_jobs;"

