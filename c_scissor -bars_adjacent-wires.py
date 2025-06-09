# -*- coding: utf-8 -*-
# ====================================================================
# ABAQUS PYTHON SCRIPT: Create & Mesh Adjacent Connector Wires
# (Between Collinear Bar Instances)
#
# !!! IMPORTANT !!!
# This script is intended to run AFTER the main script that creates
# the bar parts and instances.
# It assumes the following variables are already defined and accessible:
#   - myModel: The Abaqus Mdb Model object.
#   - a: The rootAssembly object from myModel.
#   - n_x, n_y, n_z: Integers defining the grid size (used for loops).
#   - Instance naming convention follows: "BasePartName_Zindex_Yindex_Xindex"
#     (e.g., "BarY-b_0_1_2")
# ====================================================================

from abaqus import *
from abaqusConstants import *
import math
import warnings
import traceback # For detailed error messages
import re # For parsing instance names
# Explicitly import mesh module for ElemType
import mesh

# ====================================================================
# 1) Helper Functions (Distance, Vertex Coord)
# ====================================================================

def distance_3d(p1, p2):
    """Calculates the Euclidean distance between two 3D points."""
    try:
        if p1 is None or p2 is None: return float('inf')
        return math.sqrt(sum([(a - b)**2 for a, b in zip(p1, p2)]))
    except TypeError:
        warnings.warn(f"Invalid input for distance calculation: p1={p1}, p2={p2}")
        return float('inf')
    except Exception as e:
        warnings.warn(f"Distance calculation error: {str(e)}")
        return float('inf')

def get_global_vertex_coord(inst_obj, v_index):
    """
    Safely gets the GLOBAL coordinates of a vertex by index from an instance.
    Handles potential errors.
    """
    try:
        if v_index >= len(inst_obj.vertices):
            # warnings.warn(f"Vertex index {v_index} out of bounds for instance '{inst_obj.name}' (has {len(inst_obj.vertices)} vertices).")
            return None
        vertex = inst_obj.vertices[v_index]
        coord = vertex.pointOn[0]
        # print(f"DEBUG: Coord for {inst_obj.name} V{v_index}: {coord}") # Optional debug
        return coord
    except IndexError:
        warnings.warn(f"IndexError getting coord v{v_index} for instance '{inst_obj.name}'.")
        return None
    except Exception as e:
        warnings.warn(f"Error getting coord v{v_index} for instance '{inst_obj.name}': {str(e)}")
        return None

# ====================================================================
# 2) Pre-computation and Checks
# ====================================================================
print("\n--- Pre-computation and Checks (Adjacent Wires) ---")
prerequisites_ok = True

# --- Check if required variables exist ---
if 'myModel' not in globals() or 'a' not in globals():
    print("FATAL ERROR: 'myModel' or root assembly 'a' not defined. Run the previous script first.")
    prerequisites_ok = False
if 'n_x' not in globals() or 'n_y' not in globals() or 'n_z' not in globals():
    warnings.warn("Parameters n_x, n_y, n_z not found. Using default 6,6,6 for loop ranges.")
    n_x, n_y, n_z = 6, 6, 6 # Set defaults if missing, but this might be wrong

# --- Get instance list once (if prerequisites met) ---
all_instance_names = []
if prerequisites_ok:
    try:
        all_instance_names = list(a.instances.keys())
        if not all_instance_names:
            warnings.warn("Assembly instance list is empty! Cannot create adjacent wires.")
            prerequisites_ok = False
        else:
             print(f"  Found {len(all_instance_names)} instances in the assembly.")
    except Exception as e:
        warnings.warn(f"Could not get instance list from assembly 'a': {str(e)}")
        prerequisites_ok = False

# --- Define Connector Element Type ---
# Define once here for use in all meshing sections
connector_element_type = mesh.ElemType(elemCode=CONN3D2)

# ====================================================================
# 3) Create Wires Between Collinear Bars Y-b
# ====================================================================
print("\n#######################################################################################")
print("# --- Creating Wires Between Collinear Bars Y-b ---")
print("#######################################################################################")

# --- Define Parameters for this specific task ---
base_wire_name_dyb = 'wireAdjacent_BarY_b'
vertex_index_A_dyb = 4
vertex_index_B_dyb = 0
target_part_basename_dyb = "BarY-b"
max_connect_distance_dyb = 0.01
dist_tol_dyb = 1e-6
offset_distance_dyb = 1e-4
apply_offset_dyb = True

wires_created_dyb = 0
wire_errors_dyb = 0
skip_wire_creation_dyb = False
# ADDED: List to store names of wires created in this block for meshing
wire_names_dyb = []

# --- Check if the FIRST potential wire already exists ---
if prerequisites_ok:
    first_wire_name_dyb = f"{base_wire_name_dyb}_1"
    try:
        skip_wire_creation_dyb = first_wire_name_dyb in a.features
    except Exception as feat_check_e:
        warnings.warn(f"Could not check for existing feature '{first_wire_name_dyb}': {str(feat_check_e)}")
        skip_wire_creation_dyb = False

if skip_wire_creation_dyb:
    print(f"First adjacent wire '{first_wire_name_dyb}' exists. Assuming all adjacent Y-b wires exist, skipping creation.")
elif not prerequisites_ok:
    print("Prerequisites not met. Skipping adjacent Y-b wire creation.")
else:
    print(f"Proceeding with adjacent Y-b wire creation loop (Max Dist: {max_connect_distance_dyb})...")
    current_wire_index = 0
    processed_pair_keys = set()

    for inst_name_A in all_instance_names:
        if not inst_name_A.startswith(target_part_basename_dyb): continue
        try:
            match = re.search(r'_(\d+)_(\d+)_(\d+)$', inst_name_A)
            if not match: continue
            i, j, k = map(int, match.groups())
        except Exception as parse_e:
            warnings.warn(f"Error parsing indices from instance name '{inst_name_A}': {str(parse_e)}"); continue

        i_B, j_B, k_B = i + 1, j, k + 1
        inst_name_B = f'{target_part_basename_dyb}_{i_B}_{j_B}_{k_B}'

        if inst_name_B in a.instances:
            pair_key = tuple(sorted((inst_name_A, inst_name_B)))
            if pair_key in processed_pair_keys: continue
            processed_pair_keys.add(pair_key)

            inst_A = None; inst_B = None; coord_A = None; coord_B = None; wire_feature = None
            rename_success = False; default_name = None
            try:
                inst_A = a.instances[inst_name_A]
                inst_B = a.instances[inst_name_B]
                coord_A = get_global_vertex_coord(inst_A, vertex_index_A_dyb)
                coord_B = get_global_vertex_coord(inst_B, vertex_index_B_dyb)
                if coord_A is None or coord_B is None: continue

                dist = distance_3d(coord_A, coord_B)
                if dist >= max_connect_distance_dyb: continue

                wire_coord_A = coord_A
                wire_coord_B = coord_B
                if apply_offset_dyb and dist < dist_tol_dyb:
                    wire_coord_B = (coord_B[0], coord_B[1], coord_B[2] + offset_distance_dyb)
                    # print(f"  Applied Z-offset between {inst_name_A} V{vertex_index_A_dyb} and {inst_name_B} V{vertex_index_B_dyb}")

                wire_points_tuple = (wire_coord_A, wire_coord_B)
                # CHANGED: Ensure wire is meshable
                wire_feature = a.WirePolyLine(points=wire_points_tuple, mergeType=SEPARATE, meshable=ON)
                if not wire_feature or not hasattr(wire_feature, 'name'): raise ValueError("WirePolyLine failed.")
                default_name = wire_feature.name

                current_wire_index += 1
                desired_name = f"{base_wire_name_dyb}_{current_wire_index}"

                if default_name == desired_name: rename_success = True
                else:
                    if desired_name in a.features:
                         try: del a.features[desired_name]
                         except Exception as del_e: warnings.warn(f"!! Could not delete existing feature '{desired_name}': {repr(del_e)}")
                    try:
                        a.features.changeKey(fromName=default_name, toName=desired_name)
                        rename_success = True
                    except Exception as rename_e:
                        warnings.warn(f"!! WARNING: features.changeKey failed for '{default_name}'->'{desired_name}': {repr(rename_e)}"); rename_success = False

                if rename_success:
                    wires_created_dyb += 1
                    wire_names_dyb.append(desired_name) # ADDED: Store name for meshing

            except Exception as e:
                warnings.warn(f"!! FAILED processing connection {inst_name_A} -> {inst_name_B}: {repr(e)}")
                wire_errors_dyb += 1
                if default_name and not rename_success and default_name in a.features:
                     try: del a.features[default_name]
                     except: pass
    print(f"\nFinished Adjacent Y-b wire creation/rename attempt.")
    print(f"  Wires created/renamed in this run: {wires_created_dyb}")
    if wire_errors_dyb > 0: print(f"  Encountered {wire_errors_dyb} errors.")


# ====================================================================
# 4) Create Wires Between Collinear Bars Y-a
# ====================================================================
print("\n#######################################################################################")
print("# --- Creating Wires Between Collinear Bars Y-a ---")
print("#######################################################################################")

# --- Define Parameters ---
base_wire_name_adya = 'wireAdjacent_BarY_a'
vertex_index_A_adya = 4
vertex_index_B_adya = 0
target_part_basename_adya = "BarY-a"
max_connect_distance_adya = 0.01
dist_tol_adya = 1e-6
offset_distance_adya = 1e-4
apply_offset_adya = True

wires_created_adya = 0
wire_errors_adya = 0
skip_wire_creation_adya = False
# ADDED: List to store names of wires created in this block for meshing
wire_names_adya = []

# --- Check if FIRST wire of THIS type exists ---
if prerequisites_ok:
    first_wire_name_adya = f"{base_wire_name_adya}_1"
    try:
        skip_wire_creation_adya = first_wire_name_adya in a.features
    except Exception as feat_check_e:
        warnings.warn(f"Could not check for existing feature '{first_wire_name_adya}': {str(feat_check_e)}")
        skip_wire_creation_adya = False

if skip_wire_creation_adya:
    print(f"First adjacent wire '{first_wire_name_adya}' exists. Assuming all adjacent Y-a wires exist, skipping creation.")
elif not prerequisites_ok:
    print("Prerequisites not met. Skipping adjacent Y-a wire creation.")
else:
    print(f"Proceeding with adjacent Y-a wire creation loop (Max Dist: {max_connect_distance_adya})...")
    current_wire_index = 0
    processed_pair_keys = set()

    for inst_name_A in all_instance_names:
        if not inst_name_A.startswith(target_part_basename_adya): continue
        try:
            match = re.search(r'_(\d+)_(\d+)_(\d+)$', inst_name_A)
            if not match: continue
            i, j, k = map(int, match.groups())
        except Exception as parse_e:
            warnings.warn(f"Error parsing indices from instance name '{inst_name_A}': {str(parse_e)}"); continue

        i_B, j_B, k_B = i + 1, j, k - 1
        inst_name_B = f'{target_part_basename_adya}_{i_B}_{j_B}_{k_B}'

        if inst_name_B in a.instances:
            pair_key = tuple(sorted((inst_name_A, inst_name_B)))
            if pair_key in processed_pair_keys: continue
            processed_pair_keys.add(pair_key)

            inst_A = None; inst_B = None; coord_A = None; coord_B = None; wire_feature = None
            rename_success = False; default_name = None
            try:
                inst_A = a.instances[inst_name_A]
                inst_B = a.instances[inst_name_B]
                coord_A = get_global_vertex_coord(inst_A, vertex_index_A_adya)
                coord_B = get_global_vertex_coord(inst_B, vertex_index_B_adya)
                if coord_A is None or coord_B is None: continue

                dist = distance_3d(coord_A, coord_B)
                if dist >= max_connect_distance_adya: continue

                wire_coord_A = coord_A
                wire_coord_B = coord_B
                if apply_offset_adya and dist < dist_tol_adya:
                    wire_coord_B = (coord_B[0], coord_B[1], coord_B[2] + offset_distance_adya)
                    # print(f"  Applied Z-offset between {inst_name_A} V{vertex_index_A_adya} and {inst_name_B} V{vertex_index_B_adya}")

                wire_points_tuple = (wire_coord_A, wire_coord_B)
                # CHANGED: Ensure wire is meshable
                wire_feature = a.WirePolyLine(points=wire_points_tuple, mergeType=SEPARATE, meshable=ON)
                if not wire_feature or not hasattr(wire_feature, 'name'): raise ValueError("WirePolyLine failed.")
                default_name = wire_feature.name

                current_wire_index += 1
                desired_name = f"{base_wire_name_adya}_{current_wire_index}"

                if default_name == desired_name: rename_success = True
                else:
                    if desired_name in a.features:
                         try: del a.features[desired_name]
                         except Exception as del_e: warnings.warn(f"!! Could not delete existing feature '{desired_name}': {repr(del_e)}")
                    try:
                        a.features.changeKey(fromName=default_name, toName=desired_name)
                        rename_success = True
                    except Exception as rename_e:
                        warnings.warn(f"!! WARNING: features.changeKey failed for '{default_name}'->'{desired_name}': {repr(rename_e)}"); rename_success = False

                if rename_success:
                    wires_created_adya += 1
                    wire_names_adya.append(desired_name) # ADDED: Store name for meshing

            except Exception as e:
                warnings.warn(f"!! FAILED processing connection {inst_name_A} V{vertex_index_A_adya} -> {inst_name_B} V{vertex_index_B_adya}: {repr(e)}")
                wire_errors_adya += 1
                if default_name and not rename_success and default_name in a.features:
                     try: del a.features[default_name]
                     except: pass
    print(f"\nFinished Adjacent Y-a wire creation/rename attempt.")
    print(f"  Wires created/renamed in this run: {wires_created_adya}")
    if wire_errors_adya > 0: print(f"  Encountered {wire_errors_adya} errors.")


# ====================================================================
# 5) Create Wires Between Collinear Bars X-b
# ====================================================================
print("\n#######################################################################################")
print("# --- Creating Wires Between Collinear Bars X-b ---")
print("#######################################################################################")

# --- Define Parameters ---
base_wire_name_axb = 'wireAdjacent_BarX_b'
vertex_index_A_axb = 4
vertex_index_B_axb = 0
target_part_basename_axb = "BarX-b"
max_connect_distance_axb = 0.01
dist_tol_axb = 1e-6
offset_distance_axb = 1e-4
apply_offset_axb = True

wires_created_axb = 0
wire_errors_axb = 0
skip_wire_creation_axb = False
# ADDED: List to store names of wires created in this block for meshing
wire_names_axb = []

# --- Check if FIRST wire of THIS type exists ---
if prerequisites_ok:
    first_wire_name_axb = f"{base_wire_name_axb}_1"
    try:
        skip_wire_creation_axb = first_wire_name_axb in a.features
    except Exception as feat_check_e:
        warnings.warn(f"Could not check for existing feature '{first_wire_name_axb}': {str(feat_check_e)}")
        skip_wire_creation_axb = False

if skip_wire_creation_axb:
    print(f"First wire '{first_wire_name_axb}' exists. Assuming all Adjacent X-b wires exist, skipping creation.")
elif not prerequisites_ok:
    print("Prerequisites not met. Skipping adjacent X-b wire creation.")
else:
    print(f"Proceeding with adjacent X-b wire creation loop (Max Dist: {max_connect_distance_axb})...")
    current_wire_index = 0
    processed_pair_keys = set()

    for inst_name_A in all_instance_names:
        if not inst_name_A.startswith(target_part_basename_axb): continue
        try:
            match = re.search(r'_(\d+)_(\d+)_(\d+)$', inst_name_A)
            if not match: continue
            i, j, k = map(int, match.groups())
        except Exception as parse_e:
            warnings.warn(f"Error parsing indices from instance name '{inst_name_A}': {str(parse_e)}"); continue

        i_B, j_B, k_B = i + 1, j + 1, k
        inst_name_B = f'{target_part_basename_axb}_{i_B}_{j_B}_{k_B}'

        if inst_name_B in a.instances:
            pair_key = tuple(sorted((inst_name_A, inst_name_B)))
            if pair_key in processed_pair_keys: continue
            processed_pair_keys.add(pair_key)

            inst_A = None; inst_B = None; coord_A = None; coord_B = None; wire_feature = None
            rename_success = False; default_name = None
            try:
                inst_A = a.instances[inst_name_A]
                inst_B = a.instances[inst_name_B]
                coord_A = get_global_vertex_coord(inst_A, vertex_index_A_axb)
                coord_B = get_global_vertex_coord(inst_B, vertex_index_B_axb)
                if coord_A is None or coord_B is None: continue

                dist = distance_3d(coord_A, coord_B)
                if dist >= max_connect_distance_axb: continue

                wire_coord_A = coord_A
                wire_coord_B = coord_B
                if apply_offset_axb and dist < dist_tol_axb:
                    wire_coord_B = (coord_B[0], coord_B[1], coord_B[2] + offset_distance_axb)
                    # print(f"  Applied Z-offset between {inst_name_A} V{vertex_index_A_axb} and {inst_name_B} V{vertex_index_B_axb}")

                wire_points_tuple = (wire_coord_A, wire_coord_B)
                # CHANGED: Ensure wire is meshable
                wire_feature = a.WirePolyLine(points=wire_points_tuple, mergeType=SEPARATE, meshable=ON)
                if not wire_feature or not hasattr(wire_feature, 'name'): raise ValueError("WirePolyLine failed.")
                default_name = wire_feature.name

                current_wire_index += 1
                desired_name = f"{base_wire_name_axb}_{current_wire_index}"

                if default_name == desired_name: rename_success = True
                else:
                    if desired_name in a.features:
                         try: del a.features[desired_name]
                         except Exception as del_e: warnings.warn(f"!! Could not delete existing feature '{desired_name}': {repr(del_e)}")
                    try:
                        a.features.changeKey(fromName=default_name, toName=desired_name)
                        rename_success = True
                    except Exception as rename_e:
                        warnings.warn(f"!! WARNING: features.changeKey failed for '{default_name}'->'{desired_name}': {repr(rename_e)}"); rename_success = False

                if rename_success:
                    wires_created_axb += 1
                    wire_names_axb.append(desired_name) # ADDED: Store name for meshing

            except Exception as e:
                warnings.warn(f"!! FAILED processing connection {inst_name_A} V{vertex_index_A_axb} -> {inst_name_B} V{vertex_index_B_axb}: {repr(e)}")
                wire_errors_axb += 1
                if default_name and not rename_success and default_name in a.features:
                     try: del a.features[default_name]
                     except: pass
    print(f"\nFinished Adjacent X-b wire creation/rename attempt.")
    print(f"  Wires created/renamed in this run: {wires_created_axb}")
    if wire_errors_axb > 0: print(f"  Encountered {wire_errors_axb} errors.")


# ====================================================================
# 6) Create Wires Between Collinear Bars X-a
# ====================================================================
print("\n#######################################################################################")
print("# --- Creating Wires Between Collinear Bars X-a ---")
print("#######################################################################################")

# --- Define Parameters ---
base_wire_name_axa = 'wireAdjacent_BarX_a'
vertex_index_A_axa = 0
vertex_index_B_axa = 4
target_part_basename_axa = "BarX-a"
max_connect_distance_axa = 0.01
dist_tol_axa = 1e-6
offset_distance_axa = 1e-4
apply_offset_axa = True

wires_created_axa = 0
wire_errors_axa = 0
skip_wire_creation_axa = False
# ADDED: List to store names of wires created in this block for meshing
wire_names_axa = []

# --- Check if FIRST wire of THIS type exists ---
if prerequisites_ok:
    first_wire_name_axa = f"{base_wire_name_axa}_1"
    try:
        skip_wire_creation_axa = first_wire_name_axa in a.features
    except Exception as feat_check_e:
        warnings.warn(f"Could not check for existing feature '{first_wire_name_axa}': {str(feat_check_e)}")
        skip_wire_creation_axa = False

if skip_wire_creation_axa:
    print(f"  First wire '{first_wire_name_axa}' exists. Assuming all Adjacent X-a wires exist, skipping creation.")
elif not prerequisites_ok:
     print("Prerequisites not met. Skipping adjacent X-a wire creation.")
else:
    print(f"  Proceeding with adjacent X-a wire creation loop (Max Dist: {max_connect_distance_axa})...")
    current_wire_index = 0
    processed_pair_keys = set()

    for inst_name_A in all_instance_names:
        if not inst_name_A.startswith(target_part_basename_axa): continue
        try:
            match = re.search(r'_(\d+)_(\d+)_(\d+)$', inst_name_A)
            if not match: continue
            i, j, k = map(int, match.groups())
        except Exception as parse_e:
            warnings.warn(f"Error parsing indices from instance name '{inst_name_A}': {str(parse_e)}"); continue

        i_B, j_B, k_B = i + 1, j - 1, k
        inst_name_B = f'{target_part_basename_axa}_{i_B}_{j_B}_{k_B}'

        if inst_name_B in a.instances:
            pair_key = tuple(sorted((inst_name_A, inst_name_B)))
            if pair_key in processed_pair_keys: continue
            processed_pair_keys.add(pair_key)

            inst_A = None; inst_B = None; coord_A = None; coord_B = None; wire_feature = None
            rename_success = False; default_name = None
            try:
                inst_A = a.instances[inst_name_A]
                inst_B = a.instances[inst_name_B]
                coord_A = get_global_vertex_coord(inst_A, vertex_index_A_axa)
                coord_B = get_global_vertex_coord(inst_B, vertex_index_B_axa)
                if coord_A is None or coord_B is None: continue

                dist = distance_3d(coord_A, coord_B)
                if dist >= max_connect_distance_axa: continue

                wire_coord_A = coord_A
                wire_coord_B = coord_B
                if apply_offset_axa and dist < dist_tol_axa:
                    wire_coord_B = (coord_B[0], coord_B[1], coord_B[2] + offset_distance_axa)
                    # print(f"  Applied Z-offset between {inst_name_A} V{vertex_index_A_axa} and {inst_name_B} V{vertex_index_B_axa}")

                wire_points_tuple = (wire_coord_A, wire_coord_B)
                # CHANGED: Ensure wire is meshable
                wire_feature = a.WirePolyLine(points=wire_points_tuple, mergeType=SEPARATE, meshable=ON)
                if not wire_feature or not hasattr(wire_feature, 'name'): raise ValueError("WirePolyLine failed.")
                default_name = wire_feature.name

                current_wire_index += 1
                desired_name = f"{base_wire_name_axa}_{current_wire_index}"

                if default_name == desired_name: rename_success = True
                else:
                    if desired_name in a.features:
                         try: del a.features[desired_name]
                         except Exception as del_e: warnings.warn(f"!! Could not delete existing feature '{desired_name}': {repr(del_e)}")
                    try:
                        a.features.changeKey(fromName=default_name, toName=desired_name)
                        rename_success = True
                    except Exception as rename_e:
                        warnings.warn(f"!! WARNING: features.changeKey failed for '{default_name}'->'{desired_name}': {repr(rename_e)}"); rename_success = False

                if rename_success:
                    wires_created_axa += 1
                    wire_names_axa.append(desired_name) # ADDED: Store name for meshing

            except Exception as e:
                warnings.warn(f"!! FAILED processing connection {inst_name_A} V{vertex_index_A_axa} -> {inst_name_B} V{vertex_index_B_axa}: {repr(e)}")
                wire_errors_axa += 1
                if default_name and not rename_success and default_name in a.features:
                     try: del a.features[default_name]
                     except: pass
    print(f"\nFinished Adjacent X-a wire creation/rename attempt.")
    print(f"  Wires created/renamed in this run: {wires_created_axa}")
    if wire_errors_axa > 0: print(f"  Encountered {wire_errors_axa} errors.")


# ====================================================================
# 7) Mesh Adjacent Connector Wires (NEW STEP)
# ====================================================================
print("\n#######################################################################################")
print("# --- Meshing Adjacent Connector Wires ---")
print("#######################################################################################")

# Combine all adjacent wire names created in this script run
all_adjacent_wire_names = wire_names_dyb + wire_names_adya + wire_names_axb + wire_names_axa
print(f"Attempting to mesh {len(all_adjacent_wire_names)} adjacent wire features created in this run...")

mesh_errors = 0
edges_to_mesh = []

if all_adjacent_wire_names:
    # Collect all edges from the newly created features
    for wire_name in all_adjacent_wire_names:
        try:
            if wire_name in a.features:
                feat = a.features[wire_name]
                # Important: Access edges AFTER potential regeneration if CSYS were created,
                # or ensure regeneration happens before this step if run separately.
                # Assuming regeneration happened if needed in CSYS creation.
                if hasattr(feat, 'edges') and feat.edges:
                     edges_to_mesh.extend(feat.edges)
                else:
                     # Try getting edges by index if direct access fails (less reliable)
                     edge_indices = a.getFeatureEdges(wire_name)
                     if edge_indices:
                          for idx in edge_indices:
                               try: edges_to_mesh.append(a.edges[idx])
                               except: warnings.warn(f"Could not get edge object for index {idx} from feature {wire_name}")
                     else:
                          warnings.warn(f"Could not retrieve edges for feature '{wire_name}'.")
            else:
                warnings.warn(f"Feature '{wire_name}' not found during edge collection for meshing.")
        except Exception as e_get:
            warnings.warn(f"Error getting edges for feature '{wire_name}': {str(e_get)}")
            mesh_errors += 1

    if edges_to_mesh:
        print(f"  Collected {len(edges_to_mesh)} edges to mesh.")
        try:
            # Seed the collected edges (one element per wire)
            a.seedEdgeByNumber(edges=edges_to_mesh, number=1, constraint=FINER)
            print(f"  Seeded {len(edges_to_mesh)} edges with 1 element each.")

            # Set element type for the collected edges
            # Need to create a region from the edges
            region_to_mesh = regionToolset.Region(edges=edges_to_mesh)
            a.setElementType(regions=region_to_mesh, elemTypes=(connector_element_type,))
            print(f"  Assigned {connector_element_type.elemCode.name} element type to collected edges.")

            # Generate mesh for these specific edges
            # Note: This only meshes the specified edges. If other parts of the
            # assembly need meshing, that should be handled separately.
            # a.generateMesh(regions=edges_to_mesh) # Meshing assembly edges directly can be tricky
            # It's often better to mesh instances or the whole assembly if appropriate
            # For connector wires added to assembly, meshing the assembly might be needed
            # Let's assume assembly meshing happens LATER or is handled elsewhere.
            # We have set the seeds and element types.
            print(f"  Seeds and element types set for {len(edges_to_mesh)} adjacent wire edges.")
            print(f"  IMPORTANT: Ensure assembly mesh generation occurs AFTER this step.")


        except Exception as e_mesh:
            warnings.warn(f"!! ERROR during meshing steps for adjacent wires: {str(e_mesh)}")
            print(traceback.format_exc())
            mesh_errors += 1
    else:
        print("  No valid edges collected for meshing.")

if mesh_errors > 0:
    print(f"  Encountered {mesh_errors} errors during meshing setup.")
    overall_success = False # Mark failure if meshing had errors

# ====================================================================
# 8) Final Summary
# ====================================================================
print("\n--- Finished Adjacent Wire Creation & Meshing Setup Script ---")
total_created = wires_created_dyb + wires_created_adya + wires_created_axb + wires_created_axa
total_errors = wire_errors_dyb + wire_errors_adya + wire_errors_axb + wire_errors_axa + mesh_errors # Include mesh errors
print(f"Summary:")
print(f"  Adjacent Y-b Wires Created/Renamed: {wires_created_dyb}")
print(f"  Adjacent Y-a Wires Created/Renamed: {wires_created_adya}")
print(f"  Adjacent X-b Wires Created/Renamed: {wires_created_axb}")
print(f"  Adjacent X-a Wires Created/Renamed: {wires_created_axa}")
print(f"  -----------------------------------------")
print(f"  Total Adjacent Wires Created/Renamed: {total_created}")
if total_errors > 0:
    print(f"  Total Errors Encountered (Creation/Meshing): {total_errors}")
print("  NOTE: No Sets were created for these wires by this script.")
print("  NOTE: Meshing seeds & element types were assigned to newly created wires.")
print("        Ensure assembly mesh generation includes these wires.")
print("======================================================")
# === End of Script ===
