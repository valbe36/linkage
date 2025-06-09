

# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *
import warnings
import traceback # Import traceback for detailed error messages
import part # Explicitly import part module
import assembly # Explicitly import assembly module
import regionToolset # Explicitly import regionToolset
import mesh # Explicitly import mesh module (used for ElemType)
import section # Explicitly import section module
import connectorBehavior # Potentially needed if defining complex behaviors
import math
import re
""""
This sketch makes the scissor bars, their proprieties, mesh, instances and internal connections. It also makes the revelant RPs at the end of bars
ATT! this sketch makes only named wires. Collect the wires in sets and apply connector section in the GUI
For modifications:
users parameters: dx dy dz lenght of modules and n_X, n_y, n_z number of modules.
ATT! the bars are partiotioned in 4 parts. If you need more, 
update the vertex index when making the mid joint (current index 2) and the end joint (current indexes 0 and 4)

"""""
# --- 0) Basic Setup: Model & Parameters ---
model_name = 'Model-1' # <<< ENSURE THIS IS CORRECT
connector_section_name = 'Pure_Hinge' # Still needed if creating section
beam_section_name = 'RHS_48e3' # Section for the bars themselves
material_name = 'Steel_355'
profile_name = 'RHS_48e3_Profile'
base_wire_name_x = 'wire_middleX'
base_wire_name_y = 'wire_middleY'
base_wire_name_endX = 'wire_RP_endX'
base_wire_name_endY = 'wire_RP_endY'
base_wire_name_adjX = 'wire_adjacentX'
base_wire_name_adjY = 'wire_adjacentY'
csys_X_name = 'Connector_Global_X_Orient'
csys_Y_name = 'Connector_Global_Y_Orient'

 

# Geometry/Instance Parameters
dx = 2.208365; dy = 2.208365; dz = 1.275
n_x = 6; n_y = 6; n_z = 6

# CSYS names for connector orientation
csys_X_name = 'Connector_Global_X_Orient' # Must exist or be created
csys_Y_name = 'Connector_Global_Y_Orient' # Must exist or be created

# Define overall success flag *before* main try block
overall_success = True

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
        raise # Re-raise the error to stop the script clearly
except Exception as e:
        print(f"FATAL ERROR accessing model/assembly: {e}")
        print(traceback.format_exc()) # Print detailed traceback
        raise # Re-raise the error
print("Finished Step 0.")

    # --- Step 1: Define Material & Sections ---
print("\nStep 1: Define Material & Sections")
def create_nonlinear_steel(model, material_name):
        if material_name not in model.materials:
            print(f"  Creating material: {material_name}")
            try:
                mat = model.Material(name=material_name)
                mat.Elastic(table=((210000.0, 0.3),)) # Units: MPa, nu
                mat.Plastic(table=((355.0, 0.0), (400.0, 0.05))) # yield stress, plastic strain
                print(f"  Material '{material_name}' created.")
            except Exception as e:
                warnings.warn(f"Failed to create material '{material_name}': {e}")
                print(traceback.format_exc())
                raise # Stop script if material fails
        else:
            print(f"  Material '{material_name}' already exists.")

def create_pipe_section(model, profile_name, section_name, material_name):
        # Check/Create Profile
        if profile_name not in model.profiles:
            print(f"  Creating profile: {profile_name}")
            try:
                # Ensure PipeProfile args match your section (r, t)
                model.PipeProfile(name=profile_name, r=0.02415, t=0.003) # Example values
                print(f"  Profile '{profile_name}' created.")
            except Exception as e:
                warnings.warn(f"Failed to create profile '{profile_name}': {e}")
                print(traceback.format_exc())
                raise # Stop script if profile fails
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
                    poissonRatio=0.3 # Should match elastic definition
                )
                print(f"  Section '{section_name}' created.")
            except Exception as e:
                warnings.warn(f"Failed to create section '{section_name}': {e}")
                print(traceback.format_exc())
                raise # Stop script if section fails
        else:
            print(f"  Section '{section_name}' already exists.")

    # --- Execute Step 1 ---
create_nonlinear_steel(myModel, material_name)
create_pipe_section(myModel, profile_name, beam_section_name, material_name)
print("Finished Step 1.")

 
#--------------------------------------------------CREATE BAR PARTS

# --- Step 2: Create Parts ---
print("\nStep 2: Create Parts")
def create_bar(model_obj, part_name, start_point, end_point):

    print(f"  Attempting to create/access part: {part_name}")
    if part_name in model_obj.parts:
        print(f"  Part '{part_name}' already exists. Skipping creation.")
        return model_obj.parts[part_name]
    try:
        print(f"  Creating part: {part_name}")
        p = model_obj.Part(name=part_name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
        p.WirePolyLine(points=(start_point, end_point), mergeType=IMPRINT, meshable=ON)

        # ---  Partitioning  
        print(f"  Partitioning part '{part_name}' (User's original method)...")
        try:
            # Ensure there's an edge to partition first
            if not p.edges:
                 raise ValueError("Part has no edges after WirePolyLine.")

            initial_edge = p.edges[0] # Assume the first edge is the one to partition

            # First partition (likely creates midpoint vertex, potentially index 2)
            p.PartitionEdgeByParam(edges=(initial_edge,), parameter=0.5)
            p.PartitionEdgeByParam(edges=(p.edges[0],), parameter=0.5) # Partition first segment again (vertex at 0.25)

            if len(p.edges) > 2: # Check if enough edges exist after previous partitions
                 p.PartitionEdgeByParam(edges=(p.edges[2],), parameter=0.5) # Partition second segment (vertex at 0.75)
            else:
                 warnings.warn(f"Could not perform the third partition on edges[2] for part '{part_name}'. Not enough edges found after prior partitions.")

        except IndexError as e_idx:
             warnings.warn(f"Indexing error during partitioning of part '{part_name}'. Edges might not be indexed as expected ({e_idx}). Check partitioning result.")
        except Exception as e_part:
             warnings.warn(f"Error during partitioning of part '{part_name}': {e_part}")
             print(traceback.format_exc())

        return p
    except Exception as e:
        warnings.warn(f"Failed to create/partition part '{part_name}': {e}")
        print(traceback.format_exc())
        raise # Stop script if part creation fails (WirePolyLine or initial access)

# --- Execute Step 2 ---
bar_part_definitions = [
    ("BarX-a", (0, 0, dz), (0, dy, 0)), # Name, Start Point, End Point
    ("BarX-b", (0, 0, 0),  (0, dy, dz)),
    ("BarY-a", (dx, 0, 0), (0, 0, dz)),
    ("BarY-b", (0, 0, 0),  (dx, 0, dz)),
]
bar_part_names = [data[0] for data in bar_part_definitions]
created_parts = {}
for name, start, end in bar_part_definitions:
    part_obj = create_bar(myModel, name, start, end) # Call the updated function
    if part_obj: # Store if successfully created/accessed
         created_parts[name] = part_obj
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
                    all_edges = part.edges # Get all edges
                    if not all_edges:
                        warnings.warn(f"No edges found for part '{part_name}' during section assignment.")
                        success = False
                        continue
                    region = regionToolset.Region(edges=all_edges) # Create region from edges
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
        n1_direction = (0.0, 0.0, -1.0) # Example: n1 vector along negative global Z
        for part_name in part_names:
            if part_name in model.parts:
                try:
                    part = model.parts[part_name]
                    print(f"  Assigning orientation to Part '{part_name}'...")
                    all_edges = part.edges # Get all edges
                    if not all_edges:
                        warnings.warn(f"No edges found for part '{part_name}' during orientation assignment.")
                        success = False
                        continue
                    region = regionToolset.Region(edges=all_edges) # Create region
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

    # --- Execute Step 3 ---
sections_ok = assign_sections_to_parts(myModel, bar_part_names, beam_section_name)
orient_ok = assign_beam_orientation_to_parts(myModel, bar_part_names)
if not sections_ok or not orient_ok:
        overall_success = False # Mark potential issue but continue
        warnings.warn("Problem assigning sections or orientations to BAR parts.")
print("Finished Step 3.")


    # --- Step 4: Mesh Parts ---
print("\nStep 4: Mesh Parts")
def mesh_bars(model_obj, part_names_to_mesh):
        """Meshes specified bar parts."""
        print(" --- Meshing Bar Parts ---")
        global_seed_size = 0.13 # Desired element size
        success = True
        elemType = mesh.ElemType(elemCode=B31, elemLibrary=STANDARD) # Example: 2-node linear beam

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

    # --- Execute Step 4 ---
mesh_ok = mesh_bars(myModel, bar_part_names)
if not mesh_ok:
        overall_success = False # Mark potential issue
        warnings.warn("Problem meshing one or more BAR parts.")
print("Finished Step 4.")


#----------------------------------------------------------BARS INSTANCES --------------------------------------

# --- Step 5: Create Instances ---
print("\nStep 5: Create Instances")

# Define the instance creation function using USER'S original loop logic
# but with the SIMPLIFIED naming convention required by Steps 7 & 8.
def create_instances_user_logic(assembly_obj, model_obj, nx, ny, nz, step_x, step_y, step_z):
    """Creates instances using the user's specific loop structure and simplified naming."""
    print(" --- Creating Instances (User Specific Loops) ---")
    instances_created_total = 0
    instances_skipped_total = 0
    success = True
    instance_keys_generated = [] # Keep track of ALL instance names (new or existing)

    # Define the base part names expected by the loops
    bars_x = ['BarX-a', 'BarX-b']
    bars_y = ['BarY-a', 'BarY-b']

    # --- BarX Instances (User Loop Structure) ---
    print("  Processing BarX instances...")
    inst_count_x_created = 0
    inst_count_x_skipped = 0
    for bar_name in bars_x:
        if bar_name not in model_obj.parts:
            warnings.warn(f"Part '{bar_name}' not found. Skipping instances for this part.")
            success = False
            continue # Skip to the next bar_name if part doesn't exist
        p = model_obj.parts[bar_name]

        try:
            # USER'S ORIGINAL LOOPS for BarX
            for zlayer in range(nz):
                for ix in range(zlayer, nx): # User's range: zlayer to nx
                    for iy in range(ny):     # User's range: 0 to ny
                        # *** USE SIMPLIFIED NAMING CONVENTION ***
                        inst_name = f"{bar_name}_{zlayer}_{iy}_{ix}"
                        instance_keys_generated.append(inst_name) # Track name regardless of creation status

                        if inst_name in assembly_obj.instances:
                            inst_count_x_skipped += 1
                            continue # Skip if already exists

                        try:
                            # print(f"  Creating instance: {inst_name}") # Optional debug
                            inst = assembly_obj.Instance(name=inst_name, part=p, dependent=ON)
                            inst_count_x_created += 1
                            # Calculate translation vector
                            x_pos = ix * step_x
                            y_pos = iy * step_y
                            z_pos = zlayer * step_z
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

    # --- BarY Instances (User Loop Structure) ---
    print("  Processing BarY instances...")
    inst_count_y_created = 0
    inst_count_y_skipped = 0
    for bar_name in bars_y:
        if bar_name not in model_obj.parts:
            warnings.warn(f"Part '{bar_name}' not found. Skipping instances for this part.")
            success = False
            continue # Skip to the next bar_name if part doesn't exist
        p = model_obj.parts[bar_name]

        try:
            for zlayer in range(nz - 1):    # User's range
                for ix in range(zlayer, nx - 1): # User's range
                    for iy in range(ny + 1):     # User's range
                        # *** USE SIMPLIFIED NAMING CONVENTION ***
                        inst_name = f"{bar_name}_{zlayer}_{iy}_{ix}"
                        instance_keys_generated.append(inst_name) # Track name

                        if inst_name in assembly_obj.instances:
                            inst_count_y_skipped += 1
                            continue # Skip if already exists

                        try:
                            # print(f"  Creating instance: {inst_name}") # Optional debug
                            inst = assembly_obj.Instance(name=inst_name, part=p, dependent=ON)
                            inst_count_y_created += 1
                            # Calculate translation vector
                            x_pos = ix * step_x
                            y_pos = iy * step_y
                            z_pos = zlayer * step_z
                            if x_pos != 0.0 or y_pos != 0.0 or z_pos != 0.0:
                                inst.translate(vector=(x_pos, y_pos, z_pos))
                        except Exception as e_inst:
                            warnings.warn(f"Error creating/translating instance '{inst_name}': {e_inst}")
                            print(traceback.format_exc())
                            success = False
                            if inst_name in assembly_obj.instances:
                                try: del assembly_obj.instances[inst_name]
                                except: pass
        except Exception as e_loop_y:
            warnings.warn(f"Error during instance creation loop for BarY part '{bar_name}': {e_loop_y}")
            print(traceback.format_exc())
            success = False

    instances_created_total += inst_count_y_created
    instances_skipped_total += inst_count_y_skipped
    print(f"  BarY Instances Created: {inst_count_y_created}, Skipped: {inst_count_y_skipped}")

    print(f"\nTotal Instances Newly Created: {instances_created_total}")
    print(f"Total Instances Skipped (already existed): {instances_skipped_total}")
    if not success: warnings.warn("Issues encountered during instance creation.")
    # Ensure the returned list contains *all* names for subsequent steps
    # Remove duplicates just in case the loops generated some twice (unlikely but safe)
    unique_instance_keys = sorted(list(set(instance_keys_generated)))
    print(f"Total distinct instance names tracked: {len(unique_instance_keys)}")
    return success, unique_instance_keys # Return list of unique instance names

# --- Execute Step 5 ---
# Call the restored function with the correct arguments
instances_ok, instance_keys = create_instances_user_logic(a, myModel, n_x, n_y, n_z, dx, dy, dz)
if not instances_ok:
     overall_success = False
     warnings.warn("Problem creating instances.")


 
    # ====================================================================
    # Step 9: Regenerate Assembly (Still useful after feature creation/modification)
    # ====================================================================
print("\nStep 9: Regenerating Assembly...")
a.regenerate()
print("Assembly regenerated.")

