import subprocess
import sys
import os
import pandas as pd
from pathlib import Path

def check_section_capacity():
    """
    Check if any section is below 75% capacity based on the output from MILPsoft.py.
    
    Returns:
        bool: True if any section is below 75% capacity, False otherwise
    """
    print("Checking section capacities...")
    
    # Define the paths to the necessary files
    output_dir = os.path.join(os.getcwd(), 'output')
    student_assignments_path = os.path.join(output_dir, 'Student_Assignments.csv')
    master_schedule_path = os.path.join(output_dir, 'Master_Schedule.csv')
    sections_info_path = os.path.join(os.getcwd(), 'input', 'Sections_Information.csv')
    
    # Check if the required files exist
    if not os.path.exists(student_assignments_path) or not os.path.exists(sections_info_path):
        print("Required output files not found. Assuming sections are below capacity.")
        return True
    
    try:
        # Load data
        student_assignments = pd.read_csv(student_assignments_path)
        sections_info = pd.read_csv(sections_info_path)
        
        # Calculate enrollment for each section
        section_enrollments = student_assignments['Section ID'].value_counts().to_dict()
        
        # Check if any section is below 75% capacity
        below_capacity_sections = []
        for _, section in sections_info.iterrows():
            section_id = section['Section ID']
            capacity = section['# of Seats Available']
            enrollment = section_enrollments.get(section_id, 0)
            utilization = enrollment / capacity if capacity > 0 else 0
            
            if utilization < 0.75:
                below_capacity_sections.append((section_id, f"{utilization:.2%}"))
        
        if below_capacity_sections:
            print(f"Found {len(below_capacity_sections)} sections below 75% capacity:")
            for section_id, util in below_capacity_sections[:5]:  # Show only first 5 to avoid clutter
                print(f"  - {section_id}: {util} capacity")
            if len(below_capacity_sections) > 5:
                print(f"  - ... and {len(below_capacity_sections) - 5} more")
            return True
        else:
            print("All sections are at or above 75% capacity.")
            return False
        
    except Exception as e:
        print(f"Error checking section capacity: {str(e)}")
        # If there's an error, assume we need to optimize
        return True

def run_milpsoft():
    """
    Run the MILPsoft.py optimization script from the main directory.
    """
    milpsoft_path = os.path.join(os.getcwd(), 'main', 'milp_soft.py')
    print(f"Running MILPsoft optimization from {milpsoft_path}...")
    
    if not os.path.exists(milpsoft_path):
        raise FileNotFoundError(f"Could not find milp_soft.py at {milpsoft_path}")
    
    # Run the script
    subprocess.run([sys.executable, milpsoft_path], check=True)

def run_schedule_optimizer():
    """
    Run the schedule_optimizer.py script from the root directory.
    """
    optimizer_path = os.path.join(os.getcwd(), 'schedule_optimizer.py')
    print(f"Running schedule optimizer from {optimizer_path}...")
    
    if not os.path.exists(optimizer_path):
        raise FileNotFoundError(f"Could not find schedule_optimizer.py at {optimizer_path}")
    
    # Run the script
    subprocess.run([sys.executable, optimizer_path], check=True)

def run_optimization_pipeline():
    """
    Run the optimization pipeline:
    1. Run MILPsoft.py
    2. Check if any section is below 75% capacity
    3. If yes, run schedule_optimizer.py and then rerun MILPsoft.py
    Maximum 2 iterations of MILPsoft.py.
    """
    max_iterations = 2
    
    print("\n=== Starting Optimization Pipeline ===\n")
    
    try:
        # First run of MILPsoft.py
        print("ITERATION 1:")
        run_milpsoft()
        
        # Check section capacity
        if not check_section_capacity():
            print("\nOptimization complete! All sections are at or above 75% capacity.")
            return
        
        # We have sections below capacity, run schedule_optimizer.py
        print("\nFound sections below 75% capacity. Running schedule optimizer...")
        run_schedule_optimizer()
        
        # Second run of MILPsoft.py
        print("\nITERATION 2:")
        run_milpsoft()
        
        # Final capacity check (informational only)
        below_capacity = check_section_capacity()
        if below_capacity:
            print("\nNote: Some sections still below 75% capacity, but reached maximum iterations.")
        else:
            print("\nAll sections now at or above 75% capacity.")
            
        print("\nOptimization pipeline completed successfully.")
        
    except Exception as e:
        print(f"\nError in optimization pipeline: {str(e)}")
        print("Pipeline execution failed.")

if __name__ == "__main__":
    print("Starting master schedule optimization pipeline")
    run_optimization_pipeline()
