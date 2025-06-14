# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import math

def create_seath_seaty_coincident_connections():
    """
    ROBUST: Create connection wires between SeatH and SeatY instances by finding coincident points.
    
    Connection types determined automatically:
    1. SeatH-front: SeatH_x#_y#_z# <-> SeatY_x#_y#_z# (same indices)
    2. SeatH-back: SeatH_x#_y#_z# <-> SeatY_x#_y(#+1)_z# (SeatY y-index +1)
    
    Tolerance: 0.01 units for coincident points
    """
    
    print("SEATH TO SEATY COINCIDENT CONNECTIONS - ROBUST")
    print("=" * 60)
    print("Automatic coincident point detection (tolerance: 0.01)")
    print("SeatH-front: same indices, SeatH-back: SeatY y+1")
    print("=" * 60)
    
    # Get model and assembly
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    # Find all SeatH and SeatY instances
    seath_instances = find_instances_by_pattern(assembly, "SeatH_")
    seaty_instances = find_instances_by_pattern(assembly, "SeatY_")
    
    print("Found {} SeatH instances".format(len(seath_instances)))
    print("Found {} SeatY instances".format(len(seaty_instances)))
    
    if len(seath_instances) == 0 or len(seaty_instances) == 0:
        print("ERROR: No SeatH or SeatY instances found")
        return False
    
    # Create index maps for quick lookup
    seaty_index_map = create_instance_index_map(seaty_instances)
    
    # Clean up existing wires
    cleanup_existing_seath_seaty_wires(assembly)
    
    # Create coincident connections - FRONT FIRST, THEN BACK
    print("\nSearching for coincident points...")
    
    print("\nCreating SeatH-front connections (same indices)...")
    front_wires = create_front_connections(assembly, seath_instances, seaty_index_map)
    
    print("\nCreating SeatH-back connections (SeatY y+1)...")
    back_wires = create_back_connections(assembly, seath_instances, seaty_index_map)
    
    total_wires = front_wires + back_wires
    
    # Summary
    print("\n=== SUMMARY ===")
    print("SeatH-front wires created: {}".format(front_wires))
    print("SeatH-back wires created: {}".format(back_wires))
    print("Total coincident connection wires created: {}".format(total_wires))
    
    return total_wires > 0

def find_instances_by_pattern(assembly, pattern):
    """Find instances that match a name pattern."""
    instances = []
    for inst_name, inst in assembly.instances.items():
        if pattern in inst_name:
            instances.append((inst_name, inst))
    return instances

def create_instance_index_map(instances):
    """Create a map from (x,y,z) indices to instance for quick lookup."""
    index_map = {}
    
    for inst_name, inst in instances:
        indices = parse_instance_indices(inst_name)
        if indices is not None:
            index_map[indices] = (inst_name, inst)
    
    return index_map

def parse_instance_indices(instance_name):
    """Parse instance name to extract (x, y, z) indices."""
    try:
        # Parse name like "SeatH_x0_y15_z0"
        parts = instance_name.split('_')
        if len(parts) >= 4:
            x_idx = int(parts[1][1:])  # Remove 'x'
            y_idx = int(parts[2][1:])  # Remove 'y'
            z_idx = int(parts[3][1:])  # Remove 'z'
            return (x_idx, y_idx, z_idx)
    except:
        pass
    return None

def create_front_connections(assembly, seath_instances, seaty_index_map):
    """
    Create SeatH-front connections by finding coincident points (same indices).
    """
    
    tolerance = 0.01
    front_wires = 0
    
    print("  Processing all SeatH-front connections...")
    
    for i, (seath_name, seath_inst) in enumerate(seath_instances):
        
        if i < 3:
            print("    SeatH-front {}: {}".format(i+1, seath_name))
        elif i == 3:
            print("    ... processing remaining {} instances ...".format(len(seath_instances) - 3))
        
        try:
            # Parse SeatH instance indices
            seath_indices = parse_instance_indices(seath_name)
            if seath_indices is None:
                continue
            
            x_idx, y_idx, z_idx = seath_indices
            
            # Find front SeatY instance (same indices)
            front_seaty = seaty_index_map.get((x_idx, y_idx, z_idx))
            
            if front_seaty is None:
                if i < 3:
                    print("      No matching SeatY found for indices ({},{},{})".format(x_idx, y_idx, z_idx))
                continue
            
            # Get all SeatH vertices
            seath_vertices = []
            try:
                for v_id, vertex in enumerate(seath_inst.vertices):
                    coord = vertex.pointOn[0]
                    seath_vertices.append((v_id, vertex, coord))
            except Exception as e:
                if i < 3:
                    print("      Error getting SeatH vertices: {}".format(e))
                continue
            
            # Find coincident connections to front SeatY
            seaty_name, seaty_inst = front_seaty
            connections = find_coincident_vertices(
                seath_vertices, seaty_inst, tolerance, "front", i
            )
            
            for seath_vid, seath_vertex, seaty_vid, seaty_vertex, distance in connections:
                wire_name = "SeatH-front_{}_x{}_y{}_z{}_v{}_{}".format(
                    i+1, x_idx, y_idx, z_idx, seath_vid, seaty_vid)
                
                if create_assembly_wire_between_vertices(assembly, wire_name, seath_vertex, seaty_vertex):
                    front_wires += 1
                    
                    if front_wires <= 5:  # Show details for first few
                        print("      Front wire {}: {} v{} -> {} v{} (dist: {:.4f})".format(
                            front_wires, seath_name, seath_vid, seaty_name, seaty_vid, distance))
        
        except Exception as e:
            if i < 3:
                print("      Error processing {}: {}".format(seath_name, e))
            continue
    
    print("  SeatH-front wires created: {}".format(front_wires))
    return front_wires

def create_back_connections(assembly, seath_instances, seaty_index_map):
    """
    Create SeatH-back connections by finding coincident points (SeatY y+1).
    """
    
    tolerance = 0.01
    back_wires = 0
    
    print("  Processing all SeatH-back connections...")
    
    for i, (seath_name, seath_inst) in enumerate(seath_instances):
        
        if i < 3:
            print("    SeatH-back {}: {}".format(i+1, seath_name))
        elif i == 3:
            print("    ... processing remaining {} instances ...".format(len(seath_instances) - 3))
        
        try:
            # Parse SeatH instance indices
            seath_indices = parse_instance_indices(seath_name)
            if seath_indices is None:
                continue
            
            x_idx, y_idx, z_idx = seath_indices
            
            # Find back SeatY instance (y+1)
            back_seaty = seaty_index_map.get((x_idx, y_idx + 1, z_idx))
            
            if back_seaty is None:
                if i < 3:
                    print("      No matching SeatY found for indices ({},{},{})".format(x_idx, y_idx + 1, z_idx))
                continue
            
            # Get all SeatH vertices
            seath_vertices = []
            try:
                for v_id, vertex in enumerate(seath_inst.vertices):
                    coord = vertex.pointOn[0]
                    seath_vertices.append((v_id, vertex, coord))
            except Exception as e:
                if i < 3:
                    print("      Error getting SeatH vertices: {}".format(e))
                continue
            
            # Find coincident connections to back SeatY
            seaty_name, seaty_inst = back_seaty
            connections = find_coincident_vertices(
                seath_vertices, seaty_inst, tolerance, "back", i
            )
            
            for seath_vid, seath_vertex, seaty_vid, seaty_vertex, distance in connections:
                wire_name = "SeatH-back_{}_x{}_y{}_z{}_v{}_{}".format(
                    i+1, x_idx, y_idx, z_idx, seath_vid, seaty_vid)
                
                if create_assembly_wire_between_vertices(assembly, wire_name, seath_vertex, seaty_vertex):
                    back_wires += 1
                    
                    if back_wires <= 5:  # Show details for first few
                        print("      Back wire {}: {} v{} -> {} v{} (dist: {:.4f})".format(
                            back_wires, seath_name, seath_vid, seaty_name, seaty_vid, distance))
        
        except Exception as e:
            if i < 3:
                print("      Error processing {}: {}".format(seath_name, e))
            continue
    
    print("  SeatH-back wires created: {}".format(back_wires))
    return back_wires

def find_coincident_vertices(seath_vertices, seaty_inst, tolerance, connection_type, instance_idx):
    """
    Find coincident vertices between SeatH and SeatY instances.
    Returns list of (seath_vid, seath_vertex, seaty_vid, seaty_vertex, distance).
    """
    
    coincident_connections = []
    
    try:
        # Get all SeatY vertices
        seaty_vertices = []
        for v_id, vertex in enumerate(seaty_inst.vertices):
            coord = vertex.pointOn[0]
            seaty_vertices.append((v_id, vertex, coord))
        
        # Check each SeatH vertex against all SeatY vertices
        for seath_vid, seath_vertex, seath_coord in seath_vertices:
            
            for seaty_vid, seaty_vertex, seaty_coord in seaty_vertices:
                
                # Calculate distance
                distance = calculate_distance(seath_coord, seaty_coord)
                
                if distance <= tolerance:
                    coincident_connections.append((
                        seath_vid, seath_vertex, seaty_vid, seaty_vertex, distance
                    ))
                    
                    # Show coincident points for first few instances
                    if instance_idx < 3 and len(coincident_connections) <= 3:
                        print("      Coincident {}: SeatH v{} ({:.3f},{:.3f},{:.3f}) <-> SeatY v{} ({:.3f},{:.3f},{:.3f}) dist:{:.4f}".format(
                            connection_type, seath_vid, seath_coord[0], seath_coord[1], seath_coord[2],
                            seaty_vid, seaty_coord[0], seaty_coord[1], seaty_coord[2], distance))
        
        if instance_idx < 3:
            print("    Found {} coincident {} connections".format(len(coincident_connections), connection_type))
        
    except Exception as e:
        if instance_idx < 3:
            print("    Error finding coincident vertices: {}".format(e))
    
    return coincident_connections

def calculate_distance(point1, point2):
    """Calculate 3D distance between two points."""
    return math.sqrt(sum([(point1[i] - point2[i])**2 for i in range(3)]))

def create_assembly_wire_between_vertices(assembly, wire_name, vertex1, vertex2):
    """Create assembly-level wire between two vertices."""
    
    try:
        # Check if wire already exists
        if wire_name in assembly.features:
            return True
        
        # Create wire using vertex references
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
        # Fallback: try with coordinates
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
            print("        Error creating wire {}: {}".format(wire_name, e))
            return False

def cleanup_existing_seath_seaty_wires(assembly):
    """Remove existing SeatH-SeatY wires."""
    
    wires_to_remove = []
    for feature_name in assembly.features.keys():
        if (feature_name.startswith('SeatH-front_') or 
            feature_name.startswith('SeatH-back_')):
            wires_to_remove.append(feature_name)
    
    if len(wires_to_remove) > 0:
        print("Removing {} existing SeatH-SeatY wires...".format(len(wires_to_remove)))
        for wire_name in wires_to_remove:
            try:
                del assembly.features[wire_name]
            except:
                pass

def analyze_coincident_structure():
    """
    Debug function to analyze the coincident structure between SeatH and SeatY.
    """
    
    print("\n=== COINCIDENT STRUCTURE ANALYSIS ===")
    
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    # Find sample instances
    seath_sample = None
    seaty_sample1 = None  # Same indices
    seaty_sample2 = None  # y+1 indices
    
    for inst_name, inst in assembly.instances.items():
        if inst_name.startswith('SeatH_') and seath_sample is None:
            seath_sample = (inst_name, inst)
        elif inst_name.startswith('SeatY_') and seaty_sample1 is None:
            seaty_sample1 = (inst_name, inst)
    
    if seath_sample and seaty_sample1:
        # Try to find a SeatY with y+1 indices
        seath_indices = parse_instance_indices(seath_sample[0])
        if seath_indices:
            x_idx, y_idx, z_idx = seath_indices
            target_name = "SeatY_x{}_y{}_z{}".format(x_idx, y_idx + 1, z_idx)
            
            if target_name in assembly.instances:
                seaty_sample2 = (target_name, assembly.instances[target_name])
    
    tolerance = 0.01
    
    # Analyze SeatH structure
    if seath_sample:
        inst_name, inst = seath_sample
        print("Sample SeatH instance: {}".format(inst_name))
        print("  Total vertices: {}".format(len(inst.vertices)))
        
        # Show first few vertices
        for i, vertex in enumerate(inst.vertices):
            if i < 8:
                try:
                    coord = vertex.pointOn[0]
                    print("    Vertex {}: ({:.3f}, {:.3f}, {:.3f})".format(i, coord[0], coord[1], coord[2]))
                except:
                    pass
    
    # Analyze coincident points with front SeatY
    if seath_sample and seaty_sample1:
        print("\nAnalyzing coincident points (SeatH-front):")
        seath_vertices = []
        for v_id, vertex in enumerate(seath_sample[1].vertices):
            coord = vertex.pointOn[0]
            seath_vertices.append((v_id, vertex, coord))
        
        coincident = find_coincident_vertices(seath_vertices, seaty_sample1[1], tolerance, "front", 0)
        print("  Found {} coincident points between {} and {}".format(
            len(coincident), seath_sample[0], seaty_sample1[0]))
    
    # Analyze coincident points with back SeatY
    if seath_sample and seaty_sample2:
        print("\nAnalyzing coincident points (SeatH-back):")
        seath_vertices = []
        for v_id, vertex in enumerate(seath_sample[1].vertices):
            coord = vertex.pointOn[0]
            seath_vertices.append((v_id, vertex, coord))
        
        coincident = find_coincident_vertices(seath_vertices, seaty_sample2[1], tolerance, "back", 0)
        print("  Found {} coincident points between {} and {}".format(
            len(coincident), seath_sample[0], seaty_sample2[0]))

# Main execution
if __name__ == "__main__":
    try:
        # Optional: analyze structure first
        analyze_coincident_structure()
        
        # Create the coincident connections
        success = create_seath_seaty_coincident_connections()
        
        if success:
            print("\n=== SUCCESS ===")
            print("SeatH-SeatY coincident connection wires created successfully")
            print("\nROBUST APPROACH BENEFITS:")
            print("- No hard-coded vertex IDs")
            print("- Automatic coincident point detection")
            print("- Flexible and maintainable")
            print("- Works even if vertex numbering changes")
            print("\nWIRE NAMING CONVENTION:")
            print("- SeatH-front_#_x#_y#_z#_v#_# : Front connections (same indices)")
            print("- SeatH-back_#_x#_y#_z#_v#_#  : Back connections (SeatY y+1)")
            print("\nNEXT STEPS:")
            print("1. Select 'SeatH-front_*' wires for front joint connectors")
            print("2. Select 'SeatH-back_*' wires for back joint connectors")
            print("3. Apply appropriate connector sections in Abaqus GUI")
        else:
            print("\n=== FAILED ===")
            print("Failed to create coincident connection wires")
            print("Check the analysis output above")
        
    except Exception as e:
        print("Error in main execution: {}".format(e))
        import traceback
        traceback.print_exc()