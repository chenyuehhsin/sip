import subprocess
import sys
import os

def run_step(script_name):
    print(f"\n=========================================", flush=True)
    print(f"📦 正在執行: {script_name}...", flush=True)
    print(f"=========================================", flush=True)
    
    script_path = os.path.join("scripts", script_name)
    if not os.path.exists(script_path):
        print(f"❌ 錯誤：找不到腳本 {script_path}", flush=True)
        return False
        
    try:
        # 使用 sys.executable 確保使用與目前相同路徑的 Python 解譯器
        subprocess.run([sys.executable, script_path], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 執行失敗：{script_name} 發生錯誤 (Exit Code: {e.returncode})", flush=True)
        return False

def main():
    print("🚀 開始執行 [SIP 智慧導航圖資自動化整合管線]...", flush=True)
    
    # 依序執行資料整合腳本
    steps = [
        "1_svg_parser.py",
        "enrich_pois.py",
        "2_knn_recommender.py",
        "3_merge_connections.py",
        "4_campus_features_parser.py"
    ]
    
    for step in steps:
        success = run_step(step)
        if not success:
            print("\n🛑 管線執行中斷！請修正上述步驟的錯誤後再重試。", flush=True)
            sys.exit(1)
            
    print("\n🎉 =========================================", flush=True)
    print("   🌟 所有圖資與連線整合管線執行成功！ 🌟", flush=True)
    print("   您的 final_connections.json 與圖資已全部更新完畢。", flush=True)
    print("=============================================\n", flush=True)
    print("💡 提示: 您現在可以重新整理網頁，或啟動後端觀看最新連線與 2.5D 透視效果！", flush=True)

if __name__ == "__main__":
    main()
