# -*- coding: utf-8 -*-
# ====================================================================
# ABAQUS PYTHON SCRIPT: Create Endpoint Connector Wires
# (Between Reference Points and Bar Instance Vertices)
#
# !!! IMPORTANT !!!
# This script is intended to run AFTER the main script that creates
# the bar parts, instances, and reference points (RPs).
# It assumes the following variables are already defined and accessible:
#   - myModel: The Abaqus Mdb Model object.
#   - a: The rootAssembly object from myModel.
#   - rp_data_list: A list or similar iterable containing tuples,
#                   where each tuple is (rp_obj, rp_coord).
#                   rp_obj is the ReferencePoint object, and
#                   rp_coord is a tuple (x, y, z) of its coordinates.
#                   Example: rp_data_list = [(a.referencePoints[1], (10,0,0)), ...]
# ====================================================================

from abaqus import *
from abaqusConstants import *
import math
import warnings
import traceback # For detailed error messages

# ====================================================================
# 1) Script Parameters
# ====================================================================
# --- Wire Naming ---
base_wire_name_x = "wire_RP_end_of_BarX" # Base name for wires connecting to BarX instances
base_wire_name_y = "wire_RP_end_of_BarY" # Base name for wires connecting to BarY instances

# --- Connection Logic ---
# Max distance between an RP and a vertex to be considered connected
max_distance = 0.01     # <<< ADJUST AS NEEDED (units depend on your model)
# Tolerance to consider points coincident (if dist < dist_tol, apply offset)
dist_tol = 1e-6         # <<< ADJUST AS NEEDED
# Offset applied to the vertex coordinate if points are coincident
# NOTE: The provided code applies offset only to the X-coordinate.
#       Consider applying to Z (e.g., + offset_distance) if that's more appropriate.
offset_distance = 1e-4  # <<< ADJUST AS NEEDED
# Vertex indices on the BarX/BarY instances to check for connections
# These indices MUST correspond to the endpoints after partitioning in the previous script.
candidate_indices = [0, 4] # <<< VERIFY THESE INDICES ARE CORRECT FOR YOUR PARTITIONED BARS

print("======================================================")
print("--- Running Endpoint Wire Creation Script ---")
print(f"Max Connection Distance: {max_distance}")
print(f"Coincidence Tolerance: {dist_tol}")
print(f"Offset Distance: {offset_distance}")
print(f"Candidate Vertex Indices: {candidate_indices}")
print("======================================================")

# ====================================================================
# 2) Helper Functions (Distance, Vertex Coord)
# ====================================================================
def distance_3d(p1, p2):
    """Calculates the Euclidean distance between two 3D points."""
    try:
        # Use list comprehension for safety, although generator should work
        return math.sqrt(sum([(a - b)**2 for a, b in zip(p1, p2)]))
    except TypeError:
        # Handle cases where p1 or p2 might not be valid coordinate tuples
        warnings.warn(f"Invalid input for distance calculation: p1={p1}, p2={p2}")
        return float('inf')
    except Exception as e:
        warnings.warn(f"Distance calculation error: {str(e)}")
        return float('inf')

def get_vtx_coord(inst_obj, v_index):
    """Safely gets the coordinates of a vertex by index from an instance."""
    try:
        if v_index >= len(inst_obj.vertices):
            # This check is important as accessing out-of-bounds index raises IndexError
            # warnings.warn(f"Vertex index {v_index} out of bounds for instance '{inst_obj.name}' (has {len(inst_obj.vertices)} vertices).")
            return None
        # Access vertex and then its coordinates
        vertex = inst_obj.vertices[v_index]
        return vertex.pointOn[0]
    except IndexError:
        # Should be caught by the length check above, but included for safety
        warnings.warn(f"IndexError getting coord v{v_index} for instance '{inst_obj.name}'.")
        return None
    except Exception as e:
        # Catch other potential errors (e.g., accessing .pointOn)
        warnings.warn(f"Error getting coord v{v_index} for instance '{inst_obj.name}': {str(e)}")
        return None

# ====================================================================
# 3) Pre-computation and Checks
# ====================================================================
print("\n--- Pre-computation and Checks ---")
instances_valid = True
rps_valid = True

# --- Check if required variables exist ---
if 'myModel' not in globals() or 'a' not in globals():
    print("FATAL ERROR: 'myModel' or root assembly 'a' not defined. Run the previous script first.")
    instances_valid = False # Treat as fatal
if 'rp_data_list' not in globals():
    print("FATAL ERROR: 'rp_data_list' not defined. Ensure RPs were created and data stored.")
    rps_valid = False # Treat as fatal

# --- Get instance list once (if prerequisites met) ---
instance_list = []
if instances_valid and rps_valid:
    try:
        # Use items() to get (name, object) pairs directly
        instance_list = list(a.instances.items())
        if not instance_list:
            warnings.warn("Assembly instance list is empty!")
            # Don't mark as invalid, maybe no instances are expected yet
        else:
             print(f"  Found {len(instance_list)} instances in the assembly.")
    except Exception as e:
        warnings.warn(f"Could not get instance list from assembly 'a': {str(e)}")
        instances_valid = False # Cannot proceed without instances

# --- Check RP data ---
if rps_valid:
    if not rp_data_list:
        warnings.warn("RP data list ('rp_data_list') is empty. No endpoint wires can be created.")
        rps_valid = False # Cannot proceed without RPs
    else:
         print(f"  Found {len(rp_data_list)} RP data entries.")

# ====================================================================
# 4) Create and Rename Endpoint Wires (SEPARATE X and Y Loops)
# ====================================================================
print("\n--- Starting Endpoint Wire Creation Section (Separate X/Y) ---")

# --- Block 4A: Process BarX Endpoint Wires ---
print(f"\nChecking/Creating Endpoint Wires for BarX ('{base_wire_name_x}*')...")
wires_created_x = 0
wire_errors_x = 0
skip_x_endpoint_wires = False

# Check if the first potential wire already exists to allow skipping if re-run
if instances_valid and rps_valid: # Only check if prerequisites are met
    try:
        first_wire_name_x = f"{base_wire_name_x}_1"
        skip_x_endpoint_wires = first_wire_name_x in a.features
    except Exception as feat_check_e:
        warnings.warn(f"Check failed for feature '{first_wire_name_x}': {str(feat_check_e)}")
        # Assume we should not skip if check fails
        skip_x_endpoint_wires = False

if skip_x_endpoint_wires:
    print(f"  First potential wire '{first_wire_name_x}' exists. Skipping BarX endpoint wire creation.")
elif not instances_valid or not rps_valid:
    print("  Prerequisites not met (Instances or RPs missing/invalid). Skipping BarX endpoint wire creation.")
else:
    print("  Proceeding with BarX endpoint wire creation loop...")
    current_x_index = 0 # Counter for X wire naming

    # Loop through RPs
    for rp_index, rp_data in enumerate(rp_data_list):
        try:
            rp_obj, rp_coord = rp_data # Unpack RP object and coordinates
        except (TypeError, ValueError):
            warnings.warn(f"  Skipping invalid RP data entry at index {rp_index}: {rp_data}")
            continue

        # Loop through Instances
        for inst_name, inst_obj in instance_list:
            # Filter for BarX ONLY
            if not inst_name.startswith("BarX"): # Make sure prefix matches instance names
                continue

            # Loop through Candidate Vertices on this instance
            for v_index in candidate_indices:
                v_coord = get_vtx_coord(inst_obj, v_index)
                if v_coord is None: continue # Skip if vertex coord retrieval failed

                # Check distance between RP and vertex
                dist = distance_3d(rp_coord, v_coord)

                if dist < max_distance: # Found a potential X connection
                    # Apply offset if points are nearly identical
                    wire_coord_B = v_coord
                    if dist < dist_tol:
                        # Apply offset to X coordinate (as per original user code)
                        wire_coord_B = (v_coord[0] + offset_distance, v_coord[1], v_coord[2])
                        # print(f"DEBUG: Applied offset for RP {rp_index} <-> {inst_name} V{v_index}") # Optional

                    # --- Create and Rename Wire Feature ---
                    wire_feature = None # Reset for each attempt
                    default_name = None
                    rename_success = False
                    try:
                        # Points for the wire
                        wire_points_tuple = (rp_coord, wire_coord_B)

                        # Create the wire feature
                        wire_feature = a.WirePolyLine(points=wire_points_tuple,
                                                      mergeType=SEPARATE,
                                                      meshable=OFF) # Ensure non-meshable

                        # Check if feature creation returned an object
                        if not wire_feature or not hasattr(wire_feature, 'name'):
                            raise ValueError("WirePolyLine command failed or returned invalid object.")

                        default_name = wire_feature.name # Get the auto-generated name

                        # Increment counter and generate desired name
                        current_x_index += 1
                        desired_name = f"{base_wire_name_x}_{current_x_index}"

                        # Rename the feature
                        if default_name == desired_name:
                            # print(f"DEBUG: Wire already has desired name: {desired_name}") # Optional
                            rename_success = True
                        else:
                            # Check if desired name already exists (e.g., from previous run)
                            if desired_name in a.features:
                                try:
                                    # print(f"DEBUG: Deleting existing feature with desired name: {desired_name}") # Optional
                                    del a.features[desired_name]
                                except Exception as del_e:
                                     warnings.warn(f"!! Could not delete existing feature '{desired_name}': {repr(del_e)}")
                                     # Continue, changeKey might still work or fail cleanly

                            # Attempt rename
                            try:
                                a.features.changeKey(fromName=default_name, toName=desired_name)
                                # print(f"DEBUG: Renamed '{default_name}' to '{desired_name}'") # Optional
                                rename_success = True
                            except Exception as rename_e:
                                warnings.warn(f"!! Rename failed '{default_name}' -> '{desired_name}': {repr(rename_e)}")
                                rename_success = False

                        # Increment success counter only if rename succeeded (or wasn't needed)
                        if rename_success:
                            wires_created_x += 1

                    except Exception as e_wire:
                        # Catch errors during WirePolyLine or renaming
                        rp_name_str = getattr(rp_obj, 'name', f'RP_Index_{rp_index}') # Get RP name safely
                        warnings.warn(f"!! FAILED BarX wire {rp_name_str} <-> {inst_name} V{v_index}: {repr(e_wire)}")
                        wire_errors_x += 1
                        # Clean up partially created feature if rename failed but creation succeeded
                        if default_name and not rename_success and default_name in a.features:
                             try: del a.features[default_name]
                             except: pass
                    # --- End Try-Except for one X wire ---
    print(f"  Finished BarX wires loop. Created/Renamed: {wires_created_x}. Errors: {wire_errors_x}.")


# --- Block 4B: Process BarY Endpoint Wires ---
print(f"\nChecking/Creating Endpoint Wires for BarY ('{base_wire_name_y}*')...")
wires_created_y = 0
wire_errors_y = 0
skip_y_endpoint_wires = False

# Check if the first potential wire already exists
if instances_valid and rps_valid: # Only check if prerequisites met
    try:
        first_wire_name_y = f"{base_wire_name_y}_1"
        skip_y_endpoint_wires = first_wire_name_y in a.features
    except Exception as feat_check_e:
        warnings.warn(f"Check failed for feature '{first_wire_name_y}': {str(feat_check_e)}")
        skip_y_endpoint_wires = False

if skip_y_endpoint_wires:
    print(f"  First potential wire '{first_wire_name_y}' exists. Skipping BarY endpoint wire creation.")
elif not instances_valid or not rps_valid:
    print("  Prerequisites not met (Instances or RPs missing/invalid). Skipping BarY endpoint wire creation.")
else:
    print("  Proceeding with BarY endpoint wire creation loop...")
    current_y_index = 0 # Counter for Y wire naming

    # Loop through RPs
    for rp_index, rp_data in enumerate(rp_data_list):
        try:
            rp_obj, rp_coord = rp_data # Unpack
        except (TypeError, ValueError):
            # Warning printed in X loop, maybe skip here unless debugging needed
            # warnings.warn(f"  Skipping invalid RP data entry at index {rp_index}: {rp_data}")
            continue

        # Loop through Instances
        for inst_name, inst_obj in instance_list: # Use same instance list
            # Filter for BarY ONLY
            if not inst_name.startswith("BarY"): # Make sure prefix matches instance names
                continue

            # Loop through Candidate Vertices
            for v_index in candidate_indices:
                v_coord = get_vtx_coord(inst_obj, v_index)
                if v_coord is None: continue

                # Check distance
                dist = distance_3d(rp_coord, v_coord)

                if dist < max_distance: # Found a potential Y connection
                    # Apply offset if points are nearly identical
                    wire_coord_B = v_coord
                    if dist < dist_tol:
                        wire_coord_B = (v_coord[0] + offset_distance, v_coord[1], v_coord[2])

                    # --- Create and Rename Wire Feature ---
                    wire_feature = None
                    default_name = None
                    rename_success = False
                    try:
                        wire_points_tuple = (rp_coord, wire_coord_B)
                        wire_feature = a.WirePolyLine(points=wire_points_tuple,
                                                      mergeType=SEPARATE,
                                                      meshable=OFF)

                        if not wire_feature or not hasattr(wire_feature, 'name'):
                            raise ValueError("WirePolyLine command failed or returned invalid object.")

                        default_name = wire_feature.name

                        current_y_index += 1 # Increment Y counter
                        desired_name = f"{base_wire_name_y}_{current_y_index}" # Use Y base name

                        if default_name == desired_name:
                            rename_success = True
                        else:
                            if desired_name in a.features:
                                try: del a.features[desired_name]
                                except Exception as del_e: warnings.warn(f"!! Could not delete existing feature '{desired_name}': {repr(del_e)}")
                            try:
                                a.features.changeKey(fromName=default_name, toName=desired_name)
                                rename_success = True
                            except Exception as rename_e:
                                warnings.warn(f"!! Rename failed '{default_name}' -> '{desired_name}': {repr(rename_e)}")
                                rename_success = False

                        if rename_success:
                            wires_created_y += 1

                    except Exception as e_wire:
                        rp_name_str = getattr(rp_obj, 'name', f'RP_Index_{rp_index}')
                        warnings.warn(f"!! FAILED BarY wire {rp_name_str} <-> {inst_name} V{v_index}: {repr(e_wire)}")
                        wire_errors_y += 1
                        if default_name and not rename_success and default_name in a.features:
                             try: del a.features[default_name]
                             except: pass
                    # --- End Try-Except for one Y wire ---
    print(f"  Finished BarY wires loop. Created/Renamed: {wires_created_y}. Errors: {wire_errors_y}.")


# ====================================================================
# 5) Final Summary
# ====================================================================
print("\n--- Finished Endpoint Wire Creation Script ---")
# Use the specific counters from each block
total_wire_errors = wire_errors_x + wire_errors_y
print(f"  Endpoint X Wires Created/Renamed in this run: {wires_created_x}")
print(f"  Endpoint Y Wires Created/Renamed in this run: {wires_created_y}")
if total_wire_errors > 0:
    print(f"  Encountered {total_wire_errors} total errors during processing.")
print("======================================================")
# === End of Script ===
