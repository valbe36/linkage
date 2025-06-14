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

# ChordLower Script for Grandstand Seating Substructure - Modified for RP-Z connections
# Creates 3D deformable wire elements from (0,0,0) to (0, dy, -dz)
# Connects endpoints to RP-Z sets with precise modular coordinates

# Basic Setup: Model & Parameters
model_name = 'Model-1'
material_name = 'Steel_355'  # Already exists from script A
profile_name = 'CHS_60e3_t3e2_Profile'
section_name = 'CHS_60e3_t3e2'

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

# Chord parameters (same as original)
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

print("=== CHORDLOWER TO RP-Z CONNECTION SCRIPT ===")
print("Creating seating substructure ChordLower elements")
print("Connecting to RP-Z sets with precise modular coordinates")
print("Part geometry: from (0,0,0) to (0,{},{})".format(dy, -dz))
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

# Step 1: Create Cross-Section for ChordLower (same as original)
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
            raise
    else:
        print("  Profile '{}' already exists".format(profile_name))

    # Create beam section
    if section_name not in model.sections:
        print("  Creating beam section: {}".format(section_name))
        try:
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
            raise
    else:
        print("  Section '{}' already exists".format(section_name))
    
    return True

# Execute Step 1
section_ok = create_chord_lower_section(myModel, profile_name, section_name, material_name)
if not section_ok:
    overall_success = False
    warnings.warn("Failed to create ChordLower cross-section")

# Step 2: Create ChordLower Part (same as original)
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
            if len(p.edges) >= 2:
                p.PartitionEdgeByParam(edges=(p.edges[1],), parameter=0.5)
            else:
                warnings.warn("Could not find second edge for partitioning")

            print("  Successfully partitioned into 3 segments")
            
        except Exception as e_part:
            warnings.warn("Error during partitioning: {}".format(e_part))

        return p
        
    except Exception as e:
        warnings.warn("Failed to create ChordLower part '{}': {}".format(part_name, e))
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

# Step 3: Assign Section and Orientation (same as original)
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
        success = False
    
    return success

# Execute Step 3
if chord_lower_part:
    section_assign_ok = assign_section_and_orientation(myModel, part_name, section_name)
    if not section_assign_ok:
        overall_success = False
        warnings.warn("Failed to assign section/orientation to ChordLower")

# Step 4: Mesh ChordLower Part (same as original)
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
        return False

# Execute Step 4
if chord_lower_part:
    mesh_ok = mesh_chord_lower_part(myModel, part_name, mesh_size)
    if not mesh_ok:
        overall_success = False
        warnings.warn("Failed to mesh ChordLower part")

# Step 5: Create ChordLower Instances (same as original)
print("\nStep 5: Create ChordLower Instances")

def create_chord_lower_instances(assembly_obj, model_obj, part_name, n_instances_x, n_levels_y, spacing_x, dy, start_z, dz):
    """Create instances of ChordLower following the specified pattern."""
    
    print("  Creating ChordLower instances...")
    print("  Pattern: {} instances per level, {} levels".format(n_instances_x, n_levels_y))
    
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
        success = False
    
    print("  ChordLower instances created: {}, skipped: {}".format(instances_created, instances_skipped))
    
    return success

# Execute Step 5
if chord_lower_part:
    instances_ok = create_chord_lower_instances(a, myModel, part_name, n_instances_x, n_levels_y, spacing_x, dy, start_z, dz)
    if not instances_ok:
        overall_success = False
        warnings.warn("Failed to create ChordLower instances")

# ============================================================================
# MODIFIED STEP 7: Connect ChordLower Endpoints to RP-Z Sets
# ============================================================================

print("\nStep 7: Connect ChordLower Endpoints to RP-Z Sets")

def create_chord_lower_rpz_wires(assembly_obj, n_instances_x, n_levels_y, spacing_x, dy, start_z, dz):
    """Create wires connecting ChordLower endpoints to RP-Z sets using precise modular coordinates."""
    
    print("  Creating ChordLower to RP-Z connection wires...")
    print("  Using precise modular coordinate matching")
    
    wires_created = 0
    wires_failed = 0
    
    # Clean up existing wires first
    cleanup_existing_chord_rpz_wires(assembly_obj)
    
    try:
        for iy in range(n_levels_y):  # Levels: 0, 1, 2, 3, 4
            y_start = (iy + 1) * dy  # y = 127.5, 255, 382.5, 510, 637.5
            y_end = (iy + 2) * dy    # y = 255, 382.5, 510, 637.5, 765
            z_start = start_z - (iy * dz)    # z = 1105, 884, 663, 442, 221
            z_end = z_start - dz             # z = 884, 663, 442, 221, 0
            
            print("    Level {}: Processing ChordLower instances".format(iy + 1))
            
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
                    
                    # Calculate module coordinates for endpoints using modular system
                    # Start point: at (x_position, y_start, z_start)
                    start_mod_coords = (ix, iy + 1, int(round(z_start / dz)))
                    
                    # End point: at (x_position, y_end, z_end)  
                    end_mod_coords = (ix, iy + 2, int(round(z_end / dz)))
                    
                    print("      Instance {}: start module ({},{},{}), end module ({},{},{})".format(
                        inst_name, start_mod_coords[0], start_mod_coords[1], start_mod_coords[2],
                        end_mod_coords[0], end_mod_coords[1], end_mod_coords[2]))
                    
                    # Find RP-Z sets at these module coordinates
                    start_rpz_set = find_rpz_by_module_coords(assembly_obj, *start_mod_coords)
                    end_rpz_set = find_rpz_by_module_coords(assembly_obj, *end_mod_coords)
                    
                    # Create wire for start point
                    if start_rpz_set:
                        wire_name = "ChordLowerRPZ_x{}_y{}_z{}_start".format(ix, iy + 1, 0)
                        if create_wire_to_rpz_set(assembly_obj, start_vertex, start_rpz_set, wire_name):
                            wires_created += 1
                            print("      Created wire: {} (to {})".format(wire_name, start_rpz_set))
                        else:
                            wires_failed += 1
                    else:
                        print("      No RP-Z set found at start module coords ({},{},{})".format(*start_mod_coords))
                        wires_failed += 1
                    
                    # Create wire for end point
                    if end_rpz_set:
                        wire_name = "ChordLowerRPZ_x{}_y{}_z{}_end".format(ix, iy + 1, 0)
                        if create_wire_to_rpz_set(assembly_obj, end_vertex, end_rpz_set, wire_name):
                            wires_created += 1
                            print("      Created wire: {} (to {})".format(wire_name, end_rpz_set))
                        else:
                            wires_failed += 1
                    else:
                        print("      No RP-Z set found at end module coords ({},{},{})".format(*end_mod_coords))
                        wires_failed += 1
                        
                except Exception as e_inst:
                    print("      Error processing instance {}: {}".format(inst_name, e_inst))
                    wires_failed += 2  # Both start and end failed
    
    except Exception as e_loop:
        print("    Error during wire creation: {}".format(e_loop))
    
    print("  ChordLower RP-Z wires created: {}, failed: {}".format(wires_created, wires_failed))
    return wires_created

def find_rpz_by_module_coords(assembly_obj, mod_x, mod_y, mod_z):
    """Find RP-Z set by module coordinates."""
    
    set_name = "RP-Z_x{}_y{}_z{}".format(mod_x, mod_y, mod_z)
    
    if set_name in assembly_obj.sets:
        try:
            rp_set = assembly_obj.sets[set_name]
            if hasattr(rp_set, 'referencePoints') and len(rp_set.referencePoints) > 0:
                return set_name
        except Exception as e:
            print("        Error accessing RP-Z set {}: {}".format(set_name, e))
    
    return None

def create_wire_to_rpz_set(assembly_obj, chord_vertex, rpz_set_name, wire_name):
    """Create wire between ChordLower vertex and RP-Z set."""
    
    try:
        # Check if wire already exists
        if wire_name in assembly_obj.features:
            return True
        
        # Get the RP from the set
        rpz_set = assembly_obj.sets[rpz_set_name]
        if len(rpz_set.referencePoints) != 1:
            print("        Error: RP-Z set {} contains {} RPs (expected 1)".format(
                rpz_set_name, len(rpz_set.referencePoints)))
            return False
        
        rp = rpz_set.referencePoints[0]
        
        # Create wire
        wire_feature = assembly_obj.WirePolyLine(
            mergeType=IMPRINT,
            meshable=False,
            points=((chord_vertex, rp),)
        )
        
        # Rename the wire feature
        old_name = wire_feature.name
        assembly_obj.features.changeKey(old_name, wire_name)
        
        return True
        
    except Exception as e:
        print("        Error creating wire {}: {}".format(wire_name, e))
        return False

def cleanup_existing_chord_rpz_wires(assembly_obj):
    """Remove existing ChordLower-RP-Z wires."""
    
    existing_wires = []
    for feature_name in assembly_obj.features.keys():
        if feature_name.startswith('ChordLowerRPZ_'):
            existing_wires.append(feature_name)
    
    if len(existing_wires) > 0:
        print("  Removing {} existing ChordLower-RP-Z wires...".format(len(existing_wires)))
        for wire_name in existing_wires:
            try:
                del assembly_obj.features[wire_name]
            except:
                pass

# Execute Step 7
print("  Searching for RP-Z sets to connect ChordLower endpoints...")
wires_created = create_chord_lower_rpz_wires(a, n_instances_x, n_levels_y, spacing_x, dy, start_z, dz)
if wires_created > 0:
    print("  SUCCESS: Created {} ChordLower-RP-Z connection wires".format(wires_created))
else:
    print("  WARNING: No ChordLower-RP-Z connection wires created")
    overall_success = False

# Step 8: Regenerate Assembly
print("\nStep 8: Regenerating Assembly...")
try:
    a.regenerate()
    print("Assembly regenerated successfully")
except Exception as e:
    warnings.warn("Error regenerating assembly: {}".format(e))
    overall_success = False

# Final Summary
print("\n" + "="*60)
print("CHORDLOWER TO RP-Z CONNECTION SUMMARY")
print("=" * 60)

if overall_success:
    print("SUCCESS: ChordLower elements created and connected to RP-Z sets!")
    print("SUCCESS: Cross-section: {} (CHS 60.3 x 3.2)".format(section_name))
    print("SUCCESS: Part: {} (3 segments, length approximately 255 cm)".format(part_name))
    print("SUCCESS: Mesh: Element type B31, seed size {}".format(mesh_size))
    print("SUCCESS: Instances: {} x {} = {} total instances".format(n_instances_x, n_levels_y, n_instances_x * n_levels_y))
    print("SUCCESS: RP-Z Connection wires: ChordLowerRPZ_x#_y#_z#_start and ChordLowerRPZ_x#_y#_z#_end")
    print("SUCCESS: Precise modular coordinate matching with RP-Z sets")
    print("SUCCESS: Duplicate avoidance ensures one wire per connection point")
    print("\nNEXT STEPS:")
    print("1. In Abaqus GUI, select wires named 'ChordLowerRPZ_*'")
    print("2. Apply appropriate connector sections")
    print("3. These connections link ChordLower endpoints to RP-Z reference points")
    print("4. Ready for structural analysis!")
else:
    print("ERROR: ChordLower creation completed with errors")
    print("Please review warnings above before proceeding")

print("Script completed. Overall success: {}".format(overall_success))