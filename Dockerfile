# Python Base Image
FROM python:3.11-slim

# Create current directory /app
WORKDIR /app

# Copies requirments file 
COPY requirements.txt .

# Downloads dependencies and packages
RUN pip install --no-cache-dir -r requirements.txt

# Copies whole current directory and puts it into current directory of image
COPY . .

# Where the database is written, mounted from the host at runtime
RUN mkdir -p /data
ENV DATA_DIR=/data

# The API listens here (documentation)
EXPOSE 8000

# Runs in command line when someone starts the container, --host allows container
# to accept connections with any interface
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]




