# -*- coding: utf-8 -*-
"""
Create Set of All RP-Z with Module Coordinate Y = 0

Creates a set containing all RP-Z reference points that have module coordinate y = 0
(i.e., sets named like RP-Z_x#_y0_z#)
"""

from abaqus import *
from abaqusConstants import *

def create_rpz_y0_set():
    """
    Create a set of all RP-Z reference points with module coordinate y = 0.
    """
    
    print("=== CREATING RP-Z Y=0 SET ===")
    print("Finding all RP-Z sets with module coordinate y = 0")
    print("Set name will be: RP-Z_y0")
    print("")
    
    # Get model and assembly
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        print("Successfully accessed model and assembly")
    except Exception as e:
        print("ERROR: Could not access model: {}".format(e))
        return False
    
    # Find all RP-Z sets with y = 0
    rpz_y0_sets = find_rpz_y0_sets(assembly)
    
    if len(rpz_y0_sets) == 0:
        print("No RP-Z sets found with y = 0")
        return False
    
    print("Found {} RP-Z sets with y = 0".format(len(rpz_y0_sets)))
    
    # Create the set
    success = create_y0_set(assembly, rpz_y0_sets)
    
    # Verify results
    verify_y0_set(assembly)
    
    return success

def find_rpz_y0_sets(assembly):
    """Find all RP-Z sets with module coordinate y = 0."""
    
    rpz_y0_sets = []
    
    print("Scanning RP-Z sets...")
    
    for set_name in assembly.sets.keys():
        if set_name.startswith('RP-Z_'):
            # Extract coordinates from set name
            coords = extract_coordinates_from_set_name(set_name)
            
            if coords is not None:
                x, y, z = coords
                
                # Check if y = 0
                if y == 0:
                    try:
                        rp_set = assembly.sets[set_name]
                        if hasattr(rp_set, 'referencePoints') and len(rp_set.referencePoints) > 0:
                            rpz_y0_sets.append({
                                'set_name': set_name,
                                'set_object': rp_set,
                                'coords': coords,
                                'rp': rp_set.referencePoints[0]
                            })
                            print("  Found: {} (x{}_y{}_z{})".format(set_name, x, y, z))
                    except Exception as e:
                        print("  Warning: Could not access {}: {}".format(set_name, e))
    
    return rpz_y0_sets

def extract_coordinates_from_set_name(set_name):
    """Extract coordinates from RP-Z set name."""
    try:
        if not set_name.startswith('RP-Z_'):
            return None
        
        coords_part = set_name[5:]  # Remove "RP-Z_"
        
        # Handle potential suffix numbers
        if coords_part.count('_') > 2:
            parts = coords_part.split('_')
            if len(parts) > 3 and parts[-1].isdigit():
                coords_part = '_'.join(parts[:-1])
        
        # Parse x#_y#_z# pattern
        coord_parts = coords_part.split('_')
        
        if len(coord_parts) != 3:
            return None
        
        x_part, y_part, z_part = coord_parts
        
        if (x_part.startswith('x') and y_part.startswith('y') and z_part.startswith('z')):
            x = int(x_part[1:])
            y = int(y_part[1:])
            z = int(z_part[1:])
            return (x, y, z)
        
        return None
        
    except Exception:
        return None

def create_y0_set(assembly, rpz_y0_sets):
    """Create the RP-Z_y0 set."""
    
    set_name = 'RP-ground'
    
    print("\nCreating set '{}'...".format(set_name))
    
    try:
        # Remove existing set if it exists
        if set_name in assembly.sets:
            print("  Removing existing set: {}".format(set_name))
            del assembly.sets[set_name]
        
        # Collect all RPs
        rps_for_set = []
        for rpz_info in rpz_y0_sets:
            rps_for_set.append(rpz_info['rp'])
        
        # Create the set
        assembly.Set(referencePoints=tuple(rps_for_set), name=set_name)
        
        print("  Successfully created set '{}' with {} RPs".format(set_name, len(rps_for_set)))
        
        # Show coordinate distribution
        show_coordinate_distribution(rpz_y0_sets)
        
        return True
        
    except Exception as e:
        print("  ERROR creating set '{}': {}".format(set_name, e))
        return False

def show_coordinate_distribution(rpz_y0_sets):
    """Show the distribution of coordinates for the y=0 RP-Z sets."""
    
    print("\n  Coordinate distribution (y=0):")
    
    # Group by x coordinate
    x_groups = {}
    for rpz_info in rpz_y0_sets:
        x = rpz_info['coords'][0]
        if x not in x_groups:
            x_groups[x] = []
        x_groups[x].append(rpz_info)
    
    for x in sorted(x_groups.keys()):
        z_coords = [rpz_info['coords'][2] for rpz_info in x_groups[x]]
        z_coords.sort()
        print("    x = {}: {} RPs at z = {}".format(x, len(z_coords), z_coords))

def verify_y0_set(assembly):
    """Verify that the RP-Z_y0 set was created correctly."""
    
    print("\n=== VERIFICATION ===")
    
    set_name = 'RP-ground'
    
    if set_name in assembly.sets:
        try:
            rp_set = assembly.sets[set_name]
            rp_count = len(rp_set.referencePoints)
            print("Set '{}': {} RPs".format(set_name, rp_count))
            
            # Verify that all RPs are indeed from y=0 sets
            print("Verification: Checking that all RPs are from y=0 coordinate sets...")
            
            # Find original set names for verification
            y0_set_names = []
            for original_set_name in assembly.sets.keys():
                if original_set_name.startswith('RP-Z_') and '_y0_' in original_set_name:
                    y0_set_names.append(original_set_name)
            
            print("  Original RP-Z y=0 sets found: {}".format(len(y0_set_names)))
            
            # Show examples of included sets
            if len(y0_set_names) > 0:
                print("  Example sets included:")
                for set_name_example in sorted(y0_set_names)[:10]:
                    print("    - {}".format(set_name_example))
                if len(y0_set_names) > 10:
                    print("    ... and {} more".format(len(y0_set_names) - 10))
            
        except Exception as e:
            print("Set '{}': ERROR reading - {}".format(set_name, e))
    else:
        print("Set '{}': NOT FOUND".format(set_name))

def show_usage_info():
    """Show usage information for the created set."""
    
    print("\n=== USAGE INFORMATION ===")
    print("Set 'RP-Z_y0' contains all RP-Z reference points at ground level (y=0)")
    print("This set can be used for:")
    print("- Applying ground-level boundary conditions")
    print("- Foundation loads and constraints")
    print("- Base-level structural connections")
    print("- Ground reaction analysis")
    print("")
    print("The set includes RP-Z from various x and z coordinates, all at y=0")

def main():
    """Main function to create RP-Z y=0 set."""
    
    print("RP-Z Y=0 SET CREATOR")
    print("=" * 25)
    print("Creates a set of all RP-Z reference points with module coordinate y = 0")
    print("")
    
    try:
        # Create the set
        success = create_rpz_y0_set()
        
        # Show usage information
        if success:
            show_usage_info()
        
        print("")
        print("=" * 25)
        
        if success:
            print("SUCCESS: RP-Z y=0 set created!")
            print("Set name: 'RP-ground'")
            print("Contains all RP-Z reference points at ground level (y=0)")
        else:
            print("WARNING: RP-Z y=0 set creation issues")
            print("Check that RP-Z sets exist (run script e first)")
        
    except Exception as e:
        print("ERROR in main execution: {}".format(e))
        import traceback
        traceback.print_exc()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    main()