# Standard library imports
import os
import logging
from datetime import datetime
import platform

# Third-party imports
import gurobipy as gp
from gurobipy import GRB
import pandas as pd

# Local imports
from load import ScheduleDataLoader
import greedy  # Import the greedy module

class ScheduleOptimizer:
    def __init__(self):
        """Initialize the scheduler using the existing data loader"""
        # Set up logging
        self.setup_logging()
        
        # Use the existing data loader
        loader = ScheduleDataLoader()
        self.data = loader.load_all()
        
        # Extract data from loader
        self.students = self.data['students']
        self.student_preferences = self.data['student_preferences']
        self.teachers = self.data['teachers']
        self.sections = self.data['sections']
        self.teacher_unavailability = self.data['teacher_unavailability']
        
        # Define periods
        self.periods = ['R1', 'R2', 'R3', 'R4', 'G1', 'G2', 'G3', 'G4']
        
        # Define course period restrictions once
        self.course_period_restrictions = {
            'Medical Career': ['R1', 'G1'],
            'Heroes Teach': ['R2', 'G2']
        }
        
        # Create course to sections mapping
        self.course_to_sections = {}
        for _, row in self.sections.iterrows():
            if row['Course ID'] not in self.course_to_sections:
                self.course_to_sections[row['Course ID']] = []
            self.course_to_sections[row['Course ID']].append(row['Section ID'])
        
        # Initialize the Gurobi model
        self.model = gp.Model("School_Scheduling")
        
        self.logger.info("Initialization complete")
    
    def get_allowed_periods(self, course_id):
        """Get allowed periods for a course based on restrictions"""
        return self.course_period_restrictions.get(course_id, self.periods)

    def setup_logging(self):
        """Set up logging configuration"""
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)
        
        log_filename = os.path.join(output_dir, f'gurobi_scheduling_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def create_variables(self):
        """Create decision variables for the model"""
        # x[i,j] = 1 if student i is assigned to section j
        self.x = {}
        for _, student in self.students.iterrows():
            student_id = student['Student ID']
            prefs = self.student_preferences[
                self.student_preferences['Student ID'] == student_id
            ]['Preferred Sections'].iloc[0].split(';')
            
            for course_id in prefs:
                if course_id in self.course_to_sections:
                    for section_id in self.course_to_sections[course_id]:
                        self.x[student_id, section_id] = self.model.addVar(
                            vtype=GRB.BINARY,
                            name=f'x_{student_id}_{section_id}'
                        )

        # z[j,p] = 1 if section j is scheduled in period p
        self.z = {}
        for _, section in self.sections.iterrows():
            section_id = section['Section ID']
            course_id = section['Course ID']
            
            # Use centralized method for period restrictions
            allowed_periods = self.get_allowed_periods(course_id)
                
            for period in allowed_periods:
                self.z[section_id, period] = self.model.addVar(
                    vtype=GRB.BINARY,
                    name=f'z_{section_id}_{period}'
                )

        # y[i,j,p] = 1 if student i is assigned to section j in period p
        self.y = {}
        for (student_id, section_id), x_var in self.x.items():
            for period in self.periods:
                if (section_id, period) in self.z:
                    self.y[student_id, section_id, period] = self.model.addVar(
                        vtype=GRB.BINARY,
                        name=f'y_{student_id}_{section_id}_{period}'
                    )

        self.model.update()
        self.logger.info("Variables created successfully")

    def add_constraints(self):
        """Add all necessary constraints to the model"""
        
        # 1. Each section must be scheduled in exactly one period
        for section_id in self.sections['Section ID']:
            valid_periods = [p for p in self.periods if (section_id, p) in self.z]
            if valid_periods:
                self.model.addConstr(
                    gp.quicksum(self.z[section_id, p] for p in valid_periods) == 1,
                    name=f'one_period_{section_id}'
                )

        # 2. Section capacity constraints
        for _, section in self.sections.iterrows():
            section_id = section['Section ID']
            capacity = section['# of Seats Available']
            self.model.addConstr(
                gp.quicksum(self.x[student_id, section_id] 
                           for student_id in self.students['Student ID']
                           if (student_id, section_id) in self.x) <= capacity,
                name=f'capacity_{section_id}'
            )

        # 3. Student course requirements
        for _, student in self.students.iterrows():
            student_id = student['Student ID']
            requested_courses = self.student_preferences[
                self.student_preferences['Student ID'] == student_id
            ]['Preferred Sections'].iloc[0].split(';')
            
            for course_id in requested_courses:
                if course_id in self.course_to_sections:
                    self.model.addConstr(
                        gp.quicksum(self.x[student_id, section_id]
                                  for section_id in self.course_to_sections[course_id]
                                  if (student_id, section_id) in self.x) == 1,
                        name=f'course_requirement_{student_id}_{course_id}'
                    )

        # 4. Teacher conflicts - no teacher can teach multiple sections in same period
        for _, teacher in self.teachers.iterrows():
            teacher_id = teacher['Teacher ID']
            teacher_sections = self.sections[
                self.sections['Teacher Assigned'] == teacher_id
            ]['Section ID']
            
            for period in self.periods:
                self.model.addConstr(
                    gp.quicksum(self.z[section_id, period]
                               for section_id in teacher_sections
                               if (section_id, period) in self.z) <= 1,
                    name=f'teacher_conflict_{teacher_id}_{period}'
                )

        # 5. Student period conflicts
        for student_id in self.students['Student ID']:
            for period in self.periods:
                self.model.addConstr(
                    gp.quicksum(self.y[student_id, section_id, period]
                               for section_id in self.sections['Section ID']
                               if (student_id, section_id, period) in self.y) <= 1,
                    name=f'student_period_conflict_{student_id}_{period}'
                )

        # 6. Linking constraints between x, y, and z variables
        for (student_id, section_id, period), y_var in self.y.items():
            self.model.addConstr(
                y_var <= self.x[student_id, section_id],
                name=f'link_xy_{student_id}_{section_id}_{period}'
            )
            self.model.addConstr(
                y_var <= self.z[section_id, period],
                name=f'link_yz_{student_id}_{section_id}_{period}'
            )
            self.model.addConstr(
                y_var >= self.x[student_id, section_id] + self.z[section_id, period] - 1,
                name=f'link_xyz_{student_id}_{section_id}_{period}'
            )

        # 7. SPED student distribution constraint (soft)
        sped_students = self.students[self.students['SPED'] == 1]['Student ID']
        for section_id in self.sections['Section ID']:
            self.model.addConstr(
                gp.quicksum(self.x[student_id, section_id]
                           for student_id in sped_students
                           if (student_id, section_id) in self.x) <= 12,
                name=f'sped_distribution_{section_id}'
            )

        self.logger.info("Constraints added successfully")

    def set_objective(self):
        """Set the objective function to maximize student satisfaction"""
        # Primary objective: maximize the number of satisfied course requests
        satisfaction = gp.quicksum(self.x[student_id, section_id]
                                 for (student_id, section_id) in self.x)
        
        self.model.setObjective(satisfaction, GRB.MAXIMIZE)
        self.logger.info("Objective function set successfully")

    def greedy_initial_solution(self):
        """Generate a feasible initial solution using the advanced greedy algorithm"""
        self.logger.info("Generating initial solution using advanced greedy algorithm...")
        
        try:
            # Format data for greedy algorithm
            student_data = self.students
            student_pref_data = self.student_preferences
            section_data = self.sections
            periods = self.periods
            teacher_unavailability = self.teacher_unavailability
            
            # Call the greedy algorithm from greedy.py
            x_vars, z_vars, y_vars = greedy.greedy_initial_solution(
                student_data, student_pref_data, section_data, periods, teacher_unavailability
            )
            
            self.logger.info(f"Greedy algorithm generated initial values for: {len(x_vars)} x vars, "
                            f"{len(z_vars)} z vars, {len(y_vars)} y vars")
            
            # Set start values for Gurobi variables
            # Set x variables
            for (student_id, section_id), value in x_vars.items():
                if (student_id, section_id) in self.x:
                    self.x[student_id, section_id].start = value
            
            # Set z variables
            for (section_id, period), value in z_vars.items():
                if (section_id, period) in self.z:
                    self.z[section_id, period].start = value
            
            # Set y variables
            for (student_id, section_id, period), value in y_vars.items():
                if (student_id, section_id, period) in self.y:
                    self.y[student_id, section_id, period].start = value
            
            # Calculate solution quality metrics
            assigned_students = sum(1 for (_, _), val in x_vars.items() if val > 0.5)
            total_students = len(self.students)
            assigned_sections = len(set(section_id for (_, section_id), val in x_vars.items() if val > 0.5))
            total_sections = len(self.sections)
            
            self.logger.info(f"Initial solution: {assigned_students}/{total_students} students assigned, "
                            f"{assigned_sections}/{total_sections} sections used")
            
            # Set the MIPFocus parameter to use the initial solution effectively
            self.model.setParam('MIPFocus', 1)  # Focus on finding good feasible solutions
            
        except Exception as e:
            self.logger.error(f"Error generating initial solution: {str(e)}")
            self.logger.warning("Falling back to simple greedy algorithm")
            self._simple_greedy_initial_solution()
        
    def _simple_greedy_initial_solution(self):
        """Original simple greedy algorithm as fallback"""
        # Initialize capacity tracking
        section_capacity = self.sections.set_index('Section ID')['# of Seats Available'].to_dict()
        
        # Initialize assignments
        student_assignments = {}
        section_periods = {}
        
        # Assign students to sections based on preferences
        for _, student in self.students.iterrows():
            student_id = student['Student ID']
            prefs = self.student_preferences[
                self.student_preferences['Student ID'] == student_id
            ]['Preferred Sections'].iloc[0].split(';')
            
            for course_id in prefs:
                if (course_id in self.course_to_sections) and (student_id not in student_assignments):
                    for section_id in self.course_to_sections[course_id]:
                        if section_capacity[section_id] > 0:
                            student_assignments[student_id] = section_id
                            section_capacity[section_id] -= 1
                            break
        
        # Assign sections to periods
        for _, section in self.sections.iterrows():
            section_id = section['Section ID']
            course_id = section['Course ID']
            
            # Use centralized method for period restrictions
            allowed_periods = self.get_allowed_periods(course_id)
            
            for period in allowed_periods:
                if (section_id, period) in self.z:
                    section_periods[section_id] = period
                    break
        
        # Set start values for decision variables
        for (student_id, section_id), x_var in self.x.items():
            if student_assignments.get(student_id) == section_id:
                x_var.start = 1
            else:
                x_var.start = 0
        
        for (section_id, period), z_var in self.z.items():
            if section_periods.get(section_id) == period:
                z_var.start = 1
            else:
                z_var.start = 0
        
        for (student_id, section_id, period), y_var in self.y.items():
            if student_assignments.get(student_id) == section_id and section_periods.get(section_id) == period:
                y_var.start = 1
            else:
                y_var.start = 0
        
        self.logger.info("Simple greedy initial solution generated successfully")

    def solve(self):
        """Solve the optimization model to find a solution in the top 10%"""
        try:
            # Calculate upper bound on objective (total course requests)
            total_requests = 0
            for _, student in self.students.iterrows():
                student_id = student['Student ID']
                requested_courses = self.student_preferences[
                    self.student_preferences['Student ID'] == student_id
                ]['Preferred Sections'].iloc[0].split(';')
                total_requests += len(requested_courses)
            
            # Get system memory information
            import psutil
            total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)  # RAM in GB
            self.logger.info(f"System has {total_ram_gb:.1f} GB of RAM available")
            
            # Calculate memory to use - allow up to 90% of system RAM for large systems
            if total_ram_gb > 300:  # For very large memory systems (like 384GB)
                mem_limit_gb = int(total_ram_gb * 0.90)  # Use up to 90%
                node_file_start = 0.95  # Start writing to disk at 95% memory usage
            elif total_ram_gb > 100:  # For medium-large systems
                mem_limit_gb = int(total_ram_gb * 0.80)  # Use up to 80%
                node_file_start = 0.85  # Start writing to disk at 85% memory usage
            else:  # For smaller systems
                mem_limit_gb = int(total_ram_gb * 0.70)  # Use up to 70%
                node_file_start = 0.75  # Start writing to disk at 75% memory usage
            
            # Set memory limit - convert GB to MB
            self.model.setParam('MemLimit', mem_limit_gb * 1024)
            self.logger.info(f"Set Gurobi memory limit to {mem_limit_gb} GB")
            
            # Set MIP gap tolerance to 10%
            self.model.setParam('MIPGap', 0.10)
            
            # Set shorter time limit since we don't need optimal
            self.model.setParam('TimeLimit', 7200)  # 2 hours
            
            # Set focus to finding feasible solutions quickly
            self.model.setParam('MIPFocus', 1)
            
            # Set presolve to aggressive
            self.model.setParam('Presolve', 2)
            
            # Start writing nodes to disk only at high memory usage
            self.model.setParam('NodefileStart', node_file_start)
            
            # Set the directory for node file offloading (Linux-compatible path)
            if platform.system() == 'Windows':
                node_dir = 'c:/path/to/fast/disk'
            else:
                # Use /tmp or a dedicated directory for node files
                node_dir = '/tmp/gurobi_nodefiles'
                os.makedirs(node_dir, exist_ok=True)
                
            self.model.setParam('NodefileDir', node_dir)
            self.logger.info(f"Using node file directory: {node_dir}")
            
            # Set aggressive parameters for large memory systems
            if total_ram_gb > 300:
                # Use in-memory computation as much as possible
                self.model.setParam('NodeMethod', 1)  # Dual simplex (more memory-intensive but faster)
                
                # Increase solution pool size to store more solutions in memory
                self.model.setParam('PoolSolutions', 10)
                self.model.setParam('PoolSearchMode', 2)
                
                # Set RINS heuristic - more aggressive with more memory
                self.model.setParam('RINS', 10)
                
                # Store more cuts in memory
                self.model.setParam('CutPasses', -1)  # automatic, aggressive
                
            # Determine optimal number of threads based on system
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            # For large memory systems, we can use more threads
            threads = min(cpu_count - 2, 64)  # Leave 2 cores free, max 64 threads
            self.model.setParam('Threads', threads)
            self.logger.info(f"Using {threads} threads out of {cpu_count} available cores")
            
            # Generate a greedy initial solution 
            # (Uses the new advanced greedy algorithm)
            self.greedy_initial_solution()
            
            self.logger.info(f"Starting optimization - accepting solutions within 10% of optimal")
            self.logger.info(f"Maximum possible satisfied requests: {total_requests}")
            
            self.model.optimize()
            
            if self.model.status == GRB.OPTIMAL:
                self.logger.info("Found solution within 10% of optimal")
                self.logger.info(f"Satisfied requests: {self.model.objVal} out of {total_requests}")
                self.logger.info(f"Satisfaction rate: {(self.model.objVal/total_requests)*100:.2f}%")
                self.save_solution()
            elif self.model.status == GRB.TIME_LIMIT:
                if (self.model.SolCount > 0):
                    self.logger.info("Time limit reached but found good solution")
                    self.logger.info(f"Satisfied requests: {self.model.objVal} out of {total_requests}")
                    self.logger.info(f"Satisfaction rate: {(self.model.objVal/total_requests)*100:.2f}%")
                    self.save_solution()
                else:
                    self.logger.error("No solution found within time limit")
            else:
                self.logger.error(f"Optimization failed with status {self.model.status}")
                
        except gp.GurobiError as e:
            self.logger.error(f"Gurobi error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error during optimization: {str(e)}")
            raise

    def save_solution(self):
        """Save the solution to CSV files"""
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)

        # Save section schedule
        section_schedule = []
        for (section_id, period), z_var in self.z.items():
            if z_var.X > 0.5:
                section_schedule.append({
                    'Section ID': section_id,
                    'Period': period
                })
        pd.DataFrame(section_schedule).to_csv(
            os.path.join(output_dir, 'Master_Schedule.csv'),
            index=False
        )

        # Save student assignments
        student_assignments = []
        for (student_id, section_id), x_var in self.x.items():
            if x_var.X > 0.5:
                student_assignments.append({
                    'Student ID': student_id,
                    'Section ID': section_id
                })
        pd.DataFrame(student_assignments).to_csv(
            os.path.join(output_dir, 'Student_Assignments.csv'),
            index=False
        )

        # Save teacher schedule
        teacher_schedule = []
        for (section_id, period), z_var in self.z.items():
            if z_var.X > 0.5:
                teacher_id = self.sections[
                    self.sections['Section ID'] == section_id
                ]['Teacher Assigned'].iloc[0]
                teacher_schedule.append({
                    'Teacher ID': teacher_id,
                    'Section ID': section_id,
                    'Period': period
                })
        pd.DataFrame(teacher_schedule).to_csv(
            os.path.join(output_dir, 'Teacher_Schedule.csv'),
            index=False
        )

        self.logger.info("Solution saved successfully")

if __name__ == "__main__":
    try:
        optimizer = ScheduleOptimizer()
        optimizer.create_variables()
        optimizer.add_constraints()
        optimizer.set_objective()
        optimizer.solve()
    except KeyboardInterrupt:
        logging.info("Optimization interrupted by user")
    except Exception as e:
        logging.error(f"Error running optimization: {str(e)}")
        raise