import subprocess
import sys
import os
import pandas as pd
from pathlib import Path

def check_section_capacity():
    """
    Check if any section falls below target utilization thresholds based on the output from MILPsoft.py.
    
    Returns:
        bool: True if any section is below target capacity, False otherwise
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
        
        # Track statistics for better reporting
        utilization_stats = {
            'very_low': [], # < 50%
            'low': [],      # 50-65%
            'medium': [],   # 65-80%
            'high': [],     # 80-95%
            'full': []      # >= 95%
        }
        
        # Check section utilization with more nuanced criteria
        below_capacity_sections = []
        for _, section in sections_info.iterrows():
            section_id = section['Section ID']
            capacity = section['# of Seats Available']
            enrollment = section_enrollments.get(section_id, 0)
            utilization = enrollment / capacity if capacity > 0 else 0
            
            # Track statistics
            if utilization < 0.50:
                utilization_stats['very_low'].append(section_id)
            elif utilization < 0.65:
                utilization_stats['low'].append(section_id)
            elif utilization < 0.80:
                utilization_stats['medium'].append(section_id)
            elif utilization < 0.95:
                utilization_stats['high'].append(section_id)
            else:
                utilization_stats['full'].append(section_id)
                
            # Size-dependent utilization thresholds - smaller sections should be more full
            target_utilization = 0.65 if capacity <= 18 else 0.60
            
            if utilization < target_utilization:
                below_capacity_sections.append((section_id, f"{utilization:.2%}"))
        
        # Print utilization statistics
        print(f"\nSection utilization statistics:")
        print(f"  Very low (<50%): {len(utilization_stats['very_low'])} sections")
        print(f"  Low (50-65%): {len(utilization_stats['low'])} sections")
        print(f"  Medium (65-80%): {len(utilization_stats['medium'])} sections")
        print(f"  High (80-95%): {len(utilization_stats['high'])} sections")
        print(f"  Full (>=95%): {len(utilization_stats['full'])} sections")
        
        if below_capacity_sections:
            print(f"\nFound {len(below_capacity_sections)} sections below target capacity:")
            for section_id, util in below_capacity_sections[:5]:  # Show only first 5 to avoid clutter
                print(f"  - {section_id}: {util} capacity")
            if len(below_capacity_sections) > 5:
                print(f"  - ... and {len(below_capacity_sections) - 5} more")
            return True
        else:
            print("\nAll sections are at or above target capacity.")
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
    2. Check if any section is below 60% capacity
    3. If yes, run schedule_optimizer.py and then rerun MILPsoft.py
    Maximum 3 iterations of MILPsoft.py.
    """
    max_iterations = 3
    
    print("\n=== Starting Optimization Pipeline ===\n")
    
    try:
        # Track current iteration
        current_iteration = 1
        
        while current_iteration <= max_iterations:
            # Run MILPsoft for this iteration
            print(f"ITERATION {current_iteration}:")
            run_milpsoft()
            
            # Check section capacity
            if not check_section_capacity():
                print(f"\nOptimization complete! All sections are at or above 60% capacity.")
                return
            
            # We have sections below capacity
            if current_iteration < max_iterations:
                # Not at max iterations yet, run optimizer and try again
                print(f"\nFound sections below 60% capacity. Running schedule optimizer...")
                try:
                    # Check if Sections_Information.csv exists and is readable before running optimizer
                    sections_file = os.path.join(os.getcwd(), 'input', 'Sections_Information.csv')
                    if os.path.exists(sections_file):
                        print(f"Sections file exists at: {sections_file}")
                        print(f"File size: {os.path.getsize(sections_file)} bytes")
                        print(f"File is readable: {os.access(sections_file, os.R_OK)}")
                        print(f"File is writable: {os.access(sections_file, os.W_OK)}")
                    else:
                        print(f"WARNING: Sections file not found at: {sections_file}")
                    
                    # Run the optimizer
                    run_schedule_optimizer()
                    
                    # Verify that optimizer modified the sections file
                    if os.path.exists(sections_file):
                        mod_time = os.path.getmtime(sections_file)
                        mod_time_str = pd.Timestamp.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
                        print(f"Sections file was last modified at: {mod_time_str}")
                        
                        # Check for optimization summary
                        output_dir = os.path.join(os.getcwd(), 'output')
                        summary_file = os.path.join(output_dir, 'optimization_summary.json')
                        if os.path.exists(summary_file):
                            try:
                                import json
                                with open(summary_file, 'r') as f:
                                    summary = json.load(f)
                                
                                # Display key stats from summary
                                print("\nOptimization Summary from JSON:")
                                print(f"  Sections before: {summary.get('sections_before', 'N/A')}")
                                print(f"  Sections after: {summary.get('sections_after', 'N/A')}")
                                print(f"  Changes made: {summary.get('changes_made', 'N/A')}")
                                
                                # Check if sections removed are listed
                                if 'sections_removed' in summary:
                                    print(f"  Removed sections: {', '.join(summary['sections_removed'])}")
                            except Exception as e:
                                print(f"Error reading optimization summary: {str(e)}")
                    else:
                        print("WARNING: Sections file not found after running optimizer")
                except Exception as e:
                    print(f"Error in schedule optimization: {str(e)}")
                    print("Continuing with pipeline despite error...")
            else:
                # At max iterations, we're done
                print(f"\nReached maximum iterations ({max_iterations}).")
                break
            
            # Increment iteration counter
            current_iteration += 1
        
        # Final capacity check (informational only)
        below_capacity = check_section_capacity()
        if below_capacity:
            print(f"\nNote: Some sections still below 60% capacity, but reached maximum iterations ({max_iterations}).")
        else:
            print("\nAll sections now at or above 60% capacity.")
            
        # Check satisfaction statistics
        constraints_file = os.path.join(os.getcwd(), 'output', 'Constraint_Violations.csv')
        if os.path.exists(constraints_file):
            try:
                constraints_df = pd.read_csv(constraints_file)
                # Find overall satisfaction row
                for _, row in constraints_df.iterrows():
                    if 'Metric' in row and row['Metric'] == 'Overall Satisfaction':
                        print(f"\nFinal satisfaction rate: {row['Percentage']} ({row.get('Status', 'N/A')})")
                        print(f"Satisfied {int(row['Count'])} out of {int(row['Total'])} course requests")
                    # Find capacity violations
                    elif 'Metric' in row and row['Metric'] == 'Sections Over Capacity':
                        if 'Count' in row and int(row['Count']) > 0:
                            print(f"Warning: {int(row['Count'])} sections are over capacity!")
            except Exception as e:
                print(f"Error reading constraint violations: {str(e)}")
            
        print("\nOptimization pipeline completed successfully.")
        
    except Exception as e:
        print(f"\nError in optimization pipeline: {str(e)}")
        print("Pipeline execution failed.")

if __name__ == "__main__":
    print("Starting master schedule optimization pipeline")
    run_optimization_pipeline()
