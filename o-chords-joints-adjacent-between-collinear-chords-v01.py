# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import math

def create_chord_endpoint_connections():
    """
    Create wires between coincident endpoints of chord instances.
    - ChordLower instances: connect coincident endpoints together
    - ChordUpper instances: connect coincident endpoints together
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    instances = assembly.instances
    
    print("=== CHORD ENDPOINT CONNECTIONS ===")
    print("Creating wires between coincident chord endpoints")
    print("")
    
    # Find chord instances
    chord_lower_instances = []
    chord_upper_instances = []
    
    for inst_name, inst in instances.items():
        if inst_name.startswith('ChordLower_'):
            chord_lower_instances.append(inst)
        elif inst_name.startswith('ChordUpper_'):
            chord_upper_instances.append(inst)
    
    print("Found {} ChordLower instances".format(len(chord_lower_instances)))
    print("Found {} ChordUpper instances".format(len(chord_upper_instances)))
    print("")
    
    # Clean up existing chord connection wires
    cleanup_existing_chord_wires(assembly)
    
    # Create connections for ChordLower instances
    lower_wires = 0
    if len(chord_lower_instances) > 0:
        lower_wires = create_chord_connections_for_type(
            assembly, chord_lower_instances, "ChordLower", "chordLowerConn")
    
    # Create connections for ChordUpper instances
    upper_wires = 0
    if len(chord_upper_instances) > 0:
        upper_wires = create_chord_connections_for_type(
            assembly, chord_upper_instances, "ChordUpper", "chordUpperConn")
    
    print("")
    print("=== SUMMARY ===")
    print("ChordLower connection wires created: {}".format(lower_wires))
    print("ChordUpper connection wires created: {}".format(upper_wires))
    print("Total chord connection wires: {}".format(lower_wires + upper_wires))

def create_chord_connections_for_type(assembly, chord_instances, chord_type, wire_prefix):
    """Create wires between coincident endpoints for a specific chord type."""
    
    print("Creating {} endpoint connections...".format(chord_type))
    
    tolerance = 0.01  # Tight tolerance for endpoint coincidence
    wires_created = 0
    processed_pairs = set()  # Avoid duplicate connections
    
    # Extract endpoint information from all chord instances
    chord_endpoints = []
    for chord_inst in chord_instances:
        try:
            vertices = chord_inst.vertices
            if len(vertices) >= 2:
                # Get start endpoint (vertex 0)
                start_vertex = vertices[0]
                start_coord = start_vertex.pointOn[0]
                chord_endpoints.append({
                    'instance': chord_inst.name,
                    'vertex': start_vertex,
                    'vertex_idx': 0,
                    'coord': start_coord,
                    'type': 'start'
                })
                
                # Get end endpoint (last vertex)
                end_vertex = vertices[-1]
                end_coord = end_vertex.pointOn[0]
                chord_endpoints.append({
                    'instance': chord_inst.name,
                    'vertex': end_vertex,
                    'vertex_idx': len(vertices) - 1,
                    'coord': end_coord,
                    'type': 'end'
                })
        except Exception as e:
            print("  Error processing {}: {}".format(chord_inst.name, e))
            continue
    
    print("  Found {} chord endpoints to check".format(len(chord_endpoints)))
    
    # Find coincident endpoint pairs
    for i, endpoint1 in enumerate(chord_endpoints):
        for j, endpoint2 in enumerate(chord_endpoints[i+1:], i+1):
            
            # Skip if same instance
            if endpoint1['instance'] == endpoint2['instance']:
                continue
            
            # Calculate distance between endpoints
            coord1 = endpoint1['coord']
            coord2 = endpoint2['coord']
            distance = math.sqrt(
                (coord1[0] - coord2[0])**2 +
                (coord1[1] - coord2[1])**2 +
                (coord1[2] - coord2[2])**2
            )
            
            if distance < tolerance:
                # Found coincident endpoints
                pair_key = tuple(sorted([
                    (endpoint1['instance'], endpoint1['vertex_idx']),
                    (endpoint2['instance'], endpoint2['vertex_idx'])
                ]))
                
                if pair_key not in processed_pairs:
                    processed_pairs.add(pair_key)
                    
                    # Create wire between coincident endpoints
                    wire_name = "{}_{}".format(wire_prefix, wires_created + 1)
                    
                    if create_wire_between_vertices(assembly, endpoint1['vertex'], endpoint2['vertex'], wire_name):
                        wires_created += 1
                        print("    Wire {}: {} {} <-> {} {} (distance: {:.4f})".format(
                            wires_created,
                            endpoint1['instance'], endpoint1['type'],
                            endpoint2['instance'], endpoint2['type'],
                            distance))
                        print("      Coords: ({:.3f}, {:.3f}, {:.3f}) <-> ({:.3f}, {:.3f}, {:.3f})".format(
                            coord1[0], coord1[1], coord1[2],
                            coord2[0], coord2[1], coord2[2]))
    
    print("  Created {} {} connection wires".format(wires_created, chord_type))
    return wires_created

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

def cleanup_existing_chord_wires(assembly):
    """Remove existing chord connection wires."""
    
    existing_wires = []
    for feature_name in assembly.features.keys():
        if (feature_name.startswith('chordLowerConn_') or 
            feature_name.startswith('chordUpperConn_')):
            existing_wires.append(feature_name)
    
    if len(existing_wires) > 0:
        print("Removing {} existing chord connection wires...".format(len(existing_wires)))
        for wire_name in existing_wires:
            try:
                del assembly.features[wire_name]
            except:
                pass
        print("Cleanup completed")
    else:
        print("No existing chord connection wires found")

def analyze_chord_endpoint_pattern():
    """Analyze the chord endpoint pattern to understand the structure."""
    
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    instances = assembly.instances
    
    print("\n=== ANALYZING CHORD ENDPOINT PATTERN ===")
    
    # Analyze ChordLower pattern
    chord_lower_instances = [inst for inst in instances.values() if inst.name.startswith('ChordLower_')]
    
    if len(chord_lower_instances) > 0:
        print("\nChordLower endpoint analysis:")
        analyze_endpoints_for_type(chord_lower_instances[:5], "ChordLower")  # Analyze first 5
    
    # Analyze ChordUpper pattern
    chord_upper_instances = [inst for inst in instances.values() if inst.name.startswith('ChordUpper_')]
    
    if len(chord_upper_instances) > 0:
        print("\nChordUpper endpoint analysis:")
        analyze_endpoints_for_type(chord_upper_instances[:5], "ChordUpper")  # Analyze first 5

def analyze_endpoints_for_type(chord_instances, chord_type):
    """Analyze endpoint positions for a chord type."""
    
    for chord_inst in chord_instances:
        try:
            vertices = chord_inst.vertices
            print("  {}: {} vertices".format(chord_inst.name, len(vertices)))
            
            if len(vertices) >= 2:
                start_coord = vertices[0].pointOn[0]
                end_coord = vertices[-1].pointOn[0]
                
                print("    Start: ({:.3f}, {:.3f}, {:.3f})".format(*start_coord))
                print("    End:   ({:.3f}, {:.3f}, {:.3f})".format(*end_coord))
                
                # Calculate chord length
                length = math.sqrt(sum([(end_coord[i] - start_coord[i])**2 for i in range(3)]))
                print("    Length: {:.3f}".format(length))
                
        except Exception as e:
            print("  Error analyzing {}: {}".format(chord_inst.name, e))

def verify_chord_connections():
    """Verify the created chord connection wires."""
    
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("\n=== VERIFICATION ===")
    
    # Count chord connection wires
    chord_lower_wires = []
    chord_upper_wires = []
    
    for feature_name in assembly.features.keys():
        if feature_name.startswith('chordLowerConn_'):
            chord_lower_wires.append(feature_name)
        elif feature_name.startswith('chordUpperConn_'):
            chord_upper_wires.append(feature_name)
    
    print("ChordLower connection wires:")
    for wire_name in chord_lower_wires[:5]:  # Show first 5
        print("  - {}".format(wire_name))
    if len(chord_lower_wires) > 5:
        print("  ... and {} more".format(len(chord_lower_wires) - 5))
    
    print("\nChordUpper connection wires:")
    for wire_name in chord_upper_wires[:5]:  # Show first 5
        print("  - {}".format(wire_name))
    if len(chord_upper_wires) > 5:
        print("  ... and {} more".format(len(chord_upper_wires) - 5))
    
    print("\nTotal chord connection wires: {}".format(len(chord_lower_wires) + len(chord_upper_wires)))

# Main execution
if __name__ == "__main__":
    try:
        print("CHORD ENDPOINT CONNECTIONS SCRIPT")
        print("=" * 40)
        print("Creates wires between coincident chord endpoints")
        print("to connect adjacent chord segments together")
        print("")
        
        # Analyze chord structure first
        analyze_chord_endpoint_pattern()
        
        print("")
        
        # Create the connections
        create_chord_endpoint_connections()
        
        # Verify results
        verify_chord_connections()
        
        print("")
        print("=== CHORD ENDPOINT CONNECTIONS COMPLETED ===")
        print("Wire naming convention:")
        print("- chordLowerConn_## : Connections between ChordLower endpoints")
        print("- chordUpperConn_## : Connections between ChordUpper endpoints")
        print("")
        print("NEXT STEPS:")
        print("1. Review wire locations in Abaqus GUI")
        print("2. Create sets for chord connection wires manually in GUI")
        print("3. Apply appropriate connector sections (rigid or flexible)")
        print("4. These connections create structural continuity between chord segments")
        
    except Exception as e:
        print("Error in main execution: {}".format(e))
        import traceback
        traceback.print_exc()