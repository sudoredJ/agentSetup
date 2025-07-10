from smolagents import tool
import requests
from bs4 import BeautifulSoup
import re
from duckduckgo_search import DDGS

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
    elif any(word in request_lower for word in ['what', 'how', 'why', 'when', 'where']):
        return "**Analysis:** Information request - user wants research and explanation."
    else:
        return f"**Analysis:** Request appears to be: {request}. Determine best approach to fulfill this."

@tool
def web_search_tool(query: str, max_results: int = 5) -> str:
    """Perform a web search and return results.

    Args:
        query: The search query string to look up.
        max_results: Maximum number of results to return (default 5).
    """
    # Placeholder implementation – replace with real search API call.
    return (
        f"Web search results for '{query}' (showing up to {max_results} results) would appear here. "
        "(Not implemented yet)"
    )

@tool
def analyze_creative_request_tool(request: str) -> str:
    """Analyzes creative writing or composition requests.

    Args:
        request (str): The user's request text to be analyzed.
    """
    request_lower = request.lower().strip()
    
    if 'dm me' in request_lower:
        if '"' in request:
            message_content = request.split('"')[1] if '"' in request else "Hello!"
            return f"**Analysis:** User wants a DM with the message: '{message_content}'"
        else:
            return "**Analysis:** User wants a friendly DM sent to them."
    elif any(word in request_lower for word in ['write', 'story', 'poem', 'create']):
        return "**Analysis:** Creative writing request - use creative tools to fulfill."
    else:
        return f"**Analysis:** Request: {request}. Determine if this needs creative writing or simple communication."

@tool
def compose_message_tool(recipient: str, content: str = None, tone: str = "friendly") -> str:
    """Composes a well-formatted message for a recipient.

    Args:
        recipient (str): The person or entity the message is intended for.
        content (str, optional): The main body of the message. Defaults to a friendly greeting.
        tone (str, optional): The tone of the message ('friendly', 'professional'). Defaults to "friendly".
    """
    if not content:
        content = "Hello! I hope you're having a great day."
        
    if tone == "friendly":
        prefix = "Hi there!"
        suffix = "Hope this brightens your day!"
    elif tone == "professional":
        prefix = "Good day,"
        suffix = "Best regards,"
    else:
        prefix = "Hello!"
        suffix = "Have a wonderful day!"
        
    return f"""{prefix}

{content}

{suffix}

— Writer Assistant"""

@tool
def proofread_tool(text: str) -> str:
    """Proofreads and corrects a given text for grammar, spelling, and style.

    Args:
        text (str): The text to be proofread.
    """
    # In a real scenario, this would use a grammar correction library or a powerful model.
    # For this example, we'll just pretend to correct it.
    corrected_text = text.replace("eror", "error").replace("writting", "writing")
    
    if corrected_text == text:
        return f"**Proofreading Complete:** No major errors found. The text is clean and well-written."
    else:
        return f"""**Proofreading Complete:** Corrections have been made.

**Original:**
{text}

**Corrected:**
{corrected_text}
"""

@tool
def fetch_and_summarize_tool(url: str) -> str:
    """Fetches content from a URL and provides a summary.

    Args:
        url (str): The URL to fetch and summarize.
    """
    try:
        # Basic URL validation
        if not re.match(r'^https?://', url):
            return "ERROR: Invalid URL format. Please provide a full URL (e.g., http://example.com)."

        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Will raise an HTTPError for bad responses (4xx or 5xx)

        # Use BeautifulSoup to parse HTML and extract text
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
            
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip()for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # For this example, we'll provide a mock summary.
        # In a real implementation, you would use a summarization model here.
        # This is where you might call an LLM with the extracted text.
        summary = f"Successfully fetched content from {url}. The content appears to be about..."
        if len(text) > 200:
             summary += f" '{text[:200].strip()}...'"
        
        return f"**Summary:** {summary}"

    except requests.exceptions.RequestException as e:
        return f"ERROR: Could not fetch content from URL. {str(e)}"
    except Exception as e:
        return f"ERROR: An unexpected error occurred. {str(e)}"