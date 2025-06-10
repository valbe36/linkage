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

def create_boundary_rps_and_wires_modular(assembly, boundary_endpoints, dx, dy, dz):
    """
    Create RPs and wires for boundary endpoints with modular tracking.
    Returns (rp_count, wire_x_count, wire_z_count, created_rps)
    """
    rp_count = 0
    wire_x_count = 0
    wire_z_count = 0
    created_rps = []  # Track created RPs: (rp, module_coords, set_name, location, bar_info)
    
    # First pass: Create all RPs with modular tracking
    print("Creating boundary RPs with modular coordinates...")
    for i, (location, bars_at_location, bar_counts) in enumerate(boundary_endpoints):
        
        print("")
        print("Creating boundary RP {}:".format(i+1))
        print("  Location: {}".format(location))
        
        try:
            # Create RP with modular tracking
            rp_feature, rp, module_coords, set_name = create_rp_with_modular_tracking(
                assembly, location, dx, dy, dz, "Boundary"
            )
            rp_count += 1
            
            # Find representative bars
            barx_rep = find_representative_bar(bars_at_location, 'BarX')
            barz_rep = find_representative_bar(bars_at_location, 'BarZ')
            
            # Track the created RP with bar information
            created_rps.append((rp, module_coords, set_name, location, bar_counts, barx_rep, barz_rep))
            
        except Exception as e:
            print("  Error creating boundary RP: {}".format(e))
    
    # Second pass: Create BarX wires
    print("")
    print("Creating RP-to-BarX wires...")
    for i, (rp, module_coords, set_name, location, bar_counts, barx_rep, barz_rep) in enumerate(created_rps):
        has_barx = (bar_counts['BarX-a'] + bar_counts['BarX-b']) > 0
        if has_barx and barx_rep:
            wire_name = "Boundary_X_{}".format(i+1)
            if create_rp_to_bar_wire(assembly, rp, barx_rep, location, wire_name, "BarX"):
                wire_x_count += 1
    
    # Third pass: Create BarZ wires
    print("")
    print("Creating RP-to-BarZ wires...")
    for i, (rp, module_coords, set_name, location, bar_counts, barx_rep, barz_rep) in enumerate(created_rps):
        has_barz = (bar_counts['BarZ-a'] + bar_counts['BarZ-b']) > 0
        if has_barz and barz_rep:
            wire_name = "Boundary_Z_{}".format(i+1)
            if create_rp_to_bar_wire(assembly, rp, barz_rep, location, wire_name, "BarZ"):
                wire_z_count += 1
    
    return rp_count, wire_x_count, wire_z_count, created_rps

# ============================================================================
# MAIN FUNCTIONS (UPDATED)
# ============================================================================

def create_boundary_supports_all_endpoints():
    """
    Create RPs and constrained wires at ALL boundary endpoints/startpoints.
    - Processes all boundary endpoints regardless of bar type intersections
    - Excludes midpoints (only start/end points)
    - Excludes internal intersections using existing criteria
    - Creates appropriate supports based on what bar types are present
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    instances = assembly.instances
    
    print("=== BOUNDARY SUPPORTS FOR ALL ENDPOINTS ===")
    print("")
    print("Step 1: Finding all boundary endpoints...")
    
    # Find all boundary endpoints (excluding midpoints and internal points)
    boundary_endpoints = find_all_boundary_endpoints(instances)
    
    print("")
    print("Step 2: Creating RPs and wires at boundary endpoints...")
    
    # Create RPs and wires
    rp_count, wire_x_count, wire_z_count = create_boundary_rps_and_wires_all_endpoints(assembly, boundary_endpoints)
    
    print("")
    print("=== SUMMARY ===")
    print("Boundary endpoint locations: " + str(len(boundary_endpoints)))
    print("Reference Points created: " + str(rp_count))
    print("RP-to-BarX wires created: " + str(wire_x_count))
    print("RP-to-BarZ wires created: " + str(wire_z_count))
    print("Total boundary wires: " + str(wire_x_count + wire_z_count))
    print("")
    print("NEXT STEPS FOR GUI:")
    print("1. Select wires named 'Boundary_X_##' (RP to BarX)")
    print("   Apply constraints: U1,U2,U3=FIXED, UR1=FREE, UR2=FIXED, UR3=FIXED")
    print("2. Select wires named 'Boundary_Z_##' (RP to BarZ)")
    print("   Apply constraints: U1,U2,U3=FIXED, UR1=FIXED, UR2=FIXED, UR3=FREE")
    print("3. Apply ground pins to RPs as needed")

def find_all_boundary_endpoints(instances):
    """
    Find ALL boundary endpoints/startpoints (excluding midpoints).
    Boundary = endpoint/startpoint that is NOT at an internal intersection.
    """
    
    # Group all bars by their vertex locations, but ONLY endpoints
    location_groups = group_bars_by_endpoints_only(instances)
    
    boundary_endpoints = []
    
    print("Analyzing " + str(len(location_groups)) + " potential endpoint locations...")
    
    # Convert to list to avoid iteration issues
    location_items = list(location_groups.items())
    
    for location, bars_at_location in location_items:
        
        # Count bars by type at this location
        bar_counts = count_bars_by_type(bars_at_location)
        
        # Check if this is an internal intersection (to EXCLUDE)
        # Internal intersection criteria: 2+ BarX-a AND 2+ BarX-b AND 2+ BarZ-a AND 2+ BarZ-b
        is_internal = (bar_counts['BarX-a'] >= 2 and bar_counts['BarX-b'] >= 2 and
                      bar_counts['BarZ-a'] >= 2 and bar_counts['BarZ-b'] >= 2)
        
        if not is_internal:
            # This is a boundary endpoint - process regardless of bar type combinations
            total_bars = (bar_counts['BarX-a'] + bar_counts['BarX-b'] + 
                         bar_counts['BarZ-a'] + bar_counts['BarZ-b'])
            
            print("Boundary endpoint at " + str(location) + ":")
            print("  BarX-a: " + str(bar_counts['BarX-a']) + ", BarX-b: " + str(bar_counts['BarX-b']))
            print("  BarZ-a: " + str(bar_counts['BarZ-a']) + ", BarZ-b: " + str(bar_counts['BarZ-b']))
            print("  Total: " + str(total_bars) + " bars")
            print("  -> BOUNDARY endpoint (not internal)")
            
            boundary_endpoints.append((location, bars_at_location, bar_counts))
        else:
            print("Skipping internal intersection at " + str(location) + " (2+ bars per type)")
    
    return boundary_endpoints

def group_bars_by_endpoints_only(instances):
    """
    Group bars by their vertex locations, but ONLY endpoints (start/end), NO midpoints.
    Returns dict: {location: [(instance, vertex, vertex_type), ...]}
    """
    location_groups = {}
    
    # Convert instances to list to avoid Abaqus collection issues
    instance_list = list(instances.values())
    
    for inst in instance_list:
        if inst.name.startswith(('BarX-', 'BarZ-')):
            try:
                vertices = inst.vertices
                if len(vertices) < 3:
                    continue
                
                # ONLY check endpoints: start (0) and end (-1) - NO midpoint
                endpoint_vertices = [
                    (vertices[0], 'start'),
                    (vertices[-1], 'end')
                ]
                
                for vertex, vertex_type in endpoint_vertices:
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

def create_boundary_rps_and_wires_all_endpoints(assembly, boundary_endpoints):
    """
    Create RPs and separate wires for ALL boundary endpoints - UPDATED with modular tracking.
    Creates wires based on what bar types are actually present.
    Returns (rp_count, wire_x_count, wire_z_count).
    """
    
    # Get module dimensions from script a parameters  
    dx = 221
    dy = 127.5
    dz = 221
    
    print("Creating boundary RPs with modular coordinate system...")
    print("Module dimensions: dx={}, dy={}, dz={}".format(dx, dy, dz))
    
    # Use the modular RP creation function
    rp_count, wire_x_count, wire_z_count, created_rps = create_boundary_rps_and_wires_modular(
        assembly, boundary_endpoints, dx, dy, dz
    )
    
    # Store created RPs info for potential later use
    print("")
    print("=== BOUNDARY RP CREATION SUMMARY ===")
    print("RPs created: {}".format(rp_count))
    print("BarX wires created: {}".format(wire_x_count))
    print("BarZ wires created: {}".format(wire_z_count))
    
    # Show some examples of created modular sets
    print("Example modular sets created:")
    for rp, module_coords, set_name, location, bar_counts, barx_rep, barz_rep in created_rps[:3]:
        print("  {} -> module {}".format(set_name, module_coords))
    if len(created_rps) > 3:
        print("  ... and {} more".format(len(created_rps) - 3))
    
    # Show ground level RPs found
    ground_rps = [(set_name, module_coords) for rp, module_coords, set_name, location, bar_counts, barx_rep, barz_rep 
                  in created_rps if module_coords[1] == 0]
    print("")
    print("Ground level RPs (y=0): {}".format(len(ground_rps)))
    for set_name, module_coords in ground_rps[:5]:
        print("  {} -> module {}".format(set_name, module_coords))
    if len(ground_rps) > 5:
        print("  ... and {} more".format(len(ground_rps) - 5))
    
    return rp_count, wire_x_count, wire_z_count

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
        # Since we're only dealing with endpoints now, prefer start over end
        start_candidates = [c for c in candidates if c[2] == 'start']
        if start_candidates:
            return start_candidates[0][:2]  # Return (instance, vertex)
        
        # Fallback to end points
        end_candidates = [c for c in candidates if c[2] == 'end']
        if end_candidates:
            return end_candidates[0][:2]
        
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

def verify_boundary_supports():
    """
    Verify the created boundary RPs and wires.
    """
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("")
    print("=== VERIFICATION ===")
    
    # Count RPs
    total_rps = len(assembly.referencePoints)
    print("Total RPs in assembly: " + str(total_rps))
    
    # Count boundary wires
    boundary_x_wires = []
    boundary_z_wires = []
    
    # Convert to list to avoid iteration issues
    feature_names = list(assembly.features.keys())
    
    for feature_name in feature_names:
        if feature_name.startswith('Boundary_X_'):
            boundary_x_wires.append(feature_name)
        elif feature_name.startswith('Boundary_Z_'):
            boundary_z_wires.append(feature_name)
    
    print("Boundary BarX wires: " + str(len(boundary_x_wires)))
    for wire_name in boundary_x_wires[:5]:  # Show first 5
        print("  - " + wire_name)
    if len(boundary_x_wires) > 5:
        print("  ... and " + str(len(boundary_x_wires) - 5) + " more")
    
    print("Boundary BarZ wires: " + str(len(boundary_z_wires)))
    for wire_name in boundary_z_wires[:5]:  # Show first 5
        print("  - " + wire_name)
    if len(boundary_z_wires) > 5:
        print("  ... and " + str(len(boundary_z_wires) - 5) + " more")

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

def create_load_application_set(assembly):
    """Create a set containing all top-level RPs for load application."""
    
    print("Creating load application set...")
    
    # Find maximum y level first
    modular_sets = [name for name in assembly.sets.keys() 
                   if name.startswith('RP_x') and '_y' in name and '_z' in name]
    
    if len(modular_sets) == 0:
        print("No modular RP sets found")
        return None
    
    max_y = max([int(s.split('_')[2][1:]) for s in modular_sets if len(s.split('_')) >= 3])
    
    # Find all RPs at top level
    top_rps = find_rps_in_module_range(assembly, y_range=(max_y, max_y))
    
    if len(top_rps) > 0:
        set_name = "RPs_LoadApplication"
        try:
            assembly.Set(referencePoints=tuple(top_rps), name=set_name)
            print("Created load application set '{}' with {} RPs at level {}".format(set_name, len(top_rps), max_y))
            return set_name
        except Exception as e:
            print("Error creating load application set: {}".format(e))
            return None
    else:
        print("No top-level RPs found")
        return None

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    try:
        create_boundary_supports_all_endpoints()
        verify_boundary_supports()
        
        print("")
        print("=== MODULAR RP MANAGEMENT READY ===")
        print("Individual access: Use sets named 'RP_x#_y#_z#' where #=module coordinates")
        print("Purpose sets: Create programmatically when needed")
        print("")
        print("Available utility functions:")
        print("- create_ground_supports_set(assembly)")
        print("- create_load_application_set(assembly)")
        print("- get_rp_by_module_coords(assembly, mod_x, mod_y, mod_z)")
        print("- find_rps_in_module_range(assembly, x_range, y_range, z_range)")
        
        # Show summary of created RPs
        assembly = mdb.models['Model-1'].rootAssembly
        list_modular_rps(assembly)
        
    except Exception as e:
        print("Error in main execution: " + str(e))
        import traceback
        traceback.print_exc()