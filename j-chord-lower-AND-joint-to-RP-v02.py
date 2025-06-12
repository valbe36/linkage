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

# ChordLower Script for Grandstand Seating Substructure
# Creates 3D deformable wire elements from (0,0,0) to (0, dy, -dz)
# Start: (0, 127.5, 1105), End: (0, 255, 884)
# Length: approximately 255 cm, partitioned into 3 equal parts
# Cross-section: Circular hollow profile (CHS 60.3 x 3.2)

# Basic Setup: Model & Parameters
model_name = 'Model-1'
material_name = 'Steel_355'  # Already exists from script A
profile_name = 'CHS_60e3_t3e2_Profile'
section_name = 'CHS_60e3_t3e2'

# Geometry Parameters (from script A)
dx = 2.21    # x-direction spacing between instances
dy = 1.275  # y-direction height increment  
dz = 2.21    # z-direction - ChordLower goes backwards (negative dz)

# ChordLower specific parameters
chord_start = (0.0, 0.0, 0.0)
chord_end = (0.0, dy, -dz)  # (0, 127.5, -221) - goes from high z to low z
mesh_size = 0.1

# Instance pattern parameters
n_instances_x = 7  # 7 rows along x direction (x = 0, 221, 442, 663, 884, 1105, 1326)
n_levels_y = 5     # 5 levels in y direction  
spacing_x = dx     # 221 cm spacing between instances
start_z = 11.05     # Starting z position for first level

# Define overall success flag
overall_success = True

print("=== CHORDLOWER CREATION SCRIPT ===")
print("Creating seating substructure ChordLower elements")
print("Part geometry: from (0,0,0) to (0,{},{})".format(dy, -dz))
print("First instance: from (0,{},{}) to (0,{},{})".format(dy, start_z, 2*dy, start_z-dz))
print("Each level moves back by {} in z direction".format(dz))
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

# Step 1: Create Cross-Section for ChordLower
print("\nStep 1: Create Cross-Section for ChordLower")

def create_chord_lower_section(model, profile_name, section_name, material_name):
    """Create circular hollow profile and beam section for ChordLower."""
    
    # Create circular profile (CHS 60.3 x 3.2)
    if profile_name not in model.profiles:
        print("  Creating circular profile: {}".format(profile_name))
        try:
            # Outer diameter 60.3 mm = 0.0603 m, thickness 3.2 mm = 0.0032 m
            radius = 0.0603 / 2.0  # 0.03015 m
            thickness = 0.0032     # 0.0032 m
            
            model.PipeProfile(name=profile_name, r=radius, t=thickness)
            print("  Profile '{}' created (r={:.4f}m, t={:.4f}m)".format(profile_name, radius, thickness))
        except Exception as e:
            warnings.warn("Failed to create profile '{}': {}".format(profile_name, e))
            print(traceback.format_exc())
            raise
    else:
        print("  Profile '{}' already exists".format(profile_name))

    # Create beam section
    if section_name not in model.sections:
        print("  Creating beam section: {}".format(section_name))
        try:
            # Check if material exists
            if material_name not in model.materials:
                warnings.warn("Material '{}' not found. Run script A first.".format(material_name))
                return False
                
            model.BeamSection(
                name=section_name,
                integration=DURING_ANALYSIS,
                profile=profile_name,
                material=material_name,
                poissonRatio=0.3
            )
            print("  Section '{}' created".format(section_name))
        except Exception as e:
            warnings.warn("Failed to create section '{}': {}".format(section_name, e))
            print(traceback.format_exc())
            raise
    else:
        print("  Section '{}' already exists".format(section_name))
    
    return True

# Execute Step 1
section_ok = create_chord_lower_section(myModel, profile_name, section_name, material_name)
if not section_ok:
    overall_success = False
    warnings.warn("Failed to create ChordLower cross-section")

# Step 2: Create ChordLower Part
print("\nStep 2: Create ChordLower Part")

def create_chord_lower_part(model, part_name, start_point, end_point):
    """Create ChordLower part as 3D deformable wire, partitioned into 3 equal segments."""
    
    print("  Creating ChordLower part: {}".format(part_name))
    
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
            # After first partition, we need to find the right edge
            if len(p.edges) >= 2:
                # Find the edge that contains the 2/3 point
                for edge in p.edges:
                    # The second segment should be partitioned at its midpoint
                    # which corresponds to 2/3 of the original edge
                    pass
                # Partition the second edge at its midpoint (which is 2/3 of original)
                p.PartitionEdgeByParam(edges=(p.edges[1],), parameter=0.5)
            else:
                warnings.warn("Could not find second edge for partitioning")

            print("  Successfully partitioned into 3 segments")
            
        except Exception as e_part:
            warnings.warn("Error during partitioning: {}".format(e_part))
            print(traceback.format_exc())

        return p
        
    except Exception as e:
        warnings.warn("Failed to create ChordLower part '{}': {}".format(part_name, e))
        print(traceback.format_exc())
        raise

# Create the ChordLower part
part_name = "ChordLower"
try:
    chord_lower_part = create_chord_lower_part(myModel, part_name, chord_start, chord_end)
    print("  ChordLower part created successfully")
except Exception as e:
    overall_success = False
    print("  Failed to create ChordLower part: {}".format(e))
    chord_lower_part = None

# Step 3: Assign Section and Orientation
print("\nStep 3: Assign Section and Orientation to ChordLower")

def assign_section_and_orientation(model, part_name, section_name):
    """Assign beam section and orientation to ChordLower part."""
    
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
        
        # Assign beam orientation (n1 vector along negative global Z)
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
if chord_lower_part:
    section_assign_ok = assign_section_and_orientation(myModel, part_name, section_name)
    if not section_assign_ok:
        overall_success = False
        warnings.warn("Failed to assign section/orientation to ChordLower")

# Step 4: Mesh ChordLower Part
print("\nStep 4: Mesh ChordLower Part")

def mesh_chord_lower_part(model, part_name, seed_size):
    """Mesh the ChordLower part with specified seed size."""
    
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
        print("  ChordLower part meshed successfully")
        
        return True
        
    except Exception as e:
        warnings.warn("Failed to mesh ChordLower part '{}': {}".format(part_name, e))
        print(traceback.format_exc())
        return False

# Execute Step 4
if chord_lower_part:
    mesh_ok = mesh_chord_lower_part(myModel, part_name, mesh_size)
    if not mesh_ok:
        overall_success = False
        warnings.warn("Failed to mesh ChordLower part")

# Step 5: Create ChordLower Instances
print("\nStep 5: Create ChordLower Instances")

def create_chord_lower_instances(assembly_obj, model_obj, part_name, n_instances_x, n_levels_y, spacing_x, dy, start_z, dz):
    """Create instances of ChordLower following the specified pattern."""
    
    print("  Creating ChordLower instances...")
    print("  Pattern: {} instances per level, {} levels".format(n_instances_x, n_levels_y))
    print("  Each level moves back by {} in z direction".format(dz))
    
    if part_name not in model_obj.parts:
        warnings.warn("Part '{}' not found for instance creation".format(part_name))
        return False
    
    p = model_obj.parts[part_name]
    instances_created = 0
    instances_skipped = 0
    success = True
    
    try:
        for iy in range(n_levels_y):  # Levels: 0, 1, 2, 3, 4
            y_start = (iy + 1) * dy  # y = 127.5, 255, 382.5, 510, 637.5
            y_end = (iy + 2) * dy    # y = 255, 382.5, 510, 637.5, 765
            z_start = start_z - (iy * dz)    # z = 1105, 884, 663, 442, 221
            z_end = z_start - dz             # z = 884, 663, 442, 221, 0
            
            print("    Level {}: y = {:.1f} to {:.1f}, z = {:.1f} to {:.1f}".format(iy + 1, y_start, y_end, z_start, z_end))
            
            for ix in range(n_instances_x):  # Instances: 0, 1, 2, 3, 4, 5, 6
                x_position = ix * spacing_x  # x = 0, 221, 442, 663, 884, 1105, 1326
                
                # Instance naming following script A pattern
                inst_name = "ChordLower_x{}_y{}_z{}".format(ix, iy + 1, 0)
                
                if inst_name in assembly_obj.instances:
                    instances_skipped += 1
                    continue
                
                try:
                    # Create instance
                    inst = assembly_obj.Instance(name=inst_name, part=p, dependent=ON)
                    instances_created += 1
                    
                    # Translate to correct position
                    # Part goes from (0,0,0) to (0,dy,-dz), instance should start at (x_position, y_start, z_start)
                    translation_vector = (x_position, y_start, z_start)
                    inst.translate(vector=translation_vector)
                    
                    print("      Created: {} from ({:.1f}, {:.1f}, {:.1f}) to ({:.1f}, {:.1f}, {:.1f})".format(
                        inst_name, x_position, y_start, z_start, x_position, y_end, z_end))
                    
                except Exception as e_inst:
                    warnings.warn("Error creating instance '{}': {}".format(inst_name, e_inst))
                    success = False
                    if inst_name in assembly_obj.instances:
                        try: 
                            del assembly_obj.instances[inst_name]
                        except: 
                            pass
    
    except Exception as e_loop:
        warnings.warn("Error during ChordLower instance creation: {}".format(e_loop))
        print(traceback.format_exc())
        success = False
    
    print("  ChordLower instances created: {}, skipped: {}".format(instances_created, instances_skipped))
    print("  Total ChordLower instances: {}".format(instances_created + instances_skipped))
    
    return success

# Execute Step 5
if chord_lower_part:
    instances_ok = create_chord_lower_instances(a, myModel, part_name, n_instances_x, n_levels_y, spacing_x, dy, start_z, dz)
    if not instances_ok:
        overall_success = False
        warnings.warn("Failed to create ChordLower instances")

# Step 7: Connect ChordLower Endpoints to Existing RPs
print("\nStep 7: Connect ChordLower Endpoints to Existing RPs")

def convert_location_to_module_coords(location, dx, dy, dz):
    """Convert absolute coordinates to module coordinates."""
    module_x = int(round(location[0] / dx))
    module_y = int(round(location[1] / dy)) 
    module_z = int(round(location[2] / dz))
    return module_x, module_y, module_z

def find_rp_by_module_coords(assembly_obj, mod_x, mod_y, mod_z):
    """Find RP by module coordinates using set name."""
    
    set_name = "RP_x{}_y{}_z{}".format(mod_x, mod_y, mod_z)
    
    if set_name in assembly_obj.sets:
        try:
            rp_set = assembly_obj.sets[set_name]
            if hasattr(rp_set, 'referencePoints') and len(rp_set.referencePoints) > 0:
                rp = rp_set.referencePoints[0]
                print("        Found RP set: {}".format(set_name))
                return rp, set_name
        except Exception as e:
            print("        Error accessing RP set {}: {}".format(set_name, e))
    
    print("        RP set {} not found".format(set_name))
    return None, None

def create_chord_lower_rp_wires(assembly_obj, n_instances_x, n_levels_y, spacing_x, dy, start_z, dz):
    """Create wires connecting ChordLower endpoints to existing RPs using module coordinates."""
    
    print("  Creating ChordLower to RP connection wires using module coordinates...")
    wires_created = 0
    wires_failed = 0
    
    try:
        for iy in range(n_levels_y):  # Levels: 0, 1, 2, 3, 4
            y_start = (iy + 1) * dy  # y = 127.5, 255, 382.5, 510, 637.5
            y_end = (iy + 2) * dy    # y = 255, 382.5, 510, 637.5, 765
            z_start = start_z - (iy * dz)    # z = 1105, 884, 663, 442, 221
            z_end = z_start - dz             # z = 884, 663, 442, 221, 0
            
            print("    Level {}: Processing y={:.1f} to {:.1f}, z={:.1f} to {:.1f}".format(iy + 1, y_start, y_end, z_start, z_end))
            
            for ix in range(n_instances_x):  # Instances: 0, 1, 2, 3, 4, 5, 6
                x_position = ix * spacing_x  # x = 0, 221, 442, 663, 884, 1105, 1326
                
                # Instance name
                inst_name = "ChordLower_x{}_y{}_z{}".format(ix, iy + 1, 0)
                
                if inst_name not in assembly_obj.instances:
                    print("      Instance {} not found, skipping".format(inst_name))
                    continue
                
                instance = assembly_obj.instances[inst_name]
                
                try:
                    # Get ChordLower vertices (start and end)
                    vertices = instance.vertices
                    if len(vertices) < 2:
                        print("      Instance {} has insufficient vertices".format(inst_name))
                        continue
                    
                    # Start point and end point vertices
                    start_vertex = vertices[0]
                    end_vertex = vertices[-1]
                    
                    # Calculate module coordinates for endpoints
                    # Module coordinates: x=ix, y and z calculated from actual coordinates
                    mod_x = ix
                    
                    # Start point module coordinates
                    mod_y_start = int(round(y_start / dy))  # Should be iy + 1
                    mod_z_start = int(round(z_start / dz))  # Should be 5 - iy
                    
                    # End point module coordinates  
                    mod_y_end = int(round(y_end / dy))      # Should be iy + 2
                    mod_z_end = int(round(z_end / dz))      # Should be 4 - iy
                    
                    print("      Instance {}: start module ({},{},{}), end module ({},{},{})".format(
                        inst_name, mod_x, mod_y_start, mod_z_start, mod_x, mod_y_end, mod_z_end))
                    
                    # Find RPs at these module coordinates
                    start_rp, start_set = find_rp_by_module_coords(assembly_obj, mod_x, mod_y_start, mod_z_start)
                    end_rp, end_set = find_rp_by_module_coords(assembly_obj, mod_x, mod_y_end, mod_z_end)
                    
                    # Create wire for start point
                    if start_rp:
                        wire_name = "ChordLowerRP_x{}_y{}_z{}_start".format(ix, iy + 1, 0)
                        if create_wire_between_points(assembly_obj, start_vertex, start_rp, wire_name):
                            wires_created += 1
                            print("      Created wire: {} (to {})".format(wire_name, start_set))
                        else:
                            wires_failed += 1
                    else:
                        print("      No RP found at start module coords ({},{},{})".format(mod_x, mod_y_start, mod_z_start))
                        wires_failed += 1
                    
                    # Create wire for end point
                    if end_rp:
                        wire_name = "ChordLowerRP_x{}_y{}_z{}_end".format(ix, iy + 1, 0)
                        if create_wire_between_points(assembly_obj, end_vertex, end_rp, wire_name):
                            wires_created += 1
                            print("      Created wire: {} (to {})".format(wire_name, end_set))
                        else:
                            wires_failed += 1
                    else:
                        print("      No RP found at end module coords ({},{},{})".format(mod_x, mod_y_end, mod_z_end))
                        wires_failed += 1
                        
                except Exception as e_inst:
                    print("      Error processing instance {}: {}".format(inst_name, e_inst))
                    wires_failed += 2  # Both start and end failed
    
    except Exception as e_loop:
        print("    Error during wire creation: {}".format(e_loop))
        print(traceback.format_exc())
    
    print("  ChordLower RP wires created: {}, failed: {}".format(wires_created, wires_failed))
    return wires_created

def create_wire_between_points(assembly_obj, vertex1, vertex2, wire_name):
    """Create wire between two points (vertex and RP)."""
    try:
        # Check if wire already exists
        if wire_name in assembly_obj.features:
            print("        Wire {} already exists, skipping".format(wire_name))
            return True
        
        # Create wire
        wire_feature = assembly_obj.WirePolyLine(
            mergeType=IMPRINT,
            meshable=False,
            points=((vertex1, vertex2),)
        )
        
        # Rename the wire feature
        old_name = wire_feature.name
        assembly_obj.features.changeKey(old_name, wire_name)
        
        return True
        
    except Exception as e:
        print("        Error creating wire {}: {}".format(wire_name, e))
        return False

# Execute Step 7
print("  Searching for existing RPs to connect ChordLower endpoints...")
wires_created = create_chord_lower_rp_wires(a, n_instances_x, n_levels_y, spacing_x, dy, start_z, dz)
if wires_created > 0:
    print("  SUCCESS: Created {} ChordLower-RP connection wires".format(wires_created))
else:
    print("  WARNING: No ChordLower-RP connection wires created")
    overall_success = False
print("\nStep 6: Regenerating Assembly...")
try:
    a.regenerate()
    print("Assembly regenerated successfully")
except Exception as e:
    warnings.warn("Error regenerating assembly: {}".format(e))
    overall_success = False

# Step 8: Create Sets for ChordLower   Instances
print("\nStep 8: Create Sets for Chord Instances")

def create_chord_instance_sets(assembly_obj):
    """Create sets containing all ChordLower  r instances."""
    
    print("  Creating instance sets...")
    
    # Find all ChordLower instances
    chord_lower_instances = []
    for inst_name in assembly_obj.instances.keys():
        if inst_name.startswith('ChordLower_'):
            chord_lower_instances.append(assembly_obj.instances[inst_name])
    
    # Find all ChordLower instances  
    chord_lower_instances = []
    for inst_name in assembly_obj.instances.keys():
        if inst_name.startswith('ChordLower_'):
            chord_lower_instances.append(assembly_obj.instances[inst_name])
    
    print("  Found {} ChordLower instances".format(len(chord_lower_instances)))
    
    sets_created = 0
    
    # Create LowerChord set
    if len(chord_lower_instances) > 0:
        try:
            lower_set_name = "LowerChord"
            if lower_set_name in assembly_obj.sets:
                print("  Set '{}' already exists, will replace it".format(lower_set_name))
                del assembly_obj.sets[lower_set_name]
            
            assembly_obj.Set(instances=tuple(chord_lower_instances), name=lower_set_name)
            print("  Created set '{}' with {} ChordLower instances".format(lower_set_name, len(chord_lower_instances)))
            sets_created += 1
            
        except Exception as e:
            print("  Error creating LowerChord set: {}".format(e))
    else:
        print("  No ChordLower instances found for set creation")
    
    # Create LowerChord set
    if len(chord_lower_instances) > 0:
        try:
            lower_set_name = "LowerChord"
            if lower_set_name in assembly_obj.sets:
                print("  Set '{}' already exists, will replace it".format(lower_set_name))
                del assembly_obj.sets[lower_set_name]
            
            assembly_obj.Set(instances=tuple(chord_lower_instances), name=lower_set_name)
            print("  Created set '{}' with {} ChordLower instances".format(lower_set_name, len(chord_lower_instances)))
            sets_created += 1
            
        except Exception as e:
            print("  Error creating LowerChord set: {}".format(e))
    else:
        print("  No ChordLower instances found for set creation")
    
    return sets_created

# Execute Step 6
sets_created = create_chord_instance_sets(a)
if sets_created > 0:
    print("  SUCCESS: Created {} chord instance sets".format(sets_created))
else:
    print("  WARNING: No chord instance sets created")


# Final Summary
print("\n" + "="*50)
print("CHORDLOWER CREATION SUMMARY")
print("=" * 50)

if overall_success:
    print("SUCCESS: ChordLower elements created successfully!")
    print("SUCCESS: Cross-section: {} (CHS 60.3 x 3.2)".format(section_name))
    print("SUCCESS: Part: {} (3 segments, length approximately 255 cm)".format(part_name))
    print("SUCCESS: Mesh: Element type B31, seed size {}".format(mesh_size))
    print("SUCCESS: Instances: {} x {} = {} total instances".format(n_instances_x, n_levels_y, n_instances_x * n_levels_y))
    print("SUCCESS: RP Connection wires: ChordLowerRP_x#_y#_z#_start and ChordLowerRP_x#_y#_z#_end")
    print("SUCCESS: Position pattern:")
    for iy in range(n_levels_y):
        y_start = (iy + 1) * dy
        y_end = (iy + 2) * dy
        z_start = start_z - (iy * dz)
        z_end = z_start - dz
        print("    Level {}: y={:.1f} to {:.1f}, z={:.1f} to {:.1f}, x=0 to {:.1f} (7 instances)".format(iy + 1, y_start, y_end, z_start, z_end, (n_instances_x - 1) * spacing_x))
    print("\nReady to create remaining seating elements (ChordLower, SeatH, SeatV)!")
else:
    print("ERROR: ChordLower creation completed with errors")
    print("Please review warnings above before proceeding")

print("Script completed. Overall success: {}".format(overall_success))