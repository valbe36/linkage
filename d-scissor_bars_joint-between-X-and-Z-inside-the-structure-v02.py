# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import regionToolset
import math

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

# Main execution
if __name__ == "__main__":
    try:
        create_internal_universal_joints()
        verify_universal_joints()
        
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