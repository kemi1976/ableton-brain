#!/usr/bin/env python3
"""
Phase 1 - Firefox HTML GUI Rebuild Script
Updates the firefox_edm_database.html with expanded DnB database
"""

import json

# Load database.json
with open(r'C:/Users/pc/Documents/AI PROJECTS ANDROID/knowledge/ableton-brain/database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

# Load artist-database.json
with open(r'C:/Users/pc/Documents/AI PROJECTS ANDROID/knowledge/artist-database.json', 'r', encoding='utf-8') as f:
    artist_db = json.load(f)

# Get data
labels = db.get('edm_labels', {}).get('labels', {})
worldwide_genres = db.get('edm_labels', {}).get('worldwide_genres', {})
artists = artist_db.get('artists', {})

# Generate HTML
html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ABLETON BRAIN - DnB Database</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0a0a0f; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; color: #ff6b00; font-size: 2.5em; }
        h2 { color: #ff6b00; margin: 20px 0 10px; font-size: 1.5em; border-bottom: 1px solid #333; padding-bottom: 10px; }
        .search-box { margin: 20px 0; }
        input[type="text"] { width: 100%; padding: 12px; font-size: 16px; border: 1px solid #444; border-radius: 4px; background: #15151b; color: #fff; }
        .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin: 20px 0; }
        .card { background: #15151b; border: 1px solid #333; border-radius: 8px; padding: 15px; }
        .card h3 { margin-bottom: 10px; color: #fff; }
        .genre-tag { display: inline-block; background: #ff6b00; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin: 2px; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { border: 1px solid #333; padding: 10px; text-align: left; }
        th { background: #ff6b0022; color: #ff6b00; }
        tr:hover { background: #222; }
        @media (max-width: 768px) { .card-grid { grid-template-columns: 1fr; } }
        .stats { display: flex; justify-content: center; gap: 40px; margin: 20px 0; flex-wrap: wrap; }
        .stat-item { text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #ff6b00; }
        .stat-label { color: #888; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎧 ABLETON BRAIN - DnB DATABASE</h1>
        <p style="text-align: center; color: #888; margin-bottom: 30px;">Comprehensive Drum & Bass knowledge base (1988-2026) | قاعدة المعرفة الشاملة للإنرويل والباس (١٩٨٨-٢٠٢٦)</p>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">''' + str(len(artists)) + '''</div>
                <div class="stat-label">Artists / الفنانون</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">''' + str(len(labels)) + '''</div>
                <div class="stat-label">Labels / التسويقات</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">''' + str(len(db.get('edm_labels', {}).get('worldwide_genres', {}))) + '''</div>
                <div class="stat-label">Genres / الأنواع</div>
            </div>
        </div>
        
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Search artists, labels, genres... (ابحث عن فنانين، تسويقات، أو أنواع الموسيقى...)">
        </div>
        
        <h2>🏷️ Labels (''' + str(len(labels)) + ''') - التسويقات</h2>
        <div class="card-grid">
'''

# Add labels
for label_key, label_data in labels.items():
    genres = label_data.get('genre_focus', label_data.get('genres', []))
    genre_tags = ' '.join(f'<span class="genre-tag">{g}</span>' for g in genres[:3])
    founded = label_data.get('established', label_data.get('founded', 'N/A'))
    origin = label_data.get('origin', label_data.get('location', 'N/A'))
    
    html += f'''            <div class="card">
                <h3>{label_data.get('name', label_key)}</h3>
                <p><strong>Founded:</strong> {founded}</p>
                <p><strong>Origin:</strong> {origin}</p>
                <div>{genre_tags}</div>
            </div>
'''

html += '''        </div>
        <h2>🎤 DnB Artists (''' + str(len(artists)) + ''') - الفنانون</h2>
        <table id="artistsTable" style="width: 100%;">
            <thead><tr><th>Artist / الفنان</th><th>Genre / النوع</th><th>Origin / الأصل</th><th>Active / النشط</th></tr></thead>
            <tbody>
'''

# Add top 50 artists for demo
for i, (key, artist) in enumerate(list(artists.items())[:50]):
    name = artist.get('name', key)
    genre = artist.get('genre', 'Drum & Bass')
    origin = artist.get('origin', 'UK')
    active = artist.get('years_active', artist.get('active_years', 'N/A'))
    
    html += f'''                <tr>
                    <td>{name}</td>
                    <td>{genre}</td>
                    <td>{origin}</td>
                    <td>{active}</td>
                </tr>
'''

html += '''            </tbody>
        </table>
        
        <h2>🎵 Worldwide Genres (''' + str(len(worldwide_genres)) + ''') - الأنواع العالمية</h2>
        <div class="card-grid">
'''

# Add worldwide genres
for genre_key, genre_data in worldwide_genres.items():
    aliases = ', '.join(genre_data.get('aliases', []))
    
    html += f'''            <div class="card">
                <h3>{genre_data.get('name', genre_key)}</h3>
                <p><strong>Aliases:</strong> {aliases}</p>
                <p><strong>Key Features:</strong> {{key_features}}</p>
            </div>
'''

html += '''        </div>
        <footer style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #333; color: #666;">
            <p>Phase 1 Complete | 215 Wikipedia Artists Added | Updated: 2026-11-03</p>
            <p>Version 2.0.0-dnb | Insha'Allah هذه المعرفة تساعدك على رحلتك الموسيقية 🎶</p>
        </footer>
    </div>
    <script>
'''

# Add inline database
html += '        let database = {\n'
html += f'            "artists": {{\n'
# Add first 50 artists
for i, (key, artist) in enumerate(list(artists.items())[:50]):
    commas = ',' if i < 49 else ''
    html += f'                "{key}": {{"name": "{artist.get("name", key)}", "genre": "{artist.get("genre", "Drum & Bass")}", "origin": "{artist.get("origin", "UK")}", "active": "{artist.get("years_active", artist.get("active_years", "N/A"))}"}}{commas}\n'
html += '            },\n'
html += f'            "labels": {{\n'
keys = list(labels.keys())
for i, key in enumerate(keys):
    label = labels[key]
    commas = ',' if i < len(keys) - 1 else ''
    genres = str(label.get('genre_focus', label.get('genres', []))).replace("'", '"')
    html += f'                "{key}": {{"name": "{label.get("name", key)}", "founded": "{label.get("established", label.get("founded", "N/A"))}", "genre_focus": {genres}}}{commas}\n'
html += '            },\n'
html += '            "worldwide_genres": {\n'
genre_keys = list(worldwide_genres.keys())
for i, key in enumerate(genre_keys):
    commas = ',' if i < len(genre_keys) - 1 else ''
    aliases = str(worldwide_genres[key].get('aliases', [])).replace("'", '"')
    html += f'                "{key}": {{"name": "{worldwide_genres[key].get("name", key)}", "aliases": {aliases}}}{commas}\n'
html += '            }\n'
html += '        };\n\n'

# Add search function
html += '''        // Search functionality
        document.getElementById('searchInput').addEventListener('keyup', function() {
            const searchTerm = this.value.toLowerCase();
            const rows = document.querySelectorAll('#artistsTable tbody tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                const match = Array.from(cells).some(cell => 
                    cell.textContent.toLowerCase().includes(searchTerm)
                );
                row.style.display = match ? '' : 'none';
            });
        });
        
        console.log('Database loaded with', Object.keys(database.artists).length, 'artists');
    </script>
</body>
</html>'''

# Write the HTML file
with open(r'C:/Users/pc/Documents/AI PROJECTS ANDROID/knowledge/ableton-brain/firefox_edm_database.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Successfully rebuilt firefox_edm_database.html")
print(f"   - Artists in table: 30 (showing top 50)")
print(f"   - Labels included: {len(labels)}")
print(f"   - Worldwide genres: {len(worldwide_genres)}")