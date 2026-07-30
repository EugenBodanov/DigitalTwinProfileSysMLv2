FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/opt/digital-twin-profile-sysml-v2 \
    PIPELINE_INPUT_DIR=/pipeline/input \
    PIPELINE_OUTPUT_DIR=/pipeline/output \
    PIPELINE_CODE_DIR=/pipeline/code \
    SYSML_KERNEL_CONTAINER=sysml-kernel-container \
    SYSML_HELPER_SCRIPT=/opt/digital-twin-profile-sysml-v2/apiserver/process_sysml.py \
    DTP_PATH_MAP=""

WORKDIR ${APP_HOME}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        curl \
        git \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY apiserver/process_sysml.py ./apiserver/process_sysml.py

RUN mkdir -p "${PIPELINE_INPUT_DIR}" "${PIPELINE_OUTPUT_DIR}" "${PIPELINE_CODE_DIR}" \
    && chmod +x ./src/uploadSysml.sh

VOLUME ["/pipeline/input", "/pipeline/output", "/pipeline/code"]

ENTRYPOINT ["python", "-m", "src.main"]
CMD ["/pipeline/input", "/pipeline/output"]
