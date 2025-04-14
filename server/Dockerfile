# Use a Python base image (slim version for smaller size)
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . /app

# Expose the port that your application listens on (Cloud Run default is 8080, but you can change it)
EXPOSE 8080

# Set the environment variable for the port (Cloud Run uses this)
ENV PORT 8080

# Command to run the application using Uvicorn (adjust if needed)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
