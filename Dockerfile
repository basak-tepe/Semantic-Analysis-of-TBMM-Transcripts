FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy API requirements (minimal, excludes heavy ML libraries)
COPY requirements-api.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-api.txt

# Create directories
RUN mkdir -p /app/data /app/src /app/api

# Copy API code
COPY api/ /app/api/

# Copy required data files EXPLICITLY
COPY data/mps_aggregated_by_term.csv /app/data/
#COPY data/topic_summary.csv /app/data/

# Copy required src files EXPLICITLY
COPY src/mp_aggregated_lookup.py /app/src/
#COPY src/mp_name_normalizer.py /app/src/
#COPY src/mp_party_lookup.py /app/src/
COPY src/widid_results/ /app/src/widid_results/

# Expose port (Cloud Run will set $PORT)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Run the application
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}
