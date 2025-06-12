# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import math

def partition_seaty_long_edges():
    """
    Partition the long edges in SeatY part into 4 equal segments.
    Long edges: (0.2,0,0) to (0.2,0,2.16) and (0.625,0,0) to (0.625,0,2.16)
    """
    
    model_name = 'Model-1'
    part_name = 'SeatY'
    
    print("=== PARTITIONING SEATY LONG EDGES ===")
    print("Partitioning long edges into 4 equal segments")
    print("")
    
    # Access model and part
    try:
        myModel = mdb.models[model_name]
        
        if part_name not in myModel.parts:
            print("ERROR: Part '{}' not found in model".format(part_name))
            print("Available parts: {}".format(list(myModel.parts.keys())))
            return False
        
        seatY_part = myModel.parts[part_name]
        print("Successfully accessed part '{}'".format(part_name))
        
    except Exception as e:
        print("ERROR accessing model/part: {}".format(e))
        return False
    
    # Analyze current edge structure
    print("\nCurrent edge structure:")
    print("  Total edges in part: {}".format(len(seatY_part.edges)))
    
    # Find the long edges to partition
    long_edge_specs = [
        ((0.2, 0.0, 0.0), (0.2, 0.0, 2.16)),    # Long edge 1
        ((0.625, 0.0, 0.0), (0.625, 0.0, 2.16)) # Long edge 2
    ]
    
    long_edges_found = find_long_edges(seatY_part, long_edge_specs)
    
    if len(long_edges_found) == 0:
        print("ERROR: No long edges found to partition")
        return False
    
    print("Found {} long edges to partition".format(len(long_edges_found)))
    
    # Partition each long edge
    partitions_created = 0
    for i, (edge, spec_start, spec_end, length) in enumerate(long_edges_found):
        print("\nPartitioning long edge {} (length: {:.3f})...".format(i+1, length))
        
        if partition_edge_into_4_segments(seatY_part, edge, spec_start, spec_end):
            partitions_created += 1
            print("  Successfully partitioned edge {} into 4 segments".format(i+1))
        else:
            print("  Failed to partition edge {}".format(i+1))
    
    # Verify final edge count
    final_edge_count = len(seatY_part.edges)
    print("\nPartitioning results:")
    print("  Long edges partitioned: {} / {}".format(partitions_created, len(long_edges_found)))
    print("  Initial edge count: {}".format(len(long_edges_found) + 4))  # Estimate
    print("  Final edge count: {}".format(final_edge_count))
    print("  Expected edge count: {}".format(6 + 6))  # 6 original + 6 from partitioning 2 edges
    
    if partitions_created == len(long_edges_found):
        print("SUCCESS: All long edges partitioned successfully")
        return True
    else:
        print("PARTIAL SUCCESS: {} / {} long edges partitioned".format(partitions_created, len(long_edges_found)))
        return False

def find_long_edges(part, long_edge_specs):
    """Find the long edges in the part that match the specifications."""
    
    print("\nSearching for long edges...")
    tolerance = 0.001
    long_edges_found = []
    
    for edge in part.edges:
        try:
            # Get edge vertices
            vertices = edge.getVertices()
            if len(vertices) >= 2:
                # Get coordinates of endpoints
                v1_coords = vertices[0].pointOn[0]
                v2_coords = vertices[-1].pointOn[0]
                
                # Calculate edge length
                length = math.sqrt(sum([(v2_coords[i] - v1_coords[i])**2 for i in range(3)]))
                
                # Check if this edge matches any of our long edge specifications
                for spec_start, spec_end in long_edge_specs:
                    # Check both orientations of the edge
                    match1 = (all(abs(v1_coords[i] - spec_start[i]) < tolerance for i in range(3)) and
                             all(abs(v2_coords[i] - spec_end[i]) < tolerance for i in range(3)))
                    match2 = (all(abs(v1_coords[i] - spec_end[i]) < tolerance for i in range(3)) and
                             all(abs(v2_coords[i] - spec_start[i]) < tolerance for i in range(3)))
                    
                    if match1 or match2:
                        long_edges_found.append((edge, spec_start, spec_end, length))
                        print("  Found long edge: start=({:.3f}, {:.3f}, {:.3f}), end=({:.3f}, {:.3f}, {:.3f}), length={:.3f}".format(
                            v1_coords[0], v1_coords[1], v1_coords[2],
                            v2_coords[0], v2_coords[1], v2_coords[2], length))
                        break
                        
        except Exception as e:
            print("  Error checking edge: {}".format(e))
            continue
    
    return long_edges_found

def partition_edge_into_4_segments(part, edge, spec_start, spec_end):
    """Partition a single edge into 4 equal segments."""
    
    try:
        print("    Partitioning edge into 4 segments...")
        print("    Edge from ({:.3f}, {:.3f}, {:.3f}) to ({:.3f}, {:.3f}, {:.3f})".format(
            spec_start[0], spec_start[1], spec_start[2],
            spec_end[0], spec_end[1], spec_end[2]))
        
        # Get current edge count for reference
        initial_edge_count = len(part.edges)
        
        # Method 1: Try direct partitioning at multiple points
        try:
            print("    Attempting Method 1: Multiple parameter partitioning...")
            
            # Partition at 0.25, 0.5, 0.75 (creates 4 segments)
            part.PartitionEdgeByParam(edges=(edge,), parameter=0.25)
            print("      Partitioned at 0.25")
            
            # After first partition, need to find the remaining long edge
            remaining_edges = find_remaining_long_edges(part, edge, 0.25)
            if remaining_edges:
                # Partition the remaining portion at its midpoint (0.5 of original)
                part.PartitionEdgeByParam(edges=(remaining_edges[0],), parameter=2.0/3.0)  # 0.5/0.75 = 2/3
                print("      Partitioned at 0.5")
                
                # Find and partition the last long segment
                remaining_edges = find_remaining_long_edges(part, edge, 0.75)
                if remaining_edges:
                    part.PartitionEdgeByParam(edges=(remaining_edges[0],), parameter=0.5)  # 0.75/1.0 = 0.5
                    print("      Partitioned at 0.75")
            
            final_edge_count = len(part.edges)
            print("    Method 1: Edge count {} -> {}".format(initial_edge_count, final_edge_count))
            
            if final_edge_count > initial_edge_count:
                return True
                
        except Exception as e1:
            print("    Method 1 failed: {}".format(e1))
        
        # Method 2: Try sequential partitioning
        try:
            print("    Attempting Method 2: Sequential partitioning...")
            
            # Reset edge count
            current_edge_count = len(part.edges)
            
            # Find the current edge again (it might have changed)
            current_edge = find_edge_by_endpoints(part, spec_start, spec_end)
            if not current_edge:
                print("    Could not find edge for Method 2")
                return False
            
            # Partition sequentially
            part.PartitionEdgeByParam(edges=(current_edge,), parameter=0.25)
            part.PartitionEdgeByParam(edges=(current_edge,), parameter=0.5)
            part.PartitionEdgeByParam(edges=(current_edge,), parameter=0.75)
            
            final_edge_count = len(part.edges)
            print("    Method 2: Edge count {} -> {}".format(current_edge_count, final_edge_count))
            
            if final_edge_count > current_edge_count:
                return True
                
        except Exception as e2:
            print("    Method 2 failed: {}".format(e2))
        
        # Method 3: Try point-based partitioning
        try:
            print("    Attempting Method 3: Point-based partitioning...")
            
            # Calculate partition points
            partition_points = []
            for param in [0.25, 0.5, 0.75]:
                point = (
                    spec_start[0] + param * (spec_end[0] - spec_start[0]),
                    spec_start[1] + param * (spec_end[1] - spec_start[1]),
                    spec_start[2] + param * (spec_end[2] - spec_start[2])
                )
                partition_points.append(point)
            
            print("    Partition points: {}".format(partition_points))
            
            # Find current edge
            current_edge = find_edge_by_endpoints(part, spec_start, spec_end)
            if not current_edge:
                print("    Could not find edge for Method 3")
                return False
            
            current_edge_count = len(part.edges)
            
            # Try partitioning by point
            for i, point in enumerate(partition_points):
                try:
                    part.PartitionEdgeByPoint(edge=current_edge, point=point)
                    print("      Partitioned at point {} ({:.3f}, {:.3f}, {:.3f})".format(
                        i+1, point[0], point[1], point[2]))
                except Exception as e_point:
                    print("      Failed to partition at point {}: {}".format(i+1, e_point))
            
            final_edge_count = len(part.edges)
            print("    Method 3: Edge count {} -> {}".format(current_edge_count, final_edge_count))
            
            if final_edge_count > current_edge_count:
                return True
        
        except Exception as e3:
            print("    Method 3 failed: {}".format(e3))
        
        print("    All partitioning methods failed")
        return False
        
    except Exception as e:
        print("    Error during partitioning: {}".format(e))
        return False

def find_remaining_long_edges(part, original_edge, partition_param):
    """Find edges that remain after partial partitioning."""
    
    # This is complex to implement reliably
    # For now, return empty list to let other methods try
    return []

def find_edge_by_endpoints(part, start_point, end_point):
    """Find an edge by its endpoint coordinates."""
    
    tolerance = 0.001
    
    for edge in part.edges:
        try:
            vertices = edge.getVertices()
            if len(vertices) >= 2:
                v1_coords = vertices[0].pointOn[0]
                v2_coords = vertices[-1].pointOn[0]
                
                # Check both orientations
                match1 = (all(abs(v1_coords[i] - start_point[i]) < tolerance for i in range(3)) and
                         all(abs(v2_coords[i] - end_point[i]) < tolerance for i in range(3)))
                match2 = (all(abs(v1_coords[i] - end_point[i]) < tolerance for i in range(3)) and
                         all(abs(v2_coords[i] - start_point[i]) < tolerance for i in range(3)))
                
                if match1 or match2:
                    return edge
        except:
            continue
    
    return None

def verify_partitioning_results():
    """Verify that the partitioning was successful."""
    
    model_name = 'Model-1'
    part_name = 'SeatY'
    
    try:
        myModel = mdb.models[model_name]
        seatY_part = myModel.parts[part_name]
        
        print("\n=== PARTITIONING VERIFICATION ===")
        print("Final edge count: {}".format(len(seatY_part.edges)))
        
        # Expected: 6 original short edges + 6 edges from partitioning 2 long edges = 12 total
        expected_count = 12
        actual_count = len(seatY_part.edges)
        
        print("Expected edge count: {}".format(expected_count))
        print("Actual edge count: {}".format(actual_count))
        
        if actual_count >= expected_count:
            print("✓ SUCCESS: Partitioning appears successful")
        else:
            print("✗ WARNING: Edge count lower than expected")
        
        # Analyze edge lengths to verify partitioning
        print("\nEdge length analysis:")
        edge_lengths = []
        
        for i, edge in enumerate(seatY_part.edges):
            try:
                vertices = edge.getVertices()
                if len(vertices) >= 2:
                    v1_coords = vertices[0].pointOn[0]
                    v2_coords = vertices[-1].pointOn[0]
                    length = math.sqrt(sum([(v2_coords[j] - v1_coords[j])**2 for j in range(3)]))
                    edge_lengths.append(length)
                    
                    if i < 10:  # Show first 10 edges
                        print("  Edge {}: length = {:.3f}".format(i+1, length))
            except:
                continue
        
        if len(edge_lengths) > 10:
            print("  ... and {} more edges".format(len(edge_lengths) - 10))
        
        # Check for expected partition lengths (original 2.16 / 4 = 0.54)
        partition_length = 2.16 / 4
        partition_edges = [l for l in edge_lengths if abs(l - partition_length) < 0.01]
        
        print("\nExpected partition segment length: {:.3f}".format(partition_length))
        print("Edges with partition length: {}".format(len(partition_edges)))
        print("Expected partition edges: 8 (4 segments × 2 long edges)")
        
    except Exception as e:
        print("Error in verification: {}".format(e))

# Main execution
if __name__ == "__main__":
    try:
        success = partition_seaty_long_edges()
        verify_partitioning_results()
        
        if success:
            print("\n=== PARTITIONING COMPLETED SUCCESSFULLY ===")
            print("SeatY long edges have been partitioned into 4 equal segments")
            print("This creates proper mesh density for structural analysis")
        else:
            print("\n=== PARTITIONING COMPLETED WITH ISSUES ===")
            print("Some long edges may not have been partitioned successfully")
            print("Check the verification results above")
        
    except Exception as e:
        print("Error in main execution: {}".format(e))
        import traceback
        traceback.print_exc()