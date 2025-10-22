# Crypto Research Dashboard

A production-grade crypto-asset watchlist and comparison-graph subsystem with a clean, modern interface inspired by Coinbase's minimalist design and professional trading terminals.

## Features

- Real-time asset tracking with price updates
- Interactive watchlist with mini-charts
- Multi-asset comparison charts
- Responsive design with light/dark mode
- Smooth animations and transitions
- Local storage persistence

## Tech Stack

### Frontend
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: TailwindCSS + Framer Motion
- **Charts**: Recharts
- **State Management**: Zustand
- **Data Fetching**: React Query (TanStack Query)

### Backend
- **Framework**: FastAPI (Python)
- **Data Store**: In-memory storage (easily replaceable with PostgreSQL)

## Getting Started

### Prerequisites
- Node.js (v18.18.0 or later, < v21)
- Python (v3.8 or later)
- pip (Python package installer)

### Installation

1. **Frontend Setup**:
   ```bash
   npm ci
   ```

2. **Backend Setup**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

### Running the Application

1. **Start the Backend Server**:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. **Start the Frontend Development Server**:
   ```bash
   npm run dev
   ```

3. Open your browser to `http://localhost:3000`

### Production Build

To create a production build:
```bash
npm run build
```

To start the production server:
```bash
npm run start
```

## Project Structure

```
├── components/
│   ├── comparison/
│   └── watchlist/
├── lib/
│   ├── api.ts
│   └── store.ts
├── pages/
│   └── index.tsx
├── types/
│   └── index.d.ts
├── backend/
│   ├── main.py
│   └── requirements.txt
└── public/
```

## Architecture

### Frontend Architecture
- **State Management**: Zustand for global watchlist state with localStorage persistence
- **Data Fetching**: React Query for API calls with automatic caching and refetching
- **UI Components**: Modular, reusable components with TypeScript interfaces
- **Styling**: TailwindCSS with dark mode support and glass-morphism effects

### Backend Architecture
- **API Design**: RESTful endpoints with proper HTTP status codes
- **Data Models**: Pydantic models for request/response validation
- **Mock Data**: In-memory storage for demonstration purposes
- **CORS**: Configured for local development

## API Endpoints

### Assets
- `GET /api/assets` - Get all available assets with prices

### Watchlist
- `GET /api/watchlist` - Get user's watchlist
- `POST /api/watchlist` - Add asset to watchlist
- `DELETE /api/watchlist/{symbol}` - Remove asset from watchlist

### Comparison
- `GET /api/comparison?base=:base&compare=:compare` - Get historical data for comparison

## Deployment

This application is configured for deployment to Vercel with the following optimizations:

- Explicit Node.js version pinning (18.18.0+)
- Deterministic builds with `npm ci`
- Proper cache configuration
- Optimized build commands

## Customization

### Adding New Assets
1. Add new asset objects to the `assets_store` in `backend/main.py`
2. The frontend will automatically fetch and display new assets

### Styling
- Modify Tailwind configuration in `tailwind.config.js`
- Update color palette in `styles/globals.css`

### Extending Functionality
- Add new components in the `components/` directory
- Create new API endpoints in `backend/main.py`
- Extend TypeScript interfaces in `types/index.d.ts`

## Future Enhancements

- WebSocket integration for real-time updates
- User authentication and personalized watchlists
- Portfolio tracking with PnL calculations
- AI-powered insights and recommendations
- Export functionality for charts and data
- Advanced charting features (zoom, pan, annotations)

## License

This project is licensed under the MIT License.