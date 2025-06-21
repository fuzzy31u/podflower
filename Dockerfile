FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies (minimal set for API only)
RUN pip install --no-cache-dir \
    flask \
    google-cloud-aiplatform[adk,agent_engines]>=1.97.0

# Copy the API file
COPY simple_test_api.py .

# Set environment variables
ENV PORT=8080
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "simple_test_api.py"] 