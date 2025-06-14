# -*- coding: utf-8 -*-
"""
Create RP-Z Surface Sets for Sloped Structure

Creates 3 sets of RP-Z based on their position on the sloped upper surface:
- RP-corner: 4 corner points (0,1,5), (6,1,5), (6,6,0), (0,6,0)
- RP-edge: Points along the 4 edges between corners
- RP-inner: Points inside the plane enclosed by edges and corners

The structure has a sloped surface where:
- Front edge (y=1): z=5
- Back edge (y=6): z=0
- Linear slope between them: z = 6-y
"""

from abaqus import *
from abaqusConstants import *

def create_rpz_surface_sets():
    """
    Create the 3 surface sets: RP-corner, RP-edge, RP-inner.
    """
    
    print("=== CREATING RP-Z SURFACE SETS ===")
    print("Defining sloped upper surface of structure")
    print("Corner points: (0,1,5), (6,1,5), (6,6,0), (0,6,0)")
    print("Surface equation: z = 6-y for points between corners")
    print("")
    
    # Get model and assembly
    try:
        model = mdb.models['Model-1']
        assembly = model.rootAssembly
        print("Successfully accessed model and assembly")
    except Exception as e:
        print("ERROR: Could not access model: {}".format(e))
        return False
    
    # Define the surface geometry
    corner_coords = [
        (0, 1, 5),  # Bottom left corner
        (6, 1, 5),  # Bottom right corner
        (6, 6, 0),  # Top right corner
        (0, 6, 0)   # Top left corner
    ]
    
    print("Corner coordinates: {}".format(corner_coords))
    
    # Find all RP-Z sets and classify them
    rpz_classification = classify_rpz_surface_points(assembly, corner_coords)
    
    # Create the 3 sets
    success = create_surface_sets(assembly, rpz_classification)
    
    # Verify results
    verify_surface_sets(assembly, rpz_classification)
    
    return success

def classify_rpz_surface_points(assembly, corner_coords):
    """Classify all RP-Z points as corner, edge, or inner."""
    
    print("Classifying RP-Z points on sloped surface...")
    
    classification = {
        'corner': [],
        'edge': [],
        'inner': [],
        'off_surface': []
    }
    
    # Convert corner coordinates to set for fast lookup
    corner_set = set(corner_coords)
    
    # Process all RP-Z sets
    for set_name in assembly.sets.keys():
        if set_name.startswith('RP-Z_'):
            coords = extract_coordinates_from_set_name(set_name)
            
            if coords is not None:
                x, y, z = coords
                
                # Check if point is on the sloped surface
                if is_on_sloped_surface(x, y, z):
                    
                    try:
                        rp_set = assembly.sets[set_name]
                        if hasattr(rp_set, 'referencePoints') and len(rp_set.referencePoints) > 0:
                            
                            rpz_info = {
                                'set_name': set_name,
                                'set_object': rp_set,
                                'coords': coords,
                                'rp': rp_set.referencePoints[0]
                            }
                            
                            # Classify the point
                            if coords in corner_set:
                                classification['corner'].append(rpz_info)
                                print("  Corner: {} at ({},{},{})".format(set_name, x, y, z))
                            elif is_on_surface_edge(coords, corner_coords):
                                classification['edge'].append(rpz_info)
                                print("  Edge: {} at ({},{},{})".format(set_name, x, y, z))
                            else:
                                classification['inner'].append(rpz_info)
                                print("  Inner: {} at ({},{},{})".format(set_name, x, y, z))
                    
                    except Exception as e:
                        print("  Warning: Could not access {}: {}".format(set_name, e))
                else:
                    # Point is not on the sloped surface
                    classification['off_surface'].append(set_name)
    
    # Summary
    print("\nClassification summary:")
    print("  Corner points: {}".format(len(classification['corner'])))
    print("  Edge points: {}".format(len(classification['edge'])))
    print("  Inner points: {}".format(len(classification['inner'])))
    print("  Off-surface points: {}".format(len(classification['off_surface'])))
    
    return classification

def is_on_sloped_surface(x, y, z):
    """Check if a point (x,y,z) is on the sloped surface."""
    
    # Surface bounds
    if not (0 <= x <= 6 and 1 <= y <= 6):
        return False
    
    # Calculate expected z for this y position
    # Linear slope: z = 6-y (at y=1, z=5; at y=6, z=0)
    expected_z = 6 - y
    
    # Check if z matches expected value
    return z == expected_z

def is_on_surface_edge(coords, corner_coords):
    """Check if a point lies on any of the 4 surface edges."""
    
    x, y, z = coords
    
    # Define the 4 edges
    edges = [
        # Edge 1: (0,1,5) to (6,1,5) - bottom edge (constant y=1, z=5)
        {'type': 'bottom', 'condition': lambda px, py, pz: py == 1 and pz == 5 and 0 < px < 6},
        
        # Edge 2: (6,1,5) to (6,6,0) - right edge (constant x=6, z=6-y)
        {'type': 'right', 'condition': lambda px, py, pz: px == 6 and pz == 6-py and 1 < py < 6},
        
        # Edge 3: (6,6,0) to (0,6,0) - top edge (constant y=6, z=0)
        {'type': 'top', 'condition': lambda px, py, pz: py == 6 and pz == 0 and 0 < px < 6},
        
        # Edge 4: (0,6,0) to (0,1,5) - left edge (constant x=0, z=6-y)
        {'type': 'left', 'condition': lambda px, py, pz: px == 0 and pz == 6-py and 1 < py < 6}
    ]
    
    # Check if point lies on any edge
    for edge in edges:
        if edge['condition'](x, y, z):
            return True
    
    return False

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

def create_surface_sets(assembly, classification):
    """Create the 3 surface sets."""
    
    print("\nCreating surface sets...")
    
    set_definitions = [
        ('RP-corner', classification['corner'], 'Corner points of sloped surface'),
        ('RP-edge', classification['edge'], 'Edge points of sloped surface'),
        ('RP-inner', classification['inner'], 'Inner points of sloped surface')
    ]
    
    sets_created = 0
    
    for set_name, rpz_list, description in set_definitions:
        
        if len(rpz_list) > 0:
            try:
                # Remove existing set
                if set_name in assembly.sets:
                    print("  Removing existing set: {}".format(set_name))
                    del assembly.sets[set_name]
                
                # Collect RPs
                rps_for_set = []
                for rpz_info in rpz_list:
                    rps_for_set.append(rpz_info['rp'])
                
                # Create the set
                assembly.Set(referencePoints=tuple(rps_for_set), name=set_name)
                sets_created += 1
                
                print("  Created set '{}': {} RPs ({})".format(set_name, len(rps_for_set), description))
                
                # Show coordinate details
                if set_name == 'RP-corner':
                    print("    Corner coordinates:")
                    for rpz_info in rpz_list:
                        x, y, z = rpz_info['coords']
                        print("      - {} at ({},{},{})".format(rpz_info['set_name'], x, y, z))
                
                elif len(rpz_list) <= 10:
                    print("    Coordinates:")
                    for rpz_info in rpz_list:
                        x, y, z = rpz_info['coords']
                        print("      - {} at ({},{},{})".format(rpz_info['set_name'], x, y, z))
                else:
                    print("    Examples:")
                    for rpz_info in rpz_list[:5]:
                        x, y, z = rpz_info['coords']
                        print("      - {} at ({},{},{})".format(rpz_info['set_name'], x, y, z))
                    print("      ... and {} more".format(len(rpz_list) - 5))
                
            except Exception as e:
                print("  ERROR creating set '{}': {}".format(set_name, e))
        else:
            print("  No points found for set '{}' - not created".format(set_name))
    
    return sets_created == 3

def verify_surface_sets(assembly, classification):
    """Verify the created surface sets."""
    
    print("\n=== VERIFICATION ===")
    
    set_names = ['RP-corner', 'RP-edge', 'RP-inner']
    
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
    
    # Show surface coverage
    total_surface_points = len(classification['corner']) + len(classification['edge']) + len(classification['inner'])
    
    print("\nSurface coverage:")
    print("  Total points on sloped surface: {}".format(total_surface_points))
    
    if total_surface_points > 0:
        corner_pct = (len(classification['corner']) * 100.0) / total_surface_points
        edge_pct = (len(classification['edge']) * 100.0) / total_surface_points  
        inner_pct = (len(classification['inner']) * 100.0) / total_surface_points
        
        print("  Corner points: {} ({:.1f}%)".format(len(classification['corner']), corner_pct))
        print("  Edge points: {} ({:.1f}%)".format(len(classification['edge']), edge_pct))
        print("  Inner points: {} ({:.1f}%)".format(len(classification['inner']), inner_pct))

def show_surface_geometry():
    """Show information about the sloped surface geometry."""
    
    print("\n=== SURFACE GEOMETRY ===")
    print("Sloped surface definition:")
    print("  Corner 1: (0,1,5) - Bottom left")
    print("  Corner 2: (6,1,5) - Bottom right") 
    print("  Corner 3: (6,6,0) - Top right")
    print("  Corner 4: (0,6,0) - Top left")
    print("")
    print("Surface equation: z = 6-y")
    print("  At y=1: z=5 (front edge)")
    print("  At y=6: z=0 (back edge)")
    print("")
    print("Edge definitions:")
    print("  Bottom edge: y=1, z=5, x=0 to 6")
    print("  Right edge: x=6, z=6-y, y=1 to 6")
    print("  Top edge: y=6, z=0, x=0 to 6")
    print("  Left edge: x=0, z=6-y, y=1 to 6")
    print("")
    print("Usage:")
    print("  RP-corner: Critical load points at structure corners")
    print("  RP-edge: Important load points along structure edges")
    print("  RP-inner: Standard load points on interior surface")

def main():
    """Main function to create RP-Z surface sets."""
    
    print("RP-Z SURFACE SETS CREATOR")
    print("=" * 30)
    print("Creates 3 sets defining the sloped upper surface")
    print("")
    
    try:
        # Show surface geometry
        show_surface_geometry()
        
        print("")
        
        # Create the sets
        success = create_rpz_surface_sets()
        
        print("")
        print("=" * 30)
        
        if success:
            print("SUCCESS: RP-Z surface sets created!")
            print("Sets created:")
            print("- RP-corner: 4 corner points of sloped surface")
            print("- RP-edge: Points along the 4 edges")
            print("- RP-inner: Points inside the surface plane")
            print("")
            print("These sets define the complete sloped upper surface")
            print("Ready for load application and boundary conditions!")
        else:
            print("WARNING: RP-Z surface set creation issues")
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