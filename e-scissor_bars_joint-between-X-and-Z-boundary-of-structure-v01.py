# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import regionToolset
import math

def create_boundary_barx_barz_joints():
    """
    Create RPs and constrained wires at boundary BarX-BarZ intersections.
    Excludes internal intersections (those with 4+ bars per type).
    Creates separate RP->BarX and RP->BarZ wires with clear naming.
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    instances = assembly.instances
    
    print("=== BOUNDARY BarX-BarZ JOINT CREATION ===")
    print("")
    print("Step 1: Finding boundary intersection points...")
    
    # Find boundary intersections (exclude internal ones)
    boundary_intersections = find_boundary_barx_barz_intersections(instances)
    
    print("")
    print("Step 2: Creating RPs and wires at boundary intersections...")
    
    # Create RPs and wires
    rp_count, wire_x_count, wire_z_count = create_boundary_rps_and_wires(assembly, boundary_intersections)
    
    print("")
    print("=== SUMMARY ===")
    print("Boundary intersection points: " + str(len(boundary_intersections)))
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

def find_boundary_barx_barz_intersections(instances):
    """
    Find boundary intersections between BarX and BarZ.
    Boundary = BarX and BarZ meet, but < 2 bars of any type (not internal).
    """
    
    # Group all bars by their vertex locations
    location_groups = group_bars_by_vertices(instances)
    
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
            # We have both bar types - check if it's boundary (not internal)
            total_bars = (bar_counts['BarX-a'] + bar_counts['BarX-b'] + 
                         bar_counts['BarZ-a'] + bar_counts['BarZ-b'])
            
            # Internal intersection criteria (to EXCLUDE):
            # Internal = 2+ BarX-a AND 2+ BarX-b AND 2+ BarZ-a AND 2+ BarZ-b
            is_internal = (bar_counts['BarX-a'] >= 2 and bar_counts['BarX-b'] >= 2 and
                          bar_counts['BarZ-a'] >= 2 and bar_counts['BarZ-b'] >= 2)
            
            if not is_internal:
                # This is a boundary intersection
                print("Boundary intersection at " + str(location) + ":")
                print("  BarX-a: " + str(bar_counts['BarX-a']) + ", BarX-b: " + str(bar_counts['BarX-b']))
                print("  BarZ-a: " + str(bar_counts['BarZ-a']) + ", BarZ-b: " + str(bar_counts['BarZ-b']))
                print("  Total: " + str(total_bars) + " bars")
                print("  -> BOUNDARY intersection (< 2 bars of some type)")
                
                boundary_intersections.append((location, bars_at_location, bar_counts))
            else:
                print("Skipping internal intersection at " + str(location) + " (4+ bars per type)")
    
    return boundary_intersections

def group_bars_by_vertices(instances):
    """
    Group bars by their vertex locations (start, midpoint, end).
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

def create_boundary_rps_and_wires(assembly, boundary_intersections):
    """
    Create RPs and separate wires for boundary intersections.
    Returns (rp_count, wire_x_count, wire_z_count).
    """
    rp_count = 0
    wire_x_count = 0
    wire_z_count = 0
    
    # Store RP and wire data for organized creation
    boundary_rps = []
    
    # First pass: Create all RPs
    print("Creating Reference Points...")
    for i, (location, bars_at_location, bar_counts) in enumerate(boundary_intersections):
        
        # Create descriptive RP name based on coordinates
        x_coord = int(round(location[0]))
        y_coord = int(round(location[1]))
        z_coord = int(round(location[2]))
        rp_name = "RP_Boundary_X" + str(x_coord) + "_Y" + str(y_coord) + "_Z" + str(z_coord)
        
        print("")
        print("Creating RP " + str(i+1) + ": " + rp_name)
        print("  Location: " + str(location))
        
        try:
            rp_feature = assembly.ReferencePoint(point=location)
            rp = assembly.referencePoints[rp_feature.id]
            rp_count += 1
            
            print("  RP created successfully")
            
            # Find representative bars
            barx_rep = find_representative_bar(bars_at_location, 'BarX')
            barz_rep = find_representative_bar(bars_at_location, 'BarZ')
            
            # Store for wire creation
            boundary_rps.append((i+1, rp, location, barx_rep, barz_rep))
            
        except Exception as e:
            print("  Error creating RP: " + str(e))
    
    # Second pass: Create BarX wires first
    print("")
    print("Creating RP-to-BarX wires...")
    for rp_index, rp, location, barx_rep, barz_rep in boundary_rps:
        if barx_rep:
            wire_name = "Boundary_X_" + str(rp_index)
            if create_rp_to_bar_wire(assembly, rp, barx_rep, location, wire_name, "BarX"):
                wire_x_count += 1
        else:
            print("  Warning: No BarX representative found for RP " + str(rp_index))
    
    # Third pass: Create BarZ wires second
    print("")
    print("Creating RP-to-BarZ wires...")
    for rp_index, rp, location, barx_rep, barz_rep in boundary_rps:
        if barz_rep:
            wire_name = "Boundary_Z_" + str(rp_index)
            if create_rp_to_bar_wire(assembly, rp, barz_rep, location, wire_name, "BarZ"):
                wire_z_count += 1
        else:
            print("  Warning: No BarZ representative found for RP " + str(rp_index))
    
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

def verify_boundary_joints():
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
    for wire_name in boundary_x_wires:
        print("  - " + wire_name)
    
    print("Boundary BarZ wires: " + str(len(boundary_z_wires)))
    for wire_name in boundary_z_wires:
        print("  - " + wire_name)

# Main execution
if __name__ == "__main__":
    try:
        create_boundary_barx_barz_joints()
        verify_boundary_joints()
        
    except Exception as e:
        print("Error in main execution: " + str(e))
        import traceback
        traceback.print_exc()