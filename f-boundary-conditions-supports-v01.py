# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import regionToolset

def apply_ground_boundary_conditions():
    """
    Apply pinned boundary conditions to all RPs at ground level (module y=0).
    Pinned = translations fixed (3 DOFs), rotations free.
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("=== GROUND BOUNDARY CONDITIONS ===")
    print("Applying pinned supports to all ground-level RPs (module y=0)")
    print("")
    
    # Find all ground-level RPs using modular coordinate system
    ground_rps = find_rps_in_module_range(assembly, y_range=(0, 0))
    
    if len(ground_rps) == 0:
        print("ERROR: No ground-level RPs found!")
        print("Make sure scripts D and E have been run with modular RP system.")
        list_available_rp_sets(assembly)
        return False
    
    print("Found {} ground-level RPs".format(len(ground_rps)))
    
    # Create ground supports set
    ground_set_name = "RPs_GroundSupports"
    
    try:
        # Check if set already exists
        if ground_set_name in assembly.sets:
            print("Set '{}' already exists, will replace it".format(ground_set_name))
            del assembly.sets[ground_set_name]
        
        # Create new set
        assembly.Set(referencePoints=tuple(ground_rps), name=ground_set_name)
        print("Created set '{}' with {} RPs".format(ground_set_name, len(ground_rps)))
        
    except Exception as e:
        print("ERROR creating ground RP set: {}".format(e))
        return False
    
    # Apply boundary condition
    bc_name = "BC_Ground_Pinned"
    
    try:
        # Check if BC already exists
        if bc_name in model.boundaryConditions:
            print("Boundary condition '{}' already exists, will replace it".format(bc_name))
            del model.boundaryConditions[bc_name]
        
        # Apply pinned boundary condition
        print("Applying pinned boundary condition: {}".format(bc_name))
        
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
        
        print("")
        print("=== SUCCESS ===")
        print("Applied pinned supports to {} ground-level RPs:".format(len(ground_rps)))
        print("  - Translations (u1, u2, u3): FIXED")
        print("  - Rotations (ur1, ur2, ur3): FREE")
        print("  - Set name: {}".format(ground_set_name))
        print("  - BC name: {}".format(bc_name))
        
        return True
        
    except Exception as e:
        print("ERROR applying boundary condition: {}".format(e))
        return False

def find_rps_in_module_range(assembly, x_range=None, y_range=None, z_range=None):
    """Find RPs within specific module coordinate ranges."""
    
    matching_rps = []
    
    for set_name in assembly.sets.keys():
        if set_name.startswith('RP_x') and '_y' in set_name and '_z' in set_name:
            try:
                parts = set_name.split('_')
                if len(parts) >= 3:
                    mod_x = int(parts[1][1:])  # Remove 'x'
                    mod_y = int(parts[2][1:])  # Remove 'y'
                    mod_z = int(parts[3][1:])  # Remove 'z'
                    
                    # Check ranges
                    x_ok = (x_range is None) or (x_range[0] <= mod_x <= x_range[1])
                    y_ok = (y_range is None) or (y_range[0] <= mod_y <= y_range[1])
                    z_ok = (z_range is None) or (z_range[0] <= mod_z <= z_range[1])
                    
                    if x_ok and y_ok and z_ok:
                        rp_set = assembly.sets[set_name]
                        if hasattr(rp_set, 'referencePoints'):
                            # Each modular set should contain exactly one RP
                            for rp in rp_set.referencePoints:
                                matching_rps.append(rp)
                                print("  Found ground RP in set: {}".format(set_name))
                            
            except (ValueError, IndexError):
                continue
    
    return matching_rps

def list_available_rp_sets(assembly):
    """List available RP sets for debugging."""
    
    print("")
    print("=== DEBUGGING: AVAILABLE RP SETS ===")
    
    # Count modular sets
    modular_sets = [name for name in assembly.sets.keys() 
                   if name.startswith('RP_x') and '_y' in name and '_z' in name]
    
    print("Modular RP sets found: {}".format(len(modular_sets)))
    
    if len(modular_sets) > 0:
        # Group by level
        by_level = {}
        for set_name in modular_sets:
            try:
                mod_y = int(set_name.split('_')[2][1:])  # Extract y coordinate
                if mod_y not in by_level:
                    by_level[mod_y] = []
                by_level[mod_y].append(set_name)
            except:
                continue
        
        print("RPs by level:")
        for level in sorted(by_level.keys()):
            print("  Level {}: {} RPs".format(level, len(by_level[level])))
            if level == 0:  # Show ground level examples
                for set_name in by_level[level][:3]:
                    print("    - {}".format(set_name))
                if len(by_level[level]) > 3:
                    print("    ... and {} more".format(len(by_level[level]) - 3))
    else:
        print("No modular RP sets found!")
        print("Please run scripts D and E with modular RP system first.")
    
    # Show some other sets for reference
    other_sets = [name for name in assembly.sets.keys() 
                 if not (name.startswith('RP_x') and '_y' in name and '_z' in name)]
    
    if len(other_sets) > 0:
        print("")
        print("Other sets in assembly (first 5):")
        for set_name in other_sets[:5]:
            print("  - {}".format(set_name))
        if len(other_sets) > 5:
            print("  ... and {} more".format(len(other_sets) - 5))

def verify_ground_boundary_conditions():
    """Verify that boundary conditions were applied correctly."""
    
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("")
    print("=== VERIFICATION ===")
    
    # Check ground support set
    ground_set_name = "RPs_GroundSupports"
    if ground_set_name in assembly.sets:
        try:
            ground_set = assembly.sets[ground_set_name]
            rp_count = len(ground_set.referencePoints)
            print("Ground support set '{}': {} RPs".format(ground_set_name, rp_count))
        except:
            print("Ground support set '{}': error reading".format(ground_set_name))
    else:
        print("Ground support set '{}' not found!".format(ground_set_name))
    
    # Check boundary condition
    bc_name = "BC_Ground_Pinned"
    if bc_name in model.boundaryConditions:
        try:
            bc = model.boundaryConditions[bc_name]
            print("Boundary condition '{}': applied in step '{}'".format(bc_name, bc.createStepName))
            
            # Try to get region info
            try:
                rp_count = len(bc.region.referencePoints)
                print("  Applied to: {} RPs".format(rp_count))
            except:
                print("  Applied to: (could not count RPs)")
                
        except:
            print("Boundary condition '{}': error reading".format(bc_name))
    else:
        print("Boundary condition '{}' not found!".format(bc_name))
    
    # Show total RPs in assembly
    total_rps = len(assembly.referencePoints)
    print("Total RPs in assembly: {}".format(total_rps))

def show_ground_rp_details():
    """Show details of ground-level RPs for verification."""
    
    assembly = mdb.models['Model-1'].rootAssembly
    
    print("")
    print("=== GROUND RP DETAILS ===")
    
    # Find ground-level RP sets
    ground_sets = []
    for set_name in assembly.sets.keys():
        if set_name.startswith('RP_x') and '_y0_' in set_name:  # y=0 module
            ground_sets.append(set_name)
    
    print("Ground-level RP sets found: {}".format(len(ground_sets)))
    
    # Show first few with module coordinates
    for set_name in sorted(ground_sets)[:10]:
        try:
            parts = set_name.split('_')
            mod_x = int(parts[1][1:])  # Remove 'x'
            mod_z = int(parts[3][1:])  # Remove 'z'
            print("  {} -> module ({}, 0, {})".format(set_name, mod_x, mod_z))
        except:
            print("  {} -> (could not parse coordinates)".format(set_name))
    
    if len(ground_sets) > 10:
        print("  ... and {} more".format(len(ground_sets) - 10))

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main function to apply ground boundary conditions."""
    
    print("GROUND BOUNDARY CONDITIONS SCRIPT")
    print("=================================")
    print("Applies pinned supports to all RPs at ground level (module y=0)")
    print("")
    
    try:
        # Apply boundary conditions
        success = apply_ground_boundary_conditions()
        
        if success:
            # Verify results
            verify_ground_boundary_conditions()
            
            # Show details
            show_ground_rp_details()
            
            print("")
            print("=== GROUND BOUNDARY CONDITIONS COMPLETED SUCCESSFULLY ===")
            print("All ground-level RPs are now pinned:")
            print("- Translations constrained (cannot move)")
            print("- Rotations free (can rotate)")
            print("Structure is ready for load application!")
            
        else:
            print("")
            print("=== GROUND BOUNDARY CONDITIONS FAILED ===")
            print("Please check the errors above and ensure:")
            print("1. Scripts D and E have been run successfully")
            print("2. Modular RP sets exist in the assembly")
            print("3. Model-1 exists and is accessible")
        
    except Exception as e:
        print("Error in main execution: {}".format(e))
        import traceback
        traceback.print_exc()

# Run the script
if __name__ == "__main__":
    main()