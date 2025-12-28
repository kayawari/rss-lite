import os
from typing import Optional, List
from fastapi import FastAPI, Request, Form, Response, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions # Required for passing tokens
from dotenv import load_dotenv
from pydantic import BaseModel

# Import the logic for parsing feeds
from app.feed_utils import parse_and_save_feed

load_dotenv()

app = FastAPI(title="Folo-Lite Phase 3")

# Supabase Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY or not SUPABASE_SECRET_KEY:
    raise ValueError("Missing environment variables")

# Global client (Used only for generic/anon operations)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

# Templates Setup
templates = Jinja2Templates(directory="../frontend/app/templates")

# --- Dependencies ---

async def get_user_supabase(request: Request) -> Client:
    """
    Creates a Supabase client acting AS THE LOGGED-IN USER.
    This passes the 'sb-access-token' to Supabase so RLS policies work.
    """
    token = request.cookies.get("sb-access-token")
    if not token:
        # If no token, we can't act as the user.
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # We initialize a new client for this specific request using the user's token
    client = create_client(
        SUPABASE_URL, 
        SUPABASE_SECRET_KEY, 
    )
    return client

async def get_current_user(request: Request):
    """
    Helper to get the user object for templates.
    """
    token = request.cookies.get("sb-access-token")
    if not token:
        return None
    try:
        # We can use the global client to verify the token
        user_response = supabase.auth.get_user(token)
        return user_response.user
    except Exception:
        return None

async def require_user(user = Depends(get_current_user)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT, 
            detail="Not authenticated",
            headers={"Location": "/login"}
        )
    return user

# --- Auth Routes ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "supabase_url": SUPABASE_URL, 
        "supabase_publishable_key": SUPABASE_PUBLISHABLE_KEY # NOTE: !!!!!!!not use service key!!!!!!!!!
    })

@app.post("/auth/session")
async def set_session(request: Request, response: Response):
    try:
        body = await request.json()
        access_token = body.get("access_token")
        if not access_token:
            return JSONResponse({"error": "No token provided"}, status_code=400)

        response = JSONResponse({"status": "success"})
        response.set_cookie(
            key="sb-access-token", 
            value=access_token, 
            httponly=True, 
            max_age=60 * 60 * 24 * 7, 
            samesite="lax",
            secure=False 
        )
        return response
    except Exception as e:
         return JSONResponse({"error": str(e)}, status_code=400)

@app.post("/auth/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("sb-access-token")
    return response

# --- Application Routes ---

@app.get("/", response_class=HTMLResponse)
async def read_root(
    request: Request, 
    feed_id: Optional[str] = Query(None),
):
    """
    The main Dashboard.
    """
    try:
        # Use the User-Scoped Client
        user_client = await get_user_supabase(request)
        user = user_client.auth.get_user(request.cookies.get("sb-access-token")).user
    except HTTPException:
        return RedirectResponse(url="/login", status_code=307)

    # 1. Get User's Subscriptions using user_client
    subs_res = user_client.table("subscriptions")\
        .select("feed_id, feeds(id, title, url)")\
        .eq("user_id", user.id)\
        .execute()
    
    subscribed_feeds = []
    user_feed_ids = []
    
    if subs_res.data:
        for item in subs_res.data:
            if item.get('feeds'):
                subscribed_feeds.append(item['feeds'])
                user_feed_ids.append(item['feed_id'])

    # 2. Determine which feeds to fetch articles from
    target_feed_ids = [feed_id] if feed_id else user_feed_ids

    # 3. Get Articles
    articles = []
    if target_feed_ids:
        # Query using user_client to ensure RLS compliance
        query = user_client.table("articles")\
            .select("*, feeds(title)")\
            .in_("feed_id", target_feed_ids)\
            .order("published_at", desc=True)\
            .limit(100)
        
        articles_res = query.execute()
        raw_articles = articles_res.data

        # 4. Get Read Status for these articles
        article_ids = [a['id'] for a in raw_articles]
        
        read_states = []
        if article_ids:
            read_res = user_client.table("user_article_states")\
                .select("article_id, is_read, is_saved")\
                .eq("user_id", user.id)\
                .in_("article_id", article_ids)\
                .execute()
            read_states = read_res.data

        state_map = {r['article_id']: r for r in read_states}

        for art in raw_articles:
            state = state_map.get(art['id'], {})
            art['is_read'] = state.get('is_read', False)
            art['is_saved'] = state.get('is_saved', False)
        
        articles = raw_articles

    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "articles": articles, 
            "user": user,
            "feeds": subscribed_feeds,
            "current_feed_id": feed_id 
        }
    )

@app.post("/feeds", response_class=HTMLResponse)
async def add_feed(
    request: Request, 
    url: str = Form(...)
):
    try:
        # 1. Get the Client acting as the User
        user_client = await get_user_supabase(request)
        
        # DEBUG: Verify we are actually logged in
        token = request.cookies.get("sb-access-token")
        user = user_client.auth.get_user(token).user

        # 2. Parse & Save using the USER client
        feed_id = await parse_and_save_feed(user_client, url)
        
        # 3. Subscribe
        user_client.table("subscriptions").upsert({
            "user_id": user.id,
            "feed_id": feed_id
        }).execute()
        
        headers = {"HX-Refresh": "true"}
        return HTMLResponse("Feed added", headers=headers)
        
    except HTTPException:
        return HTMLResponse("Please login again", status_code=401)
    except Exception as e:
        print(f"Error adding feed: {e}")
        return HTMLResponse(
            f"<div class='pico-background-red-200' style='padding:10px;'>Error: {str(e)}</div>", 
            status_code=200 
        )

@app.post("/articles/{article_id}/read", response_class=Response)
async def mark_article_read(
    article_id: str, 
    request: Request
):
    try:
        user_client = await get_user_supabase(request)
        token = request.cookies.get("sb-access-token")
        user = user_client.auth.get_user(token).user
        
        payload = {
            "user_id": user.id,
            "article_id": article_id,
            "is_read": True,
            "updated_at": "now()"
        }
        user_client.table("user_article_states").upsert(payload).execute()
        return Response(status_code=204)
    except Exception as e:
        print(f"Error marking read: {e}")
        return Response(status_code=500)
