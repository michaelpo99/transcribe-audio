# 安裝程序

這個專案提供一支 Bash 指令：

```text
transcribe-audio
media2md
```

用途是掃描目錄中的音檔與影片檔，必要時先抽音軌，再用 WhisperX 批次轉文字。

## 1. 安裝系統依賴

在 Ubuntu / WSL：

```bash
sudo apt update
sudo apt install -y ffmpeg python3-venv
```

確認 FFmpeg 與 FFprobe 可用：

```bash
ffmpeg -version
ffprobe -version
```

## 2. 取得專案

```bash
git clone https://github.com/michaelpo99/transcribe-audio.git
cd transcribe-audio
```

若你是本機手動建立或測試，也可以直接進入專案目錄：

```bash
cd ~/transcribe-audio
```

## 3. 準備 WhisperX 環境

```bash
python3 -m venv "$HOME/.venvs/whisperx"
source "$HOME/.venvs/whisperx/bin/activate"
python -m pip install --upgrade pip setuptools wheel
pip install whisperx
```

確認：

```bash
"$HOME/.venvs/whisperx/bin/whisperx" --help
"$HOME/.venvs/whisperx/bin/python" -c "import torch; print(torch.cuda.is_available())"
```

若要使用 `--diarize`，還需要：

1. Hugging Face 帳號。
2. 可讀取 `pyannote/speaker-diarization-community-1` 的權限。
3. 可用的 `HF_TOKEN`，或已登入 Hugging Face CLI。

## 4. 使用 install.sh 安裝 CLI

預設安裝到：

```text
~/bin/transcribe-audio
```

執行：

```bash
bash install.sh
```

檢查安裝與依賴：

```bash
bash install.sh --check
```

指定安裝目錄：

```bash
bash install.sh --bin-dir "$HOME/.local/bin"
```

指定 prefix，會安裝到 `PREFIX/bin`：

```bash
sudo bash install.sh --prefix /usr/local
```

移除全域指令：

```bash
bash install.sh --uninstall
```

`install.sh` 不會自動修改 shell 設定檔。若安裝目錄不在 PATH，腳本會提示應加入的 `export PATH=...`。

`media2md` 會再呼叫 `transcript-polish`，因此若要使用一鍵產出 Markdown 的流程，還需要先安裝 `transcript-polish` 並讓它可在 PATH 中被找到。

`transcribe-audio` 可用 `--transcript-dir` 改寫 raw transcript 輸出位置。

## 5. 直接執行

不安裝也可以直接執行 repo 內腳本：

```bash
./bin/transcribe-audio
./bin/transcribe-audio --check
./bin/transcribe-audio "/mnt/d/Videos/Meeting"
./bin/transcribe-audio --diarize "/mnt/d/Videos/Meeting"
./bin/transcribe-audio --transcript-dir ../meeting.transcript "/mnt/d/Videos/Meeting"
./bin/media2md
./bin/media2md --check
./bin/media2md "/mnt/d/Videos/Meeting"
./bin/media2md --polish-mode quality "/mnt/d/Videos/Meeting"
```

## 6. 手動安裝成全域指令

若不使用 `install.sh`，也可以手動複製：

```bash
mkdir -p ~/bin
cp ./bin/transcribe-audio ~/bin/transcribe-audio
cp ./bin/media2md ~/bin/media2md
chmod +x ~/bin/transcribe-audio
chmod +x ~/bin/media2md
```

把 `~/bin` 加入 PATH：

```bash
grep -qxF 'export PATH="$HOME/bin:$PATH"' ~/.bashrc || \
    echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
```

重新載入 shell：

```bash
source ~/.bashrc
```

確認安裝：

```bash
which transcribe-audio
transcribe-audio --help
transcribe-audio --check
which media2md
media2md --help
media2md --check
```

## 7. 更新安裝

若腳本有新版本：

```bash
git pull
bash install.sh
```

若 WhisperX 環境也有更新需求：

```bash
source "$HOME/.venvs/whisperx/bin/activate"
pip install --upgrade whisperx
```

## 8. 驗證

最小驗證：

```bash
transcribe-audio --help
transcribe-audio --check
media2md --help
media2md --check
```

若要驗證 diarization：

```bash
export HF_TOKEN="你的 token"
transcribe-audio --check --diarize
```

## 9. 移除

只移除全域指令：

```bash
bash install.sh --uninstall
```

這會同時移除 `transcribe-audio` 與 `media2md`。

移除 WhisperX 虛擬環境：

```bash
rm -rf "$HOME/.venvs/whisperx"
```

移除專案目錄：

```bash
cd ~
rm -rf ~/transcribe-audio
```
