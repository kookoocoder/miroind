FROM node:22.21.1-bookworm-slim

# The backend supports Python 3.11/3.12. Debian Bookworm supplies Python 3.11,
# which keeps the image small while the repository pins local development to
# Python 3.12 through .python-version.
RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-venv \
  && rm -rf /var/lib/apt/lists/*

# 从 uv 官方镜像复制 uv
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# 先复制依赖描述文件以利用缓存
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

# 安装依赖（Node + Python）
RUN npm ci \
  && npm ci --prefix frontend \
  && uv sync --frozen --project backend --python 3.11

# 复制项目源码
COPY . .

EXPOSE 3000 5001

# Start the credential-free MiroInd workflow by default. Override
# MIROIND_OFFLINE_ONLY=false and provide provider credentials for upstream
# graph/simulation features.
ENV MIROIND_OFFLINE_ONLY=true
CMD ["npm", "run", "dev:miroind"]
