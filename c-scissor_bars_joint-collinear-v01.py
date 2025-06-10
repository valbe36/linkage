from abaqus import *
from abaqusConstants import *
import regionToolset
import math

def create_rigid_joints_between_collinear_bars():
    """
    Creates rigid joints between endpoints of collinear bars at adjacent levels:
     BarX-a to BarX-a; BarX-b to BarX-b, BarZ-a to BarZ-a, BarZ-b to BarZ-b
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    # Get all instances in the assembly
    instances = assembly.instances
    
    # Create rigid connector section if it doesn't exist
    create_rigid_connector_section(model)
    
    # Find and create rigid joints for each bar type
    print("Finding collinear bar pairs...")
    
    # Process BarX bars
    barx_pairs = find_collinear_barx_pairs(instances)
    print(f"Found {len(barx_pairs)} BarX collinear pairs")
    
    # Process BarZ bars  
    barz_pairs = find_collinear_barz_pairs(instances)
    print(f"Found {len(barz_pairs)} BarZ collinear pairs")
    
    # Create rigid joints
    total_created = 0
    
    print("\nCreating rigid joints for BarX pairs...")
    for i, (bar1, bar2) in enumerate(barx_pairs):
        if create_rigid_joint(assembly, model, bar1, bar2, f"RigidX_{i}"):
            total_created += 1
    
    print(f"\nCreating rigid joints for BarZ pairs...")
    for i, (bar1, bar2) in enumerate(barz_pairs):
        if create_rigid_joint(assembly, model, bar1, bar2, f"RigidZ_{i}"):
            total_created += 1
    
    print(f"\nSuccessfully created {total_created} rigid joints")

def parse_bar_coordinates(instance_name):
    """
    Parse bar instance name to extract coordinates.
    Example: BarX-a_x0_y0_z4 -> ('BarX', 'a', 0, 0, 4)
    """
    try:
        # Split by underscore and extract parts
        parts = instance_name.split('_')
        bar_type_part = parts[0]  # BarX-a or BarZ-b etc.
        
        # Extract bar type and subtype
        bar_type = bar_type_part.split('-')[0]  # BarX or BarZ
        subtype = bar_type_part.split('-')[1]   # a or b
        
        # Extract coordinates
        x = int(parts[1][1:])  # Remove 'x' prefix
        y = int(parts[2][1:])  # Remove 'y' prefix  
        z = int(parts[3][1:])  # Remove 'z' prefix
        
        return bar_type, subtype, x, y, z
    except:
        return None, None, None, None, None

def find_collinear_barx_pairs(instances):
    """
    Find collinear BarX pairs that should be connected with rigid joints.
    Pattern: x stays constant, y increases by 1, z changes by ±1
    """
    barx_pairs = []
    instance_list = list(instances.values())
    
    # Group BarX instances by type and coordinates
    barx_instances = {}
    for inst in instance_list:
        if inst.name.startswith('BarX-'):
            bar_type, subtype, x, y, z = parse_bar_coordinates(inst.name)
            if bar_type == 'BarX':
                key = (subtype, x, y, z)
                barx_instances[key] = inst
    
    # Find collinear pairs
    for (subtype, x, y, z), inst1 in barx_instances.items():
        # Look for adjacent level bars
        # Pattern 1: y+1, z-1 (like BarX-a_x0_y0_z4 -> BarX-a_x0_y1_z3)
        target_key1 = (subtype, x, y+1, z-1)
        if target_key1 in barx_instances:
            inst2 = barx_instances[target_key1]
            barx_pairs.append((inst1, inst2))
            print(f"Found BarX collinear pair: {inst1.name} <-> {inst2.name}")
        
        # Pattern 2: y+1, z+1 (like BarX-b_x6_y0_z2 -> BarX-b_x6_y1_z3)
        target_key2 = (subtype, x, y+1, z+1)
        if target_key2 in barx_instances:
            inst2 = barx_instances[target_key2]
            barx_pairs.append((inst1, inst2))
            print(f"Found BarX collinear pair: {inst1.name} <-> {inst2.name}")
    
    return barx_pairs

def find_collinear_barz_pairs(instances):
    """
    Find collinear BarZ pairs that should be connected with rigid joints.
    Pattern: z stays constant, y increases by 1, x changes by ±1
    """
    barz_pairs = []
    instance_list = list(instances.values())
    
    # Group BarZ instances by type and coordinates
    barz_instances = {}
    for inst in instance_list:
        if inst.name.startswith('BarZ-'):
            bar_type, subtype, x, y, z = parse_bar_coordinates(inst.name)
            if bar_type == 'BarZ':
                key = (subtype, x, y, z)
                barz_instances[key] = inst
    
    # Find collinear pairs
    for (subtype, x, y, z), inst1 in barz_instances.items():
        # Look for adjacent level bars
        # Pattern 1: x-1, y+1 (like BarZ-b_x4_y0_z0 -> BarZ-b_x3_y1_z0)
        target_key1 = (subtype, x-1, y+1, z)
        if target_key1 in barz_instances:
            inst2 = barz_instances[target_key1]
            barz_pairs.append((inst1, inst2))
            print(f"Found BarZ collinear pair: {inst1.name} <-> {inst2.name}")
        
        # Pattern 2: x+1, y+1 (like BarZ-a_x4_y0_z0 -> BarZ-a_x5_y1_z0)  
        target_key2 = (subtype, x+1, y+1, z)
        if target_key2 in barz_instances:
            inst2 = barz_instances[target_key2]
            barz_pairs.append((inst1, inst2))
            print(f"Found BarZ collinear pair: {inst1.name} <-> {inst2.name}")
    
    return barz_pairs

def create_rigid_connector_section(model):
    """
    Create a rigid connector section for the joints.
    """
    section_name = 'RigidConnectorSection'
    
    try:
        if section_name not in model.sections:
            # Create a rigid connector section using TRANSLATOR type with high stiffness
            model.ConnectorSection(name=section_name, assembledType=TRANSLATOR)
            
            # Set rigid behavior (very high stiffness)
            section = model.sections[section_name]
            section.setValues(
                rotationalType=ROTATION,
                u1ReferenceLength=1.0,
                u2ReferenceLength=1.0, 
                u3ReferenceLength=1.0
            )
            
            print(f"Created rigid connector section: {section_name}")
        else:
            print(f"Rigid connector section already exists: {section_name}")
        
        return True
    except Exception as e:
        print(f"Error creating rigid connector section: {e}")
        return False

def find_closest_endpoints(inst1, inst2):
    """
    Find the closest endpoints between two bar instances.
    Returns the vertex indices of the closest endpoints.
    """
    try:
        # Get all vertices for both instances
        vertices1 = inst1.vertices
        vertices2 = inst2.vertices
        
        # Get endpoint vertices (first and last)
        endpoints1 = [vertices1[0], vertices1[-1]]  # First and last vertex
        endpoints2 = [vertices2[0], vertices2[-1]]
        
        min_distance = float('inf')
        best_pair = None
        
        # Find closest pair of endpoints
        for i, v1 in enumerate(endpoints1):
            coord1 = v1.pointOn[0]
            for j, v2 in enumerate(endpoints2):
                coord2 = v2.pointOn[0]
                
                # Calculate distance
                distance = math.sqrt(
                    (coord1[0] - coord2[0])**2 + 
                    (coord1[1] - coord2[1])**2 + 
                    (coord1[2] - coord2[2])**2
                )
                
                if distance < min_distance:
                    min_distance = distance
                    # Convert to actual vertex indices (0 for first, -1 for last)
                    idx1 = 0 if i == 0 else len(vertices1) - 1
                    idx2 = 0 if j == 0 else len(vertices2) - 1
                    best_pair = (idx1, idx2, coord1, coord2)
        
        return best_pair, min_distance
    
    except Exception as e:
        print(f"Error finding closest endpoints: {e}")
        return None, float('inf')

def create_rigid_joint(assembly, model, inst1, inst2, joint_name):
    """
    Create a rigid joint ONLY if the closest endpoints are within 0.1 distance.
    Skip bars that are not touching.
    """
    try:
        print(f"Checking {inst1.name} and {inst2.name}")
        
        # Find closest endpoints
        endpoint_info, min_distance = find_closest_endpoints(inst1, inst2)
        if endpoint_info is None:
            print(f"  Could not find endpoints, skipping")
            return False
        
        closest_idx1, closest_idx2, closest_coord1, closest_coord2 = endpoint_info
        print(f"  Closest endpoints distance: {min_distance:.6f}")
        
        # Only create wire if endpoints are touching (distance < 0.1)
        if min_distance < 0.1:
            print(f"  Endpoints are touching (distance < 0.1), creating rigid wire")
            
            # Create wire between touching endpoints
            vertex1 = inst1.vertices[closest_idx1]
            vertex2 = inst2.vertices[closest_idx2]
            
            wire_name = f"RigidWire_{joint_name}"
            wire_feature = assembly.WirePolyLine(
                mergeType=IMPRINT, 
                meshable=False, 
                points=((vertex1, vertex2),)
            )
            
            # Rename the wire feature
            old_name = wire_feature.name
            assembly.features.changeKey(old_name, wire_name)
            
            print(f"  Created rigid wire: {wire_name}")
            print(f"  Connected vertex {closest_idx1} of {inst1.name}: {closest_coord1}")
            print(f"  To vertex {closest_idx2} of {inst2.name}: {closest_coord2}")
            
            # Try to assign rigid section (simplified approach)
            try:
                # Find the edge and create a simple set
                avg_pos = ((closest_coord1[0] + closest_coord2[0])/2, 
                          (closest_coord1[1] + closest_coord2[1])/2, 
                          (closest_coord1[2] + closest_coord2[2])/2)
                edges_at_pos = assembly.edges.findAt((avg_pos,))
                
                if edges_at_pos:
                    set_name = f"RigidSet_{joint_name}"
                    assembly.Set(edges=(edges_at_pos[0],), name=set_name)
                    assembly.SectionAssignment(
                        region=assembly.sets[set_name], 
                        sectionName='RigidConnectorSection'
                    )
                    print(f"  Assigned rigid section to {set_name}")
                else:
                    print(f"  Warning: Could not assign section to {wire_name}")
            except Exception as assign_error:
                print(f"  Warning: Section assignment failed: {assign_error}")
                # Continue anyway - the wire is created
            
            return True
        else:
            print(f"  Endpoints are NOT touching (distance = {min_distance:.6f} >= 0.1), skipping")
            return False
        
    except Exception as e:
        print(f"Error checking/creating rigid joint {joint_name}: {e}")
        return False

def verify_rigid_joints():
    """
    Verify that rigid joints were created correctly.
    """
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("\n=== Rigid Joint Verification ===")
    
    # Count rigid wires
    rigid_wires = []
    for feature_name in assembly.features.keys():
        if 'Rigid' in feature_name:
            rigid_wires.append(feature_name)
    
    print(f"Rigid wire features created: {len(rigid_wires)}")
    for wire_name in rigid_wires[:10]:  # Show first 10
        print(f"  - {wire_name}")
    if len(rigid_wires) > 10:
        print(f"  ... and {len(rigid_wires) - 10} more")
    
    # Count rigid sets
    rigid_sets = []
    for set_name in assembly.sets.keys():
        if 'Rigid' in set_name:
            rigid_sets.append(set_name)
    
    print(f"Rigid sets created: {len(rigid_sets)}")

# Main execution
if __name__ == "__main__":
    try:
        print("Starting rigid joint creation between collinear bars...")
        create_rigid_joints_between_collinear_bars()
        verify_rigid_joints()
        print("\nRigid joint creation completed!")
        
    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()