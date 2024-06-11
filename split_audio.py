import os
import subprocess
import ffmpeg
import argparse
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor

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

def main():
    parser = argparse.ArgumentParser(description="Split audio into chunks with adjustable parameters.")
    parser.add_argument("audio_path", type=str, help="Path to the input audio file.")
    parser.add_argument("output_path", type=str, help="Directory to save the output audio chunks.")
    parser.add_argument("--min_length", type=int, default=10, help="Minimum length of each chunk in seconds.")
    parser.add_argument("--max_length", type=int, default=15, help="Maximum length of each chunk in seconds.")
    parser.add_argument("--silence_thresh", type=float, default=-30, help="Silence threshold in dB.")
    parser.add_argument("--silence_duration", type=int, default=200, help="Duration of silence added to the beginning and end of each chunk in milliseconds.")
    parser.add_argument("--max_workers", type=int, default=4, help="Maximum number of threads for parallel processing.")
    
    args = parser.parse_args()

    print(f"Splitting audio with the following parameters:")
    print(f"Input audio path: {args.audio_path}")
    print(f"Output path: {args.output_path}")
    print(f"Minimum chunk length: {args.min_length} seconds")
    print(f"Maximum chunk length: {args.max_length} seconds")
    print(f"Silence threshold: {args.silence_thresh} dB")
    print(f"Silence duration: {args.silence_duration} milliseconds")
    print(f"Maximum workers: {args.max_workers}")

    split_audio(args.audio_path, args.output_path, args.min_length, args.max_length, args.silence_thresh, args.silence_duration, args.max_workers)

if __name__ == "__main__":
    main()
