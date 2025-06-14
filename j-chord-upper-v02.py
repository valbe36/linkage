from abaqus import *
from abaqusConstants import *
import warnings
import traceback
import part
import assembly
import regionToolset
import mesh
import section
import math

# ChordUpper Script for Grandstand Seating Substructure
# Creates 3D deformable wire elements from (0,0,0) to (0, dy, -dz)
# Same geometry as ChordLower but with +20 y-offset
# Length: approximately 255 cm, partitioned into 3 equal parts
# Cross-section: CHS33e7_t2e5 (already exists in model)

# Basic Setup: Model & Parameters
model_name = 'Model-1'
material_name = 'Steel_355'  # Already exists from script A
section_name = 'CHS33e7_t2e5'  # Already exists in model
part_name = "ChordUpper"

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

# Chord parameters
chord_start = (0.0, 0.0, 0.0)
chord_end = (0.0, dy, -dz)  # (0, 127.5, -221) - same as ChordLower
mesh_size = 0.1
y_offset = 0.20  # Offset in +y direction from ChordLower positions

# Instance pattern parameters
n_instances_x = 7  # 7 rows along x direction (x = 0, 221, 442, 663, 884, 1105, 1326)
n_levels_y = 5     # 5 levels in y direction  
spacing_x = dx     # 221 cm spacing between instances
start_z = 11.05     # Starting z position for first level

# Define overall success flag
overall_success = True

print("=== CHORDUPPER CREATION SCRIPT ===")
print("Creating seating substructure ChordUpper elements")
print("Part geometry: from (0,0,0) to (0,{},{})".format(dy, -dz))
print("Y-offset: +{} from ChordLower positions".format(y_offset))
print("Using standardized coordinate precision system")
print("Length: {:.1f} cm".format(math.sqrt(dy*dy + dz*dz)))
print("Pattern: {} instances x {} levels = {} total instances".format(n_instances_x, n_levels_y, n_instances_x * n_levels_y))

# ====================================================================
# MAIN EXECUTION BLOCK
# ====================================================================

# Access Model and Assembly
try:
    myModel = mdb.models[model_name]
    a = myModel.rootAssembly
    print("Successfully accessed model '{}' and assembly".format(model_name))
except KeyError:
    print("FATAL ERROR: Model '{}' not found. Run script A first.".format(model_name))
    raise
except Exception as e:
    print("FATAL ERROR accessing model/assembly: {}".format(e))
    raise

# Step 1: Verify Cross-Section Exists
print("\nStep 1: Verify Cross-Section for ChordUpper")

def verify_chord_upper_section(model, section_name, material_name):
    """Verify that the ChordUpper cross-section exists."""
    
    # Check if section exists
    if section_name not in model.sections:
        warnings.warn("Section '{}' not found. Run cross-section script first.".format(section_name))
        return False
    else:
        print("  Section '{}' found".format(section_name))
    
    # Check if material exists
    if material_name not in model.materials:
        warnings.warn("Material '{}' not found. Run script A first.".format(material_name))
        return False
    else:
        print("  Material '{}' found".format(material_name))
    
    return True

# Execute Step 1
section_ok = verify_chord_upper_section(myModel, section_name, material_name)
if not section_ok:
    overall_success = False
    warnings.warn("Required cross-section or material not found")

# Step 2: Create ChordUpper Part
print("\nStep 2: Create ChordUpper Part")

def create_chord_upper_part(model, part_name, start_point, end_point):
    """Create ChordUpper part as 3D deformable wire, partitioned into 3 equal segments."""
    
    print("  Creating ChordUpper part: {}".format(part_name))
    
    if part_name in model.parts:
        print("  Part '{}' already exists. Skipping creation.".format(part_name))
        return model.parts[part_name]
    
    try:
        # Create 3D deformable wire part
        p = model.Part(name=part_name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
        
        # Create wire from start to end point
        p.WirePolyLine(points=(start_point, end_point), mergeType=IMPRINT, meshable=ON)
        print("  Wire created from {} to {} (length: {:.1f} cm)".format(start_point, end_point, math.sqrt(dy*dy + dz*dz)))
        
        # Partition into 3 equal segments
        print("  Partitioning into 3 equal segments...")
        try:
            if not p.edges:
                raise ValueError("Part has no edges after WirePolyLine")

            initial_edge = p.edges[0]
            
            # First partition at 1/3 point
            p.PartitionEdgeByParam(edges=(initial_edge,), parameter=1.0/3.0)
            
            # Second partition at 2/3 point
            if len(p.edges) >= 2:
                p.PartitionEdgeByParam(edges=(p.edges[1],), parameter=0.5)
            else:
                warnings.warn("Could not find second edge for partitioning")

            print("  Successfully partitioned into 3 segments")
            
        except Exception as e_part:
            warnings.warn("Error during partitioning: {}".format(e_part))

        return p
        
    except Exception as e:
        warnings.warn("Failed to create ChordUpper part '{}': {}".format(part_name, e))
        raise

# Create the ChordUpper part
try:
    chord_upper_part = create_chord_upper_part(myModel, part_name, chord_start, chord_end)
    print("  ChordUpper part created successfully")
except Exception as e:
    overall_success = False
    print("  Failed to create ChordUpper part: {}".format(e))
    chord_upper_part = None

# Step 3: Assign Section and Orientation
print("\nStep 3: Assign Section and Orientation to ChordUpper")

def assign_section_and_orientation(model, part_name, section_name):
    """Assign beam section and orientation to ChordUpper part."""
    
    if part_name not in model.parts:
        warnings.warn("Part '{}' not found for section assignment".format(part_name))
        return False
    
    success = True
    part = model.parts[part_name]
    
    try:
        # Assign section
        print("  Assigning section '{}' to part '{}'".format(section_name, part_name))
        all_edges = part.edges
        if not all_edges:
            warnings.warn("No edges found in part '{}'".format(part_name))
            return False
            
        region = regionToolset.Region(edges=all_edges)
        part.SectionAssignment(
            region=region, 
            sectionName=section_name, 
            offset=0.0,
            offsetType=MIDDLE_SURFACE, 
            offsetField='',
            thicknessAssignment=FROM_SECTION
        )
        print("  Section assigned successfully")
        
        # Assign beam orientation (default - n1 vector along negative global Z)
        print("  Assigning beam orientation...")
        n1_direction = (0.0, 0.0, -1.0)
        part.assignBeamSectionOrientation(
            method=N1_COSINES, 
            n1=n1_direction, 
            region=region
        )
        print("  Beam orientation assigned (n1={})".format(n1_direction))
        
    except Exception as e:
        warnings.warn("Failed to assign section/orientation to '{}': {}".format(part_name, e))
        success = False
    
    return success

# Execute Step 3
if chord_upper_part:
    section_assign_ok = assign_section_and_orientation(myModel, part_name, section_name)
    if not section_assign_ok:
        overall_success = False
        warnings.warn("Failed to assign section/orientation to ChordUpper")

# Step 4: Mesh ChordUpper Part
print("\nStep 4: Mesh ChordUpper Part")

def mesh_chord_upper_part(model, part_name, seed_size):
    """Mesh the ChordUpper part with specified seed size."""
    
    if part_name not in model.parts:
        warnings.warn("Part '{}' not found for meshing".format(part_name))
        return False
    
    try:
        part = model.parts[part_name]
        
        # Set seed size
        print("  Seeding part '{}' with size {}".format(part_name, seed_size))
        part.seedPart(size=seed_size, deviationFactor=0.1, minSizeFactor=0.1)
        
        # Set element type (B31 - 2-node linear beam)
        print("  Setting element type to B31...")
        elemType = mesh.ElemType(elemCode=B31, elemLibrary=STANDARD)
        all_edges = part.edges
        
        if not all_edges:
            warnings.warn("No edges found for element type assignment")
            return False
            
        region = regionToolset.Region(edges=all_edges)
        part.setElementType(regions=region, elemTypes=(elemType,))
        
        # Generate mesh
        print("  Generating mesh...")
        part.generateMesh()
        print("  ChordUpper part meshed successfully")
        
        return True
        
    except Exception as e:
        warnings.warn("Failed to mesh ChordUpper part '{}': {}".format(part_name, e))
        return False

# Execute Step 4
if chord_upper_part:
    mesh_ok = mesh_chord_upper_part(myModel, part_name, mesh_size)
    if not mesh_ok:
        overall_success = False
        warnings.warn("Failed to mesh ChordUpper part")

# Step 5: Create ChordUpper Instances with Standardized Coordinates
print("\nStep 5: Create ChordUpper Instances with Standardized Coordinates")

def create_chord_upper_instances_standardized(assembly_obj, model_obj, part_name, n_instances_x, n_levels_y, spacing_x, dy, start_z, dz, y_offset):
    """Create instances of ChordUpper using standardized coordinate system with y-offset."""
    
    print("  Creating ChordUpper instances with standardized coordinates...")
    print("  Pattern: {} instances per level, {} levels".format(n_instances_x, n_levels_y))
    print("  Y-offset: +{} from ChordLower positions".format(y_offset))
    print("  Using precise modular coordinate system")
    
    if part_name not in model_obj.parts:
        warnings.warn("Part '{}' not found for instance creation".format(part_name))
        return False
    
    p = model_obj.parts[part_name]
    instances_created = 0
    instances_skipped = 0
    success = True
    
    try:
        for iy in range(n_levels_y):  # Levels: 0, 1, 2, 3, 4
            # Calculate precise positions using modular coordinate system
            y_start_base = (iy + 1) * dy  # Base y position (same as ChordLower)
            y_end_base = (iy + 2) * dy
            
            # Add y-offset for ChordUpper
            y_start = y_start_base + y_offset
            y_end = y_end_base + y_offset
            
            # Z positions (same as ChordLower)
            z_start = start_z - (iy * dz)
            z_end = z_start - dz
            
            # Standardize positions to ensure precision
            y_start = standardize_position((0, y_start, 0))[1]
            y_end = standardize_position((0, y_end, 0))[1]
            z_start = standardize_position((0, 0, z_start))[2]
            z_end = standardize_position((0, 0, z_end))[2]
            
            print("    Level {}: y = {:.6f} to {:.6f}, z = {:.6f} to {:.6f}".format(
                iy + 1, y_start, y_end, z_start, z_end))
            
            for ix in range(n_instances_x):  # Instances: 0, 1, 2, 3, 4, 5, 6
                # Calculate precise x position using modular coordinate system
                x_position = get_exact_modular_coordinate(ix, spacing_x)
                
                # Instance naming following script A pattern
                inst_name = "ChordUpper_x{}_y{}_z{}".format(ix, iy + 1, 0)
                
                if inst_name in assembly_obj.instances:
                    instances_skipped += 1
                    continue
                
                try:
                    # Create instance
                    inst = assembly_obj.Instance(name=inst_name, part=p, dependent=ON)
                    instances_created += 1
                    
                    # Translate to correct position using standardized coordinates
                    translation_vector = standardize_position((x_position, y_start, z_start))
                    inst.translate(vector=translation_vector)
                    
                    if iy < 3 and ix < 3:  # Show details for first few instances
                        print("      Created: {} at ({:.6f}, {:.6f}, {:.6f})".format(
                            inst_name, translation_vector[0], translation_vector[1], translation_vector[2]))
                    
                except Exception as e_inst:
                    warnings.warn("Error creating instance '{}': {}".format(inst_name, e_inst))
                    success = False
                    if inst_name in assembly_obj.instances:
                        try: 
                            del assembly_obj.instances[inst_name]
                        except: 
                            pass
    
    except Exception as e_loop:
        warnings.warn("Error during ChordUpper instance creation: {}".format(e_loop))
        success = False
    
    print("  ChordUpper instances created: {}, skipped: {}".format(instances_created, instances_skipped))
    print("  All instances use standardized coordinate precision")
    
    return success

# Execute Step 5
if chord_upper_part:
    instances_ok = create_chord_upper_instances_standardized(a, myModel, part_name, n_instances_x, n_levels_y, spacing_x, dy, start_z, dz, y_offset)
    if not instances_ok:
        overall_success = False
        warnings.warn("Failed to create ChordUpper instances")

# Step 6: Regenerate Assembly
print("\nStep 6: Regenerating Assembly...")
try:
    a.regenerate()
    print("Assembly regenerated successfully")
except Exception as e:
    warnings.warn("Error regenerating assembly: {}".format(e))
    overall_success = False

# Final Summary
print("\n" + "=" * 60)
print("CHORDUPPER CREATION SUMMARY")
print("=" * 60)

if overall_success:
    print("SUCCESS: ChordUpper elements created successfully!")
    print("SUCCESS: Cross-section: {} (CHS 33.7 x 2.5)".format(section_name))
    print("SUCCESS: Part: {} (3 segments, length approximately 255 cm)".format(part_name))
    print("SUCCESS: Mesh: Element type B31, seed size {}".format(mesh_size))
    print("SUCCESS: Instances: {} x {} = {} total instances".format(n_instances_x, n_levels_y, n_instances_x * n_levels_y))
    print("SUCCESS: Y-offset: +{} from ChordLower positions".format(y_offset))
    print("SUCCESS: Standardized coordinate precision applied")
    print("SUCCESS: All positions calculated using modular coordinate system")
    print("SUCCESS: Position pattern:")
    for iy in range(min(3, n_levels_y)):  # Show first 3 levels
        y_start = (iy + 1) * dy + y_offset
        y_end = (iy + 2) * dy + y_offset
        z_start = start_z - (iy * dz)
        z_end = z_start - dz
        y_start = standardize_position((0, y_start, 0))[1]
        y_end = standardize_position((0, y_end, 0))[1]
        z_start = standardize_position((0, 0, z_start))[2]
        z_end = standardize_position((0, 0, z_end))[2]
        print("    Level {}: y={:.6f} to {:.6f}, z={:.6f} to {:.6f}, x=0 to {:.6f} (7 instances)".format(
            iy + 1, y_start, y_end, z_start, z_end, (n_instances_x - 1) * spacing_x))
    if n_levels_y > 3:
        print("    ... and {} more levels".format(n_levels_y - 3))
    print("\nChordUpper elements ready for connection to other components!")
else:
    print("ERROR: ChordUpper creation completed with errors")
    print("Please review warnings above before proceeding")

print("Script completed. Overall success: {}".format(overall_success))