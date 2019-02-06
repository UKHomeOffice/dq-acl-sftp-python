#!/bin/bash

# This script does the following:
# - downloads and runs 3 Docker containers all from public repositories
# - builds 3 new containers from the local repository
# - requests running user to supply values used as variables

set -e

# Setting up global variables

# Used by FTP server
echo "********************************************"
echo "Setup ftp-server variables:"
echo "********************************************"
echo "Enter Local mountpoint and press [ENTER]: "
read mountpoint

# Used by acl function
echo "********************************************"
echo "Setup ACL container variables"
echo "********************************************"
echo "Enter bucketname and press [ENTER]: "
read bucketname
echo "Enter secondarybucketname and press [ENTER]: "
read secondarybucketname
echo "Enter keyprefix and press [ENTER]: "
read keyprefix
echo "Enter awskeyid and press [ENTER]: "
read awskeyid
echo "Enter secondaryawskeyid and press [ENTER]: "
read secondaryawskeyid
echo "Enter awssecret and press [ENTER]: "
read awssecret
echo "Enter secondaryawssecret and press [ENTER]: "
read secondaryawssecret

# Create random password
echo "********************************************"
randompass=$(openssl rand -hex 24)
echo "Random password generated: $randompass"

# Create random user
echo "********************************************"
username=$(openssl rand -hex 6)
echo "Random username generated: $username"

database='foo'
table='bar'

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
        -e POSTGRES_USER=$username \
        -e POSTGRES_DB=$database \
        -d postgres
       )
       echo "Created container with SHA: $run"
}

# Build Postgres sidekick

function postgresql_sidekick {
  run=$(docker build -t psql/bash \
       --build-arg ACL_RDS_HOST='postgresql' \
       --build-arg ACL_RDS_DATABASE=$database \
       --build-arg ACL_RDS_USERNAME=$username \
       --build-arg ACL_RDS_PASSWORD=$randompass \
       --build-arg ACL_RDS_TABLE=$table . && \
       docker run --rm \
       --name psql \
       --link postgresql:postgresql \
       -d psql/bash
       )
       echo "Created container with SHA: $run"
}

# Build FTP server

function ftp {
  run=$(docker build -t server/ftp ftp/. && \
        docker run --rm \
        --name ftp \
        --cap-add=NET_ADMIN \
        -e FTP_USER=$username \
        -e FTP_PASS=$randompass \
        -v $mountpoint:/home/vsftpd/$username \
        -p 2121:21 -p 2020:20 -p 6000-6010:6000-6010 \
        -d server/ftp
        )
        echo "Created container with SHA: $run"
}

# Build Python container

function python {
  run=$(docker build -t python/acl --rm ../. && \
        docker run --rm \
        --name acl \
        -e ACL_SERVER='ftp' \
        -e ACL_USERNAME=$username \
        -e ACL_PASSWORD=$randompass \
        -e ACL_LANDING_DIR='test' \
        -e S3_BUCKET_NAME=$bucketname \
        -e S3_KEY_PREFIX=$keyprefix \
        -e S3_ACCESS_KEY_ID=$awskeyid \
        -e S3_SECRET_ACCESS_KEY=$awssecret \
        -e SECONDARY_S3_BUCKET_NAME=$secondarybucketname \
        -e SECONDARY_S3_ACCESS_KEY_ID=$secondaryawskeyid \
        -e SECONDARY_S3_SECRET_ACCESS_KEY=$secondaryawssecret \
        -e CLAMAV_URL='clamav-api' \
        -e CLAMAV_PORT='8080' \
        -e ACL_RDS_HOST='postgresql' \
        -e ACL_RDS_DATABASE=$database \
        -e ACL_RDS_USERNAME=$username \
        -e ACL_RDS_PASSWORD=$randompass \
        -e ACL_RDS_TABLE=$table \
        --link clamav-api:clamav-api \
        --link postgresql:postgresql \
        --link ftp:ftp \
        -d python/acl
       )
       echo "Created container with SHA: $run"
}

# Create FTP source dir location

function sourcedir {
  run=$(mkdir -p $mountpoint/test)
  echo "Created FTP source dir"
}

# Create valid file

function create_ok_file {
  DATE=`date -v -1d +%Y%m%d`
  run=$(echo "Test;data;in;file." > $mountpoint/test/HOMEOFFICEROLL3_$DATE.csv)
  echo "Created OK test file: HOMEOFFICEROLL3_$DATE.csv"
}

# Create virus string file

function create_virus_file {
  DATE=`date +%Y%m%d`
  run=$(cat ./eicar.com > $mountpoint/test/HOMEOFFICEROLL3_$DATE.csv)
  echo "Created FAIL test file: HOMEOFFICEROLL3_$DATE.csv"
}

function main {
  echo "********************************************"
  echo "Setting up working files and folders"
  sourcedir
  create_ok_file
  create_virus_file
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
  echo "Build FTP"
  ftp
  echo "Done."
  echo "********************************************"
  echo "Building python"
  python
  echo "Done."
}

main

exit
