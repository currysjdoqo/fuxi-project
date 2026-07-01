import json
import urllib.request
import urllib.error
import time

BASE_URL = "http://localhost:8000/api"

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

def login():
    username = f"user_{int(time.time())}"
    password = "import123"

    data, status = make_request("POST", "/auth/register", {"username": username, "password": password})
    if status == 200:
        data, status = make_request("POST", "/auth/login", {"username": username, "password": password})
        if status == 200:
            return data.get("token")

    print(f"注册/登录失败: {data}")
    return None

questions_data = [
    {
        "content": "在多道批处理系统中，作业的周转时间通常较长，其主要原因是（ ）。",
        "options": {"A": "CPU运行速度太慢", "B": "作业需要频繁与用户交互", "C": "作业在内存中排队等待CPU及I/O设备", "D": "内存容量太小导致频繁换入换出"},
        "answer": "C",
        "explanation": "多道批处理缺乏交互，作业周转慢是因为它们在内存中排队等待资源（CPU/I/O），而不是CPU速度慢（A错），B是分时系统。"
    },
    {
        "content": "当进程由就绪态转为运行态时，触发该状态变迁的事件是（ ）。",
        "options": {"A": "进程申请I/O设备", "B": "进程等待的时间发生", "C": "进程调度程序选中该进程", "D": "当前运行进程时间片用完"},
        "answer": "C",
        "explanation": "就绪→运行：由进程调度程序从就绪队列中选中一个进程分配CPU。A导致运行→阻塞，B导致阻塞→就绪，D导致运行→就绪。"
    },
    {
        "content": "操作系统内核提供的原语操作具有不可中断性，其实现通常通过（ ）。",
        "options": {"A": "关中断指令", "B": "打开中断指令", "C": "特权指令", "D": "系统调用"},
        "answer": "A",
        "explanation": "原语（原子操作）的不可中断性通过执行关中断指令实现，防止执行期间被中断。"
    },
    {
        "content": "多个并发进程访问同一个共享数据区域时，可能造成数据不一致，该区域被称为（ ）。",
        "options": {"A": "临界区", "B": "公共区", "C": "互斥区", "D": "共享内存"},
        "answer": "A",
        "explanation": "并发进程中涉及共享变量的程序段称为临界区。B/C/D是广义术语。"
    },
    {
        "content": "在死锁的四个必要条件中，破坏循环等待条件常用的方法是（ ）。",
        "options": {"A": "资源静态分配策略（一次性申请所有资源）", "B": "允许进程剥夺其他进程的资源", "C": "将资源编号，进程按编号递增顺序申请资源", "D": "允许进程在申请新资源时保留已有资源"},
        "answer": "C",
        "explanation": "破坏循环等待通常采用资源有序分配法（将资源编号，进程必须按编号递增顺序申请）。A破坏请求与保持，B破坏不可抢占，D则是导致循环等待的原因之一。"
    },
    {
        "content": "某系统采用动态分区分配策略，若当前空闲分区大小差异很大，为了给大作业预留空间，应选用（ ）算法。",
        "options": {"A": "首次适应", "B": "最佳适应", "C": "最坏适应（最大适应）", "D": "循环首次适应"},
        "answer": "C",
        "explanation": "最坏适应算法按分区大小递减排序，优先分配最大的空闲分区，剩下来的分区也较大，适合为大作业预留空间。"
    },
    {
        "content": "在段页式存储管理中，CPU每次访问一条指令或数据，至少需要访问内存（ ）次（不考虑快表）。",
        "options": {"A": "2", "B": "3", "C": "4", "D": "5"},
        "answer": "B",
        "explanation": "段页式管理：第一次访问段表，第二次访问页表，第三次访问目标数据/指令（无快表时）。共3次。"
    },
    {
        "content": "虚拟存储器的最大容量取决于（ ）。",
        "options": {"A": "内存和外存容量之和", "B": "计算机系统地址总线的位数", "C": "进程的页表大小", "D": "磁盘的读写速度"},
        "answer": "B",
        "explanation": "虚拟存储器的理论最大容量受地址总线位数（寻址范围）限制。实际使用受内外存总和限制，但决定上限的是地址结构。"
    },
    {
        "content": "下列磁盘调度算法中，既能避免饥饿现象，又兼顾了寻道时间的是（ ）。",
        "options": {"A": "先来先服务（FCFS）", "B": "最短寻道时间优先（SSTF）", "C": "扫描算法（SCAN，电梯算法）", "D": "循环扫描算法（C-SCAN）"},
        "answer": "C",
        "explanation": "SCAN（电梯算法）在移动过程中响应请求，避免SSTF的饥饿问题，同时寻道性能优于FCFS。"
    },
    {
        "content": "假脱机（SPOOLing）技术核心由两部分组成：输入井/输出井和（ ）。",
        "options": {"A": "内存缓冲区", "B": "预输入程序/缓输出程序", "C": "通道控制器", "D": "DMA控制器"},
        "answer": "B",
        "explanation": "SPOOLing系统由输入井/输出井（磁盘）和预输入/缓输出程序组成。A是缓冲，C/D是硬件。"
    },
    {
        "content": "下列文件物理结构中，既支持随机访问又便于文件动态增长的是（ ）。",
        "options": {"A": "连续结构", "B": "链接结构（隐式链接）", "C": "索引结构", "D": "顺序结构"},
        "answer": "C",
        "explanation": "索引结构：通过索引块查找，支持随机访问；新增数据只需增加索引项，易于动态增长。A/B/D动态扩展困难。"
    },
    {
        "content": "用户程序通过访管指令或系统调用进入核心态时，CPU状态的转换是（ ）。",
        "options": {"A": "由核心态转为用户态", "B": "由用户态转为核心态", "C": "保持核心态不变", "D": "保持用户态不变"},
        "answer": "B",
        "explanation": "用户程序通过访管指令（系统调用）陷入内核，CPU从用户态切换为核心态。"
    },
    {
        "content": "进程间的同步与互斥中，实现互斥的准则之一是忙则等待，其含义是（ ）。",
        "options": {"A": "若资源空闲，则允许申请", "B": "若资源被占用，则申请者必须阻塞等待", "C": "若进程阻塞，则释放资源", "D": "进程必须按顺序访问资源"},
        "answer": "B",
        "explanation": "忙则等待指当临界资源被占用时，其他请求进程必须阻塞等待直到释放。"
    },
    {
        "content": "引入动态重定位技术的主要目的是（ ）。",
        "options": {"A": "解决程序链接问题", "B": "允许作业在内存中移动，提高内存利用率", "C": "减少内存碎片", "D": "实现虚拟内存"},
        "answer": "B",
        "explanation": "动态重定位（地址变换在运行时进行）允许进程在内存中移动（紧凑），从而消除外碎片，提高内存利用率。"
    },
    {
        "content": "关于时间片轮转（RR）调度算法，下列说法正确的是（ ）。",
        "options": {"A": "时间片越大，系统开销越大", "B": "时间片越小，系统响应越快，系统开销越小", "C": "时间片的选择需平衡系统开销与响应时间", "D": "该算法不适合分时系统"},
        "answer": "C",
        "explanation": "时间片过大退化为FCFS，过小则切换开销剧增。必须平衡（C正确）。A说反了（越大开销越小），B说开销越小错。"
    },
    {
        "content": "在文件系统中，为实现设备独立性，用户程序中使用的是（ ）。",
        "options": {"A": "物理设备名（如/dev/sda）", "B": "逻辑设备名", "C": "设备控制器地址", "D": "设备号"},
        "answer": "B",
        "explanation": "设备独立性（设备无关性）要求用户使用逻辑设备名，由系统映射到物理设备。"
    },
    {
        "content": "若信号量S的初值为2，当前有3个进程等待进入临界区，则S的当前值应为（ ）。",
        "options": {"A": "1", "B": "-1", "C": "-3", "D": "2"},
        "answer": "C",
        "explanation": "S<0时绝对值代表等待进程数。有3个等待，则S = -3（初值为0，再减去3）。"
    },
    {
        "content": "操作系统为用户提供按名存取文件的功能，该功能由（ ）实现。",
        "options": {"A": "文件控制块（FCB）", "B": "文件目录", "C": "索引节点", "D": "文件分配表（FAT）"},
        "answer": "B",
        "explanation": "文件目录是实现按名存取的核心数据结构，它将文件名映射到FCB或索引节点。"
    },
    {
        "content": "在请求分页系统中，使用最佳置换算法（OPT）时，缺页中断率（ ）。",
        "options": {"A": "一定比其他算法低", "B": "一定比其他算法高", "C": "是理论最低的，但无法实现", "D": "与FIFO算法完全相同"},
        "answer": "C",
        "explanation": "OPT淘汰未来最久不用的页面，缺页率是理论最低，但无法预知未来，仅作为评价基准。"
    },
    {
        "content": "下列关于用户级线程（User-Level Thread）和内核级线程（Kernel-Level Thread）的说法，正确的是（ ）。",
        "options": {"A": "用户级线程的切换不需要内核干预", "B": "内核级线程对操作系统不可见", "C": "用户级线程可以利用多核并行", "D": "内核级线程的创建和管理开销更小"},
        "answer": "A",
        "explanation": "用户级线程由用户库管理，切换无需内核干预（A正确）。B错（内核级线程内核可见），C错（用户级线程多核并行受限），D错（内核级线程开销更大）。"
    }
]

def import_questions(token, subject_id):
    # 检查科目是否存在
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

    print(f"开始导入 {len(questions_data)} 道题目到科目 ID {subject_id}...")

    success_count = 0
    for i, q in enumerate(questions_data):
        question_data = {
            "subject_id": subject_id,
            "type": "single_choice",
            "content": q["content"],
            "options": q["options"],
            "answer": q["answer"],
            "explanation": q["explanation"]
        }

        result, status = make_request("POST", "/questions", question_data, token)
        if status == 200:
            success_count += 1
            print(f"  [{i+1}/{len(questions_data)}] 导入成功")
        else:
            print(f"  [{i+1}/{len(questions_data)}] 导入失败: {status} - {result}")

    print(f"\n导入完成！成功 {success_count}/{len(questions_data)} 道题目")

if __name__ == "__main__":
    time.sleep(2)
    token = login()
    if token:
        import_questions(token, 7)
    else:
        print("登录失败")
