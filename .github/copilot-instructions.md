# NexVest - Copilot Instructions

## Project Overview

NexVest is a FastAPI + Python financial analytics backend that provides advanced financial analysis capabilities through custom algorithms and data processing pipelines.

## Technology Stack

- **Backend Framework**: FastAPI (Python)
- **Database**: MongoDB Atlas (using pymongo)
- **Frontend Integration**: CORS enabled for React applications
- **Language**: Python 3.x

## Project Structure

```
nexvest/
├── routers/          # API route handlers
│   ├── etl.py       # ETL operations endpoints
│   ├── similarity.py # Similarity analysis endpoints
│   ├── risk.py      # Risk analysis endpoints
│   ├── patterns.py  # Pattern detection endpoints
│   └── reports.py   # Reporting endpoints
├── algorithms/       # Custom algorithm implementations
│   ├── euclidean.py # Euclidean distance calculation
│   ├── pearson.py   # Pearson correlation
│   ├── dtw.py       # Dynamic Time Warping
│   └── cosine.py    # Cosine similarity
├── etl/             # ETL pipeline components
│   ├── downloader.py # Raw HTTP requests for data download
│   ├── cleaner.py   # Data cleaning and preprocessing
│   └── storage.py   # Database storage operations
├── requirements.txt  # Python dependencies
└── .env.example     # Environment variables template
```

## Architecture Guidelines

### Algorithms
- **All algorithms must be implemented from scratch**
- **DO NOT use**: sklearn, yfinance, or any pre-built ML libraries for core algorithms
- Implement: Euclidean distance, Pearson correlation, Dynamic Time Warping (DTW), and Cosine similarity manually
- Focus on mathematical accuracy and performance optimization

### ETL Pipeline
- Use **raw HTTP requests** for data downloading (requests library)
- No external financial APIs like yfinance
- Implement custom data cleaners for financial data
- Store processed data in MongoDB Atlas

### API Design
- Follow FastAPI best practices
- Use appropriate HTTP methods (GET, POST, PUT, DELETE)
- Implement proper request/response models with Pydantic
- Include comprehensive error handling
- Document all endpoints with OpenAPI/Swagger

### Database
- Use MongoDB Atlas as the primary database
- Connect via pymongo
- Store connection string in environment variables
- Implement proper connection pooling
- Use appropriate indexes for performance

### CORS Configuration
- Enable CORS for React frontend applications
- Configure appropriate origins, methods, and headers
- Use FastAPI's CORSMiddleware

## Environment Variables

Required environment variables (see `.env.example`):
- `MONGO_URI`: MongoDB Atlas connection string

## Development Guidelines

1. **Code Style**: Follow PEP 8 conventions
2. **Type Hints**: Use type annotations for function parameters and return values
3. **Error Handling**: Implement proper try-catch blocks and return meaningful error messages
4. **Documentation**: Add docstrings to all functions and classes
5. **Testing**: Write unit tests for algorithms and integration tests for API endpoints
6. **Security**: Never commit `.env` file or expose sensitive credentials

## Dependencies Management

- All dependencies should be listed in `requirements.txt`
- Keep dependencies minimal and well-justified
- Pin versions for reproducibility

## Common Tasks

### Adding a New Router
1. Create a new file in `routers/` directory
2. Define APIRouter with appropriate prefix and tags
3. Implement endpoint functions with proper models
4. Register router in main application file

### Implementing a New Algorithm
1. Create a new file in `algorithms/` directory
2. Implement the algorithm from scratch (no sklearn/external libs)
3. Add comprehensive docstrings explaining the math
4. Write unit tests to verify correctness
5. Optimize for performance where possible

### ETL Operations
1. Downloader: Use `requests` library for HTTP calls
2. Cleaner: Implement data validation and transformation logic
3. Storage: Use pymongo to interact with MongoDB

## Best Practices

- Keep algorithms pure and testable
- Separate business logic from route handlers
- Use dependency injection for database connections
- Implement proper logging
- Handle edge cases gracefully
- Validate all input data
- Return appropriate HTTP status codes
