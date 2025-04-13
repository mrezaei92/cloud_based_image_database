#!/bin/bash

# --- Configuration ---

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: GCP Project ID not set. Use 'gcloud config set project YOUR_PROJECT_ID'"
    exit 1
fi
echo "Using GCP Project ID: $PROJECT_ID"

# Prompt for the GCP region/location of the Artifact Registry
read -p "Enter the GCP location of the repository (e.g., us-central1, europe-west2): " LOCATION
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

ARTIFACT_REGISTRY_HOST="${LOCATION}-docker.pkg.dev"
REPO_PATH="${ARTIFACT_REGISTRY_HOST}/${PROJECT_ID}/${REPO_NAME}" # Base path for images

echo "----------------------------------------"
echo "Project ID:       $PROJECT_ID"
echo "Location:         $LOCATION"
echo "Repository Name:  $REPO_NAME"
echo "Repository Path:  $REPO_PATH"
echo "----------------------------------------"

echo "Fetching unique image names from repository: $REPO_NAME..."

# Use gcloud to list packages (unique image names) in the repository
# Format extracts the full resource name.
package_list_output=$(gcloud artifacts packages list \
    --repository="$REPO_NAME" \
    --location="$LOCATION" \
    --project="$PROJECT_ID" \
    --format='value(name)')

# Check if the gcloud command *itself* failed (exit status != 0)
if [ $? -ne 0 ]; then
    echo "Error: gcloud command failed while fetching package list. See messages above."
    exit 1
fi

# Check if the *output* (list of names) is empty
if [[ -z "$(echo "$package_list_output" | tr -d '[:space:]')" ]]; then
    echo "No image names (packages) found in repository '$REPO_NAME'."
    exit 0
fi

echo "Available image names:"

declare -a image_names # Declare an array to store unique image names
name_count=0

while IFS= read -r line; do
    # Skip empty lines that might occur
    [[ -z "$line" ]] && continue

    # Extract the base image name (the part after the last '/')
    image_name=$(basename "$line")
    [[ -z "$image_name" ]] && continue # Skip if basename extraction failed

    name_count=$((name_count + 1))
    image_names[$name_count]="$image_name" # Store the simple name

    # Display the numbered entry to the user
    echo "$name_count: $image_name"

done < <(echo "$package_list_output")

# Check if any valid names were actually processed
if [ "$name_count" -eq 0 ]; then
    echo "No valid image names found after parsing."
    exit 0
fi

echo "----------------------------------------"

selected_number=0
while true; do
    read -p "Enter the number of the image name you want to deploy: " selected_number
    # Check if input is a number and within the valid range
    if [[ "$selected_number" =~ ^[0-9]+$ ]] && [ "$selected_number" -ge 1 ] && [ "$selected_number" -le "$name_count" ]; then
        break
    else
        echo "Invalid input. Please enter a number between 1 and $name_count."
    fi
done

SELECTED_IMAGE_NAME="${image_names[$selected_number]}"
echo "You selected image name: $SELECTED_IMAGE_NAME"


SELECTED_IMAGE_PATH="${REPO_PATH}/${SELECTED_IMAGE_NAME}:latest" # Base path for images



echo "----------------------------------------"
echo "Preparing to deploy..."
echo "Selected Image for deployment: $SELECTED_IMAGE_PATH"
echo ""

read -p "Enter app service name: " YOUR_SERVICE_NAME

gcloud run deploy $YOUR_SERVICE_NAME --image=$SELECTED_IMAGE_PATH --region=$LOCATION --platform=managed --memory=8Gi --cpu=2 --allow-unauthenticated




exit 0
