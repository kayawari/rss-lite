# development tasks
- [ ] logout and refresh token flow

- [ ] Deployment setting
Since you are using uv and standard Python, this is ready to deploy to Render, Railway, or Fly.io (all of which support Python + persistent usage).

- [ ] Backgroud worker
Right now, feeds only update when you add them. You might want to run your ingest_feed.py logic on a schedule (cron job) to fetch updates for all feeds every hour.

- [ ] mobile app
As per your constraints, your Supabase database is now ready for a Flutter app. The Flutter app can connect directly to the same Supabase URL, log in with the same Google account, and read the same subscriptions table.

- [ ] create gemini cli environment

- [ ] add test code
