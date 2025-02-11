FROM python:3.10.14-alpine3.20

ENV STATUS_PROVISIONER_HOME=/opt/provisioner \
    PYTHONUNBUFFERED=1


COPY docker/requirements.txt ${STATUS_PROVISIONER_HOME}/requirements.txt
COPY docker/docker-entrypoint.sh /
COPY docker/*.py ${STATUS_PROVISIONER_HOME}/

RUN set -x && apk add --upgrade --no-cache bash python3 apk-tools wget sed

# Install kubectl - it is required for vault-service-status-provisioner-cleanup job
ARG KUBECTL_VERSION="v1.32.1"
RUN set -x \
    && wget \
        --no-check-certificate \
        -nv \
        -O "/usr/local/bin/kubectl" \
        "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && chmod +x "/usr/local/bin/kubectl"

# Upgrade all tools to avoid vulnerabilities
RUN set -x && apk upgrade --no-cache --available

#Add unprivileged user
RUN set -x \
    && addgroup -S -g 1000 provisioner \
    && adduser -s /bin/bash -S -G provisioner -u 1000 provisioner \
    && addgroup provisioner root

RUN set -x \
    && python3 -m ensurepip \
    && rm -r /usr/lib/python*/ensurepip \
    && pip3 install --upgrade pip setuptools==70.0.0 \
    && pip3 install -r ${STATUS_PROVISIONER_HOME}/requirements.txt \
    && rm -rf /var/cache/apk/*

RUN set -x \
    && for path in \
         /docker-entrypoint.sh \
    ; do \
        chmod +x "$path"; \
        chgrp 0 "$path"; \
    done

WORKDIR ${STATUS_PROVISIONER_HOME}

USER 1000:0
ENTRYPOINT ["/docker-entrypoint.sh"]
