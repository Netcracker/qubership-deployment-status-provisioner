# hadolint global ignore=DL3013,DL3018
FROM python:3.13.7-alpine3.22

ENV STATUS_PROVISIONER_HOME=/opt/provisioner \
    PYTHONUNBUFFERED=1

COPY docker/requirements.txt ${STATUS_PROVISIONER_HOME}/requirements.txt
COPY docker/docker-entrypoint.sh /
COPY docker/*.py ${STATUS_PROVISIONER_HOME}/

# Install kubectl - it is required for vault-service-status-provisioner-cleanup job
ARG KUBECTL_VERSION="v1.33.4"
RUN set -x \
    && wget \
        --no-check-certificate \
        -nv \
        -O "/usr/local/bin/kubectl" \
        "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && chmod +x "/usr/local/bin/kubectl"

RUN set -x \
    # Install bash, python3, apk-tools, wget, sed
    && apk add --upgrade --no-cache \
        bash \
    # Upgrade all tools to avoid vulnerabilities
    && apk upgrade --no-cache --available \
    # Install python dependencies
    && pip3 install --no-cache-dir --upgrade \
        pip \
        setuptools \
    && pip3 install --no-cache-dir -r ${STATUS_PROVISIONER_HOME}/requirements.txt \
    && rm -rf /var/cache/apk/*

RUN set -x \
    # Add unprivileged user
    && addgroup -S -g 1000 provisioner \
    && adduser -s /bin/bash -S -G provisioner -u 1000 provisioner \
    && addgroup provisioner root \
    # Set permissions
    && chmod +x /docker-entrypoint.sh \
    && chgrp 0 /docker-entrypoint.sh

WORKDIR ${STATUS_PROVISIONER_HOME}

USER 1000:0
ENTRYPOINT ["/docker-entrypoint.sh"]
