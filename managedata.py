import json
import os
import time
import sys
import shutil
from pathlib import Path

# ================= 配置区域 =================
BASE_DIR = Path(__file__).parent if "__file__" in locals() else Path.cwd()
DATA_DIR = BASE_DIR / "data"
SUBJECTS_FILE = DATA_DIR / "subjects.json"
# ===========================================

def ensure_setup():
    """初始化根目录"""
    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if not SUBJECTS_FILE.exists():
        with open(SUBJECTS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def get_subjects():
    """获取现有学科列表"""
    try:
        with open(SUBJECTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_subjects(subjects):
    """保存学科列表"""
    with open(SUBJECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(subjects, f, ensure_ascii=False, indent=2)

def update_subject_index(subject_name, chapter_info):
    """更新特定学科的 index.json"""
    subject_dir = DATA_DIR / subject_name
    index_file = subject_dir / "index.json"
    
    if not index_file.exists():
        with open(index_file, 'w', encoding='utf-8') as f: json.dump([], f)
        
    with open(index_file, 'r', encoding='utf-8') as f:
        index = json.load(f)
    
    # 更新或添加章节
    existing_idx = -1
    for i, item in enumerate(index):
        if item['title'] == chapter_info['title']:
            existing_idx = i
            break
            
    if existing_idx != -1:
        # 删除旧文件，防止垃圾堆积
        old_file = subject_dir / index[existing_idx]['file']
        if old_file.exists() and old_file.name != chapter_info['file']:
            try: os.remove(old_file)
            except: pass
        index[existing_idx] = chapter_info
    else:
        index.append(chapter_info)
        
    # 章节排序 (按数字)
    def sort_key(item):
        import re
        nums = re.findall(r'\d+', item['title'])
        return int(nums[0]) if nums else 9999
    index.sort(key=sort_key)
    
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    return len(index)

def process_file_with_subject(source_path, subject_name):
    """
    核心逻辑：
    1. 读取 JSON
    2. 智能分章
    3. 存入 data/{学科名}/ 文件夹
    4. 更新该学科的 index.json
    5. 更新总 subjects.json
    """
    source_path = Path(str(source_path).strip('"').strip("'"))
    
    # 1. 读取内容
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
    except Exception as e:
        return False, f"JSON 读取失败: {e}"

    # 2. 提取题目
    all_questions = []
    if isinstance(content, dict):
        if "questions" in content and isinstance(content["questions"], list):
            all_questions = content["questions"]
        else:
            for val in content.values():
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict) and "question" in val[0]:
                    all_questions = val
                    break
    elif isinstance(content, list):
        all_questions = content

    if not all_questions:
        return False, "未找到题目数据"

    # 3. 准备学科目录
    subject_dir = DATA_DIR / subject_name
    if not subject_dir.exists():
        subject_dir.mkdir(parents=True, exist_ok=True)

    # 4. 智能分章
    chapters_map = {}
    for q in all_questions:
        c_name = q.get("chapter", "").strip()
        if not c_name: c_name = source_path.stem
        if c_name not in chapters_map: chapters_map[c_name] = []
        chapters_map[c_name].append(q)

    log_msgs = []
    base_time = int(time.time())

    # 5. 保存章节文件
    for idx, (chap_name, q_list) in enumerate(chapters_map.items()):
        new_filename = f"ch_{base_time}_{idx}.json"
        target_path = subject_dir / new_filename

        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(q_list, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_msgs.append(f"❌ {chap_name} 保存失败: {e}")
            continue

        # 更新学科内部索引
        chap_info = {
            "id": f"c_{base_time}_{idx}",
            "title": chap_name,
            "file": new_filename,
            "count": len(q_list),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        update_subject_index(subject_name, chap_info)
        log_msgs.append(f"✅ [{subject_name}] {chap_name} ({len(q_list)}题)")

    # 6. 更新总学科列表 (subjects.json)
    subjects = get_subjects()
    # 检查是否已有该学科
    sub_entry = next((s for s in subjects if s['name'] == subject_name), None)
    
    if not sub_entry:
        sub_entry = {
            "id": f"sub_{int(time.time())}",
            "name": subject_name,
            "dir": subject_name, # 文件夹名
            "created_at": time.strftime("%Y-%m-%d")
        }
        subjects.append(sub_entry)
    
    sub_entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_subjects(subjects)

    return True, "\n".join(log_msgs)


# --- GUI 界面 ---
def run_gui():
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext
        import tkinter.ttk as ttk
    except ImportError:
        print("未安装 Tkinter，无法启动图形界面。")
        return

    window = tk.Tk()
    window.title("题库导入助手 Pro (多学科版)")
    window.geometry("600x500")

    tk.Label(window, text="📚 全科刷题宝 - 题库管理", font=("Microsoft YaHei", 14, "bold")).pack(pady=15)
    
    # 学科选择区域
    frame_sub = tk.Frame(window)
    frame_sub.pack(pady=5)
    
    tk.Label(frame_sub, text="目标学科：", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
    
    # 获取现有学科供选择
    existing_subs = [s['name'] for s in get_subjects()]
    
    # 组合框 (既可以选，也可以自己输入)
    combo_sub = ttk.Combobox(frame_sub, values=existing_subs, width=20, font=("Microsoft YaHei", 10))
    combo_sub.pack(side=tk.LEFT, padx=5)
    if existing_subs:
        combo_sub.current(0)
    else:
        combo_sub.set("管理学") # 默认值
    
    tk.Label(window, text="提示：下拉选择现有学科，或直接输入新名称创建新学科", fg="#888", font=("Arial", 9)).pack(pady=2)

    log_box = scrolledtext.ScrolledText(window, height=12, font=("Consolas", 9))
    log_box.pack(padx=15, pady=10, fill=tk.BOTH, expand=True)

    def log(s):
        log_box.insert(tk.END, s + "\n")
        log_box.see(tk.END)

    def start_import():
        sub_name = combo_sub.get().strip()
        if not sub_name:
            messagebox.showwarning("提示", "必须填写一个学科名称！")
            return

        paths = filedialog.askopenfilenames(filetypes=[("JSON", "*.json")])
        if not paths: return
        
        for p in paths:
            log(f"正在读取: {os.path.basename(p)} ...")
            success, msg = process_file_with_subject(p, sub_name)
            log(msg)
            log("-" * 30)
        
        # 刷新下拉列表
        combo_sub['values'] = [s['name'] for s in get_subjects()]
        messagebox.showinfo("完成", f"成功导入到【{sub_name}】！\n请刷新网页查看。")

    btn = tk.Button(window, text="选择 JSON 文件并导入", command=start_import, bg="#007bff", fg="white", font=("Microsoft YaHei", 11, "bold"), height=2, width=25)
    btn.pack(pady=15)
    
    ensure_setup()
    window.mainloop()

if __name__ == "__main__":
    run_gui()