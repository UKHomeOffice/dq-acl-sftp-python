# dq-acl-ftp-python

[![Docker Repository on Quay](https://quay.io/repository/ukhomeofficedigital/dq-acl-sftp-python/status "Docker Repository on Quay")](https://quay.io/repository/ukhomeofficedigital/dq-acl-sftp-python)

A Docker container that runs the following Tasks:
- FTP LIST and check against a table in RDS PostgreSQL, add if required
- FTP GET from a remote FTP server
- Running virus check on each file pulled from FTP by sending them to ClamAV API
- AWS S3 PUT files to an S3 bucket

## Dependencies

- Docker
- Python3.7
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
  - **kube/**
    - *deployment.yml*: describe a Kubernetes POD deployment
    - *pvc.yml*: declare a Persistent Volume in Kubernetes
    - *secret.yml*: list the Drone secrets passed to the containers during deployment      
- *.drone.yml*: CI deployment configuration
- *LICENSE*: MIT license file
- *README.md*: readme file

## Kubernetes POD connectivity

The POD consists of 3 (three) Docker containers responsible for handling data.

| Container Name | Function | Language | Exposed port | Managed by |
| :--- | :---: | :---: | ---: | --- |
| dq-acl-data-ingest | Data pipeline app| Python2.7 | N/A | DQ Devops |


## RDS PostgreSQL connectivity

The RDS instance is stand alone and not part of the POD or this deployment. This **README.md** assumes the instance has been configured prior to deployment of the POD and includes:

- Database
- Table
- User
- Password

The *dq-acl-data-ingest* container connects to the PostgreSQL backend at each run using its DNS host name, username, database and password.

## Data flow

- *dq-acl-data-ingest* lists files on an FTP server and only move to the next step of the file does not yet exist in the RDS database table
- *dq-acl-data-ingest* GET files from an external FTP server
- sending these files to *clamav-api* with destination *dq-clamav:443*
- *OK* or *!OK* response text is sent back to *dq-acl-data-ingest*
  - *IF OK* file is uploaded to S3 and deleted from local storage
  - *IF !OK* file is moved to quarantine on the PVC

## Drone secrets

Environmental variables are set in Drone based on secrets listed in the *.drone.yml* file and they are passed to Kubernetes as required.

## Local Test suite

Testing the ACL Python script can be done by having access to AWS S3 and Docker.
The full stack comprises of 6 Docker containers within the same network linked to each other so DNS name resolution works between the components.

The containers can be started using the *start.sh* script located in **app/test**.
The script will require the following variables passed in at runtime.

|Name|Value|Required|Description|
| --- |:---:| :---:| --- |
| mountpoint | /local/path | True | Local Docker mountpoint |
| bucketname | s3-bucket-name | True | S3 bucket name |
| secondarybucketname | s3-bucket-name | True | S3 bucket name |
| keyprefix | prefix | True | S3 folder name |
| awskeyid | ABCD | True | AWS access key ID |
| secondaryawskeyid | ABCD | True | AWS access key ID |
| awssecret | abcdb1234 | True | AWS Secret access key |
| secondaryawssecret | abcdb1234 | True | AWS Secret access key |
| webhook | https://hooks.slack.com/services/ABCDE12345 | True | Slack Webhook URL |

- Components:
  - FTP container
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
