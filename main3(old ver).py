import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from discord.ui import Modal, TextInput
import csv
import json
import os
import random
from discord.ext import tasks
import asyncio
from datetime import datetime, timezone, timedelta
from discord import app_commands

# すべてのコマンドのデフォルト設定を上書きする設定
# これを bot.tree.command などの定義より前に書いてください
app_commands.Command._default_integration_types = {0, 1} # Guild & User
app_commands.Command._default_contexts = {0, 1, 2}        # Guild, BotDM, PrivateChannel

# --- 設定 ---
CSV_FILE = '/storage/emulated/0/Download/JWTG X Project file/files/dino-8.csv'
USER_DATA_FILE = '/storage/emulated/0/Download/JWTG X Project file/files/users.json'
TOKEN_FILE = '/storage/emulated/0/Download/JWTG X Project file/files/token.txt'
HYBRID_DATA_FILE = '/storage/emulated/0/Download/JWTG X Project file/files/hybrids.json'
EVENT_DATA_FILE = '/storage/emulated/0/Download/JWTG X Project file/files/events.json'

def load_hybrid_recipes():
    # HYBRID_DATA_FILE は "hybrids.json" などのファイルパス
    if not os.path.exists(HYBRID_DATA_FILE):
        return {}
    with open(HYBRID_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
# 通知用チャンネルID（必要に応じて書き換えてください）
NOTIFICATION_CHANNEL_ID = 1484345527578660974 

# --- 属性相性・AP倍率 ---
# 0:肉食, 1:草食, 2:翼竜, 3:両生類
ELEMENT_CHART = {
    "0": {"1": 1.5, "3": 0.5},
    "1": {"2": 1.5, "0": 0.5},
    "2": {"3": 1.5, "1": 0.5},
    "3": {"0": 1.5, "2": 0.5},
    "4": {"5": 1.5, "6": 0.5},
    "5": {"6": 1.5, "4": 0.5},
    "6": {"4": 1.5, "5": 0.5},
    "7": {"8": 1.5, "9": 0.5},
    "8": {"9": 1.5, "7": 0.5},
    "9": {"7": 1.5, "8": 0.5},
    "10": {"1": 1.5, "3": 0.5, "8": 1.5, "9": 0.5}
}
AP_MULTS = [0, 1.0, 2.4, 4.2, 6.4, 9, 12, 15.4, 20]

# --- 絵文字定義 ---
EMOJI = {
    "coin": "<:coin:1484312359781662812>",
    "cash": "<:cash:1484312404245479554>",
    "food": "<:niku:1484312451989110875>",
    "dna": "<:dna2:1484312531400003814>",
    "rp": "<:royalty_point:1484314148073639978>",
    "amber": "<:amber:1484314341862936778>",
    "b_dna": "<:BDNA:1485936376598888599>",
    "s_dna": "<:SDNA:1485936657210540042>",
    "s_dna36": "<:sdna36:1487320783306096650>",
    "s_dna58": "<:sdna58:1487321054098493470>",
    "s_dna48": "<:sdna48:1487321206771155015>",
    "s_dna86": "<:sdna86:1487324271742025868>",
    "s_dna33": "<:sdna33:1487324341451358329>",
    "s_dna53": "<:sdna53:1487324462465552515>",
    "s_dna37": "<:sdna37:1487324942755430400>",
    "s_dna114": "<:sdna114:1487325059294167131>",
    "shard": "<:shard:1485936735371137065>",
    "type_0": "<:nikushoku:1484307568292790443>", # 肉食
    "type_1": "<:soushoku:1484307627054993589>", # 草食
    "type_2": "<:yokuryuu:1484307810048016444>", # 翼竜
    "type_3": "<:ryouseirui:1484307875571433542>",
    
    "type_5": "<:doukutsu:1485704911487500470>",
    "type_6": "<:yuki:1485704937374486810>",
    "type_4": "<:sabanna:1485704953874878584>",
    
    "type_7": "<:kaimen:1485705149392617723>",
    "type_8": "<:douku2:1485705170221269144>",
    "type_9": "<:sango:1485705188420620309>",
    "type_10": "<:saikyo:1485705426782912635>" 
}

# --- データ管理 ---
dino_book = {}

def get_next_uid(u):
    inventory = u.get('inventory', [])
    if not inventory:
        return 1
    
    # 現在使用されているUIDをセット（集合）にまとめる
    # Setを使うことで検索が高速になります
    used_uids = set()
    for item in inventory:
        if isinstance(item, dict):
            used_uids.add(item.get('uid', 0))
        elif isinstance(item, int):
            used_uids.add(item)
            
    # 1から順番にチェックして、使用されていない最小の数値を探す
    new_uid = 1
    while new_uid in used_uids:
        new_uid += 1
        
    return new_uid

def load_csv():
    global dino_book
    if not os.path.exists(CSV_FILE): return
    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dino_book[row['id']] = {
                "name": row['name'], 
                "type": row['type'], 
                "rarity": row['rarity'].lower().strip(), 
                "hp": int(row['base_hp']), 
                "atk": int(row['base_atk']),
                "buy_dna": int(row['buy_dna']),
                "flock": int(row.get('flock', 0)),  # ← ここを追加！
                "hybrid": int(row['hybrid(0/1)']),
                "s_dna_type": row['s_dna_type'],
                "buy_amber": int(row.get('buy_amber', 0)), # 追加: buy_amberを取得。列がない場合は0
                "buy_s_dna": int(row['buy_s_dna']),
                "fusion_dna_amount":int( row['fusion_dna_amount']),
                "battle_in_the_water": row['battle_in_the_water'], 
            }

# パックデータの読み込み
def load_packs():
    with open('/storage/emulated/0/Download/JWTG X Project file/files/packs.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# 汎用的なパック配布関数
def give_pack(user_id, users, pack_type):
    u = get_user(user_id, users)
    packs = load_packs()  # JSONデータを読み込み
    
    if pack_type not in packs:
        return None
        
    pack_config = packs[pack_type]
    
    # --- 1. 恐竜の当選判定 ---
    # JSONに dino_drop_rate がない場合は 1.0 (100%) とみなす
    drop_rate = pack_config.get("dino_drop_rate", 1.0) 
    is_dino_hit = random.random() < drop_rate
    
    selected_id = None
    new_uid = None
    dino_name = "なし"

    if is_dino_hit:
        # 重み付け抽選用のツリー作成 (実行時に構築)
        tree = {}
        for d_id, d in dino_book.items():
            r = d['rarity'].lower().strip()
            t = str(d['type'])
            w = str(d['battle_in_the_water'])
            h = str(d['hybrid'])
        
            if r not in tree: tree[r] = {}
            if t not in tree[r]: tree[r][t] = {}
            if w not in tree[r][t]: tree[r][t][w] = {}
            if h not in tree[r][t][w]: tree[r][t][w][h] = []
            
            tree[r][t][w][h].append(d_id)

        # 抽選ロジックの優先順位
        if "fixed_ids" in pack_config:
            selected_id = random.choice(pack_config["fixed_ids"])
        elif "dino_ids" in pack_config:
            selected_id = random.choice(pack_config["dino_ids"])
        else:
            # 重み付け抽選
            r_w = pack_config.get("rarity_weights", {})
            e_w = pack_config.get("element_weights", {})
            w_w = pack_config.get("water_weights", {})
            h_w = pack_config.get("hybrid_weights", {})

            combos = []
            weights = []

            for r in r_w.keys():
                if r not in tree: continue
                for t in tree[r]:
                    for w in tree[r][t]:
                        for h in tree[r][t][w]:
                            if tree[r][t][w][h]:
                                combos.append((r, t, w, h))
                                # スコア計算: 各カテゴリの重みを掛け合わせる
                                score = (r_w.get(r, 1) * e_w.get(t, 1) * w_w.get(w, 1) * h_w.get(h, 1))
                                weights.append(score)

            if combos and sum(weights) > 0:
                chosen = random.choices(combos, weights=weights, k=1)[0]
                selected_id = random.choice(tree[chosen[0]][chosen[1]][chosen[2]][chosen[3]])

        # 当選した場合のインベントリ追加処理
        if selected_id:
            new_uid = get_next_uid(u)
            new_dino = {
                "uid": new_uid,
                "id": selected_id,
                "lv": 1,
                "exp": 0,
                "get_date": datetime.now().strftime("%Y-%m-%d")
            }
            u['inventory'].append(new_dino)
            dino_name = dino_book[selected_id]['name']

    # --- 2. 通貨の抽選 (JSONの範囲から決定) ---
    # 各通貨を0で初期化して KeyError や UnboundLocalError を防ぐ
    dna_gain = 0
    cash_gain = 0
    coin_gain = 0
    food_gain = 0

    if "dna_range" in pack_config:
        dna_gain = random.randint(*pack_config["dna_range"])
        u['dna'] += dna_gain
    
    if "cash_range" in pack_config:
        cash_gain = random.randint(*pack_config["cash_range"])
        u['cash'] += cash_gain
        
    if "coin_range" in pack_config:
        coin_gain = random.randint(*pack_config["coin_range"])
        u['coin'] += coin_gain

    if "food_range" in pack_config:
        food_gain = random.randint(*pack_config["food_range"])
        u['food'] += food_gain

    rp_amt = pack_config.get("rp_amount", 0)
    if rp_amt > 0:
        u['rp'] = u.get('rp', 0) + rp_amt

    bdna_amt = pack_config.get("b_dna_amount", 0)
    if bdna_amt > 0:
        u['b_dna'] = u.get('b_dna', 0) + bdna_amt
    
    # --- 3. 結果の返却 ---
    return {
        "pack_display_name": pack_config['name'],
        "selected_id": selected_id,
        "dino_name": dino_name,
        "dna": dna_gain,
        "coin": coin_gain,
        "cash": cash_gain,
        "food": food_gain,
        "rp": rp_amt,
        "b_dna": bdna_amt, 
        "uid": new_uid
    }

async def show_pack_open_result(interaction, result, pack_type, u):
    """
    give_packの結果を受け取り、開封Embedを表示する
    """
    # 恐竜データの取得 (selected_id が None の場合はハズレ)
    selected_id = result.get('selected_id')
    
    # レアリティに応じた色設定 (任意)
    rarity_colors = {
        "common": 0xadadad, "rare": 0x3498db, "superrare": 0x9b59b6, 
        "legend": 0xf1c40f, "tournament": 0xe74c3c, "vip": 0x1abc9c
    }
    
    embed = discord.Embed(title=f"📦 {result['pack_display_name']} 開封結果", color=0x3498db)

    if selected_id:
        dino = dino_book.get(str(selected_id))
        if dino:
            # ステータス計算 (Lv.1固定)
            hp = get_current_stat(dino['hp'], 1)
            atk = get_current_stat(dino['atk'], 1)
            type_emoji = EMOJI.get(f"type_{dino['type']}", "❓")
            
            embed.color = rarity_colors.get(dino['rarity'].lower(), 0x3498db)
            embed.add_field(
                name=f"#{result['uid']} {dino['name']} (Lv.1)", 
                value=f"{type_emoji} レアリティ: **{dino['rarity'].upper()}**\n❤️ HP: {hp} | ⚔️ ATK: {atk}", 
                inline=False
            )
    else:
        embed.add_field(name="🦕 恐竜", value="なし (ハズレ)", inline=False)
    
    # 獲得ボーナス通貨の表示
    reward_text = (
        f"{EMOJI['coin']} {result['coin']:,}\n"
        f"{EMOJI['dna']} {result['dna']:,}\n"
        f"{EMOJI['cash']} {result['cash']:,}\n"
        f"{EMOJI['food']} {result['food']:,}\n"
        f"{EMOJI['rp']} {result.get('rp', 0):,}"
    )
    embed.add_field(name="🎁 獲得ボーナス", value=reward_text, inline=False)
    
    if pack_type == "gold":
        embed.set_footer(text=f"残り所持RP: {u.get('rp', 0):,}")
    
    # バトルの後続メッセージとして送信
    await interaction.followup.send(embed=embed)
    
def load_hybrid_recipes():
    # HYBRID_DATA_FILE が "hybrids.json" だと仮定
    if not os.path.exists(HYBRID_DATA_FILE):
        return {}
    with open(HYBRID_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
        
def load_events():
    # EVENT_DATA_FILE が上で定義されていないとここでエラーになります
    if not os.path.exists(EVENT_DATA_FILE):
        return {"missions": []}
    with open(EVENT_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
        
def create_dino_embed(dino_data, found_id, lv=1, uid=None):
    # 属性・レアリティ設定
    rarity = dino_data['rarity'].lower()
    t_type = dino_data.get('type', "0")
    emoji = EMOJI.get(f"type_{t_type}", "❓")
    color_map = {"common": 0x95a5a6, "rare": 0x2ecc71, "superrare": 0x9b59b6, "legend": 0xf1c40f, "tournament": 0xe74c3c}
    embed_color = color_map.get(rarity, 0x3498db)

    # 価格計算
    buy_dna = int(dino_data.get('buy_dna', 0))
    sell_dna = buy_dna // 2
    
    amber_cost = int(dino_data.get('buy_amber', 0))
    amber_display = f"`{amber_cost:,}`" if amber_cost > 0 else "購入不可" # 0なら購入不可と表示
     
    title = f"🦖 図鑑データ: {dino_data['name']}"
    if uid:
        title = f"🦖 所持恐竜: {dino_data['name']} [#{uid}]"

    embed = discord.Embed(title=title, color=embed_color)
    
    # 基本情報
    info_text = (
        f"**ID:** `{found_id}`\n"
        f"**属性:** {emoji} (Type {t_type})\n"
        f"**レアリティ:** {rarity.upper()}\n"
        f"**販売価格:** {EMOJI['dna']} `{buy_dna:,}` / {EMOJI['amber']} {amber_display}\n"
        f"**売却価格:** {EMOJI['dna']} `{sell_dna:,}`" # 売値を表示
    )
    embed.add_field(name="基本情報", value=info_text, inline=False)

    # ステータス表示（uidがある場合は現在のLv、ない場合は成長表）
    if uid:
        # 個別詳細（現在のステータス）
        curr_hp = get_current_stat(dino_data['hp'], lv)
        curr_atk = get_current_stat(dino_data['atk'], lv)
        embed.add_field(name=f"📈 現在のステータス (Lv.{lv})", value=f"❤️ HP: `{curr_hp:,}`\n⚔️ ATK: `{curr_atk:,}`", inline=False)
    else:
        # 図鑑用（成長表）
        levels = [1, 10, 20, 30, 40]
        stat_text = "```md\n| Lv | HP    | ATK  |\n|----|-------|------|\n"
        for l in levels:
            h = get_current_stat(dino_data['hp'], l)
            a = get_current_stat(dino_data['atk'], l)
            stat_text += f"| {l:2} | {h:5,} | {a:4,} |\n"
        stat_text += "```"
        embed.add_field(name="📈 成長ステータス", value=stat_text, inline=False)

    # 相性ヒント
    strong_to = [k for k, v in ELEMENT_CHART.get(t_type, {}).items() if v > 1.0]
    weak_to = [k for k, v in ELEMENT_CHART.items() if v.get(t_type, 1.0) > 1.0]
    hint = ""
    if strong_to: hint += f"✅ 有利: {', '.join([EMOJI.get(f'type_{t}', t) for t in strong_to])}\n"
    if weak_to: hint += f"⚠️ 不利: {', '.join([EMOJI.get(f'type_{t}', t) for t in weak_to])}"
    if hint: embed.add_field(name="⚔️ 相性メモ", value=hint, inline=False)

    return embed

def check_constraints(dino_data, constraints):
    """
    dino_data: ユーザーの所持している個体データ (dict)
    constraints: events.json の 'constraints' (dict)
    """
    # 制限自体がない場合は即パス
    if not constraints:
        return True, ""

    # 図鑑データの取得
    d_info = dino_book.get(str(dino_data['id']))
    if not d_info:
        return False, "図鑑にデータがありません"

    # 1. レベル制限
    if 'min_lv' in constraints and dino_data['lv'] < constraints['min_lv']:
        return False, f"レベル不足 (最低: Lv.{constraints['min_lv']})"
    if 'max_lv' in constraints and dino_data['lv'] > constraints['max_lv']:
        return False, f"レベル制限超過 (最大: Lv.{constraints['max_lv']})"

    # 2. 属性制限
    if 'allowed_types' in constraints:
        if str(d_info['type']) not in [str(t) for t in constraints['allowed_types']]:
            return False, "属性が一致しません"

    # 3. レアリティ制限
    if 'allowed_rarities' in constraints:
        # 図鑑のレアリティを大文字にして比較
        if d_info['rarity'].upper() not in [r.upper() for r in constraints['allowed_rarities']]:
            return False, f"レアリティ {d_info['rarity']} は参加不可です"

    # 4. ハイブリッド制限
    if 'hybrid_type' in constraints:
        # CSVの列名 'hybrid(0/1)' を参照
        current_hybrid_val = int(d_info.get('hybrid(0/1)', 0))
        if current_hybrid_val != int(constraints['hybrid_type']):
            h_names = {0: "通常種", 1: "ハイブリッド"}
            h_name = h_names.get(int(constraints['hybrid_type']), "指定種別")
            return False, f"種別制限: {h_name}限定です"

    # 5. 環境制限 (water_type) ★ここが重要★
    if 'water_type' in constraints:
        # 恐竜側の値 (0:陸上, 1:全地形, 2:水中)
        dino_water_val = int(d_info.get('battle_in_the_water', 0))
        # 制限側の値 (0:陸上限定イベント, 2:水中限定イベント)
        required_water_type = int(constraints['water_type'])

        # 「恐竜が全地形対応(1)」ならどんな制限もパス
        # それ以外で、制限と一致しない場合はエラー
        if dino_water_val != 1 and dino_water_val != required_water_type:
            w_names = {0: "陸上", 1: "全地形", 2: "水中"}
            req_name = w_names.get(required_water_type, "指定環境")
            return False, f"環境制限: {req_name}の恐竜のみ参加可能です"

    # すべてのチェックを通過
    return True, ""
    
class EventListView(discord.ui.View):
    def __init__(self, interaction, missions):
        super().__init__(timeout=180)
        self.interaction = interaction
        
        # --- フィルタリングロジック ---
        now = datetime.now()
        current_weekday = now.weekday() # 0(月)〜6(日)を取得
        
        active_missions = []
        for m in missions:
            # 1. 期間の判定 (start_date <= 今 <= end_date)
            try:
                start = datetime.strptime(m.get('start_date', '2000-01-01'), "%Y-%m-%d")
                end = datetime.strptime(m.get('end_date', '2099-12-31'), "%Y-%m-%d")
                if not (start <= now <= end):
                    continue # 期間外ならスキップ
            except ValueError:
                pass # 日付形式エラーは無視して次に進む

            # 2. 曜日の判定 (available_days)
            # JSON内で "available_days": [0, 2, 4] のように管理されている想定
            avail_days = m.get('available_days', [])
            if avail_days and current_weekday not in avail_days:
                continue # 今日の曜日が含まれていなければスキップ
                
            active_missions.append(m)
                
        self.missions = active_missions
        self.page = 0
        self.per_page = 10 # 1ページ10件に変更

    def make_embed(self):
        if not self.missions:
            embed = discord.Embed(
                title="📅 開催中のイベント一覧", 
                description="現在挑戦可能なイベントはありません。", 
                color=0x00ffff
            )
            return embed

        start = self.page * self.per_page
        end = start + self.per_page
        current_list = self.missions[start:end]
        
        embed = discord.Embed(
            title="📅 開催中のイベント一覧",
            description=f"IDを指定して `/event id` で挑戦できます。\n(本日開催中: {len(self.missions)} 件)",
            color=0x00ffff
        )
        
        for m in current_list:
            # 報酬の表示
            rew = m.get('reward', {})
            reward_parts = []
            
            for k, v in rew.items():
                if k == "pack": continue # パックは非表示
                
                # EMOJI辞書から s_dnaXX や基本通貨の絵文字を取得
                emoji = EMOJI.get(k, "")
                if emoji:
                    reward_parts.append(f"{emoji}{v}")
                else:
                    reward_parts.append(f"**{k}**: {v}")

            reward_brief = " ".join(reward_parts)
            
            embed.add_field(
                name=f"ID: {m['id']} | {m['name']}",
                value=f"🎁 {reward_brief or '報酬なし'}",
                inline=False
            )
            
        total_pages = (len(self.missions) - 1) // self.per_page + 1
        embed.set_footer(text=f"Page {self.page + 1} / {total_pages}")
        return embed

    @discord.ui.button(label="前へ", style=discord.ButtonStyle.grey)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
        else:
            await interaction.response.send_message("これ以上前には戻れません。", ephemeral=True)

    @discord.ui.button(label="次へ", style=discord.ButtonStyle.grey)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if (self.page + 1) * self.per_page < len(self.missions):
            self.page += 1
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
        else:
            await interaction.response.send_message("次のページはありません。", ephemeral=True)


# --- チーム編成用モーダル ---
class TeamSelectModal(discord.ui.Modal, title="チーム編成 (UID入力)"):
    # 入力フィールドの説明を UID に変更
    uids_input = discord.ui.TextInput(
        label="恐竜のUIDをカンマ区切りで入力",
        placeholder="例: 101, 105, 120 (/invで確認したID)",
        min_length=1,
        max_length=50
    )

    def __init__(self, preview_view):
        super().__init__()
        self.preview_view = preview_view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # 入力されたUIDをリスト化 (空白削除)
            raw_input = self.uids_input.value.replace(" ", "")
            input_uids = [i for i in raw_input.split(",") if i.strip()]
            
            # 最大3体まで
            input_uids = input_uids[:3]
            
            # --- ここで変数名を「new_uids」に統一します ---
            new_uids = []
            inventory = self.preview_view.u.get('inventory', [])
            
            # 入力された各UIDが、ユーザーのインベントリに存在するかチェック
            for target_uid in input_uids:
                # インベントリ内の恐竜のUIDと、入力されたUID(文字列)を比較
                dino = next((d for d in inventory if str(d['uid']) == target_uid), None)
                if dino:
                    new_uids.append(dino['uid'])
            
            if not new_uids:
                await interaction.response.send_message("❌ 入力されたUIDが見つかりませんでした。正しいUIDを入力してください。", ephemeral=True)
                return
            # 親View（プレビュー画面）の選択データを更新
            self.preview_view.my_uids = new_uids 
            
            # 「挑戦する」ボタンを有効化 (children[1]が挑戦ボタン)
            self.preview_view.challenge_button.disabled = False
            
            # プレビュー画面（EmbedとView）を最新状態に更新
            await interaction.response.edit_message(
                embed=self.preview_view.make_preview_embed(), 
                view=self.preview_view
            )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ エラーが発生しました: {e}", ephemeral=True)

def get_current_stat(base_val, level):
    multiplier = 0.1 + (0.9 * (level - 1) / 39)
    return int(base_val * multiplier)

def load_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

class InventoryView(discord.ui.View):
    def __init__(self, inv, user_id, page=0):
        super().__init__(timeout=60)
        self.inv = inv
        self.user_id = user_id
        self.page = page
        self.per_page = 20
        self.max_page = (len(inv) - 1) // self.per_page

    def make_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        current_list = self.inv[start:end]
        
        lines = []
        for i in current_list:
            d_base = dino_book.get(str(i['id']))
            type_emoji = EMOJI.get(f"type_{d_base.get('type')}", "❓") if d_base else "⚠️"
            name = d_base['name'] if d_base else f"不明(ID:{i['id']})"
            lines.append(f"**#{i['uid']}** | {type_emoji} {name} (Lv.{i['lv']})")

        embed = discord.Embed(
            title="🦖 コレクション", 
            description="\n".join(lines), 
            color=0x1abc9c
        )
        embed.set_footer(text=f"Page {self.page + 1} / {self.max_page + 1} (Total: {len(self.inv)})")
        return embed

    @discord.ui.button(label="◀ 前へ", style=discord.ButtonStyle.gray)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("自分のみ操作可能です。", ephemeral=True)
        
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="次へ ▶", style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("自分のみ操作可能です。", ephemeral=True)

        if self.page < self.max_page:
            self.page += 1
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
        else:
            await interaction.response.defer()
            
    def apply_damage(self, target, damage, raw_atk_ap, effective_ap):
        """
        damage: 計算済みの最終ダメージ
        raw_atk_ap: 攻撃側が【選択した】AP (7以上なら無条件貫通)
        effective_ap: 防御を差し引いた【実効】AP
        """
        if damage <= 0: return 0
        actual = damage
        
        # --- 群れ（Flock）システムの判定 ---
        if target.get('is_flock'):
            # 【判定】攻撃ボタンで7または8を選んでいれば貫通！
            if raw_atk_ap >= 7:
                target['hp'] -= damage
                if target['hp'] <= 0:
                    target['flock_count'] = 0
                
                self.log += f"\n💥 {raw_atk_ap}APの強襲！ 群れの特性を貫通した！"
            
            else:
                # 6AP以下での攻撃は通常のストッパー発動
                one_third = target['max_hp'] // 3
                threshold = one_third * (target['flock_count'] - 1)
                
                if (target['hp'] - damage) < threshold:
                    actual = target['hp'] - threshold
                    target['hp'] = threshold
                    target['flock_count'] -= 1
                else:
                    target['hp'] -= damage
        else:
            # 通常の恐竜
            target['hp'] -= damage
            
        if target['hp'] < 0: target['hp'] = 0
        return actual


def get_user(user_id, all_users):
    uid = str(user_id)
    if uid not in all_users:
        all_users[uid] = {
            "coin": 15000, "cash": 1000, "food": 4500, "dna": 5000, "rp": 10000, "amber": 0,
            "b_dna": 0,    # 追加: B-DNA
            "medal": {},
            "s_dna": {},   # 追加: S-DNA (恐竜ID別の辞書形式)
            "shard": {},   # 追加: Shard (恐竜ID別の辞書形式)
            "inventory": [], "last_free_pack": "2000-01-01 00:00:00","win_count": 0,  
            "last_factory_claim": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    # 既存ユーザーへのデータ補完
    if "last_factory_claim" not in all_users[uid]:
        all_users[uid]["last_factory_claim"] = "2000-01-01 00:00:00"
    if "win_count" not in all_users[uid]:
        all_users[uid]["win_count"] = 0
    return all_users[uid]
    if "b_dna" not in all_users[uid]: all_users[uid]["b_dna"] = 0
    if "s_dna" not in all_users[uid]: all_users[uid]["s_dna"] = {}
    if "shard" not in all_users[uid]: all_users[uid]["shard"] = {}
    if "medals" not in all_users[uid]: 
        # 既存の 'medal'(数値) がある場合は移行し、なければ空の辞書を作成
        old_medal_count = all_users[uid].pop('medal', 0)
        all_users[uid]["medals"] = {"total": old_medal_count} 
    
    # ... (既存の補完処理)
    return all_users[uid]

def get_next_uid(u):
    inventory = u.get('inventory', [])
    if not inventory:
        return 1
    
    uids = []
    for item in inventory:
        # itemが辞書形式の場合のみ .get() を使う
        if isinstance(item, dict):
            uids.append(int(item.get('uid', 0)))
        # もし文字列などが混じっていたら無視するか、適切に処理する
        elif isinstance(item, (int, str)) and str(item).isdigit():
            uids.append(int(item))
            
    return (max(uids) + 1) if uids else 1
 

def get_rarity_weight(rarity):
    weights = {"common": 1, "rare": 2, "superrare": 4, "legend": 6, "tournament": 9, "star": 9, "vip": 10, "superstar": 12}
    return weights.get(rarity.lower(), 1)
    
def load_hybrid_recipes():
    file_path = HYBRID_DATA_FILE
    if not os.path.exists(file_path):
        # ファイルがない場合のデフォルト（空）
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# --- ボットクラス ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        
class BattleView(View):
    def __init__(self, interaction, u, my_uids, en_infos, en_lvs):
        super().__init__(timeout=300)
        self.interaction = interaction
        self.u = u
        
        # プレイヤーチーム (最大3体) のデータ構築
        self.p_team = []
        for uid in my_uids:
            d_item = next((i for i in u['inventory'] if i['uid'] == uid), None)
            if d_item:
                d_info = dino_book[str(d_item['id'])]
                max_hp = get_current_stat(d_info['hp'], d_item['lv'])
                self.p_team.append({
                    "uid": uid, "name": d_info['name'], "type": d_info['type'],
                    "hp": max_hp, "max_hp": max_hp, "atk": get_current_stat(d_info['atk'], d_item['lv']),
                    "lv": d_item['lv'], "is_dead": False
                })
        
        # 敵チーム (最大3体)
        self.e_team = []
        for i in range(len(en_infos)):
            max_hp = get_current_stat(en_infos[i]['hp'], en_lvs[i])
            self.e_team.append({
                "name": en_infos[i]['name'], "type": en_infos[i]['type'],
                "hp": max_hp, "max_hp": max_hp, "atk": get_current_stat(en_infos[i]['atk'], en_lvs[i]),
                "lv": en_lvs[i], "is_dead": False
            })

        self.p_idx = 0 # 現在出撃中のインデックス
        self.e_idx = 0
        self.p_ap, self.e_ap, self.turn = 1, 1, 1
        self.step = "ATK"
        self.p_selected_atk = 0
        self.log = "バトル開始！先鋒を出撃させました。"
        self.create_buttons()

    def make_embed(self):
        p = self.p_team[self.p_idx]
        e = self.e_team[self.e_idx]
        p_mult = ELEMENT_CHART.get(p['type'], {}).get(e['type'], 1.0)
        e_mult = ELEMENT_CHART.get(e['type'], {}).get(p['type'], 1.0)
        
        
        embed = discord.Embed(title=f"⚔️ ターン {self.turn} (チーム戦)", color=0x3498db)
        
        # チーム生存状況
        p_lives = "".join(["🔵" if not d['is_dead'] else "❌" for d in self.p_team])
        e_lives = "".join(["🔴" if not d['is_dead'] else "❌" for d in self.e_team])

        def hp_bar(curr, maxi):
            per = max(0, min(10, int(curr/maxi*10)))
            return "🟩" * per + "⬜" * (10-per)

        embed.add_field(name=f"あなたのチーム {p_lives}", 
                        value=f"**{p['name']}** (Lv.{p['lv']})\n{hp_bar(p['hp'], p['max_hp'])}\nHP: {p['hp']}/{p['max_hp']} | ATK: {p['atk']}(x{p_mult})\nAP: **{self.p_ap}**", inline=True)
        
        embed.add_field(name=f"敵のチーム {e_lives}", 
                        value=f"**{e['name']}** (Lv.{e['lv']})\n{hp_bar(e['hp'], e['max_hp'])}\nHP: {e['hp']}/{e['max_hp']} | ATK: {e['atk']}(x{e_mult})\nAP: **{self.e_ap}**", inline=True)
        
        embed.description = f"```ml\n{self.log}\n```"
        return embed

    def create_buttons(self):
        self.clear_items()
        # AP選択ボタン (攻撃・防御用)
        limit = self.p_ap if self.step == "ATK" else (self.p_ap - self.p_selected_atk)
        for i in range(limit + 1):
            btn = Button(label=str(i), style=discord.ButtonStyle.primary if i > 0 else discord.ButtonStyle.grey, custom_id=f"ap_{i}")
            btn.callback = self.ap_callback
            self.add_item(btn)
        
        # 交代ボタン (APが1以上あり、控えがいる場合のみ)
        if self.step == "ATK" and self.p_ap >= 1:
            for i, d in enumerate(self.p_team):
                if i != self.p_idx and not d['is_dead']:
                    swap_btn = Button(label=f"交代:{d['name']}", style=discord.ButtonStyle.success, custom_id=f"swap_{i}")
                    swap_btn.callback = self.swap_callback
                    self.add_item(swap_btn)

    async def ap_callback(self, interaction: discord.Interaction):
        val = int(interaction.data['custom_id'].split("_")[1])
        if self.step == "ATK":
            self.p_selected_atk = val
            self.step = "DEF"
            self.create_buttons()
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
        else:
            await self.resolve_turn(interaction, self.p_selected_atk, val)

    async def swap_callback(self, interaction: discord.Interaction):
        # 交代処理 (APを1消費)
        new_idx = int(interaction.data['custom_id'].split("_")[1])
        old_name = self.p_team[self.p_idx]['name']
        self.p_idx = new_idx
        self.p_ap -= 1
        self.log = f"🔄 {old_name} を下げて {self.p_team[self.p_idx]['name']} を出した！ (AP-1)"
        # 交代したらそのターンは攻撃・防御選択へ
        self.step = "ATK"
        self.create_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    async def resolve_turn(self, interaction, p_atk, p_def):
        p = self.p_team[self.p_idx]
        e = self.e_team[self.e_idx]
        
        # CPU思考 (交代はせず攻撃/防御のみ)
        e_atk = random.randint(0, self.e_ap)
        e_def = self.e_ap - e_atk
        
        p_mult = ELEMENT_CHART.get(p['type'], {}).get(e['type'], 1.0)
        e_mult = ELEMENT_CHART.get(e['type'], {}).get(p['type'], 1.0)

        # ダメージ計算
        p_rem_ap = max(0, p_atk - e_def)
        # 残ったAP個数に対応する倍率を AP_MULTS から取得
        p_rem_mult = AP_MULTS[p_rem_ap]
        # ダメージ計算: 攻撃力 * 残りAPの倍率 * 属性相性
        p_final = int(self.p_team[self.p_idx]['atk'] * p_rem_mult * p_mult)
        self.e_team[self.e_idx]['hp'] -= p_final

        e_rem_ap = max(0, e_atk - p_def)
        e_rem_mult = AP_MULTS[e_rem_ap]
        e_final = int(self.e_team[self.e_idx]['atk'] * e_rem_mult * e_mult)
        self.p_team[self.p_idx]['hp'] -= e_final
        
        self.log = f"自:攻{p_atk}防{p_def} / 敵:攻{e_atk}防{e_def}\n💥 与ダメ:{p_final} / 被ダメ:{e_final}"
        
        # 死亡判定
        if p['hp'] <= 0:
            p['hp'] = 0; p['is_dead'] = True
            next_p = next((i for i, d in enumerate(self.p_team) if not d['is_dead']), None)
            if next_p is not None: 
                self.p_idx = next_p
                self.log += f"\n💀 {p['name']} は倒れた！ {self.p_team[self.p_idx]['name']} 出撃！"
        
        if e['hp'] <= 0:
            e['hp'] = 0; e['is_dead'] = True
            next_e = next((i for i, d in enumerate(self.e_team) if not d['is_dead']), None)
            if next_e is not None:
                self.e_idx = next_e
                self.log += f"\n🦖 野生の {e['name']} を倒した！ 次の敵が出現！"

        # 決着判定
        p_all_dead = all(d['is_dead'] for d in self.p_team)
        e_all_dead = all(d['is_dead'] for d in self.e_team)

        if p_all_dead or e_all_dead:
            win = e_all_dead
            embed = self.make_embed()
            embed.add_field(name="結果", value="✨ あなたの勝利！" if win else "💀 敗北...", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        else:
            recovery = min((self.turn) + 1, 4)
            self.p_ap = min(8, (self.p_ap - p_atk - p_def) + recovery)
            self.e_ap = min(8, (self.e_ap - e_atk - e_def) + recovery)    
            self.turn += 1
            self.step = "ATK"
            self.create_buttons()
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
            
class EventPreviewView(View):
    def __init__(self, interaction, u, my_uids, mission_data):
        super().__init__(timeout=300)
        self.interaction = interaction
        self.u = u
        self.my_uids = my_uids 
        self.mission_data = mission_data

        # --- ここは「ボタン」の制限だけ！ ---
        m = self.mission_data 
        available_days = m.get('available_days')
        
        if available_days is not None:
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone(timedelta(hours=9)))
            if now.weekday() not in available_days:
                # embed.color などはここでは絶対に使わない（まだ存在しないから）
                self.challenge_button.disabled = True
                self.challenge_button.label = "本日は開催外です"

    def make_preview_embed(self):
        m = self.mission_data
        embed = discord.Embed(
            title=m.get('name', 'イベント'),
            description="イベントの詳細と現在の編成状況です。",
            color=0x00ff00
        )
        
        c_list = []  # ここでリストを初期化

        # 1. 開催日の表示
        days_list = m.get('available_days')
        if days_list is not None:
            week_map = {0: "月", 1: "火", 2: "水", 3: "木", 4: "金", 5: "土", 6: "日"}
            d_names = [week_map.get(int(d), "？") for d in days_list]
            d_str = "・".join(d_names)
            c_list.append(f"・開催日: 毎週 {d_str}曜日")
            
        # 👾 敵の情報表示
        enemy_list = ""
        for i, en in enumerate(self.mission_data['enemies'], 1):
            d_info = dino_book.get(str(en['id']), {"name": "不明", "type": 0})
            type_emoji = EMOJI.get(f"type_{d_info['type']}", "❓")
            enemy_list += f"{i}. {type_emoji} **{d_info['name']}** (Lv.{en['lv']})\n"
        embed.add_field(name="👾 出現する敵", value=enemy_list, inline=False)

        # 2. 報酬の表示
        r = m.get('reward', {})
        r_parts = []
        
        # 1. 通貨・ポイント類の処理
        # EMOJI辞書にあるキーと一致するものを回す
        for key in ['coin', 'cash', 'dna', 'food', 'amber', 'rp', 'b_dna']:
            if key in r:
                emoji = EMOJI.get(key, "")
                r_parts.append(f"{emoji} {r[key]:,}")

        # 2. パックの処理 (packs.jsonを参照)
        if 'pack' in r:
            pack_id = r['pack']
            # packs.json をロード (関数外でロード済みならそれを使ってください)
            try:
                all_packs = load_packs() 
                pack_info = all_packs.get(pack_id)
                if pack_info:
                    pack_name = pack_info.get('name', pack_id)
                    r_parts.append(f"🎁 **{pack_name}**")
                else:
                    r_parts.append(f"🎁 パック({pack_id})")
            except:
                r_parts.append(f"🎁 パック({pack_id})")

        # 3. S-DNAの処理 (特殊なキー形式に対応)
        sdna_data = m.get('S-DNA', {})
        if sdna_data:
            for s_id, s_amt in sdna_data.items():
                # 恐竜名を取得
                dino_info = dino_book.get(str(s_id))
                dino_name = dino_info.get('name', f"ID:{s_id}") if dino_info else f"ID:{s_id}"
                
                # 対応する絵文字キー (s_dna36 など) があるか確認
                emoji_key = f"s_dna{s_id}"
                s_emoji = EMOJI.get(emoji_key, EMOJI.get('s_dna', '🧪'))
                
                r_parts.append(f"{s_emoji} {dino_name} S-DNA: {s_amt}")

        # フィールドへ追加
        reward_display = "\n".join(r_parts) if r_parts else "なし"
        embed.add_field(name="🎁 報酬", value=reward_display, inline=False)

        # 3. 出撃制限の表示
        con = m.get('constraints', {})
        if con:
            # --- レベル制限 ---
            if 'min_lv' in con or 'max_lv' in con:
                min_l = con.get('min_lv', 1)
                max_l = con.get('max_lv', 40)
                c_list.append(f"・レベル: Lv.{min_l} ～ {max_l}")
            
            # --- 属性制限 ---
            if 'allowed_types' in con:
                tn = {
                    "0": "<:nikushoku:1484307568292790443>", "1": "<:soushoku:1484307627054993589>",
                    "2": "<:yokuryuu:1484307810048016444>", "3": "<:ryouseirui:1484307875571433542>",
                    "4": "<:sabanna:1485704953874878584>", "5": "<:doukutsu:1485704911487500470>",
                    "6": "<:yuki:1485704937374486810>", "7": "<:kaimen:1485705149392617723>",
                    "8": "<:douku2:1485705170221269144>", "9": "<:sango:1485705188420620309>",
                    "10": "<:saikyo:1485705426782912635>"
                }
                types = [tn.get(str(t), str(t)) for t in con['allowed_types']]
                c_list.append(f"・属性: {' '.join(types)}")
            
            # --- レアリティ制限 ---
            if 'allowed_rarities' in con:
                rarities = [r.upper() for r in con['allowed_rarities']]
                c_list.append(f"・レアリティ: {', '.join(rarities)}")
            
            # --- ハイブリッド制限 ---
            if 'hybrid_type' in con:
                if con['hybrid_type'] == 0:
                    c_list.append("・種類: 通常種のみ")
                elif con['hybrid_type'] == 1:
                    c_list.append("・種類: ハイブリッドのみ")

            # --- 環境制限 ---
            if 'water_type' in con:
                water_labels = {0: "陸上限定", 1: "全地形対応", 2: "水中限定"}
                w_str = water_labels.get(int(con['water_type']), f"特殊環境({con['water_type']})")
                c_list.append(f"・環境: {w_str}")

            con_str = "\n".join(c_list)
        else:
            con_str = "制限なし"
    
        embed.add_field(name="⚠️ 出撃制限", value=con_str, inline=False)

        # 4. 現在の編成表示
        party_str = ""
        if not self.my_uids:
            party_str = "*未選択*"
        else:
            for uid in self.my_uids:
                d = next((x for x in self.u['inventory'] if x['uid'] == uid), None)
                if d:
                    info = dino_book.get(str(d['id']), {"name": "不明"})
                    is_ok, _ = check_constraints(d, con)
                    status = "✅" if is_ok else "❌"
                    party_str += f"{status} **{info['name']}** (Lv.{d['lv']})\n"
        
        embed.add_field(name="🦕 あなたの編成", value=party_str, inline=False)
        return embed


    @discord.ui.button(label="チーム編成", style=discord.ButtonStyle.primary, row=0)
    async def select_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        # モーダルを呼び出す
        await interaction.response.send_modal(TeamSelectModal(self))

    @discord.ui.button(label="挑戦する", style=discord.ButtonStyle.green)
    async def challenge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 最終チェック
        constraints = self.mission_data.get('constraints')
        for uid in self.my_uids:
            dino = next((d for d in self.u['inventory'] if d['uid'] == uid), None)
            if dino:
                is_ok, reason = check_constraints(dino, constraints)
                if not is_ok:
                    await interaction.response.send_message(f"❌ 条件を満たしていない恐竜が含まれています: {reason}", ephemeral=True)
                    return

        # バトル開始
        view = EventBattleView(interaction, self.u, self.my_uids, self.mission_data)
        await interaction.response.edit_message(embed=view.make_embed(), view=view)

    @discord.ui.button(label="戻る", style=discord.ButtonStyle.grey, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="キャンセルしました。", embed=None, view=None)
            
class EventBattleView(BattleView):
    def __init__(self, interaction, u, my_uids, mission_data):
        # 敵チームの構成 (events.jsonから取得)
        en_infos = []
        en_lvs = []
        for en in mission_data['enemies']:
            d_info = dino_book.get(str(en['id']))
            if d_info:
                en_infos.append(d_info)
                en_lvs.append(en['lv'])
        
        # 親クラス(BattleView)の初期化
        super().__init__(interaction, u, my_uids, en_infos, en_lvs)
        self.mission_data = mission_data

    async def resolve_turn(self, interaction, p_atk, p_def):
        p = self.p_team[self.p_idx]
        e = self.e_team[self.e_idx]
        
        # CPU思考 (交代はせず攻撃/防御のみ)
        e_atk = random.randint(0, self.e_ap)
        e_def = self.e_ap - e_atk
        
        p_mult = ELEMENT_CHART.get(p['type'], {}).get(e['type'], 1.0)
        p_rem_ap = max(0, p_atk - e_def) # プレイヤーの実効AP
        p_raw = int(p['atk'] * AP_MULTS[min(p_rem_ap, 8)] * p_mult)
        
        # 呼び出し (p_atkが7以上なら貫通)
        p_final = self.apply_damage(e, p_raw, p_atk, p_rem_ap)

        # --- 敵からプレイヤーへの攻撃 ---
        e_mult = ELEMENT_CHART.get(e['type'], {}).get(p['type'], 1.0)
        e_rem_ap = max(0, e_atk - p_def) # 敵の実効AP
        e_raw = int(e['atk'] * AP_MULTS[min(e_rem_ap, 8)] * e_mult)
        
        # 呼び出し (e_atkが7以上なら貫通)
        e_final = self.apply_damage(p, e_raw, e_atk, e_rem_ap)
        
        # --- ログ更新 ---
        self.log = f"自:攻{p_atk}防{p_def} / 敵:攻{e_atk}防{e_def}\n💥 与ダメ:{p_final} / 被ダメ:{e_final}"
        
        # 死亡判定
        if p['hp'] <= 0:
            p['hp'] = 0; p['is_dead'] = True
            next_p = next((i for i, d in enumerate(self.p_team) if not d['is_dead']), None)
            if next_p is not None: 
                self.p_idx = next_p
                self.log += f"\n💀 {p['name']} は倒れた！ {self.p_team[self.p_idx]['name']} 出撃！"
        
        if e['hp'] <= 0:
            e['hp'] = 0; e['is_dead'] = True
            next_e = next((i for i, d in enumerate(self.e_team) if not d['is_dead']), None)
            if next_e is not None:
                self.e_idx = next_e
                self.log += f"\n🦖 野生の {e['name']} を倒した！ 次の敵が出現！"

        # 決着判定
        p_all_dead = all(d['is_dead'] for d in self.p_team)
        e_all_dead = all(d['is_dead'] for d in self.e_team)

        if p_all_dead or e_all_dead:
            win = e_all_dead
            reward_text = ""
            
            if win:
                reward_text = self.apply_rewards(interaction)
            
            embed = self.make_embed()
            result_emoji = "✨ あなたの勝利！" if win else "💀 敗北..."
            
            # 報酬がある場合は、結果の下に追加表示する
            if reward_text:
                result_value = f"{result_emoji}\n\n**勝利報酬**\n{reward_text} 入手！"
            else:
                result_value = result_emoji
                
            embed.add_field(name="結果", value=result_value, inline=False)
            
            # 最後にデータを保存
            save_users(load_users()) 
            
            # メッセージを更新（View=Noneでボタンを消す）
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        else:
            recovery = min((self.turn) + 1, 4)
            self.p_ap = min(8, (self.p_ap - p_atk - p_def) + recovery)
            self.e_ap = min(8, (self.e_ap - e_atk - e_def) + recovery)    
            self.turn += 1
            self.step = "ATK"
            self.create_buttons()
            await interaction.response.edit_message(embed=self.make_embed(), view=self)

    def apply_rewards(self, interaction: discord.Interaction):
        log_parts = []
        rew = self.mission_data.get('reward', {})
        sdna_rew = self.mission_data.get('S-DNA', {})
        
        users = load_users()
        user_id = str(interaction.user.id)
        u = get_user(user_id, users)
        series_name = self.mission_data.get("series", "General")
        
        # 報酬加算ループ
        for key, amount in rew.items():
            if key == "pack":
                # パックを開封し、結果を取得
                pack_result = give_pack(user_id, users, amount)
                log_parts.append(f"📦 {pack_result['pack_display_name']}")
                
                # 【追加】開封Embedを非同期で表示させる
                # self.stop() の前に実行されるようにスケジュール
                import asyncio
                asyncio.create_task(show_pack_open_result(interaction, pack_result, amount, u))
                
            elif key == "medal":
                if "medals" not in u: u["medals"] = {}
                u["medals"][series_name] = u["medals"].get(series_name, 0) + amount
                u["medals"]["total"] = u["medals"].get("total", 0) + amount
                log_parts.append(f"🏅 {series_name}メダル+{amount}")

            elif key in EMOJI:
                u[key] = u.get(key, 0) + amount
                log_parts.append(f"{EMOJI[key]}{amount}")

        # S-DNAの処理
        if sdna_rew:
            if "s_dna" not in u: u["s_dna"] = {}
            for s_id, s_amt in sdna_rew.items():
                u["s_dna"][str(s_id)] = u["s_dna"].get(str(s_id), 0) + s_amt
                # S-DNA個別の絵文字対応
                s_emoji = EMOJI.get(f"s_dna{s_id}", EMOJI.get('s_dna', '🧪'))
                log_parts.append(f"{s_emoji}{s_amt}")

        save_users(users)
        self.u = u
        return " ".join(log_parts) if log_parts else ""
        
class OpponentSetupModal(discord.ui.Modal, title="迎撃パーティの選択"):
    # 最大3体分のUID入力欄
    uids_input = discord.ui.TextInput(
        label="出撃させる恐竜のUIDをカンマ区切りで入力",
        placeholder="例: 1, 5, 12 (最大3体まで)",
        required=True,
        min_length=1,
        max_length=20
    )

    def __init__(self, opponent, challenger, challenger_uids, users_data):
        super().__init__()
        self.opponent = opponent
        self.challenger = challenger
        self.challenger_uids = challenger_uids
        self.users = users_data

    async def on_submit(self, interaction: discord.Interaction):
        # 入力されたUIDをリスト化
        try:
            raw_uids = [int(x.strip()) for x in self.uids_input.value.split(",") if x.strip()]
            opp_uids = raw_uids[:3] # 最大3体
            
            # データの存在チェック
            u = get_user(self.opponent.id, self.users)
            valid_uids = [d['uid'] for d in u['inventory']]
            if not all(uid in valid_uids for uid in opp_uids):
                await interaction.response.send_message("❌ 所持していないUIDが含まれています。", ephemeral=True)
                return

            # バトル開始！
            pvp_view = PVPBattleView(interaction, self.challenger, self.opponent, self.challenger_uids, opp_uids, self.users)
            pvp_view.create_buttons()
            await interaction.response.send_message(f"🔥 バトル開始！ {self.challenger.mention} vs {self.opponent.mention}")
            await interaction.edit_original_response(embed=pvp_view.make_embed(), view=pvp_view)
            
        except ValueError:
            await interaction.response.send_message("❌ 数字をカンマ区切りで入力してください。", ephemeral=True)

class PVPBattleView(View):
    def __init__(self, interaction, p1, p2, p1_uids, p2_uids, users_data):
        super().__init__(timeout=600)
        self.interaction = interaction
        self.p1 = p1  
        self.p2 = p2  
        self.users = users_data
        
        # チーム構築
        self.teams = {
            p1.id: self.build_team(p1.id, p1_uids),
            p2.id: self.build_team(p2.id, p2_uids)
        }
        
        self.turn_owner = p1.id
        self.ap = {p1.id: 1, p2.id: 1}
        self.turn_count = 1
        self.step = "ATK"
        self.selected_atk = 0
        self.log = f"⚔️ バトル開始！ {p1.display_name} のターンです。"

    def build_team(self, user_id, uids):
        team = []
        u = get_user(user_id, self.users)
        for uid in uids:
            d_item = next((i for i in u['inventory'] if i['uid'] == uid), None)
            if d_item:
                d = dino_book[str(d_item['id'])]
                hp = get_current_stat(d['hp'], d_item['lv'])
                
                # --- 群れの実装 ---
                is_flock = int(d.get('flock', 0)) == 1
                team.append({
                    "name": d['name'], 
                    "type": d['type'], 
                    "hp": hp, 
                    "max_hp": hp,
                    "atk": get_current_stat(d['atk'], d_item['lv']), 
                    "is_dead": False,
                    "is_flock": is_flock,
                    "flock_count": 3 if is_flock else 1  # 3体で1組（HP 100%, 66%, 33%）
                })
        return {"list": team, "idx": 0}

    def make_embed(self):
        embed = discord.Embed(title=f"🏟️ PvPマッチ: ターン {self.turn_count}", color=0xe74c3c)
        
        # HPバーを生成する補助関数
        def hp_bar(curr, maxi):
            per = max(0, min(10, int(curr/maxi*10)))
            return "🟩" * per + "⬜" * (10-per)

        for user in [self.p1, self.p2]:
            t = self.teams[user.id]
            curr = t['list'][t['idx']]
            lives = "".join(["🔵" if not d['is_dead'] else "❌" for d in t['list']])
            status = "▶️ **あなたの手番**" if self.turn_owner == user.id else "⏳ 待機中"
            
            name_display = curr['name']
            if curr['is_flock']:
                name_display += f" (🏃×{curr['flock_count']})"
            
            embed.add_field(
                name=f"{user.display_name} {lives}",
                value=f"{status}\n**{name_display}**\n{hp_bar(curr['hp'], curr['max_hp'])}\nHP: {curr['hp']}/{curr['max_hp']}\nAP: **{self.ap[user.id]}**",
                inline=True
            )
        
        embed.description = f"```ml\n{self.log}\n```"
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.turn_owner:
            await interaction.response.send_message("相手のターンが終わるまで待ってください！", ephemeral=True)
            return False
        return True

    def create_buttons(self):
        self.clear_items()
        current_ap = self.ap[self.turn_owner]
        
        # 1. 攻撃・防御ボタン (数字のみ・色分け)
        limit = current_ap if self.step == "ATK" else (current_ap - self.selected_atk)
        # 攻撃(ATK)は赤色、防御(DEF)は青色
        style = discord.ButtonStyle.danger if self.step == "ATK" else discord.ButtonStyle.primary

        for i in range(limit + 1):
            btn = Button(label=str(i), style=style, custom_id=f"ap_{i}")
            btn.callback = self.ap_callback
            self.add_item(btn)

        # 2. 交代ボタン (攻撃選択ステップかつ、1AP以上ある場合のみ)
        if self.step == "ATK" and current_ap >= 1:
            t = self.teams[self.turn_owner]
            for i, dino in enumerate(t['list']):
                if not dino['is_dead'] and i != t['idx']:
                    btn = Button(label=f"交代: {dino['name']}", style=discord.ButtonStyle.green, custom_id=f"sw_{i}")
                    btn.callback = self.switch_callback
                    self.add_item(btn)

    async def switch_callback(self, interaction: discord.Interaction):
        # 自分のターンかチェック
        if interaction.user.id != self.turn_owner:
            return await interaction.response.send_message("相手のターンです！", ephemeral=True)

        new_idx = int(interaction.data['custom_id'].split("_")[1])
        t = self.teams[self.turn_owner]
        old_name = t['list'][t['idx']]['name']
        
        # 交代処理
        t['idx'] = new_idx
        self.ap[self.turn_owner] -= 1 # 1AP消費
        self.log = f"🔄 {interaction.user.display_name} は {old_name} から {t['list'][new_idx]['name']} に交代した！ (1AP消費)"
        
        self.create_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    async def ap_callback(self, interaction: discord.Interaction):
        val = int(interaction.data['custom_id'].split("_")[1])
        
        if self.step == "ATK":
            self.selected_atk = val
            self.step = "DEF"
            self.create_buttons()
            # 攻撃側が選んだ段階では、ログには何も出さず「防御選択中」にする
            self.log = f"⚔️ {interaction.user.display_name} が行動を選択しました。\n防御側はAPを選んでください。"
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
        else:
            self.selected_def = val

            await self.resolve_pvp_turn(interaction, self.selected_atk, self.selected_def)

    async def resolve_pvp_turn(self, interaction, p_atk, p_def):
        attacker_id = self.turn_owner
        defender_id = self.p2.id if attacker_id == self.p1.id else self.p1.id
        
        atk_team = self.teams[attacker_id]
        def_team = self.teams[defender_id]
        
        a = atk_team['list'][atk_team['idx']]
        d = def_team['list'][def_team['idx']]
        
        elem_mult = ELEMENT_CHART.get(a['type'], {}).get(d['type'], 1.0)
        
        # 2. 実効AP（防御を差し引いた、ダメージ倍率用のAP）を計算
        rem_ap = max(0, p_atk - p_def)
        
        # 3. AP倍率を適用して「元のダメージ」を計算
        rem_mult = AP_MULTS[min(rem_ap, 8)]
        raw_damage = int(a['atk'] * rem_mult * elem_mult)
        
        # 4. apply_damage 関数を呼び出し（ここで貫通判定とHP減少を行う）
        # 引数: (対象, ダメージ, 選択したAP, 実効AP)
        actual_damage = self.apply_damage(d, raw_damage, p_atk, rem_ap)
        # --- ダメージ計算 (ここまで) ---

        attacker_name = self.p1.display_name if attacker_id == self.p1.id else self.p2.display_name
        
        # ここを修正！ p_final ではなく actual_damage を使う
        self.log = (
            f"📢 ターン結果発表！\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔥 {attacker_name}の攻撃： {p_atk} AP\n"
            f"🛡️ 相手の防御： {p_def} AP\n"
            f"➡️ 差し引き {rem_ap} AP 分のダメージ！\n"
            f"💥 {d['name']} に {actual_damage} ダメージ！" # ここを actual_damage に変更
        )
        
        if d['hp'] <= 0:
            d['hp'] = 0
            d['is_dead'] = True
            next_idx = next((i for i, dino in enumerate(def_team['list']) if not dino['is_dead']), None)
            
            if next_idx is not None:
                def_team['idx'] = next_idx
                self.log += f"\n💀 {d['name']} は倒れた！ 次の個体が出撃します。"
            else:
                # 🏆 試合終了：報酬処理
                winner_id = str(attacker_id)
                loser_id = str(defender_id)
                self.users[winner_id]['cash'] += 150
                self.users[winner_id]['rp'] += 200
                self.users[loser_id]['cash'] = max(0, self.users[loser_id]['cash'] - 30)
                save_users(self.users)
                
                winner_m = self.p1 if int(winner_id) == self.p1.id else self.p2
                loser_m = self.p2 if int(winner_id) == self.p1.id else self.p1

                embed = self.make_embed()
                embed.title = "🏁 バトル決着！"
                embed.add_field(name="結果", value=f"👑 **勝者:** {winner_m.mention}\n💀 **敗者:** {loser_m.mention}", inline=False)
                await interaction.response.edit_message(embed=embed, view=None)
                self.stop()
                return
                
        current_round = (self.turn_count + 1) // 2
        reg_recovery = min(current_round, 4)

        # 2. 攻撃側のAPを消費
        self.ap[attacker_id] = max(0, self.ap[attacker_id] - p_atk - p_def)
        
        # 2. ターン交代
        self.turn_owner = defender_id 
        self.turn_count += 1

        # 3. 次の手番の人（新・攻撃側）のAP回復計算
        # 現在のラウンド数に基づく基本回復量 (1, 2, 3, 最大4)
        current_round = (self.turn_count + 1) // 2
        base_recovery = min(current_round, 4)

        # 後攻の最初のターン (ターン2) は必ず +1
        if self.turn_count == 2:
            base_recovery = 1
            
        # 【AP持ち越しシステム】
        # 前ターンの残り(self.ap[self.turn_owner]) + 今回の回復量(base_recovery)
        new_ap = self.ap[self.turn_owner] + base_recovery
        
        # 最大8を超えないように設定
        self.ap[self.turn_owner] = min(8, new_ap)

        # 4. 状態リセット
        self.step = "ATK"
        self.selected_atk = 0
        self.create_buttons()

        # 5. 画面更新
        try:
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
        except discord.errors.InteractionResponded:
            await interaction.edit_original_response(embed=self.make_embed(), view=self)
        except Exception as e:
            print(f"Update Error: {e}")

class WalletView(discord.ui.View):
    def __init__(self, u):
        super().__init__(timeout=60)
        self.u = u
        self.page = 1
        self.max_page = 3

    def make_embed(self):
        if self.page == 1:
            # 1ページ目: 基本通貨
            embed = discord.Embed(title="💰 あなたのウォレット (1/3)", color=0xffd700)
            desc = (
                f"{EMOJI['coin']} コイン: {self.u['coin']:,}\n"
                f"{EMOJI['cash']} キャッシュ: {self.u['cash']:,}\n"
                f"{EMOJI['dna']} DNA: {self.u['dna']:,}\n"
                f"{EMOJI['food']} フード: {self.u['food']:,}\n"
                f"{EMOJI['rp']} RP: {self.u.get('rp', 0):,}\n"
                f"{EMOJI['amber']} アンバー: {self.u.get('amber', 0):,}\n"
                f"{EMOJI['b_dna']} B-DNA: {self.u.get('b_dna', 0):,}"
            )
            embed.description = desc
            return embed

        elif self.page == 2:
            # 2ページ目: S-DNA & Shard
            embed = discord.Embed(title="🧪 特殊アイテム (2/3)", color=0x9b59b6)
            
            # --- S-DNAの全表示ロジック ---
            sdna_display = []
            # EMOJI辞書から "s_dna" で始まるキー（s_dna, s_dna36など）をすべてループ
            for key, emoji_syntax in EMOJI.items():
                if key.startswith("s_dna"):
                    # 絵文字キーから数字部分を抽出 (例: "s_dna36" -> "36")
                    # "s_dna" そのものの場合は、汎用的なIDとして扱う
                    d_id = key.replace("s_dna", "")
                    
                    # ユーザーデータから所持数を取得（なければ0）
                    # self.u['s_dna'] が辞書であることを想定
                    user_sdna_dict = self.u.get('s_dna', {})
                    amount = user_sdna_dict.get(d_id, 0)
                    
                    sdna_display.append(f"{emoji_syntax} {amount:,}個")

            # --- Shardの表示ロジック ---
            shard_list = []
            for d_id, amt in self.u.get('shard', {}).items():
                if amt > 0:
                    d_info = dino_book.get(str(d_id))
                    name = d_info.get('name', f"ID:{d_id}") if d_info else f"ID:{d_id}"
                    shard_list.append(f"{EMOJI.get('shard', '💎')} {name}: {amt:,}個")

            # フィールドに追加
            # S-DNAは数が多いので、joinでつなげて表示
            embed.add_field(
                name="🧪 S-DNA 一覧", 
                value="\n".join(sdna_display) if sdna_display else "データなし", 
                inline=False
            )
            embed.add_field(
                name="💎 Shard", 
                value="\n".join(shard_list) if shard_list else "なし", 
                inline=False
            )
            return embed

        else:
            # 3ページ目: メダル内訳
            embed = discord.Embed(title="🏅 獲得メダル一覧 (3/3)", color=0xe67e22)
            medals_dict = self.u.get('medals', {})
            medal_list = [f"・[{s}] メダル {c}枚" for s, c in medals_dict.items() if s != "total" and c > 0]
            embed.description = "\n".join(medal_list) if medal_list else "なし"
            embed.set_footer(text=f"総獲得メダル数: {medals_dict.get('total', 0)}枚")
            return embed

    @discord.ui.button(label="ページ切り替え", style=discord.ButtonStyle.grey)
    async def toggle_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 修正前: self.page = 2 if self.page == 1 else 1
        
        # 修正後: ページを1進める。最大ページ(3)を超えたら1に戻す
        self.page += 1
        if self.page > self.max_page:
            self.page = 1
            
        await interaction.response.edit_message(embed=self.make_embed(), view=self)
bot = MyBot()

# --- スラッシュコマンド ---

@bot.tree.command(name="start", description="パークを開設します")
async def start(interaction: discord.Interaction):
    users = load_users()
    if str(interaction.user.id) in users:
        await interaction.response.send_message("既にパークを所有しています！", ephemeral=True)
    else:
        get_user(interaction.user.id, users)
        save_users(users)
        await interaction.response.send_message("🏝️ **パーク開設完了！** `/pack` で最初の恐竜を手に入れよう！")

@bot.tree.command(name="wallet", description="所持金やアイテムを確認します")
async def wallet(interaction: discord.Interaction):
    users = load_users()
    u = get_user(interaction.user.id, users)
    view = WalletView(u)
    await interaction.response.send_message(embed=view.make_embed(), view=view)

@bot.tree.command(name="event", description="イベント一覧を表示、またはID指定で挑戦します")
@app_commands.describe(event_id="挑戦するイベントのID（省略で一覧表示）")
async def event_command(interaction: discord.Interaction, event_id: int = None):
    # 1. データの読み込み
    event_data = load_events()
    missions = event_data.get("missions", [])

    if not missions:
        await interaction.response.send_message("❌ 現在開催中のイベントはありません。", ephemeral=True)
        return

    # ユーザーデータの読み込み
    users = load_users()
    u = get_user(interaction.user.id, users)

    # --- パターンA: IDが指定された場合 (個別のイベント詳細へ) ---
    if event_id is not None:
        mission_data = next((m for m in missions if m['id'] == event_id), None)
        
        if not mission_data:
            await interaction.response.send_message(f"❌ ID: `{event_id}` のイベントは見つかりませんでした。", ephemeral=True)
            return

        if not u['inventory']:
            await interaction.response.send_message("❌ 所持している恐竜がいません。", ephemeral=True)
            return

        # 個別のミッションがある時だけ EventPreviewView を呼び出す
        # 引数: interaction, ユーザーデータ, 空のチームリスト, ミッションデータ
        view = EventPreviewView(interaction, u, [], mission_data)
        await interaction.response.send_message(embed=view.make_preview_embed(), view=view)
        return # ここで処理終了

    # --- パターンB: ID未指定の場合 (一覧表示を表示) ---
    # ここでは mission 変数は使わず、EventListView を呼び出すだけにする
    view = EventListView(interaction, missions)
    await interaction.response.send_message(embed=view.make_embed(), view=view)

@bot.tree.command(name="dino", description="名前またはIDで恐竜のステータスを表示します")
async def dino_info(interaction: discord.Interaction, query: str):
    found_id = None
    if query in dino_book:
        found_id = query
    else:
        for d_id, d_data in dino_book.items():
            if query.lower() in d_data['name'].lower():
                found_id = d_id
                break 

    if not found_id:
        await interaction.response.send_message(f"❌ 「{query}」は見つかりませんでした。", ephemeral=True)
        return

    embed = create_dino_embed(dino_book[found_id], found_id)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="inv", description="所持恐竜の一覧または詳細を表示します")
async def inventory(interaction: discord.Interaction, uid: int = None):
    users = load_users()
    u = get_user(interaction.user.id, users)
    inv = u.get('inventory', [])
    
    # 新しいもの順（取得日順）に表示するためにリバース
    inv = list(reversed(inv))

    if not inv:
        await interaction.response.send_message("恐竜がいません。", ephemeral=True)
        return
    
    # 詳細表示モード (UID指定時)
    if uid:
        d_item = next((i for i in inv if i['uid'] == uid), None)
        if not d_item:
            await interaction.response.send_message("そのUIDの恐竜は見つかりません。", ephemeral=True)
            return
            
        d_base = dino_book.get(str(d_item['id']))
        if not d_base:
            await interaction.response.send_message("図鑑データエラー。管理者に報告してください。", ephemeral=True)
            return

        embed = create_dino_embed(d_base, str(d_item['id']), lv=d_item['lv'], uid=uid)
        await interaction.response.send_message(embed=embed)
    
    # 一覧表示モード (ページ式)
    else:
        view = InventoryView(inv, interaction.user.id)
        await interaction.response.send_message(embed=view.make_embed(), view=view)

@bot.tree.command(name="feed", description="エサをあげます（Lv10/20/30/40で停止）")
async def feed(interaction: discord.Interaction, uid: int, amount: int):
    if amount <= 0:
        await interaction.response.send_message("❌ 1回以上の回数を指定してください。", ephemeral=True)
        return

    users = load_users()
    u = get_user(interaction.user.id, users)
    
    # インベントリから対象の恐竜を探す
    dino = next((i for i in u['inventory'] if i['uid'] == uid), None)
    
    if not dino:
        await interaction.response.send_message("❌ 指定されたUIDの恐竜が見つかりません。", ephemeral=True)
        return
        
    if dino['lv'] % 10 == 0:
        await interaction.response.send_message(f"❌ Lv.{dino['lv']}に達しています。進化が必要です。", ephemeral=True)
        return

    # 図鑑（dino_book）から詳細データを取得
    dino_info = dino_book.get(str(dino['id']))
    if not dino_info:
        await interaction.response.send_message("❌ 図鑑データが見つかりません。", ephemeral=True)
        return

    dino_name = dino_info.get('name', '不明な恐竜')
    
    # --- 倍率の設定 ---
    # 1. レアリティ倍率
    rarity_weight = get_rarity_weight(dino_info['rarity'])
    
    # 2. ハイブリッド倍率 (0->1倍, 1->3倍, 2->6倍)
    hybrid_val = dino_info.get('hybrid', 0)
    if hybrid_val == 1:
        hybrid_factor = 3
    elif hybrid_val == 2:
        hybrid_factor = 6
    else:
        hybrid_factor = 1

    old_lv = dino['lv']
    actual_count = 0
    total_cost = 0

    for _ in range(amount):
        # 指定された計算式: Lv × レアリティ倍率 × ハイブリッド倍率 × 100
        cost = dino['lv'] * rarity_weight * hybrid_factor * 100
        
        if u['food'] >= cost:
            u['food'] -= cost
            total_cost += cost
            dino['lv'] += 1
            actual_count += 1
            
            # 10の倍数でストップ
            if dino['lv'] % 10 == 0:
                break
        else:
            break

    if actual_count == 0:
        # 次の1回に必要なコストを計算して表示
        next_cost = dino['lv'] * rarity_weight * hybrid_factor * 100
        await interaction.response.send_message(f"❌ フードが足りません。(必要: {next_cost:,} {EMOJI['food']})", ephemeral=True)
        return

    save_users(users)

    # シンプルな埋め込みメッセージの作成
    embed = discord.Embed(
        description=f"**#{uid} {dino_name}** が **Lv.{dino['lv']}** になりました！\n"
                    f"消費したエサ : {EMOJI['food']} {total_cost:,}",
        color=0x2ecc71
    )
    
    # 最大レベル到達時のみフッターを表示（任意）
    if dino['lv'] % 10 == 0:
        embed.set_footer(text="進化が必要です。")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="factory", description="食料工場から餌を回収します")
async def factory(interaction: discord.Interaction):
    users = load_users()
    u = get_user(interaction.user.id, users)
    
    now = datetime.now()
    last_str = u.get('last_factory_claim', "2000-01-01 00:00:00")
    last_time = datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
    
    # 経過時間を計算（分単位）
    diff = now - last_time
    minutes_passed = int(diff.total_seconds() / 60)
    
    # --- 設定値 ---
    food_per_minute = 50  # 1分間に生産される餌の量
    max_minutes = 1440    # 最大24時間分まで蓄積可能
    # --------------
    
    if minutes_passed <= 0:
        await interaction.response.send_message("🏭 まだ餌が生産されていません。もう少し待ってみよう！", ephemeral=True)
        return

    # 蓄積時間を上限でカット
    actual_minutes = min(minutes_passed, max_minutes)
    earned_food = actual_minutes * food_per_minute
    
    # データ更新
    u['food'] += earned_food
    u['last_factory_claim'] = now.strftime("%Y-%m-%d %H:%M:%S")
    save_users(users)
    
    # メッセージ作成
    embed = discord.Embed(title="🏭 食料工場 - 回収完了", color=0xffa500)
    embed.add_field(name="蓄積時間", value=f"{minutes_passed} 分 (最大 {max_minutes}分)", inline=True)
    embed.add_field(name="獲得した餌", value=f"{EMOJI['food']} **{earned_food:,}**", inline=True)
    embed.add_field(name="現在の総数", value=f"{EMOJI['food']} {u['food']:,}", inline=False)
    
    if minutes_passed > max_minutes:
        embed.set_footer(text="⚠️ 工場の貯蔵庫がいっぱいになっていました！こまめに回収しましょう。")

    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="pack", description="カードパックを開封します")
@app_commands.describe(pack_type="パックの種類を選択してください")
@app_commands.choices(pack_type=[
    app_commands.Choice(name="無料パック (1時間毎)", value="free"),
    app_commands.Choice(name="純金パック (10,000 RP)", value="gold")
])
async def pack(interaction: discord.Interaction, pack_type: str):
    users = load_users()
    u = get_user(interaction.user.id, users)
    now = datetime.now()

    # --- 条件チェック (時間制限やコスト) ---
    if pack_type == "free":
        last_str = u.get('last_free_pack', "2000-01-01 00:00:00")
        last = datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
        
        if now < last + timedelta(hours=1):
            rem = (last + timedelta(hours=1)) - now
            minutes = rem.seconds // 60
            await interaction.response.send_message(f"⏳ あと {minutes}分 お待ちください。", ephemeral=True)
            return
        
        # 最後に時刻を更新するためにここで代入（保存はgive_packの後）
        u['last_free_pack'] = now.strftime("%Y-%m-%d %H:%M:%S")
        color = 0x3498db

    elif pack_type == "gold":
        if u.get('rp', 0) < 10000:
            rp_emoji = EMOJI.get('rp')
            await interaction.response.send_message(f"❌ {EMOJI['rp']} が足りません (10,000必要 / 所持: {u.get('rp', 0):,})", ephemeral=True)
            return
        
        # コストを引く（give_pack内ではなく、コマンド側で制御するのが安全です）
        u['rp'] -= 10000
        color = 0xffd700

    # --- 【重要】汎用関数 give_pack で抽選と付与を実行 ---
    # この中でレアリティ・属性・水中フラグの重み付け抽選が行われます
    result = give_pack(interaction.user.id, users, pack_type)

    if not result:
        await interaction.response.send_message("❌ パックのデータが見つかりません。", ephemeral=True)
        return

    # データの保存
    save_users(users)

    # --- Embed表示 ---
    # give_packが返してくれたIDを使ってステータスを取得
    dino = dino_book[str(result['selected_id'])] # selected_idを返すようにgive_packを少し修正
    hp = get_current_stat(dino['hp'], 1)
    atk = get_current_stat(dino['atk'], 1)
    type_emoji = EMOJI.get(f"type_{dino['type']}", "❓")
    
    embed = discord.Embed(title=f"📦 {result['pack_display_name']} 開封結果", color=color)

    # --- 恐竜が当選したかどうかで処理を分ける ---
    if result['selected_id'] is not None:
        # 当選した場合の処理
        dino = dino_book[str(result['selected_id'])]
        hp = get_current_stat(dino['hp'], 1)
        atk = get_current_stat(dino['atk'], 1)
        type_emoji = EMOJI.get(f"type_{dino['type']}", "❓")
        
        embed.add_field(
            name=f"#{result['uid']} {dino['name']} (Lv.1)", 
            value=f"{type_emoji} レアリティ: **{dino['rarity']}**\n❤️ HP: {hp} | ⚔️ ATK: {atk}", 
            inline=False
        )
    else:
        # 外れ（恐竜なし）の場合の処理
        embed.add_field(
            name="恐竜なし", 
            value="残念！今回のパックには恐竜が入っていませんでした。", 
            inline=False
        )
    
    # 獲得報酬の表示
    reward_text = f"{EMOJI['coin']} {result['coin']}\n{EMOJI['dna']} {result['dna']}\n{EMOJI['cash']} {result['cash']}\n{EMOJI['food']} {result['food']}\n{EMOJI['rp']} {result['rp']}"
    embed.add_field(name="🎁 獲得ボーナス", value=reward_text, inline=False)
    
    if pack_type == "gold":
        embed.set_footer(text=f"残り所持RP: {u['rp']:,}")
    
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="buy", description="アンバーで生物を購入します")
async def buy_dino(interaction: discord.Interaction, dino_id: str):
    users = load_users()
    u = get_user(interaction.user.id, users)
    
    # 図鑑に存在するか確認
    if dino_id not in dino_book:
        await interaction.response.send_message("❌ そのIDの生物は見つかりません。", ephemeral=True)
        return
        
    dino_data = dino_book[dino_id]
    amber_cost = dino_data.get('buy_amber', 0)
    
    # buy_amberが0の場合は購入不可
    if amber_cost <= 0:
        await interaction.response.send_message(f"❌ **{dino_data['name']}** はアンバーで購入することはできません。", ephemeral=True)
        return
    
    # 所持金チェック
    if u.get('amber', 0) < amber_cost:
        await interaction.response.send_message(f"❌ アンバーが足りません。 (必要: {amber_cost:,})", ephemeral=True)
        return
        
    # 購入処理
    u['amber'] -= amber_cost
    new_uid = get_next_uid(u)
    new_dino = {
        "uid": new_uid,
        "id": dino_id,
        "lv": 1,
        "exp": 0,
        "get_date": datetime.now().strftime("%Y-%m-%d")
    }
    u['inventory'].append(new_dino)
    save_users(users)
    
    await interaction.response.send_message(f"✅ {EMOJI['amber']} `{amber_cost:,}` を支払い、**{dino_data['name']}** (UID: {new_uid}) を購入しました！")



@bot.tree.command(name="sell", description="所持している恐竜を売却し、DNAを受け取ります")
@app_commands.describe(uid="売却する恐竜のUIDを入力してください")
async def sell(interaction: discord.Interaction, uid: int):
    users = load_users()
    u = get_user(interaction.user.id, users)
    
    # 1. インベントリから該当する恐竜(UID)を探す
    inventory = u.get('inventory', [])
    target_index = -1
    target_dino_data = None
    
    for i, dino in enumerate(inventory):
        if dino.get('uid') == uid:
            target_index = i
            target_dino_data = dino
            break
            
    if target_index == -1:
        await interaction.response.send_message(f"❌ UID: {uid} の恐竜を所持していません。", ephemeral=True)
        return

    # 2. 図鑑から恐竜の情報を取得して価格を計算
    dino_id_str = str(target_dino_data['id'])
    if dino_id_str not in dino_book:
        await interaction.response.send_message("❌ 図鑑データにエラーがあります。管理者に連絡してください。", ephemeral=True)
        return
    
    dino_info = dino_book[dino_id_str]
    try:
        original_price = int(dino_info.get('buy_dna', 0))
    except ValueError:
        original_price = 0
        
    sell_price = original_price // 2  # 小数点切り捨てで半分にする

    # 3. 売却処理（インベントリから削除、DNA加算）
    # 削除する前に名前などを取得しておく
    dino_name = dino_info.get('name', '不明な恐竜')
    dino_lv = target_dino_data.get('lv', 1)
    
    removed_dino = inventory.pop(target_index)
    u['dna'] = u.get('dna', 0) + sell_price
    
    # 4. 保存
    save_users(users)
    
    # 5. 結果表示
    embed = discord.Embed(
        title="💰 売却完了",
        description=f"**{dino_name}** (Lv.{dino_lv}) を売却しました。",
        color=discord.Color.red()
    )
    embed.add_field(name="売却価格", value=f"+ {sell_price} DNA", inline=True)
    embed.add_field(name="現在のDNA", value=f"{u['dna']} DNA", inline=True)
    embed.set_footer(text=f"UID: {uid} を削除しました")
    
    await interaction.response.send_message(embed=embed)

@tasks.loop(seconds=60)  # 60秒ごとに全ユーザーの進化状況をチェック
async def check_evolution_finish():
    users = load_users()
    data_changed = False
    now = datetime.now()

    for user_id_str, u in users.items():
        # インベントリ内の恐竜をループ
        for d in u.get('inventory', []):
            if "evolution_end" in d:
                end_time = datetime.strptime(d['evolution_end'], "%Y-%m-%d %H:%M:%S")
                
                # もし完了時間を過ぎていたら
                if now >= end_time:
                    # 進化・融合の確定処理
                    old_name = dino_book.get(str(d['id']), {'name': '不明'})['name']
                    
                    if "pending_hybrid_id" in d:
                        new_id = d['pending_hybrid_id']
                        new_name = dino_book.get(str(new_id), {'name': '新種'})['name']
                        d['id'] = int(new_id)
                        d['lv'] = 1
                        del d['pending_hybrid_id']
                        announce_text = f"🧪 <@{user_id_str}> さん、融合完了！\n**{old_name}** ➔ **{new_name}** が誕生しました！"
                    else:
                        d['lv'] += 1
                        new_lv = d['lv']
                        announce_text = f"🧬 <@{user_id_str}> さん、進化完了！\n**{old_name}** が **Lv.{new_lv}** になりました！"

                    # 予約時間を消して保存フラグを立てる
                    del d['evolution_end']
                    data_changed = True

                    # 通知を送る
                    channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
                    if channel:
                        try:
                            await channel.send(announce_text)
                        except Exception as e:
                            print(f"自動通知エラー: {e}")

    if data_changed:
        save_users(users)
    
@bot.tree.command(name="evolve", description="恐竜を合成・進化させます")
@app_commands.describe(mode="アクションを選択", uid1="個体1 (ベース)", uid2="個体2 (材料)")
@app_commands.choices(mode=[
    app_commands.Choice(name="🧬 合成・融合開始", value="start"),
    app_commands.Choice(name="⏩ キャッシュで時間を短縮", value="speedup"),
    app_commands.Choice(name="✅ 完了した恐竜を受け取る", value="claim")
])
async def evolve(interaction: discord.Interaction, mode: str, uid1: int = None, uid2: int = None):
    users = load_users()
    u = get_user(interaction.user.id, users)

    # --- 【1】合成・融合開始モード ---
    if mode == "start":
        if uid1 is None or uid2 is None:
            await interaction.response.send_message("❌ 合成には2体のUIDが必要です。", ephemeral=True)
            return
        
        # インベントリから検索
        d1 = next((i for i in u['inventory'] if i['uid'] == uid1), None)
        d2 = next((i for i in u['inventory'] if i['uid'] == uid2), None)
        
        if not d1 or not d2:
            await interaction.response.send_message("❌ 指定されたUIDの恐竜があなたの手持ちに見つかりません。", ephemeral=True)
            return

        # dino_book から情報を取得 (KeyError対策で .get() を使用)
        d1_info = dino_book.get(str(d1['id']))
        d2_info = dino_book.get(str(d2['id']))

        # 図鑑にデータがない場合のエラー回避
        if d1_info is None or d2_info is None:
            err_id = d1['id'] if d1_info is None else d2['id']
            await interaction.response.send_message(f"❌ 図鑑エラー: ID `{err_id}` のデータがCSVに見つかりません。", ephemeral=True)
            return

        # --- 分岐判定 ---
        # A. 通常の進化 (同種合成)
        if str(d1['id']) == str(d2['id']):
            if d1.get('lv', 1) != d2.get('lv', 1) or d1.get('lv', 1) % 10 != 0:
                await interaction.response.send_message("❌ 通常進化には同じレベル(10, 20, 30)の2体が必要です。", ephemeral=True)
                return
            
            wait_minutes = d1.get('lv', 1) * 2
            display_msg = f"🧬 **{d1_info['name']}** の進化を開始しました！"

        # --- B. ハイブリッド融合 (異種合成) ---
        else:
            hybrid_recipes = load_hybrid_recipes()

            # --- 【重要】ここを修正：IDを数値(int)としてソートしてから文字列にする ---
            # これにより、("11", "0") でも必ず "0,11" というキーが生成されます
            raw_ids = sorted([int(d1['id']), int(d2['id'])])
            recipe_key = f"{raw_ids[0]},{raw_ids[1]}"
            
            recipe = hybrid_recipes.get(recipe_key)

            if not recipe:
                await interaction.response.send_message(
                    f"❌ レシピが見つかりません。\n"
                    f"検索キー: `{recipe_key}`\n"
                    f"(ヒント: hybrids.json のキーと一致するか確認してください)", 
                    ephemeral=True
                )
                return
            
            # Lv40チェック
            if int(d1.get('lv', 1)) < 40 or int(d2.get('lv', 1)) < 40:
                await interaction.response.send_message(
                    "❌ 融合には両方の個体が **Lv.40** である必要があります。", 
                    ephemeral=True
                )
                return

            # レアリティ別コスト (superstarなども含めた辞書)
            rarity_costs = {
                "common": 50, 
                "rare": 200, 
                "super_rare": 800, 
                "legendary": 2000,
                "superstar": 5000
            }
            
            r_key = str(d1_info.get('rarity', 'common')).lower()
            fusion_cost = rarity_costs.get(r_key, 1000)

            if u.get('dna', 0) < fusion_cost:
                await interaction.response.send_message(
                    f"❌ DNA不足 (必要: {fusion_cost} / 所持: {u.get('dna', 0)})", 
                    ephemeral=True
                )
                return

            # --- 処理確定 ---
            u['dna'] -= fusion_cost
            
            # 結果のIDを一時保存（claim時にこれに上書きする）
            d1['pending_hybrid_id'] = str(recipe['result_id']) 
            
            display_msg = f"🧪 **{recipe.get('name', '新種')}** への融合を開始しました！"
            wait_minutes = 30 # 時間計算ロジックを入れる場合はここを変更

        # 共通予約処理
        end_time = datetime.now() + timedelta(minutes=wait_minutes)
        d1['evolution_end'] = end_time.strftime("%Y-%m-%d %H:%M:%S")
        u['inventory'].remove(d2) # 材料を消す
        save_users(users)

        await interaction.response.send_message(f"{display_msg}\n✅ 完了予定: {d1['evolution_end']}")

    # --- 【2】スピードアップモード ---
    elif mode == "speedup":
        # (先ほど作成したスピードアップのロジックをここに配置)
        if uid1 is None:
            await interaction.response.send_message("❌ 短縮したい個体のUIDを指定してください。", ephemeral=True)
            return
        d1 = next((i for i in u['inventory'] if i['uid'] == uid1), None)
        if not d1 or "evolution_end" not in d1:
            await interaction.response.send_message("❌ その個体は進化中ではありません。", ephemeral=True)
            return

        end_time = datetime.strptime(d1['evolution_end'], "%Y-%m-%d %H:%M:%S")
        remaining_seconds = (end_time - datetime.now()).total_seconds()
        if remaining_seconds <= 0:
            await interaction.response.send_message("✅ すでに完了しています！", ephemeral=True)
            return

        cash_cost = max(5, int(remaining_seconds // 60) + 1)
        if u['cash'] < cash_cost:
            await interaction.response.send_message(f"❌ キャッシュ不足 (必要: {cash_cost})", ephemeral=True)
            return

        u['cash'] -= cash_cost
        d1['evolution_end'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_users(users)
        await interaction.response.send_message(f"⏩ {cash_cost} Cashで時間を短縮しました！")

    # --- 【3】受け取りモード ---
    elif mode == "claim":
        if uid1 is None:
            await interaction.response.send_message("❌ UIDを指定してください。", ephemeral=True)
            return

        d1 = next((i for i in u['inventory'] if i['uid'] == uid1), None)
        if not d1 or "evolution_end" not in d1:
            await interaction.response.send_message("❌ 進化・融合中の個体ではありません。", ephemeral=True)
            return

        end_time = datetime.strptime(d1['evolution_end'], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < end_time:
            await interaction.response.send_message("⌛ まだ完了していません。", ephemeral=True)
            return

        # 融合か通常進化かで分岐
        if "pending_hybrid_id" in d1:
            new_id = d1['pending_hybrid_id']
            old_name = dino_book.get(str(d1['id']), {'name': '不明'})['name']
            new_name = dino_book.get(str(new_id), {'name': '新種'})['name']
            
            d1['id'] = int(new_id) # ID更新
            d1['lv'] = 1           # 融合後はLv.1から
            del d1['pending_hybrid_id']
            msg = f"🧪 融合完了！ **{old_name}** は **{new_name}** に生まれ変わりました！"
        else:
            d1['lv'] += 1
            msg = f"🧬 進化完了！ **{dino_book[str(d1['id'])]['name']}** が Lv.{d1['lv']} になりました！"

        del d1['evolution_end']
        save_users(users)
        await interaction.response.send_message(msg)
    
@bot.tree.command(name="battle", description="最大3体でチーム戦を開始！")
async def battle(interaction: discord.Interaction, uid1: int, uid2: int = None, uid3: int = None):
    users = load_users(); u = get_user(interaction.user.id, users)
    uids = [uid for uid in [uid1, uid2, uid3] if uid is not None]
    
    # 敵の生成 (プレイヤーの数に合わせる)
    en_infos = []
    en_lvs = []
    for _ in range(len(uids)):
        en_id = random.choice(list(dino_book.keys()))
        en_infos.append(dino_book[en_id])
        en_lvs.append(random.randint(5, 15))

    view = BattleView(interaction, u, uids, en_infos, en_lvs)
    await interaction.response.send_message(embed=view.make_embed(), view=view)
    
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    if not check_evolution_finish.is_running():
        check_evolution_finish.start() # 監視スタート
    # dino_bookの読み込み等、既存の処理...

@bot.tree.command(name="reset", description="データをリセットします")
async def reset(interaction: discord.Interaction):
    await interaction.response.send_message("⚠️ 本当にリセットしますか？ 30秒以内に `yes` と打ってください。")
    def check(m): return m.author == interaction.user and m.content.lower() == "yes" and m.channel == interaction.channel
    try:
        await bot.wait_for('message', check=check, timeout=30.0)
        users = load_users(); uid = str(interaction.user.id)
        if uid in users: del users[uid]; save_users(users)
        await interaction.followup.send("✅ リセット完了。")
    except: await interaction.followup.send("⌛ キャンセルされました。")


@bot.tree.command(name="battle_pvp", description="他のプレイヤーに挑みます (参加費: 5キャッシュ)")
async def battle_pvp(interaction: discord.Interaction, opponent: discord.Member, uid1: int, uid2: int = None, uid3: int = None):
    if opponent.bot or opponent == interaction.user:
        await interaction.response.send_message("無効な相手です。", ephemeral=True); return

    users = load_users()
    u = get_user(interaction.user.id, users)
    
    # --- 参加費チェック ---
    entry_fee = 5
    if u['cash'] < entry_fee:
        await interaction.response.send_message(
            f"❌ キャッシュが足りません！対人戦には {EMOJI['cash']} {entry_fee} 必要です。", 
            ephemeral=True
        )
        return

    # 先に参加費を徴収
    u['cash'] -= entry_fee
    save_users(users)
    
    challenger_uids = [uid for uid in [uid1, uid2, uid3] if uid is not None]
    
    class AcceptView(View):
        def __init__(self):
            super().__init__(timeout=60)
        
        @discord.ui.button(label="受けて立つ！", style=discord.ButtonStyle.red)
        async def accept(self, btn_interaction, button):
            if btn_interaction.user != opponent:
                await btn_interaction.response.send_message("あなたへの挑戦ではありません！", ephemeral=True); return
            
            modal = OpponentSetupModal(opponent, interaction.user, challenger_uids, users)
            await btn_interaction.response.send_modal(modal)
            self.stop()

    view = AcceptView()
    await interaction.response.send_message(
        f"⚔️ **PVP CHALLENGE** ⚔️\n{opponent.mention}！ {interaction.user.mention} が勝負を挑んできたぞ！\n"
        f"(挑戦者は既に {EMOJI['cash']} {entry_fee} を支払いました)", 
        view=view
    )

@bot.tree.command(name="ranking", description="サーバー内の勝利数ランキングを表示します")
async def ranking(interaction: discord.Interaction):
    users = load_users()
    
    # 勝利数が多い順に並び替え
    # (user_id, data) のタプルにして、win_count でソート
    sorted_users = sorted(
        users.items(), 
        key=lambda x: x[1].get('win_count', 0), 
        reverse=True
    )

    embed = discord.Embed(title="🏆 恐竜バトル勝利数ランキング", color=0xf1c40f)
    
    ranking_text = ""
    for i, (user_id, data) in enumerate(sorted_users[:10], 1):
        # ユーザー名を取得（ボットが知っている範囲で）
        member = interaction.guild.get_member(int(user_id))
        name = member.display_name if member else f"User({user_id})"
        
        wins = data.get('win_count', 0)
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}位"
        ranking_text += f"{medal} **{name}**: {wins}勝\n"

    if not ranking_text:
        ranking_text = "まだ対戦データがありません。"

    embed.description = ranking_text
    await interaction.response.send_message(embed=embed)

    
@bot.tree.command(name="admin", description="管理者用アイテム・恐竜付与")
@app_commands.describe(category="付与するカテゴリー", target="対象メンバー", id_or_item="アイテム名または恐竜ID", amount="個数またはレベル")
@app_commands.choices(category=[
    app_commands.Choice(name="💰 アイテム (cash/dna/coin等)", value="item"),
    app_commands.Choice(name="🦖 恐竜 (dino_idを指定)", value="dino")
])
@app_commands.checks.has_role("JWTG X 管理人")
async def admin(interaction: discord.Interaction, category: str, target: discord.Member, id_or_item: str, amount: int = 1):
    users = load_users()
    u = get_user(target.id, users)
    
    if category == "item":
        # アイテム付与: キーが存在するか確認してから加算
        if id_or_item in u:
            u[id_or_item] += amount
        else:
            await interaction.response.send_message(f"❌ アイテム '{id_or_item}' はユーザーデータ内に見つかりません。", ephemeral=True)
            return

    elif category == "dino":
        # 恐竜付与: IDがdino_bookに存在するか確認
        # dino_bookのキーが文字列(str)であることを想定
        if id_or_item in dino_book:
            new_dino = {
                "uid": get_next_uid(u),
                "id": int(id_or_item),  # 恐竜IDを数値として保存する場合
                "lv": amount           # 引数のamountを初期レベルとして設定
            }
            u['inventory'].append(new_dino)
        else:
            await interaction.response.send_message(f"❌ 恐竜ID '{id_or_item}' は図鑑に存在しません。", ephemeral=True)
            return

    elif category == "medal":
        # id_or_item をシリーズ名として扱う
        if "medals" not in u: u["medals"] = {}
        u["medals"][id_or_item] = u["medals"].get(id_or_item, 0) + amount
        u["medals"]["total"] = u.get("medals", {}).get("total", 0) + amount
        
    save_users(users)
    await interaction.response.send_message(f"🛠️ {target.display_name} へ {id_or_item} を {amount} 付与しました。", ephemeral=True)


# ボット起動時の処理などで一度だけ実行
@bot.event
async def on_ready():
    print(f"{bot.user} が起動しました。コマンド同期完了！")


# トークンの読み込みと起動
if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, 'r') as f: bot.run(f.read().strip())