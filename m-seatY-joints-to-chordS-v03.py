# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import math

def create_seaty_chord_joints_one_wire_per_vertex():
    """
    Create wires between SeatY and Chord instances.
    FIXED: Each SeatY vertex connects to exactly ONE chord vertex (the closest one).
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    instances = assembly.instances
    
    print("=== SEATY CHORD JOINTS - ONE WIRE PER VERTEX (FIXED) ===")
    print("Each SeatY vertex will connect to exactly ONE closest chord vertex")
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
    
    # Clean up existing wires first
    cleanup_existing_seaty_wires(assembly)
    
    # Create joints with one-wire-per-vertex logic
    lower_wires = 0
    upper_wires = 0
    
    if len(chord_lower_instances) > 0:
        lower_wires = create_one_wire_per_seaty_vertex(
            assembly, seaty_instances, chord_lower_instances, [4, 5], "seatYtoCL")
    
    if len(chord_upper_instances) > 0:
        upper_wires = create_one_wire_per_seaty_vertex(
            assembly, seaty_instances, chord_upper_instances, [0, 3], "seatYtoCU")
    
    print("")
    print("=== SUMMARY ===")
    print("seatYtoCL wires created: {}".format(lower_wires))
    print("seatYtoCU wires created: {}".format(upper_wires))
    print("Total wires created: {}".format(lower_wires + upper_wires))
    
    # Verify one wire per vertex
    verify_one_wire_per_vertex(assembly, seaty_instances)

def create_one_wire_per_seaty_vertex(assembly, seaty_instances, chord_instances, target_vertices, wire_prefix):
    """Create exactly one wire per SeatY vertex to the closest chord vertex."""
    
    print("Creating {} wires (one per SeatY vertex)...".format(wire_prefix))
    
    tolerance = 0.04
    wires_created = 0
    
    # Build chord vertex map for efficient searching
    chord_vertex_map = []
    for chord_inst in chord_instances:
        try:
            chord_vertices = chord_inst.vertices
            for j, chord_vertex in enumerate(chord_vertices):
                chord_coord = chord_vertex.pointOn[0]
                chord_vertex_map.append({
                    'vertex': chord_vertex,
                    'coord': chord_coord,
                    'instance': chord_inst.name,
                    'vertex_idx': j
                })
        except:
            continue
    
    print("  Built chord vertex map with {} vertices".format(len(chord_vertex_map)))
    
    # Process each SeatY instance
    for seaty_inst in seaty_instances:
        try:
            seaty_vertices = seaty_inst.vertices
            
            if len(seaty_vertices) < max(target_vertices) + 1:
                continue
            
            # Process each target vertex in this SeatY instance
            for vertex_idx in target_vertices:
                seaty_vertex = seaty_vertices[vertex_idx]
                seaty_coord = seaty_vertex.pointOn[0]
                
                # Find the CLOSEST chord vertex within tolerance
                closest_chord = find_closest_chord_vertex_within_tolerance(
                    seaty_coord, chord_vertex_map, tolerance)
                
                if closest_chord:
                    # Create exactly ONE wire to the closest chord vertex
                    wire_name = "{}_{}".format(wire_prefix, wires_created + 1)
                    
                    if create_wire_between_vertices(assembly, seaty_vertex, closest_chord['vertex'], wire_name):
                        wires_created += 1
                        print("    Wire {}: {} vertex {} -> {} vertex {} (dist: {:.4f})".format(
                            wires_created, seaty_inst.name, vertex_idx, 
                            closest_chord['instance'], closest_chord['vertex_idx'], closest_chord['distance']))
        except:
            continue
def find_closest_chord_vertex_within_tolerance(seaty_coord, chord_vertex_map, tolerance):
    """Find the closest chord vertex, with tie-breaking for equidistant vertices."""
    
    # Find all chord vertices within tolerance
    candidates = []
    
    for chord_info in chord_vertex_map:
        chord_coord = chord_info['coord']
        distance = math.sqrt(
            (seaty_coord[0] - chord_coord[0])**2 +
            (seaty_coord[1] - chord_coord[1])**2 +
            (seaty_coord[2] - chord_coord[2])**2
        )
        
        if distance <= tolerance:
            chord_info_with_distance = chord_info.copy()
            chord_info_with_distance['distance'] = distance
            candidates.append(chord_info_with_distance)
    
    if not candidates:
        return None
    
    if len(candidates) == 1:
        return candidates[0]
    
    # Multiple candidates - apply tie-breaking logic
    # Sort by distance first
    candidates.sort(key=lambda x: x['distance'])
    
    closest_distance = candidates[0]['distance']
    closest_candidates = [c for c in candidates if abs(c['distance'] - closest_distance) < 0.001]
    
    if len(closest_candidates) == 1:
        return closest_candidates[0]
    
    # Tie-breaking: multiple chord vertices at same distance (the 48 duplicate problem!)
    # Strategy: Choose the one with lower vertex index, then lower instance name
    print("      TIE-BREAKING: {} equidistant chord vertices (distance {:.4f})".format(
        len(closest_candidates), closest_distance))
    
    for candidate in closest_candidates:
        print("        -> {} vertex {} at ({:.3f}, {:.3f}, {:.3f})".format(
            candidate['instance'], candidate['vertex_idx'], 
            candidate['coord'][0], candidate['coord'][1], candidate['coord'][2]))
    
    # Tie-breaking rules:
    # 1. Prefer lower vertex index
    # 2. If same vertex index, prefer lexicographically smaller instance name
    def tie_breaker_key(candidate):
        return (candidate['vertex_idx'], candidate['instance'])
    
    closest_candidates.sort(key=tie_breaker_key)
    chosen = closest_candidates[0]
    
    print("        CHOSEN: {} vertex {} (tie-breaker applied)".format(
        chosen['instance'], chosen['vertex_idx']))
    
    return chosen

def create_wire_between_vertices(assembly, vertex1, vertex2, wire_name):
    """Create a wire between two vertices."""
    
    try:
        if wire_name in assembly.features:
            return False
        
        wire_feature = assembly.WirePolyLine(
            mergeType=IMPRINT,
            meshable=False,
            points=((vertex1, vertex2),)
        )
        
        old_name = wire_feature.name
        assembly.features.changeKey(old_name, wire_name)
        
        return True
        
    except Exception as e:
        print("      Error creating wire {}: {}".format(wire_name, e))
        return False

def cleanup_existing_seaty_wires(assembly):
    """Remove existing seatY chord wires."""
    
    existing_wires = []
    for feature_name in assembly.features.keys():
        if feature_name.startswith('seatYtoCL_') or feature_name.startswith('seatYtoCU_'):
            existing_wires.append(feature_name)
    
    if len(existing_wires) > 0:
        print("Removing {} existing seatY chord wires...".format(len(existing_wires)))
        for wire_name in existing_wires:
            try:
                del assembly.features[wire_name]
            except:
                pass
        print("Cleanup completed")

def verify_one_wire_per_vertex(assembly, seaty_instances):
    """Verify that each SeatY vertex has exactly one wire."""
    
    print("\n=== VERIFICATION: ONE WIRE PER VERTEX ===")
    
    # Count expected vs actual wires
    total_seaty_instances = len(seaty_instances)
    expected_wires = total_seaty_instances * 4  # 2 vertices × 2 chord types
    
    # Count actual wires
    seatytocl_wires = [name for name in assembly.features.keys() if name.startswith('seatYtoCL_')]
    seatytocu_wires = [name for name in assembly.features.keys() if name.startswith('seatYtoCU_')]
    actual_wires = len(seatytocl_wires) + len(seatytocu_wires)
    
    print("SeatY instances: {}".format(total_seaty_instances))
    print("Expected wires: {} instances × 4 vertices = {}".format(total_seaty_instances, expected_wires))
    print("Actual wires: {} (seatYtoCL: {}, seatYtoCU: {})".format(
        actual_wires, len(seatytocl_wires), len(seatytocu_wires)))
    
    if actual_wires == expected_wires:
        print("✓ SUCCESS: Exactly one wire per SeatY vertex achieved!")
    else:
        difference = actual_wires - expected_wires
        if difference > 0:
            print("✗ ERROR: {} excess wires still exist".format(difference))
        else:
            print("✗ ERROR: {} missing wires".format(-difference))

# Main execution
if __name__ == "__main__":
    try:
        print("SEATY CHORD JOINTS - ONE WIRE PER VERTEX FIX")
        print("=" * 50)
        print("PROBLEM: SeatY vertices equidistant from 2 collinear chord vertices")
        print("SOLUTION: Tie-breaking logic to choose exactly 1 chord vertex")
        print("")
        
        create_seaty_chord_joints_one_wire_per_vertex()
        
        print("")
        print("=== FIXED: ONE WIRE PER SEATY VERTEX ===")
        print("Applied tie-breaking for equidistant chord vertices")
        print("Should eliminate the 48 duplicate wires")
        
    except Exception as e:
        print("Error: {}".format(e))
        import traceback
        traceback.print_exc()