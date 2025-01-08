# 定义要用到的命令
POETRY ?= poetry
PIP ?= pip
TWINE ?= twine
# 3.8.12
# 3.9.13
# 3.10.5
# 3.11.10
# 3.12.7
PYTHON_VERSION ?= 3.12.7
POETRY_VERSION ?= 1.8.5
IMAGE_VERSION ?= "dev"
IMAGE_REPO ?= "mirrors.tencent.com/throttled-py"

# 安装依赖的目标
install:
	$(POETRY) install

# 初始化项目
init:
	$(PIP) install --upgrade pip
	$(PIP) install poetry==$(POETRY_VERSION)
	$(POETRY) install
	pre-commit install
	pre-commit install --hook-type commit-msg

# 打包的目标
build:
	$(POETRY) build

# 生成 setup.py 的目标
setup_py:
	$(POETRY) run poetry-setup

# 上传到 PyPI 的目标
upload:
	$(TWINE) upload dist/*

# 上传到 PyPI 测试环境的目标
upload_test:
	$(TWINE) upload --repository-url https://test.pypi.org/legacy/ dist/*

# 设置默认目标：安装依赖、构建并上传到 PyPI
.PHONY: default
default: install build upload

docker-build-local:
	docker build -t ${IMAGE_REPO}:${IMAGE_VERSION}-${PYTHON_VERSION} \
	--build-arg PYTHON_VERSION=${PYTHON_VERSION} \
	--build-arg POETRY_VERSION=${POETRY_VERSION} .
