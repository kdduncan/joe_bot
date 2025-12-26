# Multi-Agent Mode - Quick Start

## ✅ Agent Mode is Now Default!

The bot now uses an intelligent multi-agent architecture by default.

## Architecture

```
User Query → Summary Agent (Plans) → Fetcher Agent (Executes) → Summary Agent (Interprets) → Response
```

### Two Agents:

1. **Summary Agent** (Conversational AI)
   - Understands your query
   - Calls Fetcher Agent as a tool
   - Interprets results with context
   - Generates natural language summaries
   - Model: `qwen/qwen-2.5-72b-instruct`

2. **Fetcher Agent** (Python code)
   - Executes database queries
   - Filters and aggregates data
   - Returns structured results
   - 100% deterministic

## Example Interaction

**You**: "How's the Massachusetts job market compared to last year?"

**Summary Agent** (internal):
- Plans: Need to compare MA jobs 2023 vs 2024
- Calls: `fetch_job_data(filters={state: "massachusetts", compare_by: "year", compare_values: ["2023", "2024"]}, fetch_type="compare")`

**Fetcher Agent** (internal):
- Returns: `{2023: 110 jobs, 2024: 127 jobs}`

**Summary Agent** (to you):
> "Massachusetts shows strong growth with 127 postings in 2024, up 15.5% from 110 in 2023. This suggests expanding academic opportunities in the state."

## Configuration

### Default (Agent Mode ON)
Your `.env`:
```bash
USE_AGENT_MODE=true
AGENT_MODEL=qwen/qwen-2.5-72b-instruct
OPENROUTER_API_KEY=your_key_here
```

### Disable Agent Mode (Use Simple Mode)
```bash
USE_AGENT_MODE=false
```

## Testing

### Local Test
```bash
python test_interactive.py
```

Try:
```
Query: How many jobs in Massachusetts compared to California?
Query: What's the trend for economics positions over the years?
Query: Tell me about job market in 2024
```

### Expected Behavior

**Agent Mode ON**:
- Natural language responses
- Contextual insights
- Comparisons and trends
- ~2-5 second response time

**Agent Mode OFF**:
- Template-based responses
- Just the numbers
- No insights
- <10ms response time

## Models

### Current: qwen/qwen-2.5-72b-instruct
- Good balance of speed and intelligence
- Strong reasoning capabilities
- Open source

### Alternatives

**Faster**:
```bash
AGENT_MODEL=openai/gpt-4o-mini  # Very fast, good quality
```

**Smarter**:
```bash
AGENT_MODEL=anthropic/claude-3.5-sonnet  # Best reasoning (paid)
```

**Free**:
```bash
AGENT_MODEL=google/gemini-flash-1.5-8b:free  # Free tier
```

## Troubleshooting

### "Agent mode is disabled"
- Check: `USE_AGENT_MODE=true` in `.env`
- Check: `OPENROUTER_API_KEY` is set
- Run: `python verify.py` to see logs

### Agent responses seem slow
- Try faster model: `gpt-4o-mini`
- Or disable: `USE_AGENT_MODE=false`

### Prefer simple mode
```bash
USE_AGENT_MODE=false
```
Bot will use pattern matching (instant responses, no AI).

## Fallback Behavior

If agent mode fails, the bot automatically falls back to:
1. LLM query parsing (if enabled)
2. Pattern matching (always works)

You'll never get an error - just different response styles!

## Files Created

- `summary_agent.py` - Conversational AI agent
- `fetcher_agent.py` - Data retrieval tool
- `agent_orchestrator.py` - Coordinates both agents
- `query_engine.py` - Updated with agent integration

## Security

✅ Still 100% read-only
- Agent only calls Fetcher as a tool
- Fetcher only reads database
- No write operations anywhere
- AI only generates text, never executes code

## Next Steps

1. Get OpenRouter API key: https://openrouter.ai/keys
2. Add to `.env`: `OPENROUTER_API_KEY=your_key`
3. Test: `python test_interactive.py`
4. Deploy to Discord and enjoy intelligent responses! 🚀

## Troubleshooting

### Agent Mode Not Working
**Check**: `USE_AGENT_MODE=true` and `OPENROUTER_API_KEY` is set in `.env`

**Model errors (404)**:
- Model may not be available
- Try `openai/gpt-4o-mini` or `google/gemini-flash-1.5:free`
- Check https://openrouter.ai/models for current models

### Rate Limits
- Free tier has limits
- Disable temporarily: `USE_AGENT_MODE=false`
- Bot automatically falls back to pattern matching

### Prefer Simple Mode
Set `USE_AGENT_MODE=false` for instant pattern-matching responses (no AI).

## Chart Generation

The Visualization Agent creates temporary charts:

**Chart Types**:
- Bar charts (comparisons)
- Line charts (trends)
- Pie charts (distributions)
- Comparison charts (multi-series)

**How to Use**:
```
"Show me a graph of jobs by year"
"Create a chart comparing states"
"Visualize the trend in economics"
```

**In Discord**:
- Charts are created temporarily
- Attached inline to messages
- Auto-deleted after sending
- No permanent storage

The agent automatically decides when visualizations would help explain the data.

## Comparison: Agent vs Pattern

| Feature | Agent Mode | Pattern Matching |
|---------|-----------|------------------|
| Query Understanding | AI-powered | Regex/keywords |
| Responses | Natural language | Templates |
| Insights | Yes | No |
| Charts | Yes | No |
| Speed | ~2-5s | <10ms |
| Cost | ~$0.001/query | Free |
| Reliability | Fallback to pattern | Always works |

**Recommendation**: Use agent mode for the best user experience!
