# Solar Assistant Gauge Analysis

## Overview
Solar Assistant uses semi-circular gauges with animated gradients to display power metrics for Load, Solar PV, Grid, and Battery.

## HTML Structure
```html
<div class="gauge">
    <div class="mask">
        <div class="semi-circle [color]"></div>
        <div class="semi-circle--mask" style="transform: rotate([angle]deg)"></div>
    </div>
    <div class="value">[value] W</div>
    <div class="label">[label]</div>
</div>
```

## Gauge Rotation Formula
The gauge mask rotation is calculated based on the percentage of maximum value:
- **Formula**: `rotation = (value / max_value) * 180`
- **Range**: 0° to 180°
  - 0° = 0% (empty/minimum)
  - 90° = 50% (half)
  - 180° = 100% (full/maximum)

## Color Classes and Gradients

### Blue (Load)
```css
.gauge .semi-circle.blue {
    background: linear-gradient(-45deg, #00b7ff, #001aff, #6588e8, #0048ff);
    background-size: 400% 400%;
    animation: animated-gradient 5s ease infinite;
}
```

### Yellow (Solar PV)
```css
.gauge .semi-circle.yellow {
    background: linear-gradient(-120deg, #fff900, #ffb100, #ffe500, #ffe396);
    background-size: 400% 400%;
    animation: animated-gradient 10s ease infinite;
}
```

### Red (Grid)
```css
.gauge .semi-circle.red {
    background: linear-gradient(-75deg, #ffa200, red, #ff664d, red);
    background-size: 400% 400%;
    animation: animated-gradient 5s ease infinite;
}
```

### Green (Battery)
```css
.gauge .semi-circle.green {
    background: linear-gradient(120deg, #3bff29, #3e9e00, #00ff0f, #92ff7f);
    background-size: 400% 400%;
    animation: animated-gradient 3s ease infinite;
}
```

## Key CSS Properties

### Gauge Container
- Width: 11.5em
- Height: 5.75em (half of width for semi-circle)
- Position: relative
- Overflow: hidden on mask

### Semi-Circle
- Border-radius: 50% 50% 50% 50%/100% 100% 0 0 (creates half circle)
- Inner white circle created with :before pseudo-element
- Width: 8.5em (smaller than container)

### Mask Rotation
- Transform-origin: center center
- Transition: all 0.3s ease-in-out
- Initial background covers the colored semi-circle
- Rotation reveals the colored portion

### Animation
```css
@keyframes animated-gradient {
    0% { background-position: 0 50%; }
    50% { background-position: 100% 50%; }
    to { background-position: 0 50%; }
}
```

## Dashboard Layout
- Uses flexbox grid system
- Cards with sections for info and gauges
- Responsive design with media queries
- Half-width columns for 4 gauges

## Status Icons
- 80x80px images with gradient backgrounds
- Includes: Inverter, Solar PV, Grid, Battery status
- Links to detailed status pages

## Battery Change Indicator
- Shows charge/discharge rate in %/hr
- Positive values prefixed with "+"
- Negative values prefixed with "-"
- Color coded (green for positive, red for negative)

## Implementation Notes
1. The gauge uses a masking technique where a gray semi-circle rotates to reveal the colored gauge underneath
2. The rotation angle directly corresponds to the percentage value
3. Animated gradients provide visual interest without affecting the gauge reading
4. All measurements use em units for scalability
5. Z-index layering ensures proper element stacking