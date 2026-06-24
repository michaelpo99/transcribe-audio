# AGENTS.md

本文件定義 Codex 與其他程式代理在 `transcribe-audio` repo 內工作的專案規範。

修改程式前應先閱讀本文件，以及與需求最接近的 `docs/SDD-*.md`。

## 專案責任

`transcribe-audio` 負責：

- 掃描與選取音訊、影片輸入。
- 必要時使用 FFmpeg 做轉錄前音軌處理。
- 呼叫 WhisperX 執行 ASR、alignment 與 diarization。
- 將 WhisperX 結果轉成 raw transcript。
- 依 CR-004 將 alignment words 重組為可讀 SRT。
- 透過 `media2md` 串接外部 `transcript-polish`。

本 repo 不負責摘要、內容改寫、翻譯或 LLM 語意審查。

## 主要規格

實作前依工作範圍閱讀：

```text
docs/SDD-whisperx-batch-transcribe.md
docs/SDD-ARCH-python-subtitle-postprocessing.md
docs/SDD-CR-004-word-timed-srt-postprocessing.md
```

- `SDD-whisperx-batch-transcribe.md` 定義整體轉錄責任。
- `SDD-ARCH-python-subtitle-postprocessing.md` 定義 Bash/Python 邊界、package、安裝與測試規範。
- `SDD-CR-004-word-timed-srt-postprocessing.md` 定義詞級字幕重切與清理行為。

## 架構規則

維持混合架構：

```text
Bash
  CLI、media scanning、FFmpeg、WhisperX、檔案流程與環境檢查

Python
  WhisperX JSON、Unicode、詞級時間、字幕切分、SRT writer 與規則清理
```

不要在 Bash 內實作 JSON parser、Unicode display width、浮點時間分配或字幕規則引擎。

Python 程式採標準 `src` package layout：

```text
src/transcribe_audio/
tests/
pyproject.toml
```

不要把可重用的 Python 邏輯直接放在 `bin/` 或 shell heredoc。`bin/` 只放使用者入口與
薄 wrapper。

## Python 規範

使用：

```text
Python >= 3.12
argparse
dataclasses
pathlib
pytest
ruff
```

優先使用標準庫。新增 runtime dependency 前，必須先確認標準庫無法可靠完成需求，
並同步更新架構文件與安裝文件。

模組應保持小而可測試。CLI 只負責參數解析與 orchestration，不應承載核心演算法。

所有時間在核心 model 中使用整數毫秒；只在讀取 WhisperX JSON 與輸出 SRT 時進行
秒數或 timecode 轉換，避免浮點累積誤差。

## 字幕處理守則

1. 原始 WhisperX SRT 必須可追溯，不得被後製結果覆蓋而無備份。
2. 有詞級時間時必須優先使用，不得退回文字比例估算。
3. fallback 不得造成文字遺失、重複、負時間或 cue 重疊。
4. 輸出 cue index 必須從 1 連續重編。
5. 清理規則必須 deterministic，不得依賴網路服務或 LLM。
6. 任何會刪除或壓縮文字的規則都必須有 report 與測試。
7. corpus-specific 規則應放在 profile，不應硬編碼在通用切分演算法。
8. 不得將使用者提供的完整商業字幕、音訊或影片提交為 fixture。

## 測試規範

Python 測試使用 `pytest`，fixture 放在：

```text
tests/fixtures/
```

使用短小、人工合成的 JSON 與 SRT。每個 fixture 優先只驗證一項行為。

最低完成條件：

```bash
pytest
ruff check .
```

涉及 shell pipeline 時，另執行：

```bash
bash -n bin/transcribe-audio
bash -n bin/media2md
bash -n install.sh
```

測試不得要求網路、GPU、大型模型或真實媒體檔。WhisperX 與外部命令應以 fixture、
stub 或 fake executable 隔離。

## 文件規範

行為改變時：

1. 更新對應的 `docs/SDD-CR-*.md` 或主要 SDD。
2. 架構、package 或安裝方式改變時，更新
   `docs/SDD-ARCH-python-subtitle-postprocessing.md`。
3. 使用方式改變時，更新 `README.md` 與 `docs/INSTALL.md`。
4. 新增 CR 使用 `docs/SDD-CR-###-<slug>.md`，編號不得重複。

文件中的 proposed 行為不得描述成已完成功能。

## 安全與相容性

- 不得預設覆蓋使用者既有輸出；覆蓋必須符合既有 `--force` 語意。
- 使用暫存檔加原子 rename 發布主要 SRT，避免留下半成品。
- 保持 batch、single-file、glob 與 regex selector 行為相容。
- Python 後處理失敗時必須保留 raw 產物並回報可操作的錯誤。
- 不得在 repo 中加入 token、憑證、私有 transcript 或本機絕對路徑。

