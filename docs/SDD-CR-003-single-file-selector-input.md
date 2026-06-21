# SDD/CR-003：single-file and selector input support

狀態：Completed
日期：2026-06-21
適用 repo：transcribe-audio

## 1. 背景

目前 `transcribe-audio` 與 `media2md` 主要以目錄為輸入：

```bash
transcribe-audio ./meeting
media2md ./meeting
```

這適合批次處理，但常見情境是：同一個目錄裡有很多檔案，使用者只想補跑其中一個檔案，或只處理主檔名符合條件的一小批檔案。

`transcript-polish` 已支援單一文字檔輸入，因此本 CR 的重點是讓 `transcribe-audio` 與 `media2md` 支援單檔與 selector 模式。

## 2. 目標

新增以下用法：

```bash
transcribe-audio --file ./meeting/a.mp4
transcribe-audio --file a ./meeting
media2md --file ./meeting/a.mp4
media2md --file a ./meeting
```

預期：

```text
media2md --file a ./meeting
  -> 只處理符合 selector 的 media file
  -> 產生 ./meeting/transcript/a.txt
  -> 只 polish ./meeting/transcript/a.txt
  -> 產生 ./meeting/polished/a.md
```

## 3. 指令設計

### 3.1 `transcribe-audio`

新增：

```bash
transcribe-audio --file INPUT [目錄]
transcribe-audio --glob PATTERN [目錄]
transcribe-audio --regex PATTERN [目錄]
transcribe-audio --all-matches --file INPUT [目錄]
```

### 3.2 `media2md`

新增同樣 selector 參數：

```bash
media2md --file INPUT [目錄]
media2md --glob PATTERN [目錄]
media2md --regex PATTERN [目錄]
media2md --all-matches --file INPUT [目錄]
```

`--file`、`--glob`、`--regex` 互斥。

## 4. Selector 規則

### 4.1 `--file INPUT`

`--file` 支援兩種情境：

1. 若 `INPUT` 是存在的檔案路徑，直接處理該檔案。
2. 若 `INPUT` 不是存在的檔案路徑，視為主檔名前綴 selector。

前綴 selector 規則：

- 只搜尋 target directory 第一層。
- 只匹配目前 `transcribe-audio` 已支援的 media files。
- 比對時忽略副檔名，只看 basename stem。
- stem 以 selector 開頭即匹配。
- selector 是 literal string，不解讀 wildcard 或 regular expression。

範例：

```text
meeting/
├── 會議A.mp4
├── 會議A.m4a
├── 會議B.mov
└── notes.txt
```

```bash
media2md --file 會議A ./meeting
```

會匹配 media stem 以 `會議A` 開頭的檔案，但不會匹配 `notes.txt`。

### 4.2 `--glob PATTERN`

`--glob` 使用 shell-style wildcard，但只比對 basename stem，不比對副檔名。

範例：

```bash
media2md --glob '會議*' ./meeting
transcribe-audio --glob 'A00[1-5]*' ./meeting
```

使用者應用引號包住 pattern，避免 shell 先展開。

### 4.3 `--regex PATTERN`

`--regex` 使用 regular expression，比對 basename stem，不比對副檔名。

範例：

```bash
media2md --regex '^會議[0-9]+' ./meeting
transcribe-audio --regex '^A00[1-5]' ./meeting
```

### 4.4 多筆匹配

若 selector 匹配 0 筆，應報錯。

若 selector 匹配多筆，預設應報錯並列出候選，避免誤處理：

```text
錯誤：selector 匹配到多個 media files，請指定更精確的 selector，或使用 --all-matches。
```

若使用者加上 `--all-matches`，則處理所有匹配檔案。

## 5. Target directory 推導

若 `--file INPUT` 是存在的檔案路徑：

- target directory 預設為該檔案的 parent directory。
- 若同時提供 `[目錄]`，該目錄應與檔案 parent directory 一致，否則報錯。

若 `INPUT` 是 selector：

- 若有提供 `[目錄]`，在該目錄第一層搜尋。
- 若沒有提供 `[目錄]`，在目前工作目錄搜尋。

## 6. media2md selector 行為

`media2md` 在 selector 模式下不應做整個 transcript 目錄的 batch polish。

應使用：

```bash
transcript-polish --file <transcript-dir>/<stem>.txt --output-dir <polished-dir>
```

而不是：

```bash
transcript-polish --dir <transcript-dir> --output-dir <polished-dir>
```

若 `transcribe-audio` 沒有產生預期 transcript，`media2md` 應報錯並印出預期路徑。

## 7. 與既有 batch 模式的關係

既有行為維持不變：

```bash
transcribe-audio ./meeting
media2md ./meeting
```

仍是：

```text
先整批 transcribe，再整批 polish。
```

selector 模式才採用單檔或多檔精準處理。

## 8. 驗收標準

### 8.1 單一實際路徑

```bash
media2md --file ./meeting/a.mp4
```

應只處理 `a.mp4`，並產生：

```text
meeting/transcript/a.txt
meeting/polished/a.md
```

### 8.2 前綴 selector

```bash
media2md --file a ./meeting
```

若只匹配一個 media file，應成功。

若匹配多個 media files，應 fail 並列出候選。

### 8.3 glob selector

```bash
media2md --glob 'A00*' --all-matches ./meeting
```

應處理所有 stem 符合 `A00*` 的 media files。

### 8.4 regex selector

```bash
media2md --regex '^A00[1-5]' --all-matches ./meeting
```

應處理所有 stem 符合 regex 的 media files。

### 8.5 batch 模式不破壞

```bash
media2md ./meeting
```

仍維持既有 batch 行為。

## 9. 文件更新

README 與 docs/INSTALL.md 應新增範例：

```bash
transcribe-audio --file ./meeting/a.mp4
transcribe-audio --file a ./meeting
transcribe-audio --glob '會議*' ./meeting
transcribe-audio --regex '^A00[1-5]' ./meeting

media2md --file ./meeting/a.mp4
media2md --file a ./meeting
media2md --glob '會議*' ./meeting
media2md --regex '^A00[1-5]' ./meeting
```

並說明：

- `--file` 預設是主檔名前綴匹配。
- `--file` 不解讀 wildcard 或 regex。
- wildcard 使用 `--glob`。
- regular expression 使用 `--regex`。
- 多筆匹配預設失敗；要處理全部需加 `--all-matches`。

## 10. 不納入本次 CR

本次不做：

- `transcript-polish --output-file`。
- 改變 `transcript-polish --file` 既有語意。
- 改變 `media2md ./meeting` 預設 batch 行為。
- 讓 `--file` 自動解析 wildcard 或 regex。
- 遞迴掃描子目錄。
- 多筆匹配時自動選第一筆。

## 11. 建議實作順序

1. 抽出 supported media extension 與 media scanning 邏輯，讓 batch 與 selector 共用。
2. 新增 selector resolver：actual file path、literal prefix、glob、regex。
3. 在 `transcribe-audio` 加入 `--file`、`--glob`、`--regex`、`--all-matches`。
4. 在 selector 模式只建立 selected files queue，不掃描整個目錄。
5. 在 `media2md` 加入同樣 selector 參數。
6. 讓 `media2md` selector 模式只 polish 對應 transcript files。
7. 更新 README 與 docs/INSTALL.md。
8. 加入手動測試案例。
