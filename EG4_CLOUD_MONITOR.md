# EG4 Cloud Monitor

This module provides tools to retrieve live statistics from the EG4 cloud monitoring platform at monitor.eg4electronics.com.

## Overview

The EG4 cloud monitor uses JavaScript to dynamically load data, requiring browser automation to access the values. We use Playwright to automate a headless browser that logs in and extracts live inverter data.

## Setup

1. Install required dependencies:
```bash
pip install playwright python-dotenv
playwright install chromium
```

2. Configure your credentials in `.env`:
```
EG4_MONITOR_USERNAME=your_username
EG4_MONITOR_PASSWORD=your_password
```

## Available Scripts

### 1. Simple Battery SOC Monitor (`eg4_soc_monitor.py`)
Focused monitor that displays only battery State of Charge with a visual progress bar.

```bash
python3 eg4_soc_monitor.py
```

Output example:
```
[14:23:45] Battery: [████████████████████] 99%
[14:24:15] Battery: [████████████████████] 98%
```

### 2. Full Live Monitor (`eg4_cloud_live.py`)
Attempts to retrieve all available statistics including battery SOC, power values, and voltages.

```bash
python3 eg4_cloud_live.py
```

### 3. Other Utilities

- `eg4_playwright_monitor.py` - Interactive version with single/continuous mode options
- `eg4_cloud_monitor.py` - Initial attempt using requests/BeautifulSoup (requires JS)
- `eg4_cloud_selenium.py` - Alternative using Selenium WebDriver
- `eg4_api_direct.py` - API endpoint discovery tool

## Technical Details

### How It Works

1. **Authentication**: Logs into the EG4 cloud portal using provided credentials
2. **Navigation**: Navigates to the inverter monitor page
3. **Data Extraction**: Uses JavaScript evaluation to extract values from DOM elements
4. **Continuous Monitoring**: Polls for updates every 30 seconds

### Key Elements Targeted

- Battery SOC: `.socText` or `.socHolder` containing percentage
- Other values: Elements with classes containing "monitor", "data", or "value"

### Limitations

- Requires active internet connection
- Depends on EG4's cloud service availability
- Page structure changes may break the scrapers
- Only retrieves data visible in the web interface

## Troubleshooting

1. **Login Fails**: Verify credentials in `.env` file
2. **No Data Retrieved**: EG4 may have changed their page structure
3. **Browser Errors**: Ensure Playwright and Chromium are properly installed
4. **Timeout Errors**: Check internet connection and EG4 service status

## Alternative: Direct Inverter Connection

For local network access without cloud dependency, see the direct inverter monitoring scripts that connect to the EG4 dongle at port 8000.