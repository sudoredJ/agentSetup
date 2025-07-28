# Task Logging and Analytics System - Three Implementation Approaches

## Overview
We need a lightweight task logging system that tracks:
- Every task request (timestamp, user, original request text)
- Agent confidence evaluations
- Which agent was assigned
- Task outcome (success/failure)
- Execution time
- Export to CSV for analysis

## Quick Decision Summary
After deep analysis, **Approach 2 (SQLite)** is recommended for immediate implementation:
- Thread-safe with WAL mode
- ~200-300 lines of code
- Handles 10,000+ requests/day
- Built-in querying and CSV export
- No new dependencies
- Easy migration path from JSON if needed

## Approach 1: Minimal JSON Log File

### Concept
Add lightweight logging to existing code with minimal changes. Append JSON lines to a log file that can be easily converted to CSV.

### Implementation Points
- Add to `main.py` orchestrator's `handle_orchestrator_mention()`
- Add to `check_and_assign()` for confidence tracking
- Add to `specialist_agent.py` `process_assignment()` for outcomes
- Use Python's built-in `json` and `csv` modules

### Pros
- Minimal code changes (~50 lines total)
- No new dependencies
- Easy to implement immediately
- Can be added without breaking anything

### Cons
- Not real-time queryable
- Manual CSV export needed
- No built-in analytics

### Code Sketch
```python
# In main.py
import json
from datetime import datetime

def log_task(event_type, data):
    """Append task event to log file"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        **data
    }
    with open("task_logs.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")

# In handle_orchestrator_mention:
log_task("task_request", {
    "user_id": user_id,
    "request": text,
    "channel_id": channel_id,
    "thread_ts": thread_ts
})

# In check_and_assign after evaluations:
log_task("evaluations", {
    "thread_ts": thread_ts,
    "evaluations": evaluations,
    "assigned_to": agent_name if evaluations else None,
    "max_confidence": confidence if evaluations else 0
})

# In specialist_agent.py process_assignment completion:
log_task("task_complete", {
    "thread_ts": thread_ts,
    "agent": self.name,
    "success": True,
    "execution_time": time.time() - start_time
})
```

## Approach 2: SQLite Database

### Concept
Use SQLite for structured storage with easy querying and built-in CSV export capabilities.

### Implementation Points
- Create `src/core/task_logger.py` module
- SQLite database with tables: tasks, evaluations, outcomes
- Add hooks to existing code
- Include utility functions for CSV export

### Pros
- Structured data with relationships
- Easy querying and filtering
- Built-in to Python (no deps)
- Can generate reports on demand
- Thread-safe

### Cons
- Slightly more complex setup
- Need schema migrations for changes
- More code than JSON approach

### Code Sketch
```python
# src/core/task_logger.py
import sqlite3
from contextlib import contextmanager

class TaskLogger:
    def __init__(self, db_path="task_logs.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with self.get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    request TEXT,
                    channel_id TEXT,
                    thread_ts TEXT UNIQUE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    task_id INTEGER,
                    agent_name TEXT,
                    confidence INTEGER,
                    assigned BOOLEAN,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS outcomes (
                    task_id INTEGER,
                    agent_name TEXT,
                    success BOOLEAN,
                    execution_time REAL,
                    error_message TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            """)
    
    @contextmanager
    def get_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def log_task(self, user_id, request, channel_id, thread_ts):
        with self.get_db() as conn:
            conn.execute(
                "INSERT INTO tasks (user_id, request, channel_id, thread_ts) VALUES (?, ?, ?, ?)",
                (user_id, request, channel_id, thread_ts)
            )
    
    def export_to_csv(self, output_file="task_report.csv"):
        # Export with pandas or csv module
        pass

# Initialize in main.py
task_logger = TaskLogger()
```

## Approach 3: Event Stream with Metrics Collector

### Concept
Create an event-driven system that collects metrics in memory and periodically flushes to disk. Includes real-time statistics.

### Implementation Points
- Event emitter pattern in `src/core/event_logger.py`
- Metrics aggregator with time windows
- Background thread for periodic CSV dumps
- Real-time stats available via new tool

### Pros
- Real-time metrics
- Low latency
- Can add Slack commands for stats
- Extensible for future analytics
- Could integrate with monitoring tools

### Cons
- Most complex implementation
- Memory usage for buffering
- Need careful thread synchronization

### Code Sketch
```python
# src/core/event_logger.py
from collections import defaultdict, deque
from dataclasses import dataclass
import threading
import csv

@dataclass
class TaskEvent:
    timestamp: float
    event_type: str
    thread_ts: str
    data: dict

class MetricsCollector:
    def __init__(self, flush_interval=300):  # 5 minutes
        self.events = deque(maxlen=10000)
        self.stats = defaultdict(lambda: {"total": 0, "success": 0})
        self.lock = threading.Lock()
        self._start_flush_thread(flush_interval)
    
    def emit(self, event_type, thread_ts, **data):
        with self.lock:
            event = TaskEvent(
                timestamp=time.time(),
                event_type=event_type,
                thread_ts=thread_ts,
                data=data
            )
            self.events.append(event)
            self._update_stats(event)
    
    def get_stats(self, agent_name=None):
        with self.lock:
            if agent_name:
                return dict(self.stats[agent_name])
            return {k: dict(v) for k, v in self.stats.items()}
    
    def _flush_to_csv(self):
        # Periodically write buffered events to CSV
        pass

# Global metrics instance
metrics = MetricsCollector()

# In code:
metrics.emit("task_request", thread_ts, user_id=user_id, request=text)
metrics.emit("task_assigned", thread_ts, agent=agent_name, confidence=confidence)
metrics.emit("task_complete", thread_ts, agent=self.name, success=True)
```

## Recommendation

**For immediate implementation: Approach 1 (JSON Log)**
- Can be added today with ~50 lines of code
- Zero risk to existing functionality
- Easy to convert to CSV with a simple script

**For long-term: Approach 2 (SQLite)**
- Best balance of features and simplicity
- Can migrate from JSON logs
- Supports complex queries and reports
- Standard Python library

**For future scaling: Approach 3 (Event Stream)**
- When you need real-time dashboards
- When you want to add monitoring/alerting
- When you have high task volume

## Migration Path
1. Start with JSON logging (Approach 1)
2. After 1-2 weeks, write migration script to SQLite (Approach 2)
3. Keep JSON logging as backup
4. Eventually add event streaming for real-time needs

## CSV Export Format
Regardless of approach, the CSV should include:
```csv
timestamp,user_id,request,assigned_agent,confidence,other_agents_confidence,success,execution_time,error_message
2024-01-15T10:30:00Z,U123456,"Research quantum computing",Grok,92,"Writer:30;Builder:15",true,45.2,
2024-01-15T10:31:00Z,U789012,"Write a poem",Writer,95,"Grok:20",true,23.1,
2024-01-15T10:32:00Z,U345678,"Unknown request",,,,,false,0,"No agent confident enough"
```