# Audio Splitter GUI

这是一个用于分割音频文件的图形用户界面（GUI）工具。用户可以设置分割参数，并通过 GUI 界面轻松处理音频文件。

## 功能

- 根据静音点分割音频文件。
- 设置每个片段的最短和最长长度。
- 添加开头和结尾的静音。
- 并行处理以提高效率。

## 依赖

- Python 3.x
- ffmpeg
- pydub
- tkinter

## 安装

1. 安装 Python 依赖包：

    ```sh
    pip install ffmpeg-python pydub
    ```

2. 确保已安装 `ffmpeg` 并添加到系统路径中。

## 使用

1. 运行 `split_audio.py` 脚本：

    ```sh
    python split_audio.py
    ```

2. 通过 GUI 界面设置参数，并点击“开始处理”按钮。

## 开发者

- **Alan** - [gushuaialan@gmail.com](mailto:gushuaialan@gmail.com)
