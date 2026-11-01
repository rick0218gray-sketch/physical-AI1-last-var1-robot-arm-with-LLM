# Colab (A100) で実行したセル

1. GPU の確認
   ```
   !nvidia-smi --query-gpu=name,memory.total --format=csv
   ```
2. Ollama の導入とモデルの取得（serve は 127.0.0.1 だけで待ち受ける）
   ```
   !sudo apt-get -qq install -y zstd > /dev/null; curl -fsSL https://ollama.com/install.sh | sh > /tmp/ollama_install.log 2>&1
   import subprocess, time
   subprocess.Popen('OLLAMA_HOST=127.0.0.1:11434 nohup ollama serve > /tmp/ollama.log 2>&1', shell=True)
   time.sleep(5)
   subprocess.Popen("nohup sh -c 'ollama pull qwen2.5:32b-instruct && ollama pull qwen2.5:14b-instruct && ollama pull qwen2.5:3b-instruct' > /tmp/pull.log 2>&1", shell=True)
   ```
3. d_llm 一式（commander.py, eval/, skills.mock.json, skill_hints.json, mock_run_skill.sh）を tar.gz + base64 にしてセルに埋め込み、/content/d_llm に展開する。転送後の md5 が手元と一致することを確認した。
4. 評価の実行
   ```
   %cd /content/d_llm
   !OLLAMA_URL=http://127.0.0.1:11434 python eval/run_eval.py --models qwen2.5:32b-instruct qwen2.5:14b-instruct qwen2.5:3b-instruct --tag colab_a100 --min-free-mib 0
   ```
5. 終了後、「ランタイムを接続解除して削除」でランタイムを止めた。
