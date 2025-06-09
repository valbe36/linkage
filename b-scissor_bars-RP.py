

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

""""
This sketch makes the scissor bars  revelant RPs at the end of bars

"""""
# --- 0) Basic Setup: Model & Parameters ---
model_name = 'Model-1' # <<< ENSURE THIS IS CORRECT
# Geometry/Instance Parameters
dx = 2.208365; dy = 2.208365; dz = 1.275
n_x = 6; n_y = 6; n_z = 6



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

 

                               #######################################################################################
# # ------------------------------------------------------------------RPs AT ENDPOINTS  ------------------------------------------------------------------------
                              ###################################################################################### 



# 0) User Parameters & Setup
model_name = 'Model-1' # <<< ENSURE THIS IS CORRECT
rp_set_name = "RP_End_Set"

try:
    myModel = mdb.models[model_name]
    a = myModel.rootAssembly # Get initial assembly reference
    print("Successfully accessed model '{}' and assembly 'a'.".format(model_name))
except KeyError:
    raise KeyError("FATAL ERROR: Model '{}' not found.".format(model_name))
except Exception as e:
    raise Exception("FATAL ERROR during model/assembly access: {}".format(str(e)))

# Create RPs ONLY IF NO RPs Exist
print("\nChecking for any existing Reference Points...")
rp_data_list = []         # Stores (rp_obj, coord) ONLY if RPs are newly created
skip_endpoint_wires = False # Flag to control wire loop execution

try:
    # Check if the referencePoints repository is non-empty
    if a.referencePoints:
        print("  Existing RPs found. Skipping RP creation AND endpoint wire creation.")
        # If RPs exist, we skip creating wires according to user request
        skip_endpoint_wires = True
    else:
        # --- If no RPs found initially, create them now ---
        print("  No existing RPs found. Creating new RPs...")
        skip_endpoint_wires = False # Ensure wires will be created

        # <<< DEFINE dx, dy, dz, n_x, n_y, n_z, x_range_rp, y_range_rp HERE >>>
        x_range_rp = range(n_x)
        y_range_rp = range(n_y + 1)
        # <<< --------------------------------------------------------- >>>

        rp_creation_errors = 0; rp_created_count = 0
        try:
            assy_for_rp_create = myModel.rootAssembly # Fetch fresh
            if not hasattr(assy_for_rp_create, 'ReferencePoint'): raise AttributeError("...")

            # --- RP Creation Loop ---
            for x in x_range_rp:
                for y in y_range_rp:
                    num_z = x + 2 # <<< VERIFY Z-LOGIC
                    for z in range(num_z):
                        coord = (x * dx, y * dy, z * dz)
                        try:
                            rp_obj = assy_for_rp_create.ReferencePoint(point=coord)
                            if rp_obj is None: raise ValueError("...")
                            # Populate list ONLY when creating RPs
                            rp_data_list.append((rp_obj, coord))
                            rp_created_count += 1
                        except Exception as e: warnings.warn(...); rp_creation_errors += 1
            print("Finished RP creation phase. Created {} RPs...".format(rp_created_count))
            # Make sure rp_data_list is populated if creation happened
            if rp_created_count == 0 and rp_creation_errors == 0:
                 warnings.warn("RP creation loop finished but no RPs were created.")

        except Exception as e:
             warnings.warn("!! ERROR during RP creation phase: {}. No RPs created.".format(repr(e)))
             rp_data_list = [] # Ensure list is empty

except Exception as e:
    warnings.warn("Could not check for existing RPs: {}. Assuming none exist.".format(str(e)))
    skip_endpoint_wires = False # Proceed with RP creation if check fail
 



