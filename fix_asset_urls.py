import sqlite3
import json
from urllib.parse import quote

conn = sqlite3.connect('test.db')
cursor = conn.cursor()

cursor.execute('SELECT id, options FROM questions WHERE type = "code"')
questions = cursor.fetchall()

fixed_count = 0
for q_id, options_str in questions:
    try:
        options = json.loads(options_str)
        
        if '_asset_url' in options and '_asset_download_url' not in options:
            asset_url = options['_asset_url']
            # 从 asset_url 提取文件名
            saved_name = asset_url.split('/')[-1]
            asset_name = options.get('_asset_name', saved_name)
            
            # 生成下载URL
            download_url = f"/api/uploads/download/{saved_name}?name={quote(asset_name)}"
            options['_asset_download_url'] = download_url
            
            # 更新数据库
            cursor.execute(
                'UPDATE questions SET options = ? WHERE id = ?',
                (json.dumps(options), q_id)
            )
            fixed_count += 1
            print(f"Fixed question {q_id}: added download URL for {asset_name}")
    except Exception as e:
        print(f"Error processing question {q_id}: {e}")

conn.commit()
conn.close()

print(f"\nFixed {fixed_count} questions")
