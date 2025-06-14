# -*- coding: utf-8 -*-
"""
Create Wires Between Coincident RPs Script

Creates wires between coincident RPs from RP-X and RP-Z sets:
- Finds RP-X and RP-Z sets with same module coordinates
- Example: RP-X_x1_y5_z3 and RP-Z_x1_y5_z3 are coincident
- Creates wires between these coincident RPs
- Names wires: WireRP_x1_y5_z3
"""

from abaqus import *
from abaqusConstants import *

def create_coincident_rp_wires():
    """
    Main function to create wires between coincident RPs from RP-X and RP-Z sets.
    """
    
    print("=== CREATING WIRES BETWEEN COINCIDENT RPs ===")
    print("Finding coincident RPs between RP-X and RP-Z sets")
    print("Coincident = same module coordinates, different type (X vs Z)")
    print("")
    
    # Get model and assembly
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        print("Successfully accessed model and assembly")
    except Exception as e:
        print("ERROR: Could not access model: {}".format(e))
        return False
    
    # Find all RP-X and RP-Z sets
    rp_x_sets = {}  # module_coords -> set_name
    rp_z_sets = {}  # module_coords -> set_name
    
    print("Scanning for RP sets...")
    
    for set_name in assembly.sets.keys():
        if set_name.startswith('RP-X_'):
            coords = extract_module_coordinates(set_name)
            if coords:
                rp_x_sets[coords] = set_name
        elif set_name.startswith('RP-Z_'):
            coords = extract_module_coordinates(set_name)
            if coords:
                rp_z_sets[coords] = set_name
    
    print("Found RP sets:")
    print("  RP-X sets: {}".format(len(rp_x_sets)))
    print("  RP-Z sets: {}".format(len(rp_z_sets)))
    
    if len(rp_x_sets) == 0:
        print("ERROR: No RP-X sets found")
        return False
    
    if len(rp_z_sets) == 0:
        print("ERROR: No RP-Z sets found")
        return False
    
    # Find coincident pairs (same module coordinates)
    coincident_pairs = []
    
    for coords in rp_x_sets.keys():
        if coords in rp_z_sets:
            # Found coincident RPs
            rp_x_set_name = rp_x_sets[coords]
            rp_z_set_name = rp_z_sets[coords]
            coincident_pairs.append((coords, rp_x_set_name, rp_z_set_name))
    
    print("")
    print("Found {} coincident RP pairs".format(len(coincident_pairs)))
    
    if len(coincident_pairs) == 0:
        print("No coincident RPs found - no wires to create")
        return False
    
    # Show examples of coincident pairs
    print("Examples of coincident pairs:")
    for i, (coords, rp_x_name, rp_z_name) in enumerate(coincident_pairs[:5]):
        print("  {}: {} <-> {}".format(i+1, rp_x_name, rp_z_name))
    if len(coincident_pairs) > 5:
        print("  ... and {} more pairs".format(len(coincident_pairs) - 5))
    
    print("")
    
    # Clean up existing wires
    cleanup_existing_coincident_wires(assembly)
    
    # Create wires between coincident RPs
    wires_created = 0
    wires_failed = 0
    
    for coords, rp_x_set_name, rp_z_set_name in coincident_pairs:
        if create_wire_between_coincident_rps(assembly, coords, rp_x_set_name, rp_z_set_name):
            wires_created += 1
        else:
            wires_failed += 1
    
    print("")
    print("=== SUMMARY ===")
    print("Wires created: {}".format(wires_created))
    print("Wires failed: {}".format(wires_failed))
    print("Total pairs processed: {}".format(len(coincident_pairs)))
    
    if wires_created > 0:
        print("SUCCESS: Coincident RP wires created successfully!")
        return True
    else:
        print("WARNING: No wires were created")
        return False

def extract_module_coordinates(set_name):
    """
    Extract module coordinates from RP set name.
    
    Args:
        set_name: e.g., "RP-X_x6_y4_z0" or "RP-Z_x3_y2_z1"
    
    Returns:
        tuple: (x, y, z) module coordinates or None if parsing fails
    """
    
    try:
        # Remove the RP-X_ or RP-Z_ prefix
        if set_name.startswith('RP-X_'):
            coords_part = set_name[5:]  # Remove "RP-X_"
        elif set_name.startswith('RP-Z_'):
            coords_part = set_name[5:]  # Remove "RP-Z_"
        else:
            return None
        
        # Handle potential suffix numbers (like _1, _2 for duplicates)
        if coords_part.count('_') > 2:
            parts = coords_part.split('_')
            # Check if last part is a number (suffix)
            if len(parts) > 3 and parts[-1].isdigit():
                # Remove the numeric suffix
                coords_part = '_'.join(parts[:-1])
        
        # Parse x#_y#_z# pattern
        coord_parts = coords_part.split('_')
        
        if len(coord_parts) != 3:
            return None
        
        x_part, y_part, z_part = coord_parts
        
        # Check format and extract numbers
        if (x_part.startswith('x') and y_part.startswith('y') and z_part.startswith('z')):
            x = int(x_part[1:])  # Remove 'x' prefix
            y = int(y_part[1:])  # Remove 'y' prefix
            z = int(z_part[1:])  # Remove 'z' prefix
            return (x, y, z)
        else:
            return None
        
    except Exception as e:
        print("  Warning: Could not parse coordinates from '{}': {}".format(set_name, e))
        return None

def create_wire_between_coincident_rps(assembly, coords, rp_x_set_name, rp_z_set_name):
    """
    Create a wire between coincident RPs from RP-X and RP-Z sets.
    
    Args:
        assembly: Abaqus assembly object
        coords: (x, y, z) module coordinates tuple
        rp_x_set_name: Name of RP-X set
        rp_z_set_name: Name of RP-Z set
    
    Returns:
        bool: Success status
    """
    
    try:
        # Get the RP sets
        if rp_x_set_name not in assembly.sets:
            print("  ERROR: RP-X set '{}' not found".format(rp_x_set_name))
            return False
        
        if rp_z_set_name not in assembly.sets:
            print("  ERROR: RP-Z set '{}' not found".format(rp_z_set_name))
            return False
        
        rp_x_set = assembly.sets[rp_x_set_name]
        rp_z_set = assembly.sets[rp_z_set_name]
        
        # Get the RPs from each set
        if len(rp_x_set.referencePoints) != 1:
            print("  ERROR: RP-X set '{}' contains {} RPs (expected 1)".format(
                rp_x_set_name, len(rp_x_set.referencePoints)))
            return False
        
        if len(rp_z_set.referencePoints) != 1:
            print("  ERROR: RP-Z set '{}' contains {} RPs (expected 1)".format(
                rp_z_set_name, len(rp_z_set.referencePoints)))
            return False
        
        rp_x = rp_x_set.referencePoints[0]
        rp_z = rp_z_set.referencePoints[0]
        
        # Create wire name
        wire_name = "WireRP_x{}_y{}_z{}".format(coords[0], coords[1], coords[2])
        
        # Handle potential duplicate names
        base_name = wire_name
        counter = 1
        while wire_name in assembly.features:
            wire_name = "{}_{}".format(base_name, counter)
            counter += 1
        
        # Create wire between the two RPs
        wire_feature = assembly.WirePolyLine(
            mergeType=IMPRINT,
            meshable=False,
            points=((rp_x, rp_z),)
        )
        
        # Rename the wire feature
        old_name = wire_feature.name
        assembly.features.changeKey(old_name, wire_name)
        
        print("  Created wire: {} connecting {} and {}".format(
            wire_name, rp_x_set_name, rp_z_set_name))
        
        return True
        
    except Exception as e:
        print("  ERROR creating wire for coords {}: {}".format(coords, e))
        return False

def cleanup_existing_coincident_wires(assembly):
    """
    Clean up existing coincident RP wires.
    """
    
    print("Cleaning existing coincident RP wires...")
    
    try:
        # Find existing coincident wires
        coincident_wires = []
        for feature_name in assembly.features.keys():
            if feature_name.startswith('WireRP_x') and '_y' in feature_name and '_z' in feature_name:
                coincident_wires.append(feature_name)
        
        # Remove them
        wires_removed = 0
        for wire_name in coincident_wires:
            try:
                del assembly.features[wire_name]
                wires_removed += 1
            except:
                pass
        
        print("  Removed {} existing coincident wires".format(wires_removed))
        return True
        
    except Exception as e:
        print("  Error during cleanup: {}".format(e))
        return False

def verify_coincident_wires():
    """
    Verify that coincident RP wires were created correctly.
    """
    
    print("\n=== VERIFICATION ===")
    
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        
        # Find all coincident RP wires
        coincident_wires = []
        
        for feature_name in assembly.features.keys():
            if feature_name.startswith('WireRP_x') and '_y' in feature_name and '_z' in feature_name:
                coincident_wires.append(feature_name)
        
        print("Coincident RP wires found: {}".format(len(coincident_wires)))
        
        if len(coincident_wires) > 0:
            print("Example coincident wires:")
            for wire_name in sorted(coincident_wires)[:10]:
                print("  - {}".format(wire_name))
            
            if len(coincident_wires) > 10:
                print("  ... and {} more".format(len(coincident_wires) - 10))
        else:
            print("No coincident RP wires found")
        
        return len(coincident_wires)
        
    except Exception as e:
        print("ERROR during verification: {}".format(e))
        return 0

def show_rp_analysis():
    """
    Show analysis of available RP sets for debugging.
    """
    
    print("\n=== RP SETS ANALYSIS ===")
    
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        
        # Collect RP sets by type
        rp_x_coords = set()
        rp_z_coords = set()
        
        rp_x_sets = []
        rp_z_sets = []
        
        for set_name in assembly.sets.keys():
            if set_name.startswith('RP-X_'):
                rp_x_sets.append(set_name)
                coords = extract_module_coordinates(set_name)
                if coords:
                    rp_x_coords.add(coords)
            elif set_name.startswith('RP-Z_'):
                rp_z_sets.append(set_name)
                coords = extract_module_coordinates(set_name)
                if coords:
                    rp_z_coords.add(coords)
        
        print("RP set analysis:")
        print("  RP-X sets: {} (unique coordinates: {})".format(len(rp_x_sets), len(rp_x_coords)))
        print("  RP-Z sets: {} (unique coordinates: {})".format(len(rp_z_sets), len(rp_z_coords)))
        
        # Find overlapping coordinates
        common_coords = rp_x_coords.intersection(rp_z_coords)
        print("  Common coordinates: {}".format(len(common_coords)))
        
        if len(common_coords) > 0:
            print("Examples of common coordinates:")
            for coords in sorted(list(common_coords))[:5]:
                print("  - x{}_y{}_z{}".format(coords[0], coords[1], coords[2]))
            if len(common_coords) > 5:
                print("  ... and {} more".format(len(common_coords) - 5))
        else:
            print("No common coordinates found!")
            print("This means no coincident RPs exist")
        
        # Show some examples of each type
        if len(rp_x_sets) > 0:
            print("Example RP-X sets:")
            for set_name in sorted(rp_x_sets)[:5]:
                print("  - {}".format(set_name))
        
        if len(rp_z_sets) > 0:
            print("Example RP-Z sets:")
            for set_name in sorted(rp_z_sets)[:5]:
                print("  - {}".format(set_name))
        
    except Exception as e:
        print("ERROR during analysis: {}".format(e))

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main function to create coincident RP wires."""
    
    print("COINCIDENT RP WIRES CREATION SCRIPT")
    print("=" * 40)
    print("Creates wires between coincident RPs from RP-X and RP-Z sets")
    print("Example: RP-X_x1_y5_z3 <-> RP-Z_x1_y5_z3")
    print("")
    
    try:
        # Show analysis of available RP sets
        show_rp_analysis()
        
        print("")
        
        # Create coincident wires
        success = create_coincident_rp_wires()
        
        # Verify results
        total_wires = verify_coincident_wires()
        
        print("")
        print("=" * 40)
        
        if success and total_wires > 0:
            print("SUCCESS: Coincident RP wires created!")
            print("- {} wires created between coincident RPs".format(total_wires))
            print("- Connects RP-X and RP-Z sets at same module coordinates")
            print("- Named as WireRP_x#_y#_z#")
            print("- Ready for connector assignment and analysis")
            print("")
            print("NEXT STEPS:")
            print("1. In Abaqus GUI, select wires named 'WireRP_*'")
            print("2. Apply appropriate connector sections (rigid or flexible)")
            print("3. These connections link BarX and BarZ endpoint RPs")
        else:
            print("WARNING: Coincident wire creation issues")
            print("Possible causes:")
            print("- No RP-Z sets found (only RP-X sets exist)")
            print("- No matching coordinates between RP-X and RP-Z sets")
            print("- Check that both RP creation scripts (d and e) have been run")
        
    except Exception as e:
        print("ERROR in main execution: {}".format(e))
        import traceback
        traceback.print_exc()

# Run the script
if __name__ == "__main__":
    main()