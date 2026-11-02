# Pinned test runner image for Adversary sandbox
FROM python:3.12-slim

# Install test tools
RUN pip install --no-cache-dir pytest>=8.0.0 hypothesis>=6.100.0

# Create unprivileged runner user
RUN useradd -u 1000 -m runner
USER 1000:1000

WORKDIR /app

