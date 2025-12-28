import feedparser
from datetime import datetime
from supabase import Client

async def parse_and_save_feed(supabase: Client, feed_url: str):
    """
    Parses a feed URL, saves the feed info and its articles to Supabase.
    Returns the feed_id.
    """
    # 1. Parse
    feed_data = feedparser.parse(feed_url)
    
    if feed_data.bozo and not feed_data.entries:
        # If it's malformed and has no entries, fail.
        # (Sometimes bozo is true for minor encoding errors, so we check entries too)
        raise ValueError(f"Could not parse feed: {feed_data.bozo_exception}")

    # 2. Insert/Get Feed
    # We use upsert to ensure we get the ID if it already exists
    feed_payload = {
        "url": feed_url,
        "title": feed_data.feed.get("title", feed_url),
        "site_link": feed_data.feed.get("link", ""),
        "last_fetched_at": datetime.now().isoformat()
    }

    res = supabase.table("feeds").upsert(feed_payload, on_conflict="url").execute()
    # Supabase returns a list of inserted rows
    if not res.data:
        # Should not happen with upsert, but safety check
        raise ValueError("Failed to save feed to database")
        
    feed_id = res.data[0]['id']

    # 3. Process Articles
    articles_to_insert = []
    for entry in feed_data.entries:
        external_id = entry.get("id", entry.get("link"))
        published_at = datetime.now().isoformat()
        
        if hasattr(entry, "published_parsed") and entry.published_parsed:
             published_at = datetime(*entry.published_parsed[:6]).isoformat()

        article = {
            "feed_id": feed_id,
            "external_id": external_id,
            "title": entry.get("title", "No Title"),
            "content": entry.get("summary", "") or entry.get("description", ""),
            "url": entry.get("link", ""),
            "published_at": published_at
        }
        articles_to_insert.append(article)

    # 4. Batch Insert (Ignore duplicates)
    if articles_to_insert:
        supabase.table("articles").upsert(
            articles_to_insert, 
            on_conflict="feed_id,external_id", 
            ignore_duplicates=True
        ).execute()


    return feed_id
