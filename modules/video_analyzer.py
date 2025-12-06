"""
動画分析モジュール
"""
from typing import Dict, Any, List
import cv2
import numpy as np
from moviepy.editor import VideoFileClip
import io
import tempfile
import os

def download_youtube_video(url: str, max_duration: int = 60) -> bytes:
    """
    YouTube動画をダウンロード
    
    Args:
        url: YouTube URL
        max_duration: 最大ダウンロード時間（秒）
        
    Returns:
        動画データ（バイト列）
    """
    try:
        import yt_dlp
        
        # 一時ファイルパス
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            tmp_path = tmp_file.name
        
        # yt-dlp設定
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': tmp_path,
            'quiet': True,
            'no_warnings': True,
        }
        
        # ダウンロード
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # ファイルを読み込み
        with open(tmp_path, 'rb') as f:
            video_data = f.read()
        
        # クリーンアップ
        os.unlink(tmp_path)
        
        return video_data
    except ImportError:
        print("yt-dlpがインストールされていません: pip install yt-dlp")
        return None
    except Exception as e:
        print(f"YouTube動画ダウンロードエラー: {str(e)}")
        return None

def extract_frames_from_video(video_data: bytes, interval: int = 1, 
                              max_duration: int = 60) -> List[tuple]:
    """
    動画からフレームを抽出
    
    Args:
        video_data: 動画データ
        interval: フレーム抽出間隔（秒）
        max_duration: 最大処理時間（秒）
        
    Returns:
        (タイムスタンプ, 画像データ)のリスト
    """
    frames = []
    
    try:
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            tmp_file.write(video_data)
            tmp_path = tmp_file.name
        
        # OpenCVで動画を読み込み
        cap = cv2.VideoCapture(tmp_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        # 最大時間でクリップ
        process_duration = min(duration, max_duration)
        frame_interval = int(fps * interval)
        
        frame_count = 0
        while cap.isOpened() and len(frames) < process_duration:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 指定間隔でフレームを抽出
            if frame_count % frame_interval == 0:
                timestamp = frame_count / fps
                
                # フレームをJPEGに変換
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                
                frames.append((timestamp, frame_bytes))
            
            frame_count += 1
        
        cap.release()
        
        # 一時ファイルを削除
        os.unlink(tmp_path)
        
    except Exception as e:
        print(f"フレーム抽出エラー: {str(e)}")
    
    return frames

def extract_audio_from_video(video_data: bytes) -> bytes:
    """
    動画から音声を抽出
    
    Args:
        video_data: 動画データ
        
    Returns:
        音声データ（MP3）
    """
    try:
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_video:
            tmp_video.write(video_data)
            tmp_video_path = tmp_video.name
        
        # MoviePyで音声抽出
        video = VideoFileClip(tmp_video_path)
        
        # 音声を一時ファイルに保存
        tmp_audio_path = tmp_video_path.replace('.mp4', '.mp3')
        video.audio.write_audiofile(tmp_audio_path, logger=None)
        
        # 音声データを読み込み
        with open(tmp_audio_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        # クリーンアップ
        video.close()
        os.unlink(tmp_video_path)
        os.unlink(tmp_audio_path)
        
        return audio_data
    except Exception as e:
        print(f"音声抽出エラー: {str(e)}")
        return b""

def analyze_video_content(ai_handler, video_data: bytes, system_prompt: str,
                         criteria_sections: list, additional_context: str = "") -> Dict[str, Any]:
    """
    動画を分析
    
    Args:
        ai_handler: AIハンドラーインスタンス
        video_data: 動画データ
        system_prompt: システムプロンプト
        criteria_sections: 適用する診断基準セクション
        additional_context: 追加の参考情報（企業情報、補足情報など）
        
    Returns:
        分析結果
    """
    # フレーム抽出（1秒ごと、最大60秒）
    frames = extract_frames_from_video(video_data, interval=1, max_duration=60)
    
    if not frames:
        return {
            "error": "フレーム抽出失敗",
            "details": "動画からフレームを抽出できませんでした"
        }
    
    # 代表的なフレームを分析（最初、中間、最後）
    representative_indices = [0, len(frames) // 2, len(frames) - 1]
    frame_analyses = []
    
    for idx in representative_indices:
        if idx < len(frames):
            timestamp, frame_data = frames[idx]
            
            frame_prompt = f"""
【分析対象】
動画のフレーム（タイムスタンプ: {timestamp:.1f}秒）

【適用する診断基準】
{', '.join(criteria_sections)}

このフレームのビジュアル要素とテキストを分析してください。
"""
            
            # 追加の参考情報があれば追加
            if additional_context:
                frame_prompt += f"\n\n【参考情報】\n{additional_context}\n※上記の参考情報も考慮して解析してください。"
            
            try:
                frame_result = ai_handler.analyze_image(system_prompt, frame_prompt, frame_data)
                frame_result['timestamp'] = timestamp
                frame_analyses.append(frame_result)
            except Exception as e:
                print(f"フレーム分析エラー (t={timestamp}): {str(e)}")
    
    # 全フレーム分析結果を統合
    all_violations = []
    all_recommendations = []
    
    for analysis in frame_analyses:
        if "violations" in analysis:
            for v in analysis["violations"]:
                v['timestamp'] = analysis.get('timestamp', 0)
                all_violations.append(v)
        if "recommendations" in analysis:
            all_recommendations.extend(analysis.get("recommendations", []))
    
    # 統合結果を作成
    integrated_result = {
        "overall_risk": "Medium Risk",  # デフォルト
        "score": 50,
        "violations": all_violations,
        "recommendations": all_recommendations,
        "summary": f"{len(frames)}フレームを分析。{len(all_violations)}件の問題を検出。",
        "frame_count": len(frames),
        "analyzed_frames": len(frame_analyses)
    }
    
    return integrated_result

def get_video_info(video_data: bytes) -> Dict[str, Any]:
    """
    動画の基本情報を取得
    
    Args:
        video_data: 動画データ
        
    Returns:
        動画情報
    """
    try:
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            tmp_file.write(video_data)
            tmp_path = tmp_file.name
        
        # OpenCVで動画情報取得
        cap = cv2.VideoCapture(tmp_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        
        cap.release()
        os.unlink(tmp_path)
        
        return {
            "duration_seconds": duration,
            "fps": fps,
            "total_frames": total_frames,
            "width": width,
            "height": height,
            "size_mb": len(video_data) / (1024 * 1024)
        }
    except Exception as e:
        return {
            "error": f"動画情報の取得に失敗: {str(e)}"
        }
