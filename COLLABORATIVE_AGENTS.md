# Collaborative Agent Discussion System

## Overview
Implemented a DSPy-powered collaborative discussion system where agents negotiate task assignments through multi-round discussions until one reaches 50% confidence.

## Key Changes

### 1. Negotiation Module (`src/agents/negotiation_module.py`)
- **CollaborativeEvaluator**: DSPy module that allows agents to adjust confidence based on other agents' evaluations
- **AgentDiscussionCoordinator**: Facilitates multi-round discussions between agents
- Uses DSPy ChainOfThought for reasoning about task assignments
- Maximum 3 rounds of discussion with 1-second pauses
- Target confidence: 50%

### 2. Specialist Agent Updates (`src/agents/specialist_agent.py`)
- Added `collaborative_evaluate()` method that uses DSPy to consider other agents' input
- Falls back to base evaluation if DSPy is unavailable
- Applies confidence adjustments based on negotiation results

### 3. Assignment Logic Updates (`src/orchestrator/assignment.py`)
- If max initial confidence < 50%, triggers collaborative discussion
- Reduced timeout from 15s to 8s for faster response
- Reduced check interval from 0.5s to 0.3s
- Falls back to regular assignment if discussion fails

## How It Works

1. Orchestrator receives a request and asks all agents to evaluate
2. If highest confidence < 50%, collaborative discussion begins
3. Agents share their evaluations and reasoning in Slack thread
4. Each agent can adjust confidence based on others' input using DSPy
5. Process continues up to 3 rounds or until someone reaches 50%
6. Final assignment made to highest confidence agent

## Example Flow
```
User: "help me think about consciousness"
Grok: 20% (I focus on research, not Socratic dialog)
Writer: 40% (I can handle Socratic dialog)
-- Round 2 --
Writer: 55% (Other agents agree this is my specialty)
ASSIGNED: Writer
```

## Benefits
- Prevents low-confidence assignments
- Allows agents to negotiate and reach consensus
- Leverages DSPy for intelligent reasoning
- Maintains fast response times