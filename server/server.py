from utils import *


# Create the FastAPI application instance
app = FastAPI()


# --- API Endpoint ---
# this is to handle the case where the embedding is recieved, in which case the extraction of embedding is performed on the client side. 
@app.post("/embed", response_model=dict)
async def face_retrieval_by_emb(payload: DataPayload):
    
    img_embd = payload.data
    print(f"Received request for /embed endpoint: Size of embedding: {len(img_embd)}")


    try:
        
       return_val = handle_embedding(img_embd)

       return return_val


    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error processing upload: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")





# this is to handle the case where the actual image recieved, in which case the extraction of embedding is performed on the server side. 
@app.post("/faceimage", response_model=dict)
async def face_retrieval_by_img(file: UploadFile = File(...)):
    
    print(f"Received request for /faceimage endpoint for file: {file.filename}")
    try:
        contents = await file.read()

        # Open the image using Pillow from the bytes
        try:
            image = Image.open(io.BytesIO(contents))
            print(f"Successfully decoded image: {file.filename} (Format: {image.format})")

        except Exception as decode_error:
            print(f"Error decoding image {file.filename}: {decode_error}")
            raise HTTPException(status_code=400, detail=f"Invalid image file or format: {decode_error}")


        # Generate the embedding of the image
        try:
            img_embd = generate_img_embedding(image)
            print(f"Successfully embedded the image.")

        except Exception as e:
            print(f"Error embedding the image: {e}")
            raise HTTPException(status_code=500, detail=f"Could not embed the image.")


        
        return_val = handle_embedding(img_embd)

        return return_val


    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error processing upload for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {e}")
    finally:
        await file.close()





if __name__ == "__main__":
    import uvicorn

    print("Starting server with uvicorn...")
    
    uvicorn.run(app, host="0.0.0.0", port=8080)
