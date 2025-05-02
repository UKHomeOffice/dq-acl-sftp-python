FROM alpine:3.18.7

ENV USERMAP_UID 1000
ENV RUNNER_UID 1001
ENV DOCKER_UID 1002
ENV PYTHONPATH="$PYTHONPATH:/ADT"


# Setup folder structure and copy files
RUN mkdir -p \
             /tmp/ADT/scripts \
             /tmp/ADT/data/acl \
             /tmp/ADT/stage/acl \
             /tmp/ADT/quarantine/acl \
             /tmp/ADT/log \
             /tmp/ADT/bin \
             /ADT \
             /home/runner/.pm2 \
             /home/runner/.ssh

COPY packages.txt /tmp/ADT/scripts
COPY package.json /
COPY ecosystem.config.js /tmp/ADT/scripts
COPY docker-entrypoint.sh /
ADD bin /tmp/ADT/bin
ADD scripts /tmp/ADT/scripts

# Add user
RUN addgroup -g $RUNNER_UID runner && \
    adduser -u $USERMAP_UID -G runner -D runner && \
    addgroup -g $DOCKER_UID docker && \
    chown -R runner:runner /ADT && \
    chown -R runner:runner /home/runner/.pm2 && \
    chown -R runner:runner /home/runner/.ssh

# Install script dependencies
RUN apk update  && \
    apk add --update py3-boto3 py3-pip py3-requests py3-schedule \
                    py3-schedule py3-psycopg2 py3-cryptography py3-semver libcrypto3 libssl3

# Wheel required for non-legacy ftputil install
RUN pip3 install wheel ftputil

# Install PM2
RUN apk add nodejs npm
RUN npm install -g nodemon pm2 npm

VOLUME ["/ADT"]
RUN chown -R runner:runner /ADT

RUN chown runner:runner /docker-entrypoint.sh && \
chmod +x /docker-entrypoint.sh

USER ${USERMAP_UID}

WORKDIR /ADT

ENTRYPOINT ["sh", "/docker-entrypoint.sh"]

# Start PM2
CMD pm2-docker /ADT/scripts/ecosystem.config.js  -- --config $ACL_SERVER $ACL_USERNAME $ACL_PASSWORD $ACL_LANDING_DIR $S3_BUCKET_NAME \
    $S3_ACCESS_KEY_ID $S3_SECRET_ACCESS_KEY $CLAMAV_URL $CLAMAV_PORT \
    $ACL_RDS_HOST $ACL_RDS_DATABASE $ACL_RDS_USERNAME $ACL_RDS_PASSWORD $ACL_RDS_TABLE $SLACK_WEBHOOK

# Save PM2 configuration
RUN pm2 save
