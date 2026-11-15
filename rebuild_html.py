import json

# Read knowledge database
with open(r'C:/Users/pc/Documents/AI PROJECTS ANDROID/knowledge/ableton-brain/database.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

# Build the inline database for HTML
database = {
    'labels': db.get('edm_labels', {}).get('labels', {}),
    'artists': db.get('artists', {}),
    'worldwide_genres': db.get('edm_labels', {}).get('worldwide_genres', {}),
    'corrections_made': db.get('edm_labels', {}).get('corrections_made', {}),
    'research_metadata': db.get('edm_labels', {}).get('research_metadata', {})
}

html_parts = []

# HTML header
html_parts.append('<!DOCTYPE html>\n')
html_parts.append('<html lang="en">\n')
html_parts.append('<head>\n')
html_parts.append('    <meta charset="UTF-8">\n')
html_parts.append('    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n')
html_parts.append('    <title>ABLETON BRAIN - EDM Database</title>\n')
html_parts.append('    <style>\n')
html_parts.append('        * { box-sizing: border-box; margin: 0; padding: 0; }\n')
html_parts.append('        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0a0a0f; color: #e0e0e0; padding: 20px; }\n')
html_parts.append('        .container { max-width: 1200px; margin: 0 auto; }\n')
html_parts.append('        h1 { text-align: center; margin-bottom: 30px; color: #00d4ff; font-size: 2.5em; }\n')
html_parts.append('        h2 { color: #00d4ff; margin: 20px 0 10px; font-size: 1.5em; border-bottom: 1px solid #333; padding-bottom: 10px; }\n')
html_parts.append('        .search-box { margin: 20px 0; }\n')
html_parts.append('        input[type="text"] { width: 100%; padding: 12px; font-size: 16px; border: 1px solid #444; border-radius: 4px; background: #15151b; color: #fff; }\n')
html_parts.append('        .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin: 20px 0; }\n')
html_parts.append('        .card { background: #15151b; border: 1px solid #333; border-radius: 8px; padding: 15px; }\n')
html_parts.append('        .card h3 { margin-bottom: 10px; color: #fff; }\n')
html_parts.append('        .genre-tag { display: inline-block; background: #4a90d9; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin: 2px; }\n')
html_parts.append('        table { width: 100%; border-collapse: collapse; margin: 15px 0; }\n')
html_parts.append('        th, td { border: 1px solid #333; padding: 10px; text-align: left; }\n')
html_parts.append('        th { background: #00d4ff22; color: #00d4ff; }\n')
html_parts.append('        tr:hover { background: #222; }\n')
html_parts.append('        @media (max-width: 768px) { .card-grid { grid-template-columns: 1fr; } }\n')
html_parts.append('    </style>\n')
html_parts.append('</head>\n')
html_parts.append('<body>\n')
html_parts.append('    <div class="container">\n')
html_parts.append('        <h1>🎧 ABLETON BRAIN - EDM DATABASE</h1>\n')

footer_text = "Comprehensive knowledge base of UK Drum & Bass, Jungle, and Electronic Music (1980s-2026)"
html_parts.append(f'        <p style="text-align: center; color: #888; margin-bottom: 30px;">{footer_text}</p>\n')

# Search section
html_parts.append('        <div class="search-box">\n')
search_placeholder = "Search artists, labels, genres... (ابحث عن فنانين، تسويقات، أو أنواع الموسيقى...)"
html_parts.append(f'            <input type="text" id="searchInput" placeholder="{search_placeholder}" onkeyup="filterTable()">\n')
html_parts.append('        </div>\n')

# Labels section
html_parts.append(f"        <h2>📦 Labels ({len(database['labels'])}) - التسويقات ({len(database['labels'])})</h2>\n")
html_parts.append('        <div class="card-grid">\n')
for lid, label in database['labels'].items():
    name = label.get('name', lid.replace('_', ' ').title())
    genre_focus = label.get('genre_focus', [])
    html_parts.append('            <div class="card">\n')
    html_parts.append(f'                <h3>{name}</h3>\n')
    html_parts.append(f'                <p><strong>Founded:</strong> {label.get("established", "N/A")}</p>\n')
    html_parts.append(f'                <p><strong>Origin:</strong> {label.get("origin", "N/A")}</p>\n')
    if genre_focus:
        tags = ''.join([f'<span class="genre-tag">{g}</span>' for g in genre_focus[:3]])
        html_parts.append(f'                <div>{tags}</div>\n')
    html_parts.append('            </div>\n')
html_parts.append('        </div>\n')

# Artists section
html_parts.append(f"        <h2>🎤 Artists ({len(database['artists'])}) - الفنانون ({len(database['artists'])})</h2>\n")
html_parts.append('        <table id="artistsTable" style="width: 100%;">\n')
html_parts.append('            <thead><tr><th>Artist / الفنان</th><th>Genre / النوع</th><th>Origin / الأصل</th><th>Active / النشط</th></tr></thead>\n')
html_parts.append('            <tbody>\n')
for aid, artist in database['artists'].items():
    name = artist.get('name') or artist.get('real_name', aid.replace('_', ' ').title())
    genre = artist.get('genre', 'N/A')
    origin = artist.get('origin', 'N/A')
    years = artist.get('years_active', 'N/A')
    if isinstance(genre, list):
        genre = ', '.join(genre) if genre else 'N/A'
    html_parts.append(f'                <tr><td>{name}</td><td>{genre}</td><td>{origin}</td><td>{years}</td></tr>\n')
html_parts.append('            </tbody>\n')
html_parts.append('        </table>\n')

# Genres section
html_parts.append(f"        <h2>🎵 Worldwide Genres ({len(database['worldwide_genres'])}) - الأنواع العالمية ({len(database['worldwide_genres'])})</h2>\n")
html_parts.append('        <div class="card-grid">\n')

genre_map = {
    'drum_and_bass': 'Drum & Bass',
    'jungle': 'Jungle', 
    'jungle_techno': 'Jungle Techno',
    'hardcore': 'UK Hardcore',
    'uk_garage': 'UK Garage',
    'dubstep': 'Dubstep'
}

for gid, genre in database['worldwide_genres'].items():
    name = genre.get('name', genre_map.get(gid, gid.replace('_', ' ').title()))
    aliases = genre.get('aliases', [])
    html_parts.append('            <div class="card">\n')
    html_parts.append(f'                <h3>{name}</h3>\n')
    if aliases:
        alias_str = ', '.join(aliases)
        html_parts.append(f'                <p><strong>Aliases / بدائل:</strong> {alias_str}</p>\n')
    chars = genre.get('key_characteristics', [])
    if chars:
        char_str = ', '.join(chars[:3])
        html_parts.append(f'                <p><strong>Key Features / المميزات الرئيسية:</strong> {char_str}</p>\n')
    html_parts.append('            </div>\n')
html_parts.append('        </div>\n')

# Corrections section
html_parts.append('        <h2>✅ Corrections Made - تصحيحات مُجَرَّدَة</h2>\n')
html_parts.append('        <table id="correctionsTable" style="width: 100%;">\n')
html_parts.append('            <thead><tr><th>Artist / الفنان</th><th>Error Type / نوع الخطأ</th><th>Correction / التصحيح</th></tr></thead>\n')
html_parts.append('            <tbody>\n')
for aid, correction in database['corrections_made'].items():
    artist_name = database['artists'].get(aid, {}).get('name') or aid.replace('_', ' ').title()
    error_type = correction.get('error_type', 'N/A')
    correct_class = correction.get('correct_classification', 'N/A')
    html_parts.append(f'                <tr><td>{artist_name}</td><td>{error_type}</td><td>{correct_class}</td></tr>\n')
html_parts.append('            </tbody>\n')
html_parts.append('        </table>\n')

# Footer
footer_msg = "Version 3.0.0 | Research by ABLETON BRAIN | Insha'Allah this knowledge helps your music journey 🎶"
html_parts.append(f'        <footer style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #333; color: #666;">\n')
html_parts.append(f'            <p>{footer_msg}</p>\n')
html_parts.append('        </footer>\n')

# Close container before script
html_parts.append('    </div>\n')

# Inline database for Firefox compatibility
html_parts.append('    <script>\n')
html_parts.append('        // Inline data - embedded directly for Firefox compatibility\n')
db_json = json.dumps(database, indent=12, ensure_ascii=False)
html_parts.append(f'        let database = {db_json};\n')
html_parts.append('\n')
html_parts.append('        function filterTable() {\n')
html_parts.append('            const input = document.getElementById("searchInput");\n')
html_parts.append('            const tbody = document.querySelector("#artistsTable tbody");\n')
html_parts.append('            const rows = tbody.querySelectorAll("tr");\n')
html_parts.append('            const filter = input.value.toLowerCase();\n')
html_parts.append('            rows.forEach(row => {\n')
html_parts.append('                const text = row.textContent.toLowerCase();\n')
html_parts.append('                row.style.display = text.includes(filter) ? "" : "none";\n')
html_parts.append('            });\n')
html_parts.append('        }\n')
html_parts.append('\n')
html_parts.append('        document.addEventListener("DOMContentLoaded", function() {\n')
html_parts.append('            console.log("Database loaded with", database.artists.length, "artists,", database.labels.length, "labels,", database.worldwide_genres.length, "genres");\n')
html_parts.append('        });\n')
html_parts.append('\n')
html_parts.append('        window.addEventListener("pageshow", function(event) {\n')
html_parts.append('            // Firefox sometimes clears JS state on back/forward navigation\n')
html_parts.append('            if (event.persisted) {\n')
html_parts.append('                console.log("Page restored in Firefox");\n')
html_parts.append('            }\n')
html_parts.append('        });\n')
html_parts.append('    </script>\n')
html_parts.append('</body>\n')
html_parts.append('</html>\n')

# Write the fixed HTML
with open(r'C:/Users/pc/Documents/AI PROJECTS ANDROID/knowledge/ableton-brain/firefox_edm_database.html', 'w', encoding='utf-8') as f:
    f.writelines(html_parts)

print("HTML file rebuilt successfully!")

# Verification
with open(r'C:/Users/pc/Documents/AI PROJECTS ANDROID/knowledge/ableton-brain/firefox_edm_database.html', 'r', encoding='utf-8') as f:
    content = f.read()
    print(f"File size: {len(content)} bytes")
    print(f"Has <script> tag: {'<script>' in content}")
    print(f"Has </script> tag: {'</script>' in content}")
    print(f"Has database object: {'let database' in content}")
    print(f"Has DOMContentLoaded: {'DOMContentLoaded' in content}")