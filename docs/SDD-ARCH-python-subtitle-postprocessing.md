# SDD-ARCH：Python 字幕後處理架構與 Repo 規範

最後更新：2026-06-25
適用 repo：transcribe-audio

## 1. 目的

本文件定義 `transcribe-audio` 為實作 CR-004 所需的 Python 架構，包括：

- Bash 與 Python 的責任邊界。
- Python package layout 與模組責任。
- runtime、venv、安裝及執行方式。
- 測試、fixture、lint 與文件規範。
- 與 `srt-clean` 的整合邊界。

字幕切分的產品行為與驗收條件仍以
`docs/SDD-CR-004-word-timed-srt-postprocessing.md` 為準。

本架構參考 `srt-clean` 的 `src` layout、專用 venv、pytest、ruff、薄 CLI 與
deterministic rule engine 原則，但不直接複製其 repository 結構或程式碼。

## 2. 架構決策

本 repo 維持 Bash orchestration，新增 Python 字幕處理 package：

```text
media
  -> bin/transcribe-audio
  -> FFmpeg / WhisperX
  -> WhisperX alignment JSON + raw SRT
  -> Python subtitle postprocessor
  -> readable SRT
  -> optional cleaning stage
```

責任分工：

| 元件 | 責任 |
| --- | --- |
| Bash | CLI、檔案選取、FFmpeg、WhisperX、環境檢查、產物命名與 pipeline 狀態 |
| Python | JSON parsing、詞級時間、Unicode display width、切分、合併、fallback、SRT 輸出與驗證 |
| `srt-clean` | SRT 規則清理；是否內嵌共用 engine 另以 CR 決定 |

使用 Python 是因為資料與演算法需求，不代表詞級重切應移到 `srt-clean`。WhisperX
alignment JSON 屬於轉錄 pipeline 的中間資料，因此詞級重切仍由本 repo 擁有。

## 3. 技術選型

### 3.1 Python

最低版本：

```text
Python >= 3.12
```

CR-004 第一版的詞級重切核心應只使用標準庫：

```text
argparse
dataclasses
json
pathlib
tempfile
unicodedata
```

display width 第一版使用 `unicodedata.east_asian_width()` 與 combining character
判定。若後續證明需要完整 grapheme cluster 或終端寬度相容性，再評估 `wcwidth`，
不得未經規格更新直接增加依賴。

若未來把 `srt-clean` profile engine 併入本 package，才加入：

```text
PyYAML >= 6.0.1
```

### 3.2 CLI

Python 內部入口使用標準庫 `argparse`。不引入 Click 或 Typer。

主要使用者入口仍是：

```bash
transcribe-audio
```

Python CLI 是內部可測試介面，不要求成為主要公開命令。開發與除錯可使用：

```bash
python -m transcribe_audio.subtitle_cli --help
```

### 3.3 時間表示

內部統一使用整數毫秒：

```text
WhisperX float seconds
  -> parse boundary 轉成 integer milliseconds
  -> split / merge / validate
  -> writer 轉成 SRT timecode
```

不得在核心演算法內長期傳遞 binary float。秒轉毫秒採一致的四捨五入規則，
所有 cue 必須符合：

```text
0 <= start_ms < end_ms
previous.end_ms <= current.start_ms
```

## 4. Package Layout

目標結構：

```text
transcribe-audio/
├── AGENTS.md
├── pyproject.toml
├── bin/
│   ├── transcribe-audio
│   ├── media2md
│   └── transcribe-audio-subtitle
├── src/
│   └── transcribe_audio/
│       ├── __init__.py
│       ├── subtitle_cli.py
│       ├── models.py
│       ├── whisperx_json.py
│       ├── display_width.py
│       ├── segmenter.py
│       ├── timing.py
│       ├── srt_writer.py
│       ├── validator.py
│       └── cleaning.py
└── tests/
    ├── fixtures/
    ├── test_whisperx_json.py
    ├── test_display_width.py
    ├── test_segmenter.py
    ├── test_timing.py
    ├── test_srt_writer.py
    ├── test_validator.py
    └── test_subtitle_cli.py
```

模組責任：

| 模組 | 責任 |
| --- | --- |
| `subtitle_cli.py` | 解析內部 CLI 參數並組裝 pipeline |
| `models.py` | `WordTiming`、`SourceSegment`、`SubtitleCue` 等 dataclasses |
| `whisperx_json.py` | 嚴格讀取及驗證 WhisperX alignment JSON |
| `display_width.py` | Unicode display columns 與安全換行 |
| `segmenter.py` | 依標點、停頓、寬度及持續時間決定詞群 |
| `timing.py` | 首尾詞時間、缺值 interpolation、比例 fallback 與短段合併 |
| `srt_writer.py` | SRT timecode、換行、cue 重編與 UTF-8 輸出 |
| `validator.py` | 文字守恆、時間單調、無重疊、行數及寬度檢查 |
| `cleaning.py` | 清理 adapter；第一版可呼叫外部工具，未來可改接 package API |

不要把所有邏輯集中在 `subtitle_cli.py`。不要在 shell heredoc 中建立另一份 Python
實作。

## 5. 資料模型與 Pipeline

核心資料模型至少包含：

```text
WordTiming
  text
  start_ms | None
  end_ms | None

SourceSegment
  text
  start_ms
  end_ms
  words[]

SubtitleCue
  text
  lines[]
  start_ms
  end_ms
  source_segment_index
  timing_source = word | interpolated | proportional
```

處理順序固定為：

1. 讀取 alignment JSON。
2. 將 seconds 正規化為 integer milliseconds。
3. 保留所有原始文字 token，包括沒有時間的標點或詞。
4. 產生候選自然邊界。
5. 依寬度及最長時間切成詞群。
6. 優先以首尾有效 word timestamps 定時。
7. 對局部缺值做 interpolation；整段無詞級時間才做 proportional fallback。
8. 在不破壞限制時合併過短 cue。
9. 換行、重編 index 並驗證。
10. 寫入暫存檔，驗證成功後原子替換主要 SRT。
11. 依模式執行 cleaning adapter。

`timing_source` 應保留在記憶體或 debug/report 資料中，使測試與問題診斷能判斷某 cue
使用真實詞級時間或 fallback。

## 6. srt-clean 邊界

第一版不可把 `srt-clean` 原始碼直接複製進本 repo，避免形成兩份規則來源。

允許的整合階段：

```text
Phase 1
  cleaning.py 以 subprocess adapter 呼叫已安裝的 srt-clean。

Phase 2
  srt-clean 提供穩定 Python library API，本 repo 以 dependency import。

Phase 3
  若決定合併 repo，移轉 engine、profiles、tests 與授權後，
  由同一 package 直接呼叫；原 repo 封存，維持單一 source of truth。
```

無論使用哪一階段，詞級重切先完成，再進行規則清理。清理器不得負責解析 WhisperX
JSON，也不得重新估算 cue timecode。

直接移植或內嵌前必須先確認：

- 原 repo 授權文件。
- profiles 的 package data 安裝方式。
- library API 與版本相容政策。
- 原測試是否完整遷移。
- 原 `srt-clean` CLI 是否仍需保留。

## 7. pyproject.toml 規格

實作 CR-004 時新增 `pyproject.toml`，最低內容：

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "transcribe-audio"
version = "0.1.0"
description = "WhisperX transcription pipeline and subtitle postprocessor"
requires-python = ">=3.12"
dependencies = []

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "ruff>=0.5",
]

[project.scripts]
transcribe-audio-subtitle = "transcribe_audio.subtitle_cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`transcribe-audio-subtitle` 是內部入口，不取代 Bash 的 `transcribe-audio`。

## 8. Venv 與安裝策略

### 8.1 開發環境

repo 內使用：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
pip install -e ".[dev]"
```

`.venv/`、`.pytest_cache/`、`.ruff_cache/` 與 build artifacts 不得提交。

### 8.2 正式安裝

Python 後處理使用專用環境：

```text
~/.venvs/transcribe-audio
```

不把本 package 安裝進 `~/.venvs/whisperx`。原因：

- WhisperX 的 Torch/CUDA 依賴較重，升級與字幕 package 不應互相污染。
- 字幕後處理不需要 import WhisperX。
- 可以獨立檢查、更新與復原。

正式 `install.sh` 在 CR-004 實作後應：

1. 檢查 Python 3.12 以上。
2. 建立或更新 `~/.venvs/transcribe-audio`。
3. 將本 repo 的零依賴 package 部署到該 venv 的 `site-packages`。
4. 安裝 Bash commands 到使用者選擇的 `bin_dir`。
5. 安裝 `transcribe-audio-subtitle` wrapper，指向 venv 內的 Python module。
6. `--check` 驗證 package import、內部 CLI 及版本。
7. `--uninstall` 移除 commands；是否移除 venv 必須明確提示，不得默默刪除。

正式安裝不依賴網路，也不要求 venv 預先具有 `pip`、`setuptools` 或 `wheel`。
`pyproject.toml` 用於開發、測試及一般 Python packaging；repo 的 `install.sh` 使用
直接部署 package 的方式，避免在使用者機器上臨時下載 build dependencies。

允許以環境變數覆寫內部入口，供測試與進階部署使用：

```text
TRANSCRIBE_AUDIO_SUBTITLE_BIN
```

### 8.3 Repo 直接執行

repo 內的 `bin/transcribe-audio-subtitle` 以 `PYTHONPATH=<repo>/src` 啟動 module，
因此不需先建立開發 venv 即可直接執行 runtime 功能。`transcribe-audio` 搜尋順序：

```text
TRANSCRIBE_AUDIO_SUBTITLE_BIN
與 transcribe-audio 同目錄的 transcribe-audio-subtitle
~/.venvs/transcribe-audio/bin/transcribe-audio-subtitle
<repo>/.venv/bin/transcribe-audio-subtitle
PATH 中的 transcribe-audio-subtitle
```

若 SRT 後處理已啟用但找不到 Python 入口，應在 WhisperX 開始前 fail fast，並顯示
安裝或停用後處理的操作方式。

## 9. 測試規範

### 9.1 Fixture

只使用小型 synthetic fixtures：

```text
tests/fixtures/<case>.input.json
tests/fixtures/<case>.expected.srt
```

不得提交：

- 完整商業影片字幕。
- 使用者私有 transcript。
- 音訊、影片或模型檔。
- 必須使用 GPU 或下載模型的測試資料。

### 9.2 必要案例

至少涵蓋：

- 正常 `segments[].words[]` 解析。
- segment 或 word 欄位缺失與型別錯誤。
- 日文無空格、全形標點與 combining characters。
- 強標點、弱標點、停頓與強制寬度切分。
- 首尾詞時間、局部缺值 interpolation、全段 proportional fallback。
- 短段合併與最長持續時間。
- cue 不重疊、index 重編及 SRT timecode rounding。
- 所有輸入文字只出現一次。
- 暫存輸出失敗時不覆蓋主要 SRT。
- 外部 cleaner 不存在或失敗時保留 split SRT。

### 9.3 驗證命令

Python：

```bash
pytest
ruff check .
```

Shell：

```bash
bash -n bin/transcribe-audio
bash -n bin/media2md
bash -n install.sh
```

整合測試使用 fake WhisperX executable 與暫存目錄，不依賴網路、GPU 或真實媒體。

## 10. Repo 與文件規範

- 使用 `src/transcribe_audio/`，不得在 repo root 散放 Python modules。
- 使用 `tests/` 與 pytest，不在 shell script 中建立主要測試框架。
- 公開行為由 SDD/CR 定義，tests 是可執行規格。
- 新增或修改行為時，同步更新 CR、README、INSTALL 與 help。
- proposed 功能不得在 README 或 INSTALL 中描述成已可用。
- 所有使用者錯誤訊息必須說明失敗原因與可採取動作。
- 主要輸出採暫存檔及原子 rename，raw output 永遠可回溯。
- 程式不得依賴目前工作目錄尋找 package data。
- profile 若納入 package，必須使用 package resources，不使用 repo-relative path。
- 不加入大型 dependency、網路服務或 LLM，除非另開 CR 說明效益與失敗模式。

## 11. 實作順序

1. 新增 `pyproject.toml`、package skeleton、pytest 與 ruff 設定。
2. 建立 models、WhisperX JSON parser、time conversion 與 validator。
3. 建立 display width、segmenter、timing fallback 與 SRT writer。
4. 建立內部 CLI 與 synthetic fixture tests。
5. 修改 Bash pipeline，自動取得 JSON、保存 raw SRT 並呼叫內部 CLI。
6. 更新 `install.sh`、`--check`、README 與 INSTALL。
7. 加入 `srt-clean` adapter；是否改 library import 另行決策。
