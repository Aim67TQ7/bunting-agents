# School Bus Route Optimizer - Frontend

## Overview
Modern React dashboard for the School Bus Route Optimization System. Built with TypeScript, Tailwind CSS, and React Query for optimal performance and user experience.

## Key Features
- **Role-based Dashboard**: Different views for Admin, District Admin, Driver, and Parent users
- **Real-time Updates**: Live GPS tracking and route notifications
- **Interactive Maps**: Route visualization with Leaflet integration
- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **Advanced Analytics**: Charts and reports with Recharts
- **PWA Ready**: Progressive Web App capabilities for mobile devices

## Tech Stack
- **React 18** - Latest React with concurrent features
- **TypeScript** - Type safety throughout the application
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Query** - Server state management and caching
- **Zustand** - Client state management
- **React Hook Form** - Form handling with validation
- **Socket.io Client** - Real-time WebSocket communication
- **Leaflet** - Interactive maps for route visualization
- **Recharts** - Data visualization and analytics

## Prerequisites
- Node.js 18+
- npm or yarn
- Backend server running on localhost:3000

## Quick Start

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start Development Server
```bash
npm run dev
```

The application will be available at `http://localhost:3001`

### 3. Build for Production
```bash
npm run build
npm run preview
```

## Project Structure
```
frontend/
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── auth/         # Authentication components
│   │   ├── layout/       # Layout components (Sidebar, Header)
│   │   └── ui/           # Base UI components
│   ├── pages/            # Route-based page components
│   │   ├── auth/         # Login, register pages
│   │   ├── dashboard/    # Main dashboard
│   │   ├── routes/       # Route management
│   │   ├── students/     # Student management
│   │   ├── buses/        # Fleet management
│   │   ├── drivers/      # Driver management
│   │   ├── tracking/     # Real-time tracking
│   │   ├── analytics/    # Reports and analytics
│   │   └── settings/     # System settings
│   ├── services/         # API services and HTTP client
│   ├── store/            # Global state management
│   ├── types/            # TypeScript type definitions
│   ├── hooks/            # Custom React hooks
│   └── utils/            # Helper functions
├── public/               # Static assets
└── dist/                 # Build output
```

## Key Components

### Authentication System
- JWT-based authentication with refresh tokens
- Role-based access control
- Persistent session storage
- Automatic token refresh

### Dashboard Features
- Overview statistics and metrics
- Recent activity feed
- Quick action buttons
- Role-specific content

### Real-time Features
- WebSocket connection for live updates
- GPS tracking visualization
- Push notifications
- ETA calculations

## Available Scripts

### Development
- `npm run dev` - Start development server
- `npm run type-check` - Run TypeScript type checking
- `npm run lint` - Run ESLint

### Production
- `npm run build` - Build for production
- `npm run preview` - Preview production build

## Environment Configuration
The app uses Vite's proxy configuration to route API calls to the backend. No additional environment variables are required for basic setup.

## API Integration
All API calls are handled through:
- `services/api/client.ts` - Axios client with interceptors
- `services/api/authApi.ts` - Authentication endpoints
- Additional API services for each feature domain

## State Management
- **Authentication**: Zustand store with persistence
- **Server State**: React Query for caching and synchronization
- **UI State**: React's built-in state and context

## Styling System
- **Tailwind CSS**: Utility classes for rapid development
- **Custom Components**: Pre-built component classes
- **Responsive Design**: Mobile-first breakpoints
- **Dark Mode**: Ready for dark theme implementation

## Real-time Communication
WebSocket integration for:
- GPS position updates
- Route status changes
- System notifications
- ETA updates

## Testing Strategy
- Component testing with React Testing Library
- E2E testing with Cypress
- Type safety with TypeScript
- API integration testing

## Performance Optimizations
- Code splitting with React.lazy
- Image optimization and lazy loading
- Bundle size monitoring
- Caching strategies with React Query

## Mobile Features
- Progressive Web App (PWA) ready
- Offline capabilities
- Push notifications
- Mobile-optimized layouts

## Browser Support
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing
1. Follow TypeScript strict mode
2. Use Tailwind CSS classes consistently
3. Implement proper error handling
4. Add loading states for async operations
5. Ensure mobile responsiveness