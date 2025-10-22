# AI Development Rules & Guidelines

## Tech Stack Overview

• **Backend**: Encore.dev framework with TypeScript for API services and cron jobs
• **Frontend**: React 18+ with TypeScript, Vite build system, and Tailwind CSS for styling
• **Database**: PostgreSQL via Encore's SQLDatabase with automatic migrations
• **UI Components**: shadcn/ui component library with Radix UI primitives
• **API Communication**: Generated Encore TypeScript client for type-safe backend calls
• **State Management**: React built-in state management (useState, useEffect) with component-level state
• **Styling**: Tailwind CSS with custom configuration and dark mode support
• **Data Visualization**: Recharts or similar lightweight charting library (to be implemented)
• **Authentication**: Encore's built-in auth system (to be implemented)
• **Deployment**: Encore Cloud Platform with automatic CI/CD

## Library Usage Rules

### UI & Styling
• **Primary UI Library**: Use shadcn/ui components exclusively for all UI elements
• **Styling**: Use Tailwind CSS classes only, no inline styles or CSS-in-JS
• **Icons**: Use lucide-react icons for all iconography needs
• **Charts**: Use recharts library for data visualization (when implemented)
• **Animations**: Use tailwindcss-animate for simple animations and transitions

### State Management
• **Local State**: Use React's built-in useState and useReducer hooks
• **Global State**: Use React Context API for simple global state needs
• **Form State**: Use React Hook Form for complex form handling
• **Data Fetching**: Use Encore's generated client for all API calls

### Data Handling
• **API Client**: Use the generated Encore TypeScript client for all backend communication
• **Data Validation**: Use Zod for client-side data validation when needed
• **Date Handling**: Use native Date objects or date-fns for date manipulation
• **Caching**: Use React Query (TanStack Query) for server state caching (when implemented)

### Development Practices
• **Component Structure**: Create one file per component in the appropriate directory
• **Type Safety**: Use TypeScript for all code with strict typing
• **Error Handling**: Implement proper error boundaries and user feedback
• **Responsive Design**: All components must be mobile-responsive using Tailwind's responsive utilities
• **Accessibility**: Follow WCAG guidelines and use semantic HTML with proper ARIA attributes

### Prohibited Libraries
• Do not use Redux or other external state management libraries
• Do not use Bootstrap, Material-UI, or other competing component libraries
• Do not use jQuery or other legacy JavaScript libraries
• Do not use CSS preprocessors (Sass, Less) - use Tailwind exclusively
• Do not use classnames or clsx alternatives - use clsx as provided
• Do not use moment.js - use native Date or date-fns instead