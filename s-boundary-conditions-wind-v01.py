# -*- coding: utf-8 -*-
"""
RP-Z Connectivity Analyzer and Set Creator

Analyzes RP-Z connections to BarX and ChordLower instances and creates sets based on connectivity:
- RPw2: RP-Z that connect to 4 instances (BarX and/or ChordLower)
- RPw1: RP-Z that connect to 3 instances (BarX and/or ChordLower)  
- RPw1/2: RP-Z that connect to 2 instances (BarX and/or ChordLower)

Note: BarZ connections are ignored in the count
"""

from abaqus import *
from abaqusConstants import *
import math

# ============================================================================
# COORDINATE PRECISION SYSTEM - Same as used in other scripts
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

def analyze_rpz_connectivity():
    """
    Main function to analyze RP-Z connectivity and create sets.
    """
    
    print("=== RP-Z CONNECTIVITY ANALYZER ===")
    print("Analyzing RP-Z connections to BarX and ChordLower instances")
    print("Creating sets: RPw2 (4 connections), RPw1 (3 connections), RPw1/2 (2 connections)")
    print("Note: BarZ connections are ignored in the count")
    print("")
    
    # Get model and assembly
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        print("Successfully accessed model and assembly")
    except Exception as e:
        print("ERROR: Could not access model: {}".format(e))
        return False
    
    # Step 1: Find all RP-Z sets
    rpz_sets = find_all_rpz_sets(assembly)
    print("Found {} RP-Z sets".format(len(rpz_sets)))
    
    if len(rpz_sets) == 0:
        print("ERROR: No RP-Z sets found")
        return False
    
    # Step 2: Build endpoint maps for BarX and ChordLower instances
    barx_endpoints = build_barx_endpoint_map(assembly)
    chord_lower_endpoints = build_chord_lower_endpoint_map(assembly)
    
    print("Found {} BarX endpoints".format(len(barx_endpoints)))
    print("Found {} ChordLower endpoints".format(len(chord_lower_endpoints)))
    
    # Step 3: Analyze connectivity for each RP-Z
    connectivity_analysis = analyze_rpz_connections(rpz_sets, barx_endpoints, chord_lower_endpoints)
    
    # Step 4: Create sets based on connectivity
    success = create_connectivity_sets(assembly, connectivity_analysis)
    
    # Step 5: Verify and report results
    verify_connectivity_sets(assembly, connectivity_analysis)
    
    return success

def find_all_rpz_sets(assembly):
    """Find all RP-Z sets and extract their module coordinates."""
    
    rpz_sets = []
    
    for set_name in assembly.sets.keys():
        if set_name.startswith('RP-Z_'):
            try:
                rp_set = assembly.sets[set_name]
                if hasattr(rp_set, 'referencePoints') and len(rp_set.referencePoints) > 0:
                    # Extract module coordinates from set name
                    coords = extract_coordinates_from_set_name(set_name)
                    if coords is not None:
                        # Calculate exact position
                        position = get_modular_position(coords[0], coords[1], coords[2])
                        position = standardize_position(position)
                        
                        rpz_sets.append({
                            'set_name': set_name,
                            'set_object': rp_set,
                            'module_coords': coords,
                            'position': position,
                            'rp': rp_set.referencePoints[0]
                        })
            except Exception as e:
                print("  Warning: Could not process RP-Z set '{}': {}".format(set_name, e))
                continue
    
    return rpz_sets

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

def build_barx_endpoint_map(assembly):
    """Build a map of all BarX endpoints."""
    
    barx_endpoints = []
    
    for inst_name, inst in assembly.instances.items():
        if inst_name.startswith('BarX-'):
            try:
                vertices = inst.vertices
                
                if len(vertices) >= 2:
                    # Get start and end vertices
                    start_vertex = vertices[0]
                    end_vertex = vertices[-1]
                    
                    start_pos = standardize_position(start_vertex.pointOn[0])
                    end_pos = standardize_position(end_vertex.pointOn[0])
                    
                    barx_endpoints.append({
                        'instance_name': inst_name,
                        'position': start_pos,
                        'endpoint_type': 'start'
                    })
                    
                    barx_endpoints.append({
                        'instance_name': inst_name,
                        'position': end_pos,
                        'endpoint_type': 'end'
                    })
                    
            except Exception as e:
                print("  Warning: Could not process BarX instance '{}': {}".format(inst_name, e))
                continue
    
    return barx_endpoints

def build_chord_lower_endpoint_map(assembly):
    """Build a map of all ChordLower endpoints."""
    
    chord_lower_endpoints = []
    
    for inst_name, inst in assembly.instances.items():
        if inst_name.startswith('ChordLower_'):
            try:
                vertices = inst.vertices
                
                if len(vertices) >= 2:
                    # Get start and end vertices
                    start_vertex = vertices[0]
                    end_vertex = vertices[-1]
                    
                    start_pos = standardize_position(start_vertex.pointOn[0])
                    end_pos = standardize_position(end_vertex.pointOn[0])
                    
                    chord_lower_endpoints.append({
                        'instance_name': inst_name,
                        'position': start_pos,
                        'endpoint_type': 'start'
                    })
                    
                    chord_lower_endpoints.append({
                        'instance_name': inst_name,
                        'position': end_pos,
                        'endpoint_type': 'end'
                    })
                    
            except Exception as e:
                print("  Warning: Could not process ChordLower instance '{}': {}".format(inst_name, e))
                continue
    
    return chord_lower_endpoints

def analyze_rpz_connections(rpz_sets, barx_endpoints, chord_lower_endpoints):
    """Analyze connections for each RP-Z set."""
    
    print("\nAnalyzing RP-Z connectivity...")
    
    connectivity_analysis = {
        4: [],  # 4 connections -> RPw2
        3: [],  # 3 connections -> RPw1  
        2: [],  # 2 connections -> RPw1/2
        1: [],  # 1 connection (for information)
        0: []   # 0 connections (for information)
    }
    
    tolerance = 0.01
    
    for i, rpz_info in enumerate(rpz_sets):
        
        if i < 10:  # Show details for first 10
            print("  Analyzing {}: {}".format(i+1, rpz_info['set_name']))
        elif i == 10:
            print("  ... analyzing remaining {} RP-Z sets ...".format(len(rpz_sets) - 10))
        
        rpz_position = rpz_info['position']
        connections = []
        
        # Check BarX connections
        for barx_endpoint in barx_endpoints:
            if positions_are_coincident(rpz_position, barx_endpoint['position'], tolerance):
                connections.append({
                    'type': 'BarX',
                    'instance': barx_endpoint['instance_name'],
                    'endpoint': barx_endpoint['endpoint_type']
                })
        
        # Check ChordLower connections
        for chord_endpoint in chord_lower_endpoints:
            if positions_are_coincident(rpz_position, chord_endpoint['position'], tolerance):
                connections.append({
                    'type': 'ChordLower',
                    'instance': chord_endpoint['instance_name'],
                    'endpoint': chord_endpoint['endpoint_type']
                })
        
        # Store analysis results
        connection_count = len(connections)
        rpz_info['connections'] = connections
        rpz_info['connection_count'] = connection_count
        
        # Add to appropriate category
        if connection_count in connectivity_analysis:
            connectivity_analysis[connection_count].append(rpz_info)
        else:
            # Handle unexpected connection counts
            if connection_count not in connectivity_analysis:
                connectivity_analysis[connection_count] = []
            connectivity_analysis[connection_count].append(rpz_info)
        
        if i < 10:  # Show details for first 10
            print("    Position: ({:.6f}, {:.6f}, {:.6f})".format(*rpz_position))
            print("    Connections: {} (BarX and ChordLower only)".format(connection_count))
            for conn in connections[:3]:  # Show first 3 connections
                print("      - {} {} {}".format(conn['type'], conn['instance'], conn['endpoint']))
            if len(connections) > 3:
                print("      ... and {} more".format(len(connections) - 3))
    
    # Summary
    print("\nConnectivity Summary:")
    for count in sorted(connectivity_analysis.keys(), reverse=True):
        if len(connectivity_analysis[count]) > 0:
            print("  {} connections: {} RP-Z sets".format(count, len(connectivity_analysis[count])))
    
    return connectivity_analysis

def create_connectivity_sets(assembly, connectivity_analysis):
    """Create the three connectivity sets: RPw2, RPw1, RPw1/2."""
    
    print("\nCreating connectivity sets...")
    
    # Define set mappings
    set_definitions = [
        (4, 'RPw2', '4 connections (highest connectivity)'),
        (3, 'RPw1', '3 connections (medium connectivity)'), 
        (2, 'RPw1/2', '2 connections (lower connectivity)')
    ]
    
    sets_created = 0
    
    for connection_count, set_name, description in set_definitions:
        
        rpz_list = connectivity_analysis.get(connection_count, [])
        
        if len(rpz_list) > 0:
            try:
                # Clean up existing set
                if set_name in assembly.sets:
                    print("  Removing existing set: {}".format(set_name))
                    del assembly.sets[set_name]
                
                # Collect RPs from the RP-Z sets
                rps_for_set = []
                for rpz_info in rpz_list:
                    rps_for_set.append(rpz_info['rp'])
                
                # Create the set
                assembly.Set(referencePoints=tuple(rps_for_set), name=set_name)
                sets_created += 1
                
                print("  Created set '{}': {} RPs ({})".format(set_name, len(rps_for_set), description))
                
                # Show examples
                if len(rpz_list) > 0:
                    print("    Examples:")
                    for rpz_info in rpz_list[:3]:
                        print("      - {} (connects to {} instances)".format(
                            rpz_info['set_name'], rpz_info['connection_count']))
                        for conn in rpz_info['connections'][:2]:
                            print("        * {} {} {}".format(conn['type'], conn['instance'], conn['endpoint']))
                    if len(rpz_list) > 3:
                        print("      ... and {} more".format(len(rpz_list) - 3))
                
            except Exception as e:
                print("  ERROR creating set '{}': {}".format(set_name, e))
        else:
            print("  No RP-Z sets found with {} connections - set '{}' not created".format(connection_count, set_name))
    
    return sets_created > 0

def verify_connectivity_sets(assembly, connectivity_analysis):
    """Verify the created connectivity sets."""
    
    print("\n=== VERIFICATION ===")
    
    # Check created sets
    set_names = ['RPw2', 'RPw1', 'RPw1/2']
    
    for set_name in set_names:
        if set_name in assembly.sets:
            try:
                rp_set = assembly.sets[set_name]
                rp_count = len(rp_set.referencePoints)
                print("Set '{}': {} RPs".format(set_name, rp_count))
            except Exception as e:
                print("Set '{}': ERROR reading - {}".format(set_name, e))
        else:
            print("Set '{}': NOT FOUND".format(set_name))
    
    # Show detailed statistics
    print("\nDetailed connectivity statistics:")
    total_rpz = sum(len(rpz_list) for rpz_list in connectivity_analysis.values())
    
    for count in sorted(connectivity_analysis.keys(), reverse=True):
        rpz_count = len(connectivity_analysis[count])
        if rpz_count > 0:
            percentage = (rpz_count * 100.0) / total_rpz if total_rpz > 0 else 0
            print("  {} connections: {} RP-Z sets ({:.1f}%)".format(count, rpz_count, percentage))
    
    print("  Total RP-Z sets analyzed: {}".format(total_rpz))

def show_connectivity_examples():
    """Show examples of high connectivity RP-Z sets."""
    
    print("\n=== CONNECTIVITY EXAMPLES ===")
    
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        
        # Check if sets exist and show examples
        for set_name in ['RPw2', 'RPw1', 'RPw1/2']:
            if set_name in assembly.sets:
                print("\n{} examples:".format(set_name))
                rp_set = assembly.sets[set_name]
                print("  Total RPs in set: {}".format(len(rp_set.referencePoints)))
                print("  These RP-Z connect to multiple BarX and/or ChordLower instances")
                print("  Use in load application for areas with high structural interaction")
            else:
                print("\n{}: Not found".format(set_name))
    
    except Exception as e:
        print("Error showing examples: {}".format(e))

def main():
    """Main function to analyze RP-Z connectivity."""
    
    print("RP-Z CONNECTIVITY ANALYZER")
    print("=" * 40)
    print("Analyzes RP-Z connections to BarX and ChordLower instances")
    print("Creates sets based on connectivity count (ignoring BarZ)")
    print("")
    
    try:
        # Analyze connectivity and create sets
        success = analyze_rpz_connectivity()
        
        # Show examples
        show_connectivity_examples()
        
        print("")
        print("=" * 40)
        
        if success:
            print("SUCCESS: RP-Z connectivity analysis completed!")
            print("Sets created based on BarX + ChordLower connections:")
            print("- RPw2: RP-Z with 4 connections (highest connectivity)")
            print("- RPw1: RP-Z with 3 connections (medium connectivity)")
            print("- RPw1/2: RP-Z with 2 connections (lower connectivity)")
            print("")
            print("USAGE:")
            print("- Use RPw2 for critical load points (high structural interaction)")
            print("- Use RPw1 for important load points (medium structural interaction)")
            print("- Use RPw1/2 for standard load points (basic structural interaction)")
            print("- BarZ connections ignored as requested")
        else:
            print("WARNING: RP-Z connectivity analysis issues")
            print("Check that RP-Z sets, BarX instances, and ChordLower instances exist")
        
    except Exception as e:
        print("ERROR in main execution: {}".format(e))
        import traceback
        traceback.print_exc()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    main()