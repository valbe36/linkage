# -*- coding: utf-8 -*-
"""
Create BarX Endpoint Reference Points Script

Creates RPs at the endpoints of BarX instances only:
- Avoids duplicates using coordinate precision
- Creates individual sets for each RP
- Uses meaningful naming: RP-X_x2_y1_z5
- Applies same coordinate precision as bars for perfect alignment
"""

from abaqus import *
from abaqusConstants import *
import math

# ============================================================================
# COORDINATE PRECISION SYSTEM - Same as used in bar creation
# ============================================================================

# Global parameters - must match the bar creation script
dx = 2.21
dy = 1.275
dz = 2.21

def get_exact_modular_coordinate(module_index, spacing, precision=6):
    """Calculate exact modular coordinate with consistent precision."""
    exact_coord = module_index * spacing
    return round(exact_coord, precision)

def get_modular_position(ix, iy, iz, dx_param=None, dy_param=None, dz_param=None, precision=6):
    """Calculate exact modular position from module indices."""
    if dx_param is None: dx_param = dx
    if dy_param is None: dy_param = dy
    if dz_param is None: dz_param = dz
    
    x = get_exact_modular_coordinate(ix, dx_param, precision)
    y = get_exact_modular_coordinate(iy, dy_param, precision)
    z = get_exact_modular_coordinate(iz, dz_param, precision)
    
    return (x, y, z)

def convert_to_module_indices(x, y, z, dx_param=None, dy_param=None, dz_param=None):
    """Convert absolute coordinates back to module indices."""
    if dx_param is None: dx_param = dx
    if dy_param is None: dy_param = dy
    if dz_param is None: dz_param = dz
    
    ix = int(round(x / dx_param))
    iy = int(round(y / dy_param))
    iz = int(round(z / dz_param))
    
    return (ix, iy, iz)

def standardize_position(position, precision=6):
    """Standardize position to exact precision."""
    return tuple(round(coord, precision) for coord in position)

def positions_are_duplicate(pos1, pos2, tolerance=0.001):
    """Check if two positions are duplicates within tolerance."""
    max_diff = max(abs(c1 - c2) for c1, c2 in zip(pos1, pos2))
    return max_diff <= tolerance

# ============================================================================
# MAIN RP CREATION FUNCTIONS
# ============================================================================

def create_endpoint_rps():
    """
    Create RPs at endpoints of BarX instances only.
    """
    
    print("=== CREATING BarX ENDPOINT REFERENCE POINTS ===")
    print("Creating RPs at BarX endpoints only with coordinate precision")
    print("")
    
    # Get model and assembly
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        print("Successfully accessed model and assembly")
    except Exception as e:
        print("ERROR: Could not access model: {}".format(e))
        return False
    
    # Process BarX instances only
    print("Processing BarX instances...")
    barx_rps = process_bar_instances(assembly, 'BarX', 'X')
    
    # Summary
    print("")
    print("=== SUMMARY ===")
    print("BarX endpoint RPs created: {}".format(barx_rps))
    
    if barx_rps > 0:
        print("SUCCESS: BarX endpoint RPs created with perfect coordinate precision!")
        return True
    else:
        print("WARNING: No RPs were created")
        return False

def process_bar_instances(assembly, bar_prefix, rp_prefix):
    """
    Process all instances of a specific bar type (BarX or BarZ).
    
    Args:
        assembly: Abaqus assembly object
        bar_prefix: 'BarX' or 'BarZ'
        rp_prefix: 'X' or 'Z' for RP naming
    
    Returns:
        int: Number of RPs created
    """
    
    # Find all instances of this bar type
    bar_instances = []
    for inst_name, inst in assembly.instances.items():
        if inst_name.startswith(bar_prefix + '-'):
            bar_instances.append((inst_name, inst))
    
    print("  Found {} {} instances".format(len(bar_instances), bar_prefix))
    
    if len(bar_instances) == 0:
        return 0
    
    # Collect all endpoint positions
    endpoint_positions = []
    
    for inst_name, inst in bar_instances:
        try:
            # Get vertices of the instance
            vertices = inst.vertices
            
            if len(vertices) >= 2:
                # Get start and end vertices (first and last)
                start_vertex = vertices[0]
                end_vertex = vertices[-1]
                
                start_pos = start_vertex.pointOn[0]
                end_pos = end_vertex.pointOn[0]
                
                # Standardize positions using same precision as bars
                start_pos = standardize_position(start_pos)
                end_pos = standardize_position(end_pos)
                
                # Add to collection with instance info
                endpoint_positions.append((start_pos, inst_name, 'start'))
                endpoint_positions.append((end_pos, inst_name, 'end'))
                
        except Exception as e:
            print("    Warning: Could not process {}: {}".format(inst_name, e))
            continue
    
    print("    Collected {} endpoint positions".format(len(endpoint_positions)))
    
    # Remove duplicates and create RPs
    unique_positions = remove_duplicate_positions(endpoint_positions)
    print("    Unique positions after duplicate removal: {}".format(len(unique_positions)))
    
    # Create RPs at unique positions
    rps_created = 0
    
    for position, source_instances in unique_positions:
        if create_single_endpoint_rp(assembly, position, source_instances, rp_prefix):
            rps_created += 1
    
    return rps_created

def remove_duplicate_positions(endpoint_positions):
    """
    Remove duplicate positions and group by unique location.
    
    Args:
        endpoint_positions: List of (position, inst_name, endpoint_type)
    
    Returns:
        List of (position, [source_instances])
    """
    
    unique_positions = []
    tolerance = 0.001
    
    for position, inst_name, endpoint_type in endpoint_positions:
        # Check if this position already exists
        found_existing = False
        
        for i, (existing_pos, existing_sources) in enumerate(unique_positions):
            if positions_are_duplicate(position, existing_pos, tolerance):
                # Add this source to existing position
                unique_positions[i][1].append((inst_name, endpoint_type))
                found_existing = True
                break
        
        if not found_existing:
            # New unique position
            unique_positions.append([position, [(inst_name, endpoint_type)]])
    
    return unique_positions

def create_single_endpoint_rp(assembly, position, source_instances, rp_prefix):
    """
    Create a single RP at the specified position with individual set.
    
    Args:
        assembly: Abaqus assembly
        position: (x, y, z) coordinates
        source_instances: List of (inst_name, endpoint_type) that contribute to this RP
        rp_prefix: 'X' or 'Z' for naming
    
    Returns:
        bool: Success status
    """
    
    try:
        # Convert position to module indices for naming
        ix, iy, iz = convert_to_module_indices(*position)
        
        # Create meaningful set name
        set_name = "RP-{}_x{}_y{}_z{}".format(rp_prefix, ix, iy, iz)
        
        # Handle potential duplicates in set names
        base_name = set_name
        counter = 1
        while set_name in assembly.sets:
            set_name = "{}_{}".format(base_name, counter)
            counter += 1
        
        # Create RP at exact position
        rp_feature = assembly.ReferencePoint(point=position)
        rp = assembly.referencePoints[rp_feature.id]
        
        # Create individual set for this RP
        assembly.Set(referencePoints=(rp,), name=set_name)
        
        # Log creation details
        print("    Created RP: {} at ({:.6f}, {:.6f}, {:.6f})".format(
            set_name, position[0], position[1], position[2]))
        
        # Log source instances (first few)
        if len(source_instances) > 0:
            example_sources = source_instances[:3]
            source_info = ", ".join("{}({})".format(inst, etype) for inst, etype in example_sources)
            if len(source_instances) > 3:
                source_info += " +{} more".format(len(source_instances) - 3)
            print("      Sources: {}".format(source_info))
        
        return True
        
    except Exception as e:
        print("    ERROR creating RP at {}: {}".format(position, e))
        return False

def verify_endpoint_rps():
    """
    Verify that BarX endpoint RPs were created correctly.
    """
    
    print("\n=== VERIFICATION ===")
    
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        
        # Count RP sets by type
        rp_x_sets = []
        other_rp_sets = []
        
        for set_name in assembly.sets.keys():
            if set_name.startswith('RP-X_'):
                rp_x_sets.append(set_name)
            elif set_name.startswith('RP-'):
                other_rp_sets.append(set_name)
        
        print("RP sets created:")
        print("  RP-X sets (BarX endpoints): {}".format(len(rp_x_sets)))
        print("  Other RP sets: {}".format(len(other_rp_sets)))
        print("  Total BarX endpoint RP sets: {}".format(len(rp_x_sets)))
        
        # Show examples
        if len(rp_x_sets) > 0:
            print("\nExample RP-X sets:")
            for set_name in sorted(rp_x_sets)[:10]:
                print("  - {}".format(set_name))
            if len(rp_x_sets) > 10:
                print("    ... and {} more".format(len(rp_x_sets) - 10))
        
        # Verify a few sets contain RPs
        test_sets = rp_x_sets[:5]
        print("\nSet content verification:")
        for set_name in test_sets:
            try:
                rp_set = assembly.sets[set_name]
                rp_count = len(rp_set.referencePoints)
                print("  {}: {} RPs".format(set_name, rp_count))
            except Exception as e:
                print("  {}: ERROR - {}".format(set_name, e))
        
        return len(rp_x_sets)
        
    except Exception as e:
        print("ERROR during verification: {}".format(e))
        return 0

def show_coordinate_precision_info():
    """
    Show information about coordinate precision used.
    """
    
    print("\n=== COORDINATE PRECISION INFORMATION ===")
    print("Module dimensions: dx={}, dy={}, dz={}".format(dx, dy, dz))
    print("Precision: 6 decimal places")
    print("Duplicate tolerance: 0.001")
    print("")
    print("This ensures perfect alignment with bar instances created using")
    print("the same coordinate precision system.")

def clean_existing_endpoint_rps():
    """
    Clean up existing BarX endpoint RPs before creating new ones.
    """
    
    print("Cleaning existing BarX endpoint RPs...")
    
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        
        # Find existing BarX endpoint RP sets only
        endpoint_sets = []
        for set_name in assembly.sets.keys():
            if set_name.startswith('RP-X_'):
                endpoint_sets.append(set_name)
        
        # Remove sets and RPs
        rps_removed = 0
        sets_removed = 0
        
        for set_name in endpoint_sets:
            try:
                # Get RPs from set before deleting
                rp_set = assembly.sets[set_name]
                rp_ids = [rp.id for rp in rp_set.referencePoints]
                
                # Delete set
                del assembly.sets[set_name]
                sets_removed += 1
                
                # Delete RPs
                for rp_id in rp_ids:
                    try:
                        del assembly.referencePoints[rp_id]
                        rps_removed += 1
                    except:
                        pass
                        
            except Exception as e:
                print("  Warning: Could not clean {}: {}".format(set_name, e))
        
        print("  Removed {} RP-X sets and {} RPs".format(sets_removed, rps_removed))
        return True
        
    except Exception as e:
        print("  Error during cleanup: {}".format(e))
        return False

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main function to create BarX endpoint RPs."""
    
    print("BarX ENDPOINT REFERENCE POINTS CREATION SCRIPT")
    print("=" * 50)
    print("Creates RPs at BarX endpoints only with individual sets")
    print("")
    
    try:
        # Show coordinate system info
        show_coordinate_precision_info()
        
        # Optional: Clean existing BarX endpoint RPs
        # clean_existing_endpoint_rps()
        
        # Create BarX endpoint RPs
        success = create_endpoint_rps()
        
        # Verify results
        total_rps = verify_endpoint_rps()
        
        if success and total_rps > 0:
            print("\n" + "=" * 50)
            print("SUCCESS: BarX endpoint RPs created successfully!")
            print("- {} RPs created at BarX endpoints only".format(total_rps))
            print("- Each RP has individual set for easy access")
            print("- Perfect coordinate precision maintained")
            print("- Ready for boundary conditions and analysis")
        else:
            print("\n" + "=" * 50)
            print("WARNING: BarX endpoint RP creation issues")
            print("Check messages above for details")
        
    except Exception as e:
        print("ERROR in main execution: {}".format(e))
        import traceback
        traceback.print_exc()

# Run the script
if __name__ == "__main__":
    main()