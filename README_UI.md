# School Schedule Optimizer UI

This is a simple web interface for the School Schedule Optimizer system using Gradio.

## Requirements

- Python 3.9 or newer
- Docker installed and configured
- sudo permissions for running Docker commands

## Quick Start

1. Clone this repository to your local machine
2. Navigate to the repository directory
3. Run the start script:

```bash
./start_ui.sh
```

This will:
- Install required dependencies
- Set appropriate permissions
- Start the Gradio web interface

4. Access the UI via:
   - Local access: http://localhost:7860
   - Network access: http://YOUR-SERVER-IP:7860
   - Public access: A temporary public URL will be displayed in the terminal

## Using the Interface

The interface is divided into three tabs:

### 1. Input Files

Upload your CSV files:
- Sections_Information.csv
- Student_Info.csv
- Student_Preference_Info.csv
- Teacher_Info.csv
- Teacher_unavailability.csv

Click "Upload Files" to save them to the input directory.

### 2. Optimization

Click "Start Optimization" to run the schedule optimizer. This will:
- Execute the Docker-based optimization pipeline
- Process the input files
- Generate an optimized schedule
- This process may take several minutes

### 3. Results

After optimization completes:
- Click "Refresh Output Files" to load the generated files
- Download each file by clicking on it
- View statistics about the generated schedule

## Troubleshooting

If you encounter issues:

1. Check that all CSV files are properly formatted
2. Ensure Docker is running and you have sudo permissions
3. Check the system logs for detailed error messages

### Access from Other Devices

If you're having trouble accessing the interface from another device:

1. **Network access**: Make sure your server's firewall allows incoming connections on port 7860
   ```bash
   # To open port 7860 on Amazon Linux
   sudo iptables -A INPUT -p tcp --dport 7860 -j ACCEPT
   ```

2. **Security Groups**: If running on AWS, ensure your security group allows inbound traffic on port 7860
   - Go to EC2 dashboard → Security Groups
   - Select the security group for your instance
   - Edit inbound rules
   - Add rule: Custom TCP, Port 7860, Source 0.0.0.0/0 (or limit to your IP for better security)

3. **Using the public URL**: The temporary public URL provided by Gradio should work from any device with internet access, even if your server is behind a firewall

## Files Generated

The optimizer produces the following output files:
- Master_Schedule.csv - Complete course schedule
- Student_Assignments.csv - Student section assignments
- Teacher_Schedule.csv - Teacher assignments
- Constraint_Violations.csv - Any constraint violations