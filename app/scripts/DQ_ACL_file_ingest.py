#!/usr/bin/python3
"""
# FTP ACL Script
# Version 2

# Copy files from FTP to local drive
# Scan them using ClamAV
# Upload to S3
# Remove from local drive
"""
import re
import os
import sys
import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
import json
import urllib.request
import boto3
import requests
import psycopg2
from psycopg2 import sql
import ftputil
from requests.packages.urllib3.exceptions import InsecureRequestWarning


FTP_SERVER                     = os.environ['ACL_SERVER']
FTP_USERNAME                   = os.environ['ACL_USERNAME']
FTP_PASSWORD                   = os.environ['ACL_PASSWORD']
FTP_LANDING_DIR                = os.environ['ACL_LANDING_DIR']
DOWNLOAD_DIR                   = '/ADT/data/acl'
STAGING_DIR                    = '/ADT/stage/acl'
QUARANTINE_DIR                 = '/ADT/quarantine/acl'
SCRIPT_DIR                     = '/ADT/scripts'
LOG_FILE                       = '/ADT/log/DQ_FTP_ACL.log'
BUCKET_NAME                    = os.environ['S3_BUCKET_NAME']
S3_ACCESS_KEY_ID               = os.environ['S3_ACCESS_KEY_ID']
S3_SECRET_ACCESS_KEY           = os.environ['S3_SECRET_ACCESS_KEY']
S3_REGION_NAME                 = os.environ['S3_REGION_NAME']
BASE_URL                       = os.environ['CLAMAV_URL']
BASE_PORT                      = os.environ['CLAMAV_PORT']
RDS_HOST                       = os.environ['ACL_RDS_HOST']
RDS_DATABASE                   = os.environ['ACL_RDS_DATABASE']
RDS_USERNAME                   = os.environ['ACL_RDS_USERNAME']
RDS_PASSWORD                   = os.environ['ACL_RDS_PASSWORD']
RDS_TABLE                      = os.environ['ACL_RDS_TABLE']
SLACK_WEBHOOK                  = os.environ['SLACK_WEBHOOK']

# Setup RDS connection

CONN = psycopg2.connect(host=RDS_HOST,
                        dbname=RDS_DATABASE,
                        user=RDS_USERNAME,
                        password=RDS_PASSWORD)
CUR = CONN.cursor()

def run_virus_scan(filename):
    """
    Send a file to scanner API
    """
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    logger = logging.getLogger()
    logger.info("Virus Scanning %s folder", filename)
    file_list = os.listdir(filename)
    for scan_file in file_list:
        processing = os.path.join(STAGING_DIR, scan_file)
        with open(processing, 'rb') as scan:
            response = requests.post('https://' + BASE_URL + ':' + BASE_PORT + '/scan', files={'file': scan}, data={'name': scan_file}, verify=False)
            if not 'Everything ok : true' in response.text:
                logger.warning("Virus scan FAIL: %s is dangerous!", scan_file)
                warning = ("Virus scan FAIL: " + scan_file + " is dangerous!")
                send_message_to_slack(str(warning))
                file_quarantine = os.path.join(QUARANTINE_DIR, scan_file)
                logger.warning("Move %s from staging to quarantine %s", processing, file_quarantine)
                os.rename(processing, file_quarantine)
                continue
            else:
                logger.info("Virus scan OK: %s", scan_file)
    return True

def rds_insert(table, filename):
    """
    Insert into table
    """
    logger = logging.getLogger()
    try:
        CUR.execute(sql.SQL("INSERT INTO {} values (%s)").format(sql.Identifier(table)), (filename,))
        CONN.commit()
    except Exception as err:
        logger.error("INSERT ERROR")
        logger.exception(str(err))
        error = str(err)
        send_message_to_slack(error)
        sys.exit(1)

def rds_query(table, filename):
    """
    Query table
    """
    logger = logging.getLogger()
    try:
        CUR.execute(sql.SQL("SELECT * FROM {} WHERE filename = (%s)").format(sql.Identifier(table)), (filename,))
        CONN.commit()
    except Exception as err:
        logger.error("QUERY ERROR")
        logger.exception(str(err))
        error = str(err)
        send_message_to_slack(error)
        sys.exit(1)
    if CUR.fetchone():
        return 1
    else:
        return 0

def send_message_to_slack(text):
    """
    Formats the text and posts to a specific Slack web app's URL
    Returns:
        Slack API repsonse
    """
    logger = logging.getLogger()
    try:
        post = {
            "text": ":fire: :sad_parrot: An error has occured in the *ACL* pod :sad_parrot: :fire:",
            "attachments": [
                {
                    "text": "{0}".format(text),
                    "color": "#B22222",
                    "attachment_type": "default",
                    "fields": [
                        {
                            "title": "Priority",
                            "value": "High",
                            "short": "false"
                        }
                    ],
                    "footer": "Kubernetes API",
                    "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png"
                }
            ]
            }
        json_data = json.dumps(post)
        req = urllib.request.Request(url=SLACK_WEBHOOK,
                                     data=json_data.encode('utf-8'),
                                     headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req)
        return resp

    except Exception as err:
        logger.error(
            'The following error has occurred on line: %s',
            sys.exc_info()[2].tb_lineno)
        logger.error(str(err))
        sys.exit(1)


def main():
    """
    Main function
    """
# Setup logging and global variables
    logformat = '%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s'
    form = logging.Formatter(logformat)
    logging.basicConfig(
        format=logformat,
        level=logging.INFO
    )
    logger = logging.getLogger()
    if logger.hasHandlers():
        logger.handlers.clear()
    loghandler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7)
    loghandler.suffix = "%Y-%m-%d"
    loghandler.setFormatter(form)
    logger.addHandler(loghandler)
    consolehandler = logging.StreamHandler()
    consolehandler.setFormatter(form)
    logger.addHandler(consolehandler)
    logger.info("Starting")

    os.chdir(SCRIPT_DIR)
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    if not os.path.exists(STAGING_DIR):
        os.makedirs(STAGING_DIR)
    if not os.path.exists(QUARANTINE_DIR):
        os.makedirs(QUARANTINE_DIR)

    downloadcount = 0
    uploadcount = 0

# Connect and GET files from FTP
    logger.info("Connecting via FTP")
    try:
        with ftputil.FTPHost(FTP_SERVER, FTP_USERNAME, FTP_PASSWORD) as ftp_host:
            logger.info("Connected")
            try:
                ftp_host.chdir(FTP_LANDING_DIR)
                files = ftp_host.listdir(ftp_host.curdir)
                for file_csv in files:
                    match = re.search(r'^(.*?)homeofficeroll(\d+)_(\d{4}\d{2}\d{2})\.csv$', file_csv, re.IGNORECASE)
                    download = False
                    if match is not None:
                        try:
                            result = rds_query(RDS_TABLE, file_csv)
                        except Exception as err:
                            logger.error("Error running SQL query")
                            logger.exception(str(err))
                            error = str(err)
                            send_message_to_slack(error)
                            sys.exit(1)
                        if result == 0:
                            download = True
                            logger.info("File %s downloaded", file_csv)
                            rds_insert(RDS_TABLE, file_csv)
                            logger.info("File %s added to RDS", file_csv)
                        else:
                            logger.debug("Skipping %s", file_csv)
                            continue

                        file_csv_staging = os.path.join(STAGING_DIR, file_csv)

    # Protection against redownload
                        if os.path.isfile(file_csv_staging) and os.path.getsize(file_csv_staging) > 0 and os.path.getsize(file_csv_staging) == ftp_host.stat(file_csv).st_size:
                            download = False
                            validate = rds_query(RDS_TABLE, file_csv)
                            if validate == 1:
                                logger.info("File %s exist - skipping...", file_csv)
                        if download:
                            logger.info("Downloading %s to %s", file_csv, file_csv_staging)
                            ftp_host.download(file_csv, file_csv_staging)
                            logger.info("Downloaded %s", file_csv)
                        else:
                            logger.error("Could not download %s from FTP", file_csv)
                            continue

            except Exception as err:
                logger.error("Failure getting files from FTP")
                logger.exception(str(err))
                error = str(err)
                send_message_to_slack(error)
                sys.exit(1)

    except Exception as err:
        logger.error("Could not connect to FTP")
        logger.exception(str(err))
        error = str(err)
        send_message_to_slack(error)
        sys.exit(1)


# Run virus scan
    if run_virus_scan(STAGING_DIR):
        for obj in os.listdir(STAGING_DIR):
            scanner = rds_query(RDS_TABLE, obj)
            if scanner == 1:
                file_download = os.path.join(DOWNLOAD_DIR, obj)
                file_staging = os.path.join(STAGING_DIR, obj)
                logger.info("Move %s from staging to download %s", file_staging, file_download)
                os.rename(file_staging, file_download)
                downloadcount += 1
            else:
                logger.error("Could not run virus scan on %s", obj)
                break
        logger.info("Downloaded %s files", downloadcount)

# Move files to S3
    processed_acl_file_list = [filename for filename in os.listdir(DOWNLOAD_DIR)]
    boto_s3_session = boto3.Session(
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        region_name=S3_REGION_NAME
    )
    if processed_acl_file_list:
        for filename in processed_acl_file_list:
            s3_conn = boto_s3_session.client("s3")
            full_filepath = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(full_filepath):
                try:
                    time = datetime.datetime.now()
                    bucket_key_prefix = time.strftime("%Y-%m-%d/%H:%M:%S.%f")
                    logger.info("Copying %s to S3", filename)
                    s3_conn.upload_file(full_filepath, BUCKET_NAME,
                                        bucket_key_prefix + "/" + filename)
                    uploadcount += 1
                except Exception as err:
                    logger.error(
                        "Failed to upload %s, exiting...", filename)
                    logger.exception(str(err))
                    error = str(err)
                    send_message_to_slack(error)
                    sys.exit(1)
        logger.info("Uploaded %s files to %s", uploadcount, BUCKET_NAME)

# Cleaning up
    for filename in processed_acl_file_list:
        try:
            full_filepath = os.path.join(DOWNLOAD_DIR, filename)
            os.remove(full_filepath)
            logger.info("Cleaning up local file %s", filename)
        except Exception:
            logger.error("Failed to delete file %s", filename)
            logger.exception(str(err))
            error = str(err)
            send_message_to_slack(error)
            sys.exit(1)

# Closing SFTP connection
    ftp_host.close()
    logger.info("Connection closed")

if __name__ == '__main__':
    main()
