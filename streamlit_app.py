# -*- coding: utf-8 -*-
import streamlit as st
import yt_dlp
import os
import re
import tempfile
import threading
import time

def time_to_seconds(time_str):
    """MM:SS形式の時間を秒数に変換"""
    if ':' in time_str:
        parts = time_str.split(':')
        if len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
    return int(time_str)

def sanitize_filename(filename):
    """ファイル名から無効な文字を除去"""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def get_unique_filename(filename):
    """既存ファイルと重複しない一意のファイル名を生成"""
    if not os.path.exists(filename):
        return filename
    
    name, ext = os.path.splitext(filename)
    counter = 2
    
    while os.path.exists(f"{name}_v{counter}{ext}"):
        counter += 1
    
    return f"{name}_v{counter}{ext}"

def parse_time_range(time_input):
    """時間範囲を解析する（複数形式対応）"""
    if not time_input.strip():
        return None, None
    
    # 0429-0600形式の検出
    if '-' in time_input and ':' not in time_input:
        parts = time_input.split('-')
        if len(parts) == 2:
            start_str, end_str = parts
            # 4桁の数字をMM:SS形式に変換
            if len(start_str) == 4 and start_str.isdigit():
                start_time = f"{start_str[:2]}:{start_str[2:]}"
            else:
                start_time = start_str
            if len(end_str) == 4 and end_str.isdigit():
                end_time = f"{end_str[:2]}:{end_str[2:]}"
            else:
                end_time = end_str
            return start_time, end_time
    
    # MM:SS-MM:SS形式の検出
    elif '-' in time_input and ':' in time_input:
        parts = time_input.split('-')
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
    
    return None, None

def download_youtube_section(url, time_range, browser_choice=None, progress_callback=None, status_callback=None):
    """
    YouTubeの指定された時間範囲をダウンロードする
    """
    
    def progress_hook(d):
        """yt-dlpのダウンロード進捗フック"""
        if status_callback:
            if d['status'] == 'downloading':
                # ダウンロード中の詳細情報
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                
                if total > 0:
                    percent = (downloaded / total) * 100
                    if progress_callback:
                        progress_callback(percent / 100)
                    
                    # 速度とETAの表示
                    speed_str = f"{speed/1024/1024:.1f} MB/s" if speed else "計算中..."
                    eta_str = f"{eta}秒" if eta else "計算中..."
                    size_str = f"{downloaded/1024/1024:.1f}/{total/1024/1024:.1f} MB"
                    
                    status_callback(f"📥 ダウンロード中: {percent:.1f}% | {size_str} | 速度: {speed_str} | 残り時間: {eta_str}")
                else:
                    status_callback("📥 ダウンロード中... (サイズ計算中)")
                    
            elif d['status'] == 'finished':
                status_callback(f"✅ ダウンロード完了: {os.path.basename(d['filename'])}")
                if progress_callback:
                    progress_callback(1.0)
                    
            elif d['status'] == 'error':
                status_callback(f"❌ エラー: {d.get('error', '不明なエラー')}")
    
    # yt-dlpの設定
    ydl_opts = {
        'noplaylist': True,
        'extract_flat': False,
        'progress_hooks': [progress_hook],
    }
    
    # ブラウザからクッキーを取得
    if browser_choice and browser_choice != "使用しない":
        ydl_opts['cookiesfrombrowser'] = (browser_choice.lower(), None, None, None)
    
    try:
        if status_callback:
            status_callback("🔍 動画情報を取得中...")
        
        # 動画の情報を取得
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = sanitize_filename(info.get('title', 'video'))
            duration = info.get('duration', 0)
            
        if status_callback:
            duration_str = f"{duration//60}:{duration%60:02d}" if duration else "不明"
            status_callback(f"📹 動画情報取得完了: {title} (長さ: {duration_str})")
        
        # 時間範囲の解析
        start_time, end_time = parse_time_range(time_range)
        
        # 時間指定があるかチェック
        if start_time and end_time:
            # ファイル名を生成（時間範囲付き）
            start_formatted = start_time.replace(':', '_')
            end_formatted = end_time.replace(':', '_')
            filename = f"{title}_{start_formatted}-{end_formatted}.mp4"
            filename = get_unique_filename(filename)
            
            # 時間を秒数に変換
            start_seconds = time_to_seconds(start_time)
            end_seconds = time_to_seconds(end_time)
            
            if status_callback:
                status_callback(f"⚙️ ダウンロード設定中... (時間範囲: {start_time}-{end_time})")
            
            # 指定時間範囲のみダウンロード
            download_opts = {
                'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[ext=mp4]',
                'outtmpl': filename,
                'noplaylist': True,
                'download_ranges': yt_dlp.utils.download_range_func(None, [(start_seconds, end_seconds)]),
                'progress_hooks': [progress_hook],
            }
            
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([url])
        else:
            # ファイル名を生成（全体ダウンロード）
            filename = f"{title}.mp4"
            filename = get_unique_filename(filename)
            
            if status_callback:
                status_callback("⚙️ ダウンロード設定中... (動画全体)")
            
            # 全体ダウンロード設定（分離音声動画で最高品質）
            download_opts = {
                'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[ext=mp4]',
                'outtmpl': filename,
                'noplaylist': True,
                'progress_hooks': [progress_hook],
            }
            
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([url])
        
        return filename, True
        
    except Exception as e:
        return f"エラーが発生しました: {e}", False

# Streamlit UI
def main():
    st.set_page_config(
        page_title="YouTube区間ダウンローダー",
        page_icon="🎬",
        layout="wide"
    )
    
    st.title("🎬 YouTube区間ダウンローダー")
    st.markdown("YouTubeの動画から指定した時間範囲をダウンロードできます")
    
    # セッション状態の初期化
    if 'downloaded_file' not in st.session_state:
        st.session_state.downloaded_file = None
    if 'download_filename' not in st.session_state:
        st.session_state.download_filename = None
    if 'is_downloading' not in st.session_state:
        st.session_state.is_downloading = False
    
    
    # URL入力
    st.subheader("🎬 動画設定")
    url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...",
        help="ダウンロードしたいYouTube動画のURLを入力してください"
    )
    
    # 時間指定
    time_range = st.text_input(
        "時間範囲",
        placeholder="例: 0430-0600 または 4:30-6:00 (空欄で動画全体)",
        help="MMSS-MMSS形式（0430-0600）またはMM:SS-MM:SS形式（4:30-6:00）で入力"
    )
    
    # ブラウザ選択（Bot対策）
    st.subheader("🍪 Bot対策設定")
    browser_options = ["使用しない", "Chrome", "Firefox", "Safari", "Edge"]
    browser_choice = st.selectbox(
        "ブラウザからクッキーを取得",
        browser_options,
        help="YouTubeでBot判定される場合は、普段使用しているブラウザを選択してください"
    )
    st.session_state.browser_choice = browser_choice
    
    if browser_choice != "使用しない":
        st.info(f"💡 {browser_choice}ブラウザのクッキーを使用してBot判定を回避します")
    
    # ダウンロードボタン
    if st.button("📥 ダウンロード開始", type="primary", disabled=st.session_state.is_downloading):
        if not url:
            st.error("YouTube URLを入力してください")
            st.stop()
        
        # 時間指定の検証
        if time_range.strip():
            try:
                # 時間範囲解析のテスト
                def parse_time_range_test(time_input):
                    if not time_input.strip():
                        return None, None
                    
                    # 0429-0600形式の検出
                    if '-' in time_input and ':' not in time_input:
                        parts = time_input.split('-')
                        if len(parts) == 2:
                            start_str, end_str = parts
                            if len(start_str) == 4 and start_str.isdigit():
                                start_time = f"{start_str[:2]}:{start_str[2:]}"
                            else:
                                start_time = start_str
                            if len(end_str) == 4 and end_str.isdigit():
                                end_time = f"{end_str[:2]}:{end_str[2:]}"
                            else:
                                end_time = end_str
                            return start_time, end_time
                    
                    # MM:SS-MM:SS形式の検出
                    elif '-' in time_input and ':' in time_input:
                        parts = time_input.split('-')
                        if len(parts) == 2:
                            return parts[0].strip(), parts[1].strip()
                    
                    return None, None
                
                test_start, test_end = parse_time_range_test(time_range)
                if not test_start or not test_end:
                    st.error("時間範囲の形式が正しくありません。例: 0430-0600 または 4:30-6:00")
                    st.stop()
            except:
                st.error("時間範囲の形式が正しくありません。例: 0430-0600 または 4:30-6:00")
                st.stop()
        
        # ダウンロード開始
        st.session_state.is_downloading = True
        st.session_state.downloaded_file = None
        st.session_state.download_filename = None
        st.rerun()
    
    # ダウンロード処理の実行
    if st.session_state.is_downloading:
        # プログレスバーとステータス表示
        progress_bar = st.progress(0)
        status_text = st.empty()
        detail_text = st.empty()
        
        # リアルタイム進捗更新用のプレースホルダー
        progress_placeholder = st.empty()
        
        try:
            current_progress = [0.0]  # リストで包んで参照を維持
            
            def update_progress(percent):
                current_progress[0] = percent
                # スムーズなアニメーション
                for i in range(int(current_progress[0] * 100), int(percent * 100) + 1):
                    progress_bar.progress(i / 100)
                    time.sleep(0.01)  # 短い遅延でスムーズに
            
            def update_status(message):
                status_text.text(message)
                # 詳細情報を分離して表示
                if "📥 ダウンロード中:" in message:
                    parts = message.split(" | ")
                    if len(parts) > 1:
                        detail_text.text(" | ".join(parts[1:]))
                else:
                    detail_text.text("")
            
            # ダウンロード実行
            filename, success = download_youtube_section(
                url, time_range, st.session_state.get('browser_choice', None),
                progress_callback=update_progress,
                status_callback=update_status
            )
            
            if success:
                progress_bar.progress(1.0)
                status_text.text("🎉 ダウンロード完了!")
                detail_text.text("")
                
                # セッション状態に保存
                if os.path.exists(filename):
                    with open(filename, "rb") as file:
                        st.session_state.downloaded_file = file.read()
                    st.session_state.download_filename = os.path.basename(filename)
                    st.success(f"✅ {os.path.basename(filename)} の準備ができました！")
                    st.balloons()  # 成功時にアニメーション
                else:
                    st.error("ファイルが見つかりません")
            else:
                st.error(filename)  # エラーメッセージ
                
        except Exception as e:
            st.error(f"予期しないエラーが発生しました: {e}")
        finally:
            st.session_state.is_downloading = False
            st.rerun()
    
    # ダウンロード済みファイルがある場合は常にダウンロードボタンを表示
    if st.session_state.downloaded_file and st.session_state.download_filename:
        st.divider()
        st.subheader("📁 ダウンロード済みファイル")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"📄 ファイル: {st.session_state.download_filename}")
        with col2:
            st.download_button(
                label="💾 ダウンロード",
                data=st.session_state.downloaded_file,
                file_name=st.session_state.download_filename,
                mime="video/mp4",
                type="primary"
            )
        
        # クリアボタン
        if st.button("🗑️ ファイルをクリア", help="メモリからファイルを削除します"):
            st.session_state.downloaded_file = None
            st.session_state.download_filename = None
            st.rerun()
    
    # 使用方法の説明
    with st.expander("📖 使用方法"):
        st.markdown("""
        ### 時間形式について
        - **MMSS-MMSS形式**: `0430-0600` (4分30秒から6分まで)
        - **MM:SS-MM:SS形式**: `4:30-6:00` (同上)
        - **空欄**: 動画全体をダウンロード
        - 両方の形式に対応しています
        
        ### ダウンロードについて
        - 最大1080pの高画質でダウンロードします
        - 指定時間範囲のみをダウンロードするため高速です
        - ダウンロード完了後、「ファイルをダウンロード」ボタンから保存先を選択できます
        
        ### Bot対策について
        - YouTubeで「Sign in to confirm you're not a bot」エラーが出る場合
        - 普段YouTubeを使用しているブラウザを選択してください
        - ブラウザのクッキーが自動的に使用され、Bot判定を回避できます
        """)

if __name__ == "__main__":
    main()