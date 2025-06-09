# -*- coding: utf-8 -*-
# ADD THIS TO THE END OF YOUR a-scissor_bars-v01.py SCRIPT
# AFTER STEP 4 (Meshing) AND BEFORE STEP 9 (Regeneration)
from abaqus import *
from abaqusConstants import *
import warnings
import traceback
import part
import assembly
import regionToolset
import mesh
import section
import connectorBehavior
import math
import re


def create_direct_revolute_joint(model, assembly, inst1_name, vertex1_idx, 
                                inst2_name, vertex2_idx, joint_name, 
                                rotation_axis='Z', tolerance=0.01):
    """
    Creates a revolute joint directly between two vertices of beam instances
    Corrected version - fixes reference point set creation
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
            warnings.warn(f"Vertices are {distance:.6f} apart for joint {joint_name} (tolerance: {tolerance})")
        
        # 3. Create a reference point at the joint location (average of the two points)
        joint_coord = tuple((vertex1_coord[i] + vertex2_coord[i])/2.0 for i in range(3))
        rp_joint_feature = assembly.ReferencePoint(point=joint_coord)
        # Get the actual reference point object from the feature
        rp_joint = assembly.referencePoints[rp_joint_feature.id]
        rp_joint_set = assembly.Set(name=f"RP_{joint_name}", referencePoints=(rp_joint,))
        
        # 4. Find nodes at the vertex locations
        try:
            # Find node at vertex 1
            node1 = None
            try:
                node1 = assembly.nodes.findAt((vertex1_coord,))
            except:
                pass
                
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
            node2 = None
            try:
                node2 = assembly.nodes.findAt((vertex2_coord,))
            except:
                pass
                
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
            warnings.warn(f"Error finding nodes for {joint_name}: {node_err}")
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
        if rotation_axis.upper() == 'X':
            constrained_dofs = [5, 6]  # UR2, UR3 (rotations about Y, Z)
        elif rotation_axis.upper() == 'Y':
            constrained_dofs = [4, 6]  # UR1, UR3 (rotations about X, Z)
        elif rotation_axis.upper() == 'Z':
            constrained_dofs = [4, 5]  # UR1, UR2 (rotations about X, Y)
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
        
        print(f"Successfully created revolute joint: {joint_name}")
        print(f"  - Between {inst1_name}[V{vertex1_idx}] and {inst2_name}[V{vertex2_idx}]")
        print(f"  - Rotation allowed about {rotation_axis} axis")
        print(f"  - Distance between vertices: {distance:.6f}")
        
        return True
        
    except Exception as e:
        warnings.warn(f"Failed to create revolute joint {joint_name}: {e}")
        print(traceback.format_exc())
        return False


def create_revolute_joints_for_scissor_pairs(model, assembly, instance_keys):
    """
    Creates revolute joints for all scissor pairs in your structure
    Adapted for your specific naming convention with correct rotation axes
    """
    
    joints_created = 0
    joint_errors = 0
    
    print(f"\nCreating revolute joints for scissor pairs...")
    print(f"Total instances to process: {len(instance_keys)}")
    
    # Process BarX pairs (BarX-a with BarX-b) - rotate around X-axis
    barx_a_instances = [name for name in instance_keys if name.startswith("BarX-a_")]
    print(f"Found {len(barx_a_instances)} BarX-a instances")
    
    for inst_name in barx_a_instances:
        # Extract coordinates from instance name: BarX-a_x{ix}_y{iy}_z{iz}
        # Find corresponding BarX-b instance
        coords_part = inst_name.replace("BarX-a_", "")  # Gets "x{ix}_y{iy}_z{iz}"
        partner_name = f"BarX-b_{coords_part}"
        
        if partner_name in assembly.instances:
            # Create a clean joint name
            joint_name = f"RevoluteX_{coords_part.replace('x', '').replace('y', '').replace('z', '').replace('_', '')}"
            
            print(f"  Creating BarX joint: {inst_name} <-> {partner_name}")
            
            # Create joint at vertex 2 (middle vertex after partitioning)
            # BarX rotates around X-axis
            success = create_direct_revolute_joint(
                model=model,
                assembly=assembly,
                inst1_name=inst_name,
                vertex1_idx=2,  # Middle vertex
                inst2_name=partner_name,
                vertex2_idx=2,  # Middle vertex
                joint_name=joint_name,
                rotation_axis='X'  # BarX rotates around X-axis
            )
            
            if success:
                joints_created += 1
            else:
                joint_errors += 1
        else:
            warnings.warn(f"Partner instance {partner_name} not found for {inst_name}")
            joint_errors += 1
    
    # Process BarZ pairs (BarZ-a with BarZ-b) - rotate around Z-axis  
    barz_a_instances = [name for name in instance_keys if name.startswith("BarZ-a_")]
    print(f"Found {len(barz_a_instances)} BarZ-a instances")
    
    for inst_name in barz_a_instances:
        # Extract coordinates from instance name: BarZ-a_x{ix}_y{iy}_z{iz}
        # Find corresponding BarZ-b instance
        coords_part = inst_name.replace("BarZ-a_", "")  # Gets "x{ix}_y{iy}_z{iz}"
        partner_name = f"BarZ-b_{coords_part}"
        
        if partner_name in assembly.instances:
            # Create a clean joint name
            joint_name = f"RevoluteZ_{coords_part.replace('x', '').replace('y', '').replace('z', '').replace('_', '')}"
            
            print(f"  Creating BarZ joint: {inst_name} <-> {partner_name}")
            
            # Create joint at vertex 2 (middle vertex after partitioning)
            # BarZ rotates around Z-axis
            success = create_direct_revolute_joint(
                model=model,
                assembly=assembly,
                inst1_name=inst_name,
                vertex1_idx=2,  # Middle vertex
                inst2_name=partner_name,
                vertex2_idx=2,  # Middle vertex
                joint_name=joint_name,
                rotation_axis='Z'  # BarZ rotates around Z-axis
            )
            
            if success:
                joints_created += 1
            else:
                joint_errors += 1
        else:
            warnings.warn(f"Partner instance {partner_name} not found for {inst_name}")
            joint_errors += 1
    
    print(f"\nRevolute joint creation completed:")
    print(f"  - Joints created successfully: {joints_created}")
    print(f"  - Errors encountered: {joint_errors}")
    
    return joints_created


# ====================================================================
# ADD THIS STEP TO YOUR MAIN SCRIPT
# Insert this between Step 4 (Meshing) and Step 9 (Regeneration)
# ====================================================================

print("\n--- Step 8: Create Revolute Joints ---")
try:
    joints_created = create_revolute_joints_for_scissor_pairs(
        model=myModel, 
        assembly=a, 
        instance_keys=instance_keys
    )
    
    if joints_created > 0:
        print(f"Successfully created {joints_created} revolute joints")
    else:
        warnings.warn("No revolute joints were created")
        overall_success = False
        
except Exception as joint_err:
    warnings.warn(f"Error creating revolute joints: {joint_err}")
    print(traceback.format_exc())
    overall_success = False

print("Finished Step 8.")