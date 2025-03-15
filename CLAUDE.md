# Docker Scheduling System Instructions

## System Overview
This system uses a combination of MILP (Mixed Integer Linear Programming) and optimization scripts to create class schedules. The pipeline:
1. Runs `milp_soft.py` for initial schedule creation
2. Checks if sections are at least 75% full
3. If needed, runs `schedule_optimizer.py` to improve utilization 
4. Reruns `milp_soft.py` for final optimization

## Environment Requirements
- Docker installed with proper permissions
- Gurobi license (gurobi.lic)
- Python 3.9+

## Common Commands

### Run the Complete Pipeline
```bash
sudo ./run_docker.sh
```

### Run Individual Scripts in Docker
```bash
# Run MILP algorithm only
sudo ./run_docker.sh milp

# Run schedule optimizer only
sudo ./run_docker.sh optimizer

# Run synthetic data generator
sudo ./run_docker.sh synthetic

# Show help
sudo ./run_docker.sh help
```

### Build Docker Image Only
```bash
sudo docker build -t scheduler-optimizer .
```

### Run Container Manually
```bash
sudo docker run --rm \
  -v "$(pwd)/input:/app/input" \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/main:/app/main" \
  -v "$(pwd)/gurobi.lic:/app/gurobi.lic" \
  -e ANTHROPIC_API_KEY="your-api-key" \
  -e GRB_LICENSE_FILE="/app/gurobi.lic" \
  scheduler-optimizer
```

### Run Python Scripts Directly
```bash
# Run the full pipeline
python pipeline.py

# Run individual components
python main/milp_soft.py
python schedule_optimizer.py
python synthetic.py
```

## Output Files
- `output/Master_Schedule.csv` - Complete course schedule
- `output/Student_Assignments.csv` - Student section assignments
- `output/Teacher_Schedule.csv` - Teacher assignments
- `output/Constraint_Violations.csv` - Any constraint violations

## Troubleshooting
- Docker permission issues: Use `sudo` with Docker commands
- Missing files: Check file paths in Dockerfile and run_docker.sh
- Gurobi license: Ensure license file is correctly mounted in container