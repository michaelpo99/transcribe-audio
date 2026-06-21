# transcribe-audio

`transcribe-audio` 是一支 Bash CLI，用來掃描指定目錄第一層的音檔與影片檔，必要時先從影片抽出第一條音軌，再用 WhisperX 批次轉成逐字稿。
`media2md` 是一支 wrapper，會接續呼叫 `transcribe-audio` 與 `transcript-polish`，輸出 raw transcript 與 polished Markdown。

這個 repo 只負責 transcription 階段，不包含獨立的 `extract-audio` 工具。`transcribe-audio` 內部可以保留自己的影片抽音軌前處理邏輯，因為它的需求是服務轉錄 pipeline；獨立抽音軌工具由 `extract-audio` repo 維護。

正式文件集中放在 `docs/`：

- 安裝說明：[docs/INSTALL.md](docs/INSTALL.md)
- 需求規格：[docs/SDD-whisperx-batch-transcribe.md](docs/SDD-whisperx-batch-transcribe.md)
- 拆分與整合前置 CR：[docs/SDD-CR-001-integrated-pipeline-readiness.md](docs/SDD-CR-001-integrated-pipeline-readiness.md)
- media2md pipeline CR：[docs/SDD-CR-002-media2md-pipeline.md](docs/SDD-CR-002-media2md-pipeline.md)
- 實測筆記：[docs/notes/WhisperX 在 WSL2 的安裝與使用筆記.md](<docs/notes/WhisperX 在 WSL2 的安裝與使用筆記.md>)
- CR 文件命名規則：`docs/SDD-CR-###-<slug>.md`，同一 repo 內依建立順序遞增編號。
- Bug fix 文件命名規則：`docs/SDD-BUGFIX-###-<slug>.md`，同一 repo 內依建立順序遞增編號。

## 功能

- 掃描指定目錄第一層的音檔與影片檔。
- 音檔可直接納入轉錄。
- 影片會先抽出第一條音軌到同一目錄，再納入轉錄。
- 若影片已有同 stem 的可用音檔，預設沿用既有音檔，不重新抽取。
- 預設語言為 `zh`。
- 預設只輸出 `txt`。
- 預設輸出到目標目錄下的 `transcript/`。
- 支援 `--transcript-dir` 自訂 raw transcript 輸出位置。
- 支援 `--file`、`--glob`、`--regex` 與 `--all-matches` 做單檔或 selector 輸入。
- 支援 `--diarize` 啟用說話者分離。
- `media2md` 可串接 `transcribe-audio` 與 `transcript-polish`。
- 執行前會檢查 WhisperX、Python、Torch、FFmpeg、CUDA 與 Hugging Face 權限。
- 會依硬體自動推估 `model`、`device`、`compute_type`、`batch_size`。
- 會輸出 `_run-summary.txt` 與 `_environment.txt`。

## 專案結構

```text
transcribe-audio/
├── .gitignore
├── README.md
├── install.sh
├── bin/
│   ├── transcribe-audio
│   └── media2md
└── docs/
    ├── INSTALL.md
    ├── SDD-whisperx-batch-transcribe.md
    ├── SDD-CR-001-integrated-pipeline-readiness.md
    ├── SDD-CR-002-media2md-pipeline.md
    └── notes/
        └── WhisperX 在 WSL2 的安裝與使用筆記.md
```

## 快速開始

先安裝系統依賴：

```bash
sudo apt update
sudo apt install -y ffmpeg python3-venv
```

準備 WhisperX 環境：

```bash
python3 -m venv "$HOME/.venvs/whisperx"
source "$HOME/.venvs/whisperx/bin/activate"
python -m pip install --upgrade pip setuptools wheel
pip install whisperx
```

安裝 CLI：

```bash
bash install.sh
```

直接執行專案內腳本也可以：

```bash
./bin/transcribe-audio
./bin/transcribe-audio --check
./bin/transcribe-audio "/mnt/d/Videos/Meeting"
./bin/transcribe-audio --diarize "/mnt/d/Videos/Meeting"
./bin/transcribe-audio --transcript-dir ../meeting.transcript "/mnt/d/Videos/Meeting"
```

若想指定安裝位置，請看 [docs/INSTALL.md](docs/INSTALL.md)。

若要直接產生 Markdown，請先安裝 `transcript-polish`，再使用 `media2md`。

## 用法

```bash
transcribe-audio [目錄]
transcribe-audio --file INPUT [目錄]
transcribe-audio --glob PATTERN [目錄]
transcribe-audio --regex PATTERN [目錄]
transcribe-audio --check [目錄]
transcribe-audio --force [目錄]
transcribe-audio --diarize [目錄]
media2md [目錄]
media2md --file INPUT [目錄]
media2md --glob PATTERN [目錄]
media2md --regex PATTERN [目錄]
media2md --check [目錄]
media2md --force [目錄]
media2md --diarize [目錄]
media2md --polish-mode standard|quality [目錄]
```

### 常用範例

```bash
./bin/transcribe-audio
./bin/transcribe-audio "/mnt/d/Videos/Meeting"
./bin/transcribe-audio --check "/mnt/d/Videos/Meeting"
./bin/transcribe-audio --file ./meeting/a.mp4
./bin/transcribe-audio --file a ./meeting
./bin/transcribe-audio --glob '會議*' ./meeting
./bin/transcribe-audio --regex '^A00[1-5]' ./meeting
./bin/transcribe-audio --force "/mnt/d/Videos/Meeting"
./bin/transcribe-audio --diarize --min-speakers 2 --max-speakers 6 "/mnt/d/Videos/Meeting"
./bin/media2md "/mnt/d/Videos/Meeting"
./bin/media2md --file ./meeting/a.mp4
./bin/media2md --file a ./meeting
./bin/media2md --glob '會議*' ./meeting
./bin/media2md --regex '^A00[1-5]' ./meeting
./bin/media2md --check "/mnt/d/Videos/Meeting"
```

## 輸出

預設輸出到來源目錄下的 `transcript/`：

```text
Meeting/
├── meeting.mp4
├── meeting.m4a
└── transcript/
    ├── meeting.txt
    ├── _run-summary.txt
    └── _environment.txt
```

## 注意事項

- 目前只掃描指定目錄第一層，不遞迴子目錄。
- `--file` 會先嘗試把輸入視為實際檔案路徑；若檔案不存在，才改用 stem 前綴 selector。
- `--glob` 與 `--regex` 都只比對 basename stem，不比對副檔名。
- 多筆匹配預設失敗；要一次處理全部需加 `--all-matches`。
- 影片只抽第一條音軌。
- 若同名音檔或逐字稿輸出已存在且未指定 `--force`，會盡量沿用或跳過。
- `media2md` 在 selector 模式只會 polish 這次選到的 transcript 檔，不會掃整個 `transcript/`。
- 可用 `--transcript-dir` 將 raw transcript 改寫到其他位置。
- 預設語言是 `zh`；若音訊不是中文，請明確指定 `--language`。
- 使用 `--diarize` 前，需先確認 Hugging Face token 與 pyannote gated model 權限已可用。
- `transcript/` 與本地測試目錄不應提交到 Git。
- `media2md` 的 `--check` 不會執行正式轉錄或 polish。

## 與 extract-audio 的關係

`extract-audio` 是獨立輕量工具，專注影片抽音軌，只需要 FFmpeg/FFprobe。

`transcribe-audio` 是轉錄 pipeline 工具，抽音軌只是轉錄前處理的一部分，因此兩者允許保留不同實作與不同輸出策略。

`media2md` 只是把兩個已安裝工具串起來，不會把兩個 repo 合併成單一工具集。

## 授權

依你的需求自行補上授權條款。
