# Backend - FastAPI

This backend project is built with modern Python technologies to provide a robust, maintainable, and scalable API service.

## Tech Stack

- **FastAPI**: Modern, fast (high-performance) web framework for building APIs with Python 3.7+ and full async/await support.
- **SQLAlchemy (Async)**: Powerful and flexible ORM for database operations, using async engine and sessions.
- **Alembic**: Database migrations tool for SQLAlchemy.  
  _See [Migration Docs](./migrations/README.md) for details._
- **Pydantic**: Data validation and settings management using Python type annotations.
- **Uvicorn**: Lightning-fast ASGI server for running FastAPI applications.
- **WebSocket**: Real-time, bidirectional communication support.
- **Keycloak**: Identity and access management for authentication.
- **Redis**: In-memory data store for caching and real-time features.
- **Docker**: Containerization for development and deployment.
- **Asyncio**: Native Python async event loop for high concurrency and performance.
- **Testing**: Pytest (asyncio, coverage); fully isolated environment with a dedicated test database.  
  _See [Test Docs](./tests/README.md) for details._
- **Modbus**: Industrial communication protocol support for PLC and IoT device integration.

## Features

- 🚀 High-performance async API with FastAPI
- 🗄️ Async database integration with SQLAlchemy and Alembic
- 🧩 Modular, scalable project structure
- 🔒 Middleware support (CORS, custom middlewares)
- 📝 Data validation with Pydantic
- ⚡ Full async/await support for endpoints and database operations
- 🐳 Easy containerization with Docker
- ✅ Async Testing & coverage with a fully isolated test environment
- 🔌 Real-time communication via WebSocket
- 🔐 Secure authentication and SSO with Keycloak
- ⚡ Fast caching and pub/sub with Redis
- 🏭 Industrial IoT integration with Modbus TCP support
- 🔄 Asynchronous Modbus communication for high-performance industrial data handling