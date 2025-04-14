import streamlit as st
import requests
import os
from io import BytesIO
from PIL import Image
import time
import base64
from deepface import DeepFace
import numpy as np


DEFAULT_SERVER_URL = "http://localhost:8080/embed" # Example local URL

REQUEST_TIMEOUT = 20.0  # Increased timeout for potential upload + processing + network latency


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



def display_images(images_data, title="Returned Images"):
    """
    Display a grid of images (base64 encoded strings) using Streamlit.

    Args:
        images_data (list): A list of base64 encoded image strings.
        title (str, optional): The title to display above the images. Defaults to "Returned Images".
    """
    st.header(title)
    if not images_data:
        st.write("No images to display.") # This handles empty list *after* decoding
        return

    images_bytes = []
    for item in images_data:
        if isinstance(item, str):
             try:
                 missing_padding = len(item) % 4
                 if missing_padding:
                     item += '='* (4 - missing_padding)
                 images_bytes.append(base64.b64decode(item))
             except (base64.binascii.Error, Exception) as e:
                 st.error(f"Error decoding image data: {e}. Data length: {len(item)}")
                 continue
        else:
             st.warning(f"Received unexpected data type for display: {type(item)}")

    if not images_bytes:
        st.write("No valid image data received or decoded.")
        return

    num_images = len(images_bytes)
    if num_images <= 3:
        num_cols = num_images
    elif num_images <= 6:
        num_cols = 3
    else:
        num_cols = 4 

    if num_images > 0 and num_cols <= 0:
        num_cols = 1

    if num_images > 0:
        cols = st.columns(num_cols)
        for i, img_bytes in enumerate(images_bytes):
            try:
                image = Image.open(BytesIO(img_bytes))
                with cols[i % num_cols]:
                    st.image(image, use_container_width=True) 
            except Exception as e:
                st.error(f"Error displaying image {i+1}: {e}")



def upload_and_get_images(image_bytes, pil_image , filename="uploaded_image.jpg", server_url=""):
    """
    Uploads image bytes to the specified server URL's /face endpoint using POST
    and expects a JSON response containing returned images and a code.

    Args:
        image_bytes (bytes): The image data as bytes.
        pil_image: (Image): the image as PIL Image
        filename (str): The filename to use for the upload.
        server_url (str): The full URL of the server endpoint.

    Returns:
        tuple: (status, data) where status is one of ['success', 'timeout', 'error']
               and data is the full JSON response dictionary on success,
               or an error message otherwise.
    """
    if not server_url:
        return "error", "Server URL is not configured."



    endpoint = server_url.split("/")[-1]



    try:
        if endpoint == "embed": # when the client wants to send the embedding as query

            try:
                img_array = Pil_to_array(pil_image)
                img_embd = DeepFace.represent(img_array)[0]['embedding']
                payload = {"data": img_embd}

                st.write(f"***** {len(img_embd)} *********")

                if not isinstance(img_embd, list):
                    return "error during embedding, the output is not a list", "error during embedding, the output is not a list"

            except Exception as e:
                return f"error during embedding: {e}", f"error during embedding: {e}"


            response = requests.post(
                server_url,
                json=payload,  
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            result_data = response.json()
            return "success", result_data 



       
        elif endpoint == "faceimage": # this is when we want to send the actual image as the query
            
            data_payload = {"file": (filename, image_bytes)}
            
            response = requests.post(
                server_url,
                files=data_payload,
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status() 

            result_data = response.json()
            return "success", result_data 

        else:
            raise NotImplementedError(f"The server cannot handle the endpoint /{endpoint}. Use eihter /embed or /faceimage")



    except requests.exceptions.Timeout:
        return "timeout", f"Request timed out after {REQUEST_TIMEOUT} seconds."
    except requests.exceptions.HTTPError as http_err:
        error_detail = response.text
        try:
            error_json = response.json()
            if 'detail' in error_json:
                error_detail = error_json['detail']
        except Exception:
            pass 
        error_msg = f"HTTP error occurred: {http_err} - Detail: {error_detail}"
        return "error", error_msg
    except requests.exceptions.ConnectionError as conn_err:
         return "error", f"Connection error: Could not connect to {server_url}. Details: {conn_err}"
    except requests.exceptions.RequestException as req_err:
        return "error", f"Request error: {req_err}"
    except Exception as e:
        return "error", f"An unexpected error occurred during the request: {e}"






# --- Streamlit App ---

def main():

    st.set_page_config(layout="wide") 
    st.title("Face Image Retrieval")

    # --- Initialize Session State --- 
    if 'server_url' not in st.session_state:
        st.session_state.server_url = DEFAULT_SERVER_URL
    if 'request_state' not in st.session_state:
        st.session_state.request_state = 'idle' # idle, processing, received, timeout, error
    if 'result_data' not in st.session_state:
        st.session_state.result_data = None # Stores the full JSON response
    if 'show_results' not in st.session_state:
        st.session_state.show_results = False # Flag to display images area
    if 'uploaded_image_bytes' not in st.session_state:
        st.session_state.uploaded_image_bytes = None
    if 'uploaded_filename' not in st.session_state:
        st.session_state.uploaded_filename = None
    if 'error_message' not in st.session_state:
        st.session_state.error_message = None
    if 'image' not in st.session_state:
        st.session_state.image = None



    # --- Sidebar for Configuration --- 
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.session_state.server_url = st.text_input(
            "Server URL",
            value=st.session_state.server_url,
            placeholder="e.g., http://localhost:8080/face",
            help="Enter the full URL of the backend server endpoint."
        )
        st.caption(f"Current endpoint: {st.session_state.server_url}")
        st.markdown("---") # Separator

    
    # --- Main Page Layout --- 
    st.write("Upload an image containing a face. The system will indentify it based on similar faces in the database on the GCP server. ")
    col1, col2 = st.columns([1, 2]) # Left column for upload, right for results



    with col1:
        st.header("Upload The Face Image")
        uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "png", "jpeg"])

        if uploaded_file is not None:
            current_image_bytes = uploaded_file.getvalue()
            current_filename = uploaded_file.name

            bytes_io = BytesIO(current_image_bytes)
            curent_img = Image.open(bytes_io)


            if current_image_bytes != st.session_state.get('uploaded_image_bytes'):
                st.session_state.uploaded_image_bytes = current_image_bytes
                st.session_state.uploaded_filename = current_filename
                st.session_state.request_state = 'idle'
                st.session_state.result_data = None
                st.session_state.show_results = False
                st.session_state.error_message = None
                st.session_state.image = curent_img

            if st.session_state.uploaded_image_bytes:
                st.image(st.session_state.uploaded_image_bytes, caption="Query Image To Be Identified", width=300)

                if st.session_state.request_state == 'idle':
                    if st.button("🔍 Find Similar Faces"):
                        if not st.session_state.server_url or not st.session_state.server_url.lower().startswith(('http://', 'https://')):
                             st.error("Invalid or missing Server URL in the sidebar configuration.")
                        else:
                            st.session_state.request_state = 'processing'
                            st.session_state.show_results = False
                            st.session_state.result_data = None
                            st.session_state.error_message = None
                            st.rerun()


    if st.session_state.request_state == 'processing':
        if not st.session_state.uploaded_image_bytes:
            st.session_state.request_state = 'idle'
            st.warning("Please upload an image first.")
            st.rerun()
        else:
            with st.spinner(f"⏳ Searching for similar faces via {st.session_state.server_url}..."):
                status, data = upload_and_get_images(
                    st.session_state.uploaded_image_bytes,
                    st.session_state.image,
                    st.session_state.uploaded_filename,
                    server_url=st.session_state.server_url
                )

                if status == 'success':
                    st.session_state.request_state = 'received'
                    st.session_state.result_data = data
                elif status == 'timeout':
                    st.session_state.request_state = 'timeout'
                    st.session_state.error_message = data
                else: # error
                    st.session_state.request_state = 'error'
                    st.session_state.error_message = data

                st.rerun()



    with col2:
        st.header("Search Results")

        if st.session_state.request_state == 'received':
            server_msg = st.session_state.result_data.get('message', 'Processing successful.')
            st.success(f"{server_msg}")

            # Extract identity and response code safely using .get()
            identity = st.session_state.result_data.get('identity', 'N/A') 
            response_code = st.session_state.result_data.get('code', -1)

            # --- Display the Identity ---
            st.markdown(f"**Detected Identity:** `{identity}`") 

            # --- Handle Response Code ---
            if response_code == 0:
                st.info("ℹ️ No similar images found in the database.")
                st.session_state.show_results = False

            elif response_code == 1:
                if st.session_state.result_data and 'returned_images' in st.session_state.result_data and st.session_state.result_data['returned_images']:
                     st.session_state.show_results = True # Flag to show images below
                else:
                    st.warning("⚠️ Server indicated success (code=1), but no images were returned.")
                    st.session_state.show_results = False
            else:
                st.error(f"❓ Received unexpected response code from server: {response_code}")
                st.session_state.show_results = False


        elif st.session_state.request_state == 'timeout':
            st.warning(f"⏱️ Request Timeout: {st.session_state.error_message}" or "Timeout: Server did not respond in time.")

        elif st.session_state.request_state == 'error':
            st.error(f"❌ Request Error: {st.session_state.error_message}" or "An error occurred during the request.")
            if "connection error" in (st.session_state.error_message or "").lower():
                st.info("💡 Tip: Check if the server URL in the sidebar is correct and if the backend server is running.")


        # --- Show Results Area (Images) ---
        if st.session_state.request_state == 'received' and st.session_state.show_results:
            images_to_display = st.session_state.result_data.get('returned_images', [])
            if images_to_display:
                display_images(images_to_display, title="Similar Faces Found:")


if __name__ == "__main__":
    main()