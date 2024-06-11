import os
import subprocess
import ffmpeg
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import filedialog, messagebox

def find_silence_points(audio_path, silence_thresh=-30):
    cmd = [
        'ffmpeg', '-i', audio_path,
        '-af', f'silencedetect=noise={silence_thresh}dB:d=0.2',
        '-f', 'null', '-'
    ]

    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)
    output = process.communicate()[1]

    silence_points = []
    for line in output.split('\n'):
        if 'silence_end' in line:
            time_str = line.split('silence_end: ')[1].split('|')[0]
            silence_points.append(float(time_str))
        elif 'silence_start' in line:
            time_str = line.split('silence_start: ')[1]
            silence_points.append(float(time_str))

    return silence_points

def export_chunk_with_silence(audio_path, start, end, output_file, silence_duration):
    duration = float(ffmpeg.probe(audio_path)['format']['duration'])
    segment_start = max(0, start)
    segment_end = min(end, duration)

    temp_output_file = output_file + "_temp.wav"
    subprocess.run([
        'ffmpeg', '-i', audio_path,
        '-ss', str(segment_start), '-to', str(segment_end),
        '-c', 'copy', temp_output_file
    ])

    segment = AudioSegment.from_file(temp_output_file)
    silence = AudioSegment.silent(duration=silence_duration)
    segment_with_silence = silence + segment + silence
    segment_with_silence.export(output_file, format="wav")

    os.remove(temp_output_file)

def process_chunk(audio_path, start_time, end_time, output_path, chunk_index, silence_duration):
    output_file = os.path.join(output_path, f"chunk_{chunk_index}.wav")
    export_chunk_with_silence(audio_path, start_time, end_time, output_file, silence_duration)

def split_audio(audio_path, output_path, min_length, max_length, silence_thresh, silence_duration, max_workers):
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    silence_points = find_silence_points(audio_path, silence_thresh)
    
    start_time = 0
    chunk_index = 0
    tasks = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for silence_point in silence_points:
            segment_length = silence_point - start_time
            if segment_length >= min_length:
                if segment_length > max_length:
                    next_silence_point = min(start_time + max_length, silence_point)
                    tasks.append(executor.submit(process_chunk, audio_path, start_time, next_silence_point, output_path, chunk_index, silence_duration))
                    chunk_index += 1
                    start_time = next_silence_point
                else:
                    tasks.append(executor.submit(process_chunk, audio_path, start_time, silence_point, output_path, chunk_index, silence_duration))
                    chunk_index += 1
                    start_time = silence_point

        end_time = float(ffmpeg.probe(audio_path)['format']['duration'])
        if start_time < end_time:
            tasks.append(executor.submit(process_chunk, audio_path, start_time, end_time, output_path, chunk_index, silence_duration))

        for task in tasks:
            task.result()

def start_processing(audio_path, output_path, min_length, max_length, silence_thresh, silence_duration, max_workers):
    try:
        split_audio(audio_path, output_path, min_length, max_length, silence_thresh, silence_duration, max_workers)
        messagebox.showinfo("完成", "音频处理完成！")
    except Exception as e:
        messagebox.showerror("错误", str(e))

def browse_file(entry):
    file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.aac *.flac")])
    if file_path:
        entry.delete(0, tk.END)
        entry.insert(0, file_path)

def browse_directory(entry):
    directory_path = filedialog.askdirectory()
    if directory_path:
        entry.delete(0, tk.END)
        entry.insert(0, directory_path)

def create_gui():
    root = tk.Tk()
    root.title("音频分割工具")

    tk.Label(root, text="输入音频文件路径:").grid(row=0, column=0, padx=10, pady=10)
    audio_path_entry = tk.Entry(root, width=50)
    audio_path_entry.grid(row=0, column=1, padx=10, pady=10)
    tk.Button(root, text="浏览", command=lambda: browse_file(audio_path_entry)).grid(row=0, column=2, padx=10, pady=10)

    tk.Label(root, text="输出目录:").grid(row=1, column=0, padx=10, pady=10)
    output_path_entry = tk.Entry(root, width=50)
    output_path_entry.grid(row=1, column=1, padx=10, pady=10)
    tk.Button(root, text="浏览", command=lambda: browse_directory(output_path_entry)).grid(row=1, column=2, padx=10, pady=10)

    tk.Label(root, text="最短片段长度 (秒):").grid(row=2, column=0, padx=10, pady=10)
    min_length_entry = tk.Entry(root)
    min_length_entry.insert(0, "10")
    min_length_entry.grid(row=2, column=1, padx=10, pady=10)

    tk.Label(root, text="最长片段长度 (秒):").grid(row=3, column=0, padx=10, pady=10)
    max_length_entry = tk.Entry(root)
    max_length_entry.insert(0, "15")
    max_length_entry.grid(row=3, column=1, padx=10, pady=10)

    tk.Label(root, text="静音阈值 (dB):").grid(row=4, column=0, padx=10, pady=10)
    silence_thresh_entry = tk.Entry(root)
    silence_thresh_entry.insert(0, "-30")
    silence_thresh_entry.grid(row=4, column=1, padx=10, pady=10)

    tk.Label(root, text="静音时长 (毫秒):").grid(row=5, column=0, padx=10, pady=10)
    silence_duration_entry = tk.Entry(root)
    silence_duration_entry.insert(0, "200")
    silence_duration_entry.grid(row=5, column=1, padx=10, pady=10)

    tk.Label(root, text="最大并行线程数:").grid(row=6, column=0, padx=10, pady=10)
    max_workers_entry = tk.Entry(root)
    max_workers_entry.insert(0, "4")
    max_workers_entry.grid(row=6, column=1, padx=10, pady=10)

    tk.Button(root, text="开始处理", command=lambda: start_processing(
        audio_path_entry.get(),
        output_path_entry.get(),
        int(min_length_entry.get()),
        int(max_length_entry.get()),
        float(silence_thresh_entry.get()),
        int(silence_duration_entry.get()),
        int(max_workers_entry.get())
    )).grid(row=7, column=0, columnspan=3, padx=10, pady=20)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
