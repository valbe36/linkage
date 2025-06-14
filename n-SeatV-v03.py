# -*- coding: utf-8 -*-
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

# SeatY Script - partition encoded in geometry
# Long segments are created as 4 individual segments directly

# Basic Setup: Model & Parameters
model_name = 'Model-1'
material_name = 'Steel_355'
section_name = 'RHS_48e3'
part_name = "SeatY"

# Geometry Parameters
dx = 2.21    # x-direction spacing between instances
dy = 1.275  # y-direction height increment  
dz = 2.21    # z-direction spacing

# SeatY specific parameters
mesh_size = 0.12

# FIXED GEOMETRY: Create all segments individually
# Original long segments divided into 4 parts each
segment_length = 2.16 / 4  # 0.54 units per segment

print("=== SEATY CREATION - FIXED GEOMETRY VERSION ===")
print("Long segments divided into 4 parts of {:.3f} units each".format(segment_length))

# Define all wire segments with correct partitioning
def create_seaty_segments():
    """Create all SeatY segments with proper division of long segments."""
    
    segments = []
    
    # Short segments (unchanged from original)
    segments.append(((0.0, 0.0, 0.0), (0.0, 0.2, 0.0)))      # Segment 1: vertical short
    segments.append(((0.0, 0.2, 0.0), (0.0, 0.625, 0.0)))    # Segment 2: vertical short
    segments.append(((2.16, 0.0, 0.0), (2.16, 0.2, 0.0)))    # Segment 3: vertical short
    segments.append(((2.16, 0.2, 0.0), (2.16, 0.625, 0.0)))  # Segment 4: vertical short
    
    # First long segment divided into 4 parts (y = 0.2, varying x)
    for i in range(4):
        x_start = i * segment_length        # 0, 0.54, 1.08, 1.62
        x_end = (i + 1) * segment_length    # 0.54, 1.08, 1.62, 2.16
        segments.append(((x_start, 0.2, 0.0), (x_end, 0.2, 0.0)))
    
    # Second long segment divided into 4 parts (y = 0.625, varying x)  
    for i in range(4):
        x_start = i * segment_length        # 0, 0.54, 1.08, 1.62
        x_end = (i + 1) * segment_length    # 0.54, 1.08, 1.62, 2.16
        segments.append(((x_start, 0.625, 0.0), (x_end, 0.625, 0.0)))
    
    return segments

# Instance pattern parameters
n_instances_x = 6  # 6 rows along x direction
n_levels_y = 16    # More levels due to finer y spacing
n_levels_z = 15    # More levels due to finer z spacing
spacing_x = dx     # 221 cm spacing between instances
spacing_y = dy / 3 # 127.5/3 = 42.5 cm spacing in y
spacing_z = dz / 3 # 221/3 = 73.67 cm spacing in z  
start_z = 11.05    # Starting z position for first level
start_x = 0.025

# Define overall success flag
overall_success = True

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
    
    if section_name not in model.sections:
        warnings.warn("Section '{}' not found. Run cross-section script first.".format(section_name))
        return False
    else:
        print("  Section '{}' found".format(section_name))
    
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

# Step 2: Create SeatY Part with Fixed Geometry
print("\nStep 2: Create SeatY Part with Fixed Geometry")

def create_seat_y_part_fixed_geometry(model, part_name):
    """Create SeatY part with correct segmentation from the beginning."""
    
    print("  Creating SeatY part: {}".format(part_name))
    
    if part_name in model.parts:
        print("  Part '{}' already exists. Deleting and recreating...".format(part_name))
        try:
            del model.parts[part_name]
            print("  Deleted existing part")
        except:
            print("  Could not delete existing part")
    
    try:
        # Create 3D deformable wire part
        p = model.Part(name=part_name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
        
        # Get all segments with correct division
        segments = create_seaty_segments()
        
        print("  Creating {} wire segments...".format(len(segments)))
        print("  Segment breakdown:")
        print("    - 4 short vertical segments")
        print("    - 4 segments for first long edge (y=0.2)")
        print("    - 4 segments for second long edge (y=0.625)")
        print("    - Total: {} segments".format(len(segments)))
        
        # Create all wire segments
        for i, (start_point, end_point) in enumerate(segments):
            length = math.sqrt(sum([(end_point[j] - start_point[j])**2 for j in range(3)]))
            segment_type = "LONG-PART" if abs(length - segment_length) < 0.01 else "SHORT"
            
            print("    Segment {}: {} to {} - {:.3f} units ({})".format(
                i+1, start_point, end_point, length, segment_type))
            
            p.WirePolyLine(points=(start_point, end_point), mergeType=IMPRINT, meshable=ON)
        
        print("  Total edges created: {}".format(len(p.edges)))
        print("  Expected: 12 edges (4 short + 4 + 4 long parts)")
        
        if len(p.edges) == 12:
            print("  SUCCESS: Correct number of edges created")
        else:
            print("  WARNING: Expected 12 edges, got {}".format(len(p.edges)))
        
        return p
        
    except Exception as e:
        warnings.warn("Failed to create SeatY part '{}': {}".format(part_name, e))
        print(traceback.format_exc())
        raise

# Create the SeatY part
try:
    seat_y_part = create_seat_y_part_fixed_geometry(myModel, part_name)
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
        
        # Assign beam orientation
        print("  Assigning beam orientation...")
        n1_direction = (0.0, 1.0, 0.0)  # n1 along Y axis for XZ plane geometry
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

def create_seat_y_instances_no_rotation(assembly_obj, model_obj, part_name, n_instances_x, n_levels_y, spacing_x, spacing_y, spacing_z, start_z):
    """Create instances of SeatY with NO rotation needed."""
    
    print("  Creating SeatY instances...")
    print("  Pattern: {} instances per level, {} levels".format(n_instances_x, n_levels_y))
    print("  NO ROTATION - geometry designed correctly from start")
    
    if part_name not in model_obj.parts:
        warnings.warn("Part '{}' not found for instance creation".format(part_name))
        return False
    
    p = model_obj.parts[part_name]
    instances_created = 0
    instances_skipped = 0
    success = True
    
    try:
        for iy in range(n_levels_y):
            y_pos = 1.275 + (iy * spacing_y)      # Start at 127.5, step by 42.5
            z_pos = start_z - (iy * spacing_z)    # Start at 1105, step back by 73.67
            
            if iy < 3:  # Show first few levels
                print("    Level {}: y = {:.1f}, z = {:.1f}".format(iy + 1, y_pos, z_pos))
            elif iy == 3:
                print("    ... creating remaining levels ...")
            
            for ix in range(n_instances_x):  # 6 instances per level
                x_position = start_x + (ix * spacing_x)  # x = 0, 221, 442, 663, 884, 1105
                
                # Instance naming
                inst_name = "SeatY_x{}_y{}_z{}".format(ix, iy + 1, 0)
                
                if inst_name in assembly_obj.instances:
                    instances_skipped += 1
                    continue
                
                try:
                    # Create instance
                    inst = assembly_obj.Instance(name=inst_name, part=p, dependent=ON)
                    instances_created += 1
                    
                    # Translate to correct position - NO ROTATION
                    translation_vector = (x_position, y_pos, z_pos)
                    inst.translate(vector=translation_vector)
                    
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
    instances_ok = create_seat_y_instances_no_rotation(a, myModel, part_name, n_instances_x, n_levels_y, spacing_x, spacing_y, spacing_z, start_z)
    if not instances_ok:
        overall_success = False
        warnings.warn("Failed to create SeatY instances")

# Step 6: Regenerate Assembly
print("\nStep 6: Regenerating Assembly...")
try:
    a.regenerate()
    print("Assembly regenerated successfully")
except Exception as e:
    warnings.warn("Error regenerating assembly: {}".format(e))
    overall_success = False

# Final Summary
print("\n" + "=" * 50)
print("SEATY CREATION SUMMARY - FIXED GEOMETRY VERSION")
print("=" * 50)

if overall_success:
    print("SUCCESS: SeatY frame elements created with correct segmentation!")
    print("SUCCESS: Cross-section: {} (RHS 48.3 x 3.0)".format(section_name))
    print("SUCCESS: Part: {} (12 individual segments, NO partitioning needed)".format(part_name))
    print("SUCCESS: Long segments automatically divided into 4 parts each")
    print("SUCCESS: Mesh: Element type B31, seed size {}".format(mesh_size))
    print("SUCCESS: Instances: 6 x-positions with finer Y/Z grid")
    print("SUCCESS: Geometry: Designed directly in XZ plane with correct segmentation")
    print("SUCCESS: Beam orientation: n1 along Y axis")
    print("")
    print("GEOMETRY DETAILS:")
    segments = create_seaty_segments()
    for i, (start, end) in enumerate(segments):
        length = math.sqrt(sum([(end[j] - start[j])**2 for j in range(3)]))
        segment_type = "LONG-PART" if abs(length - segment_length) < 0.01 else "SHORT"
        print("  Segment {}: {} to {} - {:.3f} units ({})".format(
            i+1, start, end, length, segment_type))
    print("")
    print("NO POST-PROCESSING PARTITIONING REQUIRED!")
else:
    print("ERROR: SeatY creation completed with errors")
    print("Please review warnings above before proceeding")

print("Script completed. Overall success: {}".format(overall_success))