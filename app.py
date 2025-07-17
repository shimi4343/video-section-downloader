# -*- coding: utf-8 -*-
import yt_dlp
import os
import re
import subprocess
import tempfile

def download_youtube_section(url, start_time, end_time):
    """
    YouTubeの指定された時間範囲をダウンロードする
    
    Args:
        url (str): YouTube URL
        start_time (str): 開始時間 (MM:SS形式、空欄の場合は動画全体)
        end_time (str): 終了時間 (MM:SS形式、空欄の場合は動画全体)
    """
    
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
    
    # yt-dlpの設定
    ydl_opts = {
        'noplaylist': True,
        'extract_flat': False,
    }
    
    try:
        # 動画の情報を取得
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = sanitize_filename(info.get('title', 'video'))
        
        # 時間指定があるかチェック
        if start_time.strip() and end_time.strip():
            # ファイル名を生成（時間範囲付き）
            start_formatted = start_time.replace(':', '_')
            end_formatted = end_time.replace(':', '_')
            filename = f"{title}_{start_formatted}-{end_formatted}.mp4"
            filename = get_unique_filename(filename)
            
            # 時間を秒数に変換
            start_seconds = time_to_seconds(start_time)
            end_seconds = time_to_seconds(end_time)
            
            # 指定時間範囲のみダウンロード
            download_opts = {
                'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[ext=mp4]',
                'outtmpl': filename,
                'noplaylist': True,
                'download_ranges': yt_dlp.utils.download_range_func(None, [(start_seconds, end_seconds)]),
            }
            
            print(f"指定時間範囲({start_time}-{end_time})をダウンロード中...")
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([url])
        else:
            # ファイル名を生成（全体ダウンロード）
            filename = f"{title}.mp4"
            filename = get_unique_filename(filename)
            
            # 全体ダウンロード設定（分離音声動画で最高品質）
            download_opts = {
                'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[ext=mp4]',
                'outtmpl': filename,
                'noplaylist': True,
            }
            
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([url])
        
        print(f"ダウンロード完了: {filename}")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")

def main():
    """メイン関数"""
    print("YouTube区間ダウンローダー")
    print("時間形式: MM:SS (例: 01:30)")
    print("※開始時間・終了時間を空欄にすると動画全体をダウンロードします")
    
    url = input("YouTube URL: ")
    start_time = input("開始時間 (MM:SS、空欄で全体): ")
    end_time = input("終了時間 (MM:SS、空欄で全体): ")
    
    download_youtube_section(url, start_time, end_time)

if __name__ == "__main__":
    main()