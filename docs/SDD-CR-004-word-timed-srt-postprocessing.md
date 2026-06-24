# SDD/CR-004：詞級時間字幕重切與清理

狀態：Completed
日期：2026-06-25
適用 repo：transcribe-audio

Python package、Bash/Python 邊界、venv、安裝與測試規範見：

```text
docs/SDD-ARCH-python-subtitle-postprocessing.md
```

## 1. 背景

目前 `transcribe-audio` 直接使用 WhisperX 產生 SRT。WhisperX 完成 alignment
後雖然可能具有詞級時間，但輸出的 SRT 仍以較大的 segment 為單位，因此會出現：

- 單一字幕持續時間過長。
- 單一字幕文字過多，佔滿大部分畫面。
- 同一句、短語、笑聲或辨識幻覺重複出現。
- 事後只讀 SRT 時，只能看到 segment 的起訖時間，無法利用原有詞級時間精準重切。

本 CR 在 WhisperX 與最終 SRT 之間加入字幕後處理。後處理應優先使用
WhisperX alignment JSON 的詞級時間，自行決定字幕邊界；只有在詞級時間缺失時，
才使用 segment 時間做比例分配。

## 2. 目標

當輸出格式包含 SRT 時，預設產生適合直接觀看的字幕：

```text
WhisperX alignment result
  -> 保留原始 WhisperX SRT
  -> 依詞級時間重切字幕
  -> 視設定執行 srt-clean
  -> 輸出主要 SRT
```

輸出範例：

```text
transcript/
├── meeting.srt
├── meeting.whisperx.raw.srt
└── meeting.clean-report.txt
```

其中：

- `meeting.srt` 是重切及清理後的主要字幕。
- `meeting.whisperx.raw.srt` 是未經本功能修改的 WhisperX 原始字幕。
- `meeting.clean-report.txt` 只在實際執行 `srt-clean` 且工具有產生報告時保留。

## 3. CLI 設計

### 3.1 字幕後處理模式

新增：

```bash
transcribe-audio \
  --subtitle-postprocess off|split|clean \
  [其他參數] [輸入]
```

模式語意：

| 模式 | 行為 |
| --- | --- |
| `off` | 保留目前行為，直接使用 WhisperX 產生的 SRT，不建立 raw 備份 |
| `split` | 保留 raw SRT，執行內建詞級重切，不呼叫 `srt-clean` |
| `clean` | 保留 raw SRT，先執行內建詞級重切，再於可用時呼叫 `srt-clean` |

當輸出格式為 `srt` 或 `all` 時，預設模式為 `clean`。非 SRT 輸出不執行字幕後處理。

### 3.2 清理 profile

新增：

```bash
transcribe-audio \
  --subtitle-clean-profile PROFILE \
  [其他參數] [輸入]
```

規則：

- 只有 `--subtitle-postprocess clean` 會使用此參數。
- 使用者指定 profile 時，直接將該值傳給 `srt-clean`。
- 未指定時，日文自動使用 `jp-adult-soft`。
- 未指定時，英文自動使用 `en-adult-soft`。
- 其他語言不自動選 profile，只執行內建重切。
- 指定 `--subtitle-clean-profile` 但找不到 `srt-clean` 時，顯示警告並繼續完成內建重切。

## 4. WhisperX 輸出與資料來源

### 4.1 自動取得詞級資料

使用者不需要額外要求 JSON。當輸出包含 SRT 且後處理模式不是 `off` 時，
`transcribe-audio` 應確保 WhisperX 同一次轉錄產生 alignment JSON，並讀取：

```text
segments[].start
segments[].end
segments[].text
segments[].words[].word
segments[].words[].start
segments[].words[].end
```

此 JSON 是後處理的中間資料。若使用者原本沒有要求 JSON 輸出，處理完成後不必將
它視為公開產物；實作可使用暫存位置，避免改變既有輸出集合。

### 4.2 原始 SRT 備份

在 `split` 或 `clean` 模式：

1. WhisperX 原始 SRT 先保存為 `<stem>.whisperx.raw.srt`。
2. 內建後處理結果寫入 `<stem>.srt`。
3. 若執行 `srt-clean`，清理後結果取代 `<stem>.srt`，但不可修改 raw 備份。

若後處理失敗，應保留 raw SRT，報告失敗並將該檔案視為轉錄失敗，不得以不完整的
處理結果覆蓋主要 SRT。

## 5. 內建字幕重切

### 5.1 預設限制

第一版採用以下預設值：

| 限制 | 預設值 |
| --- | --- |
| 每段最多行數 | 2 行 |
| 每行最大顯示寬度 | 約 42 display columns |
| 每段最短時間 | 約 0.8 秒 |
| 每段最長時間 | 約 7 秒 |

顯示寬度應以終端顯示寬度概念計算，而不是單純字元數。全形 CJK 字元通常計為
2 columns，半形拉丁字母、數字及標點通常計為 1 column。

### 5.2 切分優先順序

重切時依序考慮：

1. 強標點，例如 `。`、`！`、`？`、`.`、`!`、`?`。
2. 弱標點，例如 `、`、`，`、`,`、`;`、`；`。
3. 詞與詞之間明顯的時間停頓。
4. 顯示寬度及最長持續時間限制。
5. 找不到自然邊界時，在不遺失文字的前提下使用最近的詞邊界強制切分。

日文及其他無空格文本不得依空白作為唯一切分依據，應結合 alignment words、
標點、停頓與顯示寬度。

### 5.3 詞級時間決定

若新字幕段內至少有可用的詞級時間：

- `start` 取該段第一個有時間詞的 `start`。
- `end` 取該段最後一個有時間詞的 `end`。
- 相鄰字幕不得重疊。
- 時間應限制在原始 WhisperX segment 的起訖範圍內。

標點或未對齊詞沒有時間時，應附著於相鄰的有時間詞，不得因缺少時間而遺失。

### 5.4 詞級時間缺失的 fallback

若某個切分區間沒有足夠詞級時間，使用原始 segment 的時間範圍按文字顯示寬度比例
分配。fallback 必須符合：

- 第一段不得早於原始 segment `start`。
- 最後一段不得晚於原始 segment `end`。
- 中間切點保持單調遞增。
- 相鄰字幕不得重疊。
- 不得因 fallback 刪除或重複原文。
- 極短 segment 無法同時滿足最短持續時間時，優先保留原始時間邊界。

### 5.5 短段合併

重切後低於約 0.8 秒的字幕，若合併後仍符合兩行、顯示寬度及最長時間限制，
應優先與語意及時間上較接近的前段或後段合併。無法安全合併時保留短段，
不得擴張到與相鄰字幕重疊。

## 6. srt-clean 整合

`clean` 模式下：

1. 先完成內建詞級重切。
2. 檢查 `srt-clean` 是否可在 `PATH` 找到。
3. 有可用 profile 時，以重切後 SRT 為輸入執行清理。
4. 將清理結果寫回主要 `<stem>.srt`。
5. 保留工具產生的 `<stem>.clean-report.txt`。

`srt-clean` 主要處理：

- 單一 cue 內重複短語。
- 連續重複的假名、笑聲或噪音。
- profile 已知的 ASR 幻覺內容。

若找不到 `srt-clean`，應顯示一次清楚警告，保留內建重切結果並繼續處理其他檔案。
這不是轉錄失敗。

若 `srt-clean` 已找到但執行失敗，應保留內建重切結果、記錄警告並繼續，不得破壞
raw 備份或主要 SRT。

## 7. 相容性與範圍

既有 batch、single-file、glob 及 regex selector 行為維持不變。

以下輸出不受字幕後處理影響：

```text
txt
json
vtt
tsv
aud
```

`--subtitle-postprocess off` 必須維持既有 SRT 行為，以便比較輸出及處理特殊素材。

本 CR 第一版不包含：

- 變更 WhisperX 模型、語言偵測或 alignment 模型。
- 對 VTT 套用相同重切流程。
- 使用語言模型摘要、改寫或翻譯字幕。
- 在內建重切階段刪除疑似幻覺文字。
- 取代 `srt-clean` 的完整規則系統。
- 提供所有寬度、行數及時間限制的 CLI 微調參數。

## 8. 驗收標準

### 8.1 詞級時間重切

給定一個具有多個 `words[]` 的長 segment：

- 應產生多個字幕段。
- 每段 `start` 與 `end` 應對應該段首尾詞時間。
- 字幕時間單調遞增且互不重疊。
- 所有原文只出現一次。

### 8.2 部分時間缺失

給定部分詞缺少 `start` 或 `end`：

- 有時間的區間優先使用詞級時間。
- 無法定時的區間使用 segment 比例 fallback。
- 不遺失、不重複文字，且時間不超出原始 segment。

### 8.3 日文無空格文本

給定含日文標點或詞間停頓的長文本：

- 能在自然標點或停頓附近切分。
- 不依賴空白才能切分。
- 主要字幕原則上不超過兩行，每行約 42 display columns。

### 8.4 長度與持續時間

- 超過約 7 秒的長字幕應繼續切分。
- 低於約 0.8 秒的短字幕在符合限制時應合併。
- 無法同時滿足所有限制時，優先確保時間合法、文字完整及字幕不重疊。

### 8.5 raw 與主要輸出

在 `split` 或 `clean` 模式：

- `<stem>.whisperx.raw.srt` 保留 WhisperX 原始內容。
- `<stem>.srt` 是後處理結果。
- 重複執行時不得把已處理 SRT 當成 raw 來源。

在 `off` 模式：

- `<stem>.srt` 維持 WhisperX 原始輸出。
- 不要求建立 `<stem>.whisperx.raw.srt`。

### 8.6 srt-clean

- 日文自動使用 `jp-adult-soft`。
- 英文自動使用 `en-adult-soft`。
- 指定 profile 時覆寫語言自動選擇。
- 已安裝時能移除 profile 判定的重複或幻覺內容，並保留 report。
- 未安裝時只警告一次，主要 SRT 仍由內建重切成功產生。
- 執行失敗時保留內建重切結果及 raw 備份。

### 8.7 既有功能

- `txt`、`json`、`vtt`、`tsv` 及 `aud` 的產物與既有行為一致。
- batch 與 selector 模式均能套用字幕後處理。
- `--subtitle-postprocess off` 可回復既有 SRT 行為。

## 9. 建議實作順序

1. 依 Python 架構文件建立 `pyproject.toml`、`src/transcribe_audio/` 與測試骨架。
2. 讓 SRT 後處理模式自動取得 WhisperX alignment JSON。
3. 建立 JSON 解析、display width 計算及 SRT 寫入元件。
4. 實作詞級切分、fallback 分配、短段合併及時間合法性檢查。
5. 加入 raw SRT 備份與原子性主要檔案替換。
6. 整合可選的 `srt-clean` 與語言 profile 對應。
7. 更新 install、CLI help、README 與 INSTALL 說明。
8. 以 synthetic fixtures 與去識別化的 WhisperX 結構完成驗收測試。

## 10. 實作結果

- Bash 保留 media、FFmpeg、WhisperX 與產物流程責任。
- Python package 位於 `src/transcribe_audio/`，負責 JSON、詞級時間、切分、fallback、
  SRT writer、驗證與 cleaner adapter。
- `srt` 模式使用暫存 WhisperX `all` 輸出取得 alignment JSON，不額外公開內部 JSON。
- `all` 模式保留 JSON、TXT 等原有產物，只將原始 SRT 改名為 raw 備份。
- `srt-clean` 缺失或失敗時保留 split SRT；缺失警告每次執行只顯示一次。
- 安裝使用獨立 `~/.venvs/transcribe-audio`，不修改 WhisperX venv。

完成時自動測試涵蓋 parser、writer、Unicode width、詞級時間、interpolation、
proportional fallback、日文無空格文本、短段合併、原子輸出、安裝、fake WhisperX
pipeline、`off`、`split`、`clean`、`all`、profile 對應及 cleaner 降級。

另以本機既有長 SRT 做不提交內容的 regression：

```text
raw cues                         345
raw cues over 84 columns         104
raw cues over 7 seconds          262
split cues over 2 x 42 columns   0
split cues over 7 seconds        0
```

最後以 12 秒日文音訊片段執行真實 WhisperX 3.8.6 alignment smoke test：

```text
WhisperX raw SRT cues       1
word-timed final SRT cues   4
srt-clean report            generated
temporary alignment JSON    removed
pipeline result             success
```
