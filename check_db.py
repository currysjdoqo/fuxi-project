import sqlite3
import json

conn = sqlite3.connect('test.db')
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor]

if 'questions' in tables:
    cursor = conn.execute('SELECT id, content, options, type FROM questions')
    print("Attachment Questions (type=code with _asset_url):")
    for row in cursor:
        q_id, content, options_str, q_type = row
        if q_type == 'code':
            try:
                options = json.loads(options_str)
                if '_asset_url' in options:
                    print(f"\nID: {q_id}")
                    print(f"Content: {content}")
                    print(f"Asset URL: {options.get('_asset_url', '')}")
                    print(f"Asset Download URL: {options.get('_asset_download_url', '')}")
                    print(f"Asset Name: {options.get('_asset_name', '')}")
            except:
                pass

conn.close()