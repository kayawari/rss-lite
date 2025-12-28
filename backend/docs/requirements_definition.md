Requirements Definition: Minimalist RSS Reader (Project "Folo-Lite")

1. Project Overview

Goal: Build a clean, distraction-free web-based RSS reader.
Core Philosophy: "Content First." The UI should get out of the way. Speed and simplicity (via htmx) take precedence over complex animations or heavy client-side state.
Reference: Inspired by Folo (clean layout, read-later focus), but stripping away the complex AI/LLM features for the initial MVP.
Future Roadmap: While focusing on the web app now, we are considering adding a mobile app in the future, likely built with Flutter.

2. Technical Stack Constraints

Component

Technology

Reasoning / Specifics

Language

Python 3.14

Latest stable release.

Package Manager

uv

Used for fast, reliable dependency management and virtual environments.

Backend Framework

FastAPI

Selected for native async support (critical for fetching feeds) and strict Pydantic typing.

Frontend

htmx + Jinja2

Server-Side Rendering (SSR) with htmx handling dynamic interactions (add feed, mark read, filter) without a JS build step.

Database

Supabase (PostgreSQL)

Managed DB + Auth. Uses a Hybrid Security Model: User context for subscriptions, Admin context for data ingestion.

Styling

Pico.css

Minimalist class-less CSS framework for instant mobile responsiveness.

3. Functional Requirements (MVP)

3.1 Authentication (User Management) ✅ Completed

Sign Up / Login: Handled via Supabase Auth (Google OAuth).

Session Management: Secure HttpOnly cookies set by the FastAPI backend after OAuth callback.

3.2 Feed Management ✅ Completed

Add Feed: User pastes a URL; the system parses it server-side.

Architecture Note: This action uses the Service Role Key to bypass RLS for the shared feeds table, then uses the User Key to create the private subscription.

List Feeds: Sidebar navigation showing subscribed feeds.

Filter: Ability to filter the timeline by clicking a specific feed.

3.3 Reading Experience ✅ Completed

Timeline View: Unified stream of articles, sorted by date (newest first).

Article Preview: Clicking "Show Preview" expands the content inline without leaving the page (HTMX).

Original Link: Clicking the title opens the original URL in a new tab.

3.4 Interaction & State ✅ Completed

Read Status: * Articles are marked as "read" in the database when clicked or previewed.

UI immediately dims read articles to 60% opacity.

Mark All Read: (Planned for next iteration).

4. Non-Functional Requirements

4.1 Performance

HTMX Interactions: Navigation uses hx-boost or hx-target to prevent full page reloads.

Async Fetching: The backend uses Python's asyncio to fetch external RSS feeds without blocking the API.

4.2 Security & Permissions

Row Level Security (RLS): Enabled on all tables.

feeds / articles: Publicly readable by authenticated users, writable only by Admin (Backend).

subscriptions / user_article_states: Strictly scoped to auth.uid() = user_id.

Secrets Management: Service Role Key is strictly confined to the backend environment (.env), never exposed to the client.

5. Data Model (Implemented Schema)

1. profiles * Syncs with auth.users via database trigger.

2. feeds (Master Data)

Stores unique feed URLs and metadata.

url is unique to prevent duplication across users.

3. subscriptions (Junction Table)

Links user_id <-> feed_id.

Enables the Many-to-Many relationship (User A and User B can both follow Feed X without duplicating Feed X).

4. articles (Content)

Stores individual feed items.

unique(feed_id, external_id) constraint prevents duplicate articles.

5. user_article_states (User Data)

Tracks is_read and is_saved per user/article pair.

6. Implementation Phases

Phase 1: The Walking Skeleton ✅

[x] Setup Python/FastAPI/Supabase.

[x] Script to ingest public feeds.

[x] Render list via Jinja2.

Phase 2: The User Loop ✅

[x] Implement Google OAuth.

[x] Create subscriptions logic.

[x] "Add Feed" form with backend parsing.

Phase 3: The Polish ✅

[x] Sidebar navigation.

[x] Read/Unread state tracking.

[x] Fix RLS permissions using Hybrid Service Key approach.

Phase 4: Future / Maintenance 🚧

[ ] Background Worker (Cron) to auto-update feeds every hour.

[ ] "Saved for Later" view.

[ ] Mobile App (Flutter).
