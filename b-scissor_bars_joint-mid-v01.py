from abaqus import *
from abaqusConstants import *
import regionToolset
import math

def create_coordinate_systems(assembly):
    """
    Create coordinate systems for connector orientation.
    """
    try:
        # Create coordinate system for X-axis rotation (BarX joints)
        csys_x_name = 'Connector_X_Rotation_CSYS'
        if csys_x_name not in assembly.datums:
            assembly.DatumCsysByThreePoints(
                name=csys_x_name,
                coordSysType=CARTESIAN,
                origin=(0.0, 0.0, 0.0),
                point1=(1.0, 0.0, 0.0),  # X-axis
                point2=(0.0, 1.0, 0.0)   # Y-axis
            )
            print(f"Created coordinate system: {csys_x_name}")
        
        # Create coordinate system for Z-axis rotation (BarZ joints)
        csys_z_name = 'Connector_Z_Rotation_CSYS'
        if csys_z_name not in assembly.datums:
            assembly.DatumCsysByThreePoints(
                name=csys_z_name,
                coordSysType=CARTESIAN,
                origin=(0.0, 0.0, 0.0),
                point1=(0.0, 0.0, 1.0),  # Z-axis
                point2=(1.0, 0.0, 0.0)   # X-axis
            )
            print(f"Created coordinate system: {csys_z_name}")
            
    except Exception as e:
        print(f"Error creating coordinate systems: {e}")

def create_shared_connector_sections(model):
    """
    Create only 2 shared connector sections - one for each rotation axis.
    """
    try:
        # Create X-axis rotation section
        section_x_name = 'HingeSection_X_Shared'
        if section_x_name not in model.sections:
            model.ConnectorSection(name=section_x_name, assembledType=HINGE)
            print(f"Created shared hinge section: {section_x_name}")
        
        # Create Z-axis rotation section  
        section_z_name = 'HingeSection_Z_Shared'
        if section_z_name not in model.sections:
            model.ConnectorSection(name=section_z_name, assembledType=HINGE)
            print(f"Created shared hinge section: {section_z_name}")
            
    except Exception as e:
        print(f"Error creating shared connector sections: {e}")

def create_revolute_joints():
    """
    Creates hinge connectors (revolute joints) between intersecting bars using vertex 2 (midpoint).
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    # Create coordinate systems for connector orientation
    create_coordinate_systems(assembly)
    
    # Create only 2 shared connector sections (one for each rotation axis)
    create_shared_connector_sections(model)
    
    # Get all instances in the assembly
    instances = assembly.instances
    
    # Find all bar pairs that need joints
    bar_pairs = find_intersecting_bar_pairs(instances)
    
    print(f"Found {len(bar_pairs)} bar pairs for joint creation")
    
    # Create connectors for each bar pair
    success_count = 0
    for i, (bar_a, bar_b, joint_type) in enumerate(bar_pairs):
        try:
            if create_revolute_connector(assembly, model, bar_a, bar_b, joint_type, i):
                success_count += 1
        except Exception as e:
            print(f"Error creating connector for {bar_a.name} - {bar_b.name}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"Successfully created {success_count} out of {len(bar_pairs)} connectors")

def find_intersecting_bar_pairs(instances):
    """
    Find pairs of bars that should be connected with revolute joints.
    Returns list of tuples: (instance_a, instance_b, joint_type)
    """
    bar_pairs = []
    instance_list = list(instances.values())
    
    for inst_a in instance_list:
        if not inst_a.name.startswith(('BarZ-a', 'BarX-a')):
            continue
            
        # Determine the corresponding 'b' bar
        if inst_a.name.startswith('BarZ-a'):
            target_name = inst_a.name.replace('BarZ-a', 'BarZ-b')
            joint_type = 'Z'  # Rotation axis
        elif inst_a.name.startswith('BarX-a'):
            target_name = inst_a.name.replace('BarX-a', 'BarX-b')
            joint_type = 'X'  # Rotation axis
        else:
            continue
            
        # Find the corresponding 'b' instance
        for inst_b in instance_list:
            if inst_b.name == target_name:
                bar_pairs.append((inst_a, inst_b, joint_type))
                break
    
    return bar_pairs

def create_revolute_connector(assembly, model, instance_a, instance_b, joint_type, pair_index):
    """
    Create a revolute connector at the midpoint (vertex 2) of intersecting bars.
    """
    
    try:
        # Get vertex 2 (midpoint) from both instances
        if len(instance_a.vertices) < 3 or len(instance_b.vertices) < 3:
            print(f"Error: Insufficient vertices in {instance_a.name} or {instance_b.name}")
            return False
        
        # Vertex 2 is at index 2 (assuming 0-based indexing, but let's be safe)
        vertex_a = instance_a.vertices[2]  # Vertex 2 (midpoint)
        vertex_b = instance_b.vertices[2]  # Vertex 2 (midpoint)
        
        coord_a = vertex_a.pointOn[0]
        coord_b = vertex_b.pointOn[0]
        
        print(f"Creating connector between {instance_a.name} and {instance_b.name}")
        print(f"Vertex coordinates A: {coord_a}, B: {coord_b}")
        
        # Check if vertices are close (should be for intersecting bars)
        dx = coord_a[0] - coord_b[0]
        dy = coord_a[1] - coord_b[1] 
        dz = coord_a[2] - coord_b[2]
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        if distance > 1.0:  # Tolerance
            print(f"Warning: Vertices are {distance:.3f} units apart")
        
        # Use average position for connector
        connector_pos = ((coord_a[0] + coord_b[0]) / 2.0,
                        (coord_a[1] + coord_b[1]) / 2.0,
                        (coord_a[2] + coord_b[2]) / 2.0)
        
        # Use shared connector section
        if joint_type == 'Z':
            section_name = 'HingeSection_Z_Shared'
        else:  # joint_type == 'X'
            section_name = 'HingeSection_X_Shared'
        
        # Create wire for connector
        wire_name = f"HingeConnector_{pair_index}_{joint_type}"
        if not create_connector_wire(assembly, vertex_a, vertex_b, wire_name):
            return False
        
        # Assign section to wire
        if not assign_section_to_wire(assembly, wire_name, section_name, connector_pos):
            return False
        
        print(f"Successfully created hinge connector: {wire_name}")
        return True
        
    except Exception as e:
        print(f"Error in create_revolute_connector: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_connector_wire(assembly, vertex_a, vertex_b, wire_name):
    """
    Create a wire between two vertices for the connector.
    """
    try:
        # Create wire between the two vertices
        wire_feature = assembly.WirePolyLine(
            mergeType=IMPRINT, 
            meshable=False, 
            points=((vertex_a, vertex_b),)
        )
        
        # Rename the wire feature
        old_name = wire_feature.name
        assembly.features.changeKey(old_name, wire_name)
        
        print(f"Created wire feature: {wire_name}")
        return True
        
    except Exception as e:
        print(f"Error creating wire {wire_name}: {e}")
        return False

def assign_section_to_wire(assembly, wire_name, section_name, position):
    """
    Assign connector section to the wire using featureName method.
    """
    try:
        # Get the wire feature
        if wire_name not in assembly.features:
            print(f"Wire feature {wire_name} not found")
            return False
        
        wire_feature = assembly.features[wire_name]
        
        # Find the specific edge using featureName
        target_edge = None
        
        # Search through all edges to find the one with matching featureName
        for edge in assembly.edges:
            if hasattr(edge, 'featureName') and edge.featureName == wire_feature.name:
                target_edge = edge
                break
        
        if target_edge is None:
            print(f"Could not find edge with featureName {wire_feature.name}")
            # Try fallback method
            try:
                edges_at_pos = assembly.edges.findAt((position,))
                if len(edges_at_pos) > 0:
                    target_edge = edges_at_pos[0]
                    print(f"Using fallback edge at position {position}")
            except:
                print(f"Fallback method also failed for {wire_name}")
                return False
        
        if target_edge is None:
            print(f"No suitable edge found for {wire_name}")
            return False
        
        # Create set for the edge
        set_name = f"ConnectorSet_{wire_name}"
        try:
            assembly.Set(edges=(target_edge,), name=set_name)
        except Exception as e:
            print(f"Error creating set {set_name}: {e}")
            return False
        
        # Assign section to the set
        try:
            assembly.SectionAssignment(
                region=assembly.sets[set_name], 
                sectionName=section_name
            )
            print(f"Assigned section {section_name} to {set_name}")
            return True
            
        except Exception as e:
            print(f"Error assigning section {section_name}: {e}")
            return False
            
    except Exception as e:
        print(f"Error in assign_section_to_wire: {e}")
        return False

def verify_connectors():
    """
    Verify that connectors were created correctly.
    """
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("\n=== Connector Verification ===")
    print(f"Total edges in assembly: {len(assembly.edges)}")
    print(f"Total sets in assembly: {len(assembly.sets)}")
    print(f"Total features in assembly: {len(assembly.features)}")
    print(f"Total datums in assembly: {len(assembly.datums)}")
    
    # Count connector sections
    connector_sections = []
    for name, section in model.sections.items():
        if hasattr(section, 'assembledType'):
            connector_sections.append(name)
    
    print(f"Connector sections created: {len(connector_sections)}")
    for section_name in connector_sections:
        print(f"  - {section_name}")
    
    # List wire features
    wire_features = []
    for feature_name in assembly.features.keys():
        if 'Hinge' in feature_name or 'Connector' in feature_name:
            wire_features.append(feature_name)
    
    print(f"Wire features created: {len(wire_features)}")
    for wire_name in wire_features[:10]:  # Show first 10
        print(f"  - {wire_name}")
    if len(wire_features) > 10:
        print(f"  ... and {len(wire_features) - 10} more")
    
    # List connector sets
    connector_sets = []
    for set_name in assembly.sets.keys():
        if 'Connector' in set_name:
            connector_sets.append(set_name)
    
    print(f"Connector sets created: {len(connector_sets)}")
    for set_name in connector_sets[:10]:  # Show first 10
        print(f"  - {set_name}")
    if len(connector_sets) > 10:
        print(f"  ... and {len(connector_sets) - 10} more")
    
    # List coordinate systems
    csys_names = []
    for datum_name in assembly.datums.keys():
        if 'Connector' in datum_name or 'CSYS' in datum_name:
            csys_names.append(datum_name)
    
    print(f"Coordinate systems created: {len(csys_names)}")
    for csys_name in csys_names:
        print(f"  - {csys_name}")

# Main execution
if __name__ == "__main__":
    try:
        print("Starting hinge connector creation (revolute joints)...")
        print("Creating coordinate systems...")
        print("Creating shared connector sections...")
        create_revolute_joints()
        verify_connectors()
        print("\nHinge connector creation completed!")
        print("Note: Using shared connector sections and coordinate systems for efficiency")
        
    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()