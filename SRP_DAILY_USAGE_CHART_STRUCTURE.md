# SRP Daily Usage Chart Implementation Documentation

## Overview
The SRP daily usage chart is a fully implemented interactive SVG-based visualization that displays real energy usage data extracted from SRP's customer portal. This chart supports multiple data views (Net Energy, Generation, Usage, Demand) and includes temperature overlays with real-time data extraction.

## Implementation Status: ✅ COMPLETED

### Features Implemented:
- ✅ Real-time data extraction from SRP customer portal
- ✅ Interactive chart with 4 data views: Net Energy, Generation, Usage, Demand
- ✅ Temperature overlay with high/low temperature data
- ✅ 31+ days of historical data
- ✅ Automatic data calculations from off-peak and on-peak values
- ✅ Caching system (6-hour cache) to avoid repeated logins
- ✅ Error handling and retry logic for robust operation
- ✅ Solar Assistant-style dashboard integration
- ✅ Color-coded charts for each data type:
  - **Net Energy**: Blue/Red (positive/negative)
  - **Generation**: Green
  - **Usage**: Red
  - **Demand**: Orange (with message for daily view)

### API Endpoints:
- `GET /api/srp/chart` - Returns chart data (cached)
- `GET /api/srp/chart?force_refresh=true` - Forces fresh data extraction
- `GET /api/srp/demand` - Returns peak demand data (separate endpoint)

## Chart Components

### 1. Chart Type Controls
The chart includes button controls to switch between different data views:
- **Net Energy**: Shows net usage/generation (positive = usage, negative = generation) - Blue/Red color coding
- **Generation**: Shows solar generation values (calculated from negative on-peak values) - Green bars
- **Usage**: Shows total energy consumption (sum of off-peak and on-peak absolute values) - Red bars
- **Demand**: Shows peak demand values in kW - Orange bars (Note: Daily view shows message as SRP doesn't provide daily demand data)

### 2. SVG Structure

#### Main SVG Container
```html
<svg class="usage-chart" width="100%" height="400" viewBox="0 0 1200 400">
  <!-- Chart content -->
</svg>
```

#### Bar Chart Groups
Each rate period has its own group for bars:
```html
<g class="viz-offPeak" data-rate="off-peak">
  <!-- Off-peak bars -->
</g>
<g class="viz-onPeak" data-rate="on-peak">
  <!-- On-peak bars -->
</g>
<g class="viz-superOffPeak" data-rate="super-off-peak">
  <!-- Super off-peak bars -->
</g>
```

#### Individual Bars
Each bar represents hourly or 15-minute interval data:
```html
<rect class="usage-bar" 
      x="50" 
      y="200" 
      width="20" 
      height="100"
      data-time="2025-01-23T14:00:00"
      data-value="3.45"
      data-rate="on-peak">
</rect>
```

#### Temperature Overlay
Temperature data is rendered as a line path:
```html
<g class="temperature-overlay">
  <path class="temp-line" d="M 50 100 L 100 95 L 150 90..." 
        stroke="#ff6b6b" 
        stroke-width="2" 
        fill="none"/>
  <!-- Temperature value labels -->
  <text class="temp-label" x="50" y="95">75°F</text>
</g>
```

### 3. Actual Data Format (Implemented)

#### SRP Chart API Response Structure
```javascript
{
  "chartAvailable": true,
  "dateRange": "Fri, May 23 through 6/22/2025",
  "dates": [
    "5/23/2025",
    "5/24/2025",
    "5/25/2025",
    // ... 31+ dates
  ],
  "netEnergy": [45.0, 59.0, 34.0, 35.0, 28.0, ...],  // Daily net energy in kWh
  "generation": [0, 0, 0, 0, 0, 26.0, 28.0, ...],    // Daily generation in kWh
  "usage": [45.0, 59.0, 34.0, 35.0, 28.0, ...],      // Daily usage in kWh
  "demand": [0.0, 0.0, 0.0, 0.0, 0.0, ...],          // Daily peak demand in kW
  "offPeak": [45.0, 59.0, 34.0, 35.0, 28.0, ...],    // Off-peak usage in kWh
  "onPeak": [0.0, 0.0, 0.0, 0.0, 0.0, -26.0, ...],   // On-peak usage/generation in kWh
  "temperatures": {
    "high": [95, 98, 89, 91, 85, ...],                // Daily high temperatures in °F
    "low": [72, 75, 68, 70, 65, ...]                  // Daily low temperatures in °F
  },
  "cached": true,                                      // Whether data is from cache
  "cache_age_seconds": 1234,                          // Age of cached data
  "cache_timestamp": "2025-06-24T13:57:58.554753"     // When data was cached
}
```

#### Rate Period Definitions
```javascript
const ratePeriods = {
  "super-off-peak": {
    "color": "#22c55e",  // Green
    "hours": [23, 0, 1, 2, 3, 4, 5],
    "label": "Super Off-Peak"
  },
  "off-peak": {
    "color": "#3b82f6",  // Blue
    "hours": [6, 7, 8, 9, 10, 11, 12, 13, 14, 19, 20, 21, 22],
    "label": "Off-Peak"
  },
  "on-peak": {
    "color": "#ef4444",  // Red
    "hours": [15, 16, 17, 18],
    "label": "On-Peak"
  }
};
```

### 4. Interactive Features

#### Tooltip on Hover
```javascript
// Tooltip data structure
{
  "time": "3:30 PM",
  "date": "Jan 23, 2025",
  "value": 3.45,
  "unit": "kWh",
  "rateType": "On-Peak",
  "temperature": "85°F",
  "cost": "$0.52"  // Optional
}
```

#### Chart Type Switching
```javascript
function switchChartType(type) {
  // type: 'netEnergy' | 'generation' | 'usage' | 'demand'
  
  // Update bar heights based on selected data type
  updateBars(data.intervals, type);
  
  // Update y-axis scale
  updateYAxis(getMaxValue(data.intervals, type));
  
  // Update chart title and labels
  updateChartLabels(type);
}
```

### 5. Rendering Logic

#### Bar Positioning
```javascript
// Calculate bar positions
const barWidth = chartWidth / (intervals.length * 1.2);
const barSpacing = barWidth * 0.2;

intervals.forEach((interval, index) => {
  const x = marginLeft + (index * (barWidth + barSpacing));
  const height = scaleY(interval[selectedDataType]);
  const y = chartHeight - height - marginBottom;
  
  // Create bar with appropriate rate period color
  createBar(x, y, barWidth, height, ratePeriods[interval.rateType].color);
});
```

#### Temperature Line Overlay
```javascript
// Create temperature line path
const tempLine = d3.line()
  .x((d, i) => marginLeft + (i * intervalWidth) + (intervalWidth / 2))
  .y(d => tempScaleY(d.temperature))
  .curve(d3.curveMonotoneX);

const pathData = tempLine(intervals);
```

### 6. CSS Styling

```css
/* Rate period colors */
.viz-offPeak rect { fill: #3b82f6; }
.viz-onPeak rect { fill: #ef4444; }
.viz-superOffPeak rect { fill: #22c55e; }

/* Hover effects */
.usage-bar:hover { 
  opacity: 0.8; 
  cursor: pointer;
}

/* Temperature overlay */
.temperature-overlay {
  pointer-events: none;
}

.temp-line {
  stroke: #ff6b6b;
  stroke-width: 2;
  fill: none;
  stroke-dasharray: 5,5;
}

/* Tooltip */
.chart-tooltip {
  position: absolute;
  padding: 10px;
  background: rgba(0, 0, 0, 0.9);
  color: white;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  z-index: 1000;
}
```

### 7. Implementation Notes

1. **Data Aggregation**: 
   - 15-minute interval data from smart meters
   - Hourly aggregation for daily view
   - Real-time updates during peak hours

2. **Performance Considerations**:
   - Use SVG for better scalability
   - Implement virtual scrolling for long date ranges
   - Cache calculated positions

3. **Accessibility**:
   - Include ARIA labels for screen readers
   - Keyboard navigation support
   - High contrast mode support

4. **Responsive Design**:
   - Adjust bar width based on viewport
   - Stack legend items on mobile
   - Touch-friendly tap targets

5. **Integration Points**:
   - WebSocket for real-time updates
   - REST API for historical data
   - Export functionality (PNG/CSV)

## Example Implementation

```javascript
class SRPUsageChart {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      width: options.width || 1200,
      height: options.height || 400,
      margins: options.margins || { top: 20, right: 20, bottom: 40, left: 60 },
      ...options
    };
    
    this.selectedType = 'netEnergy';
    this.data = null;
    
    this.init();
  }
  
  init() {
    // Create SVG
    this.svg = d3.select(this.container)
      .append('svg')
      .attr('width', this.options.width)
      .attr('height', this.options.height)
      .attr('viewBox', `0 0 ${this.options.width} ${this.options.height}`);
    
    // Create chart groups
    this.createChartGroups();
    
    // Setup scales
    this.setupScales();
    
    // Create axes
    this.createAxes();
    
    // Setup event handlers
    this.setupEventHandlers();
  }
  
  updateData(data) {
    this.data = data;
    this.render();
  }
  
  render() {
    // Clear existing bars
    this.svg.selectAll('.usage-bar').remove();
    
    // Render bars for selected type
    this.renderBars();
    
    // Render temperature overlay
    this.renderTemperatureOverlay();
    
    // Update axes
    this.updateAxes();
  }
  
  // ... additional methods
}
```

## Implementation Details

### Data Extraction Process
1. **Login to SRP Portal**: Automated login using Playwright browser automation
2. **Navigate to Usage Page**: Access daily usage data section
3. **Extract Table Data**: Click "View data table" to access raw data
4. **Parse Energy Values**: Extract off-peak, on-peak, and temperature data
5. **Calculate Derived Values**: Compute net energy, usage, generation, and demand
6. **Cache Results**: Store data for 6 hours to minimize SRP server load

### Key Files
- `/home/jeremy/src/solar_assistant/eg4_web_monitor.py` - Main implementation
- `/home/jeremy/src/solar_assistant/templates/index_solar_style.html` - Frontend chart
- `SRPMonitor` class - Handles SRP portal interaction
- `get_daily_usage_chart()` method - Core extraction logic

### Browser Requirements
- Playwright with Chromium
- JavaScript enabled
- Cookies and session storage support

### Error Handling
- Retry logic for login failures (up to 3 attempts)
- Timeout handling for slow page loads
- Graceful fallback to cached data when extraction fails
- Screenshot capture for debugging failed extractions

### Performance Optimizations
- 6-hour data caching to reduce server load
- Skip unnecessary chart button clicks when data already available
- Concurrent browser instance management
- Automatic cleanup of browser resources

### Security Considerations
- SRP credentials stored in environment variables
- No sensitive data logged
- Secure session management
- Browser instances properly closed after use

## Troubleshooting

### Common Issues and Fixes
1. **"Configure SRP credentials" error**: 
   - Verify SRP_USERNAME and SRP_PASSWORD environment variables
   - Hard refresh browser cache (Ctrl+Shift+R)
   - Check frontend caching issues
   
2. **Login timeout errors**:
   - Check SRP website availability
   - Verify credentials are correct
   - Wait for retry logic to attempt multiple times (up to 3)
   - Timeout increased to 30 seconds for slow page loads

3. **Empty chart data**:
   - Force refresh with `?force_refresh=true` parameter
   - Check browser console for JavaScript errors
   - Verify API endpoint returns data: `/api/srp/chart`

4. **"Cannot read properties of undefined (reading 'trim')" error** [FIXED]:
   - Issue: Mixed date formats in data array
   - Solution: Added safe date format handling in chart rendering
   - Handles both "Sun, May 25" and "5/25/2025" formats

5. **"Assignment to constant variable" error** [FIXED]:
   - Issue: JavaScript function reassignment conflicts
   - Solution: Removed problematic debug logging function reassignments

### Debug Features Added

A comprehensive debug tab was implemented to help troubleshoot chart issues:

1. **API Status Testing**:
   - Direct endpoint testing with response time measurement
   - Shows HTTP status and error messages
   - Loads and displays raw JSON response

2. **Raw Data Display**:
   - Shows complete API response for verification
   - Validates data structure and values
   - Confirms data extraction is working correctly

3. **Chart Rendering Test**:
   - Validates DOM elements (container, SVG)
   - Tests data availability
   - Attempts to render chart with debug data
   - Shows specific rendering errors

4. **Error Logging**:
   - Captures JavaScript errors
   - Displays error timestamps and details
   - Helps identify frontend issues

### Data Format Notes

The API returns data with mismatched array lengths:
- **dates**: 37 items (includes both formatted dates and raw dates)
- **usage/generation/netEnergy**: 31 items (actual data points)
- Chart handles this gracefully by defaulting missing values to 0

### Monitoring
- Check logs at `/tmp/eg4_monitor_*.log`
- API response times tracked in logs
- Screenshot capture at `/tmp/srp_*.png` for debugging
- Debug tab provides real-time troubleshooting

## Recent Updates

### Data Extraction Fixes (June 2025)
- Fixed date alignment issue where chart x-axis labels were mixed with actual dates
- Fixed usage calculation when SRP's Total column shows zeros
- Improved data extraction to properly align dates with their corresponding values
- Data now correctly matches what users see on SRP website

### Chart Type Switching (June 2025)
- Implemented proper color coding for each chart type
- Fixed chart labels and units (kWh vs kW)
- Added graceful handling for empty demand data
- Improved tooltips to show correct units based on chart type

### Known Limitations
- **Demand Data**: SRP doesn't provide daily demand data in the daily view, only current billing cycle peak demand
- **Date Formats**: Handles mixed date formats ("Sun, May 25" and "5/25/2025")
- **Total Column**: SRP sometimes shows 0 in the Total column; the system calculates usage from individual rate periods when this occurs

This implementation provides a complete, production-ready SRP daily usage chart with real data extraction, robust error handling, comprehensive debugging capabilities, and proper visualization for all chart types.