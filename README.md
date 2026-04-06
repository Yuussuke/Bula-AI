# Bula AI

Bula AI is an AI-powered application that helps users understand Brazilian medication package inserts (bulas) through natural language questions. Users can upload a PDF and receive clear, simplified answers based strictly on the document content. The system uses a retrieval-based approach to ensure accuracy and reduce hallucinations. It is designed to improve accessibility of medical information while maintaining safety.

## Tech Stack

- **Backend:** Python / FastAPI
- **Database:** PostgreSQL 15
- **Infrastructure:** Docker / Docker Compose

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed on your machine.

### Running the project

1. (Optional) Copy the example environment file and adjust values if needed:

   ```bash
   cp .env.example .env
   ```

2. Start all services with a single command:

   ```bash
   docker compose up
   ```

   Docker will build the backend image and start both the API and the database.

### Accessing the API

Once the containers are running, open your browser or use `curl` to reach the health-check endpoint:

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

The interactive API docs (Swagger UI) are also available at:

```
http://localhost:8000/docs
```
