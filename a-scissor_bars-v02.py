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
Updated scissor bars script with correct geometry:
- Coordinate system: x (perpendicular to slope), y (vertical), z (along slope)
- Slope in yz plane at ~30° angle
- BarX: spans yz plane, rotates around x-axis
- BarZ: spans xy plane, rotates around z-axis
- Grandstand tapering: 5×6 to 1×6 modules in z-direction
"""

# --- 0) Basic Setup: Model & Parameters ---
model_name = 'Model-1'
connector_section_name = 'Pure_Hinge'
beam_section_name = 'RHS_48e3'
material_name = 'Steel_355'
profile_name = 'RHS_48e3_Profile'

# Updated Geometry Parameters (30° slope)
dx = 221    # spacing perpendicular to slope (x-direction)
dy = 127.5  # height increment per level (y-direction)  
dz = 221    # spacing along slope (z-direction)

# Grandstand dimensions
n_x = 6     # modules perpendicular to slope (constant)
n_y = 5     # height levels (0 to 4: gives 5×6 to 1×6 tapering)
n_z_base = 5  # modules along slope at ground level (tapers to 1)

# CSYS names for connector orientation
csys_X_name = 'Connector_Global_X_Orient'
csys_Z_name = 'Connector_Global_Z_Orient'  # Updated from Y to Z

# Define overall success flag
overall_success = True

print(f"Updated Geometry: dx={dx}, dy={dy}, dz={dz}")
print(f"Grandstand: {n_x} × {n_y} × {n_z_base} (tapering in z-direction)")

# ====================================================================
# MAIN EXECUTION BLOCK (Sequential Steps)
# ====================================================================

# --- Access Model and Assembly ---
print("\nStep 0: Accessing Model and Assembly...")
try:
    myModel = mdb.models[model_name]
    a = myModel.rootAssembly
    print(f"Successfully accessed model '{model_name}' and assembly.")
except KeyError:
    print(f"FATAL ERROR: Model '{model_name}' not found. Create it first or check name.")
    raise
except Exception as e:
    print(f"FATAL ERROR accessing model/assembly: {e}")
    print(traceback.format_exc())
    raise
print("Finished Step 0.")

# --- Step 1: Define Material & Sections ---
print("\nStep 1: Define Material & Sections")
def create_nonlinear_steel(model, material_name):
    if material_name not in model.materials:
        print(f"  Creating material: {material_name}")
        try:
            mat = model.Material(name=material_name)
            mat.Elastic(table=((2.1e11, 0.3),))  # Units: N/m2, nu
            mat.Density(table=((7850),)) #kg
            mat.Plastic(table=((3.55e8, 0.0), (4e8, 0.05)))  # yield stress, plastic strain
            print(f"  Material '{material_name}' created.")
        except Exception as e:
            warnings.warn(f"Failed to create material '{material_name}': {e}")
            print(traceback.format_exc())
            raise
    else:
        print(f"  Material '{material_name}' already exists.")

def create_pipe_section(model, profile_name, section_name, material_name):
    # Check/Create Profile
    if profile_name not in model.profiles:
        print(f"  Creating profile: {profile_name}")
        try:
            model.PipeProfile(name=profile_name, r=0.02415, t=0.003)
            print(f"  Profile '{profile_name}' created.")
        except Exception as e:
            warnings.warn(f"Failed to create profile '{profile_name}': {e}")
            print(traceback.format_exc())
            raise
    else:
        print(f"  Profile '{profile_name}' already exists.")

    # Assign to a beam section
    if section_name not in model.sections:
        print(f"  Creating section: {section_name}")
        try:
            model.BeamSection(
                name=section_name,
                integration=DURING_ANALYSIS,
                profile=profile_name,
                material=material_name,
                poissonRatio=0.3
            )
            print(f"  Section '{section_name}' created.")
        except Exception as e:
            warnings.warn(f"Failed to create section '{section_name}': {e}")
            print(traceback.format_exc())
            raise
    else:
        print(f"  Section '{section_name}' already exists.")

# Execute Step 1
create_nonlinear_steel(myModel, material_name)
create_pipe_section(myModel, profile_name, beam_section_name, material_name)
print("Finished Step 1.")

# --- Step 2: Create Parts ---
print("\nStep 2: Create Parts")
# --- Step 2: Create Parts ---
print("\nStep 2: Create Parts")

# Check if parts already exist (check one part as indicator)
first_part_name = "BarX-a"
if first_part_name in myModel.parts:
    print(f"  Part '{first_part_name}' already exists. Skipping all part creation.")
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
            print(f"  Found existing part: {name}")
        else:
            warnings.warn(f"Expected part '{name}' not found!")
else:
    print("  Creating new parts...")
    
    def create_bar(model_obj, part_name, start_point, end_point):
        print(f"  Attempting to create/access part: {part_name}")
        if part_name in model_obj.parts:
            print(f"  Part '{part_name}' already exists. Skipping creation.")
            return model_obj.parts[part_name]
        try:
            print(f"  Creating part: {part_name}")
            p = model_obj.Part(name=part_name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
            p.WirePolyLine(points=(start_point, end_point), mergeType=IMPRINT, meshable=ON)

            # --- Partitioning (keeping your working logic) ---
            print(f"  Partitioning part '{part_name}' into 4 equal segments...")
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
                    warnings.warn(f"Could not perform the third partition on edges[2] for part '{part_name}'.")

            except IndexError as e_idx:
                warnings.warn(f"Indexing error during partitioning of part '{part_name}': {e_idx}")
            except Exception as e_part:
                warnings.warn(f"Error during partitioning of part '{part_name}': {e_part}")
                print(traceback.format_exc())

            return p
        except Exception as e:
            warnings.warn(f"Failed to create/partition part '{part_name}': {e}")
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
            print(f"  Created/accessed part: {name}")

print("Finished Step 2.")

# --- Step 3: Assign Beam Section and Orientation to Parts ---
print("\nStep 3: Assign Beam Section and Orientation")
def assign_sections_to_parts(model, part_names, section_name):
    print(" --- Assigning Beam Sections ---")
    success = True
    for part_name in part_names:
        if part_name in model.parts:
            try:
                part = model.parts[part_name]
                print(f"  Assigning section to Part '{part_name}'...")
                all_edges = part.edges
                if not all_edges:
                    warnings.warn(f"No edges found for part '{part_name}' during section assignment.")
                    success = False
                    continue
                region = regionToolset.Region(edges=all_edges)
                part.SectionAssignment(region=region, sectionName=section_name, offset=0.0,
                                     offsetType=MIDDLE_SURFACE, offsetField='',
                                     thicknessAssignment=FROM_SECTION)
                print(f"  Assigned section '{section_name}' to part '{part_name}'.")
            except Exception as e:
                warnings.warn(f"Failed to assign section to part '{part_name}': {e}")
                print(traceback.format_exc())
                success = False
        else:
            warnings.warn(f"Part '{part_name}' not found for section assignment.")
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
                print(f"  Assigning orientation to Part '{part_name}'...")
                all_edges = part.edges
                if not all_edges:
                    warnings.warn(f"No edges found for part '{part_name}' during orientation assignment.")
                    success = False
                    continue
                region = regionToolset.Region(edges=all_edges)
                part.assignBeamSectionOrientation(method=N1_COSINES, n1=n1_direction, region=region)
                print(f"  Assigned beam orientation to part '{part_name}' (n1={n1_direction}).")
            except Exception as e:
                warnings.warn(f"Failed to assign beam orientation to part '{part_name}': {e}")
                print(traceback.format_exc())
                success = False
        else:
            warnings.warn(f"Part '{part_name}' not found for orientation assignment.")
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
                print(f"  Seeding part '{part_name}' (size={global_seed_size})...")
                part.seedPart(size=global_seed_size, deviationFactor=0.1, minSizeFactor=0.1)
                print(f"  Setting element type for '{part_name}'...")
                all_edges = part.edges
                if not all_edges:
                    warnings.warn(f"No edges found for element type assignment on part '{part_name}'.")
                    success = False
                    continue
                region = regionToolset.Region(edges=all_edges)
                part.setElementType(regions=region, elemTypes=(elemType,))
                print(f"  Generating mesh for part '{part_name}'...")
                part.generateMesh()
                print(f"  Meshed part {part_name}.")
            except Exception as e:
                warnings.warn(f"Failed to mesh part '{part_name}': {e}")
                print(traceback.format_exc())
                success = False
        else:
            warnings.warn(f"Part '{part_name}' not found for meshing.")
            success = False
    return success

# Execute Step 4
mesh_ok = mesh_bars(myModel, bar_part_names)
if not mesh_ok:
    overall_success = False
    warnings.warn("Problem meshing one or more BAR parts.")
print("Finished Step 4.")

# --- Step 5: Create Instances with Updated Naming ---
print("\nStep 5: Create Instances with Grandstand Geometry")

def create_grandstand_instances(assembly_obj, model_obj, n_x, n_y, n_z_base, step_x, step_y, step_z):
    """Creates instances using grandstand geometry with updated naming."""
    print(" --- Creating Grandstand Instances ---")
    instances_created_total = 0
    instances_skipped_total = 0
    success = True
    instance_keys_generated = []

    # Define the base part names
    bars_x = ['BarX-a', 'BarX-b']  # yz plane bars
    bars_z = ['BarZ-a', 'BarZ-b']  # xy plane bars

    # --- BarX Instances (yz plane) ---
    print("  Processing BarX instances (yz plane)...")
    inst_count_x_created = 0
    inst_count_x_skipped = 0
    
    for bar_name in bars_x:
        if bar_name not in model_obj.parts:
            warnings.warn(f"Part '{bar_name}' not found. Skipping instances for this part.")
            success = False
            continue
        p = model_obj.parts[bar_name]

        try:
            for iy in range(n_y):  # Height levels
                # Calculate how many z-modules exist at this height (tapering)
                n_z_at_level = max(1, n_z_base - iy)  
                
                for iz in range(n_z_at_level):  # Along slope (tapering)
                    for ix in range(n_x + 1):  # Perpendicular to slope (need bars at boundaries: 0 to 6)
                        # Updated naming convention
                        inst_name = f"{bar_name}_x{ix}_y{iy}_z{iz}"
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
                            warnings.warn(f"Error creating/translating instance '{inst_name}': {e_inst}")
                            print(traceback.format_exc())
                            success = False
                            if inst_name in assembly_obj.instances:
                                try: del assembly_obj.instances[inst_name]
                                except: pass
        except Exception as e_loop_x:
            warnings.warn(f"Error during instance creation loop for BarX part '{bar_name}': {e_loop_x}")
            print(traceback.format_exc())
            success = False

    instances_created_total += inst_count_x_created
    instances_skipped_total += inst_count_x_skipped
    print(f"  BarX Instances Created: {inst_count_x_created}, Skipped: {inst_count_x_skipped}")

    # --- BarZ Instances (xy plane) ---
    print("  Processing BarZ instances (xy plane)...")
    inst_count_z_created = 0
    inst_count_z_skipped = 0
    
    for bar_name in bars_z:
        if bar_name not in model_obj.parts:
            warnings.warn(f"Part '{bar_name}' not found. Skipping instances for this part.")
            success = False
            continue
        p = model_obj.parts[bar_name]

        try:
            for iy in range(n_y):  # Height levels
                # Calculate how many z-modules exist at this height (tapering)
                n_z_at_level = max(1, n_z_base - iy)
                
                for iz in range(n_z_at_level):  # Along slope (tapering)
                    for ix in range(n_x ):  # Perpendicular to slope (need bars at boundaries: 0 to 5)
                        # Updated naming convention
                        inst_name = f"{bar_name}_x{ix}_y{iy}_z{iz}"
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
                            warnings.warn(f"Error creating/translating instance '{inst_name}': {e_inst}")
                            print(traceback.format_exc())
                            success = False
                            if inst_name in assembly_obj.instances:
                                try: del assembly_obj.instances[inst_name]
                                except: pass
        except Exception as e_loop_z:
            warnings.warn(f"Error during instance creation loop for BarZ part '{bar_name}': {e_loop_z}")
            print(traceback.format_exc())
            success = False

    instances_created_total += inst_count_z_created
    instances_skipped_total += inst_count_z_skipped
    print(f"  BarZ Instances Created: {inst_count_z_created}, Skipped: {inst_count_z_skipped}")

    print(f"\nTotal Instances Newly Created: {instances_created_total}")
    print(f"Total Instances Skipped (already existed): {instances_skipped_total}")
    
    if not success: 
        warnings.warn("Issues encountered during instance creation.")
    
    # Remove duplicates and return sorted list
    unique_instance_keys = sorted(list(set(instance_keys_generated)))
    print(f"Total distinct instance names tracked: {len(unique_instance_keys)}")
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

print(f"\nScript completed. Overall success: {overall_success}")
if overall_success:
    print("Ready for connector creation in next script!")
else:
    print("Please review warnings above before proceeding.")