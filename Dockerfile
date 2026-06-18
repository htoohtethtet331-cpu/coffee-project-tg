FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the default port
EXPOSE 5000

# Run the application with Gunicorn, listening on the PORT environment variable or default to 5000
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} app:app
