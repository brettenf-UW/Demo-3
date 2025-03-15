import gradio as gr
import os
import subprocess
import shutil
import time
import pandas as pd

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Define input file mappings - these are the files the user will upload
INPUT_FILES = {
    "Sections Information": "Sections_Information.csv",
    "Student Info": "Student_Info.csv",
    "Student Preferences": "Student_Preference_Info.csv",
    "Teacher Info": "Teacher_Info.csv",
    "Teacher Unavailability": "Teacher_unavailability.csv",
    "Period": "Period.csv"
}

# Define output file mappings - these are the files the user will download
OUTPUT_FILES = {
    "Master Schedule": "Master_Schedule.csv",
    "Student Assignments": "Student_Assignments.csv",
    "Teacher Schedule": "Teacher_Schedule.csv",
    "Constraint Violations": "Constraint_Violations.csv"
}

def save_file_from_upload(file_obj, file_type):
    """Save a file from a Gradio upload and return status message"""
    if file_obj is None:
        return f"No {file_type} file uploaded"
    
    # Get target filename
    target_filename = INPUT_FILES.get(file_type)
    if not target_filename:
        return f"Unknown file type: {file_type}"
    
    target_path = os.path.join(INPUT_DIR, target_filename)
    
    try:
        # Make backup of existing file
        if os.path.exists(target_path):
            backup_path = f"{target_path}.bak"
            shutil.copy2(target_path, backup_path)
            backup_msg = f"Created backup of existing {file_type} file"
        else:
            backup_msg = ""
        
        # Handle different file object types from Gradio
        if hasattr(file_obj, 'name'):  # File object from newer Gradio versions
            # Copy the uploaded file to the target location
            shutil.copy2(file_obj.name, target_path)
        elif isinstance(file_obj, str):  # String path from some Gradio versions
            shutil.copy2(file_obj, target_path)
        else:
            # Try different approach for other object types
            with open(target_path, 'wb') as f:
                if hasattr(file_obj, 'read'):  # File-like object
                    f.write(file_obj.read())
                elif hasattr(file_obj, 'save'):  # Gradio's UploadFile
                    file_obj.save(target_path)
                    return f"✅ Saved {file_type}"
                else:
                    return f"❌ Unsupported file object type for {file_type}"
        
        # Verify file was saved correctly
        if os.path.exists(target_path):
            # Try to read the CSV to verify it's valid
            try:
                df = pd.read_csv(target_path)
                row_count = len(df)
                col_count = len(df.columns)
                status = f"✅ Saved {file_type}: {row_count} rows, {col_count} columns"
                if backup_msg:
                    status = f"{status}\n{backup_msg}"
                return status
            except Exception as e:
                return f"⚠️ Saved {file_type} but file may be invalid: {str(e)}"
        else:
            return f"❌ Failed to save {file_type} file"
            
    except Exception as e:
        return f"❌ Error processing {file_type}: {str(e)}"

def upload_files(section_info, student_info, student_prefs, teacher_info, teacher_unavail, period_file):
    """Process uploaded files and save them to the input directory"""
    file_map = {
        "Sections Information": section_info,
        "Student Info": student_info,
        "Student Preferences": student_prefs,
        "Teacher Info": teacher_info,
        "Teacher Unavailability": teacher_unavail,
        "Period": period_file
    }
    
    results = []
    for file_type, file_obj in file_map.items():
        result = save_file_from_upload(file_obj, file_type)
        results.append(result)
    
    return "\n".join(results)

def run_optimization():
    """Run the optimization process using the Docker container"""
    # Check if all required input files exist (excluding Period which is optional)
    required_files = dict(INPUT_FILES)
    optional_files = ["Period"]  # Period.csv is optional
    
    for opt_file in optional_files:
        if opt_file in required_files:
            del required_files[opt_file]
    
    missing_files = []
    for file_type, filename in required_files.items():
        file_path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(file_path):
            missing_files.append(f"{file_type} ({filename})")
    
    if missing_files:
        return f"❌ Cannot start optimization: Missing required input files:\n" + "\n".join(missing_files)
    
    # Start the optimization process
    try:
        results = ["🚀 Starting optimization process...", "⏳ This may take several minutes. Please wait..."]
        
        # Run the Docker optimization script
        cmd = ["sudo", "./run_docker.sh"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=BASE_DIR)
        
        # Wait for process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            results.append("✅ Optimization completed successfully!")
            
            # Check output files and show stats
            all_found = True
            for output_type, filename in OUTPUT_FILES.items():
                file_path = os.path.join(OUTPUT_DIR, filename)
                if os.path.exists(file_path):
                    # For specific outputs, show some statistics
                    if output_type == "Constraint Violations":
                        try:
                            df = pd.read_csv(file_path)
                            for _, row in df.iterrows():
                                if 'Metric' in row and row['Metric'] == 'Overall Satisfaction':
                                    results.append(f"📊 Satisfaction Rate: {row['Percentage']} ({row.get('Status', 'N/A')})")
                                    results.append(f"📊 Satisfied {int(row['Count'])} out of {int(row['Total'])} course requests")
                        except:
                            pass
                    else:
                        try:
                            df = pd.read_csv(file_path)
                            results.append(f"📋 {output_type}: {len(df)} records generated")
                        except:
                            results.append(f"📋 {output_type} file created")
                else:
                    results.append(f"❌ Warning: {output_type} file not found")
                    all_found = False
            
            if all_found:
                results.append("\n✨ All output files were generated successfully. Click 'Refresh Output Files' to download them.")
        else:
            results.append(f"❌ Error running optimization. Check system logs for details.")
            if stderr:
                results.append(f"Error details: {stderr[:500]}...")
        
        return "\n".join(results)
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

def get_output_files():
    """Get the output files for download"""
    output_paths = []
    
    for filename in OUTPUT_FILES.values():
        file_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(file_path):
            output_paths.append(file_path)
        else:
            output_paths.append(None)
    
    return output_paths

def create_ui():
    """Create the Gradio interface"""
    with gr.Blocks(title="School Schedule Optimizer") as app:
        gr.Markdown("# 🏫 School Schedule Optimizer")
        gr.Markdown("Upload your input files, then click 'Optimize' to generate an optimized schedule.")
        
        with gr.Tab("Input Files"):
            with gr.Column():
                # Input file uploads
                gr.Markdown("### 📤 Upload Your CSV Files")
                with gr.Row():
                    with gr.Column():
                        section_info_file = gr.File(label="Sections Information CSV", file_types=[".csv"])
                        student_info_file = gr.File(label="Student Info CSV", file_types=[".csv"])
                        student_prefs_file = gr.File(label="Student Preferences CSV", file_types=[".csv"])
                    with gr.Column():
                        teacher_info_file = gr.File(label="Teacher Info CSV", file_types=[".csv"])
                        teacher_unavail_file = gr.File(label="Teacher Unavailability CSV", file_types=[".csv"])
                        period_file = gr.File(label="Period CSV", file_types=[".csv"])
                
                upload_status = gr.Textbox(label="Upload Status", lines=12, interactive=False)
                
                upload_btn = gr.Button("Upload Files", variant="primary")
                
                # Connect upload button
                upload_btn.click(
                    fn=upload_files,
                    inputs=[
                        section_info_file,
                        student_info_file,
                        student_prefs_file,
                        teacher_info_file,
                        teacher_unavail_file,
                        period_file
                    ],
                    outputs=upload_status
                )
        
        with gr.Tab("Optimization"):
            with gr.Column():
                gr.Markdown("### ⚙️ Run Optimization")
                gr.Markdown("Click the button below to start the schedule optimization process. This will run the Docker container to generate an optimal schedule.")
                
                optimize_btn = gr.Button("Start Optimization", variant="primary")
                optimization_status = gr.Textbox(label="Optimization Status", lines=15, interactive=False)
                
                # Connect optimize button
                optimize_btn.click(
                    fn=run_optimization,
                    inputs=[],
                    outputs=optimization_status
                )
        
        with gr.Tab("Results"):
            with gr.Column():
                gr.Markdown("### 📊 Download Results")
                gr.Markdown("Click 'Refresh' to see the latest output files, then download them.")
                
                # Output file downloads
                master_schedule = gr.File(label="Master Schedule", interactive=False)
                student_assignments = gr.File(label="Student Assignments", interactive=False)
                teacher_schedule = gr.File(label="Teacher Schedule", interactive=False)
                constraints = gr.File(label="Constraint Violations", interactive=False)
                
                refresh_btn = gr.Button("Refresh Output Files")
                
                # Connect refresh button
                refresh_btn.click(
                    fn=get_output_files,
                    inputs=[],
                    outputs=[
                        master_schedule,
                        student_assignments,
                        teacher_schedule,
                        constraints
                    ]
                )
    
    return app

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Start the School Schedule Optimizer UI')
    parser.add_argument('--port', type=int, default=7860, help='Port to run the Gradio app on')
    parser.add_argument('--share', action='store_true', help='Create a public share link')
    args = parser.parse_args()
    
    # Create and launch the UI
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",  # Listen on all network interfaces
        server_port=args.port,
        share=args.share,
        inbrowser=False,        # Don't automatically open browser
        quiet=False,            # Show access URLs in terminal
        favicon_path=None,
        ssl_verify=False,       # Allows connections over HTTP
        show_error=True,        # Show detailed error messages
        debug=True              # Turn on debugging for more info
    )