# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import math

def create_seaty_chord_joints():
    """
    Create wires between SeatY instances and ChordLower/ChordUpper instances
    at coincident points. Creates wires named SeatYLower_## and SeatYUpper_##.
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    instances = assembly.instances
    
    print("=== SEATY CHORD JOINT CREATION ===")
    print("Finding intersections between SeatY and Chord instances...")
    print("")
    
    # Find all relevant instances
    seaty_instances = []
    chord_lower_instances = []
    chord_upper_instances = []
    
    for inst_name, inst in instances.items():
        if inst_name.startswith('SeatY_'):
            seaty_instances.append(inst)
        elif inst_name.startswith('ChordLower_'):
            chord_lower_instances.append(inst)
        elif inst_name.startswith('ChordUpper_'):
            chord_upper_instances.append(inst)
    
    print("Found {} SeatY instances".format(len(seaty_instances)))
    print("Found {} ChordLower instances".format(len(chord_lower_instances)))
    print("Found {} ChordUpper instances".format(len(chord_upper_instances)))
    print("")
    
    if len(seaty_instances) == 0:
        print("ERROR: No SeatY instances found! Run SeatY creation script first.")
        return
    
    if len(chord_lower_instances) == 0 and len(chord_upper_instances) == 0:
        print("ERROR: No chord instances found! Run chord creation scripts first.")
        return
    
    # Create joints
    lower_wires = 0
    upper_wires = 0
    
    if len(chord_lower_instances) > 0:
        lower_wires = create_seaty_lower_joints(assembly, seaty_instances, chord_lower_instances)
    
    if len(chord_upper_instances) > 0:
        upper_wires = create_seaty_upper_joints(assembly, seaty_instances, chord_upper_instances)
    
    print("")
    print("=== SUMMARY ===")
    print("SeatY-ChordLower wires created: {}".format(lower_wires))
    print("SeatY-ChordUpper wires created: {}".format(upper_wires))
    print("Total wires created: {}".format(lower_wires + upper_wires))

def create_seaty_lower_joints(assembly, seaty_instances, chord_lower_instances):
    """Create wires between SeatY and ChordLower instances."""
    
    print("Creating SeatY-ChordLower joints...")
    
    wires_created = 0
    tolerance = 0.04  # Tolerance for coincident points
    processed_pairs = set()  # Avoid duplicate wires
    
    for seaty_inst in seaty_instances:
        try:
            seaty_vertices = seaty_inst.vertices
            
            for chord_inst in chord_lower_instances:
                try:
                    chord_vertices = chord_inst.vertices
                    
                    # Check for coincident vertices
                    for i, seaty_vertex in enumerate(seaty_vertices):
                        seaty_coord = seaty_vertex.pointOn[0]
                        
                        for j, chord_vertex in enumerate(chord_vertices):
                            chord_coord = chord_vertex.pointOn[0]
                            
                            # Calculate distance
                            distance = math.sqrt(
                                (seaty_coord[0] - chord_coord[0])**2 +
                                (seaty_coord[1] - chord_coord[1])**2 +
                                (seaty_coord[2] - chord_coord[2])**2
                            )
                            
                            if distance < tolerance:
                                # Create unique identifier for this vertex pair
                                pair_id = (
                                    seaty_inst.name, i,
                                    chord_inst.name, j
                                )
                                
                                # Avoid duplicate wires
                                if pair_id not in processed_pairs:
                                    processed_pairs.add(pair_id)
                                    
                                    # Found coincident points - create wire
                                    wire_name = "SeatYLower_{}".format(wires_created + 1)
                                    
                        
                except Exception as e:
                    print("  Error processing chord instance {}: {}".format(chord_inst.name, e))
                    continue
                    
        except Exception as e:
            print("  Error processing SeatY instance {}: {}".format(seaty_inst.name, e))
            continue
    
    print("  Total SeatY-ChordLower wires created: {}".format(wires_created))
    return wires_created

def create_seaty_upper_joints(assembly, seaty_instances, chord_upper_instances):
    """Create wires between SeatY and ChordUpper instances."""
    
    print("")
    print("Creating SeatY-ChordUpper joints...")
    
    wires_created = 0
    tolerance = 0.15  # Tolerance for coincident points
    processed_pairs = set()  # Avoid duplicate wires
    
    for seaty_inst in seaty_instances:
        try:
            seaty_vertices = seaty_inst.vertices
            
            for chord_inst in chord_upper_instances:
                try:
                    chord_vertices = chord_inst.vertices
                    
                    # Check for coincident vertices
                    for i, seaty_vertex in enumerate(seaty_vertices):
                        seaty_coord = seaty_vertex.pointOn[0]
                        
                        for j, chord_vertex in enumerate(chord_vertices):
                            chord_coord = chord_vertex.pointOn[0]
                            
                            # Calculate distance
                            distance = math.sqrt(
                                (seaty_coord[0] - chord_coord[0])**2 +
                                (seaty_coord[1] - chord_coord[1])**2 +
                                (seaty_coord[2] - chord_coord[2])**2
                            )
                            
                            if distance < tolerance:
                                # Create unique identifier for this vertex pair
                                pair_id = (
                                    seaty_inst.name, i,
                                    chord_inst.name, j
                                )
                                
                                # Avoid duplicate wires
                                if pair_id not in processed_pairs:
                                    processed_pairs.add(pair_id)
                                    
                                    # Found coincident points - create wire
                                    wire_name = "SeatYUpper_{}".format(wires_created + 1)
                                    

                        
                except Exception as e:
                    print("  Error processing chord instance {}: {}".format(chord_inst.name, e))
                    continue
                    
        except Exception as e:
            print("  Error processing SeatY instance {}: {}".format(seaty_inst.name, e))
            continue
    
    print("  Total SeatY-ChordUpper wires created: {}".format(wires_created))
    return wires_created

def create_wire_between_vertices(assembly, vertex1, vertex2, wire_name):
    """Create a wire between two vertices."""
    
    try:
        # Check if wire already exists
        if wire_name in assembly.features:
            print("    Wire {} already exists, skipping".format(wire_name))
            return False
        
        # Create wire
        wire_feature = assembly.WirePolyLine(
            mergeType=IMPRINT,
            meshable=False,
            points=((vertex1, vertex2),)
        )
        
        # Rename the wire feature
        old_name = wire_feature.name
        assembly.features.changeKey(old_name, wire_name)
        
        return True
        
    except Exception as e:
        print("    Error creating wire {}: {}".format(wire_name, e))
        return False

def find_nearby_instances(seaty_instances, chord_instances, max_distance=5.0):
    """
    Pre-filter instances that are close to each other to reduce search space.
    Returns pairs of (seaty_instance, chord_instance) that are potentially intersecting.
    """
    
    print("Pre-filtering nearby instances to optimize search...")
    
    nearby_pairs = []
    
    for seaty_inst in seaty_instances:
        try:
            # Get approximate center of SeatY instance
            seaty_vertices = seaty_inst.vertices
            if len(seaty_vertices) == 0:
                continue
                
            # Calculate center of SeatY instance
            seaty_center = [0.0, 0.0, 0.0]
            for vertex in seaty_vertices:
                coord = vertex.pointOn[0]
                seaty_center[0] += coord[0]
                seaty_center[1] += coord[1]
                seaty_center[2] += coord[2]
            
            seaty_center[0] /= len(seaty_vertices)
            seaty_center[1] /= len(seaty_vertices)
            seaty_center[2] /= len(seaty_vertices)
            
            for chord_inst in chord_instances:
                try:
                    # Get approximate center of chord instance
                    chord_vertices = chord_inst.vertices
                    if len(chord_vertices) == 0:
                        continue
                        
                    chord_center = [0.0, 0.0, 0.0]
                    for vertex in chord_vertices:
                        coord = vertex.pointOn[0]
                        chord_center[0] += coord[0]
                        chord_center[1] += coord[1]
                        chord_center[2] += coord[2]
                    
                    chord_center[0] /= len(chord_vertices)
                    chord_center[1] /= len(chord_vertices)
                    chord_center[2] /= len(chord_vertices)
                    
                    # Calculate distance between centers
                    center_distance = math.sqrt(
                        (seaty_center[0] - chord_center[0])**2 +
                        (seaty_center[1] - chord_center[1])**2 +
                        (seaty_center[2] - chord_center[2])**2
                    )
                    
                    if center_distance < max_distance:
                        nearby_pairs.append((seaty_inst, chord_inst))
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            continue
    
    print("  Found {} potentially intersecting instance pairs".format(len(nearby_pairs)))
    return nearby_pairs

def verify_seaty_chord_wires():
    """Verify that wires were created correctly."""
    
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("")
    print("=== WIRE VERIFICATION ===")
    
    # Count wires
    seaty_lower_wires = []
    seaty_upper_wires = []
    
    for feature_name in assembly.features.keys():
        if feature_name.startswith('SeatYLower_'):
            seaty_lower_wires.append(feature_name)
        elif feature_name.startswith('SeatYUpper_'):
            seaty_upper_wires.append(feature_name)
    
    print("SeatY-ChordLower wires:")
    for wire_name in seaty_lower_wires[:5]:  # Show first 5
        print("  - {}".format(wire_name))
    if len(seaty_lower_wires) > 5:
        print("  ... and {} more".format(len(seaty_lower_wires) - 5))
    
    print("")
    print("SeatY-ChordUpper wires:")
    for wire_name in seaty_upper_wires[:5]:  # Show first 5
        print("  - {}".format(wire_name))
    if len(seaty_upper_wires) > 5:
        print("  ... and {} more".format(len(seaty_upper_wires) - 5))
    
    print("")
    print("Total SeatY-ChordLower wires: {}".format(len(seaty_lower_wires)))
    print("Total SeatY-ChordUpper wires: {}".format(len(seaty_upper_wires)))
    print("Total SeatY chord wires: {}".format(len(seaty_lower_wires) + len(seaty_upper_wires)))

def cleanup_duplicate_wires():
    """Remove any duplicate wires that might have been created."""
    
    print("")
    print("Checking for duplicate wires...")
    
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    # Get all SeatY wire features
    seaty_wires = []
    for feature_name in assembly.features.keys():
        if feature_name.startswith('SeatYLower_') or feature_name.startswith('SeatYUpper_'):
            seaty_wires.append(feature_name)
    
    print("Found {} SeatY chord wires to check".format(len(seaty_wires)))
    
    # For now, just report - actual duplicate removal would need more complex logic
    print("Manual cleanup may be needed if duplicates are visually identified in GUI")

# Main execution
if __name__ == "__main__":
    try:
        print("SEATY CHORD JOINTS CREATION SCRIPT")
        print("=" * 40)
        print("Creates wires between SeatY and ChordLower/ChordUpper instances")
        print("at coincident points for joint modeling.")
        print("")
        
        create_seaty_chord_joints()
        verify_seaty_chord_wires()
        cleanup_duplicate_wires()
        
        print("")
        print("=== SEATY CHORD JOINTS COMPLETED ===")
        print("Wire naming convention:")
        print("- SeatYLower_## : Connections between SeatY and ChordLower")
        print("- SeatYUpper_## : Connections between SeatY and ChordUpper")
        print("")
        print("NEXT STEPS:")
        print("1. Review wire locations in Abaqus GUI")
        print("2. Create connector sections for these wire types")
        print("3. Apply appropriate connector sections to wire sets")
        print("4. Define connector behaviors as needed for joints")

        
    except Exception as e:
        print("Error in main execution: {}".format(e))
        import traceback
        traceback.print_exc()