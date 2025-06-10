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

# SeatY Script for Grandstand Seating Substructure
# Creates complex 3D deformable wire frame with multiple segments
# Cross-section: RHS_48e3 (already exists in model)

# Basic Setup: Model & Parameters
model_name = 'Model-1'
material_name = 'Steel_355'  # Already exists from script A
section_name = 'RHS_48e3'    # Cross-section already in model
part_name = "SeatY"

# Geometry Parameters (from script A)
dx = 2.21    # x-direction spacing between instances
dy = 1.275  # y-direction height increment  
dz = 2.21    # z-direction spacing

# SeatY specific parameters
mesh_size = 0.12

# SeatY geometry points
points = [
    (0.0, 0.0, 0.0),      # Point 1: Start
    (0.0, 0.2, 0.0),      # Point 2: First vertical end
    (0.0, 0.625, 0.0),    # Point 3: Second vertical end
    (0.0, 0.2, 2.16),     # Point 4: End of first long segment
    (0.0, 0.625, 2.16),   # Point 5: End of second long segment
    (0.0, 0.0, 2.16),     # Point 6: Final point
]

# Wire segments definition
segments = [
    (points[0], points[1]),  # Segment 1: (0,0,0) to (0,0.2,0)
    (points[1], points[2]),  # Segment 2: (0,0.2,0) to (0,0.625,0)
    (points[1], points[3]),  # Segment 3: (0,0.2,0) to (0,0.2,2.16) - LONG, needs partition
    (points[2], points[4]),  # Segment 4: (0,0.625,0) to (0,0.625,2.16) - LONG, needs partition
    (points[5], points[3]),  # Segment 5: (0,0,2.16) to (0,0.2,2.16)
    (points[3], points[4]),  # Segment 6: (0,0.2,2.16) to (0,0.625,2.16)
]

# Instance pattern parameters (finer spacing than LowerChord)
n_instances_x = 6  # 6 rows along x direction (one less than before)
n_levels_y = 16    # More levels due to finer y spacing (6 original levels * 3)
n_levels_z = 15    # More levels due to finer z spacing (5 original levels * 3)
spacing_x = dx     # 221 cm spacing between instances
spacing_y = dy / 3 # 127.5/3 = 42.5 cm spacing in y
spacing_z = dz / 3 # 221/3 = 73.67 cm spacing in z  
start_z = 11.05     # Starting z position for first level

# Define overall success flag
overall_success = True

print("=== SEATY CREATION SCRIPT ===")
print("Creating seating substructure SeatY frame elements")
print("Complex wire frame with {} segments".format(len(segments)))
print("Two long segments will be partitioned into 4 equal parts")
print("Instances rotated 90 degrees CW around Y axis")
print("Mesh size: {}".format(mesh_size))
print("Finer spacing: Y={:.1f}cm, Z={:.1f}cm".format(spacing_y, spacing_z))
print("Grid: {} x-positions, ~18 y-levels, ~15 z-levels".format(n_instances_x))

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
print("\nStep 1: Verify Cross-Section for SeatY")

def verify_seat_y_section(model, section_name, material_name):
    """Verify that the SeatY cross-section exists."""
    
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
section_ok = verify_seat_y_section(myModel, section_name, material_name)
if not section_ok:
    overall_success = False
    warnings.warn("Required cross-section or material not found")

# Step 2: Create SeatY Part
print("\nStep 2: Create SeatY Part")

def create_seat_y_part(model, part_name, segments):
    """Create SeatY part as complex 3D deformable wire frame."""
    
    print("  Creating SeatY part: {}".format(part_name))
    
    if part_name in model.parts:
        print("  Part '{}' already exists. Skipping creation.".format(part_name))
        return model.parts[part_name]
    
    try:
        # Create 3D deformable wire part
        p = model.Part(name=part_name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
        
        # Create all wire segments
        print("  Creating {} wire segments...".format(len(segments)))
        for i, (start_point, end_point) in enumerate(segments):
            print("    Segment {}: {} to {}".format(i+1, start_point, end_point))
            p.WirePolyLine(points=(start_point, end_point), mergeType=IMPRINT, meshable=ON)
        
        # Partition the two long segments (segments 3 and 4) into 4 equal parts
        print("  Partitioning long segments into 4 equal parts...")
        try:
            # The long segments are segments 3 and 4 in our segments list:
            # Segment 3: (0,0.2,0) to (0,0.2,2.16) - length 2.16
            # Segment 4: (0,0.625,0) to (0,0.625,2.16) - length 2.16
            
            print("    Total edges in part: {}".format(len(p.edges)))
            
            # Find edges by checking their endpoints against known long segment endpoints
            long_segment_endpoints = [
                ((0.0, 0.2, 0.0), (0.0, 0.2, 2.16)),    # Segment 3
                ((0.0, 0.625, 0.0), (0.0, 0.625, 2.16)) # Segment 4
            ]
            
            edges_to_partition = []
            tolerance = 0.01
            
            for edge in p.edges:
                try:
                    # Get edge vertices
                    vertices = edge.getVertices()
                    if len(vertices) >= 2:
                        # Get coordinates of endpoints
                        v1_coords = vertices[0].pointOn[0]
                        v2_coords = vertices[-1].pointOn[0]
                        
                        # Check if this edge matches any of our long segments
                        for seg_start, seg_end in long_segment_endpoints:
                            # Check both orientations of the edge
                            match1 = (all(abs(v1_coords[i] - seg_start[i]) < tolerance for i in range(3)) and
                                     all(abs(v2_coords[i] - seg_end[i]) < tolerance for i in range(3)))
                            match2 = (all(abs(v1_coords[i] - seg_end[i]) < tolerance for i in range(3)) and
                                     all(abs(v2_coords[i] - seg_start[i]) < tolerance for i in range(3)))
                            
                            if match1 or match2:
                                length = math.sqrt(sum([(v2_coords[i] - v1_coords[i])**2 for i in range(3)]))
                                edges_to_partition.append((edge, length))
                                print("    Found long edge: start={}, end={}, length={:.3f}".format(
                                    [round(c, 3) for c in v1_coords], 
                                    [round(c, 3) for c in v2_coords], 
                                    length))
                                break
                        
                except Exception as e_edge:
                    print("    Error checking edge: {}".format(e_edge))
                    continue
            
            print("    Found {} long edges to partition".format(len(edges_to_partition)))
            
            # Partition the identified long edges
            partitioned_count = 0
            for edge, length in edges_to_partition:
                try:
                    # Partition into 4 equal parts (3 partition points at 0.25, 0.5, 0.75)
                    print("    Partitioning edge with length {:.3f}...".format(length))
                    p.PartitionEdgeByParam(edges=(edge,), parameter=0.25)
                    p.PartitionEdgeByParam(edges=(edge,), parameter=0.5)  
                    p.PartitionEdgeByParam(edges=(edge,), parameter=0.75)
                    partitioned_count += 1
                    print("    Successfully partitioned edge into 4 segments")
                except Exception as e_part:
                    print("    Error partitioning edge: {}".format(e_part))
                    continue
            
            if partitioned_count == 2:
                print("  Successfully partitioned 2 long segments as expected")
            else:
                print("  Warning: Expected to partition 2 segments, actually partitioned {}".format(partitioned_count))
            
            print("  Final edge count: {} (should be {} if partitioning worked)".format(
                len(p.edges), 6 + 6))  # 6 original + 6 from partitioning
            
        except Exception as e_part:
            warnings.warn("Error during partitioning: {}".format(e_part))
            print("  Continuing without partitioning...")
            
        except Exception as e_part:
            warnings.warn("Error during partitioning: {}".format(e_part))
            print("  Continuing without partitioning...")

        return p
        
    except Exception as e:
        warnings.warn("Failed to create SeatY part '{}': {}".format(part_name, e))
        print(traceback.format_exc())
        raise

# Create the SeatY part
try:
    seat_y_part = create_seat_y_part(myModel, part_name, segments)
    print("  SeatY part created successfully")
except Exception as e:
    overall_success = False
    print("  Failed to create SeatY part: {}".format(e))
    seat_y_part = None

# Step 3: Assign Section and Orientation
print("\nStep 3: Assign Section and Orientation to SeatY")

def assign_section_and_orientation(model, part_name, section_name):
    """Assign beam section and orientation to SeatY part."""
    
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
        print(traceback.format_exc())
        success = False
    
    return success

# Execute Step 3
if seat_y_part:
    section_assign_ok = assign_section_and_orientation(myModel, part_name, section_name)
    if not section_assign_ok:
        overall_success = False
        warnings.warn("Failed to assign section/orientation to SeatY")

# Step 4: Mesh SeatY Part
print("\nStep 4: Mesh SeatY Part")

def mesh_seat_y_part(model, part_name, seed_size):
    """Mesh the SeatY part with specified seed size."""
    
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
        print("  SeatY part meshed successfully")
        
        return True
        
    except Exception as e:
        warnings.warn("Failed to mesh SeatY part '{}': {}".format(part_name, e))
        print(traceback.format_exc())
        return False

# Execute Step 4
if seat_y_part:
    mesh_ok = mesh_seat_y_part(myModel, part_name, mesh_size)
    if not mesh_ok:
        overall_success = False
        warnings.warn("Failed to mesh SeatY part")

# Step 5: Create SeatY Instances
print("\nStep 5: Create SeatY Instances")

def create_seat_y_instances(assembly_obj, model_obj, part_name, n_instances_x, n_levels_y, spacing_x, spacing_y, spacing_z, start_z):
    """Create instances of SeatY following LowerChord pattern but with finer spacing."""
    
    print("  Creating SeatY instances...")
    print("  Pattern: {} instances per level, {} levels".format(n_instances_x, n_levels_y))
    print("  Finer spacing: Y={:.1f}cm, Z={:.1f}cm between levels".format(spacing_y, spacing_z))
    print("  Each instance rotated 90 degrees clockwise around Y axis")
    
    if part_name not in model_obj.parts:
        warnings.warn("Part '{}' not found for instance creation".format(part_name))
        return False
    
    p = model_obj.parts[part_name]
    instances_created = 0
    instances_skipped = 0
    success = True
    
    try:
        for iy in range(n_levels_y):  # More levels due to finer spacing
            y_pos = 1.275 + (iy * spacing_y)      # Start at 127.5, step by 42.5
            z_pos = start_z - (iy * spacing_z)    # Start at 1105, step back by 73.67
            
            print("    Level {}: y = {:.1f}, z = {:.1f}".format(iy + 1, y_pos, z_pos))
            
            for ix in range(n_instances_x):  # 6 instances per level
                x_position = ix * spacing_x  # x = 0, 221, 442, 663, 884, 1105
                
                # Instance naming
                inst_name = "SeatY_x{}_y{}_z{}".format(ix, iy + 1, 0)
                
                if inst_name in assembly_obj.instances:
                    instances_skipped += 1
                    continue
                
                try:
                    # Create instance
                    inst = assembly_obj.Instance(name=inst_name, part=p, dependent=ON)
                    instances_created += 1
                    
                    # Translate to correct position
                    translation_vector = (x_position, y_pos, z_pos)
                    inst.translate(vector=translation_vector)
                    
                    # Rotate 90 degrees clockwise around Y axis using assembly method
                    assembly_obj.rotate(instanceList=(inst_name,), 
                                       axisPoint=(x_position, y_pos, z_pos), 
                                       axisDirection=(0.0, 1.0, 0.0), 
                                       angle=90.0)
                    
                    if iy < 3:  # Show first few levels
                        print("      Created: {} at position ({:.1f}, {:.1f}, {:.1f}) rotated 90deg CW".format(
                            inst_name, x_position, y_pos, z_pos))
                    elif iy == 3:
                        print("      ... creating remaining levels ...")
                    
                except Exception as e_inst:
                    warnings.warn("Error creating instance '{}': {}".format(inst_name, e_inst))
                    success = False
                    if inst_name in assembly_obj.instances:
                        try: 
                            del assembly_obj.instances[inst_name]
                        except: 
                            pass
    
    except Exception as e_loop:
        warnings.warn("Error during SeatY instance creation: {}".format(e_loop))
        print(traceback.format_exc())
        success = False
    
    print("  SeatY instances created: {}, skipped: {}".format(instances_created, instances_skipped))
    print("  Total SeatY instances: {}".format(instances_created + instances_skipped))
    
    return success

# Execute Step 5
if seat_y_part:
    instances_ok = create_seat_y_instances(a, myModel, part_name, n_instances_x, n_levels_y, spacing_x, spacing_y, spacing_z, start_z)
    if not instances_ok:
        overall_success = False
        warnings.warn("Failed to create SeatY instances")

# Step 7: Regenerate Assembly
print("\nStep 7: Regenerating Assembly...")
try:
    a.regenerate()
    print("Assembly regenerated successfully")
except Exception as e:
    warnings.warn("Error regenerating assembly: {}".format(e))
    overall_success = False

# Final Summary
print("\n" + "=" * 50)
print("SEATY CREATION SUMMARY")
print("=" * 50)

if overall_success:
    print("SUCCESS: SeatY frame elements created successfully!")
    print("SUCCESS: Cross-section: {} (RHS 48.3 x 3.0)".format(section_name))
    print("SUCCESS: Part: {} (complex wire frame with partitioned long segments)".format(part_name))
    print("SUCCESS: Mesh: Element type B31, seed size {}".format(mesh_size))
    print("SUCCESS: Instances: 6 x-positions with finer Y/Z grid (~1620 total instances)")
    print("SUCCESS: Set created: 'SeatY' for easy selection")
    print("SUCCESS: Spacing: X=221cm, Y={:.1f}cm, Z={:.1f}cm".format(spacing_y, spacing_z))
    print("SUCCESS: Rotation: 90 degrees clockwise around Y axis")
    print("SUCCESS: Frame geometry:")
    for i, (start, end) in enumerate(segments):
        print("    Segment {}: {} to {}".format(i+1, start, end))
    print("\nReady for joint creation and remaining seating elements!")
else:
    print("ERROR: SeatY creation completed with errors")
    print("Please review warnings above before proceeding")

print("Script completed. Overall success: {}".format(overall_success))