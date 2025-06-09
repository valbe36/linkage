

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
print("Finished Step 5.")


 #---------------------------------------------------------------WIRES PREREQUISITES -------------------------
 
# ====================================================================
# (Middle Wires + Meshing)
# ====================================================================
 

# Define Connector Element Type globally
connector_element_type = mesh.ElemType(elemCode=CONN3D2)
# Define Connector Section Name
connector_section_name = 'Pure_Hinge' # Or your desired name
# Define CSYS names
csys_X_name = 'Connector_Global_X_Orient'
csys_Y_name = 'Connector_Global_Y_Orient'
# Define Base wire names
base_wire_name_x = 'wire_middleX'
base_wire_name_y = 'wire_middleY'


# ====================================================================
# Step 6: Setup Connector Prerequisites
# ====================================================================

print("\nStep 6: Setup Connector Prerequisites")
    # --- (Use your working setup_connectors_prerequisites function here) ---
def setup_connectors_prerequisites(model, assembly, conn_section_name, csys_X_name, csys_Y_name):
        """
        Sets up connector sections and finds/creates orientation datums.
        Uses user's original logic for checking/creating/accessing CSYS.
        Defines JOIN/REVOLUTE connector section directly.
        """
        print("\n--- Setting up Connector Prerequisites (User's Original Logic - Fixed) ---")
        csys_X = None
        csys_Y = None
        connector_section_ok = True
        csys_ok = True
        try:
            # Ensure Connector Section exists
            if conn_section_name not in model.sections: # Uses 'model' correctly
                print(f"  Creating Connector Section '{conn_section_name}'.")
                try:
                    model.ConnectorSection(name=conn_section_name,
                                           translationalType=JOIN,
                                           rotationalType=REVOLUTE)
                    print(f"  Connector Section '{conn_section_name}' created.")
                except Exception as e:
                    warnings.warn(f"Failed to create Connector Section '{conn_section_name}': {e}")
                    print(traceback.format_exc())
                    connector_section_ok = False
            else:
                print(f"  Connector Section '{conn_section_name}' already exists.")

            # Ensure Orientation CSYS exist (User's original helper function)
            def ensure_csys_exists(name, origin, point1, point2):
                csys_obj_inner = None
                success_inner = True
                if name in assembly.features: # Uses 'assembly' correctly
                    # print(f"  Datum CSYS Feature '{name}' found in features.") # Less verbose
                    try:
                        feature_id = assembly.features[name].id
                        csys_obj_inner = assembly.datums[feature_id]
                        # print(f"  Successfully accessed existing Datum CSYS '{name}' (ID: {feature_id}).")
                        success_inner = True
                    except KeyError:
                         warnings.warn(f"Feature '{name}' exists, but Datum ID {feature_id} not found in assembly.datums. Attempting recreation.")
                         success_inner = False
                    except Exception as e_access:
                        warnings.warn(f"Error accessing existing CSYS '{name}' via datum ID: {e_access}. Attempting recreation.")
                        success_inner = False
                else:
                     # print(f"  Datum CSYS Feature '{name}' not found in features. Will attempt creation.")
                     success_inner = False

                if not success_inner:
                    print(f"  Creating Datum CSYS '{name}'.")
                    try:
                        if name in assembly.features:
                             print(f"  Warning: Deleting existing feature '{name}' before attempting datum creation again.")
                             del assembly.features[name]
                        csys_feature = assembly.DatumCsysByThreePoints(name=name, coordSysType=CARTESIAN,
                                                                        origin=origin, point1=point1, point2=point2)
                        print(f"  Successfully created Datum CSYS Feature '{name}'.")
                        csys_obj_inner = assembly.datums[csys_feature.id]
                        success_inner = True
                        print("  Regenerating assembly after CSYS creation.")
                        assembly.regenerate()
                    except Exception as e_create:
                        warnings.warn(f"Failed to create Datum CSYS '{name}': {e_create}")
                        print(traceback.format_exc())
                        success_inner = False
                        csys_obj_inner = None
                return csys_obj_inner, success_inner

            csys_X, success_x = ensure_csys_exists(csys_X_name, (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
            csys_Y, success_y = ensure_csys_exists(csys_Y_name, (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0))

            if not success_x or not success_y: csys_ok = False
            if not csys_X or not csys_Y: csys_ok = False; warnings.warn(f"Failed to obtain valid Datum objects for CSYS.")

        except Exception as e_main:
             print(f"ERROR during connector prerequisite setup: {e_main}")
             print(traceback.format_exc()); connector_section_ok = False; csys_ok = False

        if not connector_section_ok: raise Exception(f"FATAL: Connector Section setup failed.")
        if not csys_ok: raise Exception(f"FATAL: Datum CSYS setup failed.")

        print(f"  Prerequisites OK. Using CSYS features named: '{csys_X_name}', '{csys_Y_name}'")
        return True, csys_X, csys_Y

    # --- Execute Step 6 ---
prereq_ok, csys_X_obj, csys_Y_obj = setup_connectors_prerequisites(
        myModel, a, connector_section_name, csys_X_name, csys_Y_name
    )
if not prereq_ok:
        overall_success = False
        warnings.warn("Connector prerequisite setup reported failure.")
        # Optional: raise Exception("Stopping script due to prerequisite failure.")

    # ====================================================================
    # Step 7: Create X-Connector Wires & Assign Properties
    # ====================================================================

# Function to create CONN3D2 elements between vertex pairs
def create_CONN3D2_connector(assembly, model, 
                            instA, vIdxA, 
                            instB, vIdxB, 
                            wire_name_base="Connector",
                            section_name="Pure_Hinge",
                            csys_for_orient=None):
    """
    Creates a CONN3D2 element between two vertices of instances.
    Returns the wire feature name and connector element set.
    """
    
    # Generate unique wire name
    wire_name = f"{wire_name_base}_between_{instA.name}_{instB.name}"
    
    try:
        # Get vertices
        if vIdxA >= len(instA.vertices) or vIdxB >= len(instB.vertices):
            warnings.warn(f"Vertex index out of range: {instA.name}[{vIdxA}] or {instB.name}[{vIdxB}]")
            return None, None
            
        vertexA = instA.vertices[vIdxA]
        vertexB = instB.vertices[vIdxB]
        
        # Create wire feature connecting the two vertices
        if wire_name in assembly.features:
            del assembly.features[wire_name]
            
        wire_feature = assembly.WirePolyLine(
            points=((vertexA.pointOn[0], vertexB.pointOn[0]),),
            mergeType=SEPARATE,
            meshable=ON
        )
        
        # Rename the wire feature
        assembly.features.changeKey(fromName=wire_feature.name, toName=wire_name)
        assembly.regenerate()
        
        # Find the edge
        wire_edges = assembly.getFeatureEdges(wire_name)
        if not wire_edges:
            warnings.warn(f"No edges found for wire {wire_name}")
            return wire_name, None
            
        edge = assembly.edges[wire_edges[0]]
        
        # Create element type for CONN3D2
        elemType = mesh.ElemType(elemCode=CONN3D2)
        
        # Seed and mesh the edge
        assembly.seedEdgeByNumber(edges=assembly.edges[edge.index:edge.index+1], number=1)
        assembly.setElementType(edges=assembly.edges[edge.index:edge.index+1], elemTypes=(elemType,))
        assembly.generateMesh(regions=assembly.edges[edge.index:edge.index+1])
        
        # Create region from edge for section assignment
        region = regionToolset.Region(edges=assembly.edges[edge.index:edge.index+1])
        
        # Assign connector section
        assembly.SectionAssignment(region=region, sectionName=section_name)
        
        # Apply orientation if CSYS provided
        if csys_for_orient:
            assembly.ConnectorOrientation(region=region, localCsys1=csys_for_orient)
            
        # Create element set for easy reference
        elemSet = assembly.Set(name=f"{wire_name}_Set", elements=assembly.elements.findAt(((edge.pointOn[0]),)))
        
        return wire_name, elemSet
        
    except Exception as e:
        warnings.warn(f"Error creating CONN3D2 for {wire_name}: {e}")
        print(traceback.format_exc())
        return None, None

# Function to create all X-connector pairs
def create_X_connectors(assembly, model, instance_keys, csys_X, connector_section_name):
    """Creates CONN3D2 connectors for all X-scissor pairs"""
    print("\n--- Creating X-Connectors (CONN3D2) ---")
    
    created_connectors = []
    processed_pairs = set()
    
    for inst_a_name in instance_keys:
        if inst_a_name.startswith("BarX-a_"):
            # Find partner BarX-b instance
            indices_part = inst_a_name.split("BarX-a_", 1)[1]
            partner_b_name = f"BarX-b_{indices_part}"
            
            # Create pair key to avoid duplicates
            pair_key = tuple(sorted((inst_a_name, partner_b_name)))
            
            if partner_b_name in assembly.instances and pair_key not in processed_pairs:
                try:
                    inst_a = assembly.instances[inst_a_name]
                    inst_b = assembly.instances[partner_b_name]
                    
                    # Create CONN3D2 at vertex 2 (adjust index as needed)
                    wire_name, elem_set = create_CONN3D2_connector(
                        assembly=assembly,
                        model=model,
                        instA=inst_a,
                        vIdxA=2,  # Adjust vertex index as needed
                        instB=inst_b,
                        vIdxB=2,  # Adjust vertex index as needed
                        wire_name_base="X_Connector",
                        section_name=connector_section_name,
                        csys_for_orient=csys_X
                    )
                    
                    if wire_name and elem_set:
                        created_connectors.append({
                            'wire_name': wire_name,
                            'element_set': elem_set,
                            'instances': (inst_a_name, partner_b_name)
                        })
                        print(f"Created X-connector: {inst_a_name} <-> {partner_b_name}")
                    
                    processed_pairs.add(pair_key)
                    
                except Exception as e:
                    warnings.warn(f"Failed to create X-connector for pair {inst_a_name}-{partner_b_name}: {e}")
    
    print(f"Total X-connectors created: {len(created_connectors)}")
    return created_connectors

# Function to create all Y-connector pairs  
def create_Y_connectors(assembly, model, instance_keys, csys_Y, connector_section_name):
    """Creates CONN3D2 connectors for all Y-scissor pairs"""
    print("\n--- Creating Y-Connectors (CONN3D2) ---")
    
    created_connectors = []
    processed_pairs = set()
    
    for inst_a_name in instance_keys:
        if inst_a_name.startswith("BarY-a_"):
            # Find partner BarY-b instance
            indices_part = inst_a_name.split("BarY-a_", 1)[1]
            partner_b_name = f"BarY-b_{indices_part}"
            
            # Create pair key to avoid duplicates
            pair_key = tuple(sorted((inst_a_name, partner_b_name)))
            
            if partner_b_name in assembly.instances and pair_key not in processed_pairs:
                try:
                    inst_a = assembly.instances[inst_a_name]
                    inst_b = assembly.instances[partner_b_name]
                    
                    # Create CONN3D2 at vertex 2 (adjust index as needed)
                    wire_name, elem_set = create_CONN3D2_connector(
                        assembly=assembly,
                        model=model,
                        instA=inst_a,
                        vIdxA=2,  # Adjust vertex index as needed
                        instB=inst_b,
                        vIdxB=2,  # Adjust vertex index as needed
                        wire_name_base="Y_Connector",
                        section_name=connector_section_name,
                        csys_for_orient=csys_Y
                    )
                    
                    if wire_name and elem_set:
                        created_connectors.append({
                            'wire_name': wire_name,
                            'element_set': elem_set,
                            'instances': (inst_a_name, partner_b_name)
                        })
                        print(f"Created Y-connector: {inst_a_name} <-> {partner_b_name}")
                    
                    processed_pairs.add(pair_key)
                    
                except Exception as e:
                    warnings.warn(f"Failed to create Y-connector for pair {inst_a_name}-{partner_b_name}: {e}")
    
    print(f"Total Y-connectors created: {len(created_connectors)}")
    return created_connectors

# Usage in your main script:
if prereq_ok and csys_X_obj and csys_Y_obj:
    print("\nStep 7: Create CONN3D2 Connectors")
    
    # Create X-connectors
    x_connectors = create_X_connectors(a, myModel, instance_keys, csys_X_obj, connector_section_name)
    
    # Create Y-connectors  
    y_connectors = create_Y_connectors(a, myModel, instance_keys, csys_Y_obj, connector_section_name)
    
    if x_connectors and y_connectors:
        print(f"Successfully created {len(x_connectors)} X-connectors and {len(y_connectors)} Y-connectors")
    else:
        overall_success = False
        warnings.warn("Failed to create all required connectors")

    # ====================================================================
    # Step 9: Regenerate Assembly (Still useful after feature creation/modification)
    # ====================================================================
print("\nStep 9: Regenerating Assembly...")
a.regenerate()
print("Assembly regenerated.")


 