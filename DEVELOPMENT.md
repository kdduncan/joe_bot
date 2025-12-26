# Development Guide

## Local Testing (No Discord Needed!)

You can test the bot **locally** without setting up Discord.

### Interactive Testing
```bash
python test_interactive.py
```

Choose mode:
- **Mode 1**: Interactive (type queries one by one)
- **Mode 2**: Test Mode (runs predefined tests)
- **Mode 3**: Single Query (test one and exit)

### Quick Verification
```bash
python verify.py
```

Runs automated checks with no interaction needed.

### What You Can Test Locally
✅ Database connection  
✅ Query parsing (pattern matching + agent mode)  
✅ Statistics generation  
✅ All query types (count, list, stats, help)  
✅ Chart generation (if agent mode enabled)  

## Data Management

### Database Source
The bot uses `jobs.db` (SQLite) containing all job postings.
The source data comes from Excel files in the `joe_data/` directory.

### Updating Data
If you add new Excel files to `joe_data/`:
```bash
python migrate_data.py
```

This rebuilds `jobs.db` from all `.xlsx` files in the directory.

## Field Support

All data from the database is accessible and filterable!

## Troubleshooting

### Agent Mode Not Working

**Check configuration**:
```bash
# In .env
USE_AGENT_MODE=true
OPENROUTER_API_KEY=your_key_here
AGENT_MODEL=qwen/qwen-2.5-72b-instruct
```

**Model issues** (404 errors):
- Model may not be available
- Try alternatives: `openai/gpt-4o-mini`, `google/gemini-flash-1.5:free`
- Check https://openrouter.ai/models for current models

**Rate limits**:
- Free tier has limits
- Disable temporarily: `USE_AGENT_MODE=false`
- Bot falls back to pattern matching automatically

### Pattern Matching Fallback

If agent mode fails, the bot automatically uses pattern matching:
```
Agent mode → Pattern matching → Always works!
```

No action needed - the fallback is automatic.

## Development Workflow

1. **Test Locally First**
   ```bash
   python test_interactive.py
   ```

2. **Verify Everything Works**
   ```bash
   python verify.py
   ```

3. **Deploy to Discord**
   ```bash
   python main.py
   ```

## Testing Examples

Try these queries in interactive mode:

**Counts**:
- "how many jobs in 2024"
- "jobs in Massachusetts"
- "economics positions"

**Trends** (Agent mode):
- "show me a graph of jobs by year"
- "create a chart comparing states"

**Lists**:
- "list jobs at Harvard"
- "show positions in California"

**Statistics**:
- "stats by country"
- "breakdown by year"

## Files Overview

**Core Code**:
- `main.py` - Entry point
- `data_loader.py` - Database handler
- `query_engine.py` - Query processing
- `discord_bot.py` - Discord integration

**Agent Architecture**:
- `agent_orchestrator.py` - Coordinates agents
- `summary_agent.py` - Conversational AI
- `fetcher_agent.py` - Data retrieval
- `visualization_agent.py` - Chart generation

**Utilities**:
- `migrate_data.py` - Data migration tool
- `verify.py` - Verification script
- `test_interactive.py` - Local testing
- `test_interactive.py` - Local testing

**Configuration**:
- `config.py` - Configuration loader
- `.env` - Your settings (not in git)
- `.env.example` - Template

## Chart Generation

Charts are created temporarily:
- Saved to system temp directory
- Attached to Discord/output
- Auto-deleted after use
- No permanent storage

Supports: bar charts, line charts, pie charts, comparison charts

## Tips

- **Start local**: Test without Discord first
- **Pattern matching**: Works without any API keys
- **Agent mode**: Requires OpenRouter API key
- **Charts**: Only in agent mode
- **Fallback**: Always works even if agents fail

Happy developing! 🚀
