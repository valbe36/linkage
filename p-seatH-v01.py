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

# SeatH Script for Grandstand Seating Substructure
# Creates 5 parallel, disjointed wires of equal length
# First and last wires: RHS_60x5x2e5, Middle wires: RHS_40x25x2e5
# Cross-sections already exist in model

# Basic Setup: Model & Parameters
model_name = 'Model-1'
material_name = 'Steel_355'  # Already exists from script A
section_name_outer = 'RHS_60x40x2.5'      # First and last wires
section_name_middle = 'RHS_40x25x2.5'    # Middle wires (2, 3, 4)
part_name = "SeatH"

# Geometry Parameters
dx = 2.21    # x-direction spacing between instances
dy = 1.275  # y-direction height increment  
dz = 2.21    # z-direction spacing

# SeatH specific parameters
mesh_size = 0.12
wire_length = dz/3    # dz/3=0.7367 Length along z direction
wire_offset = 0.54     # Offset along x direction between wires
y_offset_from_seaty = 0.625  # Additional y offset from SeatY positions

# Wire positions (5 wires)
wire_x_positions = [
    0.0,           # Wire 1 (outer - RHS_60x5x2e5)
    0.54,          # Wire 2 (middle - RHS_40x25x2e5)
    1.08,          # Wire 3 (middle - RHS_40x25x2e5)
    1.62,          # Wire 4 (middle - RHS_40x25x2e5)  
    2.16           # Wire 5 (outer - RHS_60x5x2e5)
]

# Wire segments definition (5 parallel wires)
wire_segments = []
for i, x_pos in enumerate(wire_x_positions):
    start_point = (x_pos, 0.0, 0.0)
    end_point = (x_pos, 0.0, wire_length)
    wire_segments.append((start_point, end_point, i + 1))  # Include wire number

# Instance pattern parameters (same as SeatY)
n_instances_x = 6  # 6 rows along x direction
n_levels_y = 15    # More levels due to finer   spacing
n_levels_z = 15    # More levels due to finer   spacing
spacing_x = dx     # 221 cm spacing between instances
spacing_y = dy / 3 # 127.5/3 = 42.5 cm spacing in y
spacing_z = dz / 3 # 221/3 = 73.67 cm spacing in z  
start_z = 11.05 -dz/3   # Starting z position for first level
start_x = 0.025

# Define overall success flag
overall_success = True

#region
print("=== SEATH CREATION SCRIPT ===")
print("Creating seating substructure SeatH frame elements")
print("5 parallel wires, length {} along z".format(wire_length))
print("Wire spacing: {} along x".format(wire_offset))
print("Cross sections: Outer wires = {}, Middle wires = {}".format(section_name_outer, section_name_middle))
print("Mesh size: {}".format(mesh_size))
print("Y offset from SeatY: +{}".format(y_offset_from_seaty))

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

# Step 1: Verify Cross-Sections Exist
print("\nStep 1: Verify Cross-Sections for SeatH")

def verify_seat_h_sections(model, section_outer, section_middle, material_name):
    """Verify that the SeatH cross-sections exist."""
    
    sections_ok = True
    
    if section_outer not in model.sections:
        warnings.warn("Section '{}' not found. Run cross-section script first.".format(section_outer))
        sections_ok = False
    else:
        print("  Outer section '{}' found".format(section_outer))
    
    if section_middle not in model.sections:
        warnings.warn("Section '{}' not found. Run cross-section script first.".format(section_middle))
        sections_ok = False
    else:
        print("  Middle section '{}' found".format(section_middle))
    
    if material_name not in model.materials:
        warnings.warn("Material '{}' not found. Run script A first.".format(material_name))
        sections_ok = False
    else:
        print("  Material '{}' found".format(material_name))
    
    return sections_ok

# Execute Step 1
sections_ok = verify_seat_h_sections(myModel, section_name_outer, section_name_middle, material_name)
if not sections_ok:
    overall_success = False
    warnings.warn("Required cross-sections or material not found")

# Step 2: Create SeatH Part
print("\nStep 2: Create SeatH Part")

def create_seat_h_part(model, part_name, wire_segments):
    """Create SeatH part as 5 parallel, disjointed wires."""
    
    print("  Creating SeatH part: {}".format(part_name))
    
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
        
        # Create all wire segments
        print("  Creating {} wire segments...".format(len(wire_segments)))
        for i, (start_point, end_point, wire_num) in enumerate(wire_segments):
            print("    Wire {}: {} to {} (x={:.2f})".format(wire_num, start_point, end_point, start_point[0]))
            p.WirePolyLine(points=(start_point, end_point), mergeType=IMPRINT, meshable=ON)
        
        print("  Total edges created: {}".format(len(p.edges)))
        print("  All wires are parallel and disjointed as required")
        
        return p
        
    except Exception as e:
        warnings.warn("Failed to create SeatH part '{}': {}".format(part_name, e))
        print(traceback.format_exc())
        raise

# Create the SeatH part
try:
    seat_h_part = create_seat_h_part(myModel, part_name, wire_segments)
    print("  SeatH part created successfully")
except Exception as e:
    overall_success = False
    print("  Failed to create SeatH part: {}".format(e))
    seat_h_part = None

# Step 3: Assign Sections and Orientations
print("\nStep 3: Assign Sections and Orientations to SeatH")

def assign_sections_to_seat_h(model, part_name, section_outer, section_middle):
    """Assign different beam sections to different wires based on position."""
    
    if part_name not in model.parts:
        warnings.warn("Part '{}' not found for section assignment".format(part_name))
        return False
    
    success = True
    part = model.parts[part_name]
    
    try:
        print("  Assigning sections to individual wires...")
        all_edges = part.edges
        
        if len(all_edges) != 5:
            warnings.warn("Expected 5 edges, found {}".format(len(all_edges)))
            return False
        
        # Sort edges by x-coordinate to match wire order
        edge_info = []
        for edge in all_edges:
            try:
                vertices = edge.getVertices()
                if len(vertices) >= 1:
                    # Get x-coordinate of first vertex
                    x_coord = vertices[0].pointOn[0][0]
                    edge_info.append((edge, x_coord))
            except:
                continue
        
        # Sort by x-coordinate
        edge_info.sort(key=lambda x: x[1])
        
        print("  Found {} edges, assigning sections...".format(len(edge_info)))
        
        # Assign sections based on wire position
        for i, (edge, x_coord) in enumerate(edge_info):
            wire_num = i + 1
            
            # Determine section based on wire number
            if wire_num == 1 or wire_num == 5:
                # Outer wires (1 and 5)
                section_name = section_outer
                wire_type = "outer"
            else:
                # Middle wires (2, 3, 4)
                section_name = section_middle
                wire_type = "middle"
            
            print("    Wire {} (x={:.2f}): {} section '{}'".format(wire_num, x_coord, wire_type, section_name))
            
            # Create region for this edge
            region = regionToolset.Region(edges=(edge,))
            
            # Assign section
            part.SectionAssignment(
                region=region, 
                sectionName=section_name, 
                offset=0.0,
                offsetType=MIDDLE_SURFACE, 
                offsetField='',
                thicknessAssignment=FROM_SECTION
            )
            
            # Assign beam orientation
            # For rectangular sections: 40mm dimension should be along Y
            # n1 vector defines the local x-axis direction (section width direction)
            # Setting n1 along global Z will orient the 40mm dimension along global Y
            n1_direction = (0.0, 0.0, 1.0)  # n1 along Z axis
            
            part.assignBeamSectionOrientation(
                method=N1_COSINES, 
                n1=n1_direction, 
                region=region
            )
            
            print("      Section '{}' assigned with orientation n1={}".format(section_name, n1_direction))
        
        print("  All sections and orientations assigned successfully")
        
    except Exception as e:
        warnings.warn("Failed to assign sections/orientations to '{}': {}".format(part_name, e))
        print(traceback.format_exc())
        success = False
    
    return success

# Execute Step 3
if seat_h_part:
    sections_assign_ok = assign_sections_to_seat_h(myModel, part_name, section_name_outer, section_name_middle)
    if not sections_assign_ok:
        overall_success = False
        warnings.warn("Failed to assign sections/orientations to SeatH")

# Step 4: Mesh SeatH Part
print("\nStep 4: Mesh SeatH Part")

def mesh_seat_h_part(model, part_name, seed_size):
    """Mesh the SeatH part with specified seed size."""
    
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
        print("  SeatH part meshed successfully")
        
        return True
        
    except Exception as e:
        warnings.warn("Failed to mesh SeatH part '{}': {}".format(part_name, e))
        print(traceback.format_exc())
        return False

# Execute Step 4
if seat_h_part:
    mesh_ok = mesh_seat_h_part(myModel, part_name, mesh_size)
    if not mesh_ok:
        overall_success = False
        warnings.warn("Failed to mesh SeatH part")

#endregion
# Step 5: Create SeatH Instances
print("\nStep 5: Create SeatH Instances")

def create_seat_h_instances(assembly_obj, model_obj, part_name, n_instances_x, n_levels_y, spacing_x, spacing_y, spacing_z, start_z, y_offset):
    """Create instances of SeatH following SeatY pattern with additional y offset."""
    
    print("  Creating SeatH instances...")
    print("  Pattern: {} instances per level, {} levels".format(n_instances_x, n_levels_y))
    print("  Y offset from SeatY: +{}".format(y_offset))
    
    if part_name not in model_obj.parts:
        warnings.warn("Part '{}' not found for instance creation".format(part_name))
        return False
    
    p = model_obj.parts[part_name]
    instances_created = 0
    instances_skipped = 0
    success = True
    
    try:
        for iy in range(n_levels_y):
            # Same as SeatY but with additional y offset
            y_pos = 1.275 + (iy * spacing_y) + y_offset      # SeatY position + additional offset
            z_pos = start_z - (iy * spacing_z)               # Start at 1105, step back by 73.67
            
            if iy < 3:  # Show first few levels
                print("    Level {}: y = {:.1f}, z = {:.1f}".format(iy + 1, y_pos, z_pos))
            elif iy == 3:
                print("    ... creating remaining levels ...")
            
            for ix in range(n_instances_x):  # 6 instances per level
                x_position = start_x+(ix * spacing_x)  # x = 0, 221, 442, 663, 884, 1105
                
                # Instance naming
                inst_name = "SeatH_x{}_y{}_z{}".format(ix, iy + 1, 0)
                
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
                    
                except Exception as e_inst:
                    warnings.warn("Error creating instance '{}': {}".format(inst_name, e_inst))
                    success = False
                    if inst_name in assembly_obj.instances:
                        try: 
                            del assembly_obj.instances[inst_name]
                        except: 
                            pass
    
    except Exception as e_loop:
        warnings.warn("Error during SeatH instance creation: {}".format(e_loop))
        print(traceback.format_exc())
        success = False
    
    print("  SeatH instances created: {}, skipped: {}".format(instances_created, instances_skipped))
    print("  Total SeatH instances: {}".format(instances_created + instances_skipped))
    
    return success

# Execute Step 5
if seat_h_part:
    instances_ok = create_seat_h_instances(a, myModel, part_name, n_instances_x, n_levels_y, spacing_x, spacing_y, spacing_z, start_z, y_offset_from_seaty)
    if not instances_ok:
        overall_success = False
        warnings.warn("Failed to create SeatH instances")

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
print("SEATH CREATION SUMMARY")
print("=" * 50)

if overall_success:
    print("SUCCESS: SeatH frame elements created successfully!")
    print("SUCCESS: Part: {} (5 parallel disjointed wires)".format(part_name))
    print("SUCCESS: Wire specifications:")
    print("  - Length: {} along z direction".format(wire_length))
    print("  - Spacing: {} along x direction".format(wire_offset))
    print("  - Wire positions: {}".format([round(x, 2) for x in wire_x_positions]))
    print("SUCCESS: Cross sections assigned:")
    print("  - Wires 1,5 (outer): {}".format(section_name_outer))
    print("  - Wires 2,3,4 (middle): {}".format(section_name_middle))
    print("SUCCESS: Beam orientation: n1 along Z axis (40mm dimension along Y)")
    print("SUCCESS: Mesh: Element type B31, seed size {}".format(mesh_size))
    print("SUCCESS: Instances: Same pattern as SeatY + {} y offset".format(y_offset_from_seaty))
    print("SUCCESS: Instance positions follow SeatY pattern:")
    print("  - {} x-positions with finer Y/Z grid".format(n_instances_x))
    print("  - Y spacing: {:.1f}cm, Z spacing: {:.1f}cm".format(spacing_y, spacing_z))
    print("")
    print("WIRE DETAILS:")
    for i, (start, end, wire_num) in enumerate(wire_segments):
        section = section_name_outer if (wire_num == 1 or wire_num == 5) else section_name_middle
        wire_type = "outer" if (wire_num == 1 or wire_num == 5) else "middle"
        print("  Wire {}: {} to {} ({}, {})".format(wire_num, start, end, wire_type, section))
    print("")
    print("Ready for joint creation and load application!")
else:
    print("ERROR: SeatH creation completed with errors")
    print("Please review warnings above before proceeding")

print("Script completed. Overall success: {}".format(overall_success))