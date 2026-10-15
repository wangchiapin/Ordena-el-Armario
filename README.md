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
- 介面語言：Español（預設）／English
- 發音標示：不顯示／拼音／注音／兩種都顯示（台灣讀音）
- 語音一律念繁體、台灣讀音

## 排行榜
- 錯誤少的排前面，錯誤一樣比時間。
- 玩完後輸入名字才存；每台裝置只留最好成績。
- 有開「顯示指令文字」的成績會標「con texto／with text」。

## 圖片
`images/圖片{id}.webp`（300×300）。程式依序找 `.webp` → `.png` → 顯示文字。

## Firebase 規則
`firestore-rules-full.txt` 是 memorma-24dab 的完整規則（含 Memorama、本遊戲、色數消消樂）。
