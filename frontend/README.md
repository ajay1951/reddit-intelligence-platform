# Reddit Intelligence Platform - Frontend Interface

This is the user interface for the **AI-Powered Market Intelligence Platform**. It is built as a Single Page Application (SPA) providing a sleek, modern dashboard to interact with the backend data pipelines and AI agents.

## 🚀 Key Features

- **Deep Research Terminal:** A specialized interface that connects to the backend AI agent swarm via Server-Sent Events (SSE). It streams the "chain of thought" from multiple AI agents live to the screen, providing real-time research synthesis.
- **Analytics Dashboard:** Visualizes massive amounts of unstructured Reddit data (sentiment trends, hiring statistics, and top skills) using interactive charts.
- **System Administration:** A control panel to dispatch background Celery tasks (batch scraping) to the backend ETL pipeline.

## 🛠️ Tools & Technologies

This frontend is engineered for extreme performance and developer experience using modern web standards:

- **Core Framework:** [React 19](https://react.dev/) powered by [Vite](https://vitejs.dev/) for instant HMR (Hot Module Replacement) and optimized production builds.
- **Routing:** [React Router v7](https://reactrouter.com/) for seamless, client-side navigation between the Dashboard, Admin, and Research pages.
- **Styling:** Custom Vanilla CSS utilizing CSS variables to enforce a strictly typed design system. Features advanced visual elements like **Glassmorphism**, deep dark mode aesthetics, and fluid micro-animations.
- **Data Visualization:** [Recharts](https://recharts.org/) for rendering responsive, customizable charts (Bar, Line, Pie) for sentiment and salary analytics.
- **Iconography:** [Lucide React](https://lucide.dev/) for clean, consistent, and lightweight SVG icons.
- **HTTP Client:** [Axios](https://axios-http.com/) for structured REST API communication with the FastAPI backend.

## 📂 Project Structure

```text
src/
├── assets/         # Static images and icons
├── components/     # Reusable UI components (Cards, Buttons, Charts, Layouts)
├── pages/          # Full-page route views (Dashboard, Admin, DeepResearch)
├── App.jsx         # Root component and Router configuration
├── main.jsx        # React DOM entry point
└── index.css       # Global design system variables and utility classes
```

## ⚙️ Development Setup

To run the frontend locally, ensure you have **Node.js (v18+)** installed.

1. **Install Dependencies:**
   ```bash
   npm install
   ```

2. **Start the Development Server:**
   ```bash
   npm run dev
   ```
   *The application will be available at `http://localhost:5173`. Ensure your FastAPI backend is running on port 8000 for full functionality.*

## 🏗️ Building for Production

To create an optimized production bundle:

```bash
npm run build
```

This will output the minified static files into the `dist/` directory, which can be served by Nginx, Vercel, Netlify, or any static file host.
