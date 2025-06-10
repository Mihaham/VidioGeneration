# Stage 1: Builder stage
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04 AS builder

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    wget \
    python3.10 \
    python3-pip \
    python3.10-venv \
    libgl1 \
    libglib2.0-0 \
    libgoogle-perftools-dev \
    bc \
    && rm -rf /var/lib/apt/lists/*

FROM builder AS requirements_installer

WORKDIR /app
RUN git clone --branch v1.10.1 --depth 1 https://github.com/AUTOMATIC1111/stable-diffusion-webui


WORKDIR /app/stable-diffusion-webui

# Create and setup virtual environment
RUN python3 -m venv venv

RUN venv/bin/python -m pip install \
    -r requirements.txt \
    -r requirements_npu.txt \
    -r requirements-test.txt \
    -r requirements_versions.txt \
    xformers==0.0.23.post1 \
    torchvision==0.16.2

RUN venv/bin/python -m pip install git+https://github.com/openai/CLIP.git

RUN venv/bin/python -m pip install loguru

COPY print_replacer.py print_replacer.py
COPY mytqdm.py mytqdm.py
RUN venv/bin/python print_replacer.py /app/stable-diffusion-webui

# Stage 2: Runtime stage
FROM requirements_installer AS starter

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.10 \
    libgl1 \
    libglib2.0-0 \
    libgoogle-perftools-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/stable-diffusion-webui

# Configure environment
RUN echo "#!/bin/bash\n\
export COMMANDLINE_ARGS='--listen --api --api-log --administrator --xformers'" > webui-user.sh
COPY tqdm_replacer.py tqdm_replacer.py
COPY total_tqdm.py total_tqdm.py

RUN sed -i '1i import os\nif not os.environ.get("DISABLE_PROGRESS_LOGGING"):\n    import tqdm_replacer  # Кастомный прогресс-бар\n' /app/stable-diffusion-webui/launch.py


EXPOSE 7860

CMD ["bash", "webui.sh", "-f"]