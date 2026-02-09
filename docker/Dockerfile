# hadolint global ignore=DL3013,DL3018
FROM --platform=$BUILDPLATFORM python:3.14.3-alpine3.23

# For multi-platform build
ARG BUILDPLATFORM
ARG TARGETOS
ARG TARGETARCH

# kubectl version
ARG KUBECTL_VERSION="v1.35.0"

ENV STATUS_PROVISIONER_HOME=/opt/provisioner \
    PYTHONUNBUFFERED=1 \
    USER_UID=1000 \
    USER_GID=1000

COPY docker/requirements.txt ${STATUS_PROVISIONER_HOME}/requirements.txt
COPY docker/docker-entrypoint.sh /
COPY docker/*.py ${STATUS_PROVISIONER_HOME}/

# Install kubectl - it is required for vault-service-status-provisioner-cleanup job
RUN set -x \
    && wget \
        --no-check-certificate \
        -nv \
        -O "/usr/local/bin/kubectl" \
        "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/${TARGETOS}/${TARGETARCH}/kubectl" \
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
    && addgroup -S -g ${USER_GID} provisioner \
    && adduser -s /bin/bash -S -G provisioner -u ${USER_UID} provisioner \
    && addgroup provisioner root \
    # Set permissions
    && chmod +x /docker-entrypoint.sh \
    && chgrp 0 /docker-entrypoint.sh

WORKDIR ${STATUS_PROVISIONER_HOME}

USER ${USER_UID}:0

ENTRYPOINT ["/docker-entrypoint.sh"]
