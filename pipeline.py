import subprocess
import sys
import os
from pathlib import Path

# Define potential paths where scripts might be located
def find_script(script_name):
    """Find the script in various potential locations"""
    # List of potential directories to check
    potential_dirs = [
        os.getcwd(),                     # Current directory
        os.path.dirname(os.getcwd()),    # Parent directory
        os.path.join(os.getcwd(), 'main'), # 'main' subfolder
        os.path.join(os.getcwd(), 'root'), # 'root' subfolder
        os.path.join(os.path.dirname(os.getcwd()), 'main'),  # Parent's main folder
        '/app'                           # Docker container's directory
    ]
    
    # Check each directory for the script
    for directory in potential_dirs:
        script_path = os.path.join(directory, script_name)
        if os.path.isfile(script_path):
            print(f"Found {script_name} at: {script_path}")
            return script_path
            
    # If not found, raise an error
    raise FileNotFoundError(f"Could not find {script_name} in any of the expected locations")

def check_capacity():
    """
    Check if any section is below 75% capacity.
    
    This is a placeholder - you'll need to implement the actual check based 
    on how your MILPsoft.py outputs section capacity data.
    
    Returns:
        bool: True if any section is below 75% capacity, False otherwise
    """
    # Implement your capacity checking logic here
    # Example implementation might read from a file output by MILPsoft.py
    print("Checking section capacities...")
    
    # Replace with actual implementation
    # For example, parse output files from MILPsoft.py
    below_threshold = True  # Change this based on your actual check
    
    return below_threshold

def run_optimization_pipeline():
    """Run the MILPsoft optimization pipeline up to 2 times"""
    max_iterations = 2
    
    # Find script paths with correct filenames
    try:
        milpsoft_path = find_script("milp_soft.py")  # Updated correct filename
        optimizer_path = find_script("schedule_optimizer.py")  # Updated correct filename
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure both milp_soft.py and schedule_optimizer.py are available.")
        return
    
    for iteration in range(max_iterations):
        print(f"\nStarting iteration {iteration + 1}/{max_iterations}")
        
        # Run milp_soft.py
        print(f"Running milp_soft.py from {milpsoft_path}...")
        subprocess.run([sys.executable, milpsoft_path], check=True)
        
        # Check if any section is below 75% capacity
        if not check_capacity():
            print("All sections are at or above 75% capacity. Optimization complete!")
            break
            
        # If this is the last iteration, don't run optimizer again
        if iteration == max_iterations - 1:
            print("Reached maximum iterations. Final schedule determined.")
            break
            
        # Run schedule_optimizer.py to improve the schedule
        print(f"Some sections below 75% capacity. Running schedule_optimizer.py from {optimizer_path}...")
        subprocess.run([sys.executable, optimizer_path], check=True)
    
    print("\nOptimization pipeline completed successfully.")

if __name__ == "__main__":
    print("Starting master schedule optimization pipeline")
    run_optimization_pipeline()
