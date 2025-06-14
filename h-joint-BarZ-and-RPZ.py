# -*- coding: utf-8 -*-
"""
Create Wires Between RP-Z Sets and Coincident BarZ Instances

Creates wires between RP-Z reference points and coincident BarZ instance endpoints:
- Finds all RP-Z sets (e.g., RP-Z_x0_y1_z0)
- Finds all BarZ instances (e.g., BarZ-a_x0_y0_z0, BarZ-b_x0_y0_z0)
- Identifies coincident points between RP locations and BarZ endpoints
- Creates one wire per RP-Z (no duplicates, even if multiple BarZ are coincident)
- Names wires: WireRPZ_x0_y1_z0
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

def standardize_position(position, precision=6):
    """Standardize position to exact precision."""
    return tuple(round(coord, precision) for coord in position)

def positions_are_coincident(pos1, pos2, tolerance=0.01):
    """Check if two positions are coincident within tolerance."""
    max_diff = max(abs(c1 - c2) for c1, c2 in zip(pos1, pos2))
    return max_diff <= tolerance

def create_rpz_to_barz_wires():
    """
    Main function to create wires between RP-Z sets and coincident BarZ endpoints.
    """
    
    print("=== CREATING WIRES BETWEEN RP-Z AND BARZ INSTANCES ===")
    print("Connecting RP-Z reference points to coincident BarZ endpoints")
    print("One wire per RP-Z, avoiding duplicates")
    print("")
    
    # Get model and assembly
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        print("Successfully accessed model and assembly")
    except Exception as e:
        print("ERROR: Could not access model: {}".format(e))
        return False
    
    # Find all RP-Z sets
    rpz_sets = find_rpz_sets(assembly)
    print("Found {} RP-Z sets".format(len(rpz_sets)))
    
    if len(rpz_sets) == 0:
        print("ERROR: No RP-Z sets found")
        return False
    
    # Find all BarZ instances  
    barz_instances = find_barz_instances(assembly)
    print("Found {} BarZ instances".format(len(barz_instances)))
    
    if len(barz_instances) == 0:
        print("ERROR: No BarZ instances found")
        return False
    
    # Build BarZ endpoint map for efficient searching
    barz_endpoints = build_barz_endpoint_map(barz_instances)
    print("Extracted {} BarZ endpoints".format(len(barz_endpoints)))
    
    # Clean up existing wires
    cleanup_existing_rpz_barz_wires(assembly)
    
    # Create wires between RP-Z sets and coincident BarZ endpoints
    wires_created = 0
    wires_failed = 0
    
    print("")
    print("Creating RP-Z to BarZ connection wires...")
    
    for i, (set_name, rp_set) in enumerate(rpz_sets):
        
        if i < 5:  # Show progress for first few
            print("  Processing {}: {}".format(i+1, set_name))
        elif i == 5:
            print("  ... processing remaining {} RP-Z sets ...".format(len(rpz_sets) - 5))
        
        if create_wire_for_rpz_set(assembly, set_name, rp_set, barz_endpoints, i < 5):
            wires_created += 1
        else:
            wires_failed += 1
    
    print("")
    print("=== SUMMARY ===")
    print("Wires created: {}".format(wires_created))
    print("Wires failed: {}".format(wires_failed))
    print("Total RP-Z sets processed: {}".format(len(rpz_sets)))
    
    if wires_created > 0:
        print("SUCCESS: RP-Z to BarZ wires created successfully!")
        return True
    else:
        print("WARNING: No wires were created")
        return False

def find_rpz_sets(assembly):
    """Find all RP-Z sets in the assembly."""
    
    rpz_sets = []
    
    for set_name in assembly.sets.keys():
        if set_name.startswith('RP-Z_'):
            try:
                rp_set = assembly.sets[set_name]
                if hasattr(rp_set, 'referencePoints') and len(rp_set.referencePoints) > 0:
                    rpz_sets.append((set_name, rp_set))
            except Exception as e:
                print("  Warning: Could not access RP-Z set '{}': {}".format(set_name, e))
                continue
    
    return rpz_sets

def find_barz_instances(assembly):
    """Find all BarZ instances in the assembly."""
    
    barz_instances = []
    
    for inst_name, inst in assembly.instances.items():
        if inst_name.startswith('BarZ-'):
            barz_instances.append((inst_name, inst))
    
    return barz_instances

def build_barz_endpoint_map(barz_instances):
    """Build a map of all BarZ endpoints for efficient searching."""
    
    barz_endpoints = []
    
    for inst_name, inst in barz_instances:
        try:
            # Get instance vertices (endpoints)
            vertices = inst.vertices
            
            if len(vertices) >= 2:
                # Get start and end vertices
                start_vertex = vertices[0]
                end_vertex = vertices[-1]
                
                start_pos = standardize_position(start_vertex.pointOn[0])
                end_pos = standardize_position(end_vertex.pointOn[0])
                
                # Add both endpoints to the map
                barz_endpoints.append({
                    'instance_name': inst_name,
                    'instance': inst,
                    'vertex': start_vertex,
                    'vertex_id': 0,
                    'position': start_pos,
                    'endpoint_type': 'start'
                })
                
                barz_endpoints.append({
                    'instance_name': inst_name,
                    'instance': inst,
                    'vertex': end_vertex,
                    'vertex_id': len(vertices) - 1,
                    'position': end_pos,
                    'endpoint_type': 'end'
                })
                
        except Exception as e:
            print("  Warning: Could not process BarZ instance '{}': {}".format(inst_name, e))
            continue
    
    return barz_endpoints

def create_wire_for_rpz_set(assembly, set_name, rp_set, barz_endpoints, show_details):
    """
    Create a wire between an RP-Z set and its coincident BarZ endpoint.
    """
    
    tolerance = 0.01
    
    try:
        # Get the RP from the set
        if len(rp_set.referencePoints) != 1:
            if show_details:
                print("    ERROR: RP-Z set '{}' contains {} RPs (expected 1)".format(
                    set_name, len(rp_set.referencePoints)))
            return False
        
        rp = rp_set.referencePoints[0]
        
        # Extract coordinates from set name and calculate RP position
        coords = extract_coordinates_from_set_name(set_name)
        if coords is None:
            if show_details:
                print("    Could not extract coordinates from {}".format(set_name))
            return False
        
        # Calculate RP position using modular coordinate system
        rp_position = get_modular_position(coords[0], coords[1], coords[2])
        rp_position = standardize_position(rp_position)
        
        # Find coincident BarZ endpoints
        coincident_endpoints = []
        
        for endpoint_info in barz_endpoints:
            if positions_are_coincident(rp_position, endpoint_info['position'], tolerance):
                coincident_endpoints.append(endpoint_info)
        
        if len(coincident_endpoints) == 0:
            if show_details:
                print("    No coincident BarZ endpoints found for {}".format(set_name))
                print("      RP position: ({:.6f}, {:.6f}, {:.6f})".format(*rp_position))
            return False
        
        # Select the best endpoint (in case of multiple coincident endpoints)
        selected_endpoint = select_best_endpoint(coincident_endpoints)
        
        # Create wire name
        wire_name = "WireRPZ_x{}_y{}_z{}".format(coords[0], coords[1], coords[2])
        
        # Handle potential duplicate names
        base_name = wire_name
        counter = 1
        while wire_name in assembly.features:
            wire_name = "{}_{}".format(base_name, counter)
            counter += 1
        
        # Create wire between RP and BarZ endpoint
        wire_feature = assembly.WirePolyLine(
            mergeType=IMPRINT,
            meshable=False,
            points=((rp, selected_endpoint['vertex']),)
        )
        
        # Rename the wire feature
        old_name = wire_feature.name
        assembly.features.changeKey(old_name, wire_name)
        
        if show_details:
            distance = math.sqrt(sum([(rp_position[i] - selected_endpoint['position'][i])**2 for i in range(3)]))
            print("    Created wire: {} -> {} {} (distance: {:.6f})".format(
                wire_name, selected_endpoint['instance_name'], 
                selected_endpoint['endpoint_type'], distance))
            print("      RP position: ({:.6f}, {:.6f}, {:.6f})".format(*rp_position))
            print("      BarZ position: ({:.6f}, {:.6f}, {:.6f})".format(*selected_endpoint['position']))
            
            if len(coincident_endpoints) > 1:
                print("      Note: {} coincident endpoints found, selected {}".format(
                    len(coincident_endpoints), selected_endpoint['instance_name']))
        
        return True
        
    except Exception as e:
        if show_details:
            print("    ERROR creating wire for {}: {}".format(set_name, e))
        return False

def select_best_endpoint(coincident_endpoints):
    """
    Select the best endpoint when multiple BarZ endpoints are coincident.
    Uses tie-breaking rules for consistency.
    """
    
    if len(coincident_endpoints) == 1:
        return coincident_endpoints[0]
    
    # Sort by instance name for consistency
    coincident_endpoints.sort(key=lambda x: (x['instance_name'], x['endpoint_type']))
    
    return coincident_endpoints[0]

def extract_coordinates_from_set_name(set_name):
    """
    Extract coordinates from RP-Z set name.
    
    Args:
        set_name: e.g., "RP-Z_x0_y1_z0"
    
    Returns:
        tuple: (x, y, z) coordinates or None if parsing fails
    """
    
    try:
        # Remove the RP-Z_ prefix
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
        else:
            return None
        
    except Exception:
        return None

def cleanup_existing_rpz_barz_wires(assembly):
    """Clean up existing RP-Z to BarZ wires."""
    
    print("Cleaning existing RP-Z to BarZ wires...")
    
    try:
        # Find existing wires
        existing_wires = []
        for feature_name in assembly.features.keys():
            if feature_name.startswith('WireRPZ_x') and '_y' in feature_name and '_z' in feature_name:
                existing_wires.append(feature_name)
        
        # Remove them
        wires_removed = 0
        for wire_name in existing_wires:
            try:
                del assembly.features[wire_name]
                wires_removed += 1
            except:
                pass
        
        print("  Removed {} existing RP-Z to BarZ wires".format(wires_removed))
        
    except Exception as e:
        print("  Error during cleanup: {}".format(e))

def verify_rpz_barz_wires():
    """Verify that RP-Z to BarZ wires were created correctly."""
    
    print("\n=== VERIFICATION ===")
    
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        
        # Find all RP-Z to BarZ wires
        rpz_barz_wires = []
        
        for feature_name in assembly.features.keys():
            if feature_name.startswith('WireRPZ_x') and '_y' in feature_name and '_z' in feature_name:
                rpz_barz_wires.append(feature_name)
        
        print("RP-Z to BarZ wires found: {}".format(len(rpz_barz_wires)))
        
        if len(rpz_barz_wires) > 0:
            print("Example wires:")
            for wire_name in sorted(rpz_barz_wires)[:10]:
                print("  - {}".format(wire_name))
            
            if len(rpz_barz_wires) > 10:
                print("  ... and {} more".format(len(rpz_barz_wires) - 10))
        else:
            print("No RP-Z to BarZ wires found")
        
        return len(rpz_barz_wires)
        
    except Exception as e:
        print("ERROR during verification: {}".format(e))
        return 0

def analyze_rpz_barz_coincidence():
    """Analyze coincidence between RP-Z sets and BarZ instances for debugging."""
    
    print("\n=== RP-Z to BarZ COINCIDENCE ANALYSIS ===")
    
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        
        # Sample analysis with first few RP-Z sets
        rpz_sets = find_rpz_sets(assembly)
        barz_instances = find_barz_instances(assembly)
        
        if len(rpz_sets) == 0 or len(barz_instances) == 0:
            print("No RP-Z sets or BarZ instances found for analysis")
            return
        
        barz_endpoints = build_barz_endpoint_map(barz_instances)
        
        print("Analysis of first 5 RP-Z sets:")
        
        tolerance = 0.01
        
        for i, (set_name, rp_set) in enumerate(rpz_sets[:5]):
            print("\n  RP-Z set: {}".format(set_name))
            
            try:
                if len(rp_set.referencePoints) == 1:
                    # Calculate RP position from set name instead of trying to access it directly
                    coords = extract_coordinates_from_set_name(set_name)
                    if coords is None:
                        print("    ERROR: Could not extract coordinates from set name")
                        continue
                    
                    rp_position = get_modular_position(coords[0], coords[1], coords[2])
                    rp_position = standardize_position(rp_position)
                    print("    RP position: ({:.6f}, {:.6f}, {:.6f})".format(*rp_position))
                    
                    # Find coincident endpoints
                    coincident_count = 0
                    for endpoint_info in barz_endpoints:
                        if positions_are_coincident(rp_position, endpoint_info['position'], tolerance):
                            coincident_count += 1
                            if coincident_count <= 3:  # Show first 3
                                distance = math.sqrt(sum([(rp_position[j] - endpoint_info['position'][j])**2 for j in range(3)]))
                                print("      Coincident: {} {} (distance: {:.6f})".format(
                                    endpoint_info['instance_name'], endpoint_info['endpoint_type'], distance))
                    
                    if coincident_count == 0:
                        print("      No coincident BarZ endpoints found")
                    elif coincident_count > 3:
                        print("      ... and {} more coincident endpoints".format(coincident_count - 3))
                        
                else:
                    print("    ERROR: Set contains {} RPs (expected 1)".format(len(rp_set.referencePoints)))
                    
            except Exception as e:
                print("    ERROR analyzing {}: {}".format(set_name, e))
        
    except Exception as e:
        print("ERROR during analysis: {}".format(e))

def main():
    """Main function to create RP-Z to BarZ wires."""
    
    print("RP-Z TO BARZ WIRE CREATION SCRIPT")
    print("=" * 40)
    print("Creates wires between RP-Z sets and coincident BarZ endpoints")
    print("One wire per RP-Z, avoiding duplicates")
    print("")
    
    try:
        # Analyze coincidence first (for debugging)
        analyze_rpz_barz_coincidence()
        
        print("")
        
        # Create the wires
        success = create_rpz_to_barz_wires()
        
        # Verify results
        total_wires = verify_rpz_barz_wires()
        
        print("")
        print("=" * 40)
        
        if success and total_wires > 0:
            print("SUCCESS: RP-Z to BarZ wires created!")
            print("- {} wires created between RP-Z sets and BarZ endpoints".format(total_wires))
            print("- Each RP-Z connected to one coincident BarZ endpoint")
            print("- Duplicates avoided using tie-breaking rules")
            print("- Named as WireRPZ_x#_y#_z#")
            print("")
            print("NEXT STEPS:")
            print("1. In Abaqus GUI, select wires named 'WireRPZ_*'")
            print("2. Apply appropriate connector sections")
            print("3. These connections link RP-Z reference points to BarZ bars")
        else:
            print("WARNING: RP-Z to BarZ wire creation issues")
            print("Possible causes:")
            print("- No RP-Z sets found (run script e first)")
            print("- No BarZ instances found (run script a first)")
            print("- No coincident points found (check coordinate precision)")
        
    except Exception as e:
        print("ERROR in main execution: {}".format(e))
        import traceback
        traceback.print_exc()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    main()