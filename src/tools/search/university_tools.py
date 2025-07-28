"""University domain lookup tools using the university-domains-list API."""

import requests
import json
from typing import Optional, List, Dict, Any
from smolagents import tool
import logging

logger = logging.getLogger(__name__)

# Using the free hosted API
UNIVERSITY_API_BASE = "http://universities.hipolabs.com"

@tool
def search_university(
    name: Optional[str] = None,
    domain: Optional[str] = None,
    country: Optional[str] = None
) -> str:
    """Search for universities by name, domain, or country.
    
    Args:
        name: University name to search for (partial match supported)
        domain: Domain to search for (e.g., 'mit.edu')
        country: Country name to filter by
        
    Returns:
        Information about matching universities including domains and websites
        
    Examples:
        search_university(name="MIT")
        search_university(domain="stanford.edu")
        search_university(country="United States", name="Berkeley")
    """
    try:
        # Build query parameters
        params = {}
        if name:
            params['name'] = name
        if country:
            params['country'] = country
            
        # Make request to API
        if params:
            url = f"{UNIVERSITY_API_BASE}/search"
            response = requests.get(url, params=params, timeout=10)
        else:
            # Get all universities if no params (limit to first 100)
            url = UNIVERSITY_API_BASE
            response = requests.get(url, timeout=10)
            
        response.raise_for_status()
        
        # Parse response
        try:
            universities = response.json()
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response: {response.text[:200]}")
            return "Error: Invalid response from university API"
        
        # Ensure we have a list
        if not isinstance(universities, list):
            logger.error(f"Unexpected response format: {type(universities)}")
            return "Error: Unexpected response format from university API"
        
        # If searching by domain, filter results
        if domain:
            domain_lower = domain.lower()
            universities = [
                uni for uni in universities 
                if any(domain_lower in d.lower() for d in uni.get('domains', []))
            ]
        
        # Limit results to prevent huge outputs
        universities = universities[:10]
        
        if not universities:
            return "No universities found matching your search criteria."
        
        # Format results
        results = []
        for uni in universities:
            uni_info = []
            uni_info.append(f"**{uni.get('name', 'Unknown')}**")
            uni_info.append(f"Country: {uni.get('country', 'Unknown')}")
            
            if uni.get('state-province'):
                uni_info.append(f"State/Province: {uni['state-province']}")
            
            domains = uni.get('domains', [])
            if domains:
                uni_info.append(f"Domains: {', '.join(domains)}")
            
            web_pages = uni.get('web_pages', [])
            if web_pages:
                uni_info.append(f"Websites: {', '.join(web_pages)}")
            
            results.append('\n'.join(uni_info))
        
        header = f"Found {len(results)} universities"
        if len(universities) == 10:
            header += " (showing first 10)"
        header += ":\n\n"
        
        return header + '\n\n---\n\n'.join(results)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching universities: {e}")
        return f"Error searching universities: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"An error occurred: {str(e)}"


@tool
def verify_university_email(email: str) -> str:
    """Verify if an email address belongs to a known university domain.
    
    Args:
        email: Email address to verify (e.g., 'student@mit.edu')
        
    Returns:
        University information if the domain is recognized, or a message if not found
        
    Example:
        verify_university_email("john@stanford.edu")
    """
    try:
        # Extract domain from email
        if '@' not in email:
            return "Invalid email address format. Please provide an email like 'user@domain.edu'"
        
        domain = email.split('@')[1].lower()
        
        # Search all universities (this is not ideal for production - better to cache)
        response = requests.get(UNIVERSITY_API_BASE, timeout=10)
        response.raise_for_status()
        universities = response.json()
        
        # Find universities with matching domain
        matches = []
        for uni in universities:
            uni_domains = [d.lower() for d in uni.get('domains', [])]
            if domain in uni_domains:
                matches.append(uni)
        
        if not matches:
            return f"The domain '{domain}' is not recognized as a university domain."
        
        # Format results
        results = []
        for uni in matches:
            uni_info = []
            uni_info.append(f"✓ **{uni.get('name', 'Unknown')}**")
            uni_info.append(f"  Country: {uni.get('country', 'Unknown')}")
            
            if uni.get('state-province'):
                uni_info.append(f"  State/Province: {uni['state-province']}")
            
            web_pages = uni.get('web_pages', [])
            if web_pages:
                uni_info.append(f"  Official Website: {web_pages[0]}")
            
            results.append('\n'.join(uni_info))
        
        return f"Email domain '{domain}' is verified!\n\n" + '\n\n'.join(results)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error verifying email: {e}")
        return f"Error verifying university email: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"An error occurred: {str(e)}"


@tool
def list_universities_by_country(country: str, limit: int = 20) -> str:
    """List universities in a specific country.
    
    Args:
        country: Country name (e.g., 'United States', 'Canada', 'United Kingdom')
        limit: Maximum number of universities to return (default 20)
        
    Returns:
        List of universities in the specified country
        
    Example:
        list_universities_by_country("Germany", limit=10)
    """
    try:
        # Search by country
        params = {'country': country}
        response = requests.get(f"{UNIVERSITY_API_BASE}/search", params=params, timeout=10)
        response.raise_for_status()
        universities = response.json()
        
        if not universities:
            return f"No universities found in {country}. Try variations like 'United States' instead of 'USA'."
        
        # Limit results
        universities = universities[:limit]
        
        # Format results
        results = []
        for i, uni in enumerate(universities, 1):
            uni_info = f"{i}. **{uni.get('name', 'Unknown')}**"
            
            domains = uni.get('domains', [])
            if domains:
                uni_info += f" ({domains[0]})"
            
            results.append(uni_info)
        
        header = f"Universities in {country} (showing {len(results)} of {len(universities)}):\n\n"
        return header + '\n'.join(results)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error listing universities: {e}")
        return f"Error listing universities: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"An error occurred: {str(e)}"