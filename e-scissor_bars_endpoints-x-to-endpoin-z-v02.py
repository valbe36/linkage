# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import regionToolset
import math

def create_rp_wires_at_barx_barz_intersections():
    """
    Find coincident points between BarX and BarZ bars.
    Create one RP per intersection point (using default Abaqus names).
    Create wires: RP to BarX (with X in name), RP to BarZ (with Z in name).
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    # Get all instances in the assembly
    instances = assembly.instances
    
    print("Finding BarX and BarZ bar endpoints...")
    
    # Get all BarX and BarZ bar endpoints
    barx_endpoints = get_bar_endpoints(instances, 'BarX')
    barz_endpoints = get_bar_endpoints(instances, 'BarZ')
    
    print("Found " + str(len(barx_endpoints)) + " BarX endpoints")
    print("Found " + str(len(barz_endpoints)) + " BarZ endpoints")
    
    # Find coincident points between BarX and BarZ
    intersection_points = find_barx_barz_intersections(barx_endpoints, barz_endpoints)
    
    print("Found " + str(len(intersection_points)) + " BarX-BarZ intersection points")
    
    # Create RPs and wires
    rp_count = 0
    wire_x_count = 0
    wire_z_count = 0
    
    # Create RPs first
    rp_data = []
    for i, (location, barx_bars, barz_bars) in enumerate(intersection_points):
        created_rp = create_reference_point(assembly, location, i)
        
        if created_rp:
            rp_count += 1
            print("")
            print("Created RP at " + str(location))
            print("  BarX bars at this location: " + str(len(barx_bars)))
            for bar_info in barx_bars:
                print("    - " + bar_info[0].name)
            print("  BarZ bars at this location: " + str(len(barz_bars)))
            for bar_info in barz_bars:
                print("    - " + bar_info[0].name)
            
            # Store data for wire creation
            rp_data.append((i, created_rp, location, barx_bars, barz_bars))
    
    print("")
    print("Creating BarX wires (RP to BarX)...")
    
    # Create BarX wires first
    for i, rp, location, barx_bars, barz_bars in rp_data:
        if len(barx_bars) > 0:
            # Pick first BarX bar as representative
            representative_barx = barx_bars[0]
            wire_name = "Wire_RP_BarX_" + str(i) + "_X"
            
            if create_rp_to_bar_wire(assembly, rp, representative_barx, location, wire_name, "BarX"):
                wire_x_count += 1
    
    print("")
    print("Creating BarZ wires (RP to BarZ)...")
    
    # Create BarZ wires second
    for i, rp, location, barx_bars, barz_bars in rp_data:
        if len(barz_bars) > 0:
            # Pick first BarZ bar as representative
            representative_barz = barz_bars[0]
            wire_name = "Wire_RP_BarZ_" + str(i) + "_Z"
            
            if create_rp_to_bar_wire(assembly, rp, representative_barz, location, wire_name, "BarZ"):
                wire_z_count += 1
    
    print("")
    print("Summary:")
    print("  Reference Points created: " + str(rp_count))
    print("  RP-to-BarX wires created: " + str(wire_x_count))
    print("  RP-to-BarZ wires created: " + str(wire_z_count))

def get_bar_endpoints(instances, bar_type):
    """
    Get all endpoints for bars of specified type (BarX or BarZ).
    Returns list of: (instance, endpoint_coord, endpoint_type)
    """
    endpoints = []
    
    for inst in instances.values():
        if inst.name.startswith(bar_type + '-'):
            try:
                # Get endpoints (first and last vertices)
                vertices = inst.vertices
                if len(vertices) >= 2:
                    endpoint1 = vertices[0].pointOn[0]
                    endpoint2 = vertices[-1].pointOn[0]
                    
                    # Round coordinates to avoid floating point issues
                    coord1 = (round(endpoint1[0], 2), round(endpoint1[1], 2), round(endpoint1[2], 2))
                    coord2 = (round(endpoint2[0], 2), round(endpoint2[1], 2), round(endpoint2[2], 2))
                    
                    endpoints.append((inst, coord1, 'start'))
                    endpoints.append((inst, coord2, 'end'))
                    
            except Exception as e:
                print("Error processing " + bar_type + " endpoints for " + inst.name + ": " + str(e))
    
    return endpoints

def find_barx_barz_intersections(barx_endpoints, barz_endpoints):
    """
    Find coincident points between BarX and BarZ endpoints.
    Returns list of: (location, barx_bars_at_location, barz_bars_at_location)
    """
    intersection_points = []
    processed_locations = set()
    tolerance = 0.1
    
    # Compare each BarX endpoint with each BarZ endpoint
    for barx_inst, barx_coord, barx_type in barx_endpoints:
        for barz_inst, barz_coord, barz_type in barz_endpoints:
            
            # Calculate distance between endpoints
            distance = math.sqrt(sum([(barx_coord[i] - barz_coord[i])**2 for i in range(3)]))
            
            if distance < tolerance:
                # Found coincident point
                # Use average position as intersection location
                avg_location = (
                    (barx_coord[0] + barz_coord[0]) / 2.0,
                    (barx_coord[1] + barz_coord[1]) / 2.0,
                    (barx_coord[2] + barz_coord[2]) / 2.0
                )
                
                # Round to avoid duplicates
                rounded_location = (round(avg_location[0], 2), round(avg_location[1], 2), round(avg_location[2], 2))
                
                if rounded_location not in processed_locations:
                    processed_locations.add(rounded_location)
                    
                    # Find all BarX and BarZ bars at this location
                    barx_bars_here = find_bars_at_location(barx_endpoints, rounded_location, tolerance)
                    barz_bars_here = find_bars_at_location(barz_endpoints, rounded_location, tolerance)
                    
                    if len(barx_bars_here) > 0 and len(barz_bars_here) > 0:
                        intersection_points.append((rounded_location, barx_bars_here, barz_bars_here))
                        
                        print("Intersection found at " + str(rounded_location) + ":")
                        print("  Distance: " + str(round(distance, 6)))
                        print("  BarX bars: " + str(len(barx_bars_here)))
                        print("  BarZ bars: " + str(len(barz_bars_here)))
    
    return intersection_points

def find_bars_at_location(endpoints, target_location, tolerance):
    """
    Find all bars that have an endpoint at the target location.
    Returns list of: (instance, coord, endpoint_type)
    """
    bars_at_location = []
    
    for inst, coord, endpoint_type in endpoints:
        distance = math.sqrt(sum([(coord[i] - target_location[i])**2 for i in range(3)]))
        
        if distance < tolerance:
            bars_at_location.append((inst, coord, endpoint_type))
    
    return bars_at_location

def create_reference_point(assembly, location, index):
    """
    Create a reference point at the specified location with coordinate-based naming.
    """
    try:
        rp_feature = assembly.ReferencePoint(point=location)
        rp = assembly.referencePoints[rp_feature.id]
        
        # Create coordinate-based name for easy identification
        x_coord = int(round(location[0]))
        y_coord = int(round(location[1]))
        z_coord = int(round(location[2]))
        coord_name = "RP_X" + str(x_coord) + "_Y" + str(y_coord) + "_Z" + str(z_coord)
        
        # Create a set for the reference point with coordinate name
        assembly.Set(referencePoints=(rp,), name=coord_name)
        
        print("  Created RP at " + str(location) + " with set: " + coord_name)
        return rp
        
    except Exception as e:
        print("Error creating reference point: " + str(e))
        return None

def create_rp_to_bar_wire(assembly, rp, bar_info, rp_location, wire_name, bar_type):
    """
    Create a wire from reference point to bar endpoint.
    bar_info is: (instance, coord, endpoint_type)
    """
    try:
        bar_instance, bar_coord, endpoint_type = bar_info
        
        print("Creating " + bar_type + " wire: RP to " + bar_instance.name)
        print("  Wire name: " + wire_name)
        print("  Bar endpoint: " + str(bar_coord))
        
        # Find the exact vertex at the bar coordinate
        target_vertex = find_vertex_at_coordinate(bar_instance, bar_coord)
        
        if target_vertex is None:
            print("  Error: Could not find vertex at coordinate " + str(bar_coord))
            return False
        
        # Create wire from RP to bar vertex
        wire_feature = assembly.WirePolyLine(
            mergeType=IMPRINT,
            meshable=False,
            points=((rp, target_vertex),)
        )
        
        # Rename the wire feature
        old_name = wire_feature.name
        assembly.features.changeKey(old_name, wire_name)
        
        print("  Successfully created wire: " + wire_name)
        
        # Try to create set for manual section assignment
        try:
            set_name = "Set_" + wire_name
            
            # Find the edge at the location
            avg_pos = ((rp_location[0] + bar_coord[0])/2, (rp_location[1] + bar_coord[1])/2, (rp_location[2] + bar_coord[2])/2)
            edges_at_pos = assembly.edges.findAt((avg_pos,))
            
            if edges_at_pos:
                assembly.Set(edges=(edges_at_pos[0],), name=set_name)
                print("  Created set: " + set_name + " (ready for manual section assignment)")
            else:
                print("  Note: Set creation skipped - assign section manually in GUI")
                
        except Exception as assign_error:
            print("  Note: Set creation failed - assign section manually in GUI: " + str(assign_error))
        
        return True
        
    except Exception as e:
        print("Error creating wire " + wire_name + ": " + str(e))
        return False

def find_vertex_at_coordinate(instance, target_coord):
    """
    Find the vertex of an instance at the specified coordinate.
    """
    try:
        vertices = instance.vertices
        tolerance = 0.1
        
        for vertex in vertices:
            vertex_coord = vertex.pointOn[0]
            rounded_coord = (round(vertex_coord[0], 2), round(vertex_coord[1], 2), round(vertex_coord[2], 2))
            
            if rounded_coord == target_coord:
                return vertex
        
        # If exact match not found, find closest vertex
        min_distance = float('inf')
        closest_vertex = None
        
        for vertex in vertices:
            vertex_coord = vertex.pointOn[0]
            distance = math.sqrt(sum([(vertex_coord[i] - target_coord[i])**2 for i in range(3)]))
            
            if distance < min_distance:
                min_distance = distance
                closest_vertex = vertex
        
        if min_distance < tolerance:
            return closest_vertex
        
        return None
        
    except Exception as e:
        print("Error finding vertex at coordinate " + str(target_coord) + " for " + instance.name + ": " + str(e))
        return None

def verify_rp_wires():
    """
    Verify that RPs and wires were created correctly.
    """
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("")
    print("=== RP Wire Verification ===")
    
    # Count reference points
    rp_count = len(assembly.referencePoints)
    print("Total reference points: " + str(rp_count))
    
    # Count RP wires
    rp_barx_wires = []
    rp_barz_wires = []
    
    for feature_name in assembly.features.keys():
        if 'Wire_RP_BarX' in feature_name:
            rp_barx_wires.append(feature_name)
        elif 'Wire_RP_BarZ' in feature_name:
            rp_barz_wires.append(feature_name)
    
    print("RP-to-BarX wire features created: " + str(len(rp_barx_wires)))
    for wire_name in rp_barx_wires[:5]:  # Show first 5
        print("  - " + wire_name)
    if len(rp_barx_wires) > 5:
        print("  ... and " + str(len(rp_barx_wires) - 5) + " more")
    
    print("RP-to-BarZ wire features created: " + str(len(rp_barz_wires)))
    for wire_name in rp_barz_wires[:5]:  # Show first 5
        print("  - " + wire_name)
    if len(rp_barz_wires) > 5:
        print("  ... and " + str(len(rp_barz_wires) - 5) + " more")
    
    # Count sets for manual section assignment
    rp_sets = []
    for set_name in assembly.sets.keys():
        if 'Wire_RP' in set_name:
            rp_sets.append(set_name)
    
    print("Sets created for manual section assignment: " + str(len(rp_sets)))

# Main execution
if __name__ == "__main__":
    try:
        print("Starting RP and wire creation at BarX-BarZ intersections...")
        create_rp_wires_at_barx_barz_intersections()
        verify_rp_wires()
        print("")
        print("RP and wire creation completed!")
        print("")
        print("Note: You can now manually assign connector sections to these wires in the GUI.")
        print("  - RP-to-BarX wires (with X): Apply revolute joints with X-axis rotation")
        print("  - RP-to-BarZ wires (with Z): Apply revolute joints with Z-axis rotation")
        
    except Exception as e:
        print("Error in main execution: " + str(e))
        import traceback
        traceback.print_exc()