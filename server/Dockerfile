FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Expose the port that your application listens on (Cloud Run default is 8080, but you can change it if you need to)
EXPOSE 8080

# Set the environment variable for the port (Cloud Run uses this)
ENV PORT 8080

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
