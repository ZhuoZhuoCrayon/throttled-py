ARG PYTHON_VERSION=3.8.12

FROM python:${PYTHON_VERSION}-slim-buster AS base

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

## PYTHON
# Seems to speed things up
ENV PYTHONUNBUFFERED=1
# Turns off writing .pyc files. Superfluous on an ephemeral container.
ENV PYTHONDONTWRITEBYTECODE=1

# Ensures that the python and pip executables used
# in the image will be those from our virtualenv.
ENV PATH="/venv/bin:$PATH"

RUN set -ex && \
    chmod 1777 /tmp && \
    rm /etc/apt/sources.list && \
    echo "deb https://mirrors.cloud.tencent.com/debian buster main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.cloud.tencent.com/debian buster-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb-src https://mirrors.cloud.tencent.com/debian buster main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb-src https://mirrors.cloud.tencent.com/debian buster-updates main contrib non-free" >> /etc/apt/sources.list

RUN set -ex && mkdir ~/.pip && printf '[global]\nindex-url = https://mirrors.tencent.com/pypi/simple/' > ~/.pip/pip.conf


FROM base AS builder
ARG POETRY_VERSION=1.4.1
ENV POETRY_VERSION=${POETRY_VERSION}

WORKDIR /

# Install OS package dependencies.
# Do all of this in one RUN to limit final image size.
RUN set -ex &&  \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc gettext && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /
COPY poetry.lock /

# 创建 Python 虚拟环境并安装依赖
RUN set -ex &&  \
    python -m venv /venv &&  \
    pip install --upgrade pip && \
    pip install poetry==${POETRY_VERSION} && \
    poetry config virtualenvs.create false


RUN set -ex && \
    poetry install --no-root

FROM base AS base-app

# 安装运行时依赖
RUN set -ex &&  \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gettext curl vim && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
USER root

ADD ./ ./

# 拷贝构件
COPY --from=builder /venv /venv


FROM base-app AS app
ENTRYPOINT ["scripts/docker-entrypoint.sh"]
