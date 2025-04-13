#!/bin/bash

# Bash script to create a Google Cloud Storage bucket
# and upload the contents of a local folder to it.
# Includes a check for gcloud login status.

echo "-------------------------------------------"
echo "Checking Google Cloud authentication..."
echo "-------------------------------------------"

# --- Check gcloud command ---
if ! command -v gcloud &> /dev/null
then
    echo "Error: gcloud command could not be found."
    echo "Please install the Google Cloud SDK and ensure gcloud is in your PATH."
    exit 1
fi

# --- Check gsutil ---
if ! command -v gsutil &> /dev/null
then
    echo "Error: gsutil command could not be found."
    echo "Please install the Google Cloud SDK and ensure gsutil is in your PATH."
    exit 1
fi


# --- Check gcloud Authentication ---
# Check if there is an active authenticated account
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null)

if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "You are not logged into Google Cloud."
  echo "Attempting to initiate login..."
  # Attempt to log in - this will open a browser window
  gcloud auth login
  if [[ $? -ne 0 ]]; then
      echo "Error: gcloud login command failed. Please try logging in manually ('gcloud auth login') and then re-run the script."
      exit 1
  fi
  # Verify login was successful
  ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null)
  if [[ -z "$ACTIVE_ACCOUNT" ]]; then
      echo "Error: Login attempt failed or was cancelled. Please log in manually and re-run the script."
      exit 1
  else
      echo "Successfully logged in as: $ACTIVE_ACCOUNT"
  fi
else
  echo "Already logged in as: $ACTIVE_ACCOUNT"
fi
echo "-------------------------------------------"


# --- Configuration ---
# Prompt the user for the bucket name
read -p "Enter the desired GCS bucket name (must be globally unique): " BUCKET_NAME

# Prompt the user for the local folder path to upload
read -p "Enter the path to the local folder you want to upload: " LOCAL_FOLDER_PATH

read -p "Enter the project ID: " PROJECT_ID


# --- Validate Input ---
# Check if bucket name is provided
if [[ -z "$BUCKET_NAME" ]]; then
  echo "Error: Bucket name cannot be empty."
  exit 1
fi

# Check if the local folder exists
if [[ ! -d "$LOCAL_FOLDER_PATH" ]]; then
  echo "Error: Local folder '$LOCAL_FOLDER_PATH' not found or is not a directory."
  exit 1
fi

# Construct the GCS bucket URI
GCS_BUCKET_URI="gs://$BUCKET_NAME"



echo "-------------------------------------------"
echo "Attempting to create bucket: $GCS_BUCKET_URI"
echo "-------------------------------------------"

# --- Create Bucket ---
# Use gsutil to create the bucket.
gsutil mb "$GCS_BUCKET_URI"
if [[ $? -ne 0 ]]; then
    echo "Error: Failed to create bucket $GCS_BUCKET_URI."
    echo "Possible reasons: Bucket name already exists, insufficient permissions, or invalid name."
    exit 1
fi
echo "Bucket $GCS_BUCKET_URI created successfully."
echo "-------------------------------------------"


echo "-------------------------------------------"
echo "Attempting to upload folder: $LOCAL_FOLDER_PATH to $GCS_BUCKET_URI"
echo "-------------------------------------------"

# --- Upload Folder Contents ---
# If you want the folder itself (e.g., `gs://bucket/my_folder/...`), remove the trailing slash: "$LOCAL_FOLDER_PATH"
gsutil -m cp -r "$LOCAL_FOLDER_PATH" "$GCS_BUCKET_URI/"
if [[ $? -ne 0 ]]; then
    echo "Error: Failed to upload contents of $LOCAL_FOLDER_PATH."
    # echo "Attempting to remove partially created bucket..."
    gsutil rb "$GCS_BUCKET_URI"
    exit 1
fi

echo "-------------------------------------------"
echo "Successfully uploaded contents of '$LOCAL_FOLDER_PATH' to '$GCS_BUCKET_URI'."
echo "Script finished."
echo "-------------------------------------------"




echo "-------------------------------------------"
echo "Attempting to set project ID to: $PROJECT_ID"
echo "-------------------------------------------"

gcloud config set project $PROJECT_ID

if [ $? -eq 0 ]; then
  echo "Set command executed successfully."
  echo "Verifying the currently set project ID..."


  CURRENT_PROJECT=$(gcloud config get-value project)
  echo "Current project ID is configured as: $CURRENT_PROJECT"
  
  if [ "$CURRENT_PROJECT" = "$PROJECT_ID" ]; then
    echo "Verification successful: Project ID matches."
  else
    echo "Verification failed: Set project ID ($CURRENT_PROJECT) does not match the intended ID ($PROJECT_ID)."
  fi
else
  echo "Error: Failed to set the project ID."
fi



exit 0
