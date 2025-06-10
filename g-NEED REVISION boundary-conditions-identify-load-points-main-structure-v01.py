from abaqus import *
from abaqusConstants import *

def apply_loads_to_sloped_top_surface():
    """
    Apply loads to the sloped top surface using direct RP set names.
    Corners: A:RP_x6_y1_z5, B:RP_x0_y1_z5, C:RP_x6_y6_z0, D:RP_x0_y6_z0
    """
    
    # Get model and assembly references
    model = mdb.models['Model-1']
    assembly = model.rootAssembly
    
    print("=== LOAD APPLICATION TO SLOPED TOP SURFACE ===")
    
    # Step 1: Define the four corners using actual RP set names
    corner_sets = {
        'A': 'RP_x6_y1_z5',  # (6,1,5)
        'B': 'RP_x0_y1_z5',  # (0,1,5) 
        'C': 'RP_x6_y6_z0',  # (6,6,0)
        'D': 'RP_x0_y6_z0'   # (0,6,0)
    }
    
    corner_coords = {
        'A': (6, 1, 5),
        'B': (0, 1, 5),
        'C': (6, 6, 0), 
        'D': (0, 6, 0)
    }
    
    print("Corner RP sets:")
    for corner_name, set_name in corner_sets.items():
        coord = corner_coords[corner_name]
        print("  {}: {} at {}".format(corner_name, set_name, coord))
    
    # Step 2: Find all RP sets on the sloped surface
    surface_rp_sets = find_surface_rp_sets(assembly, corner_coords)
    
    # Step 3: Classify RP sets
    corner_rp_sets, edge_rp_sets, internal_rp_sets = classify_surface_rp_sets(
        surface_rp_sets, corner_sets, corner_coords)
    
    # Step 4: Create load sets and apply loads
    create_load_sets_from_names(assembly, corner_rp_sets, edge_rp_sets, internal_rp_sets)
    apply_load_case_1(model, assembly)
    
    print("Load application completed!")

def find_surface_rp_sets(assembly, corner_coords):
    """Find all RP sets that lie on the sloped plane defined by corners."""
    
    print("Finding RP sets on sloped surface...")
    
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
    
    # The plane is defined by corners: A(6,1,5), B(0,1,5), C(6,6,0), D(0,6,0)
    # The plane equation can be derived, but it's easier to check ranges and interpolation
    
    for mod_x, mod_y, mod_z, set_name in all_rp_sets:
        if is_on_sloped_surface(mod_x, mod_y, mod_z, corner_coords):
            surface_rp_sets.append((mod_x, mod_y, mod_z, set_name))
            print("  Surface RP: {} at ({},{},{})".format(set_name, mod_x, mod_y, mod_z))
    
    print("Total RP sets on sloped surface: {}".format(len(surface_rp_sets)))
    return surface_rp_sets

def is_on_sloped_surface(x, y, z, corner_coords):
    """Check if point (x,y,z) lies on the sloped plane."""
    
    # Extract corner coordinates
    ax, ay, az = corner_coords['A']  # (6,1,5)
    bx, by, bz = corner_coords['B']  # (0,1,5)
    cx, cy, cz = corner_coords['C']  # (6,6,0) 
    dx, dy, dz = corner_coords['D']  # (0,6,0)
    
    # The sloped surface has:
    # - At y=1: z goes from 5 (front edge AB)
    # - At y=6: z goes from 0 (back edge CD)
    # - Linear variation in between
    
    # Check if y is within range
    if not (1 <= y <= 6):
        return False
    
    # Check if x is within range
    if not (0 <= x <= 6):
        return False
    
    # For this y position, calculate expected z range using linear interpolation
    y_fraction = float(y - 1) / float(6 - 1)  # 0 at front (y=1), 1 at back (y=6)
    expected_z = 5 - y_fraction * (5 - 0)     # z goes from 5 to 0
    
    # Allow small tolerance
    tolerance = 0.1
    return abs(z - expected_z) < tolerance

def classify_surface_rp_sets(surface_rp_sets, corner_sets, corner_coords):
    """Classify surface RP sets as corners, edges, or internal."""
    
    print("Classifying surface RP sets...")
    
    corner_rp_sets = []
    edge_rp_sets = []
    internal_rp_sets = []
    
    # Extract corner coordinates as tuples for easy comparison
    corner_coord_tuples = [corner_coords[name] for name in ['A', 'B', 'C', 'D']]
    corner_names = ['A', 'B', 'C', 'D']
    
    for mod_x, mod_y, mod_z, set_name in surface_rp_sets:
        coord = (mod_x, mod_y, mod_z)
        
        # Check if it's a corner
        if coord in corner_coord_tuples:
            corner_idx = corner_coord_tuples.index(coord)
            corner_name = corner_names[corner_idx]
            corner_rp_sets.append((set_name, corner_name))
            print("  Corner {}: {}".format(corner_name, set_name))
            
        # Check if it's on an edge
        elif is_on_surface_edge(coord, corner_coords):
            edge_rp_sets.append(set_name)
            print("  Edge RP: {}".format(set_name))
            
        # Otherwise it's internal
        else:
            internal_rp_sets.append(set_name)
            print("  Internal RP: {}".format(set_name))
    
    print("Classification complete:")
    print("  Corners: {}".format(len(corner_rp_sets)))
    print("  Edges: {}".format(len(edge_rp_sets)))
    print("  Internal: {}".format(len(internal_rp_sets)))
    
    return corner_rp_sets, edge_rp_sets, internal_rp_sets

def is_on_surface_edge(point, corner_coords):
    """Check if point lies on any of the four edges: AB, BC, CD, DA."""
    
    x, y, z = point
    tolerance = 0.1
    
    # Edge AB: from A(6,1,5) to B(0,1,5) - constant y=1, z=5, varying x
    if abs(y - 1) < tolerance and abs(z - 5) < tolerance:
        if 0 <= x <= 6:
            return True

    # Edge BD: from B(0,1,5) to D(0,6,0) - constant x=0, varying y,z  
    if abs(x - 0) < tolerance:
        if 1 <= y <= 6:
            # Linear interpolation for z: at y=1, z=5; at y=6, z=0
            expected_z = 5 - (y - 1) / (6 - 1) * (5 - 0)
            if abs(z - expected_z) < tolerance:
                return True

    # Edge DC: from D(0,6,0) to C(6,6,0) - constant y=6, z=0, varying x
    if abs(y - 6) < tolerance and abs(z - 0) < tolerance:
        if 0 <= x <= 6:
            return True

    # Edge CA: from C(6,6,0) to A(6,1,5) - constant x=6, varying y,z
    if abs(x - 6) < tolerance:
        if 1 <= y <= 6:
            # Linear interpolation for z: at y=6, z=0; at y=1, z=5  
            expected_z = 0 + (1 - y) / (1 - 6) * (5 - 0)
            # Simplified: expected_z = (5 - y) 
            expected_z = 5 - y
            if abs(z - expected_z) < tolerance:
                return True
    
    return False

def create_load_sets_from_names(assembly, corner_rp_sets, edge_rp_sets, internal_rp_sets):
    """Create load sets using RP set names."""
    
    print("Creating load application sets...")
    
    # Create corner set
    if corner_rp_sets:
        corner_rps = []
        for set_name, corner_name in corner_rp_sets:
            if set_name in assembly.sets:
                rp_set = assembly.sets[set_name]
                if hasattr(rp_set, 'referencePoints'):
                    corner_rps.extend(rp_set.referencePoints)
        
        if corner_rps:
            try:
                assembly.Set(referencePoints=tuple(corner_rps), name='LoadSet_Corners')
                print("  Created corner set with {} RPs".format(len(corner_rps)))
            except Exception as e:
                print("  Error creating corner set: {}".format(e))
    
    # Create edge set
    if edge_rp_sets:
        edge_rps = []
        for set_name in edge_rp_sets:
            if set_name in assembly.sets:
                rp_set = assembly.sets[set_name]
                if hasattr(rp_set, 'referencePoints'):
                    edge_rps.extend(rp_set.referencePoints)
        
        if edge_rps:
            try:
                assembly.Set(referencePoints=tuple(edge_rps), name='LoadSet_Edges')
                print("  Created edge set with {} RPs".format(len(edge_rps)))
            except Exception as e:
                print("  Error creating edge set: {}".format(e))
    
    # Create internal set
    if internal_rp_sets:
        internal_rps = []
        for set_name in internal_rp_sets:
            if set_name in assembly.sets:
                rp_set = assembly.sets[set_name]
                if hasattr(rp_set, 'referencePoints'):
                    internal_rps.extend(rp_set.referencePoints)
        
        if internal_rps:
            try:
                assembly.Set(referencePoints=tuple(internal_rps), name='LoadSet_Internal')
                print("  Created internal set with {} RPs".format(len(internal_rps)))
            except Exception as e:
                print("  Error creating internal set: {}".format(e))

def apply_load_case_1(model, assembly):
    """Apply Load Case 1: Uniform distributed load on sloped surface."""
    
    print("Applying Load Case 1 to sloped surface...")
    
    # Define load magnitudes (N) - negative = downward
    corner_load = -2000.0    # Higher load at corners
    edge_load = -1500.0      # Medium load at edges  
    internal_load = -1000.0  # Lower load at internal points
    
    # Create step for loads
    step_name = 'LoadCase1_Sloped'
    if step_name not in model.steps:
        model.StaticStep(name=step_name, previous='Initial', 
                        description='Load Case 1: Uniform load on sloped surface')
    
    # Apply loads to corners
    if 'LoadSet_Corners' in assembly.sets:
        try:
            model.ConcentratedForce(
                name='Load_Corners_LC1',
                createStepName=step_name,
                region=assembly.sets['LoadSet_Corners'],
                cf2=corner_load,
                distributionType=UNIFORM
            )
            print("  Applied corner loads: {} N per RP".format(corner_load))
        except Exception as e:
            print("  Error applying corner loads: {}".format(e))
    
    # Apply loads to edges
    if 'LoadSet_Edges' in assembly.sets:
        try:
            model.ConcentratedForce(
                name='Load_Edges_LC1',
                createStepName=step_name,
                region=assembly.sets['LoadSet_Edges'],
                cf2=edge_load,
                distributionType=UNIFORM
            )
            print("  Applied edge loads: {} N per RP".format(edge_load))
        except Exception as e:
            print("  Error applying edge loads: {}".format(e))
    
    # Apply loads to internal points
    if 'LoadSet_Internal' in assembly.sets:
        try:
            model.ConcentratedForce(
                name='Load_Internal_LC1',
                createStepName=step_name,
                region=assembly.sets['LoadSet_Internal'],
                cf2=internal_load,
                distributionType=UNIFORM
            )
            print("  Applied internal loads: {} N per RP".format(internal_load))
        except Exception as e:
            print("  Error applying internal loads: {}".format(e))

# Main execution
if __name__ == "__main__":
    try:
        apply_loads_to_sloped_top_surface()
        print("\n=== SLOPED SURFACE LOAD APPLICATION SUMMARY ===")
        print("Load Case 1 applied using RP set names!")
        print("Corners: A(6,1,5), B(0,1,5), C(6,6,0), D(0,6,0)")
        print("Edges: AB, BC, CD, DA")
        print("Ready to add more load cases...")
        
    except Exception as e:
        print("Error in load application: {}".format(e))
        import traceback
        traceback.print_exc()