# Use an official Python base image (Debian)
FROM python:3.12

# Install dependencies
RUN apt update && apt install -y osslsigncode dirmngr ca-certificates gnupg

# Add mono repository
RUN echo "deb [trusted=yes] https://download.mono-project.com/repo/debian stable-buster main" | tee /etc/apt/sources.list.d/mono-official-stable.list

# Install mono-complete package
RUN apt update && apt install -y mono-complete

# Set the working directory inside the container
WORKDIR /PositiveIntent

# Copy PositiveIntent to container working directory
COPY . .

# Install Python dependencies
RUN pip install -r requirements.txt

# Set the entry point to allow passing arguments
ENTRYPOINT ["python", "build.py"]
