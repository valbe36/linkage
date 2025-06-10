# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import regionToolset
import math

def create_wires_between_coincident_endpoints():
    """
    Create wires between coincident endpoints of different bar subtypes:
    - BarX-a and BarX-b (when endpoints coincide)
    - BarZ-a and BarZ-b (when endpoints coincide)
    At each location, pick only 1 representative from each subtype.
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    # Get all instances in the assembly
    instances = assembly.instances
    
    print("Grouping bars by endpoint locations...")
    
    # Group all bars by their endpoint locations
    endpoint_groups = group_bars_by_endpoints(instances)
    print("Found " + str(len(endpoint_groups)) + " unique endpoint locations")
    
    # Find locations where different subtypes meet
    barx_connections = find_subtype_intersections(endpoint_groups, 'BarX')
    barz_connections = find_subtype_intersections(endpoint_groups, 'BarZ')
    
    print("Found " + str(len(barx_connections)) + " BarX connection points")
    print("Found " + str(len(barz_connections)) + " BarZ connection points")
    
    # Create wires
    total_created = 0
    
    print("")
    print("Creating BarX wires...")
    for i, (location, bar_a, bar_b) in enumerate(barx_connections):
        wire_name = "Wire_BarX_Joint_" + str(i)
        if create_endpoint_wire(assembly, bar_a, bar_b, location, wire_name, "BarX"):
            total_created += 1
    
    print("")
    print("Creating BarZ wires...")
    for i, (location, bar_a, bar_b) in enumerate(barz_connections):
        wire_name = "Wire_BarZ_Joint_" + str(i)
        if create_endpoint_wire(assembly, bar_a, bar_b, location, wire_name, "BarZ"):
            total_created += 1
    
    print("")
    print("Successfully created " + str(total_created) + " endpoint wires")

def group_bars_by_endpoints(instances):
    """
    Group all bars by their endpoint locations.
    Returns dict: coordinate_tuple -> bar_category -> list of instances
    """
    endpoint_groups = {}
    
    for inst in instances.values():
        if inst.name.startswith(('BarX-', 'BarZ-')):
            try:
                # Determine bar type and subtype
                if inst.name.startswith('BarX-a'):
                    bar_category = 'BarX-a'
                elif inst.name.startswith('BarX-b'):
                    bar_category = 'BarX-b'
                elif inst.name.startswith('BarZ-a'):
                    bar_category = 'BarZ-a'
                elif inst.name.startswith('BarZ-b'):
                    bar_category = 'BarZ-b'
                else:
                    continue
                
                # Get endpoints (first and last vertices)
                vertices = inst.vertices
                if len(vertices) >= 2:
                    endpoint1 = vertices[0].pointOn[0]
                    endpoint2 = vertices[-1].pointOn[0]
                    
                    # Round coordinates to avoid floating point issues
                    coord1 = (round(endpoint1[0], 2), round(endpoint1[1], 2), round(endpoint1[2], 2))
                    coord2 = (round(endpoint2[0], 2), round(endpoint2[1], 2), round(endpoint2[2], 2))
                    
                    # Add to groups
                    for coord in [coord1, coord2]:
                        if coord not in endpoint_groups:
                            endpoint_groups[coord] = {}
                        if bar_category not in endpoint_groups[coord]:
                            endpoint_groups[coord][bar_category] = []
                        endpoint_groups[coord][bar_category].append(inst)
                        
            except Exception as e:
                print("Error processing endpoints for " + inst.name + ": " + str(e))
    
    return endpoint_groups

def find_subtype_intersections(endpoint_groups, bar_type):
    """
    Find locations where both a and b subtypes of the same bar type meet.
    Returns list of: (location, representative_a, representative_b)
    """
    connections = []
    
    for location, bars_at_location in endpoint_groups.items():
        # Check if both subtypes are present
        subtype_a_key = bar_type + "-a"
        subtype_b_key = bar_type + "-b"
        
        if subtype_a_key in bars_at_location and subtype_b_key in bars_at_location:
            # Get representatives (just pick the first one from each list)
            bars_a = bars_at_location[subtype_a_key]
            bars_b = bars_at_location[subtype_b_key]
            
            if len(bars_a) > 0 and len(bars_b) > 0:
                representative_a = bars_a[0]  # Pick first one
                representative_b = bars_b[0]  # Pick first one
                
                connections.append((location, representative_a, representative_b))
                
                print(bar_type + " intersection at " + str(location) + ":")
                print("  " + str(len(bars_a)) + " " + subtype_a_key + " bars available, selected: " + representative_a.name)
                print("  " + str(len(bars_b)) + " " + subtype_b_key + " bars available, selected: " + representative_b.name)
    
    return connections

def create_endpoint_wire(assembly, bar_a, bar_b, location, wire_name, bar_type):
    """
    Create a wire between endpoints of two bars at the specified location.
    """
    try:
        print("Creating " + bar_type + " wire: " + bar_a.name + " and " + bar_b.name)
        print("  Wire name: " + wire_name)
        print("  At location: " + str(location))
        
        # Find the exact vertices at the specified location
        vertex_a = find_vertex_at_location(bar_a, location)
        vertex_b = find_vertex_at_location(bar_b, location)
        
        if vertex_a is None or vertex_b is None:
            print("  Error: Could not find vertices at location " + str(location))
            return False
        
        # Create wire between the vertices
        wire_feature = assembly.WirePolyLine(
            mergeType=IMPRINT,
            meshable=False,
            points=((vertex_a, vertex_b),)
        )
        
        # Rename the wire feature
        old_name = wire_feature.name
        assembly.features.changeKey(old_name, wire_name)
        
        print("  Successfully created wire: " + wire_name)
        
        # Try to assign section (optional - can be done manually in GUI)
        try:
            # Create a simple set name for manual section assignment later
            set_name = "Set_" + wire_name
            
            # Find the edge at the location
            avg_pos = location
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

def find_vertex_at_location(instance, target_location):
    """
    Find the vertex of an instance that is closest to the target location.
    """
    try:
        vertices = instance.vertices
        tolerance = 0.1
        
        for vertex in vertices:
            vertex_coord = vertex.pointOn[0]
            rounded_coord = (round(vertex_coord[0], 2), round(vertex_coord[1], 2), round(vertex_coord[2], 2))
            
            if rounded_coord == target_location:
                return vertex
        
        # If exact match not found, find closest vertex
        min_distance = float('inf')
        closest_vertex = None
        
        for vertex in vertices:
            vertex_coord = vertex.pointOn[0]
            distance = math.sqrt(sum([(vertex_coord[i] - target_location[i])**2 for i in range(3)]))
            
            if distance < min_distance:
                min_distance = distance
                closest_vertex = vertex
        
        if min_distance < tolerance:
            return closest_vertex
        
        return None
        
    except Exception as e:
        print("Error finding vertex at location " + str(target_location) + " for " + instance.name + ": " + str(e))
        return None

def verify_endpoint_wires():
    """
    Verify that endpoint wires were created correctly.
    """
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("")
    print("=== Endpoint Wire Verification ===")
    
    # Count BarX wires
    barx_wires = []
    barz_wires = []
    
    for feature_name in assembly.features.keys():
        if 'Wire_BarX_Joint' in feature_name:
            barx_wires.append(feature_name)
        elif 'Wire_BarZ_Joint' in feature_name:
            barz_wires.append(feature_name)
    
    print("BarX wire features created: " + str(len(barx_wires)))
    for wire_name in barx_wires[:5]:  # Show first 5
        print("  - " + wire_name)
    if len(barx_wires) > 5:
        print("  ... and " + str(len(barx_wires) - 5) + " more")
    
    print("BarZ wire features created: " + str(len(barz_wires)))
    for wire_name in barz_wires[:5]:  # Show first 5
        print("  - " + wire_name)
    if len(barz_wires) > 5:
        print("  ... and " + str(len(barz_wires) - 5) + " more")
    
    # Count sets for manual section assignment
    endpoint_sets = []
    for set_name in assembly.sets.keys():
        if 'Wire_Bar' in set_name:
            endpoint_sets.append(set_name)
    
    print("Sets created for manual section assignment: " + str(len(endpoint_sets)))

# Main execution
if __name__ == "__main__":
    try:
        print("Starting endpoint wire creation between different bar subtypes...")
        create_wires_between_coincident_endpoints()
        verify_endpoint_wires()
        print("")
        print("Endpoint wire creation completed!")
        print("")
        print("Note: You can now manually assign revolute joint sections to these wires in the GUI.")
        
    except Exception as e:
        print("Error in main execution: " + str(e))
        import traceback
        traceback.print_exc()