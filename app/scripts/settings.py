"""Settings module - used to import the configuration settings from the
environment variables"""

import os

"""DQ ACL file ingest"""
PROCESS_INTERVAL     = int(os.environ.get('PROCESS_INTERVAL', 60))
ACL_SERVER           = os.environ.get('ACL_SERVER')
ACL_USERNAME         = os.environ.get('ACL_USERNAME')
ACL_PASSWORD         = os.environ.get('ACL_PASSWORD')
ACL_LANDING_DIR      = os.environ.get('ACL_LANDING_DIR')
S3_BUCKET_NAME       = os.environ.get('S3_BUCKET_NAME')
S3_KEY_PREFIX        = os.environ.get('S3_KEY_PREFIX')
S3_ACCESS_KEY_ID     = os.environ.get('S3_ACCESS_KEY_ID')
S3_SECRET_ACCESS_KEY = os.environ.get('S3_SECRET_ACCESS_KEY')
CLAMAV_URL           = os.environ.get('CLAMAV_URL')
CLAMAV_PORT          = os.environ.get('CLAMAV_PORT')
ACL_RDS_HOST         = os.environ.get('ACL_RDS_HOST')
ACL_RDS_DATABASE     = os.environ.get('ACL_RDS_DATABASE')
ACL_RDS_USERNAME     = os.environ.get('ACL_RDS_USERNAME')
ACL_RDS_PASSWORD     = os.environ.get('ACL_RDS_PASSWORD')
ACL_RDS_TABLE        = os.environ.get('ACL_RDS_TABLE')
