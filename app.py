import subprocess
import sys
import re
import os
import tempfile
import shutil
import glob
import platform

def validate_time_format(time_str):
    """時間フォーマットを検証（00:00, 00:12, 01:22:33, 0000, 000010形式）"""
    # MM:SS または HH:MM:SS 形式
    colon_pattern = r'^\d{1,2}:\d{2}(:\d{2})?$'
    # MMSS または HHMMSS 形式（4桁または6桁）
    digit_pattern = r'^\d{4}$|^\d{6}$'
    
    return re.match(colon_pattern, time_str) is not None or re.match(digit_pattern, time_str) is not None

def normalize_time_format(time_str):
    """時間フォーマットを正規化（4桁・6桁をMM:SS・HH:MM:SS形式に変換）"""
    if re.match(r'^\d{4}$', time_str):
        # 4桁の場合：MMSS -> MM:SS
        return f"{time_str[:2]}:{time_str[2:]}"
    elif re.match(r'^\d{6}$', time_str):
        # 6桁の場合：HHMMSS -> HH:MM:SS
        return f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
    else:
        # すでに正しい形式の場合はそのまま返す
        return time_str

def get_unique_filename(base_path):
    """既存ファイルと重複しない一意のファイル名を生成"""
    if not os.path.exists(base_path):
        return base_path
    
    # ファイル名と拡張子を分離
    name, ext = os.path.splitext(base_path)
    counter = 2
    
    while os.path.exists(f"{name}_V{counter}{ext}"):
        counter += 1
    
    return f"{name}_V{counter}{ext}"

def validate_youtube_url(url):
    """YouTubeのURLを検証"""
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'https?://youtu\.be/[\w-]+',
        r'https?://(?:www\.)?youtube\.com/embed/[\w-]+',
        r'https?://(?:www\.)?youtube\.com/shorts/[\w-]+'
    ]
    return any(re.match(pattern, url) for pattern in youtube_patterns)

def main():
    print("YouTube動画ダウンローダー")
    print("=" * 30)
    
    # YouTubeのURL入力
    while True:
        youtube_url = input("YouTubeのURLを入力してください: ").strip()
        if validate_youtube_url(youtube_url):
            break
        print("無効なYouTubeのURLです。正しいURLを入力してください。")
    
    # ダウンロード区間の入力
    while True:
        start_time = input("開始時間を入力してください（例: 00:00, 01:30, 01:22:33, 0130, 012233、空欄で動画全体）: ").strip()
        if not start_time or validate_time_format(start_time):
            break
        print("無効な時間フォーマットです。00:00、01:22:33、0130、012233の形式で入力してください。")
    
    while True:
        end_time = input("終了時間を入力してください（例: 00:10, 02:30, 01:25:45, 0230, 012545、空欄で動画全体）: ").strip()
        if not end_time or validate_time_format(end_time):
            break
        print("無効な時間フォーマットです。00:00、01:22:33、0130、012233の形式で入力してください。")
    
    # 時間指定の確認
    if (start_time and not end_time) or (not start_time and end_time):
        print("開始時間と終了時間の両方を入力するか、両方とも空欄にしてください。")
        return
    
    # yt-dlpコマンドを構築
    cmd = [
        "yt-dlp",
        "-S", "codec:avc:aac,res:1080,fps:60,hdr:sdr"
    ]
    
    # Streamlitクラウド環境の検出
    is_streamlit_cloud = False
    try:
        is_streamlit_cloud = (
            "STREAMLIT_SHARING" in os.environ or 
            "streamlit" in os.environ.get("HOME", "").lower() or
            "appuser" in os.environ.get("HOME", "").lower() or
            os.path.exists("/home/appuser")
        )
    except Exception:
        pass
    
    # ローカル環境でのみクッキーオプションを追加
    if not is_streamlit_cloud:
        try:
            cmd.extend(["--cookies-from-browser", "chrome"])
        except Exception:
            pass
    
    # 時間指定がある場合のみセクションダウンロードを追加
    if start_time and end_time:
        # 時間を正規化してからダウンロードセクションの文字列を作成
        normalized_start = normalize_time_format(start_time)
        normalized_end = normalize_time_format(end_time)
        download_sections = f"*{normalized_start}-{normalized_end}"
        cmd.extend([
            "--download-sections", download_sections,
            "--force-keyframes-at-cuts"
        ])
        print(f"指定区間: {normalized_start} ～ {normalized_end}")
        
        # クラウド環境では警告を表示
        if is_streamlit_cloud:
            print("⚠️ クラウド環境ではffmpegが利用できないため、エラーが発生する可能性があります。")
    else:
        print("動画全体をダウンロードします")
    
    cmd.extend([
        "-f", "bv+ba",
        "-o", "%(title)s_%(height)s_%(fps)s_%(vcodec.:4)s_(%(id)s).%(ext)s",
        youtube_url
    ])
    
    print(f"\n実行するコマンド:")
    # 表示用にコマンドの引数を引用符で囲む
    cmd_display = []
    for arg in cmd:
        if arg == "codec:avc:aac,res:1080,fps:60,hdr:sdr":
            cmd_display.append(f'"{arg}"')
        elif arg == "bv+ba":
            cmd_display.append(f'"{arg}"')
        elif arg == "%(title)s_%(height)s_%(fps)s_%(vcodec.:4)s_(%(id)s).%(ext)s":
            cmd_display.append(f'"{arg}"')
        elif start_time and end_time and arg == download_sections:
            cmd_display.append(f'"{arg}"')
        elif arg == youtube_url:
            cmd_display.append(f'"{arg}"')
        else:
            cmd_display.append(arg)
    print(" ".join(cmd_display))
    print("\nダウンロードを開始します...")
    
    try:
        # 一意のファイル名生成のため、一時ディレクトリを使用
        temp_dir = tempfile.mkdtemp()
        temp_cmd = cmd.copy()
        
        # 一時ディレクトリに出力するように変更
        for i, arg in enumerate(temp_cmd):
            if arg == "-o":
                temp_cmd[i+1] = os.path.join(temp_dir, temp_cmd[i+1])
                break
        
        # yt-dlpコマンドを実行
        result = subprocess.run(temp_cmd, check=True, capture_output=True, text=True)
        print("ダウンロードが完了しました！")
        if result.stdout:
            print(f"出力: {result.stdout}")
        
        # 一時ディレクトリからダウンロードされたファイルを取得
        temp_files = glob.glob(os.path.join(temp_dir, "*.mp4"))
        
        if temp_files:
            # 最新のファイルを取得
            temp_file = temp_files[0]
            original_name = os.path.basename(temp_file)
            
            # 現在のディレクトリで一意のファイル名を生成
            final_path = get_unique_filename(original_name)
            
            # ファイルを現在のディレクトリにコピー
            shutil.move(temp_file, final_path)
            print(f"ファイルが保存されました: {final_path}")
            
            # 一時ディレクトリをクリーンアップ
            shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            # 一時ディレクトリをクリーンアップ
            shutil.rmtree(temp_dir, ignore_errors=True)
            print("ダウンロードに失敗しました。")
            
    except subprocess.CalledProcessError as e:
        print(f"エラーが発生しました: {e}")
        if e.stderr:
            print(f"エラー詳細: {e.stderr}")
        # 一時ディレクトリをクリーンアップ
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(1)
    except FileNotFoundError:
        print("yt-dlpが見つかりません。yt-dlpがインストールされているか確認してください。")
        # 一時ディレクトリをクリーンアップ
        if 'temp_dir' in locals():
            shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(1)

if __name__ == "__main__":
    main()