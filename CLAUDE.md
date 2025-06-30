# CLAUDE.md - Project Context for Claude Code

## Project Overview
Solar Assistant is a comprehensive solar monitoring system for EG4 inverters with multiple deployment options and advanced features.

## Key Components
1. **EG4 Web Monitor** (`eg4_web_monitor.py`) - Main Flask app with real-time monitoring
2. **Service Monitor** (`service_monitor.py`) - Auto-recovery system for containers
3. **Docker Implementation** - Full containerized deployment
4. **SRP Integration** - Salt River Project utility data integration

## Common Commands
- **Run Web Monitor**: `docker-compose -f docker-compose.eg4.yml up -d`
- **View Logs**: `docker-compose -f docker-compose.eg4.yml logs -f eg4_web_monitor`
- **Restart Container**: `docker-compose -f docker-compose.eg4.yml restart eg4_web_monitor`
- **Run Tests**: `pytest tests/` (if tests directory exists)
- **Check Linting**: `flake8 *.py` or `pylint *.py`
- **Type Check**: `mypy *.py` (if configured)

## Recent Issues & Solutions
1. **Browser Crashes in Container**:
   - Solution: Added `--single-process` flag and increased shm_size to 2GB
   - Key args: `--no-sandbox`, `--disable-setuid-sandbox`, `--disable-dev-shm-usage`

2. **Configuration Tab Frozen**:
   - Cause: Duplicate JavaScript `switchTab` functions
   - Solution: Removed duplicates in `templates/index_solar_style.html`

3. **SRP Data Not Showing**:
   - Issue: Navigation flow broken after login detection
   - Solution: Ensure `navigate_to_usage()` and `extract_usage_data()` run after login

## Architecture Notes
- Uses Flask + SocketIO for real-time updates
- Playwright for browser automation (EG4 cloud and SRP scraping)
- SQLite for data persistence
- Docker for containerization
- Multi-threaded monitoring with asyncio

## Environment Variables (.env)
```
EG4_USERNAME=your_eg4_username
EG4_PASSWORD=your_eg4_password
SRP_USERNAME=your_srp_username
SRP_PASSWORD=your_srp_password
```

## Key Features
- Real-time monitoring via WebSocket
- Multi-inverter support
- Data export (CSV/JSON/Excel)
- MQTT integration
- Alert system
- Service auto-recovery
- SRP utility integration (off-peak/on-peak visualization)

## Development Notes
- Always check browser stability flags when modifying Playwright code
- Use 60-second polling intervals for monitoring
- SRP chart uses blue for off-peak, red for on-peak
- Cross-origin access supported (e.g., 172.16.105.5 → 172.16.106.10:8282)

## Testing & Debugging
- Debug templates available but should not be committed
- Use `/debug` endpoint for troubleshooting
- Check container logs for browser crashes
- Service monitor logs to `service_monitor.log`

## Git Workflow
- Main branch: `main`
- Always run linting before commits
- Clean up test/debug files before pushing
- Update documentation when adding features