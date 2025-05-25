from openai import OpenAI
import os
import requests
import urllib.parse
from dotenv import load_dotenv
from typing import List, Optional
import json

load_dotenv()

class AutomatedWikipediaAgent:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("MILITARY_API_KEY"),
        )
        self.model = "google/gemma-3n-e4b-it:free"
    
    def search_wikipedia(self, query: str, limit: int = 10) -> List[dict]:
        """
        Step 1: Search Wikipedia and return list of articles with metadata
        """
        print(f"🔍 Searching Wikipedia for: '{query}'")
        
        api_url = "https://en.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': query,
            'srlimit': limit,
            'srprop': 'size|wordcount|timestamp|snippet'
        }
        
        try:
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            search_results = data.get('query', {}).get('search', [])
            
            # Build list with URLs and metadata
            articles = []
            for i, result in enumerate(search_results, 1):
                title = result['title']
                snippet = result.get('snippet', '').replace('<span class="searchmatch">', '').replace('</span>', '')
                encoded_title = urllib.parse.quote(title.replace(' ', '_'))
                url = f"https://en.wikipedia.org/wiki/{encoded_title}"
                
                articles.append({
                    'index': i,
                    'title': title,
                    'url': url,
                    'snippet': snippet,
                    'wordcount': result.get('wordcount', 0)
                })
            
            print(f"📋 Found {len(articles)} Wikipedia articles")
            return articles
            
        except Exception as e:
            print(f"❌ Wikipedia search error: {e}")
            return []
    
    def ai_select_best_url(self, query: str, articles: List[dict]) -> str:
        """
        Step 2: AI model selects the most relevant URL from the list
        """
        print(f"🤖 AI analyzing {len(articles)} articles to find most relevant...")
        
        # Prepare the article list for AI
        articles_text = ""
        for article in articles:
            articles_text += f"{article['index']}. Title: {article['title']}\n"
            articles_text += f"   URL: {article['url']}\n"
            articles_text += f"   Description: {article['snippet']}\n"
            articles_text += f"   Word count: {article['wordcount']}\n\n"
        
        system_prompt = """You are an expert at selecting the most relevant Wikipedia article.

Your task:
1. Analyze the user's query and the list of Wikipedia articles
2. Select ONLY the most relevant article that best matches the query
3. Return ONLY the URL of the selected article
4. NO explanations, NO additional text, JUST the URL

Rules:
- Return EXACTLY one URL
- The URL must be from the provided list
- Choose based on relevance to the user's query
- Consider title relevance, description content, and article length"""

        user_message = f"""Query: {query}

Available Wikipedia articles:
{articles_text}

Select the MOST RELEVANT URL for this query. Return ONLY the URL:"""

        try:
            # Combine system prompt with user message for models that don't support system role
            combined_message = f"""{system_prompt}

Query: {query}

Available Wikipedia articles:
{articles_text}

Based on the above instructions, select the MOST RELEVANT URL for this query. Return ONLY the URL:"""

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": combined_message}
                ],
                temperature=0.1,  # Low temperature for consistent selection
                max_tokens=100
            )
            
            selected_url = completion.choices[0].message.content.strip()
            
            # Validate that the returned URL is from our list
            valid_urls = [article['url'] for article in articles]
            if selected_url in valid_urls:
                print(f"✅ AI selected: {selected_url}")
                return selected_url
            else:
                # Fallback to first URL if AI returns invalid selection
                print(f"⚠️ AI returned invalid URL, using first result")
                return articles[0]['url'] if articles else ""
                
        except Exception as e:
            print(f"❌ AI selection error: {e}")
            # Fallback to first URL
            return articles[0]['url'] if articles else ""
    
    def optimize_query(self, user_query: str) -> str:
        """
        Step 1: AI optimizes the user query for better Wikipedia search results
        """
        print(f"🧠 Optimizing query: '{user_query}'")
        
        system_prompt = """You are a Wikipedia search query optimization expert.

Your task:
1. Take the user's natural language query
2. Transform it into the most effective Wikipedia search terms
3. Remove unnecessary words, add relevant keywords
4. Make it concise but comprehensive for Wikipedia search

Rules:
- Return ONLY the optimized search query
- No explanations, just the improved search terms
- Focus on key concepts, proper nouns, and important keywords
- Remove filler words like "give me", "I want", "information about"
- Add relevant synonyms or alternative terms if helpful
- Keep it under 10 words when possible

Examples:
- "give me info about Indian army operations" → "Indian Army military operations combat missions"
- "I want to know about python programming" → "Python programming language"
- "tell me about artificial intelligence" → "artificial intelligence machine learning"
"""

        user_message = f"Optimize this query for Wikipedia search: {user_query}"
        
        try:
            # Combine system prompt with user message for models that don't support system role
            combined_message = f"{system_prompt}\n\nUser request: {user_message}\n\nOptimized query:"
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": combined_message}
                ],
                temperature=0.3,
                max_tokens=50
            )
            
            optimized_query = completion.choices[0].message.content.strip()
            print(f"✨ Optimized to: '{optimized_query}'")
            return optimized_query
            
        except Exception as e:
            print(f"⚠️ Query optimization failed: {e}, using original query")
            return user_query
    
    def search_and_select(self, query: str) -> str:
        """
        Main agent function: Automatically execute the full flow
        User Query → AI Query Optimization → Wikipedia Search → AI Selection → Return single URL
        """
        print(f"\n🚀 Starting automated search for: '{query}'")
        print("="*60)
        
        # Step 1: Optimize query with AI
        optimized_query = self.optimize_query(query)
        
        # Step 2: Search Wikipedia with optimized query
        articles = self.search_wikipedia(optimized_query)
        
        if not articles:
            print("❌ No Wikipedia articles found")
            return ""
        
        # Step 3: AI selects best URL (using original query for relevance)
        selected_url = self.ai_select_best_url(query, articles)
        
        if selected_url:
            print("="*60)
            print(f"🎯 FINAL RESULT: {selected_url}")
            return selected_url
        else:
            print("❌ Failed to select URL")
            return ""
    
    def batch_search(self, queries: List[str]) -> dict:
        """
        Process multiple queries automatically
        """
        results = {}
        
        for i, query in enumerate(queries, 1):
            print(f"\n{'='*20} QUERY {i}/{len(queries)} {'='*20}")
            url = self.search_and_select(query)
            results[query] = url
        
        return results

# Convenience functions for direct use
def get_wikipedia_url(query: str) -> str:
    """
    Simple function: Input query → Output single most relevant Wikipedia URL
    """
    agent = AutomatedWikipediaAgent()
    return agent.search_and_select(query)

def get_multiple_urls(queries: List[str]) -> dict:
    """
    Process multiple queries at once
    """
    agent = AutomatedWikipediaAgent()
    return agent.batch_search(queries)

# Example usage
if __name__ == "__main__":
   
    
    # Multiple queries example
    queries = [
        "list of all indian Army military operations",
    ]
    
    results = get_multiple_urls(queries)
    
    print("BATCH RESULTS:")
    for query, url in results.items():
        print(f"Query: {query}")
        print(f"URL: {url}")
        print("-" * 40)