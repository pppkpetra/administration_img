# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt /app/


# Copy the current directory contents into the container at /app
COPY . /app

RUN apt-get update && apt-get install -y postgresql-server-dev-all build-essential && rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 7000

# Define environment variable
ENV FLASK_APP=app.py 
ENV FLASK_ENV=development
ENV FLASK_DEBUG=0

CMD ["flask","run","--host=0.0.0.0", "--port=7000"]

# # Run app.py when the container launches
# CMD ["python", "app.py"]

