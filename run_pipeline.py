import subprocess
import sys
import os

def run_step(script_name):
    print(f"\n=========================================")
    print(f"📦 正在執行: {script_name}...")
    print(f"=========================================")
    
    script_path = os.path.join("scripts", script_name)
    if not os.path.exists(script_path):
        print(f"❌ 錯誤：找不到腳本 {script_path}")
        return False
        
    try:
        # 使用 sys.executable 確保使用與目前相同路徑的 Python 解譯器
        subprocess.run([sys.executable, script_path], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 執行失敗：{script_name} 發生錯誤 (Exit Code: {e.returncode})")
        return False

def main():
    print("🚀 開始執行 [SIP 智慧導航圖資自動化整合管線]...")
    
    # 依序執行的三部曲腳本
    steps = [
        "1_svg_parser.py",
        "2_knn_recommender.py",
        "3_merge_connections.py"
    ]
    
    for step in steps:
        success = run_step(step)
        if not success:
            print("\n🛑 管線執行中斷！請修正上述步驟的錯誤後再重試。")
            sys.exit(1)
            
    print("\n🎉 =========================================")
    print("   🌟 所有圖資與連線整合管線執行成功！ 🌟")
    print("   您的 final_connections.json 與圖資已全部更新完畢。")
    print("=============================================\n")
    print("💡 提示: 您現在可以重新整理網頁，或啟動後端觀看最新連線與 2.5D 透視效果！")

if __name__ == "__main__":
    main()