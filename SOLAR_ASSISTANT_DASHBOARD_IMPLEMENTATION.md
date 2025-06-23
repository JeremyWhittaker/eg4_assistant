# Solar Assistant Dashboard Implementation

## Overview
This document describes the implementation of a Solar Assistant-style dashboard for EG4 inverter monitoring, including integration with Salt River Project (SRP) for peak demand tracking.

## Features

### 1. Solar Assistant Style Gauges
- Semi-circular CSS-based gauges that replicate Solar Assistant's visual style
- Real-time animations with smooth transitions
- Dark theme matching Solar Assistant's design
- Responsive layout for mobile and desktop

### 2. Real-time Monitoring
- WebSocket connection for live data updates
- 5-second refresh interval
- Battery, Solar PV, Grid, and Load monitoring
- System status and daily statistics

### 3. Configuration Management
- EG4 cloud credentials storage
- SRP account integration
- Alert configuration for battery SOC, peak demand, and connectivity

### 4. SRP Peak Demand Integration
- Automated login to SRP account
- Peak demand data extraction
- Billing cycle information display

## Configuration

### Solar Assistant IP Address
The current Solar Assistant instance is located at:
- **IP Address**: 172.16.109.214
- **Port**: 80 (HTTP)

### Environment Variables
Create a `.env` file with the following:
```
EG4_MONITOR_USERNAME=your_eg4_username
EG4_MONITOR_PASSWORD=your_eg4_password
SRP_USERNAME=your_srp_username
SRP_PASSWORD=your_srp_password
```

#### Credential Persistence
- Credentials entered in the web interface are automatically saved to the `.env` file
- On startup, the application loads and verifies saved credentials
- Usernames are displayed in the configuration form for easy reference
- Passwords are securely hidden with dots in the interface
- To switch accounts, simply enter new credentials and click save

### Running the Monitor
```bash
python eg4_web_monitor.py
```
Access the dashboard at: http://localhost:8282

## Technical Implementation

### Gauge Design
The gauges use CSS masks and transforms to create the semi-circular appearance:
```css
.gauge {
    width: 12em;
    height: 7.5em;
    position: relative;
    overflow: hidden;
}

.gauge .semi-circle--mask {
    position: absolute;
    top: 0;
    left: 0;
    width: 11.5em;
    height: 11.5em;
    background: #0f172a;
    border-radius: 50%;
    transform: rotate(calc(var(--rotation) * 1deg));
}
```

### Data Flow
1. **EG4 Cloud Scraping**: Playwright browser automation logs into monitor.eg4electronics.com
2. **Data Extraction**: CSS selectors extract real-time values
3. **WebSocket Broadcasting**: Flask-SocketIO pushes updates to connected clients
4. **Gauge Updates**: JavaScript calculates rotation angles and updates displays

### SRP Integration
The SRP integration uses Playwright to:
1. Navigate to https://myaccount.srpnet.com/power
2. Login with stored credentials (automatically loaded from .env)
3. Navigate to the usage page at https://myaccount.srpnet.com/power/myaccount/usage
4. Extract peak demand data from the `.srp-red-text strong` element
5. Return formatted JSON with demand value and billing cycle

#### Important Notes:
- Credentials are saved without quotes to the `.env` file
- On startup, credentials are automatically loaded and verified
- The system navigates to the usage page specifically to get accurate peak demand data
- No re-login is required after container restarts

## File Structure
```
solar_assistant/
├── eg4_web_monitor.py          # Main Flask application
├── templates/
│   └── index_solar_style.html  # Solar Assistant style dashboard
├── solar_assistant_styles.css  # Extracted Solar Assistant styles
└── .env                        # Configuration (not in repo)
```

## Troubleshooting

### SRP Login Issues
If SRP login fails:
1. Verify credentials in `.env` file (should NOT have quotes around values)
2. Check if SRP website has changed by running `python find_srp_login.py`
3. Ensure Playwright and Chromium are properly installed
4. The login URL is `https://myaccount.srpnet.com/power`
5. Peak demand data is on the usage page: `https://myaccount.srpnet.com/power/myaccount/usage`

### Common Issues Fixed
1. **Quotes in .env file**: The system now saves credentials without quotes
2. **Wrong peak demand value**: Fixed by navigating to the usage page instead of dashboard
3. **Login button not clickable**: Fixed by using Enter key to submit form
4. **Credentials not persisting**: Fixed by properly writing to .env file without quotes

### Gauge Display Issues
If gauges appear broken:
1. Check browser console for JavaScript errors
2. Verify WebSocket connection is established
3. Ensure CSS files are loaded correctly

### Data Not Updating
If real-time data stops:
1. Check if EG4 cloud session expired
2. Verify network connectivity
3. Restart the monitor service

## Future Enhancements
1. Historical data graphing
2. Export functionality
3. Mobile app integration
4. Additional utility provider integrations
5. Energy usage predictions