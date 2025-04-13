import os
import numpy as np
import shutil
import json
import base64
import sys



def create_folder(folder_name):

    try:
        # Check if the folder already exists
        if os.path.exists(folder_name):
            print(f"Folder '{folder_name}' already exists.")
            return  # Exit the function if the folder exists

        # Create the folder
        os.makedirs(folder_name)
        print(f"Folder '{folder_name}' created successfully.")
    except OSError as e:
        print(f"Error creating folder '{folder_name}': {e}")
    except ValueError as ve:
        print(f"Error: {ve}")



# this code assuems that all images are stored under destination_dataset, where there is a sub-folder for every person

def main():

    destination_dataset = sys.argv[2]

    source_dataset = sys.argv[1]

    create_folder(destination_dataset)


    num_sample_per_folder = 20 # to sample from each identity


    folder_list  = os.listdir(source_dataset)


    folder_label_map = dict(zip(folder_list,[i for i in range(len(folder_list))]))



    for f in folder_list:
        
        cel_folder = os.path.join(source_dataset,f)

        cel_content = os.listdir(cel_folder)

        select_samples = np.random.choice(cel_content, num_sample_per_folder, replace=False).tolist()

        for final_f in select_samples:
            dist_img_name = f"{folder_label_map[f]}_{f}_{final_f}"
            
            source_path = os.path.join(cel_folder,final_f)
            
            destination_path = os.path.join(destination_dataset,dist_img_name)
            
            shutil.copy2(source_path, destination_path)



    with open( os.path.join(destination_dataset, "label_map.json"), 'w') as f:
          json.dump(folder_label_map, f, indent=4)




if __name__ == "__main__":
    main()
