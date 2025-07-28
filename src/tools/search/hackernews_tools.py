"""HackerNews API tools for fetching and filtering stories."""

import requests
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from smolagents import tool
import logging
import os

logger = logging.getLogger(__name__)

# HackerNews API base URL
HN_API_BASE = "https://hacker-news.firebaseio.com/v0"

# File to track last post time
LAST_POST_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'last_hn_post.json')

@tool
def get_top_hn_stories(limit: int = 30) -> str:
    """Fetch top stories from HackerNews.
    
    Args:
        limit: Maximum number of stories to return (default 30)
        
    Returns:
        Formatted list of top HackerNews stories
    """
    try:
        # Get top story IDs
        response = requests.get(f"{HN_API_BASE}/topstories.json", timeout=10)
        response.raise_for_status()
        story_ids = response.json()[:limit]
        
        stories = []
        for story_id in story_ids:
            try:
                # Get story details
                story_response = requests.get(f"{HN_API_BASE}/item/{story_id}.json", timeout=10)
                story_response.raise_for_status()
                story = story_response.json()
                
                if story and not story.get('deleted') and not story.get('dead'):
                    stories.append(story)
            except Exception as e:
                logger.error(f"Error fetching story {story_id}: {e}")
                continue
        
        # Format results
        formatted_stories = []
        for i, story in enumerate(stories, 1):
            story_info = []
            story_info.append(f"{i}. **{story.get('title', 'Untitled')}**")
            
            if story.get('url'):
                story_info.append(f"   URL: {story['url']}")
            else:
                story_info.append(f"   URL: https://news.ycombinator.com/item?id={story.get('id')}")
            
            story_info.append(f"   Score: {story.get('score', 0)} | Comments: {story.get('descendants', 0)}")
            story_info.append(f"   By: {story.get('by', 'unknown')} | Time: {datetime.fromtimestamp(story.get('time', 0)).strftime('%Y-%m-%d %H:%M')}")
            
            formatted_stories.append('\n'.join(story_info))
        
        return f"Top {len(formatted_stories)} HackerNews Stories:\n\n" + '\n\n'.join(formatted_stories)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching HN stories: {e}")
        return f"Error fetching HackerNews stories: {str(e)}"


@tool
def find_ai_law_stories(limit: int = 50) -> str:
    """Find HackerNews stories related to AI, law, and human-AI interaction.
    
    Args:
        limit: Number of top stories to search through (default 50)
        
    Returns:
        The most relevant story about AI/law/human-AI interaction
    """
    try:
        # Keywords to look for
        ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'gpt', 'llm', 
                       'neural', 'deep learning', 'chatbot', 'automation', 'algorithm']
        law_keywords = ['law', 'legal', 'regulation', 'policy', 'rights', 'ethics', 'privacy', 
                        'compliance', 'court', 'lawsuit', 'legislation', 'copyright', 'liability']
        human_keywords = ['human', 'society', 'social', 'people', 'interaction', 'collaboration',
                          'augment', 'assist', 'impact', 'future', 'workplace', 'job']
        
        # Get top stories
        response = requests.get(f"{HN_API_BASE}/topstories.json", timeout=10)
        response.raise_for_status()
        story_ids = response.json()[:limit]
        
        # Score each story based on relevance
        scored_stories = []
        
        for story_id in story_ids:
            try:
                story_response = requests.get(f"{HN_API_BASE}/item/{story_id}.json", timeout=10)
                story_response.raise_for_status()
                story = story_response.json()
                
                if not story or story.get('deleted') or story.get('dead'):
                    continue
                
                title = (story.get('title', '') + ' ' + story.get('text', '')).lower()
                
                # Calculate relevance score
                score = 0
                ai_score = sum(1 for keyword in ai_keywords if keyword in title)
                law_score = sum(1 for keyword in law_keywords if keyword in title)
                human_score = sum(1 for keyword in human_keywords if keyword in title)
                
                # Higher score for stories that combine topics
                if ai_score > 0:
                    score += ai_score * 2
                if law_score > 0:
                    score += law_score * 3  # Law + AI is particularly relevant
                if human_score > 0:
                    score += human_score * 2
                
                # Bonus for combining multiple themes
                themes_count = (1 if ai_score > 0 else 0) + (1 if law_score > 0 else 0) + (1 if human_score > 0 else 0)
                if themes_count >= 2:
                    score *= themes_count
                
                if score > 0:
                    scored_stories.append((score, story))
                    
            except Exception as e:
                logger.error(f"Error processing story {story_id}: {e}")
                continue
        
        # Sort by score and get the best one
        scored_stories.sort(key=lambda x: x[0], reverse=True)
        
        if not scored_stories:
            return "No AI/law/human-AI stories found in current top stories."
        
        # Return the most relevant story
        _, best_story = scored_stories[0]
        
        story_info = []
        story_info.append(f"**Most Relevant AI/Law/Human-AI Story:**\n")
        story_info.append(f"**{best_story.get('title', 'Untitled')}**")
        
        if best_story.get('url'):
            story_info.append(f"URL: {best_story['url']}")
        else:
            story_info.append(f"URL: https://news.ycombinator.com/item?id={best_story.get('id')}")
        
        story_info.append(f"Score: {best_story.get('score', 0)} | Comments: {best_story.get('descendants', 0)}")
        story_info.append(f"By: {best_story.get('by', 'unknown')} | Time: {datetime.fromtimestamp(best_story.get('time', 0)).strftime('%Y-%m-%d %H:%M')}")
        
        if best_story.get('text'):
            story_info.append(f"\nText: {best_story['text'][:200]}...")
        
        # Add relevance explanation
        story_info.append(f"\n*Relevance: Found {len(scored_stories)} related stories. This one scored highest.*")
        
        return '\n'.join(story_info)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error finding AI/law stories: {e}")
        return f"Error finding AI/law stories: {str(e)}"


@tool
def check_hn_post_schedule() -> str:
    """Check if it's time to post a HackerNews story (24h since last post).
    
    Returns:
        Information about whether it's time to post and when the last post was made
    """
    try:
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(LAST_POST_FILE), exist_ok=True)
        
        # Check if tracking file exists
        if os.path.exists(LAST_POST_FILE):
            with open(LAST_POST_FILE, 'r') as f:
                data = json.load(f)
                last_post_time = datetime.fromisoformat(data.get('last_post_time'))
                
            time_since_last = datetime.now() - last_post_time
            hours_since = time_since_last.total_seconds() / 3600
            
            if hours_since >= 24:
                return f"It's been {hours_since:.1f} hours since the last post. Time to post a new story!"
            else:
                hours_until = 24 - hours_since
                return f"Last post was {hours_since:.1f} hours ago. Wait {hours_until:.1f} more hours before posting."
        else:
            # First time - should post
            return "No previous post recorded. Time to make the first post!"
            
    except Exception as e:
        logger.error(f"Error checking post schedule: {e}")
        return "Unable to check post schedule. Assuming it's time to post."


@tool
def record_hn_post() -> str:
    """Record that a HackerNews story was posted (updates the timestamp).
    
    Returns:
        Confirmation message
    """
    try:
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(LAST_POST_FILE), exist_ok=True)
        
        # Record the current time
        data = {
            'last_post_time': datetime.now().isoformat(),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(LAST_POST_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        return f"Post recorded at {data['timestamp']}. Next post due in 24 hours."
        
    except Exception as e:
        logger.error(f"Error recording post: {e}")
        return f"Error recording post: {str(e)}"