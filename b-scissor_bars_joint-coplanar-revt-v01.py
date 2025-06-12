# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import regionToolset
import math

def create_simple_bar_intersection_wires():
    """
    Create wires between intersecting bar pairs:
    - BarX-a <-> BarX-b at intersection points
    - BarZ-a <-> BarZ-b at intersection points
    If multiple bars intersect at same point, create only one wire per bar type.
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    # Get all instances in the assembly
    instances = assembly.instances
    
    print("Starting simple bar intersection wire creation...")
    print("")
    
    # Find BarX intersections and create wires
    barx_wires = create_barx_intersection_wires(assembly, instances)
    
    print("")
    
    # Find BarZ intersections and create wires
    barz_wires = create_barz_intersection_wires(assembly, instances)
    
    print("")
    print("=== SUMMARY ===")
    print("BarX intersection wires created: " + str(barx_wires))
    print("BarZ intersection wires created: " + str(barz_wires))
    print("Total wires created: " + str(barx_wires + barz_wires))
    print("")
    print("NEXT STEPS:")
    print("1. In Abaqus GUI, go to Interaction > Connector Assignment")
    print("2. Select wires named 'WireBetweenBarX_##' and apply HINGE connectors with X-axis rotation")
    print("3. Select wires named 'WireBetweenBarZ_##' and apply HINGE connectors with Z-axis rotation")
    print("4. This will create the revolute joints for your scissor mechanism")

def create_barx_intersection_wires(assembly, instances):
    """
    Find intersections between BarX-a and BarX-b bars and create wires.
    """
    print("Creating BarX intersection wires...")
    
    # Get all BarX bars
    barx_a_bars = []
    barx_b_bars = []
    
    for inst in instances.values():
        if inst.name.startswith('BarX-a_'):
            barx_a_bars.append(inst)
        elif inst.name.startswith('BarX-b_'):
            barx_b_bars.append(inst)
    
    print("Found " + str(len(barx_a_bars)) + " BarX-a bars")
    print("Found " + str(len(barx_b_bars)) + " BarX-b bars")
    
    # Find intersection points
    intersection_data = find_bar_intersections(barx_a_bars, barx_b_bars, "BarX")
    
    print("Found " + str(len(intersection_data)) + " BarX intersection points")
    
    # Create wires
    wires_created = 0
    for i, (location, bar_a, bar_b, vertex_a, vertex_b) in enumerate(intersection_data):
        wire_name = "WireBetweenBarX_" + str(i + 1)
        
        if create_intersection_wire(assembly, bar_a, bar_b, location, wire_name, vertex_a, vertex_b):
            wires_created += 1
    
    return wires_created

def create_barz_intersection_wires(assembly, instances):
    """
    Find intersections between BarZ-a and BarZ-b bars and create wires.
    """
    print("Creating BarZ intersection wires...")
    
    # Get all BarZ bars
    barz_a_bars = []
    barz_b_bars = []
    
    for inst in instances.values():
        if inst.name.startswith('BarZ-a_'):
            barz_a_bars.append(inst)
        elif inst.name.startswith('BarZ-b_'):
            barz_b_bars.append(inst)
    
    print("Found " + str(len(barz_a_bars)) + " BarZ-a bars")
    print("Found " + str(len(barz_b_bars)) + " BarZ-b bars")
    
    # Find intersection points
    intersection_data = find_bar_intersections(barz_a_bars, barz_b_bars, "BarZ")
    
    print("Found " + str(len(intersection_data)) + " BarZ intersection points")
    
    # Create wires
    wires_created = 0
    for i, (location, bar_a, bar_b, vertex_a, vertex_b) in enumerate(intersection_data):
        wire_name = "WireBetweenBarZ_" + str(i + 1)
        
        if create_intersection_wire(assembly, bar_a, bar_b, location, wire_name, vertex_a, vertex_b):
            wires_created += 1
    
    return wires_created

def find_bar_intersections(bars_a, bars_b, bar_type):
    """
    Find intersection points between 'a' and 'b' type bars.
    Checks all possible intersections: endpoints and midpoints.
    Returns list of (location, representative_a, representative_b, vertex_a, vertex_b).
    """
    intersection_data = []
    processed_locations = set()
    tolerance = 0.1
    
    print("Searching for " + bar_type + " intersection points (all vertices)...")
    
    # Compare each 'a' bar with each 'b' bar
    for bar_a in bars_a:
        try:
            vertices_a = bar_a.vertices
            # Get all key points: start (0), midpoint (2), end (-1)
            if len(vertices_a) < 3:
                continue
                
            points_a = [
                (vertices_a[0], vertices_a[0].pointOn[0], 'start'),   # Start point
                (vertices_a[2], vertices_a[2].pointOn[0], 'mid'),     # Midpoint  
                (vertices_a[-1], vertices_a[-1].pointOn[0], 'end')    # End point
            ]
            
            for bar_b in bars_b:
                try:
                    vertices_b = bar_b.vertices
                    if len(vertices_b) < 3:
                        continue
                        
                    points_b = [
                        (vertices_b[0], vertices_b[0].pointOn[0], 'start'),   # Start point
                        (vertices_b[2], vertices_b[2].pointOn[0], 'mid'),     # Midpoint
                        (vertices_b[-1], vertices_b[-1].pointOn[0], 'end')    # End point
                    ]
                    
                    # Check all point combinations
                    best_distance = float('inf')
                    best_intersection = None
                    
                    for vertex_a, coord_a, type_a in points_a:
                        for vertex_b, coord_b, type_b in points_b:
                            # Calculate distance between points
                            distance = math.sqrt(sum([(coord_a[i] - coord_b[i])**2 for i in range(3)]))
                            
                            if distance < tolerance and distance < best_distance:
                                # Found intersection - use average position
                                avg_location = (
                                    (coord_a[0] + coord_b[0]) / 2.0,
                                    (coord_a[1] + coord_b[1]) / 2.0,
                                    (coord_a[2] + coord_b[2]) / 2.0
                                )
                                
                                best_distance = distance
                                best_intersection = (avg_location, bar_a, bar_b, vertex_a, vertex_b, type_a, type_b)
                    
                    # If we found an intersection for this bar pair
                    if best_intersection:
                        avg_location, bar_a, bar_b, vertex_a, vertex_b, type_a, type_b = best_intersection
                        
                        # Round to avoid duplicate nearby locations
                        rounded_location = (
                            round(avg_location[0], 1),
                            round(avg_location[1], 1),
                            round(avg_location[2], 1)
                        )
                        
                        # Only create one wire per location
                        if rounded_location not in processed_locations:
                            processed_locations.add(rounded_location)
                            intersection_data.append((avg_location, bar_a, bar_b, vertex_a, vertex_b))
                            
                            print("  Intersection: " + bar_a.name + " <-> " + bar_b.name)
                            print("    Location: " + str(avg_location) + " (distance: " + str(round(best_distance, 6)) + ")")
                            print("    Connection: " + type_a + " to " + type_b)
                
                except Exception as e:
                    print("  Error processing " + bar_b.name + ": " + str(e))
                    
        except Exception as e:
            print("  Error processing " + bar_a.name + ": " + str(e))
    
    return intersection_data

def create_intersection_wire(assembly, bar_a, bar_b, location, wire_name, vertex_a, vertex_b):
    """
    Create a wire between the specified vertices of two intersecting bars.
    """
    try:
        print("Creating wire: " + wire_name)
        print("  Between: " + bar_a.name + " and " + bar_b.name)
        
        # Create wire between the specific intersection vertices
        wire_feature = assembly.WirePolyLine(
            mergeType=IMPRINT,
            meshable=False,
            points=((vertex_a, vertex_b),)
        )
        
        # Rename the wire feature
        old_name = wire_feature.name
        assembly.features.changeKey(old_name, wire_name)
        
        print("  Successfully created wire: " + wire_name)
        return True
        
    except Exception as e:
        print("  Error creating wire " + wire_name + ": " + str(e))
        return False

def verify_wires():
    """
    Verify that wires were created correctly.
    """
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("")
    print("=== WIRE VERIFICATION ===")
    
    # Count wires
    barx_wires = []
    barz_wires = []
    
    for feature_name in assembly.features.keys():
        if feature_name.startswith('WireBetweenBarX'):
            barx_wires.append(feature_name)
        elif feature_name.startswith('WireBetweenBarZ'):
            barz_wires.append(feature_name)
    
    print("BarX wires in model:")
    for wire_name in barx_wires:
        print("  - " + wire_name)
    
    print("BarZ wires in model:")
    for wire_name in barz_wires:
        print("  - " + wire_name)
    
    print("")
    print("Total BarX wires: " + str(len(barx_wires)))
    print("Total BarZ wires: " + str(len(barz_wires)))
    print("Total wires: " + str(len(barx_wires) + len(barz_wires)))

# Main execution
if __name__ == "__main__":
    try:
        create_simple_bar_intersection_wires()
        verify_wires()
        
    except Exception as e:
        print("Error in main execution: " + str(e))
        import traceback
        traceback.print_exc()