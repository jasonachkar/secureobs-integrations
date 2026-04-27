FROM python:3.12-slim
LABEL maintainer="Jason Achkar Diab"

RUN apt-get update && apt-get install -y --no-install-recommends \
        git wget ca-certificates \
    && pip install --no-cache-dir semgrep requests \
    && wget -q https://github.com/gitleaks/gitleaks/releases/download/v8.21.2/gitleaks_8.21.2_linux_x64.tar.gz \
    && tar -xzf gitleaks_8.21.2_linux_x64.tar.gz gitleaks \
    && mv gitleaks /usr/local/bin/gitleaks \
    && rm gitleaks_8.21.2_linux_x64.tar.gz \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY scripts/ /scripts/

ENTRYPOINT ["python3", "/scripts/cli.py"]
