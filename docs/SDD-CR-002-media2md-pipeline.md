# SDD/CR-002：media2md pipeline wrapper

狀態：Completed
日期：2026-06-21
適用 repo：transcribe-audio

## 1. 背景

目前 `transcribe-audio` 負責 media pool 到 raw transcript：掃描目錄第一層音檔與影片檔，必要時做轉錄前音軌處理，再用 WhisperX 產生逐字稿。

`transcript-polish` 則負責 raw transcript 到 readable Markdown：保守整理逐字稿，不摘要、不改寫、不新增資訊。

兩者是同一條使用者流程的前後段，但工程型態不同：

- `transcribe-audio` 是 Bash CLI，重點是 media 掃描、WhisperX、FFmpeg、Torch/CUDA runtime。
- `transcript-polish` 是 Python package，重點是文字整理、模型模式、prompt、輸出 Markdown。

本 CR 採用以下方向：

```text
不合併 repo。
不新增第三個 orchestration repo。
在 transcribe-audio repo 新增短命令 media2md，負責串接兩個已安裝工具。
```

## 2. 目標

新增一支短命令：

```bash
media2md ./meeting
```

預設流程：

```text
media / audio / video
  -> transcribe-audio
  -> meeting/transcript/
  -> transcript-polish
  -> meeting/polished/
```

預設目錄結果：

```text
meeting/
├── meeting.mp4
├── meeting.m4a
├── transcript/
│   ├── meeting.txt
│   ├── _run-summary.txt
│   └── _environment.txt
└── polished/
    ├── meeting.md
    ├── _run-summary.txt
    └── _environment.txt
```

## 3. 指令名稱決策

採用：

```text
media2md
```

原因：

- 比 `transcribe-and-polish` 短很多。
- 比 `tp`、`run`、`pipeline` 更清楚。
- 比 `audio2md` 準確，因為輸入可以是影片或音檔。
- 產物是 Markdown，所以 `2md` 能直接表達最終目的。

## 4. 本 repo 需要新增或修改的功能

### 4.1 新增 `bin/media2md`

`media2md` 應放在：

```text
bin/media2md
```

基本用法：

```bash
media2md [目錄]
media2md --check [目錄]
media2md --force [目錄]
media2md --diarize [目錄]
```

它應做的事：

1. 驗證目標目錄存在。
2. 檢查 `transcribe-audio` 可用；若 PATH 找不到，應優先嘗試 `media2md` 同目錄下的 `transcribe-audio`。
3. 檢查 `transcript-polish` 可用。
4. 執行 `transcribe-audio`，產生 raw transcript。
5. 執行 `transcript-polish --dir <meeting/transcript> --output-dir <meeting/polished>`。
6. 顯示最後產物位置。

在呼叫下游工具前，`target_dir` 應先轉成絕對路徑，避免 relative path 造成輸出巢狀。

### 4.2 `install.sh` 應同時安裝 `media2md`

目前 `install.sh` 只安裝 `transcribe-audio`。

本 CR 完成後，預設應安裝：

```text
~/bin/transcribe-audio
~/bin/media2md
```

`--check` 應檢查：

- `transcribe-audio` 是否已安裝。
- `media2md` 是否已安裝。
- `transcript-polish` 是否可在 PATH 找到。
- FFmpeg / FFprobe / Python / WhisperX 是否可用。

`--uninstall` 應同時移除：

```text
transcribe-audio
media2md
```

### 4.3 README / INSTALL 文件更新

README 應新增一節：

```text
## 一鍵流程：media2md
```

並給出：

```bash
media2md ./meeting
```

INSTALL 應說明：

- `media2md` 需要先安裝 `transcript-polish`。
- 若只要 raw transcript，可只用 `transcribe-audio`。
- 若要 raw transcript + polished Markdown，可用 `media2md`。

### 4.4 `transcribe-audio` 可選新增 `--transcript-dir`

目前 `transcribe-audio` 固定輸出到：

```text
<target>/transcript/
```

短期 `media2md` 可以直接沿用這個預設，不一定要先改。

但為了後續 pipeline 彈性，建議新增：

```bash
transcribe-audio --transcript-dir DIR [目錄]
```

語意：

- 若 `DIR` 是相對路徑，應以 target directory 為基準。
- 若 `DIR` 是絕對路徑，直接使用該絕對路徑。
- 預設仍為 `transcript`。

這可讓未來支援：

```bash
transcribe-audio --transcript-dir ../meeting.transcript ./meeting
```

但本次 `media2md` 的預設仍應使用：

```text
meeting/transcript/
```

### 4.5 `media2md` 的 force 語意

建議一開始採用簡單規則：

```text
--force 同時傳給 transcribe-audio 與 transcript-polish
```

後續如果需要更細控制，再加：

```text
--force-transcribe
--force-polish
--skip-transcribe
--skip-polish
```

本 CR 第一版不必一次實作全部細分參數，避免 CLI 過度複雜。

### 4.6 `media2md` 的 polish 模式

`media2md` 應允許把 transcript-polish 的常用參數往後傳。

建議第一版支援：

```bash
media2md --polish-mode standard ./meeting
media2md --polish-mode quality ./meeting
```

對應呼叫：

```bash
transcript-polish \
  --mode standard \
  --dir "$(pwd)/meeting/transcript" \
  --output-dir "$(pwd)/meeting/polished"
```

若未指定，交給 `transcript-polish` 自己的預設設定。

## 5. 不納入本次 CR 的事項

本次不做：

- 合併 `transcript-polish` repo。
- 建立第三個 orchestration repo。
- 改成 Python monorepo。
- 產生會議紀錄、摘要、決議、待辦。
- 改變 `transcribe-audio` 既有預設輸出 layout。

## 6. 驗收標準

### 6.1 安裝

執行：

```bash
bash install.sh
```

應安裝：

```text
transcribe-audio
media2md
```

### 6.2 check

執行：

```bash
bash install.sh --check
```

應檢查 `media2md`、`transcribe-audio` 與 `transcript-polish` 的可用狀態。

### 6.3 一鍵流程

給定：

```text
meeting/
  meeting.mp4
```

執行：

```bash
media2md ./meeting
```

預期產生：

```text
meeting/transcript/
meeting/polished/
```

### 6.4 舊流程不破壞

以下指令仍可單獨使用：

```bash
transcribe-audio ./meeting
```

並仍只產生 raw transcript。

## 7. 建議實作順序

1. 新增 `bin/media2md`。
2. 修改 `install.sh` 同時安裝 `media2md`。
3. 更新 README 與 docs/INSTALL.md。
4. 視需要新增 `transcribe-audio --transcript-dir`。
5. 加入手動測試案例。

## 8. Remaining items

- 其他更細的 wrapper 拆分參數（例如 `--force-transcribe`、`--force-polish`、`--skip-transcribe`、`--skip-polish`）可視後續需要再評估。
