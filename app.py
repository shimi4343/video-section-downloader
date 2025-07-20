import subprocess
import sys
import re

def validate_time_format(time_str):
    """時間フォーマットを検証（00:00, 00:12, 01:22:33形式）"""
    pattern = r'^\d{1,2}:\d{2}(:\d{2})?$'
    return re.match(pattern, time_str) is not None

def validate_youtube_url(url):
    """YouTubeのURLを検証"""
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'https?://youtu\.be/[\w-]+',
        r'https?://(?:www\.)?youtube\.com/embed/[\w-]+'
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
        start_time = input("開始時間を入力してください（例: 00:00, 01:30, 01:22:33）: ").strip()
        if validate_time_format(start_time):
            break
        print("無効な時間フォーマットです。00:00や01:22:33の形式で入力してください。")
    
    while True:
        end_time = input("終了時間を入力してください（例: 00:10, 02:30, 01:25:45）: ").strip()
        if validate_time_format(end_time):
            break
        print("無効な時間フォーマットです。00:00や01:22:33の形式で入力してください。")
    
    # ダウンロードセクションの文字列を作成
    download_sections = f"*{start_time}-{end_time}"
    
    # yt-dlpコマンドを構築
    cmd = [
        "yt-dlp",
        "--cookies-from-browser", "chrome",
        "-S", "codec:avc:aac,res:1080,fps:60,hdr:sdr",
        "--download-sections", download_sections,
        "--force-keyframes-at-cuts",
        "-f", "bv+ba",
        "-o", "%(title)s_%(height)s_%(fps)s_%(vcodec.:4)s_(%(id)s).%(ext)s",
        youtube_url
    ]
    
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
        elif arg == download_sections:
            cmd_display.append(f'"{arg}"')
        elif arg == youtube_url:
            cmd_display.append(f'"{arg}"')
        else:
            cmd_display.append(arg)
    print(" ".join(cmd_display))
    print("\nダウンロードを開始します...")
    
    try:
        # yt-dlpコマンドを実行
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("ダウンロードが完了しました！")
        if result.stdout:
            print(f"出力: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"エラーが発生しました: {e}")
        if e.stderr:
            print(f"エラー詳細: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("yt-dlpが見つかりません。yt-dlpがインストールされているか確認してください。")
        sys.exit(1)

if __name__ == "__main__":
    main()