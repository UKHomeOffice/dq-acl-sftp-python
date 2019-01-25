#!/usr/bin/python
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
import argparse
import logging
import ftputil
import boto3
import requests
import psycopg2
from psycopg2 import sql


FTP_SERVER           = os.environ['ACL_SERVER']
FTP_USERNAME         = os.environ['ACL_USERNAME']
FTP_PASSWORD         = os.environ['ACL_PASSWORD']
FTP_LANDING_DIR      = os.environ['ACL_LANDING_DIR']
DOWNLOAD_DIR         = '/ADT/data/acl'
STAGING_DIR          = '/ADT/stage/acl'
QUARANTINE_DIR       = '/ADT/quarantine/acl'
BUCKET_NAME          = os.environ['S3_BUCKET_NAME']
BUCKET_KEY_PREFIX    = os.environ['S3_KEY_PREFIX']
S3_ACCESS_KEY_ID     = os.environ['S3_ACCESS_KEY_ID']
S3_SECRET_ACCESS_KEY = os.environ['S3_SECRET_ACCESS_KEY']
S3_REGION_NAME       = os.environ['S3_REGION_NAME']
BASE_URL             = os.environ['CLAMAV_URL']
BASE_PORT            = os.environ['CLAMAV_PORT']
RDS_HOST             = os.environ['ACL_RDS_HOST']
RDS_DATABASE         = os.environ['ACL_RDS_DATABASE']
RDS_USERNAME         = os.environ['ACL_RDS_USERNAME']
RDS_PASSWORD         = os.environ['ACL_RDS_PASSWORD']
RDS_TABLE            = os.environ['ACL_RDS_TABLE']

# Setup RDS connection

CONN = psycopg2.connect(host=RDS_HOST, dbname=RDS_DATABASE, user=RDS_USERNAME, password=RDS_PASSWORD)
CUR = CONN.cursor()

def run_virus_scan(filename):
    """
    Send a file to scanner API
    """
    logger = logging.getLogger()
    logger.info("Virus Scanning %s folder", filename)
    # do quarantine move using via the virus scanner
    file_list = os.listdir(filename)
    for scan_file in file_list:
        processing = os.path.join(STAGING_DIR, scan_file)
        with open(processing, 'rb') as scan:
            response = requests.post('http://' + BASE_URL + ':' + BASE_PORT + '/scan', files={'file': scan}, data={'name': scan_file})
            if not 'Everything ok : true' in response.text:
                logger.error('File %s is dangerous, preventing upload', scan_file)
                file_quarantine = os.path.join(QUARANTINE_DIR, scan_file)
                logger.info('Move %s from staging to quarantine %s', processing, file_quarantine)
                os.rename(processing, file_quarantine)
                return False
            else:
                logger.info('Virus scan OK')
    return True

def rds_insert(table, filename):
    """
    Insert into table
    """
    logger = logging.getLogger()
    try:
        CUR.execute(sql.SQL("INSERT INTO {} values (%s)").format(sql.Identifier(table)), (filename,))
        CONN.commit()
    except Exception:
        logger.exception('INSERT ERROR')

def rds_query(table, filename):
    """
    Query table
    """
    logger = logging.getLogger()
    try:
        CUR.execute(sql.SQL("SELECT * FROM {} WHERE filename = (%s)").format(sql.Identifier(table)), (filename,))
        CONN.commit()
    except Exception:
        logger.exception('QUERY ERROR')
    if CUR.fetchone():
        return 1
    else:
        return 0

def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser(description='ACL FTP Downloader')
    parser.add_argument('-D', '--DEBUG', default=False, action='store_true', help='Debug mode logging')
    args = parser.parse_args()
    if args.DEBUG:
        logging.basicConfig(
            filename='/ADT/log/ftp_acl.log',
            format="%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s",
            datefmt='%Y-%m-%d %H:%M:%S',
            level=logging.DEBUG
        )
    else:
        logging.basicConfig(
            filename='/ADT/log/ftp_acl.log',
            format="%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s",
            datefmt='%Y-%m-%d %H:%M:%S',
            level=logging.INFO
        )

    logger = logging.getLogger()
    logger.info("Starting")

    os.chdir('/ADT/scripts')
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    if not os.path.exists(STAGING_DIR):
        os.makedirs(STAGING_DIR)
    if not os.path.exists(QUARANTINE_DIR):
        os.makedirs(QUARANTINE_DIR)

    downloadcount = 0
    uploadcount = 0

# Connect and GET files
    logger.info("Connecting via FTP")
    with ftputil.FTPHost(FTP_SERVER, FTP_USERNAME, FTP_PASSWORD) as ftp_host:
        logger.info("Connected")
        try:
            ftp_host.chdir(FTP_LANDING_DIR)
            files = ftp_host.listdir(ftp_host.curdir)
            for file_csv in files:
                match = re.search('^(.*?)homeofficeroll(\d+)_(\d{4}\d{2}\d{2})\.csv$', file_csv, re.I)
                download = False
                if match is not None:
                    try:
                        result = rds_query(RDS_TABLE, file_csv)
                    except Exception:
                        logger.exception("Error running SQL query")
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
                        ftp_host.download(file_csv, file_csv_staging) # remote, local (staging)
                        logger.info("Downloaded %s", file_csv)
                    else:
                        logger.error("Could not download %s from FTP", file_csv)
                        continue

        except Exception:
            logger.exception("Failure")

# Run virus scan
        if run_virus_scan(STAGING_DIR):
            for obj in os.listdir(STAGING_DIR):
                scanner = rds_query(RDS_TABLE, obj)
                if scanner == 1:
                    file_download = os.path.join(DOWNLOAD_DIR, obj)
                    file_staging = os.path.join(STAGING_DIR, obj)
                    logger.info("Move %s from staging to download %s", file_staging, file_download)
                    os.rename(file_staging, file_download)
                    file_done_download = file_download + '.done'
                    open(file_done_download, 'w').close()
                    downloadcount += 1
                else:
                    logger.error("Could not run virus scan on %s", obj)
                    break
        logger.info("Downloaded %s files", downloadcount)

# Move files to S3
        logger.info("Starting to move files to S3")
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
                logger.info("Copying %s to S3", filename)
                if os.path.isfile(full_filepath):
                    s3_conn.upload_file(full_filepath, BUCKET_NAME, BUCKET_KEY_PREFIX + "/" + filename)
                    os.remove(full_filepath)
                    logger.info("Deleting local file: %s", filename)
                    uploadcount += 1
                else:
                    logger.error("Failed to upload %s", filename)

        logger.info("Uploaded %s files", uploadcount)

# end def main

if __name__ == '__main__':
    main()
