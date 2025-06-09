# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *
import warnings
import traceback # Import traceback for detailed error messages
import part # Explicitly import part module
import assembly # Explicitly import assembly module
import regionToolset # Explicitly import regionToolset
import mesh # Explicitly import mesh module (used for ElemType)
import section # Explicitly import section module
import connectorBehavior # Potentially needed if defining complex behaviors
import math
import re



def create_direct_revolute_joint(model, assembly, inst1_name, vertex1_idx, 
                                inst2_name, vertex2_idx, joint_name, 
                                rotation_axis='Z', tolerance=0.001):
    """
    Creates a revolute joint directly between two vertices of beam instances
    This is the simplest and most reliable method for your scissor structure
    
    Args:
        model: Abaqus model object
        assembly: Abaqus assembly object
        inst1_name: Name of first instance
        vertex1_idx: Vertex index on first instance
        inst2_name: Name of second instance  
        vertex2_idx: Vertex index on second instance
        joint_name: Unique name for this joint
        rotation_axis: 'X', 'Y', or 'Z' - axis about which rotation is allowed
        tolerance: Distance tolerance for finding nodes
    
    Returns:
        Success boolean
    """
    
    try:
        # 1. Get the instances
        if inst1_name not in assembly.instances:
            raise ValueError(f"Instance {inst1_name} not found")
        if inst2_name not in assembly.instances:
            raise ValueError(f"Instance {inst2_name} not found")
            
        inst1 = assembly.instances[inst1_name]
        inst2 = assembly.instances[inst2_name]
        
        # 2. Get vertex coordinates
        if vertex1_idx >= len(inst1.vertices):
            raise ValueError(f"Vertex index {vertex1_idx} out of range for {inst1_name}")
        if vertex2_idx >= len(inst2.vertices):
            raise ValueError(f"Vertex index {vertex2_idx} out of range for {inst2_name}")
            
        vertex1_coord = inst1.vertices[vertex1_idx].pointOn[0]
        vertex2_coord = inst2.vertices[vertex2_idx].pointOn[0]
        
        # Check if vertices are close enough
        distance = math.sqrt(sum([(vertex1_coord[i] - vertex2_coord[i])**2 for i in range(3)]))
        if distance > tolerance:
            warnings.warn(f"Vertices are {distance:.6f} apart, may need adjustment")
        
        # 3. Create a reference point at the joint location (average of the two points)
        joint_coord = tuple((vertex1_coord[i] + vertex2_coord[i])/2.0 for i in range(3))
        rp_joint = assembly.ReferencePoint(point=joint_coord)
        rp_joint_set = assembly.Set(name=f"RP_{joint_name}", referencePoints=(rp_joint,))
        
        # 4. Find nodes at the vertex locations
        try:
            # Find node at vertex 1
            node1 = assembly.nodes.findAt((vertex1_coord,))
            if not node1:
                # Try to find nearby node
                nearby_nodes1 = []
                for node in assembly.nodes:
                    dist = math.sqrt(sum([(node.coordinates[i] - vertex1_coord[i])**2 for i in range(3)]))
                    if dist < tolerance:
                        nearby_nodes1.append(node)
                if nearby_nodes1:
                    node1 = nearby_nodes1[0]
                else:
                    raise ValueError(f"No node found near vertex {vertex1_idx} of {inst1_name}")
            
            # Find node at vertex 2  
            node2 = assembly.nodes.findAt((vertex2_coord,))
            if not node2:
                nearby_nodes2 = []
                for node in assembly.nodes:
                    dist = math.sqrt(sum([(node.coordinates[i] - vertex2_coord[i])**2 for i in range(3)]))
                    if dist < tolerance:
                        nearby_nodes2.append(node)
                if nearby_nodes2:
                    node2 = nearby_nodes2[0]
                else:
                    raise ValueError(f"No node found near vertex {vertex2_idx} of {inst2_name}")
                    
        except Exception as node_err:
            warnings.warn(f"Error finding nodes: {node_err}")
            warnings.warn("Make sure instances are meshed before creating joints")
            return False
        
        # 5. Create node sets
        node1_set = assembly.Set(name=f"Node1_{joint_name}", nodes=(node1,))
        node2_set = assembly.Set(name=f"Node2_{joint_name}", nodes=(node2,))
        
        # 6. Create coupling constraints to connect nodes to reference point
        # This ensures the nodes move together (translation constraint)
        model.Coupling(
            name=f"Coupling1_{joint_name}",
            controlPoint=rp_joint_set,
            surface=node1_set,
            influenceRadius=WHOLE_SURFACE,
            couplingType=KINEMATIC,
            localCsys=None,
            u1=ON, u2=ON, u3=ON,  # Couple translations
            ur1=OFF, ur2=OFF, ur3=OFF  # Don't couple rotations initially
        )
        
        model.Coupling(
            name=f"Coupling2_{joint_name}",
            controlPoint=rp_joint_set,
            surface=node2_set,
            influenceRadius=WHOLE_SURFACE,
            couplingType=KINEMATIC,
            localCsys=None,
            u1=ON, u2=ON, u3=ON,  # Couple translations
            ur1=OFF, ur2=OFF, ur3=OFF  # Don't couple rotations initially
        )
        
        # 7. Apply rotational constraints to create revolute behavior
        # Allow rotation only about the specified axis
        if rotation_axis.upper() == 'Z':
            constrained_dofs = [4, 5]  # UR1, UR2 (rotations about X, Y)
        elif rotation_axis.upper() == 'Y':
            constrained_dofs = [5, 6]  # UR1, UR3 (rotations about X, Z)
        elif rotation_axis.upper() == 'X':
            constrained_dofs = [5, 6]  # UR2, UR3 (rotations about Y, Z)
        else:
            warnings.warn(f"Invalid rotation axis: {rotation_axis}. Using Z.")
            constrained_dofs = [4, 5]
        
        # Apply boundary conditions to reference point to constrain unwanted rotations
        model.DisplacementBC(
            name=f"BC_{joint_name}",
            createStepName='Initial',
            region=rp_joint_set,
            u1=SET, u2=SET, u3=SET,  # Fix translations (controlled by coupling)
            ur1=SET if 4 in constrained_dofs else UNSET,
            ur2=SET if 5 in constrained_dofs else UNSET,
            ur3=SET if 6 in constrained_dofs else UNSET,
            amplitude=UNSET
        )
        
        print(f"Successfully created direct revolute joint: {joint_name}")
        print(f"  - Between {inst1_name}[V{vertex1_idx}] and {inst2_name}[V{vertex2_idx}]")
        print(f"  - Rotation allowed about {rotation_axis} axis")
        print(f"  - Distance between vertices: {distance:.6f}")
        
        return True
        
    except Exception as e:
        warnings.warn(f"Failed to create direct revolute joint {joint_name}: {e}")
        print(traceback.format_exc())
        return False

def create_revolute_joints_for_scissor_pairs(model, assembly, instance_keys, rotation_axis='Z'):
    """
    Creates revolute joints for all scissor pairs in your structure
    Adapted for your specific naming convention
    
    Args:
        model: Abaqus model object
        assembly: Abaqus assembly object
        instance_keys: List of instance names from your main script
        rotation_axis: Axis about which rotation is allowed
    
    Returns:
        Number of joints created successfully
    """
    
    joints_created = 0
    joint_errors = 0
    
    print(f"\nCreating revolute joints for scissor pairs...")
    
    # Process X-direction pairs (BarX-a with BarX-b)
    for inst_name in instance_keys:
        if inst_name.startswith("BarX-a_"):
            # Find corresponding BarX-b instance
            indices_part = inst_name.split("BarX-a_", 1)[1]
            partner_name = f"BarX-b_{indices_part}"
            
            if partner_name in assembly.instances:
                joint_name = f"RevoluteX_{indices_part.replace('_', '')}"
                
                # Create joint at vertex 2 (middle vertex after partitioning)
                success = create_direct_revolute_joint(
                    model=model,
                    assembly=assembly,
                    inst1_name=inst_name,
                    vertex1_idx=2,  # Middle vertex
                    inst2_name=partner_name,
                    vertex2_idx=2,  # Middle vertex
                    joint_name=joint_name,
                    rotation_axis=rotation_axis
                )
                
                if success:
                    joints_created += 1
                else:
                    joint_errors += 1
    
    # Process Y-direction pairs (BarY-a with BarY-b)  
    for inst_name in instance_keys:
        if inst_name.startswith("BarY-a_"):
            # Find corresponding BarY-b instance
            indices_part = inst_name.split("BarY-a_", 1)[1]
            partner_name = f"BarY-b_{indices_part}"
            
            if partner_name in assembly.instances:
                joint_name = f"RevoluteY_{indices_part.replace('_', '')}"
                
                # Create joint at vertex 2 (middle vertex after partitioning)
                success = create_direct_revolute_joint(
                    model=model,
                    assembly=assembly,
                    inst1_name=inst_name,
                    vertex1_idx=2,  # Middle vertex
                    inst2_name=partner_name,
                    vertex2_idx=2,  # Middle vertex
                    joint_name=joint_name,
                    rotation_axis=rotation_axis
                )
                
                if success:
                    joints_created += 1
                else:
                    joint_errors += 1
    
    print(f"Revolute joint creation completed:")
    print(f"  - Joints created successfully: {joints_created}")
    print(f"  - Errors encountered: {joint_errors}")
    
    return joints_created

# Usage example (add this to the end of your main script):
# Make sure instances are meshed before creating joints
# joints_created = create_revolute_joints_for_scissor_pairs(myModel, a, instance_keys, 'Z')