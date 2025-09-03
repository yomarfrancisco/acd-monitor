# ACD Source Code

This directory contains the source code for the Algorithmic Coordination Diagnostic (ACD) platform.

## Structure

### Backend (`src/backend/`)
- **main.py**: FastAPI application entry point
- **analytics.py**: Core coordination detection algorithms
- **models.py**: Data models and database schemas (to be implemented)

### Frontend (`src/frontend/`)
- React/TypeScript application (to be implemented)
- Dashboard components and visualizations

### Tests (`src/tests/`)
- Unit and integration tests
- Test data and fixtures

## Development

### Backend Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
cd src/backend
python main.py

# Run tests
cd src/tests
python -m pytest
```

### Frontend Development
```bash
# Install dependencies (when implemented)
cd src/frontend
npm install

# Run development server
npm run dev
```

## Architecture

The backend follows a modular architecture:
- **API Layer**: FastAPI endpoints for data ingestion and analysis
- **Analytics Layer**: Core algorithms for coordination detection
- **Data Layer**: Database models and data persistence (to be implemented)
- **Integration Layer**: External data feeds and APIs (to be implemented)
