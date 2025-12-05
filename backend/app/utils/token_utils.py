"""
Token Tracking Utilities

Tracks token usage and costs for LLM API calls.
Gemini 2.5 Flash pricing (via OpenRouter):
- $0.30 per 1M input tokens
- $2.50 per 1M output tokens
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
import tiktoken


@dataclass
class TokenUsage:
    """Track token usage for a single API call"""
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = "google/gemini-2.5-flash"
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    @property
    def input_cost(self) -> float:
        """Cost in USD for input tokens"""
        return (self.input_tokens / 1_000_000) * 0.30
    
    @property
    def output_cost(self) -> float:
        """Cost in USD for output tokens"""
        return (self.output_tokens / 1_000_000) * 2.50
    
    @property
    def total_cost(self) -> float:
        """Total cost in USD"""
        return self.input_cost + self.output_cost


class TokenTracker:
    """
    Track cumulative token usage and costs across multiple API calls.
    
    Usage:
        tracker = TokenTracker()
        tracker.add_usage(input_tokens=100, output_tokens=50)
        print(tracker.summary())
    """
    
    # Model pricing per 1M tokens
    PRICING = {
        "google/gemini-2.5-flash": {"input": 0.30, "output": 2.50},
        "google/gemini-2.0-flash-exp:free": {"input": 0.0, "output": 0.0},
        "openai/gpt-4o-mini": {"input": 0.25, "output": 2.00},
        "openai/gpt-5-mini": {"input": 0.25, "output": 2.00},  # User specified
    }
    
    def __init__(self, model: str = "google/gemini-2.5-flash"):
        self.model = model
        self.usage_history: list[TokenUsage] = []
        self._total_input = 0
        self._total_output = 0
    
    def add_usage(
        self, 
        input_tokens: int, 
        output_tokens: int,
        model: str = None
    ) -> TokenUsage:
        """Record token usage from an API call"""
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model or self.model
        )
        self.usage_history.append(usage)
        self._total_input += input_tokens
        self._total_output += output_tokens
        return usage
    
    def add_from_response(self, response) -> Optional[TokenUsage]:
        """
        Extract and record usage from OpenAI-style response object.
        
        Args:
            response: OpenAI ChatCompletion response with usage attribute
        
        Returns:
            TokenUsage if usage data found, None otherwise
        """
        if hasattr(response, 'usage') and response.usage:
            return self.add_usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            )
        return None
    
    @property
    def total_input_tokens(self) -> int:
        return self._total_input
    
    @property
    def total_output_tokens(self) -> int:
        return self._total_output
    
    @property
    def total_tokens(self) -> int:
        return self._total_input + self._total_output
    
    def get_cost(self, model: str = None) -> Dict[str, float]:
        """Calculate costs for a specific model or default model"""
        model = model or self.model
        pricing = self.PRICING.get(model, self.PRICING["google/gemini-2.5-flash"])
        
        input_cost = (self._total_input / 1_000_000) * pricing["input"]
        output_cost = (self._total_output / 1_000_000) * pricing["output"]
        
        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost
        }
    
    @property
    def total_cost(self) -> float:
        """Total cost in USD"""
        return self.get_cost()["total_cost"]
    
    def summary(self) -> str:
        """Get a formatted summary of token usage and costs"""
        costs = self.get_cost()
        return f"""
📊 Token Usage Summary
━━━━━━━━━━━━━━━━━━━━━━
Model: {self.model}
API Calls: {len(self.usage_history)}

Tokens:
  Input:  {self._total_input:,}
  Output: {self._total_output:,}
  Total:  {self.total_tokens:,}

Costs (USD):
  Input:  ${costs['input_cost']:.6f}
  Output: ${costs['output_cost']:.6f}
  Total:  ${costs['total_cost']:.6f}
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    def reset(self):
        """Reset all tracking data"""
        self.usage_history.clear()
        self._total_input = 0
        self._total_output = 0
    
    def to_dict(self) -> Dict:
        """Export usage data as dictionary"""
        costs = self.get_cost()
        return {
            "model": self.model,
            "api_calls": len(self.usage_history),
            "input_tokens": self._total_input,
            "output_tokens": self._total_output,
            "total_tokens": self.total_tokens,
            "input_cost_usd": costs["input_cost"],
            "output_cost_usd": costs["output_cost"],
            "total_cost_usd": costs["total_cost"],
        }


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text using tiktoken.
    Uses cl100k_base encoding (similar to GPT-4/Gemini tokenization).
    """
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # Fallback: rough estimate of 4 chars per token
        return len(text) // 4


# Global tracker instance for easy access
_global_tracker: Optional[TokenTracker] = None


def get_tracker() -> TokenTracker:
    """Get or create global token tracker"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = TokenTracker()
    return _global_tracker


def reset_tracker():
    """Reset the global tracker"""
    global _global_tracker
    if _global_tracker:
        _global_tracker.reset()
