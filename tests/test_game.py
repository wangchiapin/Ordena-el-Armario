# 收納小達人（Ordena el Armario）測試：不改遊戲本體，完全用畫面操作（讀「念出來的句子」判斷該放哪個物品、哪一格）
# 涵蓋：九格方位句、相對方位句、放對／放錯物品／放錯位置、已放的格子、結算、排行榜、重新開始、設定每個值
import sys, re, json
from playwright.sync_api import sync_playwright
import common
from common import *

R = Runner()
ABS = ['左上角', '正上方', '右上角', '左邊', '正中間', '右邊', '左下角', '正下方', '右下角']
DIRS = {'上面': (-1, 0), '下面': (1, 0), '左邊': (0, -1), '右邊': (0, 1)}

FAKE_FB = r"""
(function(){
  window.__db = window.__db || {}; window.__ops = window.__ops || [];
  if (window.firebase && window.firebase.__fake) return;
  const DB = window.__db, ops = window.__ops, clone = x => JSON.parse(JSON.stringify(x));
  const depth = p => p.split('/').length;
  function docRef(path){ return { path, id: path.split('/').pop(),
    async get(){ return { exists: path in DB, data: () => DB[path] && clone(DB[path]) }; },
    async set(d){ ops.push({k:'set', p:path, d:clone(d)}); DB[path] = clone(d); },
    async update(d){ DB[path] = Object.assign(DB[path]||{}, clone(d)); },
    async delete(){ delete DB[path]; },
    onSnapshot(){ return () => {}; } }; }
  function colRef(path){ const q = { doc: id => docRef(path + '/' + id),
    async add(d){ if (window.__failAdd) throw new Error('add-fail'); ops.push({k:'add', p:path, d:clone(d)}); const id = 'A' + ops.length; DB[path + '/' + id] = clone(d); return { id }; },
    where(){ return q; }, orderBy(){ return q; }, limit(){ return q; },
    async get(){ const ks = Object.keys(DB).filter(k => k.startsWith(path + '/') && depth(k) === depth(path) + 1);
      const rows = ks.map(k => clone(DB[k])).sort((a,b)=>(b.score||0)-(a.score||0));
      return { empty: rows.length === 0, docs: rows.map(r => ({ data: () => r })), size: rows.length, forEach(fn){ rows.forEach(r => fn({ data: () => r })); } }; } };
    return q; }
  const auth = { currentUser: null, async signInAnonymously(){ auth.currentUser = { uid: window.__uid || 'UID1' }; return { user: auth.currentUser }; } };
  const fsInst = { collection: colRef, async runTransaction(fn){ return fn({ get: r => r.get(), set(r, d){ DB[r.path] = clone(d); }, update(r, d){ DB[r.path] = Object.assign(DB[r.path]||{}, clone(d)); } }); } };
  const fire = () => fsInst; fire.FieldValue = { serverTimestamp: () => 'TS', delete: () => null, increment: () => 1 };
  fire.Timestamp = { now: () => ({ toMillis: () => Date.now() }), fromMillis: m => ({ toMillis: () => m }) };
  window.firebase = { __fake: true, apps: [], auth: () => auth, firestore: fire, initializeApp(){ return {}; } };
})();
"""
def route(r):
    u = r.request.url
    if u.startswith('file:'): return r.continue_()
    if 'gstatic.com/firebasejs' in u:
        if common.BLOCK_FB: return r.abort()
        return r.fulfill(status=200, content_type='application/javascript', body=FAKE_FB if 'firebase-app-compat' in u else '')
    r.abort()
common.BLOCK_FB = False
common.route = route

def page(p, settings=None, flags=None, width=1000, height=800):
    init = "window.confirm=()=>true;"
    for k, v in (flags or {}).items(): init += "window.%s=%s;" % (k, json.dumps(v))
    return open_page(p, settings=settings, width=width, height=height, wait=1500, extra_init=init)

def last_spoken(pg): return pg.evaluate("(window.__spoken[window.__spoken.length-1]||{}).text||''")

def tiles(pg):
    # itemId → 物品名稱（繁體，來自 aria-label）
    return pg.evaluate("Object.fromEntries([...document.querySelectorAll('#tray .item-tile')].map(t=>[t.dataset.itemId,t.getAttribute('aria-label')]))")

def filled(pg):
    return pg.evaluate("Object.fromEntries([...document.querySelectorAll('#shelfGrid .shelf-cell.filled')].map(c=>[c.dataset.cell,(c.querySelector('[data-item-id]')||{}).dataset?.itemId]))")

def solve(pg, sentence):
    """由念出來的句子，算出要放的物品 id 與格子"""
    tl = tiles(pg); by_name = {v: k for k, v in tl.items()}
    m = re.match(r'^把(.+?)放到櫃子的(.+)。$', sentence)
    if m:
        return by_name[m.group(1)], ABS.index(m.group(2)), 'absolute'
    m = re.match(r'^把(.+?)放在(.+?)的(上面|下面|左邊|右邊)。$', sentence)
    assert m, '看不懂的句子：' + sentence
    ref_item = by_name[m.group(2)]
    fl = filled(pg)
    ref_cell = [int(c) for c, i in fl.items() if i == ref_item]
    assert ref_cell, '參照物品還沒放上去：' + sentence
    r, c = divmod(ref_cell[0], 3); dr, dc = DIRS[m.group(3)]
    return by_name[m.group(1)], (r + dr) * 3 + (c + dc), 'relative'

def tap(pg, item_id, cell):
    pg.click(f'#tray .item-tile[data-item-id="{item_id}"]')
    pg.click(f'#shelfGrid .shelf-cell[data-cell="{cell}"]')

def play_full(pg, mistakes=0, wait=650):
    """玩完整一局，回傳 (句子型態列表, 答錯次數)"""
    kinds = []; errs = 0
    for step in range(9):
        s = last_spoken(pg)
        item, cell, kind = solve(pg, s); kinds.append(kind)
        if step < mistakes:
            other = [i for i in tiles(pg) if i != item and i not in filled(pg).values()][0]
            tap(pg, other, cell); errs += 1; pg.wait_for_timeout(80)
        tap(pg, item, cell)
        pg.wait_for_timeout(wait)
    return kinds, errs

with sync_playwright() as p:
    # ───── 1) 開頁、開始、第一題 ─────
    b, pg, errs = page(p)
    R.check(pg.evaluate("document.querySelectorAll('#shelfGrid .shelf-cell').length") == 9, '九宮格櫃子 9 格')
    R.check(pg.inner_text('#instructionText').strip() != '' and pg.is_disabled('#replayBtn'), '還沒開始：顯示說明、重聽鈕停用')
    pg.click('#startBtn'); pg.wait_for_timeout(500)
    R.check(pg.evaluate("document.querySelectorAll('#tray .item-tile').length") == 9, '托盤有 9 個物品')
    R.check(len(set(tiles(pg).values())) == 9, '9 個物品不重複')
    s = last_spoken(pg)
    R.check(re.match(r'^把.+放(到櫃子的|在).+。$', s) is not None, '開始就念出第一題：「%s」' % s)
    R.check(pg.is_enabled('#replayBtn'), '可以重聽')
    pg.evaluate("window.__spoken.length=0"); pg.click('#replayBtn'); pg.wait_for_timeout(100)
    R.check(last_spoken(pg) == s, '重聽：念同一句')
    R.check(re.match(r'^把.+放到櫃子的.+。$', s) is not None, '第一題一定是絕對位置句（櫃子還是空的，沒有參照物）')
    b.close()

    # ───── 2) 放對／放錯 ─────
    b, pg, errs = page(p)
    pg.click('#startBtn'); pg.wait_for_timeout(500)
    s = last_spoken(pg); item, cell, kind = solve(pg, s)
    others = [i for i in tiles(pg) if i != item]
    wrong_cell = (cell + 1) % 9
    # 放錯物品（位置對）
    tap(pg, others[0], cell); pg.wait_for_timeout(100)
    R.check(pg.inner_text('#errNum') == '1' and 'err' in (pg.get_attribute('#feedback', 'class') or ''), '放錯物品：錯誤 +1、顯示錯誤回饋')
    R.check(pg.evaluate("document.querySelector('#shelfGrid .shelf-cell[data-cell=\"%d\"]').classList.contains('filled')" % cell) is False, '放錯物品：沒有放進去')
    fb1 = pg.inner_text('#feedback')
    # 放錯位置（物品對）：選取還在，直接點別格
    pg.click(f'#tray .item-tile[data-item-id="{item}"]'); pg.click(f'#shelfGrid .shelf-cell[data-cell="{wrong_cell}"]'); pg.wait_for_timeout(100)
    R.check(pg.inner_text('#errNum') == '2' and pg.inner_text('#feedback') != fb1, '放錯位置：錯誤 +1、提示文字和「放錯物品」不同（%s ≠ %s）' % (pg.inner_text('#feedback'), fb1))
    R.check(pg.evaluate("document.querySelector('#tray .item-tile.selected')!==null"), '放錯位置後選取還在，可直接點別格')
    pg.evaluate("window.__spoken.length=0"); pg.wait_for_timeout(900)
    R.check(last_spoken(pg) == s, '放錯後約 0.6 秒自動重念同一句')
    # 放對
    pg.click(f'#shelfGrid .shelf-cell[data-cell="{cell}"]'); pg.wait_for_timeout(150)
    R.check(pg.evaluate("document.querySelector('#shelfGrid .shelf-cell[data-cell=\"%d\"]').classList.contains('filled')" % cell), '放對：格子被填滿')
    R.check('ok' in (pg.get_attribute('#feedback', 'class') or ''), '放對：顯示正確回饋')
    R.check(pg.evaluate("document.querySelector('#tray .item-tile[data-item-id=\"%s\"]').classList.contains('placeholder')" % item), '托盤裡該物品變成空位')
    R.check(pg.inner_text('#errNum') == '2', '放對不加錯誤')
    # 放對後 0.5 秒內不接受放置
    pg.wait_for_timeout(900)
    s2 = last_spoken(pg); R.check(s2 != s and s2.startswith('把'), '放對後自動出下一題：「%s」' % s2)
    # 已放過的格子再放：不算錯
    e0 = pg.inner_text('#errNum')
    nxt = [i for i in tiles(pg) if i != item and i not in filled(pg).values()][0]
    pg.click(f'#tray .item-tile[data-item-id="{nxt}"]'); pg.click(f'#shelfGrid .shelf-cell[data-cell="{cell}"]'); pg.wait_for_timeout(100)
    R.check(pg.inner_text('#errNum') == e0, '點已經放好的格子：不算錯')
    # 已放進去的物品不能再選
    pg.evaluate("id=>[...document.querySelectorAll('#tray .item-tile')].find(t=>t.dataset.itemId===id).click()", item); pg.wait_for_timeout(100)
    R.check(pg.evaluate("document.querySelector('#tray .item-tile.selected')?.dataset.itemId") != item, '已放好的物品不能再被選取')
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    b.close()

    # ───── 3) 完整玩一局（含故意放錯）＋結算 ─────
    b, pg, errs = page(p)
    pg.click('#startBtn'); pg.wait_for_timeout(500)
    kinds, made = play_full(pg, mistakes=3)
    pg.wait_for_timeout(500)
    R.check(pg.is_visible('#endOverlay'), '九題完成：跳出結算視窗')
    R.check(pg.inner_text('#finalErrors') == str(made), f'結算錯誤數＝故意放錯的次數 {made}')
    R.check(re.match(r'\d\d:\d\d$', pg.inner_text('#finalTime')) is not None, '結算時間格式 mm:ss：' + pg.inner_text('#finalTime'))
    R.check(set(filled(pg).keys()) == set(map(str, range(9))), '九格都放滿了')
    R.check(len(set(filled(pg).values())) == 9, '九格是 9 個不同物品')
    R.check(kinds[0] == 'absolute' and all(k in ('absolute', 'relative') for k in kinds), '句型：第一題絕對位置；其餘 %s' % ''.join(k[0] for k in kinds))
    R.check(pg.evaluate("document.getElementById('instructionText').textContent") == pg.evaluate("document.querySelector('[data-i18n=done]')?.textContent || document.getElementById('instructionText').textContent"), '說明區顯示完成訊息')
    # 排行榜：沒名字
    pg.fill('#nameInput', ''); pg.click('#saveBtn'); pg.wait_for_timeout(200)
    R.check(pg.inner_text('#saveStatus').strip() != '' and pg.evaluate("Object.keys(window.__db||{}).length") == 0, '沒填名字按儲存：提示，不上傳')
    pg.fill('#nameInput', 'Ana'); pg.click('#saveBtn'); pg.wait_for_timeout(600)
    doc = pg.evaluate("window.__db['ordena_leaderboard/UID1']")
    R.check(doc is not None and doc['name'] == 'Ana' and doc['errors'] == made, '上傳成功：{name:Ana, errors:%d}' % made)
    secs = doc['secs']
    R.check(doc['secs'] >= 10 and doc['rank'] == (999 - made) * 100000 + (99999 - secs), f'名次值＝(999−錯誤)×100000＋(99999−秒數)：{doc["rank"]}')
    R.check(doc['script'] == 'trad' and doc['lang'] == 'es' and doc['textAid'] is False, '帶上字形、語言、是否用過文字提示')
    R.check(pg.is_disabled('#saveBtn'), '儲存後按鈕停用（不重複送）')
    pg.click('#endRankBtn'); pg.wait_for_timeout(600)
    R.check('Ana' in pg.inner_text('#lbList'), '排行榜列出 Ana：' + pg.inner_text('#lbList').replace('\n', ' ')[:40])
    pg.click('#rankClose')
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    # 再玩一局（更差）→ 不覆蓋
    pg.click('#restartBtn'); pg.wait_for_timeout(500)
    kinds, made2 = play_full(pg, mistakes=5); pg.wait_for_timeout(500)
    pg.fill('#nameInput', 'Ana'); pg.click('#saveBtn'); pg.wait_for_timeout(600)
    doc2 = pg.evaluate("window.__db['ordena_leaderboard/UID1']")
    R.check(doc2['errors'] == made, '第二局錯更多：不覆蓋舊成績（仍 %d 錯）' % made)
    R.check('Ana' not in pg.inner_text('#saveStatus') and pg.inner_text('#saveStatus').strip() != '', '提示「沒有比之前好」：' + pg.inner_text('#saveStatus'))
    # 再玩一局（0 錯）→ 覆蓋
    pg.click('#restartBtn'); pg.wait_for_timeout(500)
    kinds, made3 = play_full(pg, mistakes=0); pg.wait_for_timeout(500)
    pg.fill('#nameInput', 'Ana'); pg.click('#saveBtn'); pg.wait_for_timeout(600)
    doc3 = pg.evaluate("window.__db['ordena_leaderboard/UID1']")
    R.check(doc3['errors'] == 0, '第三局 0 錯：覆蓋成新紀錄')
    b.close()

    # 多玩幾局確認句型有相對方位句，而且每題都解得出來
    b, pg, errs = page(p)
    allk = []
    for g in range(3):
        pg.click('#startBtn') if g == 0 else pg.click('#restartBtn')
        pg.wait_for_timeout(500)
        k, _ = play_full(pg, 0, wait=620); allk += k; pg.wait_for_timeout(400)
    R.check('relative' in allk and 'absolute' in allk, f'3 局 27 題：兩種句型都出現（相對 {allk.count("relative")}、絕對 {allk.count("absolute")}）')
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    b.close()

    # 上傳失敗
    common.BLOCK_FB = True
    b, pg, errs = page(p)
    pg.click('#startBtn'); pg.wait_for_timeout(500)
    play_full(pg, 0); pg.wait_for_timeout(500)
    pg.fill('#nameInput', 'Ana'); pg.click('#saveBtn'); pg.wait_for_timeout(600)
    R.check(pg.is_visible('#endOverlay') and pg.inner_text('#saveStatus').strip() != '' and not pg.is_disabled('#saveBtn'), '沒有雲端：顯示儲存失敗，按鈕仍可重按：' + pg.inner_text('#saveStatus'))
    b.close()
    common.BLOCK_FB = False

    # ───── 4) 重新開始 ─────
    b, pg, errs = page(p)
    pg.click('#startBtn'); pg.wait_for_timeout(500)
    tap(pg, *solve(pg, last_spoken(pg))[:2]); pg.wait_for_timeout(700)
    R.check(len(filled(pg)) == 1, '放了一個')
    pg.click('#startBtn'); pg.wait_for_timeout(500)      # 遊戲中按「重新開始」（confirm 已自動同意）
    R.check(len(filled(pg)) == 0 and pg.inner_text('#errNum') == '0' and pg.inner_text('#timerNum') in ('00:00', '00:01'), '重新開始：櫃子清空、錯誤與時間歸零')
    b.close()

    # ───── 5) 設定每個值 ─────
    PY = re.compile('[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]'); ZY = re.compile('[ㄅ-ㄩ]')
    base = {'v': 1, 'script': 'trad', 'lang': 'es', 'phon': 'pinyin', 'rate': 'normal'}
    for key, vals in (('script', ['trad', 'simp']), ('lang', ['es', 'en', 'zh']), ('phon', ['pinyin', 'zhuyin', 'both', 'off']), ('rate', ['slow', 'normal', 'fast'])):
        for v in vals:
            label = f'{key}={v}'
            b, pg, errs = page(p, settings=dict(base, **{key: v}))
            pg.click('#startBtn'); pg.wait_for_timeout(500)
            pg.check('#textToggle'); pg.wait_for_timeout(200)
            txt = pg.inner_text('#instructionText')
            html = pg.inner_html('#instructionText')
            if key == 'script':
                R.check(('柜子' in txt and '櫃' not in txt) if v == 'simp' else ('櫃子' in txt and '柜' not in txt), f'{label}：文字提示字形「{txt.splitlines()[0]}」')
            if key == 'phon':
                got = (bool(PY.search(txt)), bool(ZY.search(txt)))
                want = {'pinyin': (True, False), 'zhuyin': (False, True), 'both': (True, True), 'off': (False, False)}[v]
                R.check(got == want, f'{label}：文字提示 拼音{"有" if got[0] else "無"} 注音{"有" if got[1] else "無"}')
            if key == 'lang':
                btn = pg.inner_text('#startBtn')
                R.check(btn == {'es': 'Reiniciar', 'en': 'Restart', 'zh': '重新開始'}[v], f'{label}：按鈕文字「{btn}」')
            if key == 'rate':
                r = pg.evaluate("window.__spoken.map(s=>s.rate)"); want_r = {'slow': 0.45, 'normal': 0.65, 'fast': 0.85}[v]
                R.check(r and abs(r[0] - want_r) < 1e-6, f'{label}：念出速度 {r[0] if r else None}（應為 {want_r}）')
            R.check(not errs, f'{label}：沒有網頁錯誤 {errs}')
            b.close()
    # 文字提示開關：打勾後算「有用文字提示」
    b, pg, errs = page(p)
    pg.click('#startBtn'); pg.wait_for_timeout(500)
    R.check('cn-line' not in pg.inner_html('#instructionText'), '沒開文字提示：只顯示「請聽」')
    pg.check('#textToggle'); pg.wait_for_timeout(100)
    R.check('cn-line' in pg.inner_html('#instructionText') and last_spoken(pg).rstrip('。') in pg.inner_text('#instructionText').replace('\n', ''), '開文字提示：顯示與念出相同的句子')
    play_full(pg, 0); pg.wait_for_timeout(500)
    R.check(pg.is_visible('#textAidNote'), '用過文字提示：結算顯示「含文字提示」註記')
    pg.fill('#nameInput', 'Ana'); pg.click('#saveBtn'); pg.wait_for_timeout(600)
    R.check(pg.evaluate("window.__db['ordena_leaderboard/UID1'].textAid") is True, '成績標記 textAid=true')
    b.close()
    # 設定存檔 + 其他遊戲同步
    b, pg, errs = page(p)
    pg.click('#settingsBtn'); pg.wait_for_timeout(200)
    pg.evaluate("document.querySelector('#settingsBody .seg button:nth-child(2)').click()")
    pg.evaluate("localStorage.setItem('hanziGames.settings', JSON.stringify({v:1,script:'simp',lang:'en',phon:'zhuyin',rate:'fast'})); window.dispatchEvent(new StorageEvent('storage',{key:'hanziGames.settings'}))")
    pg.wait_for_timeout(300)
    R.check(pg.evaluate("document.getElementById('speedSelect').value") == 'fast', '其他遊戲改設定：速度下拉同步為 fast')
    R.check(not errs, '沒有網頁錯誤 %s' % errs)
    b.close()

print('FAILS', R.fails); sys.exit(1 if R.fails else 0)
