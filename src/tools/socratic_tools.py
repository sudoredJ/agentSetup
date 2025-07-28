"""Socratic Dialog Tools
~~~~~~~~~~~~~~~~~~~~~~~~~
Tools for implementing Socratic method conversations, enabling agents to guide
users through thoughtful questioning and self-discovery.

Provided tools:
• question_generator_tool    – Generate probing Socratic questions
• dialog_tracker_tool       – Track conversation state and themes
• insight_extractor_tool    – Extract key insights from discussions
"""

from smolagents import tool
import json
import os
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Dialog state storage
DIALOG_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "socratic_dialogs.json")


def _load_dialog_state(user_id: str) -> Dict[str, Any]:
    """Load dialog state for a specific user."""
    os.makedirs(os.path.dirname(DIALOG_STATE_FILE), exist_ok=True)
    
    if os.path.exists(DIALOG_STATE_FILE):
        try:
            with open(DIALOG_STATE_FILE, 'r') as f:
                all_states = json.load(f)
                return all_states.get(user_id, {
                    "topics": [],
                    "insights": [],
                    "question_count": 0,
                    "current_theme": None
                })
        except Exception as e:
            logger.error(f"Error loading dialog state: {e}")
    
    return {
        "topics": [],
        "insights": [],
        "question_count": 0,
        "current_theme": None
    }


def _save_dialog_state(user_id: str, state: Dict[str, Any]):
    """Save dialog state for a specific user."""
    os.makedirs(os.path.dirname(DIALOG_STATE_FILE), exist_ok=True)
    
    try:
        all_states = {}
        if os.path.exists(DIALOG_STATE_FILE):
            with open(DIALOG_STATE_FILE, 'r') as f:
                all_states = json.load(f)
        
        all_states[user_id] = state
        
        with open(DIALOG_STATE_FILE, 'w') as f:
            json.dump(all_states, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving dialog state: {e}")


@tool
def question_generator_tool(topic: str, question_type: str = "exploring", context: str = None) -> str:
    """Generate Socratic questions to guide deeper thinking about a topic.
    
    Args:
        topic: The subject or concept to explore through questioning
        question_type: Type of question - exploring, clarifying, challenging, or reflecting (default: exploring)
        context: Optional context from previous conversation
    """
    question_templates = {
        "exploring": [
            f"What do you think is the essence of {topic}?",
            f"How would you define {topic} in your own words?",
            f"What experiences have shaped your understanding of {topic}?",
            f"What aspects of {topic} are you most curious about?",
            f"How does {topic} relate to your personal values or goals?"
        ],
        "clarifying": [
            f"When you say '{topic}', what specifically do you mean?",
            f"Can you give me an example of {topic} from your experience?",
            f"What's the difference between {topic} and something similar?",
            f"What assumptions might we be making about {topic}?",
            f"How would you explain {topic} to someone unfamiliar with it?"
        ],
        "challenging": [
            f"What evidence supports your view of {topic}?",
            f"What might someone who disagrees say about {topic}?",
            f"Are there exceptions to what you've said about {topic}?",
            f"How might {topic} be viewed differently in another context?",
            f"What are the potential limitations of thinking about {topic} this way?"
        ],
        "reflecting": [
            f"How has your understanding of {topic} changed through our discussion?",
            f"What's the most important insight you've gained about {topic}?",
            f"What questions about {topic} remain unanswered for you?",
            f"How might you apply what you've learned about {topic}?",
            f"What would you like to explore next regarding {topic}?"
        ]
    }
    
    # Get appropriate question set
    questions = question_templates.get(question_type.lower(), question_templates["exploring"])
    
    # If we have context, try to make the question more specific
    if context:
        # Select a question that seems most relevant
        import random
        base_question = random.choice(questions)
        
        # Add context-aware follow-up
        follow_up = f"\n\nConsidering what you shared: '{context[:100]}...', {base_question.lower()}"
        return follow_up
    
    # Return a selection of questions
    import random
    selected_questions = random.sample(questions, min(3, len(questions)))
    
    return "Here are some questions to explore:\n\n" + "\n\n".join(f"• {q}" for q in selected_questions)


@tool
def dialog_tracker_tool(user_id: str, action: str, data: str = None) -> str:
    """Track the state and progression of a Socratic dialog.
    
    Args:
        user_id: Unique identifier for the user
        action: Action to perform - add_topic, add_insight, get_summary, or reset
        data: Data related to the action (topic name, insight text, etc.)
    """
    state = _load_dialog_state(user_id)
    
    if action == "add_topic":
        if data and data not in state["topics"]:
            state["topics"].append(data)
            state["current_theme"] = data
            state["question_count"] += 1
            _save_dialog_state(user_id, state)
            return f"Topic '{data}' added to dialog. Total topics explored: {len(state['topics'])}"
    
    elif action == "add_insight":
        if data:
            insight_entry = {
                "theme": state.get("current_theme", "General"),
                "insight": data,
                "question_number": state["question_count"]
            }
            state["insights"].append(insight_entry)
            _save_dialog_state(user_id, state)
            return f"Insight recorded under theme '{insight_entry['theme']}'. Total insights: {len(state['insights'])}"
    
    elif action == "get_summary":
        if not state["topics"] and not state["insights"]:
            return "No dialog history found. Start by exploring a topic!"
        
        summary = ["**Socratic Dialog Summary**\n"]
        
        if state["topics"]:
            summary.append(f"**Topics Explored ({len(state['topics'])}):**")
            for topic in state["topics"]:
                summary.append(f"• {topic}")
        
        if state["insights"]:
            summary.append(f"\n**Key Insights ({len(state['insights'])}):**")
            for insight in state["insights"][-5:]:  # Show last 5 insights
                summary.append(f"• [{insight['theme']}] {insight['insight']}")
        
        summary.append(f"\n*Total questions explored: {state['question_count']}*")
        
        return "\n".join(summary)
    
    elif action == "reset":
        state = {
            "topics": [],
            "insights": [],
            "question_count": 0,
            "current_theme": None
        }
        _save_dialog_state(user_id, state)
        return "Dialog state reset. Ready for a fresh conversation!"
    
    else:
        return f"Unknown action '{action}'. Use: add_topic, add_insight, get_summary, or reset"


@tool
def insight_extractor_tool(conversation: str, focus: str = None) -> str:
    """Extract key insights and learning points from a conversation.
    
    Args:
        conversation: The text of the conversation to analyze
        focus: Optional specific aspect to focus on when extracting insights
    """
    # Simple heuristic-based extraction
    insights = []
    
    # Look for insight indicators
    insight_phrases = [
        "i realized", "i think", "it seems", "perhaps", "maybe",
        "i believe", "i understand", "now i see", "that means",
        "so basically", "in other words", "the key is", "importantly",
        "i learned", "this shows", "which suggests", "therefore"
    ]
    
    sentences = conversation.lower().split('.')
    
    for sentence in sentences:
        sentence = sentence.strip()
        if any(phrase in sentence for phrase in insight_phrases):
            # Clean up and capitalize
            clean_sentence = sentence.strip()
            if clean_sentence:
                # Capitalize first letter
                clean_sentence = clean_sentence[0].upper() + clean_sentence[1:] + "."
                insights.append(clean_sentence)
    
    # Also look for questions that reveal understanding
    question_insights = []
    questions = [s.strip() for s in conversation.split('?') if s.strip()]
    
    for question in questions[:3]:  # Limit to 3 questions
        if len(question) > 20:  # Meaningful questions
            question_insights.append(f"Question raised: {question.strip()}?")
    
    # Combine insights
    all_insights = insights[:5] + question_insights  # Limit total insights
    
    if not all_insights:
        return "No specific insights detected. Try exploring the topic more deeply through questioning."
    
    result = ["**Extracted Insights:**\n"]
    
    if focus:
        result.append(f"*Focus: {focus}*\n")
    
    for i, insight in enumerate(all_insights, 1):
        result.append(f"{i}. {insight}")
    
    result.append("\n*Tip: Continue exploring these insights with follow-up questions!*")
    
    return "\n".join(result)