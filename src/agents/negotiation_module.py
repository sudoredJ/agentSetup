"""Agent Negotiation Module
~~~~~~~~~~~~~~~~~~~~~~~~~
DSPy-powered module that enables agents to discuss and negotiate
task assignments collaboratively.
"""

import dspy
import logging
import re
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class NegotiationSignature(dspy.Signature):
    """Signature for agent negotiation reasoning."""
    task: str = dspy.InputField(desc="The task to be evaluated")
    my_capabilities: str = dspy.InputField(desc="My agent capabilities")
    other_evaluations: str = dspy.InputField(desc="Other agents' evaluations and reasoning")
    
    reasoning: str = dspy.OutputField(desc="My reasoning about who should handle this")
    suggested_agent: str = dspy.OutputField(desc="Which agent I think should handle this")
    confidence_adjustment: str = dspy.OutputField(desc="How I should adjust my confidence based on discussion")


class CollaborativeEvaluator(dspy.Module):
    """Module for collaborative task evaluation and negotiation."""
    
    def __init__(self, agent_name: str, capabilities: str):
        super().__init__()
        self.agent_name = agent_name
        self.capabilities = capabilities
        self.negotiator = dspy.ChainOfThought(NegotiationSignature)
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{agent_name}")
    
    def evaluate_with_discussion(self, task: str, other_evaluations: List[Dict]) -> Tuple[int, str]:
        """
        Evaluate task considering other agents' input.
        Returns (confidence, reasoning)
        """
        # Format other evaluations
        eval_text = self._format_evaluations(other_evaluations)
        
        try:
            # Use DSPy to reason about the task
            result = self.negotiator(
                task=task,
                my_capabilities=self.capabilities,
                other_evaluations=eval_text
            )
            
            # Extract confidence adjustment
            confidence_delta = self._parse_confidence_adjustment(result.confidence_adjustment)
            
            return confidence_delta, result.reasoning
            
        except Exception as e:
            self.logger.error(f"Negotiation error: {e}")
            return 0, "Error in collaborative evaluation"
    
    def _format_evaluations(self, evaluations: List[Dict]) -> str:
        """Format other agents' evaluations for context."""
        if not evaluations:
            return "No other agents have evaluated yet."
        
        formatted = []
        for eval in evaluations:
            agent = eval.get('agent', 'Unknown')
            conf = eval.get('confidence', 0)
            reason = eval.get('reasoning', '')
            formatted.append(f"{agent}: {conf}% - {reason}")
        
        return "\n".join(formatted)
    
    def _parse_confidence_adjustment(self, adjustment_text: str) -> int:
        """Parse confidence adjustment from text."""
        # Look for patterns like "+20", "-10", "increase by 30", etc.
        patterns = [
            r'([+-]?\d+)%?',
            r'increase by (\d+)',
            r'decrease by (\d+)',
            r'boost to (\d+)',
            r'reduce to (\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, adjustment_text.lower())
            if match:
                if 'decrease' in pattern or 'reduce' in pattern:
                    return -int(match.group(1))
                elif 'to' in pattern:
                    return int(match.group(1))  # Absolute value
                else:
                    return int(match.group(1))
        
        return 0  # No adjustment found


class AgentDiscussionCoordinator:
    """Coordinates multi-agent discussion for task assignment."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.discussion_rounds = 3  # Max rounds of discussion
        self.target_confidence = 50  # Target confidence to reach
    
    def facilitate_discussion(self, task: str, agents: Dict[str, any], client, channel: str, thread_ts: str):
        """
        Facilitate discussion between agents until consensus or timeout.
        """
        evaluations = {}
        discussion_history = []
        
        for round_num in range(self.discussion_rounds):
            self.logger.info(f"Discussion round {round_num + 1}")
            
            # Each agent evaluates/re-evaluates
            for agent_name, agent in agents.items():
                if hasattr(agent, 'collaborative_evaluate'):
                    # Get agent's evaluation considering others
                    confidence, reasoning = agent.collaborative_evaluate(
                        task, 
                        discussion_history
                    )
                else:
                    # Fallback for agents without collaborative evaluation
                    can_handle, confidence = agent.evaluate_request(task)
                    if not can_handle:
                        confidence = 0
                    reasoning = f"{agent_name} evaluated based on capabilities"
                
                evaluations[agent_name] = {
                    'confidence': confidence,
                    'reasoning': reasoning,
                    'round': round_num + 1
                }
                
                # Post to thread
                message = f"🤔 {agent_name} (Round {round_num + 1}): {confidence}%\n{reasoning}"
                
                try:
                    client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text=message
                    )
                except Exception as e:
                    self.logger.error(f"Failed to post discussion: {e}")
                
                # Add to history
                discussion_history.append({
                    'agent': agent_name,
                    'confidence': confidence,
                    'reasoning': reasoning
                })
                
                # Check if we've reached target confidence
                if confidence >= self.target_confidence:
                    self.logger.info(f"{agent_name} reached target confidence!")
                    return agent_name, confidence, evaluations
            
            # Brief pause between rounds
            import time
            time.sleep(1)
        
        # Return highest confidence after all rounds
        if evaluations:
            best_agent = max(evaluations.items(), key=lambda x: x[1]['confidence'])
            return best_agent[0], best_agent[1]['confidence'], evaluations
        
        return None, 0, evaluations