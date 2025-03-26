FROM python:3.9-slim

WORKDIR /app

# Install all dependencies from requirements.txt
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/input /app/output /app/main

# Copy all files preserving directory structure
COPY main/ /app/main/
COPY input/ /app/input/
COPY output/ /app/output/
COPY pipeline.py schedule_optimizer.py synthetic.py /app/
COPY "gurobi.lic" /app/gurobi.lic

# Set environment variables for Gurobi license
ENV GRB_LICENSE_FILE=/app/gurobi.lic
ENV PATH="$PATH:/opt/gurobi/bin"

# Anthropic API key will be provided at runtime via environment variable
# Create empty .env file for dotenv loading
RUN touch /app/.env

# Verify files were copied correctly
RUN echo "Checking for required files:" && \
    [ -f /app/main/milp_soft.py ] && echo "✓ Found milp_soft.py" || echo "✗ Missing milp_soft.py" && \
    [ -f /app/schedule_optimizer.py ] && echo "✓ Found schedule_optimizer.py" || echo "✗ Missing schedule_optimizer.py" && \
    [ -f /app/pipeline.py ] && echo "✓ Found pipeline.py" || echo "✗ Missing pipeline.py" && \
    [ -f /app/synthetic.py ] && echo "✓ Found synthetic.py" || echo "✗ Missing synthetic.py" && \
    [ -f /app/gurobi.lic ] && echo "✓ Found Gurobi license file" || echo "✗ Missing Gurobi license file"

# Display environment setup
RUN echo "Environment setup complete:" && \
    echo "API Key configured" && \
    echo "Gurobi License: $(ls -la /app/gurobi.lic)"

# Run the pipeline script when the container starts
CMD ["python", "pipeline.py"]
