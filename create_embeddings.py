import os
import numpy as np
import shutil
import json
import base64
import sys
from deepface import DeepFace



def create_embeddings_jsonl(image_data, output_filename):
    """
    Creates a JSON Lines file for Vertex AI Vector Search from image data.

    Args:
        image_data (list): A list of dictionaries. Each dictionary should
                           represent an image and contain at least 'id' (str)
                           and 'embedding' (list or np.ndarray). It can also
                           contain optional 'restricts', 'numeric_restricts',
                           and 'crowding_tag'.
        output_filename (str): The path to the output .jsonl file.
    """
    print(f"Starting to write embeddings to {output_filename}...")
    count = 0
    with open(output_filename, 'w') as f:
        for item in image_data:
            try:

                json_object = {
                    "id": str(item['id']), # Ensure ID is a string
                    "embedding": None # Placeholder
                }

                embedding_data = item['embedding']
                if isinstance(embedding_data, np.ndarray):
                    json_object["embedding"] = embedding_data.tolist()
                elif isinstance(embedding_data, list):
                    json_object["embedding"] = embedding_data
                else:
                    print(f"Warning: Skipping item {item.get('id', 'UNKNOWN')} due to invalid embedding type: {type(embedding_data)}")
                    continue 

                # Add optional fields if they exist in the input data
                if 'restricts' in item:
                    json_object['restricts'] = item['restricts']
                if 'numeric_restricts' in item:
                    json_object['numeric_restricts'] = item['numeric_restricts']
                if 'crowding_tag' in item:
                    json_object['crowding_tag'] = str(item['crowding_tag']) 

                # --- Serialize and write to file ---
                json_string = json.dumps(json_object)
                f.write(json_string + '\n') 
                count += 1

            except KeyError as e:
                print(f"Warning: Skipping item due to missing key: {e}. Item data: {item}")
            except Exception as e:
                print(f"Warning: Skipping item {item.get('id', 'UNKNOWN')} due to error: {e}")

    print(f"Finished writing {count} embeddings to {output_filename}.")



# this code assuems that all images are stored under dataset_path

def main():

    dataset_path = sys.argv[1]

    output_embedding_name = sys.argv[2] #the output embedding file name. it should be .json

    not_succuess = 0
    success = 0

    list_of_dict = []

    embeddings = {}

    for img_name in os.listdir(dataset_path):

        if img_name.endswith(".png") or img_name.endswith(".jpg") or img_name.endswith(".jpeg"):
        
            path = os.path.join(dataset_path, img_name)
            
            try:

                emb = DeepFace.represent(img_path = path)[0]['embedding']
                success = success +1
                
            except:
                not_succuess = not_succuess + 1
                emb = [0 for i in range(4096)]
            
            entry = {"id": img_name, "embedding": emb}
            
            list_of_dict.append(entry)
        

    print(f"The number of images encoded into embedding: {success} \n The number of images NOT encoded into embedding: {not_succuess}")


    create_embeddings_jsonl(list_of_dict, output_embedding_name)



if __name__ == "__main__":
    main()
