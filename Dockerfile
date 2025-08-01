FROM python:3.9-slim

# For local development, we can mount the src directory
# For production, we copy the src directory into the image
COPY ./src /app/src

# Set the working directory to the app directory
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

CMD ["python", "app.py"] 