import json
import os

print("🛠️ 開始執行 [步驟三]: 人機協作資料融合器 (Merge Connections)...")

# ==========================================
# 1. 載入檔案 (草稿與人類補丁)
# ==========================================
try:
    with open('data/draft_connection.json', 'r', encoding='utf-8') as f:
        draft_connections = json.load(f)
        
    with open('data/connection_overrides.json', 'r', encoding='utf-8') as f:
        overrides = json.load(f)
except FileNotFoundError as e:
    print(f"❌ 錯誤：找不到檔案 {e.filename}。請確認已執行步驟二，並已建立 overrides 檔案。")
    exit(1)

# 深拷貝一份草稿，準備進行修改
final_connections = {k: list(v) for k, v in draft_connections.items()}

# ==========================================
# 2. 執行覆寫邏輯：✂️ 移除 (Remove)
# ==========================================
remove_rules = overrides.get("remove", [])
remove_count = 0

for rule in remove_rules:
    poi = rule.get("poi")
    target = rule.get("target")
    
    if poi in final_connections and target in final_connections[poi]:
        final_connections[poi].remove(target)
        remove_count += 1
        print(f"  ✂️  人工移除: 取消 {poi} ➔ {target} 的連線")

# ==========================================
# 3. 執行覆寫邏輯：🔗 新增 (Add)
# ==========================================
add_rules = overrides.get("add", [])
add_count = 0

for rule in add_rules:
    poi = rule.get("poi")
    target = rule.get("target")
    
    # 如果這個 POI 原本不在清單裡，幫它建一個空陣列
    if poi not in final_connections:
        final_connections[poi] = []
        
    # 避免重複加入相同的連線
    if target not in final_connections[poi]:
        final_connections[poi].append(target)
        add_count += 1
        print(f"  🔗 人工新增: 強制建立 {poi} ➔ {target} 的連線")

# ==========================================
# 4. 輸出最終 Ground Truth 檔案
# ==========================================
with open('data/final_connections.json', 'w', encoding='utf-8') as f:
    json.dump(final_connections, f, indent=2, ensure_ascii=False)

print("\n✅ [步驟三] 執行完畢！")
print(f"📊 統計: 總計套用 {remove_count} 筆移除規則、{add_count} 筆新增規則。")
print(f"📁 最終連線 Ground Truth 已成功寫入 data/final_connections.json！")