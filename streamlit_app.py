import streamlit as st
import subprocess
import re
import sys

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

def format_command_display(cmd, download_sections, youtube_url):
    """表示用にコマンドの引数を引用符で囲む"""
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
    return " ".join(cmd_display)

def main():
    st.title("YouTube動画ダウンローダー")
    st.markdown("---")
    
    # YouTubeのURL入力
    st.subheader("YouTubeのURL")
    youtube_url = st.text_input("YouTubeのURLを入力してください", placeholder="https://www.youtube.com/watch?v=...")
    
    # URL検証
    url_valid = True
    if youtube_url:
        if not validate_youtube_url(youtube_url):
            st.error("無効なYouTubeのURLです。正しいURLを入力してください。")
            url_valid = False
        else:
            st.success("有効なYouTubeのURLです。")
    
    # 時間入力
    st.subheader("ダウンロード区間")
    col1, col2 = st.columns(2)
    
    with col1:
        start_time = st.text_input("開始時間", placeholder="例: 00:00, 01:30, 01:22:33")
        start_time_valid = True
        if start_time:
            if not validate_time_format(start_time):
                st.error("無効な時間フォーマットです。00:00や01:22:33の形式で入力してください。")
                start_time_valid = False
            else:
                st.success("有効な時間フォーマットです。")
    
    with col2:
        end_time = st.text_input("終了時間", placeholder="例: 00:10, 02:30, 01:25:45")
        end_time_valid = True
        if end_time:
            if not validate_time_format(end_time):
                st.error("無効な時間フォーマットです。00:00や01:22:33の形式で入力してください。")
                end_time_valid = False
            else:
                st.success("有効な時間フォーマットです。")
    
    # すべての入力が有効かチェック
    all_valid = url_valid and start_time_valid and end_time_valid and youtube_url and start_time and end_time
    
    if all_valid:
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
        
        # コマンド表示
        st.subheader("実行するコマンド")
        formatted_cmd = format_command_display(cmd, download_sections, youtube_url)
        st.code(formatted_cmd, language="bash")
        
        # ダウンロードボタン
        if st.button("ダウンロード開始", type="primary"):
            with st.spinner("ダウンロード中..."):
                try:
                    # yt-dlpコマンドを実行
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    st.success("ダウンロードが完了しました！")
                    if result.stdout:
                        st.text_area("出力:", result.stdout, height=200)
                except subprocess.CalledProcessError as e:
                    st.error(f"エラーが発生しました: {e}")
                    if e.stderr:
                        st.text_area("エラー詳細:", e.stderr, height=200)
                except FileNotFoundError:
                    st.error("yt-dlpが見つかりません。yt-dlpがインストールされているか確認してください。")

if __name__ == "__main__":
    main()