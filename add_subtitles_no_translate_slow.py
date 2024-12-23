import os
import subprocess
import whisper
from moviepy.editor import VideoFileClip

# 初始化模型
model = whisper.load_model("base")  # 可以改为 "small" 或其他模型

def check_ffmpeg():
    """检查 FFmpeg 是否可用"""
    try:
        result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg 无法运行: {result.stderr}")
        print("FFmpeg 测试通过")
    except FileNotFoundError:
        raise RuntimeError("FFmpeg 未安装或未配置在系统路径中")
    except Exception as e:
        raise RuntimeError(f"FFmpeg 检查失败: {e}")

check_ffmpeg()

def transcribe_and_add_subtitles(video_path, output_path):
    print(f"处理视频: {video_path}")

    # 提取音频
    audio_path = "temp_audio.wav"
    try:
        video_clip = VideoFileClip(video_path)
        video_clip.audio.write_audiofile(audio_path, codec="pcm_s16le")
    except Exception as e:
        raise RuntimeError(f"音频提取失败: {e}")

    # 确保音频文件存在
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件 {audio_path} 未成功生成，请检查 FFmpeg 配置。")

    # 转录音频
    try:
        print(f"开始转录音频")
        result = model.transcribe(audio_path, language="ja")
        
        # 保存转录文本
        transcription_path = output_path or os.path.splitext(video_path)[0] + "_transcription.txt"
        with open(transcription_path, "w", encoding="utf-8") as f:
            for segment in result["segments"]:
                f.write(f"[{format_timestamp(segment['start'])} - {format_timestamp(segment['end'])}] {segment['text']}\n")
        print(f"转录完成，保存文件: {transcription_path}")
        
        # 添加字幕到视频
        subtitles_path = "temp_subtitles.srt"
        try:
            with open(subtitles_path, "w", encoding="utf-8") as f:
                for i, segment in enumerate(result["segments"], start=1):
                    f.write(f"{i}\n")
                    f.write(f"{format_timestamp(segment['start'])} --> {format_timestamp(segment['end'])}\n")
                    f.write(f"{segment['text']}\n\n")

            output_video_path = output_path or os.path.splitext(video_path)[0] + "_subtitled.mp4"
            # 使用系统中的 FFmpeg
            os.system(f"ffmpeg -i \"{video_path}\" -vf subtitles=\"{subtitles_path}\" \"{output_video_path}\"")
            print(f"字幕已添加，输出文件: {output_video_path}")
        except Exception as e:
            raise RuntimeError(f"字幕生成失败: {e}")
        finally:
            if os.path.exists(subtitles_path):
                os.remove(subtitles_path)  # 删除临时字幕文件
    except FileNotFoundError as e:
        raise RuntimeError("Whisper 未能调用 FFmpeg，请检查配置路径") from e
    except Exception as e:
        raise RuntimeError(f"音频转录失败: {e}")
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)  # 删除临时音频文件

def format_timestamp(seconds):
    """格式化时间戳为 SRT 格式"""
    millis = int((seconds - int(seconds)) * 1000)
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

# 批量处理 input_video 文件夹中的视频
input_folder = "input_video"
output_folder = "output_video"
os.makedirs(output_folder, exist_ok=True)

for file_name in os.listdir(input_folder):
    if file_name.endswith((".mp4", ".mkv", ".avi")):
        input_path = os.path.join(input_folder, file_name)
        output_path = os.path.join(output_folder, os.path.splitext(file_name)[0] + "_subtitled.mp4")
        try:
            transcribe_and_add_subtitles(input_path, output_path)
        except Exception as e:
            print(f"处理 {file_name} 时出错: {e}")
