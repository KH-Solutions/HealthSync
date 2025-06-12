# Use the official, lightweight Python image as a base
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# First, copy the dependencies file
# This allows Docker to use cache if dependencies don't change,
# which speeds up image building when code changes.
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory in the container
COPY . .

# Expose the port on which our application will run inside the container
EXPOSE 8000

# The command that will be run when the container starts
# Use --host 0.0.0.0 to make the application accessible from outside the container
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]