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

# --- 設定 ---
CSV_FILE = '/storage/emulated/0/Download/JWTG X Project file/files/dino-flock.csv'
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
    
    uids = []
    for item in inventory:
        # ここで item が辞書であることを確認しながら取得
        if isinstance(item, dict):
            uids.append(item.get('uid', 0))
        # もし item が数値や文字列ならそのまま入れる（データ不整合対策）
        elif isinstance(item, int):
            uids.append(item)
            
    return max(uids) + 1 if uids else 1

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
                "hybrid": int(row['hybrid(0/1)']),
                "s_dna_type": row['s_dna_type'],
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
    packs = load_packs()
    if pack_type not in packs: return None
    pack_config = packs[pack_type]

    drop_rate = pack_config.get("dino_drop_rate", 1.0)
    is_dino_hit = random.random() < drop_rate
    
    selected_id = None
    new_uid = None

    if is_dino_hit:
        tree = {}
        for d_id, d in dino_book.items():
            r = d['rarity'].lower().strip() # stripを追加して安全に
            t = str(d['type'])
            w = str(d['battle_in_the_water'])
            h = str(d['hybrid'])
        
            # ✅ ここを for の中にしっかり入れます
            if r not in tree: tree[r] = {}
            if t not in tree[r]: tree[r][t] = {}
            if w not in tree[r][t]: tree[r][t][w] = {}
            if h not in tree[r][t][w]: tree[r][t][w][h] = []
            
            tree[r][t][w][h].append(d_id)

        # 抽選ロジック
        if "fixed_ids" in pack_config:
            selected_id = random.choice(pack_config["fixed_ids"])
        else:
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
                                score = (r_w.get(r, 1) * e_w.get(t, 1) * w_w.get(w, 1) * h_w.get(h, 1))
                                weights.append(score)

            if not combos or sum(weights) == 0:
                # VIP確定パックならここに来ないはずですが、念のため
                selected_id = random.choice(list(dino_book.keys()))
            else:
                chosen = random.choices(combos, weights=weights, k=1)[0]
                selected_id = random.choice(tree[chosen[0]][chosen[1]][chosen[2]][chosen[3]])

    
    # インベントリに追加
    new_uid = get_next_uid(u)
    new_dino = {
        "uid": new_uid,
        "id": selected_id,
        "lv": 1,
        "exp": 0,
        "get_date": datetime.now().strftime("%Y-%m-%d")
    }
    u['inventory'].append(new_dino)
    
    # 2. 通貨の抽選 (JSONの範囲からランダムに決定)
    dna = random.randint(pack_config['dna_range'][0], pack_config['dna_range'][1])
    coin = random.randint(pack_config['coin_range'][0], pack_config['coin_range'][1])
    cash = random.randint(pack_config['cash_range'][0], pack_config['cash_range'][1])
    rp = pack_config['rp_amount']
    
    u['dna'] += dna
    u['coin'] += coin
    u['cash'] += coin
    u['rp'] = u.get('rp', 0) + rp
    
    return {
        "pack_display_name": pack_config['name'],
        "selected_id": selected_id,  # ← ここが重要！
        "dino_name": dino_book[selected_id]['name'],
        "dna": dna,
        "coin": coin,
        "cash": cash,
        "rp": rp,
        "uid": new_uid
    }
    
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
        self.missions = missions
        self.page = 0
        self.per_page = 20 # 1ページあたりの件数

    def make_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        current_list = self.missions[start:end]
        
        embed = discord.Embed(
            title="📅 開催中のイベント一覧",
            description=f"IDを指定して `/event id` で挑戦できます。\n(全 {len(self.missions)} 件)",
            color=0x00ffff
        )
        
        for m in current_list:
            # 報酬の簡易表示
            rew = m.get('reward', {})
            reward_brief = " ".join([f"{EMOJI.get(k,'')}{v}" for k,v in rew.items()])
            embed.add_field(
                name=f"ID: {m['id']} | {m['name']}",
                value=f"🎁 {reward_brief or '報酬なし'}",
                inline=False
            )
            
        embed.set_footer(text=f"Page {self.page + 1} / {(len(self.missions)-1)//self.per_page + 1}")
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

def get_user(user_id, all_users):
    uid = str(user_id)
    if uid not in all_users:
        all_users[uid] = {
            "coin": 15000, "cash": 1000, "food": 4500, "dna": 5000, "rp": 10000, "amber": 0, "medal": 0,
            "inventory": [], "last_free_pack": "2000-01-01 00:00:00","win_count": 0,  
            "last_factory_claim": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            
        }
    if "last_factory_claim" not in all_users[uid]:
        all_users[uid]["last_factory_claim"] = "2000-01-01 00:00:00"
    if "win_count" not in all_users[uid]:
        all_users[uid]["win_count"] = 0
    if "medal" not in all_users[uid]:
        all_users[uid]["medal"] = 0
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
    weights = {"common": 1, "rare": 2, "superrare": 3, "legend": 4, "tournament": 8, "star": 8, "vip": 8, "superstar": 8}
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
        r_str = ""
        if 'coin' in r: r_str += f"🪙 {r['coin']:,} "
        if 'dna' in r: r_str += f"🧬 {r['dna']:,} "
        if 'cash' in r: r_str += f"💵 {r['cash']:,} "
        
        sdna = m.get('S-DNA', {})
        if sdna:
            for s_id, s_amt in sdna.items():
                r_str += f"\n🧪 S-DNA(ID:{s_id}): {s_amt}"
        
        embed.add_field(name="🎁 報酬", value=r_str if r_str else "なし", inline=False)

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
        
        # 1. 最新の全ユーザーデータを読み込む
        users = load_users()
        user_id = str(interaction.user.id)
        u = get_user(user_id, users) # ファイルから読み込んだ最新のデータ
        
        # 2. 報酬を加算
        for key, amount in rew.items():
            if key == "pack":
                # パックは専用関数で処理（内部で保存まで行う場合が多い）
                give_pack(user_id, users, amount)
                log_parts.append(f"📦 {amount}")
            elif key in EMOJI:
                # get(key, 0) を使うことで、キーがなくてもエラーを防ぐ
                u[key] = u.get(key, 0) + amount
                log_parts.append(f"{EMOJI[key]}{amount}")

        # S-DNAの加算
        if sdna_rew:
            if "sdna" not in u: u["sdna"] = {}
            for s_id, s_amt in sdna_rew.items():
                u["sdna"][str(s_id)] = u["sdna"].get(str(s_id), 0) + s_amt
                log_parts.append(f"🧪(ID:{s_id}){s_amt}")

        # 3. 【重要】ファイルに保存する
        save_users(users)
        
        # クラス内の self.u も最新状態に更新（表示用）
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
                # ここを d にする
                d = dino_book[str(d_item['id'])]
                
                # 下の参照もすべて d に合わせる
                hp = get_current_stat(d['hp'], d_item['lv'])
                team.append({
                    "name": d['name'], 
                    "type": d['type'], 
                    "hp": hp, 
                    "max_hp": hp,
                    "atk": get_current_stat(d['atk'], d_item['lv']), 
                    "is_dead": False
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
            
            embed.add_field(
                name=f"{user.display_name} {lives}",
                value=f"{status}\n**{curr['name']}**\n{hp_bar(curr['hp'], curr['max_hp'])}\nHP: {curr['hp']}/{curr['max_hp']}\nAP: **{self.ap[user.id]}**",
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
        limit = current_ap if self.step == "ATK" else (current_ap - self.selected_atk)
        label_prefix = "攻撃" if self.step == "ATK" else "防御"
        style = discord.ButtonStyle.primary if self.step == "ATK" else discord.ButtonStyle.danger

        for i in range(limit + 1):
            btn = Button(label=f"{label_prefix}:{i}", style=style, custom_id=f"ap_{i}")
            btn.callback = self.ap_callback
            self.add_item(btn)

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
        
        # --- 相性計算 (ELEMENT_CHART) ---
        elem_mult = ELEMENT_CHART.get(a['type'], {}).get(d['type'], 1.0)
        
        # 残りAPに応じたダメージ倍率
        rem_ap = max(0, p_atk - p_def)
        # AP_MULTSの範囲外エラーを防ぐ
        rem_mult = AP_MULTS[min(rem_ap, len(AP_MULTS)-1)]
        
        # ダメージ計算
        p_final = int(a['atk'] * rem_mult * elem_mult)
        d['hp'] -= p_final
        
        attacker_name = self.p1.display_name if attacker_id == self.p1.id else self.p2.display_name
        self.log = (
            f"📢 ターン結果発表！\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔥 {attacker_name}の攻撃： {p_atk} AP\n"
            f"🛡️ 相手の防御： {p_def} AP\n"
            f"➡️ 差し引き {rem_ap} AP 分のダメージ！\n"
            f"💥 {d['name']} に {p_final} ダメージ！"
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
        
        # 3. ターンオーナーを交代
        self.turn_owner = defender_id 
        self.turn_count += 1

        # 4. 次の手番の人の回復量を決定
        if self.turn_count == 2:
            actual_recovery = 1 # 後攻の初回
        else:
            actual_recovery = reg_recovery
            
        # 5. AP回復と状態リセット
        self.ap[self.turn_owner] = min(8, self.ap[self.turn_owner] + actual_recovery)
        self.step = "ATK"
        self.selected_atk = 0
        self.create_buttons()

        # 6. 画面更新 (try/except のラインを完璧に揃える)
        try:
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
        except discord.errors.InteractionResponded:
            await interaction.edit_original_response(embed=self.make_embed(), view=self)
        except Exception as e:
            print(f"Update Error: {e}")

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

@bot.tree.command(name="wallet", description="資産状況を確認します")
async def wallet(interaction: discord.Interaction):
    users = load_users()
    u = get_user(interaction.user.id, users)
    
    embed = discord.Embed(title=f"🦖 {interaction.user.display_name} の資産", color=0x2ecc71)
    
    # メイン通貨
    embed.add_field(
        name="基本通貨・素材", 
        value=f"{EMOJI['coin']} {u['coin']:,} | {EMOJI['cash']} {u['cash']:,}\n"
              f"{EMOJI['food']} {u['food']:,} | {EMOJI['dna']} {u['dna']:,}", 
        inline=False
    )
    
    # 特殊ポイント（RP・アンバー）
    embed.add_field(
        name="特殊ポイント", 
        value=f"{EMOJI['rp']} **{u.get('rp', 0):,} RP**\n"
              f"{EMOJI['amber']} **{u.get('amber', 0):,} アンバー**", 
        inline=False
    )
    embed.add_field(name="🎖️ メダル", value=f"{u.get('medal', 0)} 枚", inline=True)
    
    await interaction.response.send_message(embed=embed)

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


@bot.tree.command(name="inv", description="所持恐竜の一覧または詳細を表示します")
async def inventory(interaction: discord.Interaction, uid: int = None):
    users = load_users()
    u = get_user(interaction.user.id, users)
    
    # インベントリの存在確認を安全に
    inv = u.get('inventory', [])
    if not inv:
        await interaction.response.send_message("恐竜がいません。", ephemeral=True)
        return
    
    if uid:
        d_item = next((i for i in inv if i['uid'] == uid), None)
        if not d_item:
            await interaction.response.send_message("見つかりません。", ephemeral=True)
            return
            
        # IDを文字列に変換して安全に取得
        d = dino_book.get(str(d_item['id']))
        if not d:
            await interaction.response.send_message(f"エラー: 図鑑にID {d_item['id']} が見つかりません。", ephemeral=True)
            return

        hp = get_current_stat(d['hp'], d_item['lv'])
        atk = get_current_stat(d['atk'], d_item['lv'])
        
        embed = discord.Embed(title=f"#{uid} {d['name']}", color=0x1abc9c)
        embed.add_field(
            name=f"Lv.{d_item['lv']} ステータス", 
            value=f"❤️ HP: {hp}\n⚔️ ATK: {atk}\n属性: {EMOJI.get(f'type_{d.get('type')}', '❓')}"
        )
        await interaction.response.send_message(embed=embed)
    
    else:
        lines = []
        for i in reversed(inv):
            # dino_bookからデータを安全に取得 (キーをstrに変換)
            d_base = dino_book.get(str(i['id']))
            
            if d_base:
                # 既存の表記スタイルを維持
                type_emoji = EMOJI.get(f"type_{d_base.get('type')}", "❓")
                name = d_base['name']
            else:
                # データが見つからない場合のフォールバック
                type_emoji = "⚠️"
                name = f"不明な恐竜 (ID:{i['id']})"
            
            lines.append(f"**#{i['uid']}** | {type_emoji} {name} (Lv.{i['lv']})")

        # 20件ごとに制限して表示
        embed = discord.Embed(title="🦖 コレクション", description="\n".join(lines[:50]), color=0x1abc9c)
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="dino", description="名前またはIDで恐竜のステータスと販売価格を表示します")
@app_commands.describe(query="検索したい恐竜の名前またはID")
async def dino_info(interaction: discord.Interaction, query: str):
    found_dino = None
    found_id = None

    # 1. ID検索
    if query in dino_book:
        found_id = query
        found_dino = dino_book[query]
    # 2. 名前検索
    else:
        for d_id, d_data in dino_book.items():
            if query.lower() in d_data['name'].lower():
                found_id = d_id
                found_dino = d_data
                dino_id = d_id
                break 

    if not found_dino:
        await interaction.response.send_message(f"❌ 「{query}」に一致する恐竜は見つかりませんでした。", ephemeral=True)
        return

    # 属性・レアリティ設定
    rarity = found_dino['rarity'].lower()
    t_type = found_dino.get('type', "0")
    emoji = EMOJI.get(f"type_{t_type}", "❓")
    color_map = {"common": 0x95a5a6, "rare": 0x2ecc71, "superrare": 0x9b59b6, "legend": 0xf1c40f, "tournament": 0xe74c3c}
    embed_color = color_map.get(rarity, 0x3498db)

    # --- 価格設定 ( /buy コマンドと共通 ) ---
    if query in dino_book:
        dna_cost = dino_book[query]['buy_dna']
    prices = {
        "common": {"dna": 500, "amber": 5},
        "rare": {"dna": 1500, "amber": 15},
        "superrare": {"dna": 3000, "amber": 30},
        "legend": {"dna": 8000, "amber": 80},
        "tournament": {"dna": 20000, "amber": 200}
    }
    cost = prices.get(rarity, prices["common"])

    embed = discord.Embed(title=f"🦖 図鑑データ: {found_dino['name']}", color=embed_color)
    
    # 基本情報に価格を追加
    info_text = (
        f"**ID:** `{found_id}`\n"
        f"**属性:** {emoji} (Type {t_type})\n"
        f"**レアリティ:** {rarity.upper()}\n"
        f"**販売価格:** {EMOJI['dna']} `{dna_cost}`:, / {EMOJI['amber']} `{cost['amber']:,}`"
    )
    embed.add_field(name="基本情報", value=info_text, inline=False)

    # 各レベルのステータス計算
    levels = [1, 10, 20, 30, 40]
    stat_text = "```md\n| Lv | HP    | ATK  |\n|----|-------|------|\n"
    for lv in levels:
        curr_hp = get_current_stat(found_dino['hp'], lv)
        curr_atk = get_current_stat(found_dino['atk'], lv)
        stat_text += f"| {lv:2} | {curr_hp:5} | {curr_atk:4} |\n"
    stat_text += "```"

    embed.add_field(name="📈 成長ステータス", value=stat_text, inline=False)
    
    # 相性ヒント
    strong_to = [k for k, v in ELEMENT_CHART.get(t_type, {}).items() if v > 1.0]
    weak_to = [k for k, v in ELEMENT_CHART.items() if v.get(t_type, 1.0) > 1.0]
    hint = ""
    if strong_to: hint += f"✅ 有利: {', '.join([EMOJI.get(f'type_{t}', t) for t in strong_to])}\n"
    if weak_to: hint += f"⚠️ 不利: {', '.join([EMOJI.get(f'type_{t}', t) for t in weak_to])}"
    
    if hint:
        embed.add_field(name="⚔️ 相性メモ", value=hint, inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="feed", description="エサをあげます（Lv10で停止）")
async def feed(interaction: discord.Interaction, uid: int, amount: int):
    users = load_users(); u = get_user(interaction.user.id, users)
    dino = next((i for i in u['inventory'] if i['uid'] == uid), None)
    if not dino or dino['lv'] % 10 == 0: await interaction.response.send_message("❌ 不可または進化が必要です。", ephemeral=True); return
    actual = 0
    for _ in range(amount):
        cost = dino['lv'] * 100
        if u['food'] >= cost:
            u['food'] -= cost; dino['lv'] += 1; actual += 1
            if dino['lv'] % 10 == 0: break
        else: break
    save_users(users)
    await interaction.response.send_message(f"🍖 {actual}回給餌完了 (Lv.{dino['lv']})")

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
        await interaction.response.send_message("❌ パックの生成に失敗しました。設定を確認してください。", ephemeral=True)
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
    embed.add_field(
        name=f"#{result['uid']} {dino['name']} (Lv.1)", 
        value=f"{type_emoji} レアリティ: **{dino['rarity']}**\n❤️ HP: {hp} | ⚔️ ATK: {atk}", 
        inline=False
    )
    
    # 獲得報酬の表示
    reward_text = f"{EMOJI['coin']} {result['coin']} | {EMOJI['dna']} {result['dna']} | {EMOJI['rp']} {result['rp']}"
    embed.add_field(name="🎁 獲得ボーナス", value=reward_text, inline=False)
    
    if pack_type == "gold":
        embed.set_footer(text=f"残り所持RP: {u['rp']:,}")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="buy", description="恐竜をDNAまたはアンバーで購入します")
@app_commands.describe(
    identifier="恐竜のIDまたは名前",
    currency="支払いに使用する通貨を選択してください"
)
@app_commands.choices(currency=[
    app_commands.Choice(name="DNA", value="dna"),
    app_commands.Choice(name="アンバー", value="amber")
])
async def buy(interaction: discord.Interaction, identifier: str, currency: str):
    users = load_users()
    u = get_user(interaction.user.id, users)
    
    # --- アンバーのレアリティ別価格設定 ---
    AMBER_PRICES = {
        "common": 500,
        "rare": 1500,
        "super_rare": 3500,
        "legendary": 8000,
        "superstar": 15000,
        "tournament": 25000
    }

    # 1. 恐竜の検索
    target_dino = None
    dino_id_key = None # 実際のIDを保持する変数

    # ID入力（数字）の場合
    if identifier.isdigit():
        if identifier in dino_book:
            target_dino = dino_book[identifier]
            dino_id_key = identifier
    # 名前入力の場合
    else:
        for d_id, d_data in dino_book.items():
            if d_data.get('name') == identifier:
                target_dino = d_data
                dino_id_key = d_id
                break
    
    if not target_dino:
        await interaction.response.send_message(f"❌ 恐竜 '{identifier}' が見つかりませんでした。", ephemeral=True)
        return

    # 2. 価格の決定 (KeyError対策として .get() を使用)
    rarity_raw = target_dino.get('rarity', 'common').lower().strip().replace(" ", "_")
    
    if currency == "amber":
        price = AMBER_PRICES.get(rarity_raw, 500) # 見つからない場合は500
        currency_display = "アンバー"
    else:
        # DNA価格の取得。'buy_dna' がなければ 0
        dna_val = target_dino.get('buy_dna', '0')
        price = int(dna_val) if str(dna_val).isdigit() else 0
        currency_display = "DNA"

    # 3. 所持金チェック
    user_balance = u.get(currency, 0)
    if user_balance < price:
        await interaction.response.send_message(
            f"❌ {currency_display}が足りません。\n必要: {price} / 所持: {user_balance}", 
            ephemeral=True
        )
        return

    # 4. 支払いと追加処理
    u[currency] -= price
    
    # ユーザーのインベントリ用データ作成
    new_dino = {
        "uid": get_next_uid(u),
        "id": int(dino_id_key), # 検索時に確定したIDを使用
        "lv": 1
    }
    
    if 'inventory' not in u:
        u['inventory'] = []
    u['inventory'].append(new_dino)
    
    save_users(users)
    
    # 5. 結果表示
    embed = discord.Embed(
        title="🛒 購入完了",
        description=f"**{target_dino.get('name', '不明')}** を手に入れました！",
        color=discord.Color.gold() if currency == "amber" else discord.Color.blue()
    )
    embed.add_field(name="支払価格", value=f"{price} {currency_display}", inline=True)
    embed.add_field(name="残り残高", value=f"{u[currency]} {currency_display}", inline=True)
    embed.set_footer(text=f"Rarity: {rarity_raw.upper()} | ID: {dino_id_key}")

    await interaction.response.send_message(embed=embed)


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

    save_users(users)
    await interaction.response.send_message(f"🛠️ {target.display_name} へ {id_or_item} を {amount} 付与しました。", ephemeral=True)


@bot.event
async def on_ready():
    load_csv()
    print(f'Logged in as {bot.user}')

# トークンの読み込みと起動
if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, 'r') as f: bot.run(f.read().strip())