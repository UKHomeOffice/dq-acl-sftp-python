# dq-acl-ftp-python

[![Docker Repository on Quay](https://quay.io/repository/ukhomeofficedigital/dq-acl-sftp-python/status "Docker Repository on Quay")](https://quay.io/repository/ukhomeofficedigital/dq-acl-sftp-python)

A collection of Docker containers and RDS instance running a data pipeline.
Tasks include:
- FTP LIST and check against a table in RDS PostgreSQL, add if required
- FTP GET from a remote FTP server
- Running virus check on each file pulled from FTP by sending them to ClamAV API
- AWS S3 PUT files to an S3 bucket

## Dependencies

- Docker
- Python2.7
- Drone
- AWS CLI
- AWS Keys with PUT access to S3
- AWS RDS PostgreSQL
- Kubernetes

## Structure

- **app/**
  - *Dockerfile*: describe what is installed in the container and the Python file that needs to run
  - *docker-entrypoint.sh*: bash scripts running at container startup
  - *packages.txt*: Python custom Modules
  - *ecosystem.config.js*: declare variables used by PM2 at runtime
  - **bin/**
    - *DQ_ACL_file_ingest*: Python script used with PM2 to declare imported files to PM2 at runtime
  - **scripts/**
    - *__init__.py*: declare Python module import
    - *DQ_ACL_file_ingest.py*: Python2.7 script running within the container
    - *settings.py*: declare variables passed to the *DQ_ACL_file_ingest.py* file at runtime
  - **test/**
    - *Dockerfile*: PostgreSQL sidekick container config
    - *start.sh*: Download, build and run Docker containers
    - *stop.sh*: Stop and remove **all** Docker containers
    - *eicar.com*: File containing a test virus string
- *.drone.yml*: CI deployment configuration
- *LICENSE*: MIT license file
- *README.md*: readme file

## Local Test suite

Testing the ACL Python script can be done by having access to AWS S3 an FTP server supporting **Passive mode** and Docker.
The full stack comprises of 5 Docker containers within the same network linked to each other so DNS name resolution works between the components.

The containers can be started using the *start.sh* script located in **app/test**.
The script will require the following variables passed in at runtime.

|Name|Value|Required|Description|
| --- |:---:| :---:| --- |
| hostaddress | DNS name or IP | True | Address of the FTP server |
| username | name | True | FTP server username |
| password | pass | True | FTP server password |
| bucketname | s3-bucket-name | True | S3 bucket name |
| keyprefix | prefix | True | S3 folder name |
| awskeyid | ABCD | True | AWS access key ID |
| awssecret | abcdb1234 | True | AWS Secret access key |
| postgresdb | db | True | Name of the PostgreSQL database |
| postgrestable | table | True | Name of a table in the database |
| postgresuser | user | True | Name of the PostgreSQL user |

- Components:
  - ClamAV container
  - ClamAV REST API container
  - PostgreSQL container
  - PostgreSQL sidekick container
  - ACL Python container

After the script has completed - for the first time it will take around 5 minutes to download all images - there should be a couple of test files in the S3 bucket given there were valid files available on the FTP server.

- Launching the test suite

NOTE: navigate to **app/test** first.

```
sh start.sh
```

- When done with testing stop the test suite

NOTE: **all** running containers will be stopped and deleted

```
sh stop.sh
```
