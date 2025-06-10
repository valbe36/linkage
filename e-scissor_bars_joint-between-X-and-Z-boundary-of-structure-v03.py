# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import regionToolset
import math

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

# Main execution
if __name__ == "__main__":
    try:
        create_boundary_supports_all_endpoints()
        verify_boundary_supports()
        
    except Exception as e:
        print("Error in main execution: " + str(e))
        import traceback
        traceback.print_exc()
        print("")
    print("=== MODULAR RP MANAGEMENT READY ===")
    print("Individual access: Use sets named 'RP_x#_y#_z#' where #=module coordinates")
    print("Purpose sets: Create programmatically when needed")
    print("")
    print("Available utility functions:")
    print("- create_ground_supports_set(assembly)")
    print("- create_load_application_set(assembly)")  
    print("- create_cable_attachment_set(assembly)")
    print("- get_rp_by_module_coords(assembly, mod_x, mod_y, mod_z)")
    print("- find_rps_in_module_range(assembly, x_range, y_range, z_range)")