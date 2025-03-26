# School Schedule Optimizer System

## Overview

The School Schedule Optimizer is a comprehensive solution for educational institutions to create optimized class schedules that maximize student satisfaction while balancing various constraints such as teacher availability, room capacities, and period assignments.

The system consists of:
1. A Mixed Integer Linear Programming (MILP) optimization engine
2. A schedule refinement system
3. A web-based user interface built with Gradio
4. Docker containerization for easy deployment

## Key Features

- **100% Student Satisfaction** - Guarantees that all student course requests are fulfilled
- **Teacher Schedule Optimization** - Ensures teachers are not double-booked
- **Section Capacity Management** - Balances class sizes while maintaining student satisfaction
- **Web-based Interface** - Upload data, run optimizations, and download results through an intuitive UI
- **Containerized Deployment** - Run the entire system in Docker with minimal setup

## System Requirements

- Docker Engine (version 20.10+)
- 8GB RAM minimum (16GB+ recommended for larger datasets)
- Gurobi license (Academic licenses available free for educational institutions)
- Python 3.9+ (if running outside Docker)
- 10GB free disk space

## Quick Start Guide

### 1. Basic Setup

1. Clone the repository:
   ```
   git clone https://github.com/your-org/scheduler-optimizer.git
   cd scheduler-optimizer
   ```

2. Set up secure credentials:
   ```
   # Create the .secrets directory
   mkdir -p .secrets
   
   # Create and edit your credentials file
   nano .secrets/.env
   
   # Run the setup script to generate credential files
   ./setup_credentials.sh
   ```
   
   See [SECURITY.md](SECURITY.md) for detailed instructions on securing credentials.

3. Build and run the Docker container:
   ```
   sudo ./run_docker.sh
   ```

### 2. Starting the Web Interface

1. Launch the web UI:
   ```
   python app.py --port 7860 --share
   ```

   Options:
   - `--port`: Specify the port to run the UI (default: 7860)
   - `--share`: Create a public share link accessible from the internet
   - Add `&` at the end to run in the background

2. Access the UI:
   - Local: http://localhost:7860
   - Remote: http://server-ip:7860
   - Public link: Provided in the terminal output if using `--share`

3. For server deployment, consider using a startup script:
   ```
   # Create the startup script
   cat > start_ui.sh << 'EOF'
   #!/bin/bash
   cd "$(dirname "$0")"
   nohup python app.py --port 7860 --server_name 0.0.0.0 > ui.log 2>&1 &
   echo "UI started on port 7860. Check ui.log for details."
   EOF
   
   # Make it executable
   chmod +x start_ui.sh
   
   # Run it
   ./start_ui.sh
   ```

### 3. Using the Web Interface

The UI is organized into three main tabs:

#### Input Files Tab
- Upload your CSV files:
  - Sections Information
  - Student Info
  - Student Preferences
  - Teacher Info
  - Teacher Unavailability
  - Period (optional)
  
- Click "Upload Files" to process the data

#### Optimization Tab
- Click "Start Optimization" to run the schedule optimization pipeline
- The optimization process:
  1. Runs the MILP algorithm to create an initial schedule
  2. Checks section utilization
  3. Runs the schedule optimizer to improve low-utilization sections
  4. Reruns the MILP algorithm for the final schedule
- Progress and results will be displayed in the status area

#### Results Tab
- Click "Refresh Output Files" to see the generated files
- Download the optimization results:
  - Master Schedule: Section to period assignments
  - Student Assignments: Student to section assignments
  - Teacher Schedule: Teacher timetables
  - Constraint Violations: Summary of optimization metrics

## Input File Formats

### Sections Information (Sections_Information.csv)
```
Section ID,Course ID,# of Seats Available,Teacher Assigned
S001,Medical Career,20,T005
S002,Medical Career,20,T007
...
```

### Student Info (Student_Info.csv)
```
Student ID,SPED
ST001,0
ST002,1
...
```

### Student Preferences (Student_Preference_Info.csv)
```
Student ID,Preferred Sections
ST001,Math 1;English 9;Biology;World History;PE
ST002,Math 1;English 9;Biology;World History;Heroes Teach
...
```

### Teacher Info (Teacher_Info.csv)
```
Teacher ID,Teacher Name
T001,John Smith
T002,Jane Doe
...
```

### Teacher Unavailability (Teacher_unavailability.csv)
```
Teacher ID,Unavailable Periods
T001,R1;G2
T002,R3;R4
...
```

### Period (Period.csv) - Optional
```
Period ID
R1
R2
...
```

## Running Individual Components

### Run MILP Only
```
sudo ./run_docker.sh milp
```

### Run Schedule Optimizer Only
```
sudo ./run_docker.sh optimizer
```

### Generate Synthetic Test Data
```
sudo ./run_docker.sh synthetic
```

### Show Help
```
sudo ./run_docker.sh help
```

## Output Files

The system generates several output files in the `output` directory:

### Master_Schedule.csv
Contains the mapping of sections to periods.
```
Section ID,Period
S001,R1
S002,G1
...
```

### Student_Assignments.csv
Contains the assignment of students to sections.
```
Student ID,Section ID
ST001,S005
ST001,S026
...
```

### Teacher_Schedule.csv
Contains the teacher assignments with periods.
```
Teacher ID,Section ID,Period
T001,S005,R1
T001,S026,G2
...
```

### Constraint_Violations.csv
Contains metrics about the optimization results.
```
Metric,Count,Total,Percentage,Satisfaction_Rate,Total_Sections,Total_Overages,Status
Missed Requests,0,2400.0,0.00%,100.00%,,,
Sections Over Capacity,4,,3.10%,,129.0,277.0,
Overall Satisfaction,2400,2400.0,100.00%,,,,Perfect
```

## Advanced Configuration

### Customizing Docker Setup

Edit the `Dockerfile` to:
- Change the Python version
- Add additional dependencies
- Modify environment variables
- Configure resource limits

### Modifying the Optimization Parameters

Edit `main/milp_soft.py` to:
- Adjust capacity violation penalties
- Change optimization time limits
- Modify memory usage parameters
- Set solution limits

### Extending the Web UI

Edit `app.py` to:
- Add new input fields
- Create additional visualization components
- Include custom preprocessing steps
- Implement advanced reporting

## Troubleshooting

### Common Issues and Solutions

1. **Docker Permission Issues**
   - Run all Docker commands with `sudo`
   - Add your user to the Docker group: `sudo usermod -aG docker $USER`

2. **Gurobi License Problems**
   - Ensure the license file is named `gurobi.lic` and placed in the root directory
   - Verify the license is valid: `grbprobe`
   - Check the container has access to the license: `docker exec scheduler-optimizer ls -la /app/gurobi.lic`

3. **Input File Errors**
   - Verify file formats match the examples above
   - Check for extra commas or special characters in CSV files
   - Ensure Student IDs in preferences match those in student info

4. **Web UI Not Accessible**
   - Verify the port is not blocked by a firewall: `sudo ufw status`
   - Check if another service is using the same port: `sudo netstat -tulpn | grep 7860`
   - Ensure you're using the correct IP address or hostname

5. **Optimization Not Finding Solutions**
   - Increase memory allocation in Docker: modify `run_docker.sh` to add `--memory=16g`
   - Extend optimization time limits in `milp_soft.py`
   - Check for conflicting constraints in your input data

### Logs and Debugging

Important log files:
- `output/gurobi_scheduling.log` - Optimization engine logs
- `ui.log` - Web interface logs
- `debug/` directory - Detailed debug information

To enable verbose logging:
```
export GRB_LOGFILE=detailed_log.log
export GRB_LOGLEVEL=1
```

## Server Deployment Guide

For long-term deployment on a server:

1. **Set up automatic startup**:
   Create a systemd service:
   ```
   sudo nano /etc/systemd/system/scheduler-ui.service
   ```

   Add the content:
   ```
   [Unit]
   Description=School Schedule Optimizer UI
   After=network.target

   [Service]
   User=yourusername
   WorkingDirectory=/path/to/scheduler-optimizer
   ExecStart=/usr/bin/python /path/to/scheduler-optimizer/app.py --port 7860 --server_name 0.0.0.0
   Restart=on-failure
   RestartSec=5s

   [Install]
   WantedBy=multi-user.target
   ```

   Enable and start the service:
   ```
   sudo systemctl enable scheduler-ui
   sudo systemctl start scheduler-ui
   ```

2. **Configure a reverse proxy** (optional, for HTTPS):
   Install Nginx:
   ```
   sudo apt update
   sudo apt install nginx
   ```

   Create a configuration:
   ```
   sudo nano /etc/nginx/sites-available/scheduler
   ```

   Add content:
   ```
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:7860;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

   Enable the site:
   ```
   sudo ln -s /etc/nginx/sites-available/scheduler /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

3. **Add HTTPS with Certbot** (recommended):
   ```
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

## Performance Optimization

For large datasets:

1. **Increase system resources**:
   - Allocate more memory to Docker: `--memory=32g`
   - Use more CPU cores: `-e GRB_THREADS=16`

2. **Optimize model parameters**:
   - Reduce solution precision: Add `self.model.Params.MIPGap = 0.01` (1% gap)
   - Use a heuristic approach: `self.model.Params.Heuristics = 0.8`
   - Limit branching: `self.model.Params.BranchDir = 1`

3. **Enable parallel optimization**:
   - Set concurrent environments: `self.model.Params.ConcurrentMIP = 4`
   - Distribute workload: `self.model.Params.DistributedMIPJobs = 4`

## Contact and Support

For support or to report issues:
- Create an issue on the GitHub repository
- Email: support@example.com
- Documentation: https://example.com/docs

## License

This project is licensed under the MIT License - see the LICENSE file for details.