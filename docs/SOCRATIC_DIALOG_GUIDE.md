# Socratic Dialog Implementation Guide

## Overview

The Writer agent has been enhanced with Socratic dialog capabilities, allowing it to guide users through thoughtful exploration of ideas using the Socratic method. This implementation leverages DSPy for enhanced reasoning and maintains conversation state across interactions.

## Implementation Details

### 1. **Socratic Tools** (`src/tools/socratic_tools.py`)

Three core tools enable Socratic dialog functionality:

#### `question_generator_tool`
- Generates contextual questions based on dialog stage
- Supports four question types:
  - **Exploring**: Initial discovery questions
  - **Clarifying**: Questions to deepen understanding
  - **Challenging**: Questions that examine assumptions
  - **Reflecting**: Questions for synthesis and insight

#### `dialog_tracker_tool`
- Maintains conversation state per user
- Actions: `add_topic`, `add_insight`, `get_summary`, `reset`
- Stores dialog history in `data/socratic_dialogs.json`
- Tracks topics explored, insights gained, and question progression

#### `insight_extractor_tool`
- Analyzes conversations to identify key learnings
- Looks for insight indicators in user responses
- Extracts meaningful questions raised during dialog

### 2. **DSPy Socratic Module** (`src/agents/dspy_modules.py`)

The `SocraticModule` class provides intelligent dialog management:

- **Components**:
  - `theme_identifier`: Extracts core themes from user statements
  - `question_generator`: Creates contextual next questions
  - `insight_extractor`: Identifies key insights from conversation
  - `dialog_router`: Determines dialog progression and stages

- **Dialog Flow**:
  1. Identifies if request is for Socratic dialog
  2. Tracks conversation state and progression
  3. Generates appropriate questions based on stage
  4. Extracts and stores insights
  5. Provides summaries of exploration

### 3. **Writer Agent Integration**

The Writer agent now includes:
- Enhanced YAML configuration with Socratic prompts
- DSPy integration (`use_dspy: true`)
- WriterModule with embedded SocraticModule
- Dynamic tool loading for Socratic tools

## Usage Guide

### Starting a Socratic Dialog

Users can initiate Socratic dialog with phrases like:
- "Let's explore the concept of happiness"
- "Help me think about my career choices"
- "Guide me through understanding AI ethics"
- "I want to discuss the meaning of success"
- "Use Socratic method to explore leadership"

### Example Conversation Flow

```
User: @writer help me think about what makes a good leader

Writer: I'd be happy to explore 'leadership' with you through Socratic dialog! 🤔

Let's begin by understanding your perspective:

Here are some questions to explore:

• What do you think is the essence of leadership?
• How would you define leadership in your own words?
• What experiences have shaped your understanding of leadership?

*Please share your thoughts on any of these questions, and we'll dive deeper together.*

User: I think leadership is about inspiring others and making tough decisions

Writer: Interesting perspective! Let's explore further:

• When you say 'inspiring others', what specifically do you mean?
• Can you give me an example of inspiring others from your experience?
• What's the difference between inspiring others and something similar?

Considering what you shared: 'I think leadership is about inspiring others and making tough decisions...', what's the difference between inspiring others and something similar?

[Dialog continues through clarifying, challenging, and reflecting stages...]
```

### Dialog Stages

1. **Exploring Stage**
   - Initial questions to understand user's perspective
   - Open-ended questions about definitions and experiences
   - Establishes baseline understanding

2. **Clarifying Stage**
   - Requests specific examples
   - Explores distinctions and nuances
   - Identifies underlying assumptions

3. **Challenging Stage**
   - Examines evidence and counterarguments
   - Explores different contexts and perspectives
   - Tests the robustness of ideas

4. **Reflecting Stage**
   - Synthesizes insights gained
   - Identifies key learnings
   - Suggests practical applications

## Technical Architecture

### Request Flow

1. User mentions Writer with Socratic phrase
2. SpecialistAgent detects DSPy mode enabled
3. WriterDSPyAgent forwards to WriterModule
4. WriterModule checks for Socratic indicators
5. SocraticModule handles dialog management
6. Tools generate questions and track state
7. Response sent via Slack DM or channel

### State Management

Dialog state is maintained per user:
```json
{
  "user_id": {
    "topics": ["leadership", "ethics"],
    "insights": [
      {
        "theme": "leadership",
        "insight": "Leadership requires balancing empathy with decisiveness",
        "question_number": 5
      }
    ],
    "question_count": 8,
    "current_theme": "leadership"
  }
}
```

## Configuration

### Writer Agent YAML (`configs/agents/writer_agent.yaml`)

```yaml
name: "Writer"
description: "A specialist agent for creative writing, drafting, message composition, and Socratic dialog."
model_id: "claude-3-haiku-20240307"
use_dspy: true  # Enable DSPy for enhanced reasoning and Socratic dialog
system_prompt: |
  You are Writer, a helpful AI specialist with two core capabilities:
  
  1. **Creative Writing**: Crafting clear, concise, and creative text for any purpose.
  2. **Socratic Dialog**: Guiding users through thoughtful exploration of ideas using the Socratic method.
  ...
tools:
  - module: "src.tools.socratic_tools"
    functions:
      - "question_generator_tool"
      - "dialog_tracker_tool"
      - "insight_extractor_tool"
```

## Best Practices

1. **Natural Progression**: Allow conversation to flow naturally through stages
2. **Active Listening**: Extract insights from user responses
3. **Contextual Questions**: Use previous answers to inform next questions
4. **Non-Judgmental**: Focus on exploration, not evaluation
5. **User-Driven**: Let users guide the depth and direction

## Troubleshooting

### Common Issues

1. **Dialog Not Initiating**
   - Check if DSPy is enabled in writer_agent.yaml
   - Verify Socratic tools are properly loaded
   - Ensure request contains Socratic trigger phrases

2. **State Not Persisting**
   - Check data directory permissions
   - Verify socratic_dialogs.json is writable
   - Look for errors in dialog_tracker_tool logs

3. **Questions Not Contextual**
   - Ensure context is being passed to DSPy module
   - Check if user_id is properly extracted
   - Verify conversation history formatting

## Future Enhancements

1. **Multi-Modal Socratic Dialog**: Incorporate images and diagrams
2. **Topic Recommendation**: Suggest related areas to explore
3. **Learning Analytics**: Track user growth over time
4. **Custom Question Banks**: Domain-specific Socratic questions
5. **Group Socratic Sessions**: Facilitate group exploration

## Summary

The Socratic dialog implementation transforms the Writer agent into a thoughtful conversation partner that helps users explore ideas deeply. By combining DSPy's reasoning capabilities with structured dialog management, the system provides meaningful, contextual questioning that promotes self-discovery and insight.