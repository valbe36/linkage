# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import warnings

def create_analysis_steps_and_loads():
    """
    Create analysis steps and load cases for grandstand structure:
    Steps: prestress, modal, ULS_gr, SLS_gr, ULS, SLS_wz, SLS_wx
    """
    
    # Get model and assembly references
    model_name = 'Model-1'
    
    try:
        model = mdb.models[model_name]
        assembly = model.rootAssembly
        print("Successfully accessed model '{}' and assembly".format(model_name))
    except KeyError:
        print("FATAL ERROR: Model '{}' not found.".format(model_name))
        return False
    except Exception as e:
        print("FATAL ERROR accessing model/assembly: {}".format(e))
        return False
    
    print("=== CREATING ANALYSIS STEPS AND LOAD CASES ===")
    print("")
    
    # Step 1: Create Analysis Steps
    print("Step 1: Creating Analysis Steps...")
    steps_created = create_analysis_steps(model)
    
    # Step 2: Create Required Sets (if they don't exist)
    print("\nStep 2: Verifying/Creating Required Sets...")
    sets_created = create_required_sets(assembly)
    
    # Step 3: Apply Loads to Each Step
    print("\nStep 3: Applying Loads to Analysis Steps...")
    loads_created = apply_loads_to_steps(model, assembly)
    
    print("\n=== SUMMARY ===")
    print("Analysis steps created: {}".format(steps_created))
    print("Sets verified/created: {}".format(sets_created))
    print("Load cases applied: {}".format(loads_created))
    
    if steps_created > 0 and loads_created > 0:
        print("\nSUCCESS: Analysis steps and load cases created successfully!")
        print_step_summary()
        return True
    else:
        print("\nWARNING: Some steps or loads may not have been created properly.")
        return False

def create_analysis_steps(model):
    """Create all required analysis steps."""
    
    steps_created = 0
    
    # Define step configurations
    step_configs = [
        {
            'name': 'prestress',
            'type': 'static',
            'description': 'Prestress analysis step',
            'previous': 'Initial'
        },
        {
            'name': 'modal',
            'type': 'frequency',
            'description': 'Modal analysis step',
            'previous': 'prestress'
        },
        {
            'name': 'ULS_gr',
            'type': 'static',
            'description': 'Ultimate Limit State - Gravity',
            'previous': 'prestress'
        },
        {
            'name': 'SLS_gr',
            'type': 'static', 
            'description': 'Service Limit State - Gravity',
            'previous': 'prestress'
        },
        {
            'name': 'ULS',
            'type': 'static',
            'description': 'Ultimate Limit State - Full Loading',
            'previous': 'ULS_gr'
        },
        {
            'name': 'SLS_wz',
            'type': 'static',
            'description': 'Service Limit State - Wind Z direction',
            'previous': 'SLS_gr'
        },
        {
            'name': 'SLS_wx',
            'type': 'static',
            'description': 'Service Limit State - Wind X direction',
            'previous': 'SLS_gr'
        }
    ]
    
    # Create each step
    for config in step_configs:
        try:
            step_name = config['name']
            
            # Check if step already exists
            if step_name in model.steps:
                print("  Step '{}' already exists, skipping".format(step_name))
                steps_created += 1
                continue
            
            # Create step based on type
            if config['type'] == 'static':
                model.StaticStep(
                    name=step_name,
                    previous=config['previous'],
                    description=config['description'],
                    timePeriod=1.0,
                    initialInc=0.1,
                    minInc=1e-10,
                    maxInc=1.0
                )
                print("  Created static step: {}".format(step_name))
                
            elif config['type'] == 'frequency':
                model.FrequencyStep(
                    name=step_name,
                    previous=config['previous'],
                    description=config['description'],
                    numEigen=10,
                    eigensolver=LANCZOS
                )
                print("  Created frequency step: {}".format(step_name))
            
            steps_created += 1
            
        except Exception as e:
            print("  ERROR creating step '{}': {}".format(config['name'], e))
    
    return steps_created

def create_required_sets(assembly):
    """Create or verify required sets for load application."""
    
    sets_created = 0
    
    # Required set definitions
    required_sets = [
        # Seating sets
        'SeatInner',
        'SeatSide', 

        
        # Reference point sets
        'RP-inner',
        'RP_side',
        'RP-corner',
        'RPw_2',
        'RPw_1', 
        'RPw_1/2'
    ]
    
    print("  Checking for required sets...")
    
    for set_name in required_sets:
        if set_name in assembly.sets:
            print("    Set '{}' exists".format(set_name))
        else:
            print("    WARNING: Set '{}' not found - attempting to create...".format(set_name))
            
            # Try to create missing sets based on naming patterns
            if create_missing_set(assembly, set_name):
                sets_created += 1
                print("    Created set: {}".format(set_name))
            else:
                print("    ERROR: Could not create set: {}".format(set_name))
    
    return sets_created

def create_missing_set(assembly, set_name):
    """Attempt to create missing sets based on existing patterns."""
    
    try:
        # This is a placeholder - you may need to customize based on your actual model
        # For now, we'll just create empty sets to avoid errors
        
        if set_name.startswith('Seat'):
            # Try to find seat-related instances
            seat_instances = []
            for inst_name in assembly.instances.keys():
                if 'Seat' in inst_name:
                    seat_instances.append(assembly.instances[inst_name])
            
            if seat_instances:
                if 'Inner' in set_name:
                    # Create set with inner seat instances (first half)
                    selected_instances = seat_instances[:len(seat_instances)//2]
                elif 'Side' in set_name:
                    # Create set with side seat instances (second half)
                    selected_instances = seat_instances[len(seat_instances)//2:]
                else:
                    selected_instances = seat_instances
                
                if selected_instances:
                    assembly.Set(instances=tuple(selected_instances), name=set_name)
                    return True
        
        elif set_name.startswith('RP'):
            # Try to find reference points
            if 'inner' in set_name.lower():
                # Find internal RPs (example: middle range of coordinates)
                rps = find_rps_by_location_pattern(assembly, 'internal')
            elif 'side' in set_name.lower():
                # Find side RPs
                rps = find_rps_by_location_pattern(assembly, 'side')
            elif 'corner' in set_name.lower():
                # Find corner RPs
                rps = find_rps_by_location_pattern(assembly, 'corner')
            else:
                rps = []
            
            if rps:
                assembly.Set(referencePoints=tuple(rps), name=set_name)
                return True
        
        return False
        
    except Exception as e:
        print("      Error creating set '{}': {}".format(set_name, e))
        return False

    

def apply_loads_to_steps(model, assembly):
    """Apply loads to each analysis step."""
    
    loads_created = 0
    
    # ULS_gr loads
    loads_created += apply_uls_gr_loads(model, assembly)
    
    # SLS_gr loads  
    loads_created += apply_sls_gr_loads(model, assembly)
    
    # ULS loads
    loads_created += apply_uls_loads(model, assembly)
    
    # SLS_wz loads
    loads_created += apply_sls_wz_loads(model, assembly)
    
    # SLS_wx loads
    loads_created += apply_sls_wx_loads(model, assembly)
    
    return loads_created

def apply_uls_gr_loads(model, assembly):
    """Apply loads for ULS_gr step."""
    
    print("  Applying ULS_gr loads...")
    loads_created = 0
    step_name = 'ULS_gr'
    
    try:
        # Gravity load: y=-1.1*9.81, applied to whole model
        gravity_magnitude = -1.1 * 9.81  # -10.791
        
        load_name = 'Gravity_ULS_gr'
        if load_name not in model.loads:
            model.Gravity(
                name=load_name,
                createStepName=step_name,
                comp2=gravity_magnitude,
                distributionType=UNIFORM
            )
            loads_created += 1
            print("    Created gravity load: {} ({} m/s^2)".format(load_name, gravity_magnitude))
        else:
            print("    Gravity load already exists: {}".format(load_name))
            
    except Exception as e:
        print("    ERROR applying ULS_gr loads: {}".format(e))
    
    return loads_created

def apply_sls_gr_loads(model, assembly):
    """Apply loads for SLS_gr step."""
    
    print("  Applying SLS_gr loads...")
    loads_created = 0
    step_name = 'SLS_gr'
    
    try:
        # Gravity load: y=-9.81, applied to whole model
        gravity_magnitude = -9.81
        
        load_name = 'Gravity_SLS_gr'
        if load_name not in model.loads:
            model.Gravity(
                name=load_name,
                createStepName=step_name,
                comp2=gravity_magnitude,
                distributionType=UNIFORM
            )
            loads_created += 1
            print("    Created gravity load: {} ({} m/s^2)".format(load_name, gravity_magnitude))
        else:
            print("    Gravity load already exists: {}".format(load_name))
            
    except Exception as e:
        print("    ERROR applying SLS_gr loads: {}".format(e))
    
    return loads_created

def apply_uls_loads(model, assembly):
    """Apply loads for ULS step."""
    
    print("  Applying ULS loads...")
    loads_created = 0
    step_name = 'ULS'
    
    # Load definitions for ULS
    load_definitions = [
        # Line loads
        ('Qv_seatingInner', 'SeatInner', 'pressure', 0, -3645, 0),
        ('Qv_seatingEdge', 'SeatSide', 'pressure', 0, -1823, 0),
        
        # Concentrated loads
        ('Qnot_inner', 'RP-inner', 'concentrated', 0, 0, 3297),
        ('Qnot_edge', 'RP_side', 'concentrated', 0, 0, 1648),
        ('Qnot_corner', 'RP-corner', 'concentrated', 0, 0, 824),
        ('Qw_inner', 'RPw_2', 'concentrated', 0, 0, 184),
        ('Qw_edge', 'RPw_1', 'concentrated', 0, 0, 92),
        ('Qw_corner', 'RPw_1/2', 'concentrated', 0, 0, 46)
    ]
    
    loads_created += apply_load_definitions(model, assembly, step_name, load_definitions, 'ULS')
    return loads_created

def apply_sls_wz_loads(model, assembly):
    """Apply loads for SLS_wz step."""
    
    print("  Applying SLS_wz loads...")
    loads_created = 0
    step_name = 'SLS_wz'
    
    # Load definitions for SLS_wz
    load_definitions = [
        # Line loads
        ('Qv_seatingInner', 'SeatInner', 'pressure', 0, -1890, 0),
        ('Qv_seatingEdge', 'SeatSide', 'pressure', 0, -945, 0),
        
        # Concentrated loads
        ('Qnot_inner', 'RP-inner', 'concentrated', 0, 0, 2442),
        ('Qnot_edge', 'RP_side', 'concentrated', 0, 0, 1221),
        ('Qnot_corner', 'RP-corner', 'concentrated', 0, 0, 611),
        ('Qw_inner', 'RPw_2', 'concentrated', 0, 0, 82),
        ('Qw_edge', 'RPw_1', 'concentrated', 0, 0, 41),
        ('Qw_corner', 'RPw_1/2', 'concentrated', 0, 0, 20)
    ]
    
    loads_created += apply_load_definitions(model, assembly, step_name, load_definitions, 'SLS_wz')
    return loads_created

def apply_sls_wx_loads(model, assembly):
    """Apply loads for SLS_wx step."""
    
    print("  Applying SLS_wx loads...")
    loads_created = 0
    step_name = 'SLS_wx'
    
    # Load definitions for SLS_wx (wind in x direction)
    load_definitions = [
        # Line loads
        ('Qv_seatingInner', 'SeatInnerEdges', 'pressure', 0, -1890, 0),
        ('Qv_seatingEdge', 'SeatSideEdges', 'pressure', 0, -945, 0),
        
        # Concentrated loads (wind loads in x direction)
        ('Qnot_inner', 'RP-inner', 'concentrated', 2442, 0, 0),
        ('Qnot_edge', 'RP_side', 'concentrated', 1221, 0, 0),
        ('Qnot_corner', 'RP-corner', 'concentrated', 611, 0, 0),
        ('Qw_inner', 'RPw_2', 'concentrated', 82, 0, 0),
        ('Qw_edge', 'RPw_1', 'concentrated', 41, 0, 0),
        ('Qw_corner', 'RPw_1/2', 'concentrated', 20, 0, 0)
    ]
    
    loads_created += apply_load_definitions(model, assembly, step_name, load_definitions, 'SLS_wx')
    return loads_created

def apply_load_definitions(model, assembly, step_name, load_definitions, load_case_prefix):
    """Apply a set of load definitions to a step."""
    
    loads_created = 0
    
    for load_name, set_name, load_type, fx, fy, fz in load_definitions:
        try:
            full_load_name = "{}_{}".format(load_case_prefix, load_name)
            
            # Skip if load already exists
            if full_load_name in model.loads:
                print("    Load already exists: {}".format(full_load_name))
                continue
            
            # Check if required set exists
            if set_name not in assembly.sets:
                print("    WARNING: Set '{}' not found for load '{}'".format(set_name, load_name))
                continue
            
            region = assembly.sets[set_name]
            
            # Apply load based on type
            if load_type == 'concentrated':
                # Concentrated force
                model.ConcentratedForce(
                    name=full_load_name,
                    createStepName=step_name,
                    region=region,
                    cf1=fx,
                    cf2=fy,
                    cf3=fz,
                    distributionType=UNIFORM
                )
                print("    Created concentrated force: {} ({}, {}, {}) N".format(
                    full_load_name, fx, fy, fz))
                loads_created += 1
                
            elif load_type == 'pressure':
                # Pressure/line load - apply as pressure or distributed load
                if fy != 0:
                    # Vertical pressure
                    model.Pressure(
                        name=full_load_name,
                        createStepName=step_name,
                        region=region,
                        magnitude=abs(fy),
                        distributionType=UNIFORM
                    )
                    print("    Created pressure load: {} ({} N/m^2)".format(full_load_name, fy))
                    loads_created += 1
                elif fx != 0 or fz != 0:
                    # Horizontal distributed load - use ConcentratedForce on RPs
                    model.ConcentratedForce(
                        name=full_load_name,
                        createStepName=step_name,
                        region=region,
                        cf1=fx,
                        cf2=fy,
                        cf3=fz,
                        distributionType=UNIFORM
                    )
                    print("    Created distributed force: {} ({}, {}, {}) N/m".format(
                        full_load_name, fx, fy, fz))
                    loads_created += 1
                    
        except Exception as e:
            print("    ERROR creating load '{}': {}".format(load_name, e))
    
    return loads_created

def print_step_summary():
    """Print summary of created steps and load cases."""
    
    print("\n=== ANALYSIS STEPS AND LOAD CASES SUMMARY ===")
    print("Steps created:")
    print("  1. prestress - Prestress analysis")
    print("  2. modal - Modal analysis (10 modes)")
    print("  3. ULS_gr - Ultimate Limit State with 1.1x gravity")
    print("  4. SLS_gr - Service Limit State with 1.0x gravity")
    print("  5. ULS - Ultimate Limit State with full loading")
    print("  6. SLS_wz - Service Limit State with wind in Z direction")
    print("  7. SLS_wx - Service Limit State with wind in X direction")
    print("")
    print("Load cases applied:")
    print("  ULS_gr: Gravity = -10.791 m/s^2")
    print("  SLS_gr: Gravity = -9.81 m/s^2")
    print("  ULS: Seating loads + wind loads (Z direction)")
    print("  SLS_wz: Reduced seating loads + wind loads (Z direction)")
    print("  SLS_wx: Reduced seating loads + wind loads (X direction)")
    print("")
    print("NEXT STEPS:")
    print("1. Review created loads in Abaqus/CAE")
    print("2. Verify load magnitudes and directions")
    print("3. Check that all required sets exist")
    print("4. Run analysis jobs for each step")

def verify_created_loads():
    """Verify that loads were created successfully."""
    
    try:
        model = mdb.models['Model-1']
        
        print("\n=== LOAD VERIFICATION ===")
        
        total_loads = len(model.loads)
        print("Total loads in model: {}".format(total_loads))
        
        # Group loads by type
        gravity_loads = []
        force_loads = []
        pressure_loads = []
        
        for load_name, load_obj in model.loads.items():
            load_type = type(load_obj).__name__
            if 'Gravity' in load_type:
                gravity_loads.append(load_name)
            elif 'Force' in load_type:
                force_loads.append(load_name)
            elif 'Pressure' in load_type:
                pressure_loads.append(load_name)
        
        print("Gravity loads: {} ({})".format(len(gravity_loads), ', '.join(gravity_loads)))
        print("Force loads: {}".format(len(force_loads)))
        print("Pressure loads: {}".format(len(pressure_loads)))
        
        # Show load distribution by step
        step_loads = {}
        for load_name, load_obj in model.loads.items():
            try:
                step = load_obj.createStepName
                if step not in step_loads:
                    step_loads[step] = []
                step_loads[step].append(load_name)
            except:
                continue
        
        print("\nLoads by analysis step:")
        for step, loads in step_loads.items():
            print("  {}: {} loads".format(step, len(loads)))
            for load in loads[:3]:  # Show first 3
                print("    - {}".format(load))
            if len(loads) > 3:
                print("    ... and {} more".format(len(loads) - 3))
        
    except Exception as e:
        print("Error in load verification: {}".format(e))

# Main execution
if __name__ == "__main__":
    try:
        print("ANALYSIS STEPS AND LOAD CASES CREATION SCRIPT")
        print("=" * 50)
        
        success = create_analysis_steps_and_loads()
        
        if success:
            verify_created_loads()
        
        print("\n" + "=" * 50)
        if success:
            print("ANALYSIS STEPS AND LOAD CASES CREATED SUCCESSFULLY")
        else:
            print("ANALYSIS STEPS AND LOAD CASES CREATION COMPLETED WITH ISSUES")
        print("=" * 50)
        
    except Exception as e:
        print("Error in main execution: {}".format(e))
        import traceback
        traceback.print_exc()