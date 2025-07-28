"""BeautifulSoup-based search system for web scraping and information gathering."""

import requests
import logging
import time
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import random

logger = logging.getLogger(__name__)

class BeautifulSearch:
    """BeautifulSoup-based search and scraping system."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.visited_urls = set()
        self.config = self._load_config()
    
    def _load_config(self):
        """Load search configuration from system config."""
        default_config = {
            'enabled': True,
            'engines': ['google', 'bing', 'wikipedia', 'duckduckgo'],
            'timeout': 15,
            'max_results_per_engine': 5
        }
        
        try:
            import yaml
            import os
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'configs', 'system_config.yaml')
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                if 'features' in config and 'search' in config['features']:
                    default_config.update(config['features']['search'])
                    
        except Exception as e:
            logger.warning(f"Could not load search config, using defaults: {e}")
        
        return default_config
        
    def search_google(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search Google using BeautifulSoup scraping."""
        try:
            logger.info(f"Searching Google for: '{query}'")
            
            # Google search URL
            search_url = "https://www.google.com/search"
            params = {
                'q': query,
                'num': max_results + 2,  # Get a few extra in case some fail
                'hl': 'en'
            }
            
            response = self.session.get(search_url, params=params, timeout=self.config['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Find search result containers
            search_results = soup.find_all('div', class_='g')
            
            for result in search_results[:max_results]:
                try:
                    # Extract title and link
                    title_element = result.find('h3')
                    if not title_element:
                        continue
                        
                    title = title_element.get_text(strip=True)
                    
                    # Find the link
                    link_element = result.find('a')
                    if not link_element:
                        continue
                        
                    url = link_element.get('href', '')
                    if not url.startswith('http'):
                        continue
                    
                    # Extract snippet
                    snippet_element = result.find('div', class_='VwiC3b')
                    snippet = snippet_element.get_text(strip=True) if snippet_element else "No description available"
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'body': snippet,
                        'source': 'Google'
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing Google result: {e}")
                    continue
            
            logger.info(f"Google search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return []
    
    def search_bing(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search Bing using BeautifulSoup scraping."""
        try:
            logger.info(f"Searching Bing for: '{query}'")
            
            search_url = "https://www.bing.com/search"
            params = {
                'q': query,
                'count': max_results
            }
            
            response = self.session.get(search_url, params=params, timeout=self.config['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Find search result containers
            search_results = soup.find_all('li', class_='b_algo')
            
            for result in search_results[:max_results]:
                try:
                    # Extract title and link
                    title_element = result.find('h2')
                    if not title_element:
                        continue
                        
                    title = title_element.get_text(strip=True)
                    
                    # Find the link
                    link_element = title_element.find('a')
                    if not link_element:
                        continue
                        
                    url = link_element.get('href', '')
                    if not url.startswith('http'):
                        continue
                    
                    # Extract snippet
                    snippet_element = result.find('p')
                    snippet = snippet_element.get_text(strip=True) if snippet_element else "No description available"
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'body': snippet,
                        'source': 'Bing'
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing Bing result: {e}")
                    continue
            
            logger.info(f"Bing search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            return []
    
    def search_wikipedia(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search Wikipedia using their API."""
        try:
            logger.info(f"Searching Wikipedia for: '{query}'")
            
            # Try direct page lookup first
            wiki_url = f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"
            response = self.session.get(wiki_url, timeout=self.config['timeout'])
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract title and content
                title = soup.find('h1', id='firstHeading')
                title_text = title.get_text(strip=True) if title else query
                
                # Extract first paragraph
                content_div = soup.find('div', id='mw-content-text')
                first_para = content_div.find('p') if content_div else None
                snippet = first_para.get_text(strip=True)[:300] + "..." if first_para else "Information about " + query
                
                return [{
                    'title': title_text,
                    'url': wiki_url,
                    'body': snippet,
                    'source': 'Wikipedia'
                }]
            
            # If direct lookup fails, try search API
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': query,
                'srlimit': max_results
            }
            
            response = self.session.get(search_url, params=params, timeout=self.config['timeout'])
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get('query', {}).get('search', []):
                    title = item.get('title', query)
                    url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    snippet = BeautifulSoup(item.get('snippet', ''), 'html.parser').get_text(strip=True)
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'body': snippet,
                        'source': 'Wikipedia'
                    })
                
                logger.info(f"Wikipedia search found {len(results)} results")
                return results
                
        except Exception as e:
            logger.error(f"Wikipedia search failed: {e}")
        
        return []
    
    def search_duckduckgo(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search DuckDuckGo using BeautifulSoup scraping."""
        try:
            logger.info(f"Searching DuckDuckGo for: '{query}'")
            
            search_url = "https://html.duckduckgo.com/html/"
            params = {
                'q': query
            }
            
            response = self.session.get(search_url, params=params, timeout=self.config['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Find search result containers
            search_results = soup.find_all('div', class_='result')
            
            for result in search_results[:max_results]:
                try:
                    # Extract title and link
                    title_element = result.find('a', class_='result__a')
                    if not title_element:
                        continue
                        
                    title = title_element.get_text(strip=True)
                    url = title_element.get('href', '')
                    
                    # DuckDuckGo uses redirect URLs, we'll keep them as-is
                    if not url:
                        continue
                    
                    # Extract snippet
                    snippet_element = result.find('a', class_='result__snippet')
                    snippet = snippet_element.get_text(strip=True) if snippet_element else "No description available"
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'body': snippet,
                        'source': 'DuckDuckGo'
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing DuckDuckGo result: {e}")
                    continue
            
            logger.info(f"DuckDuckGo search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []
    
    def search_with_fallbacks(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search using multiple engines with fallbacks."""
        # Map engine names to methods
        engine_methods = {
            'google': self.search_google,
            'bing': self.search_bing,
            'wikipedia': self.search_wikipedia,
            'duckduckgo': self.search_duckduckgo
        }
        
        # Get enabled engines from config
        enabled_engines = self.config.get('engines', ['google', 'bing', 'wikipedia', 'duckduckgo'])
        search_methods = [engine_methods[engine] for engine in enabled_engines if engine in engine_methods]
        
        all_results = []
        seen_urls = set()
        
        for method in search_methods:
            try:
                logger.info(f"Trying search method: {method.__name__}")
                results = method(query, self.config.get('max_results_per_engine', max_results))
                
                # Add unique results
                for result in results:
                    url = result.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(result)
                        
                        if len(all_results) >= max_results:
                            break
                
                if len(all_results) >= max_results:
                    break
                    
                # Add delay between search methods
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Search method {method.__name__} failed: {e}")
                continue
        
        logger.info(f"Combined search found {len(all_results)} unique results")
        return all_results[:max_results]
    
    def scrape_webpage(self, url: str) -> Dict:
        """Scrape content from a webpage."""
        try:
            if url in self.visited_urls:
                return {'error': 'URL already visited'}
            
            self.visited_urls.add(url)
            logger.info(f"Scraping webpage: {url}")
            
            response = self.session.get(url, timeout=self.config['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else "No title"
            
            # Extract main content
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.find('body')
            
            if main_content:
                # Get text content
                text = main_content.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = ' '.join(chunk for chunk in chunks if chunk)
                
                # Create summary (first 1000 characters)
                summary = clean_text[:1000] + "..." if len(clean_text) > 1000 else clean_text
                
                return {
                    'title': title_text,
                    'url': url,
                    'content': clean_text,
                    'summary': summary,
                    'word_count': len(clean_text.split()),
                    'success': True
                }
            else:
                return {
                    'title': title_text,
                    'url': url,
                    'error': 'Could not extract main content',
                    'success': False
                }
                
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return {
                'url': url,
                'error': str(e),
                'success': False
            }

# Global instance
beautiful_search = BeautifulSearch() 