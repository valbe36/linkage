# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import math

def create_seaty_chord_connection_wires_fixed():
    """
    FIXED: Create assembly connection wires between SeatY and chord instances.
    Uses specific vertex IDs:
    - SeatY vertices 2,8 -> ChordUpper
    - SeatY vertices 3,11 -> ChordLower
    """
    
    print("SEATY CHORD CONNECTION WIRES - VERTEX ID FIXED")
    print("=" * 55)
    print("SeatY vertex 2,8 -> ChordUpper")
    print("SeatY vertex 3,11 -> ChordLower")
    print("=" * 55)
    
    # Get model and assembly
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    # Find all instances
    seaty_instances = []
    chord_upper_instances = []
    chord_lower_instances = []
    
    for inst_name, inst in assembly.instances.items():
        if inst_name.startswith('SeatY_'):
            seaty_instances.append((inst_name, inst))
        elif inst_name.startswith('ChordUpper_'):
            chord_upper_instances.append((inst_name, inst))
        elif inst_name.startswith('ChordLower_'):
            chord_lower_instances.append((inst_name, inst))
    
    print("Found {} SeatY instances".format(len(seaty_instances)))
    print("Found {} ChordUpper instances".format(len(chord_upper_instances)))
    print("Found {} ChordLower instances".format(len(chord_lower_instances)))
    
    # Clean up existing wires
    cleanup_existing_wires(assembly)
    
    # Create connection wires
    upper_wires = 0
    lower_wires = 0
    
    if len(chord_upper_instances) > 0:
        print("\nCreating SeatY -> ChordUpper wires (vertices 2,8)...")
        upper_wires = create_seaty_to_chord_wires(
            assembly, seaty_instances, chord_upper_instances, 
            [2, 8], "seatYtoCU"
        )
    
    if len(chord_lower_instances) > 0:
        print("\nCreating SeatY -> ChordLower wires (vertices 3,11)...")
        lower_wires = create_seaty_to_chord_wires(
            assembly, seaty_instances, chord_lower_instances,
            [3, 11], "seatYtoCL"
        )
    
    # Summary
    total_wires = upper_wires + lower_wires
    print("\n=== SUMMARY ===")
    print("seatYtoCU wires created: {}".format(upper_wires))
    print("seatYtoCL wires created: {}".format(lower_wires))
    print("Total wires created: {}".format(total_wires))
    
    return total_wires > 0

def create_seaty_to_chord_wires(assembly, seaty_instances, chord_instances, seaty_vertex_ids, wire_prefix):
    """
    Create wires from specific SeatY vertices to closest chord vertices.
    """
    
    wires_created = 0
    tolerance = 0.04
    
    # Build chord vertex map for efficient searching
    chord_vertex_map = []
    for chord_inst_name, chord_inst in chord_instances:
        try:
            for vertex_id, vertex in enumerate(chord_inst.vertices):
                coord = vertex.pointOn[0]
                chord_vertex_map.append({
                    'instance_name': chord_inst_name,
                    'instance': chord_inst,
                    'vertex_id': vertex_id,
                    'vertex': vertex,
                    'coord': coord
                })
        except Exception as e:
            print("  Error processing {}: {}".format(chord_inst_name, e))
            continue
    
    print("  Built chord vertex map with {} vertices".format(len(chord_vertex_map)))
    
    # Process each SeatY instance
    for i, (seaty_inst_name, seaty_inst) in enumerate(seaty_instances):
        
        if i < 3:  # Show progress for first few
            print("    Processing {}: {}".format(i+1, seaty_inst_name))
        elif i == 3:
            print("    ... processing remaining {} instances ...".format(len(seaty_instances) - 3))
        
        try:
            # Check if SeatY instance has enough vertices
            if len(seaty_inst.vertices) <= max(seaty_vertex_ids):
                print("    WARNING: {} has only {} vertices, need at least {}".format(
                    seaty_inst_name, len(seaty_inst.vertices), max(seaty_vertex_ids) + 1))
                continue
            
            # Process each specified vertex
            for vertex_id in seaty_vertex_ids:
                try:
                    # Get SeatY vertex
                    seaty_vertex = seaty_inst.vertices[vertex_id]
                    seaty_coord = seaty_vertex.pointOn[0]
                    
                    # Find closest chord vertex
                    closest_chord = find_closest_chord_vertex_fixed(seaty_coord, chord_vertex_map, tolerance)
                    
                    if closest_chord is not None:
                        # Create wire name
                        wire_name = "{}_{}_{}_v{}".format(wire_prefix, i+1, seaty_inst_name.split('_')[-1], vertex_id)
                        
                        # Create assembly wire
                        if create_assembly_wire_fixed(assembly, wire_name, seaty_vertex, closest_chord['vertex']):
                            wires_created += 1
                            
                            if wires_created <= 5:  # Show details for first few
                                print("      Wire {}: {} vertex {} -> {} vertex {} (dist: {:.4f})".format(
                                    wires_created, seaty_inst_name, vertex_id,
                                    closest_chord['instance_name'], closest_chord['vertex_id'],
                                    calculate_distance(seaty_coord, closest_chord['coord'])))
                    else:
                        if i < 3:  # Only show warnings for first few
                            print("      No chord vertex found within tolerance for vertex {}".format(vertex_id))
                
                except Exception as e:
                    if i < 3:  # Only show errors for first few
                        print("      Error processing vertex {}: {}".format(vertex_id, e))
                    continue
        
        except Exception as e:
            print("    Error processing {}: {}".format(seaty_inst_name, e))
            continue
    
    print("  {} wires created for {}".format(wires_created, wire_prefix))
    return wires_created

def find_closest_chord_vertex_fixed(seaty_coord, chord_vertex_map, tolerance):
    """
    Find the closest chord vertex within tolerance, with tie-breaking.
    """
    
    # Find all chord vertices within tolerance
    candidates = []
    
    for chord_info in chord_vertex_map:
        distance = calculate_distance(seaty_coord, chord_info['coord'])
        
        if distance <= tolerance:
            chord_info_with_distance = chord_info.copy()
            chord_info_with_distance['distance'] = distance
            candidates.append(chord_info_with_distance)
    
    if len(candidates) == 0:
        return None
    
    if len(candidates) == 1:
        return candidates[0]
    
    # Multiple candidates - apply tie-breaking
    # Sort by distance first
    candidates.sort(key=lambda x: x['distance'])
    
    # Get all candidates at minimum distance
    min_distance = candidates[0]['distance']
    closest_candidates = [c for c in candidates if abs(c['distance'] - min_distance) < 0.001]
    
    if len(closest_candidates) == 1:
        return closest_candidates[0]
    
    # Tie-breaking: prefer lower vertex ID, then lexicographically smaller instance name
    def tie_breaker_key(candidate):
        return (candidate['vertex_id'], candidate['instance_name'])
    
    closest_candidates.sort(key=tie_breaker_key)
    return closest_candidates[0]

def calculate_distance(point1, point2):
    """Calculate 3D distance between two points."""
    return math.sqrt(sum([(point1[i] - point2[i])**2 for i in range(3)]))

def create_assembly_wire_fixed(assembly, wire_name, vertex1, vertex2):
    """
    Create assembly-level wire between two vertices from different instances.
    """
    
    try:
        # Check if wire already exists
        if wire_name in assembly.features:
            return True
        
        # Create wire using vertex references (not coordinates)
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
        # Fallback: try with coordinates if vertex reference fails
        try:
            coord1 = vertex1.pointOn[0]
            coord2 = vertex2.pointOn[0]
            
            wire_feature = assembly.WirePolyLine(
                mergeType=IMPRINT,
                meshable=False,
                points=(coord1, coord2)
            )
            
            old_name = wire_feature.name
            assembly.features.changeKey(old_name, wire_name)
            
            return True
            
        except Exception as e2:
            print("        Error creating wire {}: {} (fallback also failed: {})".format(wire_name, e, e2))
            return False

def cleanup_existing_wires(assembly):
    """Remove existing SeatY-chord wires."""
    
    wires_to_remove = []
    for feature_name in assembly.features.keys():
        if feature_name.startswith('seatYtoCL_') or feature_name.startswith('seatYtoCU_'):
            wires_to_remove.append(feature_name)
    
    if len(wires_to_remove) > 0:
        print("Removing {} existing SeatY-chord wires...".format(len(wires_to_remove)))
        for wire_name in wires_to_remove:
            try:
                del assembly.features[wire_name]
            except:
                pass

def verify_seaty_vertices():
    """
    Debug function to verify SeatY vertex structure.
    """
    
    print("\n=== SEATY VERTEX VERIFICATION ===")
    
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    # Find first SeatY instance
    seaty_instance = None
    for inst_name, inst in assembly.instances.items():
        if inst_name.startswith('SeatY_'):
            seaty_instance = (inst_name, inst)
            break
    
    if seaty_instance is None:
        print("No SeatY instance found for verification")
        return
    
    inst_name, inst = seaty_instance
    print("Analyzing SeatY instance: {}".format(inst_name))
    print("Total vertices: {}".format(len(inst.vertices)))
    
    # Show all vertices
    for i, vertex in enumerate(inst.vertices):
        try:
            coord = vertex.pointOn[0]
            marker = ""
            if i in [2, 8]:
                marker = " <- ChordUpper connection"
            elif i in [3, 11]:
                marker = " <- ChordLower connection"
            
            print("  Vertex {}: ({:.3f}, {:.3f}, {:.3f}){}".format(
                i, coord[0], coord[1], coord[2], marker))
        except Exception as e:
            print("  Vertex {}: Error - {}".format(i, e))

# Main execution
if __name__ == "__main__":
    try:
        # Optional: verify vertex structure first
        verify_seaty_vertices()
        
        # Create the connection wires
        success = create_seaty_chord_connection_wires_fixed()
        
        if success:
            print("\n=== SUCCESS ===")
            print("SeatY-Chord connection wires created successfully")
            print("NEXT STEPS:")
            print("1. In Abaqus GUI, select wires named 'seatYtoCU_*'")
            print("2. Apply appropriate connector sections for ChordUpper connections")
            print("3. Select wires named 'seatYtoCL_*'")
            print("4. Apply appropriate connector sections for ChordLower connections")
        else:
            print("\n=== FAILED ===")
            print("Failed to create connection wires")
            print("Check the vertex verification output above")
        
    except Exception as e:
        print("Error in main execution: {}".format(e))
        import traceback
        traceback.print_exc()