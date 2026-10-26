# Ordena el Armario

> 整理衣櫃的中文方位詞聽力遊戲

- **網址：** https://wangchiapin.github.io/Ordena-el-Armario/
- **Firebase 專案：** memorma-24dab（只用在排行榜，集合 `ordena_leaderboard`，與 Memorama、色數消消樂共用）
- **登入方式：** 匿名登入
- **狀態：** 使用中

## 玩法
- 語音念指令，玩家把物品放進 3×3 櫃子：點物品 → 點格子，或直接拖曳。
- 點物品時會念出物品名稱。

## 設定（右上角 ⚙️，記在玩家瀏覽器）
- 字體：繁體（預設）／简体
- 介面語言：Español（預設）／English／只有中文
- 發音標示：不顯示／拼音／注音／兩種都顯示（台灣讀音）
- 語速：慢／正常／快（和其他遊戲共用）
- 語音一律念繁體、台灣讀音

## 排行榜
- 錯誤少的排前面，錯誤一樣比時間。
- 玩完後輸入名字才存；每台裝置只留最好成績。
- 有開「顯示指令文字」的成績會標「con texto／with text」。

## 圖片
`images/圖片{id}.webp`（300×300）。程式依序找 `.webp` → `.png` → 顯示文字。

## Firebase 規則
Firebase 規則的正本放在私人 repo `game-kit` 的 `firebase-rules/`（memorma-24dab 專案共用一份規則）。這個 repo 不再放規則檔。

## 手機瀏覽器備註：捲動後回不到頂端（2026-10-24）
iPhone 版 Chrome 上，頁面可以捲動時，往下捲之後有時回不到最上面（Safari 正常）。
處理方式（已套用在本遊戲）：
- `<meta name="viewport">` 設 `maximum-scale=1`，不使用 `viewport-fit=cover`。
- `<html>` 加 `html{color-scheme:light}`。

兩項一起改後，手機 Chrome 測試恢復正常；尚未分開測是哪一項有效。新增頁面請照這個寫。
