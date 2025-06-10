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
                
                # Create RP at this location - store the feature
                rp_feature = assembly.ReferencePoint(point=lower_end)
                rp = assembly.referencePoints[rp_feature.id]
                
                # Store coordinates for this RP
                rp_coordinates[rp_feature.id] = lower_end
                
                # Create set for this RP
                set_name = "Set_RP_" + inst.name + "_LowerEnd"
                assembly.Set(referencePoints=(rp,), name=set_name)
                
                additional_rps.append(rp)
                
                # Check if this RP is at ground level (y close to 0)
                y_coord = lower_end[1]
                if abs(y_coord) <= tolerance:
                    ground_level_rps_created.append(rp)
                    print("  Created RP and set: " + set_name + " (GROUND LEVEL)")
                else:
                    print("  Created RP and set: " + set_name + " (y = " + str(round(y_coord, 3)) + ")")
                
        except Exception as e:
            print("Error creating RP for " + inst.name + ": " + str(e))
    
    return additional_rps, ground_level_rps_created, rp_coordinates

def find_ground_level_rps(assembly, known_rp_coords):
    """
    Find existing RPs at ground level using findAt() method.
    Focus on locations where we expect ground-level RPs to exist.
    """
    ground_rps = []
    tolerance = 0.1
    
    print("Checking for existing RPs at ground level using findAt method...")
    
    # If we have no new RPs created, just focus on the new ones
    if not known_rp_coords:
        print("No known RP coordinates, skipping existing RP search")
        return ground_rps
    
    # Test some specific ground locations based on the pattern
    # Focus on y=0 locations in a reasonable x,z grid
    test_y_values = [0.0]  # Only check exactly y=0
    
    # Get x,z ranges from our known coordinates  
    x_coords = [coord[0] for coord in known_rp_coords.values()]
    z_coords = [coord[2] for coord in known_rp_coords.values()]
    
    # Test locations in a reasonable grid
    x_range = range(int(min(x_coords) - 200), int(max(x_coords) + 200), 50)
    z_range = range(int(min(z_coords) - 200), int(max(z_coords) + 200), 50)
    
    test_count = 0
    found_count = 0
    
    for x in x_range:
        for z in z_range:
            for y in test_y_values:
                test_coord = (float(x), float(y), float(z))
                test_count += 1
                
                try:
                    # Use findAt to look for RPs at this location
                    rp_at_location = assembly.referencePoints.findAt((test_coord,))
                    
                    if rp_at_location and rp_at_location not in ground_rps:
                        ground_rps.append(rp_at_location)
                        found_count += 1
                        print("  Found existing ground-level RP at " + str(test_coord))
                        
                        if found_count >= 20:  # Reasonable limit
                            print("  ... (found " + str(found_count) + " existing ground RPs, stopping search)")
                            break
                            
                except:
                    # findAt will fail if no RP at that location - this is normal
                    pass
                
                if found_count >= 20:
                    break
            if found_count >= 20:
                break
        if found_count >= 20:
            break
    
    print("Tested " + str(test_count) + " locations, found " + str(len(ground_rps)) + " existing ground-level RPs")
    return ground_rps

def apply_ground_boundary_conditions(model, assembly, ground_rps):
    """
    Apply boundary conditions to pin ground-level RPs.
    Constrain translations (x,y,z = 0), leave rotations free.
    """
    bc_count = 0
    
    if len(ground_rps) == 0:
        print("No ground-level RPs found, skipping boundary conditions")
        return 0
    
    try:
        # Create a set containing all ground-level RPs
        ground_rp_set_name = "Set_Ground_RPs"
        assembly.Set(referencePoints=tuple(ground_rps), name=ground_rp_set_name)
        
        print("Created set containing all ground RPs: " + ground_rp_set_name)
        
        # Apply boundary condition to pin translations
        bc_name = "BC_Ground_Pinned"
        
        # Check if boundary condition already exists
        if bc_name in model.boundaryConditions:
            print("Boundary condition " + bc_name + " already exists, skipping creation")
            return 0
        
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
        print("Error applying boundary conditions: " + str(e))
        
        # Try individual BCs as fallback
        print("Attempting individual boundary conditions as fallback...")
        
        for i, rp in enumerate(ground_rps):
            try:
                # Create individual set for this RP
                individual_set_name = "Set_Ground_RP_" + str(i)
                assembly.Set(referencePoints=(rp,), name=individual_set_name)
                
                # Create individual BC
                individual_bc_name = "BC_Ground_RP_" + str(i)
                
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