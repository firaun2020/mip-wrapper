# Multi-stage build: compile .NET helper and package Python wrapper

# Stage 1: Build .NET helper
FROM mcr.microsoft.com/dotnet/sdk:6.0 AS helper-builder
WORKDIR /build
COPY native/MipWrapper.Helper/ ./
RUN dotnet publish -c Release -o /app/helper

# Stage 2: Runtime image with Python and .NET
FROM mcr.microsoft.com/dotnet/runtime:6.0
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y python3.11 python3.11-venv python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy helper from build stage
COPY --from=helper-builder /app/helper ./helper/

# Copy Python source
COPY src/mip_wrapper/ ./mip_wrapper/
COPY pyproject.toml setup.py* ./

# Install Python package
RUN pip install --no-cache-dir -e .

# Set helper executable permissions
RUN chmod +x ./helper/MipWrapper.Helper

# Add helper to PATH
ENV PATH="/app/helper:${PATH}"

# Default to Python when run
ENTRYPOINT ["python3"]
CMD ["-c", "import mip_wrapper; print(f'MIP Wrapper {mip_wrapper.__version__} ready')"]
