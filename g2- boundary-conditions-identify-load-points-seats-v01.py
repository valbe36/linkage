# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import math

def create_seath_edge_sets_fixed():
    """
    Create SeatSideEdges and SeatInnerEdges sets from SeatH instances.
    - SeatSideEdges: Wire 1 (x=0.0) and Wire 5 (x=2.16) from all instances
    - SeatInnerEdges: Wire 2 (x=0.54), Wire 3 (x=1.08), Wire 4 (x=1.62) from all instances
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("=== CREATING SEATH EDGE SETS - FIXED VERSION ===")
    print("Identifying wires by local x-coordinates within each SeatH instance")
    print("")
    
    # Find all SeatH instances
    seath_instances = []
    for inst_name in assembly.instances.keys():
        if inst_name.startswith('seat-H_'):
            seath_instances.append(assembly.instances[inst_name])
    
    print("Found {} SeatH instances".format(len(seath_instances)))
    
    if len(seath_instances) == 0:
        print("ERROR: No seat-H instances found")
        return False
    
    # Wire positions from SeatH creation (local coordinates)
    # Wire 1: x=0.0, Wire 2: x=0.54, Wire 3: x=1.08, Wire 4: x=1.62, Wire 5: x=2.16
    wire_local_x_positions = [0.0, 0.54, 1.08, 1.62, 2.16]
    
    # Collect edges by wire classification
    side_edges = []      # Wires 1 and 5
    inner_edges = []     # Wires 2, 3, and 4
    
    print("Analyzing SeatH instances...")
    
    for instance in seath_instances:
        try:
            print("  Processing instance: {}".format(instance.name))
            
            # Get instance transformation to understand global coordinates
            instance_origin = get_instance_origin(instance)
            print("    Instance origin: ({:.3f}, {:.3f}, {:.3f})".format(*instance_origin))
            
            # Get all edges from this instance
            edges = instance.edges
            print("    Total edges in instance: {}".format(len(edges)))
            
            # Classify edges by wire number
            wire_edges = {1: [], 2: [], 3: [], 4: [], 5: []}
            
            for edge in edges:
                wire_number = classify_edge_by_wire(edge, instance_origin, wire_local_x_positions)
                if wire_number > 0:
                    wire_edges[wire_number].append(edge)
            
            # Report classification for this instance
            for wire_num in range(1, 6):
                count = len(wire_edges[wire_num])
                if count > 0:
                    print("    Wire {}: {} edges".format(wire_num, count))
            
            # Add to appropriate collections
            side_edges.extend(wire_edges[1])  # Wire 1
            side_edges.extend(wire_edges[5])  # Wire 5
            
            inner_edges.extend(wire_edges[2])  # Wire 2
            inner_edges.extend(wire_edges[3])  # Wire 3
            inner_edges.extend(wire_edges[4])  # Wire 4
            
        except Exception as e:
            print("    Error processing instance {}: {}".format(instance.name, e))
            continue
    
    print("")
    print("Edge classification summary:")
    print("  Side edges (wires 1,5): {}".format(len(side_edges)))
    print("  Inner edges (wires 2,3,4): {}".format(len(inner_edges)))
    
    # Create SeatSideEdges set
    success_side = create_edge_set(assembly, 'SeatSideEdges', side_edges, "side wires (1,5)")
    
    # Create SeatInnerEdges set
    success_inner = create_edge_set(assembly, 'SeatInnerEdges', inner_edges, "inner wires (2,3,4)")
    
    print("")
    if success_side and success_inner:
        print("SUCCESS: Both SeatH edge sets created successfully")
        return True
    else:
        print("ERROR: Some SeatH edge sets failed to create")
        return False

def get_instance_origin(instance):
    """Get the origin/translation of an instance."""
    
    try:
        # Try to get instance transformation
        if hasattr(instance, 'getTranslation'):
            translation = instance.getTranslation()
            return translation
        else:
            # Alternative method: get first vertex position and estimate origin
            if len(instance.vertices) > 0:
                first_vertex = instance.vertices[0]
                vertex_coord = first_vertex.pointOn[0]
                # For SeatH, the first vertex should be close to instance origin
                return vertex_coord
            else:
                return (0.0, 0.0, 0.0)
    except:
        return (0.0, 0.0, 0.0)

def classify_edge_by_wire(edge, instance_origin, wire_x_positions):
    """
    Classify an edge by determining which wire it belongs to.
    Returns wire number (1-5) or 0 if undetermined.
    """
    
    try:
        # Get edge vertices
        vertices = edge.getVertices()
        if len(vertices) < 2:
            return 0
        
        # Get edge coordinates
        v1_coord = vertices[0].pointOn[0]
        v2_coord = vertices[-1].pointOn[0]
        
        # Calculate edge midpoint
        midpoint = (
            (v1_coord[0] + v2_coord[0]) / 2.0,
            (v1_coord[1] + v2_coord[1]) / 2.0,
            (v1_coord[2] + v2_coord[2]) / 2.0
        )
        
        # Calculate local x-coordinate relative to instance origin
        local_x = midpoint[0] - instance_origin[0]
        
        # Find closest wire x-position
        tolerance = 0.2  # Tolerance for x-position matching
        
        for i, wire_x in enumerate(wire_x_positions):
            if abs(local_x - wire_x) < tolerance:
                return i + 1  # Wire numbers are 1-based
        
        # If no match found, try alternative method using edge endpoints
        # Check if both endpoints have similar x-coordinates (indicating a wire along z)
        if abs(v1_coord[0] - v2_coord[0]) < 0.1:  # Edge is mostly along z-direction
            edge_x = v1_coord[0]  # Use actual x-coordinate
            local_x = edge_x - instance_origin[0]
            
            for i, wire_x in enumerate(wire_x_positions):
                if abs(local_x - wire_x) < tolerance:
                    return i + 1
        
        return 0  # Could not classify
        
    except Exception as e:
        return 0

def create_edge_set(assembly, set_name, edges, description):
    """Create an edge set with the given name and edges."""
    
    if len(edges) == 0:
        print("  WARNING: No edges found for {} set".format(set_name))
        return False
    
    try:
        # Remove existing set if it exists
        if set_name in assembly.sets:
            print("  Removing existing {} set".format(set_name))
            del assembly.sets[set_name]
        
        # Create new set
        assembly.Set(edges=tuple(edges), name=set_name)
        print("  SUCCESS: Created {} set with {} edges ({})".format(set_name, len(edges), description))
        return True
        
    except Exception as e:
        print("  ERROR: Failed to create {} set: {}".format(set_name, e))
        return False

def verify_seath_edge_sets():
    """Verify that the SeatH edge sets were created correctly."""
    
    assembly = mdb.models['Model-1'].rootAssembly
    
    print("")
    print("=== VERIFICATION OF SEATH EDGE SETS ===")
    
    # Check both sets
    sets_to_check = ['SeatSideEdges', 'SeatInnerEdges']
    
    for set_name in sets_to_check:
        if set_name in assembly.sets:
            try:
                edge_set = assembly.sets[set_name]
                edge_count = len(edge_set.edges)
                print("SUCCESS {}: {} edges".format(set_name, edge_count))
                
                # Additional verification: check edge distribution
                if edge_count > 0:
                    sample_edges = edge_set.edges[:3]  # Check first 3 edges
                    print("  Sample edge coordinates:")
                    for i, edge in enumerate(sample_edges):
                        try:
                            vertices = edge.getVertices()
                            if len(vertices) >= 2:
                                v1 = vertices[0].pointOn[0]
                                v2 = vertices[-1].pointOn[0]
                                midpoint_x = (v1[0] + v2[0]) / 2.0
                                print("    Edge {}: midpoint x = {:.3f}".format(i+1, midpoint_x))
                        except:
                            continue
                
            except Exception as e:
                print("ERROR {}: Cannot read set - {}".format(set_name, e))
        else:
            print("ERROR {}: Set not found".format(set_name))
    
    print("")
    print("Expected edge distribution:")
    print("- SeatSideEdges: Should contain edges from wires at x=0.0 and x=2.16")
    print("- SeatInnerEdges: Should contain edges from wires at x=0.54, 1.08, 1.62")
    print("")
    print("If edge counts are low, check:")
    print("1. SeatH instances exist and have correct geometry")
    print("2. Wire x-positions match SeatH part definition")
    print("3. Tolerance values in classification function")

def analyze_seath_structure():
    """Analyze SeatH structure to understand edge distribution."""
    
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("")
    print("=== SEATH STRUCTURE ANALYSIS ===")
    
    # Find first SeatH instance for detailed analysis
    first_seath = None
    for inst_name in assembly.instances.keys():
        if inst_name.startswith('SeatH_'):
            first_seath = assembly.instances[inst_name]
            break
    
    if first_seath is None:
        print("No SeatH instances found for analysis")
        return
    
    print("Analyzing first SeatH instance: {}".format(first_seath.name))
    
    # Get instance origin
    origin = get_instance_origin(first_seath)
    print("Instance origin: ({:.3f}, {:.3f}, {:.3f})".format(*origin))
    
    # Analyze all edges
    edges = first_seath.edges
    print("Total edges: {}".format(len(edges)))
    
    # Group edges by x-coordinate
    x_coords = []
    for edge in edges:
        try:
            vertices = edge.getVertices()
            if len(vertices) >= 2:
                v1 = vertices[0].pointOn[0]
                v2 = vertices[-1].pointOn[0]
                midpoint_x = (v1[0] + v2[0]) / 2.0
                local_x = midpoint_x - origin[0]
                x_coords.append(local_x)
        except:
            continue
    
    # Find unique x-coordinates
    unique_x = []
    for x in x_coords:
        is_unique = True
        for existing_x in unique_x:
            if abs(x - existing_x) < 0.1:
                is_unique = False
                break
        if is_unique:
            unique_x.append(x)
    
    unique_x.sort()
    print("Unique local x-coordinates found: {}".format([round(x, 3) for x in unique_x]))
    print("Expected x-coordinates: [0.0, 0.54, 1.08, 1.62, 2.16]")
    
    # Count edges at each x-coordinate
    for x in unique_x:
        count = sum(1 for coord_x in x_coords if abs(coord_x - x) < 0.1)
        print("  x = {:.3f}: {} edges".format(x, count))

# Main execution
if __name__ == "__main__":
    try:
        # First analyze the structure
        analyze_seath_structure()
        
        print("")
        
        # Create the edge sets
        success = create_seath_edge_sets_fixed()
        
        # Verify results
        verify_seath_edge_sets()
        
        if success:
            print("")
            print("=== SEATH EDGE SETS CREATION COMPLETED SUCCESSFULLY ===")
            print("- SeatSideEdges: Contains edges from outer wires (1 and 5)")
            print("- SeatInnerEdges: Contains edges from inner wires (2, 3, and 4)")
        else:
            print("")
            print("=== SEATH EDGE SETS CREATION COMPLETED WITH ERRORS ===")
            print("Check the analysis output above for issues")
        
    except Exception as e:
        print("Error in main execution: {}".format(e))
        import traceback
        traceback.print_exc()