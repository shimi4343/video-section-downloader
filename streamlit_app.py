import streamlit as st
import subprocess
import re
import sys
import os
import glob
import tempfile
import shutil

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

def validate_youtube_url(url):
    """YouTubeのURLを検証"""
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'https?://youtu\.be/[\w-]+',
        r'https?://(?:www\.)?youtube\.com/embed/[\w-]+',
        r'https?://(?:www\.)?youtube\.com/shorts/[\w-]+'
    ]
    return any(re.match(pattern, url) for pattern in youtube_patterns)

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

def format_command_display(cmd, download_sections, youtube_url):
    """表示用にコマンドの引数を引用符で囲む"""
    cmd_display = []
    for arg in cmd:
        if arg == "codec:avc:aac,res:1080,fps:60,hdr:sdr":
            cmd_display.append(f'"{arg}"')
        elif arg == "bv+ba":
            cmd_display.append(f'"{arg}"')
        elif "%(title)s_%(height)s_%(fps)s_%(vcodec.:4)s_(%(id)s)" in arg:
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
    
    # セッション状態の初期化
    if 'downloaded_file_path' not in st.session_state:
        st.session_state.downloaded_file_path = None
    if 'downloaded_file_data' not in st.session_state:
        st.session_state.downloaded_file_data = None
    if 'downloaded_file_name' not in st.session_state:
        st.session_state.downloaded_file_name = None
    if 'download_clicked' not in st.session_state:
        st.session_state.download_clicked = False
    
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
        start_time = st.text_input("開始時間", placeholder="例: 00:00, 01:30, 01:22:33, 0130, 012233（空欄で動画全体）")
        start_time_valid = True
        if start_time:
            if not validate_time_format(start_time):
                st.error("無効な時間フォーマットです。00:00、01:22:33、0130、012233の形式で入力してください。")
                start_time_valid = False
            else:
                normalized_start = normalize_time_format(start_time)
                st.success(f"有効な時間フォーマットです。({normalized_start})")
    
    with col2:
        end_time = st.text_input("終了時間", placeholder="例: 00:10, 02:30, 01:25:45, 0230, 012545（空欄で動画全体）")
        end_time_valid = True
        if end_time:
            if not validate_time_format(end_time):
                st.error("無効な時間フォーマットです。00:00、01:22:33、0130、012233の形式で入力してください。")
                end_time_valid = False
            else:
                normalized_end = normalize_time_format(end_time)
                st.success(f"有効な時間フォーマットです。({normalized_end})")
    
    # 時間指定の状態を表示
    if not start_time.strip() and not end_time.strip():
        st.info("💡 時間指定なし：動画全体をダウンロードします")
    elif start_time.strip() and end_time.strip():
        if start_time_valid and end_time_valid:
            st.info(f"💡 指定区間：{normalize_time_format(start_time) if start_time else ''} ～ {normalize_time_format(end_time) if end_time else ''}")
    else:
        if start_time.strip() or end_time.strip():
            st.warning("⚠️ 開始時間と終了時間の両方を入力するか、両方とも空欄にしてください")
    
    # すべての入力が有効かチェック
    time_input_valid = True
    if (start_time.strip() and not end_time.strip()) or (not start_time.strip() and end_time.strip()):
        time_input_valid = False
    
    all_valid = url_valid and start_time_valid and end_time_valid and time_input_valid and youtube_url
    
    if all_valid:
        # yt-dlpコマンドを構築
        cmd = [
            "yt-dlp",
            "--cookies-from-browser", "chrome",
            "-S", "codec:avc:aac,res:1080,fps:60,hdr:sdr"
        ]
        
        # 時間指定がある場合のみセクションダウンロードを追加
        if start_time.strip() and end_time.strip():
            # 時間を正規化してからダウンロードセクションの文字列を作成
            normalized_start = normalize_time_format(start_time)
            normalized_end = normalize_time_format(end_time)
            download_sections = f"*{normalized_start}-{normalized_end}"
            cmd.extend([
                "--download-sections", download_sections,
                "--force-keyframes-at-cuts"
            ])
        
        cmd.extend([
            "-f", "bv+ba",
            "-o", "%(title)s_%(height)s_%(fps)s_%(vcodec.:4)s_(%(id)s).%(ext)s",
            youtube_url
        ])
        
        # コマンド表示
        st.subheader("実行するコマンド")
        download_sections_for_display = f"*{normalized_start}-{normalized_end}" if start_time.strip() and end_time.strip() else ""
        formatted_cmd = format_command_display(cmd, download_sections_for_display, youtube_url)
        st.code(formatted_cmd, language="bash")
        
        # ダウンロードボタン
        if st.button("ダウンロード開始", type="primary"):
            with st.spinner("ダウンロード中..."):
                try:
                    # 一意のファイル名生成のため、yt-dlpコマンドを調整
                    temp_dir = tempfile.mkdtemp()
                    temp_cmd = cmd.copy()
                    
                    # 一時ディレクトリに出力するように変更
                    for i, arg in enumerate(temp_cmd):
                        if arg == "-o":
                            temp_cmd[i+1] = os.path.join(temp_dir, temp_cmd[i+1])
                            break
                    
                    # yt-dlpコマンドを実行
                    result = subprocess.run(temp_cmd, check=True, capture_output=True, text=True)
                    st.success("ダウンロードが完了しました！")
                    if result.stdout:
                        st.text_area("出力:", result.stdout, height=200)
                    
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
                        
                        # ファイルをバイナリで読み込み
                        with open(final_path, "rb") as f:
                            file_data = f.read()
                        
                        # セッション状態に保存
                        st.session_state.downloaded_file_path = final_path
                        st.session_state.downloaded_file_data = file_data
                        st.session_state.downloaded_file_name = os.path.basename(final_path)
                        
                        # 一時ディレクトリをクリーンアップ
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    else:
                        # 一時ディレクトリをクリーンアップ
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        st.error("ダウンロードに失敗しました。")
                        
                except subprocess.CalledProcessError as e:
                    st.error(f"エラーが発生しました: {e}")
                    if e.stderr:
                        st.text_area("エラー詳細:", e.stderr, height=200)
                    # 一時ディレクトリをクリーンアップ
                    if 'temp_dir' in locals():
                        shutil.rmtree(temp_dir, ignore_errors=True)
                except FileNotFoundError:
                    st.error("yt-dlpが見つかりません。yt-dlpがインストールされているか確認してください。")
                    # 一時ディレクトリをクリーンアップ
                    if 'temp_dir' in locals():
                        shutil.rmtree(temp_dir, ignore_errors=True)
    
    # ダウンロードファイルがある場合、ダウンロードボタンを表示
    if st.session_state.downloaded_file_data is not None:
        st.markdown("---")
        st.subheader("📥 ファイルダウンロード")
        
        # ダウンロードボタン（クリック時に自動削除）
        download_button = st.download_button(
            label="💾 ファイルをダウンロード",
            data=st.session_state.downloaded_file_data,
            file_name=st.session_state.downloaded_file_name,
            mime="video/mp4",
            type="primary",
            on_click=lambda: cleanup_server_file()
        )

def cleanup_server_file():
    """サーバー上のファイルとセッション状態をクリーンアップ"""
    if st.session_state.downloaded_file_path and os.path.exists(st.session_state.downloaded_file_path):
        try:
            os.remove(st.session_state.downloaded_file_path)
        except Exception:
            pass  # エラーは無視
    
    # セッション状態をクリア
    st.session_state.downloaded_file_path = None
    st.session_state.downloaded_file_data = None
    st.session_state.downloaded_file_name = None

if __name__ == "__main__":
    main()