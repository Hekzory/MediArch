# MediArch - Medical Records Management System

MediArch is a web-based medical records management system built with Flask and Python 3.13. It provides a clean, intuitive interface for healthcare providers to manage patient records efficiently.

## Features

- Patient information management (add, view, edit, delete)
- Secure PostgreSQL database for data storage
- Modern UI using Tailwind CSS
- Responsive design for desktop and mobile use

## Technology Stack

- **Python 3.13**: Latest Python version with improved performance and features
- **Flask 3.1+**: Lightweight WSGI web application framework
- **SQLAlchemy 2.0+**: SQL toolkit and Object-Relational Mapping (ORM) library
- **PostgreSQL**: Robust, enterprise-grade database
- **uv**: Fast Python package installer and resolver
- **Tailwind CSS**: Utility-first CSS framework
- **Docker**: Containerization for easy deployment

## Getting Started

### Prerequisites

- Python 3.13+
- Docker and Docker Compose (for containerized setup)
- uv package installer (recommended)

### Installation

#### Docker Setup

1. Build and start the containers:
   ```
   make build
   make up
   ```

2. The application will be available at http://localhost:8000

## Project Structure

```
MediArch/
├── src/
│   └── mediarch/
│       ├── static/
│       │   ├── css/
│       │   └── js/
│       ├── templates/
│       ├── __init__.py
│       ├── models.py
│       └── routes.py
├── tests/
├── app.py
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── docker-compose.yaml
└── README.md
```

## Testing

Run tests using pytest:

```
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

