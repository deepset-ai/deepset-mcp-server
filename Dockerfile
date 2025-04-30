# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install uv - the recommended Python package installer
RUN pip install uv

# Copy dependency definitions
COPY pyproject.toml uv.lock .

# Install project dependencies using uv based on the lock file
RUN uv sync

# Copy the rest of the application code
COPY main.py .

# Make port 8000 available to the world outside this container
# Assuming FastMCP runs on port 8000 by default (common for FastAPI/Uvicorn)
EXPOSE 8000

# Define environment variables needed by the application
# These should be provided at runtime, not hardcoded
ENV DEEPSET_API_KEY="" 
ENV DEEPSET_WORKSPACE=""
# Set PYTHONUNBUFFERED to ensure logs are output immediately
ENV PYTHONUNBUFFERED=1

# Run main.py using uv when the container launches
# Assumes main.py calls mcp.run(host="0.0.0.0", port=8000)
CMD ["uv", "run", "mcp", "run", "main.py"]

# Alternative CMD if main.py directly runs the server using mcp.run()
# CMD ["python", "main.py"]
# Note: If using 'python main.py', ensure mcp.run() binds to 0.0.0.0 