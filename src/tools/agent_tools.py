"""Generic agent-side tools
~~~~~~~~~~~~~~~~~~~~~~~~~~
These are domain-agnostic helper functions exposed as `@tool`s so that agents
can analyse requests, compose messages, fetch URLs, etc.

Provided tools:
• analyse_request_tool           – classify user intent (research context)
• compose_message_tool           – compose a formatted message
• proofread_tool                 – simple spelling/grammar fixer
• web_search_tool                – BeautifulSoup-based web search
• fetch_and_summarize_tool       – fetch webpage + summary
• deep_research_tool             – comprehensive research using multiple sources

All functions follow the smolagents docstring format (brief summary + Args).
"""
from smolagents import tool
import requests
from bs4 import BeautifulSoup
import re
import time
import logging

logger = logging.getLogger(__name__)

# Import the BeautifulSoup search system
from .beautiful_search import beautiful_search

@tool
def analyze_request_tool(request: str) -> str:
    """Analyzes what the user is really asking for in a research context.

    Args:
        request (str): The user's request text to be analyzed.
    """
    request_lower = request.lower().strip()
    
    if request_lower in ['hi', 'hello', 'hey']:
        return "**Analysis:** Simple greeting - respond warmly and offer assistance."
    elif 'dm me' in request_lower:
        return "**Analysis:** User wants a direct message sent to them. Extract any specific message content or send a friendly greeting."
    elif any(word in request_lower for word in ['write', 'story', 'poem', 'create', 'compose', 'draft']):
        return "**Analysis:** Creative writing request - use creative tools to fulfill."
    elif any(word in request_lower for word in ['what', 'how', 'why', 'when', 'where']):
        return "**Analysis:** Information request - user wants research and explanation."
    else:
        return f"**Analysis:** Request appears to be: {request}. Determine best approach to fulfill this."

@tool
def web_search_tool(query: str, max_results: int = 5) -> str:
    """Perform a web search using BeautifulSoup scraping.

    Args:
        query: The search query string to look up.
        max_results: Maximum number of results to return (default 5).
    """
    try:
        logger.info(f"Starting BeautifulSoup web search for query: '{query}'")
        
        # Use the BeautifulSoup search system with multiple engines
        results = beautiful_search.search_with_fallbacks(query, max_results)
        
        if not results:
            return f"ERROR: No search results found for '{query}'. All search engines failed."
        
        # Format results nicely
        formatted_results = [f"**Web Search Results for '{query}':**\n"]
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            url = result.get('url', '')
            snippet = result.get('body', 'No description')
            source = result.get('source', 'Unknown')
            
            formatted_results.append(f"{i}. **{title}** (via {source})")
            formatted_results.append(f"   URL: {url}")
            formatted_results.append(f"   {snippet}\n")
        
        logger.info(f"BeautifulSoup web search completed successfully, found {len(results)} results")
        return "\n".join(formatted_results)
        
    except ImportError:
        return "ERROR: Required packages not installed. Run: pip install requests beautifulsoup4"
    except Exception as e:
        logger.error(f"BeautifulSoup web search failed: {e}")
        return f"ERROR: Search failed - {str(e)}"

@tool
def compose_message_tool(recipient: str, content: str = None, tone: str = "friendly") -> str:
    """Composes a well-formatted message for a recipient.

    Args:
        recipient: The name or identifier of the message recipient.
        content: The main content of the message (optional).
        tone: The tone of the message - friendly, formal, casual, etc. (default friendly).
    """
    if not content:
        content = f"Hello {recipient}! I hope you're having a great day."
    
    tone_prefixes = {
        "friendly": "👋",
        "formal": "Dear",
        "casual": "Hey",
        "professional": "Hello"
    }
    
    prefix = tone_prefixes.get(tone.lower(), "👋")
    
    if tone.lower() == "formal":
        message = f"{prefix} {recipient},\n\n{content}\n\nBest regards,\nAssistant"
    else:
        message = f"{prefix} {recipient}!\n\n{content}\n\n— Assistant"
    
    return message

@tool
def proofread_tool(text: str) -> str:
    """Simple proofreading tool that fixes common spelling and grammar issues.

    Args:
        text: The text to proofread and correct.
    """
    # Simple corrections - in a real implementation, you might use a proper grammar checker
    corrections = {
        "teh": "the",
        "recieve": "receive",
        "seperate": "separate",
        "definately": "definitely",
        "occured": "occurred",
        "begining": "beginning",
        "beleive": "believe",
        "neccessary": "necessary",
        "priviledge": "privilege",
        "accomodate": "accommodate"
    }
    
    corrected_text = text
    for wrong, right in corrections.items():
        corrected_text = re.sub(r'\b' + wrong + r'\b', right, corrected_text, flags=re.IGNORECASE)
    
    return corrected_text

@tool
def deep_research_tool(topic: str, num_searches: int = 3) -> str:
    """Perform deep research on a topic using BeautifulSoup scraping.
    
    Args:
        topic: The main research topic
        num_searches: Number of different search angles to explore (default 3)
    """
    try:
        logger.info(f"Starting BeautifulSoup deep research on topic: '{topic}'")
        
        # Generate different search angles
        search_angles = [
            topic,  # Direct search
            f"what is {topic} explained",  # Explanatory
            f"{topic} recent developments 2024 2025",  # Recent info
        ]
        
        if num_searches > 3:
            search_angles.extend([
                f"{topic} best practices",
                f"{topic} common problems",
                f"{topic} future trends"
            ])
        
        all_results = []
        seen_urls = set()
        successful_searches = 0
        
        # Research each angle
        for i, query in enumerate(search_angles[:num_searches], 1):
            try:
                logger.info(f"Researching angle {i}/{num_searches}: '{query}'")
                
                # Use BeautifulSoup search with fallbacks
                results = beautiful_search.search_with_fallbacks(query, 3)
                successful_searches += 1
                
                for result in results:
                    url = result.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            'query': query,
                            'title': result.get('title', 'No title'),
                            'url': url,
                            'snippet': result.get('body', 'No description'),
                            'source': result.get('source', 'Unknown')
                        })
                
                logger.info(f"Angle '{query}' returned {len(results)} results")
                
                # Add delay between searches
                if i < num_searches:
                    time.sleep(3)
                    
            except Exception as e:
                logger.error(f"Error researching angle '{query}': {e}")
                continue
        
        if not all_results:
            return f"ERROR: No research results found for topic: '{topic}' after {successful_searches} search attempts."
        
        # Compile research report
        report = [f"**Deep Research Report: {topic}**\n"]
        report.append(f"*Successfully researched {successful_searches}/{num_searches} angles, found {len(all_results)} unique sources*\n")
        
        # Group by search query
        for query in search_angles[:num_searches]:
            query_results = [r for r in all_results if r['query'] == query]
            if query_results:
                report.append(f"\n**Research: '{query}'**")
                for r in query_results:
                    report.append(f"• {r['title']} (via {r['source']})")
                    report.append(f"  {r['snippet'][:150]}...")
                    report.append(f"  Source: {r['url']}")
        
        # Add summary section
        report.append("\n**Key Sources:**")
        for i, result in enumerate(all_results[:5], 1):
            report.append(f"{i}. {result['url']} (via {result['source']})")
        
        # Add source diversity info
        sources = set(r['source'] for r in all_results)
        report.append(f"\n*Research used {len(sources)} different search engines: {', '.join(sources)}*")
        
        return "\n".join(report)
        
    except ImportError:
        return "ERROR: Required packages not installed. Run: pip install requests beautifulsoup4"
    except Exception as e:
        logger.error(f"Deep research failed: {e}")
        return f"ERROR: Deep research failed - {str(e)}"

@tool
def fetch_and_summarize_tool(url: str) -> str:
    """Fetches content from a URL and provides a summary using BeautifulSoup.

    Args:
        url (str): The URL to fetch and summarize.
    """
    try:
        logger.info(f"Fetching and summarizing URL: {url}")
        
        # Use the BeautifulSoup scraping system
        result = beautiful_search.scrape_webpage(url)
        
        if not result.get('success', False):
            return f"ERROR: Failed to scrape {url} - {result.get('error', 'Unknown error')}"
        
        title = result.get('title', 'No title')
        summary = result.get('summary', 'No content available')
        word_count = result.get('word_count', 0)
        
        return f"**Content Summary from {url}:**\n\n**Title:** {title}\n\n{summary}\n\n*Full content: {word_count} words*"
        
    except Exception as e:
        logger.error(f"Failed to fetch and summarize {url}: {e}")
        return f"ERROR: Failed to process content - {str(e)}"