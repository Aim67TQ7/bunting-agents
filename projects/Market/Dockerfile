# Use an official Python runtime as a parent image.
FROM python:3.9-slim

# Set the working directory in the container.
WORKDIR /app

# Copy the current directory contents into the container at /app.
COPY docket.py ./

# (Optional) If you want to copy any additional files or requirements, do it here.

# Ensure the Python script is executable (if you plan to run it directly).
RUN chmod +x docket.py

# Run the docket program.
# You can call it directly if the shebang is correct,
# or by explicitly using the python interpreter.
CMD ["python", "docket.py"]
