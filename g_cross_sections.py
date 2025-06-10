
# -*- coding: utf-8 -*-
from abaqus import mdb
from abaqusConstants import * # DURING_ANALYSIS needed
import warnings
""""
This sketch makes the cross sections
"""""
# --- 1) Basic Setup ---
model_name = 'Model-1' 
print("Script starting: Create parts cross sections '{}'".format(model_name))

#call the model
try:
    myModel = mdb.models[model_name]
    print("Successfully accessed model '{}'.".format(model_name))
except KeyError: raise KeyError("FATAL ERROR: Model '{}' not found.".format(model_name))
except Exception as e: raise Exception("FATAL ERROR during model access: {}".format(str(e)))


                                            # ---  Function Definition for CIRCULAR PROFILES
def create_pipe_section(model_name='Model-1',
                       profile_name='DefaultPipe_Profile',  
                       section_name='DefaultPipe_Section', # 
                       material_name='Steel_355',      
                       radius=0.01,                
                       thickness=0.004):               
    """Checks for/Creates PipeProfile and a BeamSection using it."""
    try:
        model = mdb.models[model_name]
    except KeyError:
        warnings.warn("Model '{}' not found.".format(model_name)); return

    # --- Check/Create Profile ---
    profile_exists = profile_name in model.profiles
    if not profile_exists:
        print("  Creating profile: {}".format(profile_name))
        try:
            # Use arguments for dimensions
            model.PipeProfile(name=profile_name, r=radius, t=thickness)
            print("  Profile '{}' created.".format(profile_name))
            profile_exists = True
        except Exception as e:
            warnings.warn("Failed profile '{}': {}".format(profile_name, str(e)))
    else:
        print("  Profile '{}' already exists.".format(profile_name))

    # Ensure dependencies exist before creating section
    if section_name not in model.sections:
        # Check profile again after trying to create it
        profile_actually_exists = profile_name in model.profiles
        material_actually_exists = material_name in model.materials

        if not profile_actually_exists:
             warnings.warn("Cannot create section '{}': Profile '{}' not found/created.".format(section_name, profile_name))
        elif not material_actually_exists:
             warnings.warn("Cannot create section '{}': Material '{}' not found.".format(section_name, material_name))
        else:
            print("  Creating beam section: {}".format(section_name))
            try:
                model.BeamSection(name=section_name, integration=DURING_ANALYSIS,
                                 profile=profile_name, material=material_name,
                                 poissonRatio=0.3) # Use appropriate poissonRatio
                print("  Section '{}' created.".format(section_name))
            except Exception as e:
                 warnings.warn("Failed section '{}': {}".format(section_name, str(e)))
    else:
        print("  Section '{}' already exists.".format(section_name))                                 




# ---  Function Definition for RECTANGULAR PROFILES
def create_box_section(model_name='Model-1',profile_name='RHS_40x20x3_Profile', 
                       section_name='RHS_40x20x3',      
                       material_name='Steel_355',
                       height=0.04, width=0.02, thickness=0.003):
    try:
        model = mdb.models[model_name] # Assign model object
    except KeyError:
        warnings.warn("Model '{}' not found.".format(model_name))
        return # Exit function

    # Check/Create Profile
    profile_exists = profile_name in model.profiles
    if not profile_exists:
        print("  Creating profile: {}".format(profile_name))
        try:
            model.BoxProfile(name=profile_name,
                             a=height,           
                             b=width,           
                             uniformThickness=ON,
                             t1=thickness) 
            print("  Profile '{}' created.".format(profile_name))
            profile_exists = True
        except Exception as e: warnings.warn("Failed profile '{}': {}".format(profile_name, str(e)))
    else:
        print("  Profile '{}' already exists.".format(profile_name))

    # Check/Create Beam Section
    if section_name not in model.sections:
        # Check dependencies
        profile_actually_exists = profile_name in model.profiles
        material_actually_exists = material_name in model.materials
        if not profile_actually_exists:
             warnings.warn("Cannot create section '{}': Profile '{}' not found/created.".format(section_name, profile_name))
        elif not material_actually_exists:
             warnings.warn("Cannot create section '{}': Material '{}' not found.".format(section_name, material_name))
        else:
            print("  Creating beam section: {}".format(section_name))
            try:
                model.BeamSection(name=section_name, integration=DURING_ANALYSIS,
                                 profile=profile_name, material=material_name,
                                 poissonRatio=0.3) # Use appropriate poissonRatio
                print("  Section '{}' created.".format(section_name))
            except Exception as e: warnings.warn("Failed section '{}': {}".format(section_name, str(e)))
    else:
        print("  Section '{}' already exists.".format(section_name))


# --- Main Execution Part  
if __name__ == '__main__':
     model_name = 'Model-1'
     mat_name = 'Steel_355'


     print("\n--- Defining Sections ---")

     # --- Call for the FIRST Pipe Section (e.g., CHS 48.3 x 4.0) ---
     print("\nProcessing pipe section...")
     create_pipe_section(model_name=model_name,
                        profile_name='CHS_48e3_t4_Profile', 
                        section_name='CHS_48e3_t4',     
                        material_name=mat_name,
                        radius=(0.0483/2.0),              
                        thickness=0.004)                   

     # --- Call for  Pipe Section   CHS 60.3 x 3.2 
     print("\nProcessing  pipe section...")
     create_pipe_section(model_name=model_name,
                        profile_name='CHS33e7_t2e5_Profile', #
                        section_name='CHS33e7_t2e5',       
                        material_name=mat_name,           
                        radius=(0.0337 / 2.0),             
                        thickness=0.0025)                 

     # --- Call for  RHS  Section   40x20x3 
     print("\nProcessing first RHS section...")
     create_box_section(model_name=model_name,
                        profile_name='RHS_40x20x3_Profile',  
                        section_name='RHS_40x20x3',       
                        material_name=mat_name,
                        height=0.04, width=0.02, thickness=0.003)
     
          # --- Call for   RHS Section,  40x25x2.5
     print("\nProcessing second RHS section...")
     create_box_section(model_name=model_name,
                        profile_name='RHS_40x25x2.5_Profile', #
                        section_name='RHS_40x25x2.5',       
                        material_name=mat_name,           
                        height=0.04,                      
                        width=0.025,                       
                        thickness=0.0025)                  

     
     # --- Call for  RHS Section,  60x40x2.5
     print("\nProcessing second RHS section...")
     create_box_section(model_name=model_name,
                        profile_name='RHS_60x40x2.5_Profile', #
                        section_name='RHS_60x40x2.5',       
                        material_name=mat_name,           
                        height=0.06,                      
                        width=0.04,                       
                        thickness=0.0025)                  



     # --- Call for  RHS Section, 80x50x5---
     print("\nProcessing second RHS section...")
     create_box_section(model_name=model_name,
                        profile_name='RHS_80x50x5_Profile', #
                        section_name='RHS_80x50x5',       
                        material_name=mat_name,           
                        height=0.08,                      
                        width=0.05,                       
                        thickness=0.005)                  

 




     print("\nSection creation/checking finished.")





 