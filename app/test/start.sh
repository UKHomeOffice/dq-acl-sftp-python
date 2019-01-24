#!/bin/bash

# This script does the following:
# - downloads and runs 3 (three) Docker containers all from public repositories
# - builds a new container from the local repository
# - requests running user to supply values used as variables

set -e

# Set variables

# Used by ftp_server function
echo "********************************************"
echo "Setup ftp-server variables:"
echo "********************************************"
echo "Enter FTP hostaddress location (full file path) and press [ENTER]: "
read hostaddress
echo "********************************************"
echo "Enter FTP username and press [ENTER]: "
read username
echo "********************************************"
echo "Enter FTP password and press [ENTER]: "
read password

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
        -e ACL_SERVER=$hostaddress \
        -e ACL_USERNAME=$username \
        -e ACL_PASSWORD=$password \
        -e ACL_LANDING_DIR='3_Days' \
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
        --link postgresql:postgresql \
        -d python/acl
       )
       echo "Created container with SHA: $run"
}

function main {
  echo "********************************************"
  echo "Building postgressql"
  postgresql
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
}

main

exit
