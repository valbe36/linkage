# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import regionToolset
import math

def create_grandstand_load_application_sets():
    """
    Create load application sets for the sloped grandstand structure:
    - RP-corner: 4 corner RP sets
    - RP-edge: RP sets on edges (excluding corners)
    - RP-inner: RP sets inside the sloped plane
    - SeatSideEdges: First and last edges of SeatH instances
    - SeatInnerEdges: Middle edges of SeatH instances
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("=== CREATING GRANDSTAND LOAD APPLICATION SETS ===")
    print("")
    
    # Step 1: Create RP corner set
    create_rp_corner_set(assembly)
    
    # Step 2: Find all RP sets on the sloped surface and classify them
    create_rp_edge_and_inner_sets(assembly)
    
    # Step 3: Create SeatH edge sets
    create_seath_edge_sets(assembly, model)
    
    print("")
    print("=== LOAD APPLICATION SETS CREATION COMPLETED ===")
    verify_created_sets(assembly)

def create_rp_corner_set(assembly):
    """Create set containing the 4 corner RP sets."""
    
    print("Step 1: Creating RP-corner set...")
    
    # Define corner RP set names
    corner_rp_set_names = [
        'RP_x6_y1_z5',  # (6,1,5) bottom right corner
        'RP_x0_y1_z5',  # (0,1,5) bottom left corner  
        'RP_x6_y6_z0',  # (6,6,0) top right corner
        'RP_x0_y6_z0'   # (0,6,0) top left corner
    ]
    
    # Collect corner RPs
    corner_rps = []
    found_corners = []
    
    for set_name in corner_rp_set_names:
        if set_name in assembly.sets:
            try:
                rp_set = assembly.sets[set_name]
                if hasattr(rp_set, 'referencePoints'):
                    corner_rps.extend(rp_set.referencePoints)
                    found_corners.append(set_name)
                    print("  Found corner RP set: {}".format(set_name))
            except Exception as e:
                print("  Error accessing RP set {}: {}".format(set_name, e))
        else:
            print("  WARNING: Corner RP set {} not found".format(set_name))
    
    # Create corner set
    if len(corner_rps) > 0:
        try:
            set_name = 'RP-corner'
            if set_name in assembly.sets:
                del assembly.sets[set_name]
            
            assembly.Set(referencePoints=tuple(corner_rps), name=set_name)
            print("  Created '{}' set with {} RPs from {} corner sets".format(set_name, len(corner_rps), len(found_corners)))
            
        except Exception as e:
            print("  Error creating RP-corner set: {}".format(e))
    else:
        print("  ERROR: No corner RPs found")

def create_rp_edge_and_inner_sets(assembly):
    """Find all RP sets on sloped surface and classify as edge or inner."""
    
    print("Step 2: Creating RP-edge and RP-inner sets...")
    
    # Define corner coordinates for the sloped plane
    corner_coords = {
        'A': (6, 1, 5),  # bottom right
        'B': (0, 1, 5),  # bottom left
        'C': (6, 6, 0),  # top right  
        'D': (0, 6, 0)   # top left
    }
    
    # Find all RP sets on the sloped surface
    surface_rp_sets = find_surface_rp_sets(assembly, corner_coords)
    
    # Classify as corner, edge, or inner
    corner_rp_sets, edge_rp_sets, inner_rp_sets = classify_surface_rp_sets(
        surface_rp_sets, corner_coords)
    
    # Create edge set
    if len(edge_rp_sets) > 0:
        edge_rps = []
        for set_name in edge_rp_sets:
            if set_name in assembly.sets:
                try:
                    rp_set = assembly.sets[set_name]
                    if hasattr(rp_set, 'referencePoints'):
                        edge_rps.extend(rp_set.referencePoints)
                except:
                    continue
        
        if len(edge_rps) > 0:
            try:
                set_name = 'RP-edge'
                if set_name in assembly.sets:
                    del assembly.sets[set_name]
                
                assembly.Set(referencePoints=tuple(edge_rps), name=set_name)
                print("  Created '{}' set with {} RPs from {} edge sets".format(set_name, len(edge_rps), len(edge_rp_sets)))
                
            except Exception as e:
                print("  Error creating RP-edge set: {}".format(e))
    
    # Create inner set
    if len(inner_rp_sets) > 0:
        inner_rps = []
        for set_name in inner_rp_sets:
            if set_name in assembly.sets:
                try:
                    rp_set = assembly.sets[set_name]
                    if hasattr(rp_set, 'referencePoints'):
                        inner_rps.extend(rp_set.referencePoints)
                except:
                    continue
        
        if len(inner_rps) > 0:
            try:
                set_name = 'RP-inner'
                if set_name in assembly.sets:
                    del assembly.sets[set_name]
                
                assembly.Set(referencePoints=tuple(inner_rps), name=set_name)
                print("  Created '{}' set with {} RPs from {} inner sets".format(set_name, len(inner_rps), len(inner_rp_sets)))
                
            except Exception as e:
                print("  Error creating RP-inner set: {}".format(e))

def find_surface_rp_sets(assembly, corner_coords):
    """Find all RP sets that lie on the sloped plane defined by corners."""
    
    # Get all modular RP sets
    all_rp_sets = []
    for set_name in assembly.sets.keys():
        if set_name.startswith('RP_x') and '_y' in set_name and '_z' in set_name:
            try:
                parts = set_name.split('_')
                mod_x = int(parts[1][1:])  # Remove 'x'
                mod_y = int(parts[2][1:])  # Remove 'y' 
                mod_z = int(parts[3][1:])  # Remove 'z'
                all_rp_sets.append((mod_x, mod_y, mod_z, set_name))
            except:
                continue
    
    # Check which RP sets lie on the sloped plane
    surface_rp_sets = []
    
    for mod_x, mod_y, mod_z, set_name in all_rp_sets:
        if is_on_sloped_surface(mod_x, mod_y, mod_z, corner_coords):
            surface_rp_sets.append((mod_x, mod_y, mod_z, set_name))
    
    print("  Found {} RP sets on sloped surface".format(len(surface_rp_sets)))
    return surface_rp_sets

def is_on_sloped_surface(x, y, z, corner_coords):
    """Check if point (x,y,z) lies on the sloped plane."""
    
    # The sloped surface has:
    # - At y=1: z goes from 5 (front edge)
    # - At y=6: z goes from 0 (back edge)
    # - Linear variation in between
    
    # Check if y is within range
    if not (1 <= y <= 6):
        return False
    
    # Check if x is within range
    if not (0 <= x <= 6):
        return False
    
    # For this y position, calculate expected z using linear interpolation
    y_fraction = float(y - 1) / float(6 - 1)  # 0 at front (y=1), 1 at back (y=6)
    expected_z = 5 - y_fraction * (5 - 0)     # z goes from 5 to 0
    
    # Allow small tolerance
    tolerance = 0.1
    return abs(z - expected_z) < tolerance

def classify_surface_rp_sets(surface_rp_sets, corner_coords):
    """Classify surface RP sets as corners, edges, or inner."""
    
    corner_rp_sets = []
    edge_rp_sets = []
    inner_rp_sets = []
    
    # Extract corner coordinates as tuples
    corner_coord_tuples = [(6,1,5), (0,1,5), (6,6,0), (0,6,0)]
    
    for mod_x, mod_y, mod_z, set_name in surface_rp_sets:
        coord = (mod_x, mod_y, mod_z)
        
        # Check if it's a corner
        if coord in corner_coord_tuples:
            corner_rp_sets.append(set_name)
            
        # Check if it's on an edge
        elif is_on_surface_edge(coord, corner_coords):
            edge_rp_sets.append(set_name)
            
        # Otherwise it's inner
        else:
            inner_rp_sets.append(set_name)
    
    print("  Classification: {} corners, {} edges, {} inner".format(
        len(corner_rp_sets), len(edge_rp_sets), len(inner_rp_sets)))
    
    return corner_rp_sets, edge_rp_sets, inner_rp_sets

def is_on_surface_edge(point, corner_coords):
    """Check if point lies on any of the four edges: AB, BC, CD, DA."""
    
    x, y, z = point
    tolerance = 0.1
    
    # Edge AB: from (6,1,5) to (0,1,5) - constant y=1, z=5, varying x
    if abs(y - 1) < tolerance and abs(z - 5) < tolerance:
        if 0 <= x <= 6:
            return True

    # Edge BC: from (0,1,5) to (0,6,0) - constant x=0, varying y,z  
    if abs(x - 0) < tolerance:
        if 1 <= y <= 6:
            # Linear interpolation for z: at y=1, z=5; at y=6, z=0
            expected_z = 5 - (y - 1) / (6 - 1) * (5 - 0)
            if abs(z - expected_z) < tolerance:
                return True

    # Edge CD: from (0,6,0) to (6,6,0) - constant y=6, z=0, varying x
    if abs(y - 6) < tolerance and abs(z - 0) < tolerance:
        if 0 <= x <= 6:
            return True

    # Edge DA: from (6,6,0) to (6,1,5) - constant x=6, varying y,z
    if abs(x - 6) < tolerance:
        if 1 <= y <= 6:
            # Linear interpolation for z: at y=6, z=0; at y=1, z=5  
            expected_z = 5 - (y - 1)
            if abs(z - expected_z) < tolerance:
                return True
    
    return False


 

def verify_created_sets(assembly):
    """Verify that all sets were created correctly."""
    
    print("")
    print("=== VERIFICATION OF CREATED SETS ===")
    
    # List of expected sets
    expected_sets = ['RP-corner', 'RP-edge', 'RP-inner']
    
    for set_name in expected_sets:
        if set_name in assembly.sets:
            try:
                set_obj = assembly.sets[set_name]
                
                # Count elements in set
                if hasattr(set_obj, 'referencePoints'):
                    count = len(set_obj.referencePoints)
                    element_type = "RPs"
                elif hasattr(set_obj, 'edges'):
                    count = len(set_obj.edges)
                    element_type = "edges"
                else:
                    count = "unknown"
                    element_type = "elements"
                
                print("SUCCESS {}: {} {}".format(set_name, count, element_type))
                
            except Exception as e:
                print("ERROR {}: Error reading set - {}".format(set_name, e))
        else:
            print("ERROR {}: NOT FOUND".format(set_name))
    
    print("")
    print("USAGE INSTRUCTIONS:")
    print("- RP-corner: Apply high loads at structure corners")
    print("- RP-edge: Apply medium loads along structure edges")  
    print("- RP-inner: Apply standard loads on interior surface")
    print("")


# Main execution
if __name__ == "__main__":
    try:
        create_grandstand_load_application_sets()
        
    except Exception as e:
        print("Error in main execution: {}".format(e))
        import traceback
        traceback.print_exc()