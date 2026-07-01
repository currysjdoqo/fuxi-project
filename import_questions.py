import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8001/api"

def make_request(method, endpoint, data=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8') if data else None, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8')), response.status
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode('utf-8')}, e.code
    except Exception as e:
        return {"error": str(e)}, 500

# 登录获取token
def login():
    import time
    username = f"user_{int(time.time())}"  # 使用时间戳创建唯一用户名
    password = "import123"

    # 注册
    print(f"尝试注册用户: {username}")
    data, status = make_request("POST", "/auth/register", {"username": username, "password": password})
    print(f"注册响应: status={status}, data={data}")

    if status == 200:
        print(f"尝试登录用户: {username}")
        data, status = make_request("POST", "/auth/login", {"username": username, "password": password})
        print(f"登录响应: status={status}, data={data}")
        if status == 200:
            print(f"注册并登录成功，用户名: {username}")
            token = data.get("token") or data.get("access_token")
            print(f"Token: {token}")
            return token

    print(f"登录结果: {data}, status: {status}")
    return None

# 导入题目
def import_questions(token, subject_id):
    # 读取解析好的题目
    with open('parsed_questions.json', 'r', encoding='utf-8') as f:
        questions = json.load(f)

    # 先检查科目是否存在
    data, status = make_request("GET", f"/subjects/{subject_id}", token=token)
    if status != 200:
        print(f"科目 ID {subject_id} 不存在，正在创建...")
        data, status = make_request("POST", "/subjects", {"name": "操作系统", "description": "操作系统练习题"}, token)
        if status == 200:
            subject_id = data.get("id")
            print(f"科目创建成功，ID: {subject_id}")
        else:
            print(f"科目创建失败: {data}")
            return

    print(f"科目 ID: {subject_id}")
    print(f"开始导入 {len(questions)} 道题目...")

    # 批量导入题目
    success_count = 0
    for i, q in enumerate(questions):
        question_data = {
            "subject_id": subject_id,
            "type": q["type"],
            "content": q["content"],
            "answer": q["answer"],
            "explanation": q.get("explanation", ""),
            "options": q.get("options", {})  # 所有类型都提供 options 字段
        }

        result, status = make_request("POST", "/questions", question_data, token)
        if status == 200:
            success_count += 1
            print(f"  [{i+1}/{len(questions)}] 导入成功")
        else:
            print(f"  [{i+1}/{len(questions)}] 导入失败: {status} - {result}")

    print(f"\n导入完成！成功 {success_count}/{len(questions)} 道题目")

if __name__ == "__main__":
    import time
    print("等待服务器启动...")
    time.sleep(3)

    print("正在登录/注册...")
    token = login()
    if token:
        print(f"登录成功，token: {token[:20]}...")
        time.sleep(1)
        import_questions(token, 7)  # subject_id = 7
    else:
        print("登录失败，请先在网站上注册账号")
