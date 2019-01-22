#!/bin/bash

# This script does the following:
# - downloads and runs 3 (three) Docker containers all from public repositories
# - builds a new container from the local repository
# - requests running user to supply values used as variables

set -e

# Set variables

# Used by ftp_server function
echo "********************************************"
echo "Setup ftp-server container variables:"
echo "********************************************"
echo "Enter mountpoint location (full file path) and press [ENTER]: "
read mountpoint

# Used by postgresql function
echo "********************************************"
echo "Setup postgresql container variables:"
echo "********************************************"
echo "Enter postgresdb and press [ENTER]: "
read postgresdb
echo "Enter postgrestable and press [ENTER]: "
read postgrestable
echo "Enter postgresuser and press [ENTER]: "
read postgresuser

# Used by acl function
echo "********************************************"
echo "Setup ACL container variables"
echo "********************************************"
echo "Enter bucketname and press [ENTER]: "
read bucketname
echo "Enter keyprefix and press [ENTER]: "
read keyprefix
echo "Enter awskeyid and press [ENTER]: "
read awskeyid
echo "Enter awssecret and press [ENTER]: "
read awssecret

# Create random password
echo "********************************************"
randompass=$(openssl rand -hex 24)
echo "Random password generated: $randompass"

# Build FTP container

function ftp_server {
  run=$(docker run --rm \
        --name ftp-server \
        -e FTP_USER_NAME='test' \
        -e FTP_USER_PASS=$randompass \
        -e FTP_USER_HOME=/home/test \
        -v $mountpoint:/home/test/test \
        -d -p 2121:21 \
        -p 30000-30009:30000-30009 \
        stilliard/pure-ftpd
        )
        echo "Created container with SHA: $run"
}

# Build ClamAV container

function clamav {
  run=$(docker run --rm \
        --name clamav \
        -d -p 3310:3310 \
        quay.io/ukhomeofficedigital/clamav
        )
        echo "Created container with SHA: $run"
}

# Build ClamAV REST API container

function clamav_api {
  run=$(docker run --rm \
        --name clamav-api \
        -e 'CLAMD_HOST=clamav' \
        -p 8080:8080 \
        --link clamav:clamav \
        -t -i -d lokori/clamav-rest
        )
        echo "Created container with SHA: $run"
}

# Build PostgreSQL container

function postgresql {
  run=$(docker run --rm \
        --name postgresql \
        -e POSTGRES_PASSWORD=$randompass \
        -e POSTGRES_USER=$postgresuser \
        -e POSTGRES_DB=$postgresdb \
        -d postgres
       )
       echo "Created container with SHA: $run"
}

# Build Postgres sidekick

function postgresql_sidekick {
  run=$(docker build \
       -t psql/bash --rm \
       --build-arg ACL_RDS_HOST='postgresql' \
       --build-arg ACL_RDS_DATABASE=$postgresdb \
       --build-arg ACL_RDS_USERNAME=$postgresuser \
       --build-arg ACL_RDS_PASSWORD=$randompass \
       --build-arg ACL_RDS_TABLE=$postgrestable . && \
       docker run --rm \
       --name psql \
       --link postgresql:postgresql \
       -d psql/bash
       )
       echo "Created container with SHA: $run"
}

# Build Python container

function python {
  run=$(docker build -t python/acl --rm ../. && \
        docker run \
        --name acl \
        -e ACL_SERVER='ftp-server' \
        -e ACL_USERNAME='test' \
        -e ACL_PASSWORD=$randompass \
        -e ACL_LANDING_DIR='test' \
        -e S3_BUCKET_NAME=$bucketname \
        -e S3_KEY_PREFIX=$keyprefix \
        -e S3_ACCESS_KEY_ID=$awskeyid \
        -e S3_SECRET_ACCESS_KEY=$awssecret \
        -e CLAMAV_URL='clamav-api' \
        -e CLAMAV_PORT='8080' \
        -e ACL_RDS_HOST='postgresql' \
        -e ACL_RDS_DATABASE=$postgresdb \
        -e ACL_RDS_USERNAME=$postgresuser \
        -e ACL_RDS_PASSWORD=$randompass \
        -e ACL_RDS_TABLE=$postgrestable \
        --link clamav-api:clamav-api \
        --link ftp-server:ftp-server \
        --link postgresql:postgresql \
        -d python/acl
       )
       echo "Created container with SHA: $run"
}

function create_ok_file {
  DATE=`date +%Y%m%d`
  run=$(echo "Test;data;in;file." > $mountpoint/HOMEOFFICEROLL3_$DATE.csv && sleep 5) # wait for Python container start PM2 and process file
  echo "Created OK test file: HOMEOFFICEROLL3_$DATE.csv"
}

function create_virus_file {
  DATE=`date +%Y%m%d`
  run=$(cat ./eicar.com > $mountpoint/HOMEOFFICEROLL3_$DATE.csv)
  echo "Created FAIL test file: HOMEOFFICEROLL3_$DATE.csv"
}

function main {
  echo "********************************************"
  echo "Building postgressql"
  postgresql
  echo "Done."
  echo "********************************************"
  echo "Building FTP-server"
  ftp_server
  echo "Done."
  echo "********************************************"
  echo "Building clamav"
  clamav
  echo "Done."
  echo "********************************************"
  echo "Building clamav-api"
  clamav_api
  echo "Done."
  echo "********************************************"
  echo "Building and running postgresql sidekick"
  postgresql_sidekick
  echo "Done."
  echo "********************************************"
  echo "Building python"
  python
  echo "Done."
  echo "********************************************"
  echo "Generating test files."
  echo "Creating OK test file and wait 5 seconds so that Python container can process it. Waiting..."
  create_ok_file
  echo "Done."
  echo "********************************************"
  echo "Creating Virus test file. Waiting..."
  create_virus_file
  echo "Done."
  echo "********************************************"
  echo "Check S3 and verify test files are there also check clamav logs to see the virus being blocked"
  echo "********************************************"
}

main

exit
