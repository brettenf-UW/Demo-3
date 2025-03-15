FROM python:3.9-slim

WORKDIR /app

# Create directories to match potential file locations
RUN mkdir -p /app/main /app/root

# Copy all relevant files and directories
COPY . /app/
COPY pipeline.py /app/

# Try to copy from potential locations if they exist using the correct filenames
RUN find /app -name "milp_soft.py" -exec cp {} /app/ \; || echo "milp_soft.py not found in copied files"
RUN find /app -name "schedule_optimizer.py" -exec cp {} /app/ \; || echo "schedule_optimizer.py not found in copied files"

# Also explicitly copy from the known locations
COPY main/milp_soft.py /app/ || echo "Failed to copy milp_soft.py from main directory"
COPY schedule_optimizer.py /app/ || echo "Failed to copy schedule_optimizer.py from root directory"

# Install potential dependencies 
RUN pip install --no-cache-dir pandas numpy

# Run the pipeline script when the container starts
CMD ["python", "pipeline.py"]
