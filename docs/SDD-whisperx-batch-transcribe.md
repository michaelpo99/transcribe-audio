# SDD: transcribe-audio 批次轉錄工具

最後更新：2026-06-21
適用 repo：transcribe-audio

本文件已隨 `transcribe-audio` 拆分為獨立 repo 進入重新整理狀態。

目前有效邊界：

- 本 repo 只提供 `transcribe-audio`。
- 獨立抽音軌工具由 `extract-audio` repo 維護。
- 本工具負責掃描音檔與影片檔，必要時做轉錄前音軌處理，再產生 transcript。
- SRT 輸出可依 WhisperX alignment words 做後處理；行為見
  `docs/SDD-CR-004-word-timed-srt-postprocessing.md`。
- 潤稿與 Markdown 整理不屬於本工具範圍。

後續若要調整輸出 layout、metadata 位置、或與 `transcript-polish` 合併，應另開 CR。
