#!/bin/bash

# Make script executable
chmod +x "$0"

# Function to display usage information
function show_usage {
  echo "Usage: $0 [SCRIPT_NAME]"
  echo ""
  echo "Options:"
  echo "  (no argument)       Run the full pipeline (default)"
  echo "  milp                Run main/milp_soft.py"
  echo "  optimizer           Run schedule_optimizer.py"
  echo "  synthetic           Run synthetic.py"
  echo "  help                Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0                  # Run the full pipeline"
  echo "  $0 milp             # Run only the MILP script"
  echo "  $0 optimizer        # Run only the schedule optimizer"
  echo "  $0 synthetic        # Run only the synthetic data generator"
}

# Parse command line argument
SCRIPT_TO_RUN=""
if [ "$1" == "help" ] || [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
  show_usage
  exit 0
elif [ "$1" == "milp" ]; then
  SCRIPT_TO_RUN="main/milp_soft.py"
  echo "Running MILP script only..."
elif [ "$1" == "optimizer" ]; then
  SCRIPT_TO_RUN="schedule_optimizer.py"
  echo "Running schedule optimizer only..."
elif [ "$1" == "synthetic" ]; then
  SCRIPT_TO_RUN="synthetic.py"
  echo "Running synthetic data generator only..."
elif [ -n "$1" ]; then
  echo "Unknown option: $1"
  show_usage
  exit 1
fi

# Build the Docker image
echo "===== Building Docker image ====="
docker build -t scheduler-optimizer .

# Get the current directory path
CURRENT_DIR=$(pwd)

# Set API key variable - hardcoded key
ANTHROPIC_API_KEY="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"

# Base docker run command with volumes
DOCKER_CMD="docker run --rm \
  -v \"$CURRENT_DIR/input:/app/input\" \
  -v \"$CURRENT_DIR/output:/app/output\" \
  -v \"$CURRENT_DIR/main:/app/main\" \
  -v \"$CURRENT_DIR/gurobi (2).lic:/app/gurobi.lic\" \
  -e ANTHROPIC_API_KEY=\"$ANTHROPIC_API_KEY\" \
  -e GRB_LICENSE_FILE=\"/app/gurobi.lic\" \
  scheduler-optimizer"

# Run the container with the appropriate script
if [ -n "$SCRIPT_TO_RUN" ]; then
  echo -e "\n===== Running $SCRIPT_TO_RUN in Docker container ====="
  eval "$DOCKER_CMD python $SCRIPT_TO_RUN"
else
  # Default: run the pipeline
  echo -e "\n===== Running optimization pipeline in Docker container ====="
  eval "$DOCKER_CMD"
fi

echo -e "\n===== Script completed ====="

# Fix permissions on output files
echo "Fixing output permissions..."
chown -R ec2-user:ec2-user output/

echo "The output files are available in the 'output' directory."
if [ -z "$SCRIPT_TO_RUN" ]; then
  echo "Check the following files:"
  echo "  - output/Master_Schedule.csv"
  echo "  - output/Student_Assignments.csv"
  echo "  - output/Teacher_Schedule.csv"
  echo "  - output/Constraint_Violations.csv"
fi
