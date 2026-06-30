"""
Enhanced Timeline Map with Date and Hour Selection
- Date dropdown (select specific date)
- Day of week dropdown (Monday-Sunday)
- Hour slider (00:00-23:00)
- All synchronized
"""

import pandas as pd
import json
from datetime import datetime

def create_timeline_with_date_selector(merged_df, output_file='traffic_speed_timeline_with_date.html'):
    """
    Create map with date selector AND hour timeline slider
    """

    # Prepare data
    df = merged_df.copy()

    if not pd.api.types.is_datetime64_any_dtype(df['Timestamp']):
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')

    # Extract date components
    df['Hour'] = df['Timestamp'].dt.hour
    df['Date'] = df['Timestamp'].dt.date
    df['DayOfWeek'] = df['Timestamp'].dt.day_name()  # Monday, Tuesday, etc.
    df['DayOfWeekNum'] = df['Timestamp'].dt.dayofweek  # 0=Monday, 6=Sunday

    # Filter valid data
    speed_geo_df = df[
        (df['Avg_Speed'].notna()) &
        (df['Avg_Speed'] > 0) &
        (df['Latitude'].notna()) &
        (df['Longitude'].notna()) &
        (df['Hour'].notna()) &
        (df['Date'].notna())
    ].copy()

    speed_geo_df['Latitude'] = pd.to_numeric(speed_geo_df['Latitude'], errors='coerce')
    speed_geo_df['Longitude'] = pd.to_numeric(speed_geo_df['Longitude'], errors='coerce')
    speed_geo_df = speed_geo_df.dropna(subset=['Latitude', 'Longitude'])
    speed_geo_df = speed_geo_df[(speed_geo_df['Latitude'] != 0) & (speed_geo_df['Longitude'] != 0)]

    print(f"✓ Processing {len(speed_geo_df):,} records")

    # Get unique dates and days
    unique_dates = sorted(speed_geo_df['Date'].unique())
    date_to_str = {d: d.strftime('%Y-%m-%d') for d in unique_dates}

    print(f"✓ Date range: {unique_dates[0]} to {unique_dates[-1]}")
    print(f"✓ Total days: {len(unique_dates)}")

    # Aggregate by date, day of week, hour, and station
    hourly_data = speed_geo_df.groupby(['Date', 'DayOfWeek', 'Hour', 'Station']).agg({
        'Latitude': 'first',
        'Longitude': 'first',
        'Avg_Speed': 'mean',
        'Total_Flow': 'mean',
        'Avg_Occupancy': 'mean',
        'Name': 'first',
        'Fwy': 'first'
    }).reset_index()

    # Get station info
    stations = speed_geo_df.groupby('Station').agg({
        'Latitude': 'first',
        'Longitude': 'first'
    }).reset_index()

    print(f"✓ Found {len(stations)} stations")

    center_lat = stations['Latitude'].mean()
    center_lon = stations['Longitude'].mean()

    # Create nested data structure: {date: {day_of_week: {hour: {station_id: data}}}}
    data_dict = {}

    for _, row in hourly_data.iterrows():
        date_str = row['Date'].strftime('%Y-%m-%d')
        day = row['DayOfWeek']
        hour = int(row['Hour'])
        station_id = str(row['Station'])

        if date_str not in data_dict:
            data_dict[date_str] = {'day_name': day, 'hours': {}}
        if hour not in data_dict[date_str]['hours']:
            data_dict[date_str]['hours'][hour] = {}

        data_dict[date_str]['hours'][hour][station_id] = {
            'lat': float(row['Latitude']),
            'lon': float(row['Longitude']),
            'speed': float(row['Avg_Speed']),
            'flow': float(row['Total_Flow']) if pd.notna(row['Total_Flow']) else 0,
            'occupancy': float(row['Avg_Occupancy']) if pd.notna(row['Avg_Occupancy']) else 0,
            'name': str(row['Name']) if pd.notna(row['Name']) else 'N/A',
            'highway': str(row['Fwy']) if pd.notna(row['Fwy']) else 'N/A'
        }

    # Create day of week aggregation (average across all dates for each day)
    dow_data = {}
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    for day_name in day_names:
        dow_data[day_name] = {'hours': {}}
        day_df = hourly_data[hourly_data['DayOfWeek'] == day_name]

        if len(day_df) > 0:
            for hour in range(24):
                dow_data[day_name]['hours'][hour] = {}
                hour_day_df = day_df[day_df['Hour'] == hour]

                station_avg = hour_day_df.groupby('Station').agg({
                    'Latitude': 'first',
                    'Longitude': 'first',
                    'Avg_Speed': 'mean',
                    'Total_Flow': 'mean',
                    'Avg_Occupancy': 'mean',
                    'Name': 'first',
                    'Fwy': 'first'
                }).reset_index()

                for _, row in station_avg.iterrows():
                    station_id = str(row['Station'])
                    dow_data[day_name]['hours'][hour][station_id] = {
                        'lat': float(row['Latitude']),
                        'lon': float(row['Longitude']),
                        'speed': float(row['Avg_Speed']),
                        'flow': float(row['Total_Flow']) if pd.notna(row['Total_Flow']) else 0,
                        'occupancy': float(row['Avg_Occupancy']) if pd.notna(row['Avg_Occupancy']) else 0,
                        'name': str(row['Name']) if pd.notna(row['Name']) else 'N/A',
                        'highway': str(row['Fwy']) if pd.notna(row['Fwy']) else 'N/A'
                    }

    print(f"✓ Prepared data for {len(data_dict)} dates and 7 days of week")

    # Build date options for dropdown
    date_options_html = ""
    for date in unique_dates:
        date_str = date.strftime('%Y-%m-%d')
        day_name = speed_geo_df[speed_geo_df['Date'] == date]['DayOfWeek'].iloc[0]
        date_options_html += f'<option value="{date_str}">{date_str} ({day_name})</option>\n'

    # Build day of week options
    dow_options_html = ""
    for day in day_names:
        dow_options_html += f'<option value="{day}">{day}</option>\n'

    # Get first date for initialization
    first_date_str = unique_dates[0].strftime('%Y-%m-%d')

    # Create HTML
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ position: absolute; top: 0; bottom: 0; width: 100%; }}

        #timeline-container {{
            position: fixed; top: 20px; right: 20px;
            background: white; padding: 20px; border-radius: 12px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4); z-index: 1000;
            width: 380px; max-height: 90vh; overflow-y: auto;
        }}

        .section-title {{
            font-size: 16px; font-weight: bold; margin: 15px 0 10px 0;
            color: #333; border-bottom: 2px solid #FF6600; padding-bottom: 5px;
        }}

        .filter-mode {{
            display: flex; gap: 10px; margin-bottom: 15px;
        }}

        .mode-btn {{
            flex: 1; padding: 10px; border-radius: 8px; border: 2px solid #ddd;
            background: #f8f9fa; cursor: pointer; text-align: center;
            font-weight: bold; transition: all 0.3s;
        }}

        .mode-btn.active {{
            background: #FF6600; color: white; border-color: #FF6600;
        }}

        .mode-btn:hover {{ background: #e9ecef; }}
        .mode-btn.active:hover {{ background: #ff7700; }}

        .filter-section {{ display: none; }}
        .filter-section.active {{ display: block; }}

        select {{
            width: 100%; padding: 12px; font-size: 14px; border-radius: 8px;
            border: 2px solid #ddd; background: white; cursor: pointer;
            font-family: 'Courier New', monospace;
        }}

        select:focus {{ outline: none; border-color: #FF6600; }}

        #hour-display {{
            font-size: 36px; font-weight: bold; color: #FF6600;
            text-align: center; margin: 15px 0; font-family: 'Courier New';
        }}

        #hour-slider {{
            width: 100%; height: 12px; -webkit-appearance: none;
            background: linear-gradient(to right, #4CAF50 0%, #FFEB3B 50%, #F44336 100%);
            border-radius: 6px; cursor: pointer;
        }}

        #hour-slider::-webkit-slider-thumb {{
            -webkit-appearance: none; width: 26px; height: 26px;
            background: #333; border-radius: 50%; border: 3px solid white;
            box-shadow: 0 2px 6px rgba(0,0,0,0.4); cursor: pointer;
        }}

        #hour-slider::-moz-range-thumb {{
            width: 26px; height: 26px; background: #333;
            border-radius: 50%; border: 3px solid white;
            box-shadow: 0 2px 6px rgba(0,0,0,0.4); cursor: pointer;
        }}

        .slider-labels {{
            display: flex; justify-content: space-between;
            font-size: 11px; color: #666; margin-top: 8px;
            font-family: 'Courier New';
        }}

        .stats-display {{
            margin-top: 15px; padding: 15px; background: #f8f9fa;
            border-radius: 8px; border-left: 4px solid #FF6600;
        }}

        .stats-row {{
            display: flex; justify-content: space-between; margin: 8px 0; padding: 4px 0;
        }}

        .stats-value {{ font-weight: bold; color: #FF6600; }}

        .toggle-btn {{
            margin-top: 12px; padding: 10px; background: #d4edda;
            border-radius: 8px; text-align: center; cursor: pointer;
            border: 2px solid #28a745; font-weight: bold;
        }}

        .toggle-btn:hover {{ background: #c3e6cb; }}

        #legend {{
            position: fixed; bottom: 50px; right: 20px; background: white;
            padding: 18px; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.4);
            z-index: 1000; width: 280px;
        }}

        .legend-item {{ margin: 8px 0; display: flex; align-items: center; }}
        .legend-color {{
            width: 18px; height: 18px; border-radius: 50%;
            margin-right: 12px; border: 2px solid #333;
        }}

        .current-selection {{
            background: #e7f3ff; padding: 12px; border-radius: 8px;
            margin: 10px 0; border-left: 4px solid #0066cc;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>

    <div id="timeline-container">
        <div style="font-size: 18px; font-weight: bold; text-align: center; color: #FF6600; margin-bottom: 15px;">
            🗓️ Traffic Speed Timeline
        </div>

        <!-- Filter Mode Selection -->
        <div class="filter-mode">
            <div class="mode-btn active" id="mode-date" onclick="switchMode('date')">
                📅 Specific Date
            </div>
            <div class="mode-btn" id="mode-dow" onclick="switchMode('dow')">
                📆 Day of Week
            </div>
        </div>

        <!-- Date Filter -->
        <div class="filter-section active" id="filter-date">
            <div class="section-title">📅 Select Date</div>
            <select id="date-selector">
                {date_options_html}
            </select>
        </div>

        <!-- Day of Week Filter -->
        <div class="filter-section" id="filter-dow">
            <div class="section-title">📆 Select Day of Week</div>
            <select id="dow-selector">
                {dow_options_html}
            </select>
            <div style="font-size: 11px; color: #666; margin-top: 5px; font-style: italic;">
                *Averaged across all {len(unique_dates)} days
            </div>
        </div>

        <!-- Current Selection Display -->
        <div class="current-selection" id="current-selection">
            <strong>Viewing:</strong> <span id="selection-text">Loading...</span>
        </div>

        <!-- Hour Slider -->
        <div class="section-title">🕐 Select Hour</div>
        <div id="hour-display">00:00</div>
        <input type="range" id="hour-slider" min="0" max="23" value="0" step="1">
        <div class="slider-labels">
            <span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>23:00</span>
        </div>

        <!-- Statistics -->
        <div class="stats-display">
            <div class="stats-row">
                <span>Stations Active:</span>
                <span class="stats-value" id="active-stations">0</span>
            </div>
            <div class="stats-row">
                <span>Avg Speed:</span>
                <span class="stats-value" id="avg-speed">0 mph</span>
            </div>
            <div class="stats-row">
                <span>Speed Range:</span>
                <span class="stats-value" id="speed-range">0-0 mph</span>
            </div>
        </div>

        <div class="toggle-btn" id="heatmap-toggle">
            🗺️ Hide Heatmap
        </div>
    </div>

    <div id="legend">
        <div style="font-weight: bold; font-size: 16px; margin-bottom: 12px;">Speed Legend</div>
        <div class="legend-item">
            <span class="legend-color" style="background: green;"></span>
            <span><b>≥60 mph:</b> Free Flow</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background: lightgreen;"></span>
            <span><b>45-60 mph:</b> Smooth</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background: yellow;"></span>
            <span><b>30-45 mph:</b> Moderate</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background: orange;"></span>
            <span><b>15-30 mph:</b> Slow</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background: red;"></span>
            <span><b>&lt;15 mph:</b> Congested</span>
        </div>
    </div>

    <script>
        // Initialize map
        var map = L.map('map').setView([{center_lat}, {center_lon}], 10);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);

        // Data
        var dateData = {json.dumps(data_dict)};
        var dowData = {json.dumps(dow_data)};

        var markersLayer = L.layerGroup().addTo(map);
        var heatmapLayer = null;
        var heatmapVisible = true;
        var currentMode = 'date';

        function getSpeedColor(s) {{
            return s>=60?'green':s>=45?'lightgreen':s>=30?'yellow':s>=15?'orange':'red';
        }}

        function switchMode(mode) {{
            currentMode = mode;

            // Update buttons
            document.getElementById('mode-date').classList.remove('active');
            document.getElementById('mode-dow').classList.remove('active');
            document.getElementById('mode-' + mode).classList.add('active');

            // Update sections
            document.getElementById('filter-date').classList.remove('active');
            document.getElementById('filter-dow').classList.remove('active');
            document.getElementById('filter-' + mode).classList.add('active');

            // Update map
            updateMap();
        }}

        function updateMap() {{
            var hour = parseInt(document.getElementById('hour-slider').value);
            var data;
            var displayText;

            if (currentMode === 'date') {{
                var selectedDate = document.getElementById('date-selector').value;
                if (!dateData[selectedDate] || !dateData[selectedDate].hours[hour]) {{
                    console.log('No data for date:', selectedDate, 'hour:', hour);
                    markersLayer.clearLayers();
                    if (heatmapLayer) map.removeLayer(heatmapLayer);
                    return;
                }}
                data = dateData[selectedDate].hours[hour];
                var dayName = dateData[selectedDate].day_name;
                displayText = `${{selectedDate}} (${{dayName}}) at ${{String(hour).padStart(2, '0')}}:00`;
            }} else {{
                var selectedDow = document.getElementById('dow-selector').value;
                if (!dowData[selectedDow] || !dowData[selectedDow].hours[hour]) {{
                    console.log('No data for day:', selectedDow, 'hour:', hour);
                    markersLayer.clearLayers();
                    if (heatmapLayer) map.removeLayer(heatmapLayer);
                    return;
                }}
                data = dowData[selectedDow].hours[hour];
                displayText = `All ${{selectedDow}}s (avg) at ${{String(hour).padStart(2, '0')}}:00`;
            }}

            document.getElementById('selection-text').textContent = displayText;

            // Clear and update markers
            markersLayer.clearLayers();
            var speeds = [], heatData = [], active = 0;

            for (var id in data) {{
                var s = data[id], spd = s.speed, col = getSpeedColor(spd);
                speeds.push(spd); active++;
                heatData.push([s.lat, s.lon, Math.min(spd/100, 1)]);

                var popup = `<div style="min-width: 240px;">
                    <h4 style="margin: 0 0 10px 0; color: #333; border-bottom: 2px solid #FF6600; padding-bottom: 5px;">
                        Station ${{id}}
                    </h4>
                    <table style="width: 100%;">
                        <tr style="background: #f8f9fa;"><td style="padding: 6px;"><b>Time:</b></td>
                            <td>${{String(hour).padStart(2, '0')}}:00</td></tr>
                        <tr><td style="padding: 6px;"><b>Highway:</b></td><td>${{s.highway}}</td></tr>
                        <tr style="background: #f8f9fa;"><td style="padding: 6px;"><b>Location:</b></td><td>${{s.name}}</td></tr>
                        <tr style="background: #fff3cd;"><td style="padding: 6px;"><b>Speed:</b></td>
                            <td><b style="color: #FF6600; font-size: 18px;">${{spd.toFixed(1)}} mph</b></td></tr>
                        <tr style="background: #f8f9fa;"><td style="padding: 6px;"><b>Flow:</b></td><td>${{s.flow.toFixed(0)}} veh/hr</td></tr>
                        <tr><td style="padding: 6px;"><b>Occupancy:</b></td><td>${{s.occupancy.toFixed(3)}}</td></tr>
                    </table>
                </div>`;

                L.circleMarker([s.lat, s.lon], {{
                    radius: 8, fillColor: col, color: '#333', weight: 2,
                    opacity: 0.9, fillOpacity: 0.8
                }}).bindPopup(popup).bindTooltip(`${{id}}: ${{spd.toFixed(1)}} mph`).addTo(markersLayer);
            }}

            // Update heatmap
            if (heatmapLayer) map.removeLayer(heatmapLayer);
            if (heatmapVisible && heatData.length > 0) {{
                heatmapLayer = L.heatLayer(heatData, {{ radius: 25, blur: 30, max: 1.0 }}).addTo(map);
            }}

            // Update stats
            document.getElementById('active-stations').textContent = active;
            if (speeds.length > 0) {{
                var avg = speeds.reduce((a,b)=>a+b,0)/speeds.length;
                document.getElementById('avg-speed').textContent = avg.toFixed(1) + ' mph';
                document.getElementById('speed-range').textContent =
                    Math.min(...speeds).toFixed(0) + '-' + Math.max(...speeds).toFixed(0) + ' mph';
            }} else {{
                document.getElementById('avg-speed').textContent = 'N/A';
                document.getElementById('speed-range').textContent = 'N/A';
            }}
        }}

        // Event listeners
        document.getElementById('hour-slider').addEventListener('input', function() {{
            var h = parseInt(this.value);
            document.getElementById('hour-display').textContent = String(h).padStart(2, '0') + ':00';
            updateMap();
        }});

        document.getElementById('date-selector').addEventListener('change', updateMap);
        document.getElementById('dow-selector').addEventListener('change', updateMap);

        document.getElementById('heatmap-toggle').addEventListener('click', function() {{
            heatmapVisible = !heatmapVisible;
            updateMap();
            this.style.background = heatmapVisible ? '#d4edda' : '#f8d7da';
            this.style.borderColor = heatmapVisible ? '#28a745' : '#dc3545';
            this.textContent = heatmapVisible ? '🗺️ Hide Heatmap' : '🗺️ Show Heatmap';
        }});

        // Initialize
        updateMap();
    </script>
</body>
</html>
    """

    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✓ Map saved to: {output_file}")
    print(f"✓ Features: Date selector + Day of week selector + Hour slider")
    print(f"✓ {len(unique_dates)} dates available")
    print(f"✓ {len(stations)} stations with markers + heatmap")

    return output_file


if __name__ == "__main__":
    print("Import and use: create_timeline_with_date_selector(merged_df)")
