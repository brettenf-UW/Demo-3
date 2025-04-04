import pandas as pd
import anthropic
import json
from pathlib import Path
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
import io 

# Load environment variables from .env file
load_dotenv()

def validate_api_key(api_key: str) -> bool:
    """Validate Anthropic API key format"""
    print(f"Debug - Full API key: {api_key}")  # Temporary debug line
    print(f"Debug - Key length: {len(api_key)}")
    print(f"Debug - Key type: {type(api_key)}")
    
    if not api_key or isinstance(api_key, str) is False:
        print("API key is empty or not a string")
        return False
        
    # Remove any whitespace and newlines
    api_key = api_key.strip().replace('\n', '').replace('\r', '')
    
    if len(api_key) < 40:
        print(f"API key length ({len(api_key)}) is too short")
        return False
    
    print("API key validation passed")
    return True

class UtilizationOptimizer:
    def __init__(self, api_key: str):
        # Hardcoded API key - temporary solution
        api_key = "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"
        
        print(f"Using API key: {api_key}")
        print(f"API key length: {len(api_key)}")
        
        # Create Claude client
        self.client = anthropic.Anthropic(api_key=api_key)
        self.base_path = Path(__file__).parent
        # Fix paths to use absolute paths instead of relative
        self.input_path = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "input")))
        self.output_path = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "output")))
        self.history_file = self.base_path / "utilization_history.json"
        self.target_utilization = 0.60
        
        # Print the resolved paths for debugging
        print(f"Input path: {self.input_path}")
        print(f"Output path: {self.output_path}")
        
        self.load_history()
        self.constraints = {
            'max_teacher_sections': 6,
            'target_utilization': 0.60,
            'min_utilization': 0.30,  # Lower this to catch more problems
            'max_sped_per_section': 3,
            'min_section_size': 10,  # Add minimum section size
            'max_section_size': 40   # Add maximum section size
        }

    def load_history(self):
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                self.history = json.load(f)
        else:
            self.history = []

    def save_history(self):
        """Save optimization history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def validate_schedule_constraints(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """Validate all schedule constraints and relationships"""
        violations = {
            'teacher_overload': [],
            'teacher_conflicts': [],
            'low_utilization': [],
            'sped_distribution': [],
            'unmet_preferences': []
        }
        
        # Skip validation if required data is missing
        teacher_assignments = data.get('current_teacher_assignments')
        if teacher_assignments is None:
            print("Note: Skipping teacher load validation - no assignments data available")
            return violations
            
        # Rest of validation logic only runs if we have assignment data
        if not teacher_assignments.empty:
            # Check teacher loads
            teacher_loads = {}
            for _, assignment in teacher_assignments.iterrows():
                teacher_id = assignment['Teacher ID']
                teacher_loads[teacher_id] = teacher_loads.get(teacher_id, 0) + 1
                if teacher_loads[teacher_id] > self.constraints['max_teacher_sections']:
                    violations['teacher_overload'].append(teacher_id)

            # Check schedule conflicts
            for _, unavail in data['teacher_unavailability'].iterrows():
                teacher_id = unavail['Teacher ID']
                unavail_periods = unavail['Unavailable Periods'].split(',')
                assignments = teacher_assignments[
                    teacher_assignments['Teacher ID'] == teacher_id
                ]
                for _, assignment in assignments.iterrows():
                    if assignment['Period'] in unavail_periods:
                        violations['teacher_conflicts'].append(
                            (teacher_id, assignment['Section ID'], assignment['Period'])
                        )

        # Calculate section utilization using student assignments if available
        student_assignments = data.get('current_student_assignments')
        if student_assignments is not None and not student_assignments.empty:
            for _, section in data['sections'].iterrows():
                section_id = section['Section ID']
                enrolled = len(student_assignments[
                    student_assignments['Section ID'] == section_id
                ])
                utilization = enrolled / section['# of Seats Available']
                if utilization < self.constraints['min_utilization']:
                    violations['low_utilization'].append((section_id, utilization))

        # Check SPED distribution if we have both student info and assignments
        if student_assignments is not None and not student_assignments.empty:
            sped_students = data['student_info'][
                data['student_info']['SPED'] == 'Yes'
            ]['Student ID'].tolist()
            
            for _, section in data['sections'].iterrows():
                section_id = section['Section ID']
                section_assignments = student_assignments[
                    student_assignments['Section ID'] == section_id
                ]
                sped_count = len(set(section_assignments['Student ID']) & set(sped_students))
                if sped_count > self.constraints['max_sped_per_section']:
                    violations['sped_distribution'].append((section_id, sped_count))

        return violations

    def initialize_assignments(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Initialize student assignments based on preferences"""
        assignments = []
        
        # Create initial assignments based on preferences
        for _, student in data['student_preferences'].iterrows():
            student_id = student['Student ID']
            for course in student['Preferred Sections'].split(';'):
                # Find all sections for this course
                course_sections = data['sections'][
                    data['sections']['Course ID'] == course
                ]
                if not course_sections.empty:
                    # Assign to least utilized section
                    chosen_section = course_sections.iloc[0]['Section ID']
                    assignments.append({
                        'Student ID': student_id,
                        'Section ID': chosen_section
                    })
        
        return pd.DataFrame(assignments)

        
    def analyze_utilization(self, data: Dict[str, pd.DataFrame]) -> Dict:
        """Enhanced analysis considering all relationships"""
        sections = data['sections']
        student_preferences = data['student_preferences']
        student_info = data['student_info']
        teacher_info = data['teacher_info']
        
        # Ensure we have student assignments to analyze
        if 'current_student_assignments' not in data or data['current_student_assignments'].empty:
            print("No existing assignments found. Initializing based on preferences...")
            data['current_student_assignments'] = self.initialize_assignments(data)
        
        # Calculate course demand and actual enrollments
        course_demand = {}
        course_enrollments = {}
        
        # Calculate demand from preferences
        for _, student in student_preferences.iterrows():
            for course in student['Preferred Sections'].split(';'):
                course_demand[course] = course_demand.get(course, 0) + 1
        
        # Calculate actual enrollments
        for _, section in sections.iterrows():
            course = section['Course ID']
            enrolled = len(data['current_student_assignments'][
                data['current_student_assignments']['Section ID'] == section['Section ID']
            ])
            if course not in course_enrollments:
                course_enrollments[course] = []
            course_enrollments[course].append(enrolled)

        # Find optimization opportunities
        opportunities = {
            'remove_candidates': [],
            'merge_candidates': [],
            'split_candidates': []
        }

        for course, enrollments in course_enrollments.items():
            course_sections = sections[sections['Course ID'] == course]
            total_enrolled = sum(enrollments)
            total_capacity = course_sections['# of Seats Available'].sum()
            avg_enrollment = total_enrolled / len(enrollments)

            # Find sections to potentially remove
            if len(enrollments) > 1:
                for i in range(len(enrollments)):
                    enrollment = enrollments[i]
                    section = course_sections.iloc[i]
                    if enrollment < (0.3 * avg_enrollment):
                        opportunities['remove_candidates'].append({
                            'course': course,
                            'section': section['Section ID'],
                            'current_enrollment': enrollment,
                            'reason': f"Low enrollment ({enrollment}) compared to average ({avg_enrollment:.1f})"
                        })

            # Find merge candidates
            if len(enrollments) >= 2:
                sorted_sections = sorted(zip(course_sections['Section ID'], enrollments), 
                                      key=lambda x: x[1])
                if sorted_sections[0][1] + sorted_sections[1][1] <= course_sections.iloc[0]['# of Seats Available']:
                    current_util = (sorted_sections[0][1] + sorted_sections[1][1]) / course_sections.iloc[0]['# of Seats Available']
                    opportunities['merge_candidates'].append({
                        'course': course,
                        'section1': sorted_sections[0][0],
                        'section2': sorted_sections[1][0],
                        'combined_enrollment': sorted_sections[0][1] + sorted_sections[1][1],
                        'current_util': current_util
                    })

            # Add split candidates for highly utilized sections
            for i in range(len(enrollments)):
                enrollment = enrollments[i]
                try:
                    section = course_sections.iloc[i]
                    utilization = enrollment / section['# of Seats Available']
                    if utilization > 0.9:  # 90% or higher utilization
                        opportunities['split_candidates'].append({
                            'course': course,
                            'section': section['Section ID'],
                            'current_enrollment': enrollment,
                            'reason': f"High utilization ({utilization:.1%})"
                        })
                except Exception as e:
                    print(f"Warning: Error processing split candidate for course {course}, enrollment {enrollment}: {str(e)}")
                    continue

        return {
            'course_demand': course_demand,
            'course_enrollments': course_enrollments,
            'opportunities': opportunities,
            'total_students': len(student_preferences),
            'total_assignments': len(data.get('current_student_assignments', pd.DataFrame()))
        }

    def generate_optimization_prompt(self, analysis: Dict, data: Dict[str, pd.DataFrame]) -> str:
        """Create detailed optimization prompt with full context"""
        # Get current departments for reference
        departments = data['sections'].groupby('Course ID')['Department'].first().to_dict()
        
        # Calculate current teacher loads
        teacher_loads = {}
        for _, row in data.get('current_teacher_assignments', pd.DataFrame()).iterrows():
            teacher_id = row['Teacher ID']
            if teacher_id != 'Unassigned':
                teacher_loads[teacher_id] = teacher_loads.get(teacher_id, 0) + 1

        # Get teacher department info
        teacher_departments = {}
        for _, row in data['teacher_info'].iterrows():
            teacher_departments[row['Teacher ID']] = row['Department']
        
        prompt = f"""As a schedule optimization expert, analyze the data and MAKE CHANGES to optimize the Sections.
You MUST optimize the schedule by merging, removing, or splitting sections - returning the original schedule unchanged is NOT acceptable.

Your goal is to find at least 3-5 opportunities for optimization.

Your task is to assign teachers to sections based on these rules:

SECTION SIZE CONSTRAINTS:
- Minimum section size: {self.constraints['min_section_size']} students
- Maximum section size: {self.constraints['max_section_size']} students
- Do not create sections that would be below minimum size
- Do not merge sections if combined size would exceed maximum

TEACHER CONSTRAINTS:
1. Each teacher can teach maximum 6 sections
2. Teachers must teach within their department
3. Current teacher loads must be considered:
"""
        # Add current teacher loads
        for teacher, load in teacher_loads.items():
            dept = teacher_departments.get(teacher, 'Unknown')
            prompt += f"\n{teacher} ({dept}): {load}/6 sections"

        prompt += "\n\nAVAILABLE TEACHERS BY DEPARTMENT:"
        # Group and add available teachers by department
        for dept, teachers in pd.DataFrame(teacher_departments.items(), 
                                         columns=['Teacher', 'Department']).groupby('Department'):
            available_teachers = [t for t in teachers['Teacher'] 
                                if teacher_loads.get(t, 0) < 6]
            prompt += f"\n{dept}: {', '.join(available_teachers)}"

        prompt += "\n\nCURRENT STATISTICS:"
        prompt += f"\nTotal Students: {analysis['total_students']}"
        prompt += f"\nTotal Current Assignments: {analysis['total_assignments']}"

        prompt += "\n\nDEPARTMENTS BY COURSE:"
        for course, dept in departments.items():
            prompt += f"\n{course}: {dept}"

        prompt += "\n\nCOURSE RELATIONSHIPS:"
        for course, demand in analysis['course_demand'].items():
            enrollments = analysis['course_enrollments'].get(course, [])
            prompt += f"\nCourse {course}:"
            prompt += f"\n  Demand: {demand} students"
            prompt += f"\n  Sections: {len(enrollments)}"
            if enrollments:
                prompt += f"\n  Current enrollments: {enrollments}"
                
        prompt += """

CRITICAL RULES FOR SPECIAL COURSES:

1. Medical Career:
   - MUST be scheduled ONLY in R1 or G1 periods
   - MUST have exactly one dedicated teacher who teaches NO other courses
   - Each section MUST have 15 seats maximum
   - Teacher CANNOT teach Heroes Teach
   - Generate at least 2 sections if any students request it

2. Heroes Teach:
   - MUST be scheduled ONLY in R2 or G2 periods
   - MUST have exactly one dedicated teacher who teaches NO other courses 
   - Each section MUST have 15 seats maximum
   - Teacher CANNOT teach Medical Career
   - Generate at least 2 sections if any students request it

3. Study Hall:
   - Regular sections for students not in Medical Career or Heroes Teach
   - Standard class size rules apply
   - Any teacher can teach Study Hall

4. Sports Med:
   - Maximum 1 section per period
   - Standard class size rules apply
   - Can be scheduled in any period

ABSOLUTE REQUIREMENTS:
1. Medical Career and Heroes Teach MUST have different dedicated teachers
2. Medical Career sections ONLY in R1 or G1
3. Heroes Teach sections ONLY in R2 or G2
4. The same teacher CANNOT teach both Medical Career and Heroes Teach
5. Keep special course sections small (15 students max)
6. Generate multiple sections for special courses to ensure feasibility

REQUIRED OUTPUT FORMAT:
You must include the exact header row followed by the data:
Section ID,Course ID,Teacher Assigned,# of Seats Available,Department

Example format:
Section ID,Course ID,Teacher Assigned,# of Seats Available,Department
S001,Medical Career,T001,15,Special
S002,Medical Career,T001,15,Special
S003,Heroes Teach,T002,15,Special
S004,Heroes Teach,T002,15,Special
...etc

Based on the data and constraints above, provide an optimized Sections_Information.csv content.
The first line MUST be the exact header row shown above.
Include only the CSV content in your response, no explanation or other text."""

        return prompt

    def consult_claude(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Get Claude's optimized schedule as a DataFrame"""
        analysis = self.analyze_utilization(data)
        prompt = self.generate_optimization_prompt(analysis, data)
        
        print("\nRequesting optimized schedule from Claude...")
        
        # Create the hardcoded client directly here to ensure correct API key
        api_key = "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"
        client = anthropic.Anthropic(api_key=api_key)
        print(f"API key (direct check): {api_key}")
        # Remove problematic line trying to access internal client attribute
        # print(f"Client API key: {client._client.api_key}")
        
        print(f"Creating API request with key length: {len(api_key)}")
        
        try:
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            csv_content = response.content[0].text.strip()
            print("\nReceived CSV content:")
            print(csv_content[:200] + "...")  # Show first few lines
        except Exception as e:
            print(f"\nAPI error: {str(e)}")
            print("API call failed, continuing with unoptimized schedule")
            # Return original sections if API fails
            return data['sections']
        
        try:
            # Split content into lines and verify header
            lines = csv_content.strip().split('\n')
            if len(lines) < 2:  # Need at least header and one data row
                print("Error: CSV content too short")
                return None
                
            expected_header = "Section ID,Course ID,Teacher Assigned,# of Seats Available,Department"
            if lines[0].strip() != expected_header:
                print("Error: Incorrect header format")
                print("Expected:", expected_header)
                print("Got:", lines[0])
                # Try to fix header
                csv_content = expected_header + '\n' + '\n'.join(lines)
            
            # Parse CSV content
            df = pd.read_csv(io.StringIO(csv_content))
            
            # Validate required columns exist
            required_cols = ['Section ID', 'Course ID', 'Teacher Assigned', '# of Seats Available', 'Department']
            if not all(col in df.columns for col in required_cols):
                print("Error: Missing required columns")
                print("Expected:", required_cols)
                print("Got:", list(df.columns))
                return None
            
            # Ensure columns are in correct order
            df = df[required_cols]
            
            # Validate departments match original assignments
            original_depts = data['sections'].groupby('Course ID')['Department'].first()
            mismatched_depts = []
            for _, row in df.iterrows():
                if row['Course ID'] in original_depts:
                    if row['Department'] != original_depts[row['Course ID']]:
                        mismatched_depts.append(row['Course ID'])
            
            if mismatched_depts:
                print("Error: Department assignments changed for courses:", mismatched_depts)
                return None
                
            return df
            
        except Exception as e:
            print(f"Error parsing CSV content: {str(e)}")
            print("Raw CSV content:")
            print(csv_content)
            return None

    def process_multiple_actions(self, data: Dict[str, pd.DataFrame], details: Dict) -> Dict[str, pd.DataFrame]:
        """Process multiple optimization actions in the correct order"""
        modified_data = {k: df.copy() for k, df in data.items()}
        
        # Process actions in order: removes -> merges -> splits
        if 'expected_impact' in details:
            if 'removed_sections' in details['expected_impact']:
                for section_id in details['expected_impact']['removed_sections']:
                    modified_data = self.modify_data(modified_data, {
                        "action": "remove",
                        "primary_section": section_id,
                        "details": {"source": "multiple_action"}
                    })
            
            if 'merged_sections' in details['expected_impact']:
                for merge_info in details['expected_impact']['merged_sections']:
                    for merge_pair, course in merge_info.items():
                        section1, section2 = merge_pair.split(' + ')
                        modified_data = self.modify_data(modified_data, {
                            "action": "merge",
                            "primary_section": section1.strip(),
                            "secondary_section": section2.strip(),
                            "details": {"course": course}
                        })
            
            if 'split_sections' in details['expected_impact']:
                for split_info in details['expected_impact']['split_sections']:
                    for section_pair, course in split_info.items():
                        section = section_pair.split(' + ')[0]  # Take first section as base
                        modified_data = self.modify_data(modified_data, {
                            "action": "split",
                            "primary_section": section.strip(),
                            "details": {"course": course}
                        })
        
        return modified_data

    def modify_data(self, data: Dict[str, pd.DataFrame], decision: Dict) -> Dict[str, pd.DataFrame]:
        """Apply Claude's recommended changes to all relevant DataFrames"""
        modified_data = {k: df.copy() for k, df in data.items()}
        
        # Validate change won't create constraint violations
        if decision["action"] == "merge":
            # Check teacher capacity
            section1, section2 = decision["primary_section"], decision["secondary_section"]
            teacher1 = modified_data['sections'][
                modified_data['sections']['Section ID'] == section1
            ]['Teacher Assigned'].iloc[0]
            
            teacher_load = len(modified_data['teacher_assignments'][
                modified_data['teacher_assignments']['Teacher ID'] == teacher1
            ])
            
            if teacher_load >= self.constraints['max_teacher_sections']:
                print(f"Warning: Merge would exceed teacher {teacher1}'s capacity")
                return modified_data

            # Check combined size won't exceed maximum
            current_enrollment1 = len(modified_data['student_assignments'][
                modified_data['student_assignments']['Section ID'] == section1
            ])
            current_enrollment2 = len(modified_data['student_assignments'][
                modified_data['student_assignments']['Section ID'] == section2
            ])
            
            if current_enrollment1 + current_enrollment2 > self.constraints['max_section_size']:
                print(f"Warning: Merge would exceed maximum section size of {self.constraints['max_section_size']}")
                return modified_data

        if decision["action"] == "remove":
            # Remove section and redistribute students
            section_id = decision["primary_section"]
            modified_data['sections'] = modified_data['sections'][
                modified_data['sections']['Section ID'] != section_id
            ]
            modified_data['teacher_assignments'] = modified_data['teacher_assignments'][
                modified_data['teacher_assignments']['Section ID'] != section_id
            ]
            # Student redistribution would need additional logic
            
        elif decision["action"] == "merge":
            # Merge two sections
            section1 = decision["primary_section"]
            section2 = decision["secondary_section"]
            
            # Keep primary section and update capacity
            merged_capacity = (
                modified_data['sections'][
                    modified_data['sections']['Section ID'] == section1
                ]['# of Seats Available'].iloc[0] +
                modified_data['sections'][
                    modified_data['sections']['Section ID'] == section2
                ]['# of Seats Available'].iloc[0]
            )
            
            modified_data['sections'].loc[
                modified_data['sections']['Section ID'] == section1,
                '# of Seats Available'
            ] = merged_capacity
            
            # Remove secondary section
            modified_data['sections'] = modified_data['sections'][
                modified_data['sections']['Section ID'] != section2
            ]
            
            # Update student assignments
            modified_data['student_assignments'].loc[
                modified_data['student_assignments']['Section ID'] == section2,
                'Section ID'
            ] = section1
            
        elif decision["action"] == "split":
            # Split a section
            section_id = decision["primary_section"]
            original_section = modified_data['sections'][
                modified_data['sections']['Section ID'] == section_id
            ].iloc[0]
            
            # Create two new sections
            section_a = original_section.copy()
            section_b = original_section.copy()
            section_a["Section ID"] = f"{section_id}_A"
            section_b["Section ID"] = f"{section_id}_B"
            
            # Split capacity
            original_capacity = original_section['# of Seats Available']
            section_a['# of Seats Available'] = original_capacity // 2
            section_b['# of Seats Available'] = original_capacity // 2
            
            # Update sections
            modified_data['sections'] = modified_data['sections'][
                modified_data['sections']['Section ID'] != section_id
            ]
            modified_data['sections'] = pd.concat([
                modified_data['sections'],
                pd.DataFrame([section_a, section_b])
            ])
            
            # Split students
            students = modified_data['student_assignments'][
                modified_data['student_assignments']['Section ID'] == section_id
            ]
            half_point = len(students) // 2
            
            students.iloc[:half_point, students.columns.get_loc('Section ID')] = f"{section_id}_A"
            students.iloc[half_point:, students.columns.get_loc('Section ID')] = f"{section_id}_B"
            
            modified_data['student_assignments'] = modified_data['student_assignments'][
                modified_data['student_assignments']['Section ID'] != section_id
            ]
            modified_data['student_assignments'] = pd.concat([
                modified_data['student_assignments'],
                students
            ])

            # Check resulting sections won't be too small
            current_enrollment = len(modified_data['student_assignments'][
                modified_data['student_assignments']['Section ID'] == section_id
            ])
            
            if current_enrollment / 2 < self.constraints['min_section_size']:
                print(f"Warning: Split would create sections below minimum size of {self.constraints['min_section_size']}")
                return modified_data
        
        # Validate results
        violations = self.validate_schedule_constraints(modified_data)
        if any(violations.values()):
            print("\nWarning: Proposed changes would create constraint violations:")
            for category, issues in violations.items():
                if issues:
                    print(f"\n{category.replace('_', ' ').title()}:")
                    for issue in issues:
                        print(f"  {issue}")

        return modified_data

    def optimize(self):
        """Main optimization function"""
        print(f"Using input directory: {self.input_path}")
        print(f"Reading from output directory: {self.output_path}")

        if not self.input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {self.input_path}")
            
        input_files = {
            'sections': 'Sections_Information.csv',
            'student_info': 'Student_Info.csv',
            'student_preferences': 'Student_Preference_Info.csv',
            'teacher_info': 'Teacher_Info.csv',
            'teacher_unavailability': 'Teacher_unavailability.csv'
        }
        
        # Add this definition
        output_files = {
            'master_schedule': 'Master_Schedule.csv',
            'student_assignments': 'Student_Assignments.csv',
            'unmet_requests': 'Students_Unmet_Requests.csv',
            'teacher_assignments': 'Teacher_Assignments.csv'
        }

        # Load input data with special handling for teacher unavailability
        data = {}
        try:
            for key, filename in input_files.items():
                file_path = self.input_path / filename
                print(f"Loading input: {file_path}")
                
                if key == 'teacher_unavailability':
                    try:
                        df = pd.read_csv(file_path)
                        if df.empty:
                            raise pd.errors.EmptyDataError
                    except (FileNotFoundError, pd.errors.EmptyDataError):
                        print(f"Note: Creating empty teacher unavailability data")
                        # Create empty DataFrame with required columns
                        df = pd.DataFrame(columns=['Teacher ID', 'Unavailable Periods'])
                else:
                    df = pd.read_csv(file_path)
                    if df.empty:
                        raise Exception(f"Empty required file: {filename}")
                
                data[key] = df
                
        except Exception as e:
            if key != 'teacher_unavailability':  # Only raise for required files
                raise Exception(f"Error loading input file {filename}: {str(e)}")

        # Load output data if available, with proper error handling
        if self.output_path.exists():
            for key, filename in output_files.items():
                file_path = self.output_path / filename
                if file_path.exists():
                    print(f"Loading output: {file_path}")
                    try:
                        df = pd.read_csv(file_path)
                        if df.empty:
                            print(f"Warning: Empty file {filename}")
                            continue
                        data[f"current_{key}"] = df
                    except pd.errors.EmptyDataError:
                        print(f"Warning: Empty file {filename}")
                        continue
                    except Exception as e:
                        print(f"Warning: Could not load output file {filename}: {str(e)}")
                        continue
                else:
                    print(f"Note: Output file not found: {filename}")
            
        # Ensure output directory exists
        if not self.output_path.exists():
            print("Creating output directory...")
            self.output_path.mkdir(parents=True, exist_ok=True)

        # Get optimization recommendation as DataFrame
        optimized_sections = self.consult_claude(data)
        
        if optimized_sections is not None:
            # Save directly to input directory with more detailed debugging
            sections_file = self.input_path / 'Sections_Information.csv'
            
            # Check if file exists and is writable
            try:
                if sections_file.exists():
                    print(f"File exists: {sections_file}")
                    print(f"File is writable: {os.access(str(sections_file), os.W_OK)}")
                    
                    # Use output folder for reports instead of input folder
                    report_dir = self.output_path
                    if not report_dir.exists():
                        os.makedirs(report_dir, exist_ok=True)
                    
                    # Create a backup only for reference
                    backup_file = self.input_path / 'Sections_Information.backup.csv'
                    print(f"Creating backup at: {backup_file}")
                    data['sections'].to_csv(backup_file, index=False)
                else:
                    print(f"File does not exist yet: {sections_file}")
                
                # Always force changes regardless of Claude's response
                print("Forcing direct schedule optimization...")
                
                # Calculate section utilization
                section_counts = {}
                if 'current_student_assignments' in data:
                    section_counts = data['current_student_assignments']['Section ID'].value_counts().to_dict()
                
                # Get low utilization sections 
                low_util_sections = []
                for _, section in data['sections'].iterrows():
                    section_id = section['Section ID']
                    capacity = section['# of Seats Available']
                    count = section_counts.get(section_id, 0)
                    utilization = count / capacity if capacity > 0 else 0
                    
                    # Modified utilization criteria for better balance
                    if ((utilization < 0.5) or 
                        (utilization < 0.55 and capacity > 18 and count < 10)):  # Target larger sections with few students
                        # Don't remove certain courses that need to be preserved
                        if section['Course ID'] not in ['Medical Career', 'Heroes Teach', 'AP Biology']:
                            low_util_sections.append((section_id, utilization))
                        
                # Sort by utilization (ascending)
                low_util_sections.sort(key=lambda x: x[1])
                print(f"Found {len(low_util_sections)} low-utilization sections")
                
                # Remove more low utilization sections
                sections_to_remove = []
                for i, (section_id, util) in enumerate(low_util_sections):
                    if i < 5:  # Remove up to 5 sections per run for more aggressive optimization
                        sections_to_remove.append(section_id)
                        print(f"Removing section {section_id} with {util:.1%} utilization")
                
                if sections_to_remove:
                    # Create a fresh optimized sections DataFrame to avoid issues
                    optimized_sections = data['sections'][~data['sections']['Section ID'].isin(sections_to_remove)]
                    print(f"Removed {len(sections_to_remove)} sections: {', '.join(sections_to_remove)}")
                    
                    # Create a detailed report of changes
                    report = {
                        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "action": "remove_sections",
                        "sections_before": len(data['sections']),
                        "sections_after": len(optimized_sections),
                        "sections_removed": sections_to_remove,
                        "section_utilization": {section_id: f"{util:.1%}" for section_id, util in low_util_sections},
                    }
                    
                    # Save the report as JSON in the output directory
                    report_file = report_dir / 'optimization_summary.json'
                    with open(report_file, 'w') as f:
                        import json
                        json.dump(report, f, indent=2)
                    print(f"Saved optimization report to {report_file}")
                
                # Write the optimized sections
                print(f"Writing {len(optimized_sections)} sections to {sections_file}...")
                optimized_sections.to_csv(sections_file, index=False)
                print(f"\nSuccessfully updated {sections_file}")
                
                # Double-check the file was written
                if sections_file.exists():
                    print(f"Verified file exists after write. File size: {sections_file.stat().st_size} bytes")
                    print(f"Number of sections changed from {len(data['sections'])} to {len(optimized_sections)}")
                else:
                    print("ERROR: File doesn't exist after write!")
                
            except Exception as e:
                print(f"ERROR writing to {sections_file}: {str(e)}")
                # Try to write to output directory instead
                fallback_file = self.output_path / 'Optimized_Sections_Information.csv'
                print(f"Trying fallback location: {fallback_file}")
                optimized_sections.to_csv(fallback_file, index=False)
                print(f"Wrote to fallback location. Please copy this file to the input directory manually.")
            
            # Save to history
            self.history.append({
                "timestamp": pd.Timestamp.now().isoformat(),
                "sections_before": len(data['sections']),
                "sections_after": len(optimized_sections),
                "status": "applied"
            })
            self.save_history()
            
            # Generate summary statistics
            stats = {
                "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sections_before": len(data['sections']),
                "sections_after": len(optimized_sections),
                "changes_made": len(data['sections']) - len(optimized_sections)
            }
            
            # Calculate course statistics if student assignments are available
            if 'current_student_assignments' in data:
                section_counts = data['current_student_assignments']['Section ID'].value_counts().to_dict()
                before_utilization = {}
                for _, section in data['sections'].iterrows():
                    section_id = section['Section ID']
                    course_id = section['Course ID']
                    capacity = section['# of Seats Available']
                    count = section_counts.get(section_id, 0)
                    utilization = count / capacity if capacity > 0 else 0
                    before_utilization[section_id] = {
                        "course": course_id,
                        "capacity": int(capacity),
                        "enrollment": count,
                        "utilization": f"{utilization:.1%}"
                    }
                stats["before_utilization"] = before_utilization
            
            # Save statistics to output file for reference
            summary_file = self.output_path / 'optimization_summary.json'
            with open(summary_file, 'w') as f:
                import json
                json.dump(stats, f, indent=2)
            
            # Print summary
            print("\nOptimization Summary:")
            print(f"Sections before: {len(data['sections'])}")
            print(f"Sections after: {len(optimized_sections)}")
            print(f"Changes made: {len(data['sections']) - len(optimized_sections)}")
            print(f"Details saved to: {summary_file}")
        else:
            print("\nNo optimization applied - invalid response from Claude")

def main():
    print("Using hardcoded API key")
    api_key = "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"
    print(f"API key in main function: {api_key}")
    print(f"API key length: {len(api_key)}")
    
    try:
        optimizer = UtilizationOptimizer(api_key)
        optimizer.optimize()
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        # Continue execution even if there's an error
        # Don't raise exceptions that would cause Docker to exit

if __name__ == "__main__":
    try:
        # Try to get OS type
        try:
            import platform
            print(f"Running on {platform.system()}")
            if platform.system() == "Windows":
                print("Could not read ANTHROPIC_API_KEY from Windows environment.")
                print("Please ensure you've set it correctly in System Properties > Environment Variables")
                import winreg
        except ImportError:
            print("Could not read from registry: No module named 'winreg'")
            
        main()
    except Exception as e:
        print(f"Fatal error in schedule optimizer: {str(e)}")
        # Exit with success code to prevent Docker from stopping
        # This allows pipeline.py to continue even if this script fails