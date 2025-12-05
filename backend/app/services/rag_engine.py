"""
RAG (Retrieval Augmented Generation) Engine

Features:
1. Hybrid retrieval - combines current query with conversation context
2. LLM-based query rewriting - no hardcoded keywords
3. Structured output for product card selection
4. Dual namespace search (browsing + products)
"""
from typing import List, Dict, Optional, Tuple
import logging
import json
from pydantic import BaseModel, Field
from openai import OpenAI
from app.utils.config import get_settings
from app.utils.token_utils import get_tracker
from app.services.vector_store import PineconeStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryRewrite(BaseModel):
    """LLM-rewritten query for better retrieval"""
    rewritten_query: str = Field(description="The expanded search query")
    product_category: Optional[str] = Field(default=None, description="Product category if relevant (shoes, clothing, etc)")
    intent: str = Field(description="User's intent: 'recommendation', 'memory_recall', 'comparison', 'general'")


class ProductSelection(BaseModel):
    """Structured output for LLM product selections"""
    show_product_cards: bool = Field(description="Whether to display product recommendation cards")
    selected_product_names: List[str] = Field(default_factory=list, description="Product names to display as cards")


class RAGEngine:
    """
    RAG Engine with hybrid retrieval and LLM query rewriting.
    """
    
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key
        )
        self.model = settings.chat_model
        self.vector_store = PineconeStore()
        self.tracker = get_tracker()
    
    def rewrite_query(self, query: str, conversation_history: List[Dict] = None) -> QueryRewrite:
        """
        Use LLM to rewrite/expand the query based on conversation context.
        No hardcoded keywords - LLM decides everything.
        """
        history_context = ""
        if conversation_history:
            recent = conversation_history[-4:]  # Last 2 exchanges
            history_context = "\n".join([f"{m['role']}: {m['content'][:200]}" for m in recent])
        
        prompt = f"""Analyze this user query and rewrite it for optimal product search.

Conversation History:
{history_context if history_context else "No previous conversation"}

Current Query: "{query}"

Rewrite the query to be more specific and searchable. Consider:
1. If the query is vague (like "more suggestions"), expand it based on conversation context
2. Extract the product category if any (shoes, clothing, fitness, outdoor, etc)
3. Determine the user's intent

Respond with JSON:
{{"rewritten_query": "expanded search query with specific product terms", "product_category": "category or null", "intent": "recommendation|memory_recall|comparison|general"}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=150
            )
            
            content = response.choices[0].message.content.strip()
            # Parse JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            result = QueryRewrite(**data)
            logger.info(f"🔄 Query rewritten: '{query}' → '{result.rewritten_query}' (intent: {result.intent})")
            return result
        except Exception as e:
            logger.warning(f"Query rewrite failed: {e}")
            return QueryRewrite(rewritten_query=query, intent="general")
    
    def retrieve_context(
        self, 
        query: str, 
        rewritten_query: str = None,
        category: str = None,
        top_k: int = 5
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Hybrid retrieval using both original and rewritten queries.
        """
        search_query = rewritten_query or query
        logger.info(f"🔍 Searching for: '{search_query}'")
        
        # Search browsing history
        browsing_results = self.vector_store.search_browsing(search_query, top_k=top_k)
        logger.info(f"📚 Found {len(browsing_results)} browsing entries")
        
        # Search products with potentially enhanced query
        product_query = search_query
        if category:
            product_query = f"{category} {search_query}"
        
        product_results = self.vector_store.search_products(product_query, top_k=top_k * 2)  # Get more products
        logger.info(f"📦 Found {len(product_results)} products")
        
        return browsing_results, product_results
    
    def format_context(self, browsing: List[Dict], products: List[Dict]) -> str:
        """Format retrieved results into context string for LLM"""
        context_parts = []
        
        if browsing:
            context_parts.append("## User's Browsing History:")
            for i, b in enumerate(browsing, 1):
                name = b.get('product_name') or b.get('title', 'Unknown')
                price = b.get('product_price', 0)
                brand = b.get('product_brand', '')
                line = f"{i}. {name}"
                if brand:
                    line += f" by {brand}"
                if price:
                    line += f" - ${price}"
                context_parts.append(line)
        
        if products:
            context_parts.append("\n## Available Products from Catalog:")
            for i, p in enumerate(products, 1):
                name = p.get('name', 'Unknown')
                brand = p.get('brand', 'Unknown')
                price = p.get('price', 0)
                category = p.get('category', '')
                context_parts.append(f"{i}. {name} by {brand} - ${price} ({category})")
        
        return "\n".join(context_parts) if context_parts else "No relevant data found."
    
    def generate_response_with_products(
        self,
        query: str,
        context: str,
        products: List[Dict],
        intent: str,
        conversation_history: List[Dict] = None
    ) -> Tuple[str, List[Dict]]:
        """Generate response with LLM-selected products."""
        
        system_prompt = """You are Nora, a shopping assistant with access to user's browsing history and a product catalog.

Guidelines:
- Use the provided context to answer questions
- For recommendations, explain WHY based on browsing history
- Include prices when discussing products
- Be conversational and helpful

After your response, indicate which products to show as cards (if any)."""

        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history[-6:])
        
        product_names = [p.get('name', '') for p in products]
        
        user_message = f"""Context:
{context}

User's question: {query}
Intent: {intent}

---
After your response, provide JSON:
{{"show_product_cards": true/false, "selected_product_names": ["exact name 1", "exact name 2"]}}

Available products: {product_names[:10]}"""
        
        messages.append({"role": "user", "content": user_message})
        
        logger.info(f"🤖 Calling LLM ({self.model})...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=600
        )
        self.tracker.add_from_response(response)
        
        full_response = response.choices[0].message.content
        logger.info(f"✅ LLM response received ({len(full_response)} chars)")
        
        # Parse structured output - handle multiple JSON formats
        selected_products = []
        clean_response = full_response
        
        try:
            json_str = None
            
            # Try markdown code block first
            if "```json" in full_response:
                json_start = full_response.find("```json") + 7
                json_end = full_response.find("```", json_start)
                json_str = full_response[json_start:json_end].strip()
                clean_response = full_response[:full_response.find("```json")].strip()
            # Try raw JSON at end of response (with or without newline)
            elif '{"show_product_cards"' in full_response:
                json_start = full_response.find('{"show_product_cards"')
                json_str = full_response[json_start:].strip()
                clean_response = full_response[:json_start].strip()
            
            # Parse the JSON if found
            if json_str:
                selection = json.loads(json_str)
                
                if selection.get("show_product_cards", False):
                    selected_names = selection.get("selected_product_names", [])
                    for name in selected_names[:4]:
                        for p in products:
                            if p.get('name', '').lower() == name.lower():
                                selected_products.append(p)
                                break
                    logger.info(f"📦 Selected {len(selected_products)} products for display")
        except Exception as e:
            logger.warning(f"Could not parse product selection: {e}")
        
        return clean_response, selected_products
    
    def chat(self, query: str, conversation_history: List[Dict] = None) -> Dict:
        """Main chat method with hybrid retrieval."""
        
        # 1. Rewrite query using LLM (no hardcoded keywords)
        rewrite = self.rewrite_query(query, conversation_history)
        
        # 2. Hybrid retrieval with rewritten query
        browsing, products = self.retrieve_context(
            query=query,
            rewritten_query=rewrite.rewritten_query,
            category=rewrite.product_category
        )
        
        # 3. Format context
        context = self.format_context(browsing, products)
        
        # 4. Generate response with product selection
        response, selected_products = self.generate_response_with_products(
            query=query,
            context=context,
            products=products,
            intent=rewrite.intent,
            conversation_history=conversation_history
        )
        
        return {
            "response": response,
            "query_type": rewrite.intent,
            "sources": {
                "browsing": browsing[:5],
                "products": selected_products
            }
        }
    
    def close(self):
        """Cleanup resources"""
        self.vector_store.close()
