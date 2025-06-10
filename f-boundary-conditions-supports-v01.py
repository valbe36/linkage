# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import regionToolset
import math

def apply_ground_boundary_conditions():
    """
    Find ground-level RPs using existing sets and apply boundary conditions:
    - Translations (x,y,z): FIXED
    - Rotations (rx,ry,rz): FREE
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("=== GROUND BOUNDARY CONDITIONS ===")
    print("")
    print("Step 1: Looking for ground-level RPs in existing sets...")
    
    # Find ground-level RPs from existing sets
    ground_rps = find_ground_rps_from_sets(assembly)
    
    if len(ground_rps) == 0:
        print("No ground-level RPs found in sets. Trying alternative approaches...")
        ground_rps = try_alternative_approaches(model, assembly)
    
    if len(ground_rps) == 0:
        print("No ground-level RPs found. Please check if RPs exist and have been properly set up.")
        list_existing_sets_and_bcs(model, assembly)
        return
    
    print("Found " + str(len(ground_rps)) + " ground-level RPs")
    
    print("")
    print("Step 2: Creating set and applying boundary conditions...")
    
    # Apply boundary conditions
    bc_success = create_and_apply_ground_bc(model, assembly, ground_rps)
    
    print("")
    print("=== SUMMARY ===")
    print("Ground-level RPs found: " + str(len(ground_rps)))
    print("Boundary conditions applied: " + ("SUCCESS" if bc_success else "FAILED"))
    print("")
    if bc_success:
        print("Ground support boundary conditions:")
        print("- Translations (u1, u2, u3): FIXED")
        print("- Rotations (ur1, ur2, ur3): FREE")

def find_ground_rps_from_sets(assembly):
    """
    Find ground-level RPs by examining existing sets.
    Looks for coordinate-based and descriptive set names.
    """
    ground_rps = []
    
    print("Scanning existing sets for ground-level RPs...")
    
    all_sets = list(assembly.sets.keys())
    print("Total sets in assembly: " + str(len(all_sets)))
    
    # Method 1: Look for coordinate-based sets (Y=0 or near 0)
    coord_based_sets = []
    for set_name in all_sets:
        if set_name.startswith('RP_X') and '_Y' in set_name and '_Z' in set_name:
            coord_based_sets.append(set_name)
    
    print("Found " + str(len(coord_based_sets)) + " coordinate-based RP sets")
    
    # Check coordinate-based sets for ground level (Y near 0)
    for set_name in coord_based_sets:
        try:
            # Extract Y coordinate from set name like "RP_X331_Y0_Z884"
            y_part = set_name.split('_Y')[1].split('_Z')[0]
            y_value = int(y_part)
            
            # Check if Y coordinate indicates ground level (within ±5 for tolerance)
            if abs(y_value) <= 5:
                rp_set = assembly.sets[set_name]
                if hasattr(rp_set, 'referencePoints') and len(rp_set.referencePoints) > 0:
                    for rp in rp_set.referencePoints:
                        if rp not in ground_rps:
                            ground_rps.append(rp)
                    print("  Found ground RP(s) in set: " + set_name + " (Y=" + str(y_value) + ")")
                
        except (ValueError, IndexError):
            # Skip sets that don't match the expected naming pattern
            continue
    
    # Method 2: Look for descriptive sets mentioning ground/lower/y0
    ground_keywords = ['Ground', 'LowerEnd', '_y0_', 'Y0']
    descriptive_sets = []
    
    for set_name in all_sets:
        for keyword in ground_keywords:
            if keyword in set_name:
                descriptive_sets.append(set_name)
                break
    
    print("Found " + str(len(descriptive_sets)) + " descriptive sets with ground keywords")
    
    # Check descriptive sets
    for set_name in descriptive_sets:
        try:
            rp_set = assembly.sets[set_name]
            if hasattr(rp_set, 'referencePoints') and len(rp_set.referencePoints) > 0:
                for rp in rp_set.referencePoints:
                    if rp not in ground_rps:
                        ground_rps.append(rp)
                print("  Found ground RP(s) in set: " + set_name)
        except:
            print("  Error reading set: " + set_name)
    
    print("Total ground RPs found from sets: " + str(len(ground_rps)))
    return ground_rps

def try_alternative_approaches(model, assembly):
    """
    Alternative approaches to find ground RPs if sets don't work.
    """
    ground_rps = []
    
    print("Trying alternative approaches...")
    
    # Method 1: Check if there's an existing ground boundary condition we can use
    existing_ground_bc = find_existing_ground_bc(model)
    if existing_ground_bc:
        print("Found existing ground BC: " + existing_ground_bc)
        # Try to get RPs from existing BC
        try:
            bc = model.boundaryConditions[existing_ground_bc]
            if hasattr(bc, 'region') and hasattr(bc.region, 'referencePoints'):
                ground_rps = list(bc.region.referencePoints)
                print("Extracted " + str(len(ground_rps)) + " RPs from existing BC")
        except:
            print("Could not extract RPs from existing BC")
    
    # Method 2: Look for sets containing "Ground" regardless of exact name
    if len(ground_rps) == 0:
        for set_name in assembly.sets.keys():
            if 'Ground' in set_name:
                try:
                    rp_set = assembly.sets[set_name]
                    if hasattr(rp_set, 'referencePoints'):
                        for rp in rp_set.referencePoints:
                            if rp not in ground_rps:
                                ground_rps.append(rp)
                        print("Found RPs in ground set: " + set_name)
                except:
                    continue
    
    # Method 3: Manual coordinate specification based on grandstand geometry
    if len(ground_rps) == 0:
        print("Trying manual coordinate specification...")
        ground_rps = find_rps_by_manual_coordinates(assembly)
    
    return ground_rps

def find_existing_ground_bc(model):
    """
    Find existing boundary conditions that might be for ground support.
    """
    ground_bc_keywords = ['Ground', 'Pinned', 'Support', 'Base']
    
    for bc_name in model.boundaryConditions.keys():
        for keyword in ground_bc_keywords:
            if keyword in bc_name:
                return bc_name
    
    return None

def find_rps_by_manual_coordinates(assembly):
    """
    Manually specify coordinates where ground RPs should be based on grandstand geometry.
    """
    ground_rps = []
    
    print("Trying manual coordinate specification...")
    
    # Based on grandstand geometry from script a
    dx = 221
    dz = 221
    n_x = 6
    n_z_base = 5
    
    # Ground level coordinates to check (y=0)
    test_coordinates = []
    
    # Add boundary coordinates at y=0
    for ix in range(n_x + 1):  # 0 to 6
        for iz in [0, n_z_base]:  # Front and back edges
            x_pos = ix * dx
            z_pos = iz * dz
            test_coordinates.append((x_pos, 0.0, z_pos))
    
    # Add side coordinates
    for iz in range(1, n_z_base):  # 1 to 4
        for ix in [0, n_x]:  # Left and right edges
            x_pos = ix * dx
            z_pos = iz * dz
            test_coordinates.append((x_pos, 0.0, z_pos))
    
    print("Testing " + str(len(test_coordinates)) + " manual coordinates...")
    
    # Test each coordinate
    for coord in test_coordinates:
        try:
            rp = assembly.referencePoints.findAt((coord,))
            if rp and rp not in ground_rps:
                ground_rps.append(rp)
                print("  Found RP at manual coordinate: " + str(coord))
        except:
            # No RP at this coordinate
            pass
    
    print("Found " + str(len(ground_rps)) + " RPs using manual coordinates")
    return ground_rps

def create_and_apply_ground_bc(model, assembly, ground_rps):
    """
    Create a set with ground-level RPs and apply boundary conditions.
    """
    if len(ground_rps) == 0:
        return False
    
    try:
        # Create set name
        ground_set_name = "Set_Ground_Support_RPs_New"
        
        # Create new set
        print("Creating set: " + ground_set_name)
        assembly.Set(referencePoints=tuple(ground_rps), name=ground_set_name)
        print("Set created with " + str(len(ground_rps)) + " RPs")
        
        # Create boundary condition name
        bc_name = "BC_Ground_Support_New"
        
        # Apply boundary condition
        print("Applying boundary condition: " + bc_name)
        
        model.DisplacementBC(
            name=bc_name,
            createStepName='Initial',
            region=assembly.sets[ground_set_name],
            u1=SET,    # x-translation = 0 (FIXED)
            u2=SET,    # y-translation = 0 (FIXED)
            u3=SET,    # z-translation = 0 (FIXED)
            ur1=UNSET, # x-rotation = free (FREE)
            ur2=UNSET, # y-rotation = free (FREE)
            ur3=UNSET, # z-rotation = free (FREE)
            amplitude=UNSET,
            distributionType=UNIFORM,
            fieldName='',
            localCsys=None
        )
        
        print("Boundary condition applied successfully!")
        return True
        
    except Exception as e:
        print("Error applying boundary conditions: " + str(e))
        return False

def list_existing_sets_and_bcs(model, assembly):
    """
    List existing sets and boundary conditions for debugging.
    """
    print("")
    print("=== DEBUGGING INFORMATION ===")
    
    # List some sets
    all_sets = list(assembly.sets.keys())
    print("Sample sets in assembly (first 10):")
    for set_name in all_sets[:10]:
        print("  - " + set_name)
    if len(all_sets) > 10:
        print("  ... and " + str(len(all_sets) - 10) + " more sets")
    
    # List boundary conditions
    all_bcs = list(model.boundaryConditions.keys())
    print("Boundary conditions in model:")
    for bc_name in all_bcs:
        print("  - " + bc_name)
    
    # Look for likely ground sets
    print("Sets containing 'ground' keywords:")
    ground_keywords = ['Ground', 'LowerEnd', '_y0_', 'Y0', 'RP_X', 'Lower']
    for set_name in all_sets:
        for keyword in ground_keywords:
            if keyword in set_name:
                print("  - " + set_name)
                break

def verify_ground_boundary_conditions():
    """
    Verify that boundary conditions were created correctly.
    """
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("")
    print("=== VERIFICATION ===")
    
    # Count reference points
    total_rps = len(assembly.referencePoints)
    print("Total reference points in assembly: " + str(total_rps))
    
    # Check for new ground support sets
    new_ground_sets = []
    for set_name in assembly.sets.keys():
        if 'Ground_Support' in set_name and 'New' in set_name:
            new_ground_sets.append(set_name)
    
    print("New ground support sets: " + str(len(new_ground_sets)))
    for set_name in new_ground_sets:
        try:
            rp_set = assembly.sets[set_name]
            rp_count = len(rp_set.referencePoints) if hasattr(rp_set, 'referencePoints') else 0
            print("  - " + set_name + " (" + str(rp_count) + " RPs)")
        except:
            print("  - " + set_name + " (error reading)")
    
    # Check for new boundary conditions
    new_bcs = []
    for bc_name in model.boundaryConditions.keys():
        if 'Ground_Support' in bc_name and 'New' in bc_name:
            new_bcs.append(bc_name)
    
    print("New boundary conditions: " + str(len(new_bcs)))
    for bc_name in new_bcs:
        print("  - " + bc_name)

# Main execution
if __name__ == "__main__":
    try:
        print("Starting ground boundary condition application...")
        print("")
        
        # Apply ground boundary conditions
        apply_ground_boundary_conditions()
        
        # Verify results
        verify_ground_boundary_conditions()
        
        print("")
        print("Ground boundary condition script completed!")
        
    except Exception as e:
        print("Error in main execution: " + str(e))
        import traceback
        traceback.print_exc()