"""
RAG (Retrieval Augmented Generation) Engine

Clean, LLM-first architecture:
- Pure embeddings for retrieval (no regex patterns)
- Single LLM call with structured output
- Product selection by ID (no name matching)
- All intelligence handled by LLM + embeddings
"""
import json
import logging
from typing import List, Dict, Optional, Any
from openai import OpenAI
from app.utils.config import get_settings
from app.utils.token_utils import get_tracker
from app.services.vector_store import PineconeStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Simplified RAG Engine - lets embeddings and LLM handle all intelligence.
    No regex patterns, no hardcoded keywords, no manual category detection.
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
    
    def retrieve(
        self, 
        query: str, 
        top_k: int = 5,
        user_profile: Optional[object] = None
    ) -> tuple[List[Dict], List[Dict]]:
        """
        Pure embedding-based retrieval - no filters, no category detection.
        Embeddings naturally return semantically relevant results.
        """
        # Get browsing history relevant to query
        browsing_results = self.vector_store.search_browsing(
            query=query, 
            top_k=top_k
        )
        
        # Get products relevant to query
        product_results = self.vector_store.search_products(
            query=query, 
            top_k=top_k * 2  # Get more products for LLM to choose from
        )
        
        # Optional: Boost brands from user profile (soft boosting only)
        if user_profile and hasattr(user_profile, 'brand_affinity') and user_profile.brand_affinity:
            for p in product_results:
                if p.get('brand', '').lower() in [b.lower() for b in user_profile.brand_affinity]:
                    p['profile_match'] = True
        
        logger.info(f"� Found {len(browsing_results)} browsing, {len(product_results)} products")
        
        return browsing_results, product_results
    
    def format_context(
        self, 
        browsing: List[Dict], 
        products: List[Dict], 
        user_profile: Optional[object] = None
    ) -> str:
        """Format retrieved data as context for LLM"""
        parts = []
        
        # User profile context
        if user_profile:
            profile_parts = []
            if hasattr(user_profile, 'visual_style') and user_profile.visual_style:
                profile_parts.append(f"Style preferences: {', '.join(user_profile.visual_style)}")
            if hasattr(user_profile, 'brand_affinity') and user_profile.brand_affinity:
                profile_parts.append(f"Favorite brands: {', '.join(user_profile.brand_affinity)}")
            if hasattr(user_profile, 'dislikes') and user_profile.dislikes:
                profile_parts.append(f"Dislikes (avoid these): {', '.join(user_profile.dislikes)}")
            if profile_parts:
                parts.append("## User Profile\n" + "\n".join(profile_parts))
        
        # Browsing history
        if browsing:
            parts.append("## Recent Browsing History")
            for b in browsing[:5]:
                title = b.get('title', 'Unknown')
                summary = b.get('semantic_summary', '')[:200]
                parts.append(f"- {title}: {summary}")
        
        # Available products with IDs
        if products:
            parts.append("\n## Available Products (use these IDs in your response)")
            for p in products:
                pid = p.get('id', '')
                name = p.get('name', 'Unknown')
                brand = p.get('brand', '')
                price = p.get('price', 0)
                desc = p.get('description', '')[:150]
                match = " ⭐ PROFILE MATCH" if p.get('profile_match') else ""
                parts.append(f"- ID: {pid}\n  {name} by {brand} - ${price}{match}\n  {desc}")
        
        return "\n".join(parts)
    
    def generate_response(
        self,
        query: str,
        context: str,
        products: List[Dict],
        conversation_history: List[Dict] = None
    ) -> tuple[str, List[Dict]]:
        """
        Single LLM call that handles everything:
        - Understands user intent from query
        - Uses browsing context for personalization
        - Selects products by ID
        - Provides specific reasons for each
        """
        
        # Build product ID list for the prompt
        product_ids = [p.get('id', '') for p in products]
        
        system_prompt = """You are Nora, a personalized shopping assistant. You have access to the user's browsing history and available products.

Your response MUST be valid JSON in this exact format:
{
  "response": "Your helpful, conversational response",
  "selected_products": [
    {
      "id": "exact product ID from the list",
      "reason": "1-2 sentences explaining WHY this product fits the user based on their browsing history, preferences, or question"
    }
  ]
}

RULES:
1. Use ONLY product IDs from the Available Products list
2. Select 2-4 products that are ACTUALLY relevant to the user's question
3. Write personalized reasons based on their browsing history and profile
4. If no products match the user's request, return an empty selected_products array
5. Be conversational and helpful in your response"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history for context
        if conversation_history:
            messages.extend(conversation_history[-4:])
        
        user_message = f"""Context:
{context}

Available product IDs: {product_ids}

User's question: {query}

Respond with JSON containing your response and selected product IDs with reasons."""
        
        messages.append({"role": "user", "content": user_message})
        
        logger.info(f"🤖 Calling LLM...")
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        self.tracker.add_from_response(response)
        
        # Parse JSON response
        text_response = "I can help you find products!"
        selected_products = []
        
        try:
            result = json.loads(response.choices[0].message.content)
            text_response = result.get("response", text_response)
            
            # Match selected IDs to actual products
            selected_items = result.get("selected_products", [])
            logger.info(f"📋 LLM selected {len(selected_items)} products")
            
            # Create lookup by ID
            product_by_id = {p.get('id', ''): p for p in products}
            
            for item in selected_items[:4]:
                pid = item.get("id", "")
                reason = item.get("reason", "Recommended for you")
                
                if pid in product_by_id:
                    product = product_by_id[pid]
                    selected_products.append({
                        **product,
                        "reason_text": reason,
                        "reason_codes": ["personalized"]
                    })
                    
            logger.info(f"📦 Matched {len(selected_products)} products by ID")
            
        except Exception as e:
            logger.warning(f"JSON parse error: {e}")
            text_response = response.choices[0].message.content
        
        # Fallback if no products selected
        if not selected_products and products:
            logger.info("⚠️ Fallback: showing top products")
            for p in products[:4]:
                selected_products.append({
                    **p,
                    "reason_text": "Top match for your query",
                    "reason_codes": ["relevance"]
                })
        
        return text_response, selected_products
    
    def chat(
        self, 
        query: str, 
        conversation_history: List[Dict] = None, 
        user_profile: Optional[object] = None
    ) -> Dict:
        """
        Complete RAG pipeline in 3 steps:
        1. Retrieve - Embedding search for browsing + products
        2. Format - Build context string
        3. Generate - Single LLM call for response + selection
        """
        logger.info(f"💬 Query: '{query}'")
        
        # 1. Retrieve relevant context
        browsing, products = self.retrieve(
            query=query,
            user_profile=user_profile
        )
        
        # 2. Format context for LLM
        context = self.format_context(browsing, products, user_profile)
        
        # 3. Generate response with product selection
        response_text, selected_products = self.generate_response(
            query=query,
            context=context,
            products=products,
            conversation_history=conversation_history
        )
        
        return {
            "response": response_text,
            "products": selected_products,
            "sources": {
                "browsing": len(browsing),
                "products": len(products)
            }
        }
    
    def close(self):
        """Cleanup resources"""
        self.vector_store.close()
