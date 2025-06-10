# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import regionToolset
import math

def create_boundary_conditions():
    """
    1. Create additional RPs at lower end of BarX-a_x{}_y0_z4 bars
    2. Find all RPs at y=0 (with 0.1 tolerance)
    3. Pin them to ground: x,y,z = 0 (translations fixed), rx,ry,rz = free (rotations)
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    # Get all instances in the assembly
    instances = assembly.instances
    
    print("Creating additional RPs at lower ends of BarX-a_x{}_y0_z4 bars...")
    
    # Create additional RPs at lower ends of specific bars
    additional_rps, new_ground_rps, rp_coordinates = create_additional_rps_at_bar_ends(assembly, instances)
    
    print("Created " + str(len(additional_rps)) + " additional RPs")
    print("Of these, " + str(len(new_ground_rps)) + " are at ground level")
    
    # Debug: List the new ground RPs
    print("New ground-level RPs:")
    for i, rp in enumerate(new_ground_rps):
        rp_id = None
        for rp_id_key, rp_obj in assembly.referencePoints.items():
            if rp_obj is rp:
                rp_id = rp_id_key
                break
        print("  " + str(i) + ": RP ID " + str(rp_id))
    
    
    print("")
    print("Finding existing RPs at ground level (y=0)...")
    
    # Find existing RPs at y=0 using the coordinates we know
    existing_ground_rps = find_ground_level_rps(assembly, rp_coordinates)
    
    print("Found " + str(len(existing_ground_rps)) + " existing RPs at ground level")
    
    # Combine all ground-level RPs - simplified approach
    print("Combining ground-level RPs...")
    print("  New ground RPs: " + str(len(new_ground_rps)))
    print("  Existing ground RPs: " + str(len(existing_ground_rps)))
    
    # Start with new ground RPs (we know these are correct)
    unique_ground_rps = list(new_ground_rps)
    
    # Add existing ground RPs if they're not already in the list
    for existing_rp in existing_ground_rps:
        if existing_rp not in unique_ground_rps:
            unique_ground_rps.append(existing_rp)
    
    print("")
    print("Total unique ground-level RPs: " + str(len(unique_ground_rps)))
    
    print("")
    print("Applying boundary conditions to ground-level RPs...")
    
    # Apply boundary conditions
    bc_count = apply_ground_boundary_conditions(model, assembly, unique_ground_rps)
    
    print("")
    print("Summary:")
    print("  Additional RPs created: " + str(len(additional_rps)))
    print("  New ground-level RPs: " + str(len(new_ground_rps)))
    print("  Existing ground-level RPs: " + str(len(existing_ground_rps)))
    print("  Total ground-level RPs: " + str(len(unique_ground_rps)))
    print("  Boundary conditions applied: " + str(bc_count))

def create_additional_rps_at_bar_ends(assembly, instances):
    """
    Create RPs at the lower end of BarX-a_x{}_y0_z4 bars.
    Returns RPs and their coordinates for ground-level checking.
    """
    additional_rps = []
    ground_level_rps_created = []
    rp_coordinates = {}  # Store RP ID -> coordinates mapping
    tolerance = 0.1
    
    # Find all BarX-a bars at y0_z4
    target_bars = []
    for inst in instances.values():
        if inst.name.startswith('BarX-a_') and '_y0_z4' in inst.name:
            target_bars.append(inst)
    
    print("Found " + str(len(target_bars)) + " BarX-a_x{}_y0_z4 bars")
    
    for inst in target_bars:
        try:
            # Find the lower end (endpoint with smaller y-coordinate)
            vertices = inst.vertices
            if len(vertices) >= 2:
                endpoint1 = vertices[0].pointOn[0]
                endpoint2 = vertices[-1].pointOn[0]
                
                # Choose the endpoint with smaller y-coordinate (lower end)
                if endpoint1[1] <= endpoint2[1]:
                    lower_end = endpoint1
                else:
                    lower_end = endpoint2
                
                print("Creating RP at lower end of " + inst.name + " at " + str(lower_end))
                
                # Create RP at this location - store the feature with coordinate-based naming
                rp_feature = assembly.ReferencePoint(point=lower_end)
                rp = assembly.referencePoints[rp_feature.id]
                
                # Store coordinates for this RP
                rp_coordinates[rp_feature.id] = lower_end
                
                # Create coordinate-based set name for consistency
                x_coord = int(round(lower_end[0]))
                y_coord = int(round(lower_end[1]))
                z_coord = int(round(lower_end[2]))
                coord_set_name = "RP_X" + str(x_coord) + "_Y" + str(y_coord) + "_Z" + str(z_coord)
                
                # Also create the original descriptive set name
                descriptive_set_name = "Set_RP_" + inst.name + "_LowerEnd"
                
                # Create both sets
                assembly.Set(referencePoints=(rp,), name=coord_set_name)
                assembly.Set(referencePoints=(rp,), name=descriptive_set_name)
                
                additional_rps.append(rp)
                
                # Check if this RP is at ground level (y close to 0)
                if abs(y_coord) <= tolerance:
                    ground_level_rps_created.append(rp)
                    print("  Created RP: " + coord_set_name + " and " + descriptive_set_name + " (GROUND LEVEL)")
                else:
                    print("  Created RP: " + coord_set_name + " and " + descriptive_set_name + " (y = " + str(round(y_coord, 3)) + ")")
                
        except Exception as e:
            print("Error creating RP for " + inst.name + ": " + str(e))
    
    return additional_rps, ground_level_rps_created, rp_coordinates

def find_ground_level_rps(assembly, known_rp_coords):
    """
    Find existing RPs at ground level using coordinate-based set names.
    Look for sets with names like RP_X###_Y0_Z### (ground level = Y0).
    """
    ground_rps = []
    tolerance_y = 5  # Allow Y values from -5 to +5 to account for rounding
    
    print("Searching for existing ground-level RPs using coordinate-based set names...")
    
    ground_set_names = []
    for set_name in assembly.sets.keys():
        # Look for coordinate-based RP set names at ground level
        if set_name.startswith('RP_X') and '_Y' in set_name and '_Z' in set_name:
            try:
                # Extract Y coordinate from set name like "RP_X331_Y0_Z884"
                y_part = set_name.split('_Y')[1].split('_Z')[0]
                y_value = int(y_part)
                
                # Check if Y coordinate indicates ground level
                if abs(y_value) <= tolerance_y:
                    ground_set_names.append(set_name)
                    print("  Found ground-level set: " + set_name + " (Y=" + str(y_value) + ")")
                    
            except (ValueError, IndexError):
                # Skip sets that don't match the expected naming pattern
                continue
    
    print("Found " + str(len(ground_set_names)) + " ground-level RP sets")
    
    # Get the actual RP objects from the sets
    for set_name in ground_set_names:
        try:
            rp_set = assembly.sets[set_name]
            if hasattr(rp_set, 'referencePoints') and len(rp_set.referencePoints) > 0:
                rp = rp_set.referencePoints[0]  # Get the RP from the set
                ground_rps.append(rp)
                print("  Added RP from set: " + set_name)
        except Exception as e:
            print("  Error getting RP from set " + set_name + ": " + str(e))
    
    print("Successfully retrieved " + str(len(ground_rps)) + " existing ground-level RPs")
    return ground_rps

def apply_ground_boundary_conditions(model, assembly, ground_rps):
    """
    Apply boundary conditions to pin ground-level RPs.
    Constrain translations (x,y,z = 0), leave rotations free.
    """
    bc_count = 0
    
    print("Applying boundary conditions to " + str(len(ground_rps)) + " ground-level RPs...")
    
    if len(ground_rps) == 0:
        print("No ground-level RPs provided, skipping boundary conditions")
        return 0
    
    try:
        # Create a set containing all ground-level RPs
        ground_rp_set_name = "Set_Ground_RPs"
        
        print("Creating set with " + str(len(ground_rps)) + " RPs...")
        assembly.Set(referencePoints=tuple(ground_rps), name=ground_rp_set_name)
        
        print("Created set containing all ground RPs: " + ground_rp_set_name)
        
        # Apply boundary condition to pin translations
        bc_name = "BC_Ground_Pinned"
        
        # Check if boundary condition already exists
        if bc_name in model.boundaryConditions:
            print("Boundary condition " + bc_name + " already exists, skipping creation")
            return 0
        
        print("Creating boundary condition: " + bc_name)
        
        model.DisplacementBC(
            name=bc_name,
            createStepName='Initial',
            region=assembly.sets[ground_rp_set_name],
            u1=SET,    # x-translation = 0 (fixed)
            u2=SET,    # y-translation = 0 (fixed)
            u3=SET,    # z-translation = 0 (fixed)
            ur1=UNSET, # x-rotation = free
            ur2=UNSET, # y-rotation = free
            ur3=UNSET, # z-rotation = free
            amplitude=UNSET,
            distributionType=UNIFORM,
            fieldName='',
            localCsys=None
        )
        
        print("Applied boundary condition: " + bc_name)
        print("  Translations (u1, u2, u3): FIXED")
        print("  Rotations (ur1, ur2, ur3): FREE")
        
        bc_count = 1
        
    except Exception as e:
        print("Error applying group boundary condition: " + str(e))
        
        # Try individual BCs as fallback
        print("Attempting individual boundary conditions as fallback...")
        
        for i, rp in enumerate(ground_rps):
            try:
                # Create individual set for this RP
                individual_set_name = "Set_Ground_RP_" + str(i)
                assembly.Set(referencePoints=(rp,), name=individual_set_name)
                
                # Create individual BC
                individual_bc_name = "BC_Ground_RP_" + str(i)
                
                print("Creating individual BC: " + individual_bc_name)
                
                model.DisplacementBC(
                    name=individual_bc_name,
                    createStepName='Initial',
                    region=assembly.sets[individual_set_name],
                    u1=SET,    # x-translation = 0
                    u2=SET,    # y-translation = 0  
                    u3=SET,    # z-translation = 0
                    ur1=UNSET, # x-rotation = free
                    ur2=UNSET, # y-rotation = free
                    ur3=UNSET, # z-rotation = free
                    amplitude=UNSET
                )
                
                bc_count += 1
                print("  Applied individual BC: " + individual_bc_name)
                
            except Exception as individual_error:
                print("Error with individual BC " + str(i) + ": " + str(individual_error))
    
    print("Total boundary conditions applied: " + str(bc_count))
    return bc_count

def verify_boundary_conditions():
    """
    Verify that boundary conditions were created correctly.
    """
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("")
    print("=== Boundary Condition Verification ===")
    
    # Count reference points
    total_rps = len(assembly.referencePoints)
    print("Total reference points in assembly: " + str(total_rps))
    
    # Count ground-level sets
    ground_sets = []
    for set_name in assembly.sets.keys():
        if 'Ground' in set_name or 'LowerEnd' in set_name:
            ground_sets.append(set_name)
    
    print("Ground-related sets created: " + str(len(ground_sets)))
    for set_name in ground_sets:
        print("  - " + set_name)
    
    # Count boundary conditions
    boundary_conditions = []
    for bc_name in model.boundaryConditions.keys():
        if 'Ground' in bc_name or 'BC_' in bc_name:
            boundary_conditions.append(bc_name)
    
    print("Boundary conditions created: " + str(len(boundary_conditions)))
    for bc_name in boundary_conditions:
        bc = model.boundaryConditions[bc_name]
        print("  - " + bc_name)
        try:
            # Try to get some info about the BC
            print("    Type: Displacement BC")
            print("    Step: " + str(bc.createStepName))
        except:
            pass

def list_barx_a_y0_z4_bars(instances):
    """
    Helper function to list all BarX-a_x{}_y0_z4 bars for verification.
    """
    target_bars = []
    for inst in instances.values():
        if inst.name.startswith('BarX-a_') and '_y0_z4' in inst.name:
            target_bars.append(inst.name)
    
    print("")
    print("BarX-a_x{}_y0_z4 bars found:")
    for bar_name in sorted(target_bars):
        print("  - " + bar_name)
    
    return target_bars

# Main execution
if __name__ == "__main__":
    try:
        print("Starting boundary condition creation...")
        
        # Optional: List target bars first
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        instances = assembly.instances
        target_bars = list_barx_a_y0_z4_bars(instances)
        
        print("")
        print("Found " + str(len(target_bars)) + " target bars for RP creation")
        
        # Create boundary conditions
        create_boundary_conditions()
        verify_boundary_conditions()
        
        print("")
        print("Boundary condition creation completed!")
        print("")
        print("Note: Ground-level reference points are now pinned (translations fixed, rotations free)")
        
    except Exception as e:
        print("Error in main execution: " + str(e))
        import traceback
        traceback.print_exc()