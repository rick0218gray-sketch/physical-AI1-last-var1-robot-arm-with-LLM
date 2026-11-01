#!/usr/bin/env python3
"""Build the submission video (A+D) from the recorded clips: videos/submission_ad.mp4.

Runs inside the pai_ros2 container (ffmpeg + Noto Sans CJK JP).
All clips are recorded in real time; the NL demo has idle waits cut out.
"""
import os
import subprocess

V = '/workspace/a_crane/videos'
T = '/tmp/submission'
OUT = f'{V}/submission_ad.mp4'
W, H, FPS = 1184, 928, 20
BG = '0x1B2433'
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK'  # face 0 of the .ttc is JP
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', str(FPS)]

SKILLS = [('bow_055933.mp4', 'お辞儀'), ('point_left_060012.mp4', '左を指す'),
          ('point_right_060604.mp4', '右を指す'), ('grip_060906.mp4', '握る'),
          ('wave_075016.mp4', '手を振る'), ('nod_065537.mp4', 'うなずく')]

_n = 0


def text(s, size, y, color='white', x='(w-tw)/2', bold=False, box=False):
    """drawtext filter; the string goes through a file to avoid escaping."""
    global _n
    _n += 1
    path = f'{T}/t{_n}.txt'
    open(path, 'w', encoding='utf-8').write(s)
    font = f"{FONT}-{'Bold' if bold else 'Regular'}.ttc"
    extra = ':box=1:boxcolor=black@0.65:boxborderw=6' if box else ''
    return (f"drawtext=fontfile={font}:textfile={path}:expansion=none:fontcolor={color}:"
            f"fontsize={size}:x={x}:y={y}{extra}")


def ff(args):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y'] + args, check=True)


def card(out, sec, lines):
    """lines: (text, size, y, color, bold)"""
    vf = ','.join(text(s, sz, y, c, bold=b) for s, sz, y, c, b in lines)
    vf += f',fade=in:st=0:d=0.3,fade=out:st={sec - 0.3}:d=0.3'
    ff(['-f', 'lavfi', '-i', f'color=c={BG}:s={W}x{H}:r={FPS}', '-t', str(sec), '-vf', vf] + ENC + [out])


def grid(out, sec=13):
    ins, fc = [], []
    w, h = 392, 307
    for i, (f, label) in enumerate(SKILLS):
        ins += ['-i', f'{V}/{f}']
        fc.append(f'[{i}:v]tpad=stop_mode=clone:stop_duration=20,trim=duration={sec},setpts=PTS-STARTPTS,'
                  f'scale={w}:{h},{text(label, 26, "h-th-40", "0xF2A66B", x="40", bold=True, box=True)}[v{i}]')
    lay = '|'.join(f'{(i % 3) * w}_{(i // 3) * h}' for i in range(6))
    fc.append(f"{''.join(f'[v{i}]' for i in range(6))}xstack=inputs=6:layout={lay},"
              f'pad={W}:{H}:{(W - 3 * w) // 2}:150:color={BG},'
              + text('① 自動生成したお手本で学習した6つの動作', 40, 60, bold=True) + ','
              + text('各動作 5回中5回成功（等速・動作ごとに個別のACTモデル）', 28, 800, '0xC9D2E0') + '[o]')
    ff(ins + ['-filter_complex', ';'.join(fc), '-map', '[o]', '-t', str(sec)] + ENC + [out])


def compare(out):
    a, b = f'{V}/baseline_lecture_infer_062712.mp4', f'{V}/baseline_model_improved_runner_062804.mp4'
    sec, w, h = 18.5, 584, 458
    fc = [f'[0:v]tpad=stop_mode=clone:stop_duration=10,trim=duration={sec},setpts=PTS-STARTPTS,scale={w}:{h}[a]',
          f'[1:v]trim=duration={sec},setpts=PTS-STARTPTS,scale={w}:{h}[b]',
          f'[a][b]hstack=inputs=2,pad={W}:{H}:{(W - 2 * w) // 2}:200:color={BG},'
          + text('② 講義の手順との比較（同じ「お辞儀」のお手本20本）', 40, 60, bold=True) + ','
          + text('講義の推論スクリプト', 30, 145, '0xC9D2E0', x=str((W - 2 * w) // 2 + 10)) + ','
          + text('改良した実行器', 30, 145, '0xC9D2E0', x=str((W - 2 * w) // 2 + w + 10)) + ','
          + text('失敗（3回中0回）', 36, 680, '0xF28B82', x=str((W - 2 * w) // 2 + 10), bold=True) + ','
          + text('成功（5回中5回）', 36, 680, '0xF2A66B', x=str((W - 2 * w) // 2 + w + 10), bold=True) + ','
          + text('改良点：シミュレータ時刻で20Hz制御 ／ 経過時間を観測に追加 ／ 遅れを想定したデータ拡張', 26, 780, '0xC9D2E0')
          + '[o]']
    ff(['-i', a, '-i', b, '-filter_complex', ';'.join(fc), '-map', '[o]', '-t', str(sec)] + ENC + [out])


def demo(out):
    ff(['-i', f'{V}/demo_nl_commander.mp4'] + ENC + [out])


def table(out, sec, title, rows, note):
    """two-column results card: rows = (label, value)"""
    G, A = '0xC9D2E0', '0xF2A66B'
    f = [text(title, 52, 160, bold=True)]
    for i, (k, v) in enumerate(rows):
        y = 290 + 80 * i
        f += [text(k, 34, y, G, x='170'), text(v, 34, y, 'white', x='560', bold=True)]
    f.append(text(note, 26, 760, A))
    vf = ','.join(f) + f',fade=in:st=0:d=0.3,fade=out:st={sec - 0.3}:d=0.3'
    ff(['-f', 'lavfi', '-i', f'color=c={BG}:s={W}x{H}:r={FPS}', '-t', str(sec), '-vf', vf] + ENC + [out])


def main():
    os.makedirs(T, exist_ok=True)
    G, A = '0xC9D2E0', '0xF2A66B'
    parts = []

    def p(name):
        parts.append(f'{T}/{name}.mp4')
        return parts[-1]

    card(p('00_title'), 5, [
        ('言葉で指示するロボットアーム', 64, 300, 'white', True),
        ('日本語の指示 → LLMが動作の列を計画 → 模倣学習（ACT）した動作を実行', 30, 420, G, False),
        ('CRANE+ V2 ／ ROS 2 Humble ／ Gazebo ／ LeRobot ACT ／ Ollama', 26, 500, G, False),
        ('映像はすべて等速（指示デモはLLMの待ち時間のみカット）', 24, 620, A, False)])
    card(p('01_how'), 6, [
        ('しくみ', 52, 200, 'white', True),
        ('1. スクリプトでお手本を自動生成し、6つの動作をACTで学習', 32, 340, G, False),
        ('2. ローカルLLM（qwen2.5）が日本語の指示を動作の列に変換', 32, 420, G, False),
        ('3. 常駐した動作サーバが順に実行。できない指示は拒否・確認', 32, 500, G, False),
        ('AIの使用：ACT（学習と推論）＋ LLM（推論）', 28, 640, A, False)])
    grid(p('02_skills'))
    compare(p('03_compare'))
    card(p('04_nl'), 3, [
        ('③ 日本語で指示する', 52, 340, 'white', True),
        ('2つの動作の連続実行 ／ 曖昧な指示は確認 ／ できない指示は拒否', 30, 460, G, False)])
    demo(p('05_demo'))
    table(p('06_result'), 8, '結果', [
        ('6つの動作', '各5回中5回成功'),
        ('講義の手順との比較', '3回中0回 → 5回中5回'),
        ('2動作の連続実行', '15回中15回成功'),
        ('指示の判定（40問）', 'qwen2.5 3b 82% ／ 7b 90%'),
        ('1動作の所要時間', '約40秒 → 約10秒（モデル常駐）')],
        'コードとレポートは概要欄のリンクから')

    lst = f'{T}/list.txt'
    open(lst, 'w').write(''.join(f"file '{x}'\n" for x in parts))
    ff(['-f', 'concat', '-safe', '0', '-i', lst] + ENC + ['-movflags', '+faststart', OUT])
    d = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', OUT],
                       capture_output=True, text=True).stdout.strip()
    print('out:', OUT, 'duration:', d)


if __name__ == '__main__':
    main()
