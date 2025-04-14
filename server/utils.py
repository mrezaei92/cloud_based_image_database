import os
import base64
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
from typing import List
from PIL import Image
import io
from google.cloud import aiplatform
from google.cloud import storage
import numpy as np
import json
from collections import Counter
from pydantic import BaseModel 
from typing import List, Any 
import math

# --- Some Global Vars ---
PROJECT_ID = "mygcp-456216"  
REGION = "europe-west2"           
INDEX_ENDPOINT_ID = "3452941500239839232" 
DEPLOYED_INDEX_ID = "deploy_indexendpoint_1744493199600"

BUCKET_NAME = "faceverification_me"
DATASET_ADD = "CelebrityFacesmall/"


NUM_NEIGHBORS = 5 # used for performing nearsest neighbor vector search using Vetrex AI

class DataPayload(BaseModel):
    data: List[Any] 

    

def find_most_frequent_ID(img_paths_list):
    """
    img_paths_list: is a list of image names

    this function returns the most frequent name in that list. 
    """
    names_list = [img_path.split("_")[1] for img_path in img_paths_list]

    counts = Counter(names_list)

    most_freq_value, freq = counts.most_common(1)[0]

    return most_freq_value, freq




def load_json(bucket_name, source_blob_name):
    # load a .json file from GCS

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(source_blob_name)

    json_content = blob.download_as_text()

    try:
        data = json.loads(json_content)
        # print("JSON file loaded successfully:")
        # print(data)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        
    return data

    
    
def vector_search_NN(query_vector , NUM_NEIGHBORS = 3):
    # Perform vector search using Vertex AI's vector search engine
    # query_vector: a list containing the embd like [0,0.01,...]
    # NUM_NEIGHBORS: number of nearest neighbors to retrieve

    index_endpoint_name = f"projects/{PROJECT_ID}/locations/{REGION}/indexEndpoints/{INDEX_ENDPOINT_ID}"

    # Initialize the Vertex AI SDK
    aiplatform.init(project=PROJECT_ID, location=REGION)

    my_index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=index_endpoint_name)
    
    
    print(f"Searching for {NUM_NEIGHBORS} neighbors...")

    try:
        response = my_index_endpoint.find_neighbors(
            queries=[query_vector],                
            deployed_index_id=DEPLOYED_INDEX_ID, 
            num_neighbors=NUM_NEIGHBORS
            )

        print("Search completed.")

        if response and response[0]: # response is a list of lists of neighbors (one list per query)
            print(f"Found {len(response[0])} neighbors:")
            
            list_neighbors = []
            for neighbor in response[0]:
                neighbor_id = neighbor.id 
                neighbor_distance = neighbor.distance
                
                list_neighbors.append( (neighbor_id,neighbor_distance) )
                
            return list_neighbors
                
        else:
            print("No neighbors found or empty response.")
            return None

    except Exception as e:
        print(f"An error occurred during the search: {e}")



def Pil_to_array(image_pil):
    # make the image in the compatible format to be passed to DeepFace

    # Convert the Pillow image to a NumPy array
    image_np_rgb = np.array(image_pil)

    # Extract the individual color channels (R, G, B)
    red_channel = image_np_rgb[:, :, 0]
    green_channel = image_np_rgb[:, :, 1]
    blue_channel = image_np_rgb[:, :, 2]

    # Stack the channels in BGR order
    return np.stack([blue_channel, green_channel, red_channel], axis=-1)


def generate_img_embedding(img_pil):
    from deepface import DeepFace
    # given an img_pil, it generates it's embedding
    
    img_array = Pil_to_array(image_pil)

    embd = DeepFace.represent(img_array)[0]['embedding']

    return embd



def get_encoded_images_from_paths(paths):
    """
    Encodes a list of image files specified by their paths into base64 strings.

    paths (List[str]): A list of paths to image files.

    """
    encoded_images: List[str] = []
    for img_path in paths:
        encoded_img = encode_image_to_base64(BUCKET_NAME , DATASET_ADD + img_path)
        if encoded_img:
            encoded_images.append(encoded_img)
        else:
            # Log or handle missing files if needed
            print(f"Failed to load or encode image for return: {img_path}")
    return encoded_images


def encode_image_to_base64(bucket_name, blob_name):
    """
    Reads an image file (local or from Google Cloud Storage) and encodes it into a base64 string.

    Returns str of the base64 encoded string of the image, otherwise None if the file doesn't exist or an error occurs.
    """
    try:
        client = storage.Client()

        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        image_bytes = blob.download_as_bytes()

        encoded_bytes = base64.b64encode(image_bytes)
        encoded_string = encoded_bytes.decode('utf-8')
        
        return encoded_string

    except Exception as e:
        print(f"Error encoding image from GCS {bucket_name}/{blob_name}: {e}")
        return None




def handle_embedding(img_embd):
    # This function recieves an image embedding, performs vector search, and returns the results.


    # Perform vector search using Vector AI's search engine
    try:
        nearest_neighbor_list = vector_search_NN(img_embd , NUM_NEIGHBORS = NUM_NEIGHBORS)

    except Exception as e:
        print(f"Error in Vector search. Err: {e}")
        raise HTTPException(status_code=500, detail=f"CError in Vector search: {e}")


    if nearest_neighbor_list is None:
        return {
        "message": "⚠️ The image query can not be identified!",
        "returned_images": [], 
        "code": 0,
        "identity": "Unknown"
    }


    # retrieve the path of the actual images from GCS based on the search result
    print("The initial candidates: ", nearest_neighbor_list)
    
    img_paths_list = []
    
    for n in nearest_neighbor_list:

        if n[1]>= 0.25: # the threshold used by the embedding model (VGG)
            img_paths_list.append(n[0])
        else:
            print("This retrieved image not selected: ", n)

    
    if len(img_paths_list)<1: # all rejected 
            return {
        "message": "⚠️ The image query can not be identified!",
        "returned_images": [], 
        "code": 0,
        "identity": "Unknown"
    }



    try:
        most_frequent_name, freq = find_most_frequent_ID(img_paths_list)

        print(f"Most frequent name: {most_frequent_name}, freq: {freq}")


        if freq < math.ceil(NUM_NEIGHBORS/2): # the fraction of accepted images is too low
            return {
        "message": "⚠️ The image query can not be identified!",
        "returned_images": [], 
        "code": 0,
        "identity": "Unknown"}


    except Exception as e:
        print(f"Error in finding the most frequent ID. Err: {e}")
        raise HTTPException(status_code=500, detail=f"Error in finding the most frequent ID. Err: {e}")



    # Return a success response
    print(f"Encoding images to return...")
    returned_images = get_encoded_images_from_paths(img_paths_list)
    print(f"Prepared {len(returned_images)} images to return.")

    return {
        "message": "✅ The image query uccessfully identified!",
        "returned_images": returned_images, 
        "code": 1,
        "identity": most_frequent_name
    }
