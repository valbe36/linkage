# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import regionToolset
import math

# ============================================================================
# MODULAR RP FUNCTIONS
# ============================================================================

def convert_location_to_module_coords(location, dx, dy, dz):
    """
    Convert absolute coordinates to module coordinates.
    Returns (module_x, module_y, module_z)
    """
    module_x = int(round(location[0] / dx))
    module_y = int(round(location[1] / dy)) 
    module_z = int(round(location[2] / dz))
    
    return module_x, module_y, module_z

def create_rp_with_modular_tracking(assembly, location, dx, dy, dz, rp_type=""):
    """
    Create RP and immediately create its modular set.
    
    Parameters:
    - assembly: Abaqus assembly
    - location: (x, y, z) absolute coordinates
    - dx, dy, dz: module dimensions
    - rp_type: "Internal" or "Boundary" for descriptive naming
    
    Returns: (rp_feature, rp_object, module_coords, set_name)
    """
    
    # Convert to module coordinates
    mod_x, mod_y, mod_z = convert_location_to_module_coords(location, dx, dy, dz)
    
    # Create RP
    rp_feature = assembly.ReferencePoint(point=location)
    rp = assembly.referencePoints[rp_feature.id]
    
    # Create modular set name
    set_name = "RP_x{}_y{}_z{}".format(mod_x, mod_y, mod_z)
    
    # Handle potential duplicates (if RP already exists at this module location)
    base_set_name = set_name
    counter = 1
    while set_name in assembly.sets:
        set_name = "{}_{}".format(base_set_name, counter)
        counter += 1
    
    # Create set
    try:
        assembly.Set(referencePoints=(rp,), name=set_name)
        print("  Created RP set: {} at module ({},{},{})".format(set_name, mod_x, mod_y, mod_z))
        if rp_type:
            print("    Type: {} RP".format(rp_type))
    except Exception as e:
        print("  Warning: Could not create set {}: {}".format(set_name, e))
    
    return rp_feature, rp, (mod_x, mod_y, mod_z), set_name

def create_rps_and_wires_internal_modular(assembly, internal_intersections, dx, dy, dz):
    """
    Create RPs and wires for internal intersections with modular tracking.
    Returns (rp_count, wire_count, created_rps)
    """
    rp_count = 0
    wire_count = 0
    created_rps = []  # Track created RPs: (rp, module_coords, set_name, location)
    
    for i, (location, bars_at_location, bar_counts) in enumerate(internal_intersections):
        
        print("")
        print("Creating internal RP {}:".format(i+1))
        print("  Location: {}".format(location))
        
        # Create RP with modular tracking
        try:
            rp_feature, rp, module_coords, set_name = create_rp_with_modular_tracking(
                assembly, location, dx, dy, dz, "Internal"
            )
            rp_count += 1
            
            # Track the created RP
            created_rps.append((rp, module_coords, set_name, location))
            
            # Find representative bars for wires
            barx_rep = find_representative_bar(bars_at_location, 'BarX')
            barz_rep = find_representative_bar(bars_at_location, 'BarZ')
            
            # Create wire RP -> BarX
            if barx_rep:
                wire_name_x = "UniversalJoint_BarX_{}".format(i+1)
                if create_rp_to_bar_wire(assembly, rp, barx_rep, location, wire_name_x, "BarX"):
                    wire_count += 1
            
            # Create wire RP -> BarZ  
            if barz_rep:
                wire_name_z = "UniversalJoint_BarZ_{}".format(i+1)
                if create_rp_to_bar_wire(assembly, rp, barz_rep, location, wire_name_z, "BarZ"):
                    wire_count += 1
                    
        except Exception as e:
            print("  Error creating internal RP: {}".format(e))
    
    return rp_count, wire_count, created_rps

# ============================================================================
# MAIN FUNCTIONS (UPDATED)
# ============================================================================

def create_internal_universal_joints():
    """
    Create RPs and universal joint wires at internal intersection points only.
    Internal = multiple bars per type, Boundary = single bars.
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    instances = assembly.instances
    
    print("=== INTERNAL UNIVERSAL JOINT CREATION ===")
    print("")
    print("Step 1: Identifying intersection points...")
    
    # Find all intersection points and classify them
    internal_intersections, boundary_intersections = find_internal_intersections(instances)
    
    print("")
    print("Step 2: Creating RPs and wires at internal intersections...")
    
    # Create RPs and wires for internal intersections
    rp_count, wire_count = create_rps_and_wires(assembly, internal_intersections)
    
    print("")
    print("=== SUMMARY ===")
    print("Internal intersection points: " + str(len(internal_intersections)))
    print("Boundary intersection points: " + str(len(boundary_intersections)))
    print("Reference Points created: " + str(rp_count))
    print("Universal joint wires created: " + str(wire_count))
    print("")
    print("NEXT STEPS FOR GUI:")
    print("1. Select wires named 'UniversalJoint_BarX_##'")
    print("2. Apply connector with: U1,U2,U3=FIXED, UR1=FREE, UR2=FIXED, UR3=FREE")
    print("3. Select wires named 'UniversalJoint_BarZ_##'") 
    print("4. Apply connector with: U1,U2,U3=FIXED, UR1=FREE, UR2=FIXED, UR3=FREE")
    print("5. Handle boundary intersections separately")

def find_internal_intersections(instances):
    """
    Find and classify intersection points as internal or boundary.
    Returns (internal_intersections, boundary_intersections).
    """
    
    # Group all bars by their vertex locations
    location_groups = group_bars_by_vertices(instances)
    
    internal_intersections = []
    boundary_intersections = []
    
    print("Analyzing " + str(len(location_groups)) + " potential intersection locations...")
    
    # Convert to list to avoid iteration issues
    location_items = list(location_groups.items())
    
    for location, bars_at_location in location_items:
        
        # Count bars by type at this location
        bar_counts = count_bars_by_type(bars_at_location)
        
        # Check if this location has intersecting bars (BarX AND BarZ present)
        has_barx = (bar_counts['BarX-a'] + bar_counts['BarX-b']) > 0
        has_barz = (bar_counts['BarZ-a'] + bar_counts['BarZ-b']) > 0
        
        if has_barx and has_barz:
            # We have both bar types - this is a potential intersection
            total_bars = (bar_counts['BarX-a'] + bar_counts['BarX-b'] + 
                         bar_counts['BarZ-a'] + bar_counts['BarZ-b'])
            
            print("Intersection at " + str(location) + ":")
            print("  BarX-a: " + str(bar_counts['BarX-a']) + ", BarX-b: " + str(bar_counts['BarX-b']))
            print("  BarZ-a: " + str(bar_counts['BarZ-a']) + ", BarZ-b: " + str(bar_counts['BarZ-b']))
            print("  Total: " + str(total_bars) + " bars")
            
            # Internal intersection criteria (CORRECTED):
            # Internal = 4 BarX (2 BarX-a + 2 BarX-b) AND 4 BarZ (2 BarZ-a + 2 BarZ-b)
            # Boundary = Less than 4 bars per type
            is_internal = (bar_counts['BarX-a'] >= 2 and bar_counts['BarX-b'] >= 2 and
                          bar_counts['BarZ-a'] >= 2 and bar_counts['BarZ-b'] >= 2)
            
            if is_internal:
                print("  -> INTERNAL intersection (4+ BarX, 4+ BarZ)")
                internal_intersections.append((location, bars_at_location, bar_counts))
            else:
                print("  -> BOUNDARY intersection (< 4 bars per type)")
                boundary_intersections.append((location, bars_at_location, bar_counts))
    
    return internal_intersections, boundary_intersections

def group_bars_by_vertices(instances):
    """
    Group bars by their vertex locations (start, midpoint, end).
    Returns dict: {location: [(instance, vertex, vertex_type), ...]}
    """
    location_groups = {}
    tolerance = 0.1
    
    # Convert instances to list to avoid Abaqus collection issues
    instance_list = list(instances.values())
    
    for inst in instance_list:
        if inst.name.startswith(('BarX-', 'BarZ-')):
            try:
                vertices = inst.vertices
                if len(vertices) < 3:
                    continue
                
                # Check key vertices: start (0), midpoint (2), end (-1)
                key_vertices = [
                    (vertices[0], 'start'),
                    (vertices[2], 'midpoint'),  
                    (vertices[-1], 'end')
                ]
                
                for vertex, vertex_type in key_vertices:
                    coord = vertex.pointOn[0]
                    # Round coordinates to group nearby points
                    rounded_coord = (round(coord[0], 1), round(coord[1], 1), round(coord[2], 1))
                    
                    if rounded_coord not in location_groups:
                        location_groups[rounded_coord] = []
                    
                    location_groups[rounded_coord].append((inst, vertex, vertex_type))
                    
            except Exception as e:
                print("Error processing " + inst.name + ": " + str(e))
    
    return location_groups

def count_bars_by_type(bars_at_location):
    """
    Count how many bars of each type are at this location.
    Returns dict with counts for each bar type.
    """
    counts = {'BarX-a': 0, 'BarX-b': 0, 'BarZ-a': 0, 'BarZ-b': 0}
    
    # Count unique bars (avoid double-counting if bar has multiple vertices at location)
    unique_bars = set()
    for bar_instance, vertex, vertex_type in bars_at_location:
        unique_bars.add(bar_instance.name)
    
    for bar_name in unique_bars:
        if bar_name.startswith('BarX-a_'):
            counts['BarX-a'] += 1
        elif bar_name.startswith('BarX-b_'):
            counts['BarX-b'] += 1
        elif bar_name.startswith('BarZ-a_'):
            counts['BarZ-a'] += 1
        elif bar_name.startswith('BarZ-b_'):
            counts['BarZ-b'] += 1
    
    return counts

def create_rps_and_wires(assembly, internal_intersections):
    """
    Create RPs and wires for internal intersections - UPDATED with modular tracking.
    Returns (rp_count, wire_count).
    """
    
    # Get module dimensions from script a parameters
    dx = 221
    dy = 127.5
    dz = 221
    
    print("Creating internal RPs with modular coordinate system...")
    print("Module dimensions: dx={}, dy={}, dz={}".format(dx, dy, dz))
    
    # Use the modular RP creation function
    rp_count, wire_count, created_rps = create_rps_and_wires_internal_modular(
        assembly, internal_intersections, dx, dy, dz
    )
    
    # Store created RPs info for potential later use
    print("")
    print("=== INTERNAL RP CREATION SUMMARY ===")
    print("RPs created: {}".format(rp_count))
    print("Wires created: {}".format(wire_count))
    
    # Show some examples of created modular sets
    print("Example modular sets created:")
    for rp, module_coords, set_name, location in created_rps[:3]:
        print("  {} -> module {}".format(set_name, module_coords))
    if len(created_rps) > 3:
        print("  ... and {} more".format(len(created_rps) - 3))
    
    return rp_count, wire_count

def find_representative_bar(bars_at_location, bar_type):
    """
    Find one representative bar of the specified type at this location.
    Returns (instance, vertex) tuple or None.
    """
    
    # Look for bars of the specified type
    candidates = []
    for bar_instance, vertex, vertex_type in bars_at_location:
        if bar_instance.name.startswith(bar_type + '-'):
            candidates.append((bar_instance, vertex, vertex_type))
    
    if candidates:
        # Prefer midpoint connections, then start, then end
        midpoint_candidates = [c for c in candidates if c[2] == 'midpoint']
        if midpoint_candidates:
            return midpoint_candidates[0][:2]  # Return (instance, vertex)
        
        start_candidates = [c for c in candidates if c[2] == 'start']
        if start_candidates:
            return start_candidates[0][:2]
        
        # Fallback to any candidate
        return candidates[0][:2]
    
    return None

def create_rp_to_bar_wire(assembly, rp, bar_info, rp_location, wire_name, bar_type):
    """
    Create a wire between RP and bar vertex.
    bar_info is (instance, vertex) tuple.
    """
    try:
        bar_instance, vertex = bar_info
        
        print("  Creating " + bar_type + " wire: " + wire_name)
        print("    RP to " + bar_instance.name)
        
        # Create wire from RP to bar vertex
        wire_feature = assembly.WirePolyLine(
            mergeType=IMPRINT,
            meshable=False,
            points=((rp, vertex),)
        )
        
        # Rename the wire feature
        old_name = wire_feature.name
        assembly.features.changeKey(old_name, wire_name)
        
        print("    Wire created: " + wire_name)
        return True
        
    except Exception as e:
        print("    Error creating wire " + wire_name + ": " + str(e))
        return False

def verify_universal_joints():
    """
    Verify the created RPs and wires.
    """
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("")
    print("=== VERIFICATION ===")
    
    # Count RPs
    total_rps = len(assembly.referencePoints)
    print("Total RPs in assembly: " + str(total_rps))
    
    # Count universal joint wires
    universal_barx_wires = []
    universal_barz_wires = []
    
    # Convert to list to avoid iteration issues
    feature_names = list(assembly.features.keys())
    
    for feature_name in feature_names:
        if feature_name.startswith('UniversalJoint_BarX'):
            universal_barx_wires.append(feature_name)
        elif feature_name.startswith('UniversalJoint_BarZ'):
            universal_barz_wires.append(feature_name)
    
    print("Universal joint BarX wires: " + str(len(universal_barx_wires)))
    for wire_name in universal_barx_wires[:5]:  # Show first 5
        print("  - " + wire_name)
    if len(universal_barx_wires) > 5:
        print("  ... and " + str(len(universal_barx_wires) - 5) + " more")
    
    print("Universal joint BarZ wires: " + str(len(universal_barz_wires)))
    for wire_name in universal_barz_wires[:5]:  # Show first 5
        print("  - " + wire_name)
    if len(universal_barz_wires) > 5:
        print("  ... and " + str(len(universal_barz_wires) - 5) + " more")

# ============================================================================
# UTILITY FUNCTIONS FOR MODULAR RP ACCESS
# ============================================================================

def get_rp_by_module_coords(assembly, mod_x, mod_y, mod_z):
    """Get RP by module coordinates."""
    set_name = "RP_x{}_y{}_z{}".format(mod_x, mod_y, mod_z)
    
    if set_name in assembly.sets:
        try:
            return assembly.sets[set_name].referencePoints[0]
        except:
            return None
    return None

def find_rps_in_module_range(assembly, x_range=None, y_range=None, z_range=None):
    """Find RPs within specific module coordinate ranges."""
    
    matching_rps = []
    
    for set_name in assembly.sets.keys():
        if set_name.startswith('RP_x') and '_y' in set_name and '_z' in set_name:
            try:
                parts = set_name.split('_')
                if len(parts) >= 3:
                    mod_x = int(parts[1][1:])  # Remove 'x'
                    mod_y = int(parts[2][1:])  # Remove 'y'
                    mod_z = int(parts[3][1:])  # Remove 'z'
                    
                    # Check ranges
                    x_ok = (x_range is None) or (x_range[0] <= mod_x <= x_range[1])
                    y_ok = (y_range is None) or (y_range[0] <= mod_y <= y_range[1])
                    z_ok = (z_range is None) or (z_range[0] <= mod_z <= z_range[1])
                    
                    if x_ok and y_ok and z_ok:
                        rp_set = assembly.sets[set_name]
                        if hasattr(rp_set, 'referencePoints'):
                            matching_rps.extend(rp_set.referencePoints)
                            
            except (ValueError, IndexError):
                continue
    
    return list(set(matching_rps))  # Remove duplicates

def list_modular_rps(assembly):
    """List all modular RPs for verification."""
    
    modular_sets = []
    for set_name in assembly.sets.keys():
        if set_name.startswith('RP_x') and '_y' in set_name and '_z' in set_name:
            modular_sets.append(set_name)
    
    print("Modular RP sets found: {}".format(len(modular_sets)))
    
    # Group by level
    by_level = {}
    for set_name in sorted(modular_sets):
        try:
            mod_y = int(set_name.split('_')[2][1:])  # Extract y coordinate
            if mod_y not in by_level:
                by_level[mod_y] = []
            by_level[mod_y].append(set_name)
        except:
            continue
    
    for level in sorted(by_level.keys()):
        print("  Level {}: {} RPs".format(level, len(by_level[level])))
        for set_name in by_level[level][:3]:  # Show first 3
            print("    - {}".format(set_name))
        if len(by_level[level]) > 3:
            print("    ... and {} more".format(len(by_level[level]) - 3))

def create_ground_supports_set(assembly):
    """Create a set containing all ground-level RPs (module y=0)."""
    
    print("Creating ground supports set...")
    
    # Find all RPs at ground level (module y=0)
    ground_rps = find_rps_in_module_range(assembly, y_range=(0, 0))
    
    if len(ground_rps) > 0:
        set_name = "RPs_GroundSupports"
        try:
            assembly.Set(referencePoints=tuple(ground_rps), name=set_name)
            print("Created ground supports set '{}' with {} RPs".format(set_name, len(ground_rps)))
            return set_name
        except Exception as e:
            print("Error creating ground supports set: {}".format(e))
            return None
    else:
        print("No ground-level RPs found")
        return None

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        create_internal_universal_joints()
        verify_universal_joints()
        
        print("")
        print("=== MODULAR RP MANAGEMENT READY ===")
        print("Individual access: Use sets named 'RP_x#_y#_z#' where #=module coordinates")
        print("Purpose sets: Create programmatically when needed")
        print("")
        print("Available utility functions:")
        print("- create_ground_supports_set(assembly)")
        print("- get_rp_by_module_coords(assembly, mod_x, mod_y, mod_z)")
        print("- find_rps_in_module_range(assembly, x_range, y_range, z_range)")
        
        # Show summary of created RPs
        assembly = mdb.models['Model-1'].rootAssembly
        list_modular_rps(assembly)
        
    except Exception as e:
        print("Error in main execution: " + str(e))
        import traceback
        traceback.print_exc()