"""ArXiv tools for searching and retrieving academic papers.

This module provides tools for interacting with arXiv.org through their HTTP API.
"""

import os
import re
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List
from smolagents import tool

# Download path for PDFs
DOWNLOAD_PATH = os.path.join(os.path.expanduser('~'), 'Downloads', 'arxiv_papers')
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# arXiv API base URL
ARXIV_API_BASE = "http://export.arxiv.org/api/query"

def clean_text(text: str) -> str:
    """Clean text for use in search queries."""
    # Remove escape sequences and quotes
    text = re.sub(r'\\[ntr]', ' ', text)
    text = text.replace(':', ' ')
    text = re.sub(r'[\'"]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_arxiv_entry(entry: ET.Element) -> Dict[str, str]:
    """Parse a single arXiv entry from the Atom feed."""
    ns = {'atom': 'http://www.w3.org/2005/Atom',
          'arxiv': 'http://arxiv.org/schemas/atom'}
    
    # Extract basic info
    title = entry.find('atom:title', ns).text.strip()
    summary = entry.find('atom:summary', ns).text.strip()
    published = entry.find('atom:published', ns).text
    updated = entry.find('atom:updated', ns).text
    
    # Extract ID and convert to arXiv ID
    id_text = entry.find('atom:id', ns).text
    arxiv_id = id_text.split('/abs/')[-1]
    
    # Extract authors
    authors = []
    for author in entry.findall('atom:author', ns):
        name = author.find('atom:name', ns)
        if name is not None:
            authors.append(name.text)
    
    # Extract PDF link
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    
    return {
        'title': title,
        'arxiv_id': arxiv_id,
        'authors': authors,
        'summary': summary,
        'published': published,
        'updated': updated,
        'pdf_url': pdf_url,
        'abs_url': f"https://arxiv.org/abs/{arxiv_id}"
    }

def search_arxiv_api(search_query: str, start: int = 0, max_results: int = 10) -> List[Dict[str, str]]:
    """Search arXiv using their API."""
    params = {
        'search_query': search_query,
        'start': start,
        'max_results': max_results
    }
    
    url = ARXIV_API_BASE + '?' + urllib.parse.urlencode(params)
    
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read().decode('utf-8')
        
        # Parse XML
        root = ET.fromstring(data)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        results = []
        for entry in root.findall('atom:entry', ns):
            results.append(parse_arxiv_entry(entry))
        
        return results
    except Exception as e:
        raise Exception(f"Failed to search arXiv: {str(e)}")

@tool
def search_arxiv_papers(
    query: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    abstract: Optional[str] = None,
    start: int = 0
) -> str:
    """Search for papers on arXiv.org based on various criteria.
    
    Args:
        query: General keyword search across all fields
        title: Search within paper titles
        author: Search by author name(s)
        abstract: Search within abstracts
        start: Starting index for pagination (default: 0)
    
    Returns:
        Formatted string with search results
    
    Example:
        search_arxiv_papers(author="Yann LeCun", title="convolutional")
    """
    # Build search query
    search_parts = []
    
    if query:
        # Special handling for Harvard Berkman Klein Center queries
        if 'harvard berkman klein center' in query.lower():
            # Use multiple targeted searches for better results
            search_parts.extend([
                'all:"Harvard Berkman Klein Center"',
                'all:"Berkman Klein Center"',
            ])
        else:
            search_parts.append(f'all:{clean_text(query)}')
    if title:
        search_parts.append(f'ti:{clean_text(title)}')
    if author:
        search_parts.append(f'au:{clean_text(author)}')
    if abstract:
        search_parts.append(f'abs:{clean_text(abstract)}')
    
    if not search_parts:
        return "Please provide at least one search parameter (query, title, author, or abstract)"
    
    # For Harvard Berkman queries, use OR instead of AND to get more results
    if 'harvard berkman klein center' in str(query).lower():
        search_query = ' OR '.join(search_parts)
    else:
        search_query = ' AND '.join(search_parts)
    
    try:
        results = search_arxiv_api(search_query, start=start, max_results=10)
        
        if not results:
            return "No papers found matching your search criteria."
        
        # Add summary at the top
        formatted = f"**Summary:** Found {len(results)} papers"
        if query:
            formatted += f" matching '{query}'"
        if title:
            formatted += f" with title containing '{title}'"
        if author:
            formatted += f" by {author}"
        if abstract:
            formatted += f" with abstract containing '{abstract}'"
        formatted += "\n\n"
        
        formatted += f"Found {len(results)} papers:\n\n"
        for i, paper in enumerate(results, 1):
            formatted += f"{i}. {paper['title']}\n"
            formatted += f"   arXiv ID: {paper['arxiv_id']}\n"
            formatted += f"   Authors: {', '.join(paper['authors'][:3])}"
            if len(paper['authors']) > 3:
                formatted += f" and {len(paper['authors']) - 3} others"
            formatted += f"\n   Published: {paper['published'][:10]}\n\n"
        
        return formatted
    except Exception as e:
        return f"Error searching arXiv: {str(e)}"

@tool
def get_arxiv_details(title: str) -> str:
    """Get detailed information about a specific paper from arXiv.
    
    Args:
        title: The title of the paper to retrieve details for
    
    Returns:
        Formatted string with paper details
    
    Example:
        get_arxiv_details("Attention is All You Need")
    """
    try:
        # Search for the paper by title
        search_query = f'ti:{clean_text(title)}'
        results = search_arxiv_api(search_query, max_results=1)
        
        if not results:
            return f"No paper found with title: {title}"
        
        paper = results[0]
        
        formatted = "Paper Details:\n\n"
        formatted += f"Title: {paper['title']}\n"
        formatted += f"arXiv ID: {paper['arxiv_id']}\n"
        formatted += f"Authors: {', '.join(paper['authors'])}\n"
        formatted += f"Published: {paper['published'][:10]}\n"
        formatted += f"Updated: {paper['updated'][:10]}\n"
        formatted += f"PDF URL: {paper['pdf_url']}\n"
        formatted += f"Abstract URL: {paper['abs_url']}\n\n"
        formatted += f"Abstract:\n{paper['summary'][:500]}..."
        if len(paper['summary']) > 500:
            formatted += f"\n\n[Abstract truncated. Full abstract has {len(paper['summary'])} characters]"
        
        return formatted
    except Exception as e:
        return f"Error getting paper details: {str(e)}"

@tool
def download_arxiv_paper(title: str) -> str:
    """Download a paper from arXiv as a PDF file.
    
    Args:
        title: The title of the paper to download
    
    Returns:
        Success message with download location or error message
    
    Example:
        download_arxiv_paper("Attention is All You Need")
    """
    try:
        # Search for the paper by title
        search_query = f'ti:{clean_text(title)}'
        results = search_arxiv_api(search_query, max_results=1)
        
        if not results:
            return f"No paper found with title: {title}"
        
        paper = results[0]
        pdf_url = paper['pdf_url']
        arxiv_id = paper['arxiv_id'].replace('/', '_')  # Make filename safe
        
        # Download the PDF
        filename = f"{arxiv_id}.pdf"
        filepath = os.path.join(DOWNLOAD_PATH, filename)
        
        with urllib.request.urlopen(pdf_url) as response:
            pdf_data = response.read()
        
        with open(filepath, 'wb') as f:
            f.write(pdf_data)
        
        return f"Successfully downloaded '{paper['title']}' to:\n{filepath}\n\nThe paper has been saved to your Downloads/arxiv_papers folder."
    except Exception as e:
        return f"Error downloading paper: {str(e)}"

@tool
def load_arxiv_to_context(title: str) -> str:
    """Load a paper's metadata and abstract into context for analysis.
    
    Args:
        title: The title of the paper to load
    
    Returns:
        Paper information including full abstract
    
    Example:
        load_arxiv_to_context("Attention is All You Need")
    """
    try:
        # Search for the paper by title
        search_query = f'ti:{clean_text(title)}'
        results = search_arxiv_api(search_query, max_results=1)
        
        if not results:
            return f"No paper found with title: {title}"
        
        paper = results[0]
        
        content = f"=== ARXIV PAPER: {paper['title']} ===\n\n"
        content += f"arXiv ID: {paper['arxiv_id']}\n"
        content += f"Authors: {', '.join(paper['authors'])}\n"
        content += f"Published: {paper['published']}\n"
        content += f"Last Updated: {paper['updated']}\n"
        content += f"PDF URL: {paper['pdf_url']}\n"
        content += f"Abstract URL: {paper['abs_url']}\n\n"
        content += "ABSTRACT:\n"
        content += "=" * 50 + "\n"
        content += paper['summary']
        content += "\n" + "=" * 50 + "\n\n"
        content += "Note: This contains only the metadata and abstract. To analyze the full paper content, please download the PDF."
        
        return content
    except Exception as e:
        return f"Error loading paper: {str(e)}"

@tool  
def get_arxiv_url(title: str) -> str:
    """Get the direct PDF URL for a paper on arXiv.
    
    Args:
        title: The title of the paper
    
    Returns:
        The direct PDF URL or error message
    
    Example:
        get_arxiv_url("Attention is All You Need")
    """
    try:
        # Search for the paper by title
        search_query = f'ti:{clean_text(title)}'
        results = search_arxiv_api(search_query, max_results=1)
        
        if not results:
            return f"No paper found with title: {title}"
        
        paper = results[0]
        return f"PDF URL: {paper['pdf_url']}\nAbstract URL: {paper['abs_url']}"
    except Exception as e:
        return f"Error getting paper URL: {str(e)}"