# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *
import warnings
import traceback
import part
import assembly
import regionToolset
import mesh
import section
import connectorBehavior
import math
import re

"""
Updated scissor bars script with corrected grandstand geometry:
- BarX: 7 rows always (ix=0-6), decreasing modules per row, NO BarX at top level
- BarZ: decreasing rows (6,5,4,3,2,1), always 6 modules per row, continues to top
- Density fixed as proper tuple format
"""

# --- 0) Basic Setup: Model & Parameters ---
model_name = 'Model-1'
connector_section_name = 'Pure_Hinge'
beam_section_name = 'RHS_48e3'
material_name = 'Steel_355'
profile_name = 'RHS_48e3_Profile'

# Updated Geometry Parameters (30 degree slope)
dx = 221    # spacing perpendicular to slope (x-direction)
dy = 127.5  # height increment per level (y-direction)  
dz = 221    # spacing along slope (z-direction)

# Grandstand dimensions
n_x = 6     # BarX: creates 7 rows (0-6), BarZ: creates max 6 rows (1-6) and 6 modules per row (0-5)
n_y = 5     # BarX: creates 5 levels (0-4), BarZ: creates 6 levels (0-5) including top
n_z_base = 5  # BarX: starting modules per row at ground level (5,4,3,2,1 decreasing)

# CSYS names for connector orientation
csys_X_name = 'Connector_Global_X_Orient'
csys_Z_name = 'Connector_Global_Z_Orient'

# Define overall success flag
overall_success = True

print(u"Grandstand: {} BarX rows x {} BarZ rows (tapering)".format(n_x+1, n_x))

# ====================================================================
# MAIN EXECUTION BLOCK (Sequential Steps)
# ====================================================================

# --- Access Model and Assembly ---
 
try:
    myModel = mdb.models[model_name]
    a = myModel.rootAssembly
except KeyError:
    print(u"FATAL ERROR: Model '{}' not found. Create it first or check name.".format(model_name))
    raise
except Exception as e:
    print(u"FATAL ERROR accessing model/assembly: {}".format(e))
    print(traceback.format_exc())
    raise
 

# --- Step 1: Define Material & Sections ---
print(u"\nStep 1: Define Material & Sections")
def create_nonlinear_steel(model, material_name):
    if material_name not in model.materials:
        print(u"  Creating material: {}".format(material_name))
        try:
            mat = model.Material(name=material_name)
            mat.Elastic(table=((2.1e11, 0.3),))  # Units: N/m2, nu
            mat.Density(table=((7850,),))  # kg/m3 - CORRECTED: Fixed tuple format
            mat.Plastic(table=((3.55e8, 0.0), (4e8, 0.05)))  # yield stress, plastic strain
            print(u"  Material '{}' created.".format(material_name))
        except Exception as e:
            warnings.warn(u"Failed to create material '{}': {}".format(material_name, e))
            print(traceback.format_exc())
            raise
    else:
        print(u" Material '{}' already exists.".format(material_name))

def create_pipe_section(model, profile_name, section_name, material_name):
    # Check/Create Profile
    if profile_name not in model.profiles:
        print(u"  Creating profile: {}".format(profile_name))
        try:
            model.PipeProfile(name=profile_name, r=0.02415, t=0.003)
            print(u" Profile '{}' created.".format(profile_name))
        except Exception as e:
            warnings.warn(u"Failed to create profile '{}': {}".format(profile_name, e))
            print(traceback.format_exc())
            raise
    else:
        print(u" Profile '{}' already exists.".format(profile_name))

    # Assign to a beam section
    if section_name not in model.sections:
        print(u" Creating section: {}".format(section_name))
        try:
            model.BeamSection(
                name=section_name,
                integration=DURING_ANALYSIS,
                profile=profile_name,
                material=material_name,
                poissonRatio=0.3
            )
            print(u"  Section '{}' created.".format(section_name))
        except Exception as e:
            warnings.warn("Failed to create section '{}': {}".format(section_name, e))
            print(traceback.format_exc())
            raise
    else:
        print(u" Section '{}' already exists.".format(section_name))

# Execute Step 1
create_nonlinear_steel(myModel, material_name)
create_pipe_section(myModel, profile_name, beam_section_name, material_name)
 

# --- Step 2: Create Parts ---
print("\nStep 2: Create Parts")

# Check if parts already exist (check one part as indicator)
first_part_name = "BarX-a"
if first_part_name in myModel.parts:
    print("  Part '{}' already exists. Skipping all part creation.".format(first_part_name))
    print("  Assuming all required parts exist...")
    # Still populate created_parts dict for later steps
    bar_part_definitions = [
        ("BarX-a", (0, 0, dz), (0, dy, 0)),
        ("BarX-b", (0, 0, 0),  (0, dy, dz)),
        ("BarZ-a", (0, 0, 0),  (dx, dy, 0)),
        ("BarZ-b", (dx, 0, 0), (0, dy, 0)),
    ]
    bar_part_names = [data[0] for data in bar_part_definitions]
    created_parts = {}
    for name, _, _ in bar_part_definitions:
        if name in myModel.parts:
            created_parts[name] = myModel.parts[name]
            print("  Found existing part: {}".format(name))
        else:
            warnings.warn("Expected part '{}' not found!".format(name))
else:
    print("  Creating new parts...")
    
    def create_bar(model_obj, part_name, start_point, end_point):
        print("  Attempting to create/access part: {}".format(part_name))
        if part_name in model_obj.parts:
            print("  Part '{}' already exists. Skipping creation.".format(part_name))
            return model_obj.parts[part_name]
        try:
            print("  Creating part: {}".format(part_name))
            p = model_obj.Part(name=part_name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
            p.WirePolyLine(points=(start_point, end_point), mergeType=IMPRINT, meshable=ON)

            # --- Partitioning (keeping your working logic) ---
            print("  Partitioning part '{}' into 4 equal segments...".format(part_name))
            try:
                if not p.edges:
                    raise ValueError("Part has no edges after WirePolyLine.")

                initial_edge = p.edges[0]
                
                # First partition at midpoint (creates vertex at 0.5)
                p.PartitionEdgeByParam(edges=(initial_edge,), parameter=0.5)
                
                # Partition first segment at 0.5 of its length (creates vertex at 0.25 of original)
                p.PartitionEdgeByParam(edges=(p.edges[0],), parameter=0.5)
                
                # Partition second segment at 0.5 of its length (creates vertex at 0.75 of original)
                if len(p.edges) > 2:
                    p.PartitionEdgeByParam(edges=(p.edges[2],), parameter=0.5)
                else:
                    warnings.warn("Could not perform the third partition on edges[2] for part '{}'.".format(part_name))

            except IndexError as e_idx:
                warnings.warn("Indexing error during partitioning of part '{}': {}".format(part_name, e_idx))
            except Exception as e_part:
                warnings.warn("Error during partitioning of part '{}': {}".format(part_name, e_part))
                print(traceback.format_exc())

            return p
        except Exception as e:
            warnings.warn("Failed to create/partition part '{}': {}".format(part_name, e))
            print(traceback.format_exc())
            raise

    # Updated Bar Definitions for Correct Geometry
    bar_part_definitions = [
        # BarX: spans yz plane, rotates around x-axis
        ("BarX-a", (0, 0, dz), (0, dy, 0)),    # From top-back to bottom-front
        ("BarX-b", (0, 0, 0),  (0, dy, dz)),   # From bottom-back to top-front
        
        # BarZ: spans xy plane, rotates around z-axis  
        ("BarZ-a", (0, 0, 0),  (dx, dy, 0)),   # From bottom-left to top-right
        ("BarZ-b", (dx, 0, 0), (0, dy, 0)),    # From bottom-right to top-left
    ]

    bar_part_names = [data[0] for data in bar_part_definitions]
    created_parts = {}

    for name, start, end in bar_part_definitions:
        part_obj = create_bar(myModel, name, start, end)
        if part_obj:
            created_parts[name] = part_obj
             

 

# --- Step 3: Assign Beam Section and Orientation to Parts ---
print("\nStep 3: Assign Beam Section and Orientation")
def assign_sections_to_parts(model, part_names, section_name):
    
    success = True
    for part_name in part_names:
        if part_name in model.parts:
            try:
                part = model.parts[part_name]
                print("  Assigning section to Part '{}'...".format(part_name))
                all_edges = part.edges
                if not all_edges:
                    warnings.warn(u"No edges found for part '{}' during section assignment.".format(part_name))
                    success = False
                    continue
                region = regionToolset.Region(edges=all_edges)
                part.SectionAssignment(region=region, sectionName=section_name, offset=0.0,
                                     offsetType=MIDDLE_SURFACE, offsetField='',
                                     thicknessAssignment=FROM_SECTION)
                print(u"  Assigned section '{}' to part '{}'.".format(section_name, part_name))
            except Exception as e:
                warnings.warn(u"Failed to assign section to part '{}': {}".format(part_name, e))
                print(traceback.format_exc())
                success = False
        else:
            warnings.warn(u"Part '{}' not found for section assignment.".format(part_name))
            success = False
    return success

def assign_beam_orientation_to_parts(model, part_names):
    print(" --- Assigning Beam Orientations ---")
    success = True
    n1_direction = (0.0, 0.0, -1.0)  # n1 vector along negative global Z
    for part_name in part_names:
        if part_name in model.parts:
            try:
                part = model.parts[part_name]
                print("  Assigning orientation to Part '{}'...".format(part_name))
                all_edges = part.edges
                if not all_edges:
                    warnings.warn("No edges found for part '{}' during orientation assignment.".format(part_name))
                    success = False
                    continue
                region = regionToolset.Region(edges=all_edges)
                part.assignBeamSectionOrientation(method=N1_COSINES, n1=n1_direction, region=region)
                print("  Assigned beam orientation to part '{}' (n1={}).".format(part_name, n1_direction))
            except Exception as e:
                warnings.warn("Failed to assign beam orientation to part '{}': {}".format(part_name, e))
                print(traceback.format_exc())
                success = False
        else:
            warnings.warn("Part '{}' not found for orientation assignment.".format(part_name))
            success = False
    return success

# Execute Step 3
sections_ok = assign_sections_to_parts(myModel, bar_part_names, beam_section_name)
orient_ok = assign_beam_orientation_to_parts(myModel, bar_part_names)
if not sections_ok or not orient_ok:
    overall_success = False
    warnings.warn("Problem assigning sections or orientations to BAR parts.")
print("Finished Step 3.")

# --- Step 4: Mesh Parts ---
print("\nStep 4: Mesh Parts")
def mesh_bars(model_obj, part_names_to_mesh):
    """Meshes specified bar parts."""
    print(" --- Meshing Bar Parts ---")
    global_seed_size = 0.13
    success = True
    elemType = mesh.ElemType(elemCode=B31, elemLibrary=STANDARD)

    for part_name in part_names_to_mesh:
        if part_name in model_obj.parts:
            try:
                part = model_obj.parts[part_name]
                print("  Seeding part '{}' (size={})...".format(part_name, global_seed_size))
                part.seedPart(size=global_seed_size, deviationFactor=0.1, minSizeFactor=0.1)
                print("  Setting element type for '{}'...".format(part_name))
                all_edges = part.edges
                if not all_edges:
                    warnings.warn("No edges found for element type assignment on part '{}'.".format(part_name))
                    success = False
                    continue
                region = regionToolset.Region(edges=all_edges)
                part.setElementType(regions=region, elemTypes=(elemType,))
                print("  Generating mesh for part '{}'...".format(part_name))
                part.generateMesh()
                print("  Meshed part {}.".format(part_name))
            except Exception as e:
                warnings.warn("Failed to mesh part '{}': {}".format(part_name, e))
                print(traceback.format_exc())
                success = False
        else:
            warnings.warn("Part '{}' not found for meshing.".format(part_name))
            success = False
    return success

# Execute Step 4
mesh_ok = mesh_bars(myModel, bar_part_names)
if not mesh_ok:
    overall_success = False
    warnings.warn("Problem meshing one or more BAR parts.")
print("Finished Step 4.")

# --- Step 5: Create Instances with Corrected Naming ---
print("\nStep 5: Create Instances with Corrected Grandstand Geometry")

def create_grandstand_instances(assembly_obj, model_obj, n_x, n_y, n_z_base, step_x, step_y, step_z):
    """
    Creates instances using corrected grandstand geometry logic.
    
    BarX Logic:
    - Always 7 rows (ix = 0,1,2,3,4,5,6) 
    - Modules per row decrease as height increases
    - No BarX at top level
    
    BarZ Logic:
    - Number of rows decreases as height increases (6,5,4,3,2,1)
    - Each row always has 6 modules (iz = 0,1,2,3,4,5)
    - Continues to top level with 1 row
    """
    print(" --- Creating Grandstand Instances with Corrected Logic ---")
    instances_created_total = 0
    instances_skipped_total = 0
    success = True
    instance_keys_generated = []

    # Define the base part names
    bars_x = ['BarX-a', 'BarX-b']  # yz plane bars
    bars_z = ['BarZ-a', 'BarZ-b']  # xy plane bars

    # --- BarX Instances (yz plane) ---
    print("  Processing BarX instances (yz plane)...")
    print("  BarX Logic: 7 rows always, decreasing modules per row, no BarX at top")
    inst_count_x_created = 0
    inst_count_x_skipped = 0
    
    for bar_name in bars_x:
        if bar_name not in model_obj.parts:
            warnings.warn("Part '{}' not found. Skipping instances for this part.".format(bar_name))
            success = False
            continue
        p = model_obj.parts[bar_name]

        try:
            for iy in range(n_y):  # Height levels (0,1,2,3,4) - NO TOP LEVEL for BarX
                # Calculate modules per row (decreases with height)
                modules_per_row = max(1, n_z_base - iy)  # 5,4,3,2,1
                
                print("    Level {}: 7 rows, {} modules per row".format(iy, modules_per_row))
                
                for ix in range(n_x + 1):  # Always 7 rows (0,1,2,3,4,5,6)
                    for iz in range(modules_per_row):  # Decreasing modules per row
                        # Updated naming convention
                        inst_name = "{}_x{}_y{}_z{}".format(bar_name, ix, iy, iz)
                        instance_keys_generated.append(inst_name)

                        if inst_name in assembly_obj.instances:
                            inst_count_x_skipped += 1
                            continue

                        try:
                            inst = assembly_obj.Instance(name=inst_name, part=p, dependent=ON)
                            inst_count_x_created += 1
                            
                            # Calculate translation vector
                            x_pos = ix * step_x
                            y_pos = iy * step_y
                            z_pos = iz * step_z
                            
                            if x_pos != 0.0 or y_pos != 0.0 or z_pos != 0.0:
                                inst.translate(vector=(x_pos, y_pos, z_pos))
                                
                        except Exception as e_inst:
                            warnings.warn("Error creating/translating instance '{}': {}".format(inst_name, e_inst))
                            print(traceback.format_exc())
                            success = False
                            if inst_name in assembly_obj.instances:
                                try: del assembly_obj.instances[inst_name]
                                except: pass
                                
        except Exception as e_loop_x:
            warnings.warn("Error during instance creation loop for BarX part '{}': {}".format(bar_name, e_loop_x))
            print(traceback.format_exc())
            success = False

    instances_created_total += inst_count_x_created
    instances_skipped_total += inst_count_x_skipped
    print("  BarX Instances Created: {}, Skipped: {}".format(inst_count_x_created, inst_count_x_skipped))

    # --- BarZ Instances (xy plane) ---
    print("  Processing BarZ instances (xy plane)...")
    print("  BarZ Logic: decreasing rows, always 6 modules per row, continues to top")
    inst_count_z_created = 0
    inst_count_z_skipped = 0
    
    for bar_name in bars_z:
        if bar_name not in model_obj.parts:
            warnings.warn("Part '{}' not found. Skipping instances for this part.".format(bar_name))
            success = False
            continue
        p = model_obj.parts[bar_name]

        try:
            for iy in range(n_y + 1):  # Height levels (0,1,2,3,4,5) - INCLUDING TOP LEVEL for BarZ
                # Calculate number of rows (decreases with height)
                num_rows = max(1, n_x - iy)  # 6,5,4,3,2,1
                
                print("    Level {}: {} rows, 6 modules per row".format(iy, num_rows))
                
                for ix in range(1, num_rows + 1):  # Decreasing number of rows (1-6, 1-5, 1-4, 1-3, 1-2, 1)
                    for iz in range(n_x):  # Always 6 modules per row (0,1,2,3,4,5)
                        # Updated naming convention
                        inst_name = "{}_x{}_y{}_z{}".format(bar_name, ix, iy, iz)
                        instance_keys_generated.append(inst_name)

                        if inst_name in assembly_obj.instances:
                            inst_count_z_skipped += 1
                            continue

                        try:
                            inst = assembly_obj.Instance(name=inst_name, part=p, dependent=ON)
                            inst_count_z_created += 1
                            
                            # Calculate translation vector  
                            x_pos = ix * step_x
                            y_pos = iy * step_y
                            z_pos = iz * step_z
                            
                            if x_pos != 0.0 or y_pos != 0.0 or z_pos != 0.0:
                                inst.translate(vector=(x_pos, y_pos, z_pos))
                                
                        except Exception as e_inst:
                            warnings.warn("Error creating/translating instance '{}': {}".format(inst_name, e_inst))
                            print(traceback.format_exc())
                            success = False
                            if inst_name in assembly_obj.instances:
                                try: del assembly_obj.instances[inst_name]
                                except: pass
                                
        except Exception as e_loop_z:
            warnings.warn("Error during instance creation loop for BarZ part '{}': {}".format(bar_name, e_loop_z))
            print(traceback.format_exc())
            success = False

    instances_created_total += inst_count_z_created
    instances_skipped_total += inst_count_z_skipped
    print("  BarZ Instances Created: {}, Skipped: {}".format(inst_count_z_created, inst_count_z_skipped))

    print("\nTotal Instances Newly Created: {}".format(instances_created_total))
    print("Total Instances Skipped (already existed): {}".format(instances_skipped_total))
    
    # Print summary of what was created
    print("\n=== INSTANCE CREATION SUMMARY ===")
    print("BarX instances:")
    for iy in range(n_y):
        modules_per_row = max(1, n_z_base - iy)
        print("  Level {}: 7 rows x {} modules = {} instances per part".format(iy, modules_per_row, 7 * modules_per_row))
    
    print("BarZ instances:")
    for iy in range(n_y + 1):
        num_rows = max(1, n_x - iy)
        print("  Level {}: {} rows x 6 modules = {} instances per part".format(iy, num_rows, num_rows * 6))
    
    if not success: 
        warnings.warn("Issues encountered during instance creation.")
    
    # Remove duplicates and return sorted list
    unique_instance_keys = sorted(list(set(instance_keys_generated)))
    print("Total distinct instance names tracked: {}".format(len(unique_instance_keys)))
    return success, unique_instance_keys

# Execute Step 5
instances_ok, instance_keys = create_grandstand_instances(a, myModel, n_x, n_y, n_z_base, dx, dy, dz)
if not instances_ok:
    overall_success = False
    warnings.warn("Problem creating instances.")

print("Finished Step 5.")

# --- Step 9: Regenerate Assembly ---
print("\nStep 9: Regenerating Assembly...")
a.regenerate()
print("Assembly regenerated.")

print("\nScript completed. Overall success: {}".format(overall_success))
if overall_success:
    print("Ready for connector creation in next script!")
    print("Structure created with corrected tapering logic:")
    print("- BarX: 7 rows always, decreasing modules per row, NO BarX at top")
    print("- BarZ: decreasing rows (6 to 1), always 6 modules per row, continues to top")
else:
    print("Please review warnings above before proceeding.")