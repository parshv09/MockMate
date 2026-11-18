# MockMate Frontend (React + Vite + JavaScript)

React + JSX frontend for **MockMate**, built with the **Calm Broadcast Studio** design system (`design-system/mockmate/MASTER.md`) and connected to the Django REST Framework `/api/v1/` backend.

## Technology Stack

- **Framework:** React 18 (JavaScript + `.jsx` components)
- **Bundler:** Vite 6 (`vite.config.js`)
- **Routing:** React Router v6 (`react-router-dom`)
- **Styling:** Tailwind CSS v3 + CSS Custom Properties (`src/styles/tokens.css`, `src/styles/index.css`)
- **Typography:** Plus Jakarta Sans (UI/Headings) + JetBrains Mono (`tabular-nums` timers & telemetry)
- **HTTP Client:** Axios (`src/api/client.js`)

## Setup & Development Commands

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Create a local environment file from the example:
   ```bash
   cp .env.example .env
   ```

3. Install dependencies:
   ```bash
   npm install
   ```

4. Start the Vite development server (runs on `http://localhost:5173`):
   ```bash
   npm run dev
   ```

5. Build for production:
   ```bash
   npm run build
   ```

6. Preview production build locally:
   ```bash
   npm run preview
   ```

## Application Routes

| Route | Component | Mode | Purpose |
| :--- | :--- | :--- | :--- |
| `/` | `LandingPage.jsx` | Daylight Brief | Product overview & entry point |
| `/login` | `LoginPage.jsx` | Daylight Brief | Candidate sign-in |
| `/register` | `RegisterPage.jsx` | Daylight Brief | Candidate registration |
| `/dashboard` | `DashboardPage.jsx` | Daylight Brief | Studio overview, metrics & recent sessions |
| `/resumes` | `ResumesPage.jsx` | Daylight Brief | Resume vault & RAG indexing status |
| `/sessions/new` | `SessionSetupPage.jsx` | Daylight Brief | Configure Standard or Resume + JD interview |
| `/sessions/:id/interview` | `InterviewWorkspacePage.jsx` | Focus Booth | Live question prompt, audio/text answer & webcam rail |
| `/sessions/:id/summary` | `SessionSummaryPage.jsx` | Daylight Brief | Post-interview score breakdown, study key & PDF report |

