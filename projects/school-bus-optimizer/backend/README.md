# School Bus Route Optimizer - Backend

## Overview
This is the backend API for the School Bus Route Optimization System, a B2B SaaS platform that helps school districts reduce transportation costs by 15-30% through AI-powered route optimization.

## Key Features
- **Route Optimization**: Advanced algorithms to minimize distance and time
- **Real-time GPS Tracking**: WebSocket-based live bus tracking
- **Multi-tenant Architecture**: Secure data isolation between districts
- **Role-based Access Control**: Admin, District Admin, Driver, and Parent roles
- **PostGIS Integration**: Geospatial queries for efficient route calculations

## Prerequisites
- Node.js 18+ 
- PostgreSQL 14+ with PostGIS extension
- Redis 6+
- Google Maps API key

## Setup Instructions

### 1. Install Dependencies
```bash
cd backend
npm install
```

### 2. Database Setup
```bash
# Create PostgreSQL database
createdb school_bus_optimizer

# Enable PostGIS extension (run in psql)
CREATE EXTENSION IF NOT EXISTS postgis;
```

### 3. Environment Configuration
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your configuration
# Required: DATABASE_URL, JWT_SECRET, GOOGLE_MAPS_API_KEY
```

### 4. Run Migrations & Seed Data
```bash
# Compile TypeScript
npm run build

# Run database migrations
npm run migrate

# Seed with test data
npm run seed
```

### 5. Start Development Server
```bash
npm run dev
```

The server will start on `http://localhost:3000`

## API Documentation
Swagger documentation available at: `http://localhost:3000/api-docs`

## Test Credentials
After seeding, use these credentials:
- **Super Admin**: admin@schoolbusoptimizer.com / superadmin123
- **District Admin**: admin@riversideschooldistrict.edu / admin123
- **Driver**: driver1@riversideschooldistrict.edu / driver123
- **Parent**: parent1@email.com / parent123

## Core Technologies
- **Express.js**: Web framework
- **TypeScript**: Type safety
- **Sequelize**: ORM with PostGIS support
- **Socket.io**: Real-time WebSocket communication
- **JWT**: Authentication
- **Redis**: Caching and session management
- **Google Maps API**: Routing and geocoding

## Route Optimization Algorithm
The system uses a hybrid approach:
1. **DBSCAN Clustering**: Groups nearby students
2. **Nearest Neighbor**: Initial route construction
3. **2-opt Optimization**: Route improvement
4. **Constraint Handling**: Capacity, time windows, distance limits

## Project Structure
```
backend/
├── src/
│   ├── config/         # Database, Redis configuration
│   ├── controllers/    # Request handlers
│   ├── middleware/     # Auth, validation, error handling
│   ├── models/         # Sequelize models
│   ├── routes/         # API route definitions
│   ├── services/       # Business logic
│   ├── utils/          # Helper functions
│   └── websocket/      # Real-time handlers
├── migrations/         # Database migrations
├── seeds/             # Test data
└── tests/             # Unit and integration tests
```

## Key API Endpoints
- `POST /api/auth/login` - User authentication
- `POST /api/routes/district/:id/optimize` - Optimize routes
- `GET /api/tracking/buses/:id/location` - Get bus location
- `WS /ws/tracking/:busId` - Real-time tracking subscription

## Performance Metrics
- Route optimization: < 2 minutes for 500+ students
- GPS updates: < 1 second latency
- API response time: < 200ms average
- Concurrent connections: 1000+ WebSocket clients

## Security Features
- JWT with refresh tokens
- Role-based access control
- Multi-tenant data isolation
- Rate limiting
- Input validation
- Encrypted sensitive data

## Monitoring
- Winston logging with different levels
- Error tracking ready for Sentry integration
- Performance metrics via custom middleware
- Health check endpoint at `/health`