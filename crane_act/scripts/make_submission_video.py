#!/usr/bin/env python3
"""Build the submission video from the recorded clips: videos/submission_ad.mp4.

Plain footage only (explanations live in the report): title -> NL command demo
-> the six learned skills one by one. 1920x1080, 20 fps, silent AAC track.
Runs inside the pai_ros2 container (ffmpeg + Noto Sans CJK JP).
All clips are recorded in real time; the NL demo has idle LLM waits cut out.
"""
import os
import subprocess

V = '/workspace/a_crane/videos'
T = '/tmp/submission'
OUT = f'{V}/submission_ad.mp4'
W, H, FPS = 1920, 1080, 20
BG = '0x1B2433'
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK'  # face 0 of the .ttc is JP
ENC = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', str(FPS)]
FIT = f'scale=-2:{H},pad={W}:{H}:ow-iw:0:color={BG}'  # footage on the right, labels in the left column

SKILLS = [('bow_055933.mp4', 'お辞儀（bow）'), ('point_left_060012.mp4', '左を指す（point_left）'),
          ('point_right_060604.mp4', '右を指す（point_right）'), ('grip_060906.mp4', '握る（grip）'),
          ('wave_075016.mp4', '手を振る（wave）'), ('nod_065537.mp4', 'うなずく（nod）')]

_n = 0


def text(s, size, y, color='white', x='(w-tw)/2', bold=False):
    """drawtext filter; the string goes through a file to avoid escaping."""
    global _n
    _n += 1
    path = f'{T}/t{_n}.txt'
    open(path, 'w', encoding='utf-8').write(s)
    font = f"{FONT}-{'Bold' if bold else 'Regular'}.ttc"
    return (f"drawtext=fontfile={font}:textfile={path}:expansion=none:fontcolor={color}:"
            f"fontsize={size}:x={x}:y={y}")


def ff(args):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y'] + args, check=True)


def main():
    os.makedirs(T, exist_ok=True)
    G = '0xC9D2E0'
    parts = []

    title = f'{T}/00_title.mp4'
    vf = ','.join([text('日本語の指令で動くロボットアーム', 80, 380, bold=True),
                   text('CRANE+ V2 ／ ROS 2 + Gazebo ／ 動作：ACT（模倣学習） ／ 計画：ローカルLLM', 36, 520, G),
                   text('等速再生（指令デモはLLMの応答待ちのみカット）', 32, 640, '0xF2A66B')])
    ff(['-f', 'lavfi', '-i', f'color=c={BG}:s={W}x{H}:r={FPS}', '-t', '4',
        '-vf', vf + ',fade=in:st=0:d=0.3,fade=out:st=3.7:d=0.3'] + ENC + [title])
    parts.append(title)

    demo = f'{T}/01_demo.mp4'
    ff(['-i', f'{V}/demo_nl_commander.mp4', '-vf', ','.join([
        FIT, text('日本語の指令で', 44, 80, x='40', bold=True), text('動かす', 44, 140, x='40', bold=True),
        text('指令 → LLMが計画', 30, 240, G, x='40'), text('→ 学習した動作を', 30, 290, G, x='40'),
        text('　 順に実行', 30, 340, G, x='40')])] + ENC + [demo])
    parts.append(demo)

    for i, (f, label) in enumerate(SKILLS):
        out = f'{T}/02_skill{i}.mp4'
        name, key = label.split('（')
        ff(['-i', f'{V}/{f}', '-vf', ','.join([
            FIT, text(f'学習した動作 {i + 1}/6', 30, 80, G, x='40'), text(name, 52, 140, x='40', bold=True),
            text('（' + key, 30, 220, G, x='40')])] + ENC + [out])
        parts.append(out)

    lst = f'{T}/list.txt'
    open(lst, 'w').write(''.join(f"file '{x}'\n" for x in parts))
    ff(['-f', 'concat', '-safe', '0', '-i', lst, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
        '-map', '0:v', '-map', '1:a', '-shortest'] + ENC + ['-c:a', 'aac', '-b:a', '128k',
                                                           '-movflags', '+faststart', OUT])
    d = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', OUT],
                       capture_output=True, text=True).stdout.strip()
    print('out:', OUT, 'duration:', d)


if __name__ == '__main__':
    main()
