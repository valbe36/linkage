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
This sketch creates JointMidScissor connectors between scissor bar pairs at their midpoints
Uses PointFastener engineering feature to automatically create CONN3D2 connectors
BarX pairs rotate around X-axis, BarZ pairs rotate around Z-axis
"""""

# --- 0) Basic Setup: Model & Parameters ---
model_name = 'Model-1' # <<< ENSURE THIS IS CORRECT
connector_section_name = 'Pure_Hinge'
csys_X_name = 'Connector_Global_X_Orient'
csys_Z_name = 'Connector_Global_Z_Orient'

# Geometry/Instance Parameters
dx = 221; dy = 127.5; dz = 221
n_x = 6; n_y = 5; n_z_base = 5

# Connector parameters
midpoint_vertex_index = 2
fastener_physical_radius = 0.001  # Small radius for point fasteners

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

    # --- Step 1: Setup Connector Prerequisites ---
print("\nStep 1: Setup Connector Prerequisites")

def setup_connector_section(model, section_name):
    """Create connector section if it doesn't exist - REVOLUTE + JOIN type"""
    if section_name not in model.sections:
        print(f"  Creating connector section: {section_name}")
        try:
            # Create connector section with proper connection types
            # Based on documentation: REVOLUTE allows rotation, JOIN constrains translation
            model.ConnectorSection(
                name=section_name,
                translationalType=JOIN,      # No translation (rigid connection)
                rotationalType=REVOLUTE      # Allow rotation (hinge behavior)
            )
            print(f"  Connector section '{section_name}' created (REVOLUTE + JOIN).")
        except Exception as e:
            warnings.warn(f"Failed to create connector section '{section_name}': {e}")
            print(traceback.format_exc())
            raise
    else:
        print(f"  Connector section '{section_name}' already exists.")

def ensure_csys_exists(assembly, name, origin, point1, point2):
    """Create datum coordinate system if it doesn't exist - returns feature ID"""
    if name in assembly.features:
        print(f"  Datum CSYS '{name}' already exists.")
        try:
            feature_id = assembly.features[name].id
            csys_obj = assembly.datums[feature_id]
            return feature_id, True  # Return feature ID, not datum object
        except Exception as e:
            warnings.warn(f"Error accessing existing CSYS '{name}': {e}")
            return None, False
    else:
        print(f"  Creating datum CSYS: {name}")
        try:
            csys_feature = assembly.DatumCsysByThreePoints(
                name=name, 
                coordSysType=CARTESIAN,
                origin=origin, 
                point1=point1, 
                point2=point2
            )
            csys_obj = assembly.datums[csys_feature.id]
            print(f"  Successfully created datum CSYS '{name}'.")
            return csys_feature.id, True  # Return feature ID, not datum object
        except Exception as e:
            warnings.warn(f"Failed to create datum CSYS '{name}': {e}")
            return None, False

# Create connector section
setup_connector_section(myModel, connector_section_name)

# Create coordinate systems for connector orientations
csys_X_id, csys_X_ok = ensure_csys_exists(
    a, csys_X_name, 
    (0.0, 0.0, 0.0),     # origin
    (1.0, 0.0, 0.0),     # X-axis direction  
    (0.0, 1.0, 0.0)      # Y-axis direction
)

csys_Z_id, csys_Z_ok = ensure_csys_exists(
    a, csys_Z_name,
    (0.0, 0.0, 0.0),     # origin
    (0.0, 1.0, 0.0),     # Y-axis direction
    (-1.0, 0.0, 0.0)     # X-axis direction (rotated for Z-axis alignment)
)

if not csys_X_ok or not csys_Z_ok:
    print("FATAL ERROR: Could not create/access required coordinate systems.")
    raise Exception("Coordinate system setup failed.")

# Regenerate assembly after CSYS creation
print("  Regenerating assembly after CSYS setup...")
a.regenerate()
print("Finished Step 1.")

    # --- Step 2: Create JointMidScissor Connectors using PointFastener ---
print("\nStep 2: Create JointMidScissor Connectors using PointFastener")

def create_point_fastener_connector(assembly, 
                                   inst_a_name, inst_b_name,
                                   vertex_index, fastener_name,
                                   section_name, csys_for_orient, physical_radius):
    """
    Creates a CONN3D2 connector using PointFastener engineering feature.
    This automatically handles CONN3D2 element creation.
    """
    try:
        # Get instances
        if inst_a_name not in assembly.instances or inst_b_name not in assembly.instances:
            warnings.warn(f"Instances not found: {inst_a_name} or {inst_b_name}")
            return None
            
        inst_a = assembly.instances[inst_a_name]
        inst_b = assembly.instances[inst_b_name]
        
        # Get vertex coordinates
        if vertex_index >= len(inst_a.vertices) or vertex_index >= len(inst_b.vertices):
            warnings.warn(f"Vertex index {vertex_index} out of range")
            return None
            
        vertex_a = inst_a.vertices[vertex_index]
        vertex_b = inst_b.vertices[vertex_index]
        
        # Create regions from vertices
        try:
            # Create individual vertex sets first, then combine into region
            vertex_a_coord = vertex_a.pointOn[0]
            vertex_b_coord = vertex_b.pointOn[0]
            
            # Find vertices using coordinates (more reliable method)
            vertices_a = inst_a.vertices.findAt((vertex_a_coord,))
            vertices_b = inst_b.vertices.findAt((vertex_b_coord,))
            
            # Create a combined vertex sequence
            all_vertices = vertices_a + vertices_b
            
            # Create region from the vertex sequence
            region = regionToolset.Region(vertices=all_vertices)
            print(f"    Created region from {len(all_vertices)} vertices")
            
            # Check if fastener already exists using try/except
            try:
                # Try to access the fastener - this will fail if it doesn't exist
                existing_fastener = getattr(assembly.engineeringFeatures, fastener_name, None)
                if existing_fastener is not None:
                    print(f"    PointFastener '{fastener_name}' already exists, skipping...")
                    return fastener_name
            except:
                # Fastener doesn't exist, proceed with creation
                pass
            
            # Create PointFastener - this automatically creates CONN3D2 connectors
            # Use minimal working parameters first
            fastener = assembly.engineeringFeatures.PointFastener(
                name=fastener_name,
                region=region,
                physicalRadius=physical_radius,
                connectionType=CONNECTOR,  # Use CONNECTOR type for CONN3D2
                sectionName=section_name
            )
            
            print(f"    Created PointFastener: {fastener_name}")
            
            # SEPARATE STEP: Apply connector orientation after fastener creation
            if csys_for_orient:
                try:
                    # Let assembly regenerate to create the connector elements
                    assembly.regenerate()
                    
                    # Try to find the connector elements created by the fastener
                    # Method: Search for elements near the connection point
                    search_coords = [vertex_a_coord, vertex_b_coord]
                    
                    for coord in search_coords:
                        try:
                            elements_at_point = assembly.elements.findAt((coord,))
                            if elements_at_point:
                                # Check if this is a connector element (CONN3D2)
                                if hasattr(elements_at_point, 'type') and 'CONN' in str(elements_at_point.type):
                                    connector_region = regionToolset.Region(elements=(elements_at_point,))
                                    assembly.ConnectorOrientation(region=connector_region, localCsys1=csys_for_orient)
                                    print(f"    Applied orientation using CSYS ID: {csys_for_orient}")
                                    break
                        except:
                            continue
                    else:
                        print(f"    Note: Connector created but orientation will use default (global)")
                        
                except Exception as e_orient:
                    print(f"    Note: Connector created but orientation failed: {e_orient}")
            
            print(f"    Successfully created connector: {inst_a_name} and {inst_b_name}")
            return fastener_name
            
        except Exception as e_fastener:
            print(f"    ERROR creating PointFastener for {fastener_name}: {e_fastener}")
            print(traceback.format_exc())
            return None
        
    except Exception as e:
        print(f"    ERROR creating connector between {inst_a_name} and {inst_b_name}: {e}")
        print(traceback.format_exc())
        return None

# --- Execute Step 2A: BarX Mid-Scissor Connectors ---
print(" --- Creating BarX Mid-Scissor Connectors using PointFastener ---")

x_connectors_created = 0
x_connector_errors = 0

print(f"  Proceeding with X-connector creation using PointFastener...")
for iy in range(n_y):  # Height levels (0 to 4)
    n_z_at_level = max(1, n_z_base - iy)  # Tapering
    
    for iz in range(n_z_at_level):  # Along slope
        for ix in range(n_x + 1):  # Perpendicular to slope (0 to 6)
            
            # Generate instance names for BarX pair
            inst_a_name = f"BarX-a_x{ix}_y{iy}_z{iz}"
            inst_b_name = f"BarX-b_x{ix}_y{iy}_z{iz}"
            
            # Generate unique fastener name
            fastener_name = f"FastenerX_x{ix}_y{iy}_z{iz}"
            
            # Create connector using PointFastener
            result_name = create_point_fastener_connector(
                assembly=a,
                inst_a_name=inst_a_name,
                inst_b_name=inst_b_name,
                vertex_index=midpoint_vertex_index,
                fastener_name=fastener_name,
                section_name=connector_section_name,
                csys_for_orient=csys_X_id,
                physical_radius=fastener_physical_radius
            )
            
            if result_name:
                x_connectors_created += 1
            else:
                x_connector_errors += 1

print(f"  BarX Mid-Scissor Connectors Created: {x_connectors_created}")
if x_connector_errors > 0:
    print(f"  BarX Connector Errors: {x_connector_errors}")

# --- Execute Step 2B: BarZ Mid-Scissor Connectors ---
print(" --- Creating BarZ Mid-Scissor Connectors using PointFastener ---")

z_connectors_created = 0
z_connector_errors = 0

print(f"  Proceeding with Z-connector creation using PointFastener...")
for iy in range(n_y):  # Height levels (0 to 4)
    n_z_at_level = max(1, n_z_base - iy)  # Tapering
    
    for iz in range(n_z_at_level):  # Along slope  
        for ix in range(n_x):  # Perpendicular to slope (BarZ: 0 to 5, within modules)
            
            # Generate instance names for BarZ pair
            inst_a_name = f"BarZ-a_x{ix}_y{iy}_z{iz}"
            inst_b_name = f"BarZ-b_x{ix}_y{iy}_z{iz}"
            
            # Generate unique fastener name
            fastener_name = f"FastenerZ_x{ix}_y{iy}_z{iz}"
            
            # Create connector using PointFastener
            result_name = create_point_fastener_connector(
                assembly=a,
                inst_a_name=inst_a_name,
                inst_b_name=inst_b_name,
                vertex_index=midpoint_vertex_index,
                fastener_name=fastener_name,
                section_name=connector_section_name,
                csys_for_orient=csys_Z_id,
                physical_radius=fastener_physical_radius
            )
            
            if result_name:
                z_connectors_created += 1
            else:
                z_connector_errors += 1

print(f"  BarZ Mid-Scissor Connectors Created: {z_connectors_created}")
if z_connector_errors > 0:
    print(f"  BarZ Connector Errors: {z_connector_errors}")

print("Finished Step 2.")

    # --- Step 3: Final Assembly Regeneration ---
print("\nStep 3: Final Assembly Regeneration...")
a.regenerate()
print("Assembly regenerated.")

# ====================================================================
# Final Summary
# ====================================================================
print("\n--- JointMidScissor Connectors Summary ---")
total_connectors = x_connectors_created + z_connectors_created
total_errors = x_connector_errors + z_connector_errors

print(f"Total Mid-Scissor Connectors Created: {total_connectors}")
print(f"  - BarX Connectors (X-axis rotation): {x_connectors_created}")
print(f"  - BarZ Connectors (Z-axis rotation): {z_connectors_created}")

if total_errors > 0:
    print(f"Total Errors Encountered: {total_errors}")
    overall_success = False
    
if overall_success:
    print("JointMidScissor connectors script completed successfully!")
    print("PointFastener engineering features created with automatic CONN3D2 elements.")
else:
    print("JointMidScissor connectors script completed with errors.")

print("Ready for next connector type (collinear bars, endpoint connections, etc.)")