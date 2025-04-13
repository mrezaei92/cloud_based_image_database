#!/bin/bash


read -p "Enter the project ID: " PROJECT_ID

# Prompt for the GCP region/location for the Artifact Registry
read -p "Enter the GCP location (e.g., us-central1, europe-west2): " LOCATION
if [ -z "$LOCATION" ]; then
    echo "Error: Location cannot be empty."
    exit 1
fi

# Prompt for the Artifact Registry repository name
read -p "Enter the Artifact Registry repository name: " REPO_NAME
if [ -z "$REPO_NAME" ]; then
    echo "Error: Repository name cannot be empty."
    exit 1
fi

# Prompt for the local Docker image name (e.g., my-app)
read -p "Enter the local Docker image name: " LOCAL_IMAGE_NAME
if [ -z "$LOCAL_IMAGE_NAME" ]; then
    echo "Error: Local image name cannot be empty."
    exit 1
fi

read -p "Enter the local Docker image tag (default: latest): " LOCAL_IMAGE_TAG
LOCAL_IMAGE_TAG=${LOCAL_IMAGE_TAG:-latest} # Default to 'latest' if empty



gcloud config set project $PROJECT_ID
# --- Construct Full Image Names ---
LOCAL_IMAGE_FULL="$LOCAL_IMAGE_NAME:$LOCAL_IMAGE_TAG"
ARTIFACT_REGISTRY_HOST="${LOCATION}-docker.pkg.dev"
TARGET_IMAGE_NAME="${ARTIFACT_REGISTRY_HOST}/${PROJECT_ID}/${REPO_NAME}/${LOCAL_IMAGE_NAME}:${LOCAL_IMAGE_TAG}"

echo "----------------------------------------"
echo "Project ID:       $PROJECT_ID"
echo "Location:         $LOCATION"
echo "Repository Name:  $REPO_NAME"
echo "Local Image:      $LOCAL_IMAGE_FULL"
echo "Target AR Image:  $TARGET_IMAGE_NAME"
echo "----------------------------------------"
read -p "Proceed with these details? (y/N): " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1



# --- Check if Local Image Exists ---
echo "Checking if local Docker image '$LOCAL_IMAGE_NAME' exists..."
if ! docker image inspect "$LOCAL_IMAGE_NAME" > /dev/null 2>&1; then
    echo "Error: Local Docker image '$LOCAL_IMAGE_NAME' not found."
    echo "Please build the image first (e.g., 'docker build -t $LOCAL_IMAGE_NAME .')"
    exit 1
fi
echo "Local image found."


# --- Check/Create Artifact Registry Repository ---
echo "Checking if Artifact Registry repository '$REPO_NAME' exists in '$LOCATION'..."
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$LOCATION" --project="$PROJECT_ID" > /dev/null 2>&1; then
    echo "Repository '$REPO_NAME' not found. Creating it..."
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$LOCATION" \
        --description="Docker repository created by script" \
        --project="$PROJECT_ID"

    # Check if repository creation was successful
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create Artifact Registry repository '$REPO_NAME'."
        exit 1
    fi
    echo "Repository '$REPO_NAME' created successfully."
else
    echo "Repository '$REPO_NAME' already exists."
fi

# --- Configure Docker Authentication ---
echo "Configuring Docker authentication for $ARTIFACT_REGISTRY_HOST..."
gcloud auth configure-docker "$ARTIFACT_REGISTRY_HOST" --quiet

if [ $? -ne 0 ]; then
    echo "Error: Failed to configure Docker authentication."
    echo "Ensure you have the necessary permissions."
    exit 1
fi
echo "Docker authentication configured successfully."

# --- Tag the Docker Image ---
echo "Tagging local image '$LOCAL_IMAGE_FULL' as '$TARGET_IMAGE_NAME'..."
docker tag "$LOCAL_IMAGE_FULL" "$TARGET_IMAGE_NAME"

if [ $? -ne 0 ]; then
    echo "Error: Failed to tag the Docker image."
    exit 1
fi
echo "Image tagged successfully."

# --- Push the Docker Image ---
echo "Pushing image '$TARGET_IMAGE_NAME' to Artifact Registry..."
docker push "$TARGET_IMAGE_NAME"

if [ $? -ne 0 ]; then
    echo "Error: Failed to push the Docker image to Artifact Registry."
    exit 1
fi

echo "----------------------------------------"
echo "Successfully pushed image:"
echo "$TARGET_IMAGE_NAME"
echo "----------------------------------------"

exit 0
