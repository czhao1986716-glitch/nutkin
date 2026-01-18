import requests
import json
import os
import sys
import io
import datetime
from datetime import timedelta, timezone

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ================= ⚙️ 配置区 =================
# 1. 核心数据源 (BestInSlot V2 - 速度最快)
HOLDERS_URL = "https://v2api.bestinslot.xyz/brc2.0/holders?tick=nutkin"

# 2. 辅助数据源 (BRC20 Build - 用于查历史)
EXPLORER_API = "https://explorer.brc20.build/api/v2"
TOKEN_CONTRACT = "0x81f0eF688b8DCaD3f3dDAba69AD529a99f03a1b7"
PROJECT_WALLET = "0xa07764097a4da7f3b61a562ca1f8e6779494748c"

# BIS SWAP 和 BIS AMM 目标地址
BIS_SWAP_ADDRESS = "0x62879BB3dD949c4CF06f71BF7c281DcF24D163e7"
# BIS AMM: 流动性池子地址 (持有约 28M NUTKIN 代币)
BIS_AMM_ADDRESS = "0x5463191b2705596b89e000fdcd60206daa2df8ff"

# 3. 代币总量 (用于计算占比)
TOTAL_SUPPLY = 999703067  # 如果 nutkin 有不同的总量，需要修改这里

# 4. 文件名 (保持您当前的设置)
DB_FILE = "nutkin_light_db.json"
HTML_FILE = "nutkin_monitor_v35_plus.html"

# 5. 备注名单
WATCHLIST = {
    "0xa07764097a4da7f3b61a562ca1f8e6779494748c": "🥇 榜一 (项目方)",
    "0x899cdf7bf5cf1c5a1b3c9afab2faf55482b97662": "🥈 榜二 (池子)",
    "0xbacb6e7774bb84dfcc0f5ad89c51782eade91f7e": "大宇钱包",
    "0xd3a5b717ab78f6075def527f070b9ee0dc662828": "BIS",
    "0x63160c1f9f071b57b6860bd8de66c7cb87295014": "CATSWAP",
    "0xf97ed5736eb42b0056b030e56349b3f48fce1898": "岩姐线上伙伴--8sats",
    "0xb7f1b7b18c070f998320ca75d1f1e1e33d7ab421": "岩姐团队长吕小金&J K--8.5sats",
    "0xb9d545610680be42046a75d51b199b107cb51c6c": "岩姐伙伴陈老师9.3sats",
    "0x4508cd33faa924f0104071a9c20d8f558d3d3598": "卢总钱包地址1",
    "0x5f0e77e6acef04eae1aab71f28ef71159fcb2f12": "卢总钱包地址2",
    "0x440264da99dd5502d815124951c3e03affe7a284": "温州张余寿",
    "0x757e9b4bd0f30807510e96058a64d65006c5aef5": "王金龙地址",
    "0x56153c064c9fee25bc79ad8ca6bfac7212ab4c5c": "疑似项目方",
    "0xa6ce3189f420f0fd9e90760ad1e80ce1489e3b5e": "岩姐地址",
    "0x1f40dd141d78ad7abb84b92a1bc112b0332f1ca9": "阳光总地址-",
    "0x971a72167acb3e0dfa6bb5092ad3361d02a1ba5a": "项目方相关3",
    "0x3263b632d5316a187f919d58750df082ebac9568": "项目方相关4",
    "0x6f69b0f14c37c90e7cce8c019a09ad8e1f2f66a9": "阳光总地址",
    "0xf470ccb11c23250ebae4bc632ffe93961850a63e": "王金龙线上营销",
    "0xa648ab10aa4b6911e80b58fef5f402bed96a93bc": "王金龙地址2",
    "0x7eac9d9f054d12aa6e2d499e181f5932ddc41a8c": "王金龙地址3",
    "0x4ba15fd51f5ab0c31233893df6cd08283b580a0a": "王金龙地址4",
    "0x881a670564867d6af6f8b9a47b9b14186d4523b3": "王金龙地址5",
    "0xe513a6fb5fed9fe4d5abbc7f1fe64cec568fba18": "王金龙地址6",
    "0x758f29be1e23ba21a5b69c1024db4e4b33e9fc50": "王金龙地址7",
    "0x02e4b4cb9c796fa67b27b40e7a004a9180a4e4e0": "王金龙地址8",
    "0x170e7baf244a95989d059b5a4af7a27a4e712616": "105nft",
    "0xa1763467317d8f18955c06e8be2d1909c6b611e2": "105nft",
    "0xd00a593da9d9f5769b4bcbb657d3559960165299": "101nft",
    "0x8893002cf5978378db25f4648ab295ee0b0e54c5": "卢总钱包地址3",
    "0xd63c38f43f7ac86ed7332539f6d5a2b1e8c4b9bf": "阳光总相关1",
    "0xe4610c83f441e623dcc4c40d0181f22b70eefa22": "阳光总相关2",
    "0xd0dd914afa5e9e5c7f0e98142a7bf5c80a2318cc": "阳光总相关3",
    "0x5463191b2705596b89e000fdcd60206daa2df8ff": "bisamm",
    "0x250b25bd16d28b6a311918895f24ed32b9affc06": "毛毛姐"
}
# ============================================

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

# === 核心功能 1: 深度溯源 MINT 名单 ===
def fetch_mint_list_deep():
    print(f"🕵️‍♂️ [1/3] 正在全量扫描项目方历史，寻找 MINT 地址...")
    print("⏳ 正在翻阅链上账本 (为了不漏掉早期地址，这需要一点时间)...")

    minters = set()
    url = f"{EXPLORER_API}/addresses/{PROJECT_WALLET}/token-transfers"
    params = {"token": TOKEN_CONTRACT, "type": "ERC-20", "limit": 50}
    headers = {"User-Agent": "Mozilla/5.0"}

    total_scanned = 0

    while True:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code != 200: break

            data = resp.json()
            items = data.get('items', [])
            if not items: break

            total_scanned += len(items)
            print(f"   已扫描 {total_scanned} 笔交易...", end="\r")

            for item in items:
                # 校验合约
                if item.get('token', {}).get('address', '').lower() != TOKEN_CONTRACT.lower(): continue

                from_addr = item.get('from', {}).get('hash', '').lower()
                to_addr = item.get('to', {}).get('hash', '').lower()

                # 项目方发出去的 -> 接收者就是 Minter
                if from_addr == PROJECT_WALLET.lower():
                    minters.add(to_addr)

            # 翻页逻辑
            if 'next_page_params' in data and data['next_page_params']:
                params.update(data['next_page_params'])
            else:
                break
        except: break

    print(f"\n✅ MINT 名单建立完毕！共发现 {len(minters)} 个原始地址。")
    return minters

# === 核心功能 2: 智能验真 ===
def check_is_truly_new(address):
    url = f"{EXPLORER_API}/addresses/{address}/token-transfers"
    params = {"token": TOKEN_CONTRACT, "type": "ERC-20", "limit": 10}
    try:
        resp = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if resp.status_code == 200:
            items = resp.json().get('items', [])
            if not items: return True # 无记录，肯定是新人

            # 检查是否有早于24小时的交易
            now = datetime.datetime.now(timezone.utc)
            for item in items:
                ts_str = item.get('timestamp')
                try:
                    dt = datetime.datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    if (now - dt).total_seconds() > 86400: return False # 是老手回归
                except: pass
    except: pass
    return True

# === 核心功能 3: 获取目标地址的所有转账记录 ===
def get_transfers(target_address, direction="incoming", use_token_filter=True):
    """
    获取目标地址的转账记录
    参数：
        target_address: 目标地址（如 bis swap 或 bis amm）
        direction: "incoming" 接收记录, "outgoing" 发送记录
        use_token_filter: 是否只查询 NUTKIN 代币（True）还是所有代币（False）
    返回：
        字典：{地址: 总数量}
    """
    url = f"{EXPLORER_API}/addresses/{target_address}/token-transfers"
    params = {"type": "ERC-20", "limit": 100}
    # 如果启用代币过滤，添加 token 参数
    if use_token_filter:
        params["token"] = TOKEN_CONTRACT
    headers = {"User-Agent": "Mozilla/5.0"}

    transfer_data = {}  # {address: total_amount}

    print(f"   📡 正在查询 {direction}: {url}")
    print(f"   🔑 目标地址: {target_address}")

    try:
        page_count = 0
        while True:
            page_count += 1
            resp = requests.get(url, params=params, headers=headers, timeout=10)

            if resp.status_code != 200:
                print(f"   ⚠️ 请求失败 (第{page_count}页): 状态码 {resp.status_code}")
                break

            data = resp.json()
            items = data.get('items', [])

            if not items:
                print(f"   📄 第{page_count}页: 没有更多数据")
                break

            print(f"   📄 第{page_count}页: 获取到 {len(items)} 条记录")

            # 调试: 显示前3条记录
            if page_count == 1:
                print(f"   🔍 前3条记录示例:")
                for i, item in enumerate(items[:3]):
                    from_addr = item.get('from', {}).get('hash', '')
                    to_addr = item.get('to', {}).get('hash', '')
                    token_addr = item.get('token', {}).get('address', '')
                    amount = float(item.get('value', 0) or 0)
                    decimals = int(item.get('token', {}).get('decimals', 18))
                    actual_amount = amount / (10 ** decimals)
                    print(f"      {i+1}. 发送方: {from_addr[:20]}... → 接收方: {to_addr[:20]}... | 金额: {actual_amount:.2f} | 合约: {token_addr[:20]}...")

            for item in items:
                # 获取代币地址
                token_addr = item.get('token', {}).get('address', '')

                # 如果启用了代币过滤，校验合约地址
                if use_token_filter:
                    if token_addr.lower() != TOKEN_CONTRACT.lower():
                        continue

                # 获取发送方和接收方地址
                from_addr = item.get('from', {}).get('hash', '').lower()
                to_addr = item.get('to', {}).get('hash', '').lower()

                # 忽略零地址和空地址
                if not from_addr or from_addr == '0x0000000000000000000000000000000000000000':
                    continue

                # 计算金额 - API 返回的 value 在 total 对象下
                total_data = item.get('total', {})
                amount = float(total_data.get('value', 0) or 0)
                decimals = int(total_data.get('decimals', 18))
                actual_amount = amount / (10 ** decimals)

                # 根据方向统计
                if direction == "incoming":
                    # 统计发送到目标地址的记录
                    if to_addr == target_address.lower():
                        counterparty = from_addr
                    else:
                        continue
                else:  # outgoing
                    # 统计从目标地址发送出去的记录
                    if from_addr == target_address.lower():
                        counterparty = to_addr
                    else:
                        continue

                # 累加到字典
                if counterparty not in transfer_data:
                    transfer_data[counterparty] = 0.0
                transfer_data[counterparty] += actual_amount

            # 翻页逻辑
            if 'next_page_params' in data and data['next_page_params']:
                params.update(data['next_page_params'])
            else:
                break

        # 统计总金额
        total_amount = sum(transfer_data.values())
        direction_name = "接收" if direction == "incoming" else "发送"
        print(f"   ✅ {target_address}: 找到 {len(transfer_data)} 个{direction_name}地址, 总计 {total_amount:.2f} 代币")

        # 显示前5个最大的
        if transfer_data:
            sorted_parties = sorted(transfer_data.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"   📊 前5大{direction_name}方:")
            for addr, amount in sorted_parties:
                print(f"      {addr[:20]}... → {amount:.2f} 代币")

    except Exception as e:
        print(f"   ⚠️ 获取 {target_address} {direction}记录失败: {e}")
        import traceback
        traceback.print_exc()

    return transfer_data

# === 新增：直接从 BestInSlot 获取流动性数据 ===
def get_liquidity_providers_from_bis():
    """
    从 BestInSlot 获取流动性提供者数据
    由于没有专门的 API，我们尝试不同的方法
    """
    print(f"   💾 尝试获取 BIS 流动性数据...")

    # 方法1: 尝试通过交易历史获取
    # 注意：这个方法可能不会返回所有数据，因为添加流动性不是标准的 ERC-20 转账
    liquidity_data = {}

    # 这里可以添加其他获取流动性数据的方法
    # 例如：通过解析 bestinslot 页面的 JavaScript 变量
    # 或者通过其他 API 端点

    return liquidity_data

# === 保存 BIS 数据到文件 ===
def save_bis_data(bis_swap_data, bis_amm_data, lp_data=None):
    """将 BIS SWAP 和 BIS AMM 的数据保存到文件，方便调试"""
    bis_data = {
        "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
        "bis_swap": {
            "address": BIS_SWAP_ADDRESS,
            "incoming": {
                "total_senders": len(bis_swap_data.get("incoming", {})),
                "total_amount": sum(bis_swap_data.get("incoming", {}).values()),
                "top_senders": [
                    {"address": addr, "amount": amount}
                    for addr, amount in sorted(bis_swap_data.get("incoming", {}).items(), key=lambda x: x[1], reverse=True)[:20]
                ]
            },
            "outgoing": {
                "total_receivers": len(bis_swap_data.get("outgoing", {})),
                "total_amount": sum(bis_swap_data.get("outgoing", {}).values()),
                "top_receivers": [
                    {"address": addr, "amount": amount}
                    for addr, amount in sorted(bis_swap_data.get("outgoing", {}).items(), key=lambda x: x[1], reverse=True)[:20]
                ]
            }
        },
        "bis_amm": {
            "address": BIS_AMM_ADDRESS,
            "incoming": {
                "total_senders": len(bis_amm_data.get("incoming", {})),
                "total_amount": sum(bis_amm_data.get("incoming", {}).values()),
                "top_senders": [
                    {"address": addr, "amount": amount}
                    for addr, amount in sorted(bis_amm_data.get("incoming", {}).items(), key=lambda x: x[1], reverse=True)[:20]
                ]
            },
            "outgoing": {
                "total_receivers": len(bis_amm_data.get("outgoing", {})),
                "total_amount": sum(bis_amm_data.get("outgoing", {}).values()),
                "top_receivers": [
                    {"address": addr, "amount": amount}
                    for addr, amount in sorted(bis_amm_data.get("outgoing", {}).items(), key=lambda x: x[1], reverse=True)[:20]
                ]
            }
        }
    }

    # 添加流动性提供者数据
    if lp_data:
        bis_data["liquidity_providers"] = {
            "total_count": lp_data.get("total_lp_count", 0),
            "top_providers": [
                {
                    "address": addr,
                    "net_inflow": data['net'],
                    "total_in": data['in'],
                    "total_out": data['out']
                }
                for addr, data in list(lp_data.get("lp_providers", {}).items())[:20]
            ]
        }

    with open('bis_data_debug.json', 'w', encoding='utf-8') as f:
        json.dump(bis_data, f, indent=2, ensure_ascii=False)

    print(f"   💾 BIS 数据已保存到 bis_data_debug.json")
    print(f"   📊 BIS SWAP: 转入 {len(bis_swap_data.get('incoming', {}))} 个, 转出 {len(bis_swap_data.get('outgoing', {}))} 个")
    print(f"   📊 BIS AMM: 转入 {len(bis_amm_data.get('incoming', {}))} 个, 转出 {len(bis_amm_data.get('outgoing', {}))} 个")

# === 主数据抓取 ===
def fetch_data(minters_set, db_old_keys):
    print(f"🚀 [2/3] 正在下载全量持仓榜...")

    # 1. 先获取 BIS SWAP 和 BIS AMM 的所有接收和发送记录
    print(f"📊 正在获取 BIS SWAP 和 BIS AMM 转账记录...")

    # BIS SWAP: 接收记录(用户 deposit)和发送记录(用户 withdraw)
    bis_swap_incoming = get_transfers(BIS_SWAP_ADDRESS, "incoming")  # +
    bis_swap_outgoing = get_transfers(BIS_SWAP_ADDRESS, "outgoing")  # -

    # BIS AMM: 接收记录(添加流动性)和发送记录(移除流动性)
    # 注意：BIS AMM 查询时不使用代币过滤，因为添加流动性可能涉及多个代币
    bis_amm_incoming = get_transfers(BIS_AMM_ADDRESS, "incoming", use_token_filter=False)   # +
    bis_amm_outgoing = get_transfers(BIS_AMM_ADDRESS, "outgoing", use_token_filter=False)    # -

    # === 核心逻辑：追踪用户的流动性操作 ===
    # 实际流程：用户 -> BIS SWAP -> BIS AMM (添加流动性)
    #          BIS AMM -> BIS SWAP -> 用户 (移除流动性)

    # BIS SWAP -> BIS AMM 的转账表示添加流动性（从池子角度看）
    bis_swap_to_amm_in = bis_amm_incoming.get(BIS_SWAP_ADDRESS.lower(), 0)
    # BIS AMM -> BIS SWAP 的转账表示移除流动性
    bis_swap_to_amm_out = bis_amm_outgoing.get(BIS_SWAP_ADDRESS.lower(), 0)

    print(f"\n   💡 BIS SWAP -> BIS AMM 流动性:")
    print(f"      添加流动性: {bis_swap_to_amm_in:,.2f}")
    print(f"      移除流动性: {bis_swap_to_amm_out:,.2f}")
    print(f"      净流入: {bis_swap_to_amm_in - bis_swap_to_amm_out:,.2f}")

    # 创建流动性提供者完整榜单
    # 逻辑：所有转入 NUTKIN 到 BIS SWAP 的地址都是流动性提供者
    # 因为这些代币最终会进入 BIS AMM 池子
    lp_providers = {}

    # 遍历所有转入到 BIS SWAP 的地址
    for addr, amount in bis_swap_incoming.items():
        # 跳过 BIS AMM 地址本身（这是移除流动性回来的代币）
        if addr.lower() == BIS_AMM_ADDRESS.lower():
            continue

        # 获取该地址从 BIS SWAP 转出的金额（移除流动性）
        amount_out = bis_swap_outgoing.get(addr, 0)

        # 计算净流入
        net_inflow = amount - amount_out

        lp_providers[addr.lower()] = {
            'in': amount,
            'out': amount_out,
            'net': net_inflow
        }

    # 按净流入排序
    sorted_lp = sorted(lp_providers.items(), key=lambda x: x[1]['net'], reverse=True)
    print(f"\n   💎 流动性提供者统计: 找到 {len(lp_providers)} 个 LP 地址")
    print(f"   📊 前10大流动性提供者:")
    for i, (addr, data) in enumerate(sorted_lp[:10], 1):
        print(f"      {i:2d}. {addr[:20]}... → 净流入: {data['net']:,.2f} (流入: {data['in']:,.2f}, 流出: {data['out']:,.2f})")

    # 保存 BIS 数据到文件（用于调试）
    save_bis_data({
        "incoming": bis_swap_incoming,
        "outgoing": bis_swap_outgoing
    }, {
        "incoming": bis_amm_incoming,
        "outgoing": bis_amm_outgoing
    }, {
        "lp_providers": dict(sorted_lp),
        "total_lp_count": len(lp_providers)
    })

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(HOLDERS_URL, headers=headers, timeout=30)
        if resp.status_code != 200: return []
        items = resp.json().get('items', [])

        holders = []
        candidates_for_check = []

        # 创建当前持有人字典
        current_holders_map = {}

        for item in items:
            ox = item.get('evm_wallet')
            btc = item.get('btc_wallet')
            bal = float(item.get('total_balance') or item.get('evm_withdrawable_balance') or 0)

            if ox:
                key = ox.lower()
                if not btc: btc = "-"

                # 1. 判断 Mint
                is_mint = (key in minters_set)

                # 2. 计算占比
                percent = (bal / TOTAL_SUPPLY) * 100

                # 3. 获取 BIS 转账数据
                bis_swap_in = bis_swap_incoming.get(key, 0)
                bis_swap_out = bis_swap_outgoing.get(key, 0)

                # 注意：用户通过 BIS SWAP 提供/移除流动性
                # 所以用户转入到 BIS SWAP 的 NUTKIN = 他们添加到流动性池的代币
                # BIS AMM 的接收记录里只有 BIS SWAP 地址，没有直接的用户地址
                bis_amm_in = bis_swap_in  # 用户转入到 BIS SWAP = 添加流动性
                bis_amm_out = bis_swap_out  # 用户从 BIS SWAP 转出 = 移除流动性

                # 4. 计算总和：持仓 + BIS AMM 净流入
                # 注意：不要重复计算 bis_swap_net，因为 bis_amm_net 已经包含了
                bis_swap_net = bis_swap_in - bis_swap_out
                bis_amm_net = bis_amm_in - bis_amm_out
                total_balance = bal + bis_amm_net  # 只加 bis_amm_net，避免重复

                # 5. 判断用户类型
                is_potential_new = (key not in db_old_keys) and (len(db_old_keys) > 0)

                # 判断是否是流动性提供者（通过 BIS SWAP 参与了流动性池）
                is_lp = (bis_swap_in > 0 or bis_swap_out > 0)

                # 判断是否是交易者（预留标记，目前所有参与 BIS 的都是 LP）
                is_trader = False

                status = ""
                if is_lp:
                    status = "LP"  # 流动性提供者
                if is_trader:
                    status = "TRADER"  # 交易者
                if is_potential_new and not status:
                    status = "CHECKING"
                    candidates_for_check.append(key)

                holders.append({
                    "rank": len(holders) + 1,
                    "key": key,
                    "btc": btc,
                    "bal": bal,
                    "pct": percent,
                    "is_mint": is_mint,
                    "status": status,
                    "bis_swap_in": bis_swap_in,
                    "bis_swap_out": bis_swap_out,
                    "bis_amm_in": bis_amm_in,
                    "bis_amm_out": bis_amm_out,
                    "total_balance": total_balance  # 新增：总和
                })

                # 记录到当前持有人字典
                current_holders_map[key] = True

        # === 批量验真 ===
        if candidates_for_check:
            print(f"🕵️‍♂️ [3/3] 正在核实 {len(candidates_for_check)} 个新出现的地址...")
            skip_check = len(candidates_for_check) > 50

            count = 0
            cache = {}
            for addr in candidates_for_check:
                count += 1
                if skip_check:
                    res = "NEW"
                else:
                    print(f"   核查中 ({count}/{len(candidates_for_check)})...", end="\r")
                    is_true = check_is_truly_new(addr)
                    res = "NEW" if is_true else "RETURN"

                cache[addr] = res

            for h in holders:
                if h['status'] == "CHECKING":
                    h['status'] = cache.get(h['key'], "NEW")
            print("\n✅ 核实完成。")

        # === 添加已卖完但参与过 BIS 的地址 ===
        print(f"🔍 [额外] 正在查找参与过 BIS 交易但当前持仓为 0 的地址...")

        # 收集所有参与过 BIS SWAP 或 BIS AMM 的地址
        bis_swap_addresses = set(bis_swap_incoming.keys()) | set(bis_swap_outgoing.keys())
        bis_amm_addresses = set(bis_amm_incoming.keys()) | set(bis_amm_outgoing.keys())
        all_bis_addresses = bis_swap_addresses | bis_amm_addresses

        # 过滤出当前持仓为 0 但参与过 BIS 的地址
        sold_out_addresses = []
        for addr in all_bis_addresses:
            # 跳过已经在当前持有人列表中的地址
            if addr.lower() in current_holders_map:
                continue
            # 跳过 BIS SWAP 和 BIS AMM 地址本身
            if addr.lower() in [BIS_SWAP_ADDRESS.lower(), BIS_AMM_ADDRESS.lower()]:
                continue

            # 获取 BIS 数据
            bis_swap_in = bis_swap_incoming.get(addr, 0)
            bis_swap_out = bis_swap_outgoing.get(addr, 0)

            # 注意：用户通过 BIS SWAP 提供/移除流动性
            bis_amm_in = bis_swap_in  # 用户转入到 BIS SWAP = 添加流动性
            bis_amm_out = bis_swap_out  # 用户从 BIS SWAP 转出 = 移除流动性

            # 只添加确实有 BIS 交易的地址
            if bis_swap_in > 0 or bis_swap_out > 0:
                # 计算总和（持仓为 0）
                bis_swap_net = bis_swap_in - bis_swap_out
                bis_amm_net = bis_amm_in - bis_amm_out
                total_balance = bis_amm_net  # 只用 bis_amm_net，避免重复

                # 判断用户类型
                is_lp = (bis_swap_in > 0 or bis_swap_out > 0)
                is_trader = False

                status = "SOLD_OUT"  # 已卖完
                if is_lp:
                    status = "SOLD_OUT_LP"  # 已卖完的流动性提供者
                elif is_trader:
                    status = "SOLD_OUT_TRADER"  # 已卖完的交易者

                sold_out_addresses.append({
                    "rank": 9999,  # 排在最后
                    "key": addr,
                    "btc": "-",  # 没有 BTC 地址信息
                    "bal": 0,  # 当前持仓为 0
                    "pct": 0,
                    "is_mint": False,
                    "status": status,
                    "bis_swap_in": bis_swap_in,
                    "bis_swap_out": bis_swap_out,
                    "bis_amm_in": bis_amm_in,
                    "bis_amm_out": bis_amm_out,
                    "total_balance": total_balance
                })

        print(f"   ✅ 找到 {len(sold_out_addresses)} 个已卖完但参与过 BIS 的地址")

        # 将这些地址添加到持有人列表
        holders.extend(sold_out_addresses)

        return holders
    except Exception as e:
        print(f"❌ 错误: {e}")
        return []

def generate_report(holders, db):
    chart_data = {}

    # === 北京时间修正 (UTC+8) ===
    tz_cn = timezone(timedelta(hours=8))
    today_str = datetime.datetime.now(tz_cn).strftime("%Y-%m-%d")

    table_data = []

    # 创建当前持有人字典
    current_holders = {h['key']: h for h in holders}

    # 处理所有历史地址（包括当前余额为0的）
    all_keys = set(db.keys()) | set(current_holders.keys())

    for key in all_keys:
        # 如果是当前持有人，使用最新数据
        if key in current_holders:
            h = current_holders[key]
        else:
            # 如果不在当前持有人列表，创建一个空记录
            h = {
                'key': key,
                'btc': '-',
                'bal': 0,
                'pct': 0,
                'is_mint': False,
                'status': 'SOLD_OUT',  # 已卖完
                'bis_swap_in': 0,
                'bis_swap_out': 0,
                'bis_amm_in': 0,
                'bis_amm_out': 0,
                'total_balance': 0,
                'rank': 9999
            }

        # 如果没有历史记录，跳过（新地址但余额为0的）
        if key not in db or not db[key]:
            if h['bal'] == 0 and h['total_balance'] == 0:
                continue

        if key not in db: db[key] = []
        history = db[key]

        # 历史记录逻辑 - 使用 total_balance 而不是 bal
        if not history or history[-1]['t'] != today_str:
            if history:
                try:
                    last = datetime.datetime.strptime(history[-1]['t'], "%Y-%m-%d").date()
                    current_date_obj = datetime.datetime.strptime(today_str, "%Y-%m-%d").date()
                    delta = (current_date_obj - last).days
                    if delta > 1:
                        for i in range(1, delta):
                            d = (last + timedelta(days=i)).strftime("%Y-%m-%d")
                            history.append({"t": d, "y": history[-1]['y']})
                except: pass
            # 存储总和（持仓 + BIS SWAP净流入 + BIS AMM净流入）
            history.append({"t": today_str, "y": h['total_balance']})
        else:
            # 更新今天的值
            history[-1]['y'] = h['total_balance']

        if len(history) > 180: history = history[-180:]
        db[key] = history

        # 24H变化 - 基于总和计算
        change = 0
        if len(history) >= 2:
            raw_change = h['total_balance'] - history[-2]['y']
            if abs(raw_change) >= 1: change = raw_change

        chart_data[key] = history

        note = WATCHLIST.get(key, "")
        if h['is_mint'] and key != PROJECT_WALLET.lower():
            note = "🎁 [MINT] " + note

        # 计算BIS净流入
        bis_swap_net = h.get('bis_swap_in', 0) - h.get('bis_swap_out', 0)
        bis_amm_net = h.get('bis_amm_in', 0) - h.get('bis_amm_out', 0)

        table_data.append({
            "rank": h['rank'],
            "key": key,
            "btc": h['btc'],
            "bal": h['bal'],  # 原始持仓
            "pct": h['pct'],
            "change": change,  # 基于 total_balance 的24H变化
            "note": note,
            "status": h['status'],
            "is_new_day": (len(history) == 1),
            "bis_swap_in": h.get('bis_swap_in', 0),
            "bis_swap_out": h.get('bis_swap_out', 0),
            "bis_swap_net": bis_swap_net,  # BIS SWAP净流入，用于排序
            "bis_amm_in": h.get('bis_amm_in', 0),
            "bis_amm_out": h.get('bis_amm_out', 0),
            "bis_amm_net": bis_amm_net,  # BIS AMM净流入，用于排序
            "total_balance": h['total_balance']  # 总和
        })

    # 按总和排序，已卖完的（总和<=0）排在后面
    table_data.sort(key=lambda x: x['total_balance'], reverse=True)

    save_db(db)

    # === HTML 生成 ===
    json_chart = json.dumps(chart_data)
    json_table = json.dumps(table_data)

    # === 北京时间显示 ===
    now = datetime.datetime.now(tz_cn).strftime("%Y-%m-%d %H:%M")

    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8"><title>NUTKIN V35+ 融合版</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body{{background:#121212;color:#ccc;font-family:sans-serif;padding:20px}}
        h1{{text-align:center;color:#00bcd4}} .info{{text-align:center;color:#666}}

        .controls {{text-align:center; margin:20px 0;}}
        input {{background:#333;border:1px solid #555;color:#fff;padding:8px;border-radius:4px;width:300px}}

        table{{width:100%;border-collapse:collapse;background:#1e1e1e;font-size:13px}}
        th,td{{padding:10px;border-bottom:1px solid #333;text-align:left}}
        th{{background:#252525;color:#888;cursor:pointer;user-select:none}}
        th:hover{{color:#fff;background:#333}}

        .addr-0x{{color:#00bcd4;font-family:monospace;display:block}}
        .addr-btc{{color:#666;font-size:11px;font-family:monospace}}
        .up{{color:#f44336}} .down{{color:#4caf50}}

        .mint-tag{{background:#9c27b0;color:#fff;padding:2px 4px;font-size:10px;border-radius:3px;font-weight:bold;margin-right:4px}}
        .new-tag{{background:#f44336;color:#fff;padding:2px 4px;font-size:10px;border-radius:3px;margin-right:4px}}
        .ret-tag{{background:#2196F3;color:#fff;padding:2px 4px;font-size:10px;border-radius:3px;margin-right:4px}}
        .lp-tag{{background:#00e676;color:#000;padding:2px 4px;font-size:10px;border-radius:3px;font-weight:bold;margin-right:4px}}
        .trader-tag{{background:#ff9800;color:#000;padding:2px 4px;font-size:10px;border-radius:3px;font-weight:bold;margin-right:4px}}
        .soldout-tag{{background:#607d8b;color:#fff;padding:2px 4px;font-size:10px;border-radius:3px;margin-right:4px}}
        .soldout-lp-tag{{background:#009688;color:#fff;padding:2px 4px;font-size:10px;border-radius:3px;margin-right:4px}}
        .soldout-trader-tag{{background:#ff5722;color:#fff;padding:2px 4px;font-size:10px;border-radius:3px;margin-right:4px}}
        .rem{{background:#9e9e9e;color:#fff;padding:2px 4px;font-size:10px;border-radius:3px}}

        .btn{{background:#333;border:1px solid #555;color:#fff;cursor:pointer;padding:4px 8px;border-radius:4px}}

        #modal{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:999}}
        .box{{background:#222;margin:5% auto;width:90%;max-width:900px;height:500px;padding:20px;border-radius:8px;position:relative}}
        .close{{position:absolute;top:10px;right:15px;font-size:24px;cursor:pointer;color:#fff}}
    </style></head><body>

    <h1>🐿️ NUTKIN V35+ (终极融合版)</h1>
    <div class="info">总人数: <span id="count">{len(holders)}</span> | 更新: {now} (北京时间)</div>

    <div class="controls">
        <input type="text" id="search" placeholder="🔍 搜索地址 / LP / TRADER / MINT / NEW / 备注..." onkeyup="render()">
    </div>

    <div class="controls" style="margin-top: 15px;">
        <button class="btn" onclick="changePageSize()">📄 每页显示: <span id="pageSizeLabel">100</span></button>
        <span id="pageInfo" style="margin-left: 20px; color: #aaa;"></span>
        <button class="btn" onclick="prevPage()" style="margin-left: 10px;">⬅️ 上一页</button>
        <button class="btn" onclick="nextPage()" style="margin-left: 5px;">➡️ 下一页</button>
    </div>

    <table>
        <thead>
            <tr>
                <th onclick="sort('rank')" style="width:60px;">排名 ⇵</th>
                <th onclick="sort('key')">地址 (0x / btc)</th>
                <th onclick="sort('bal')" style="width:120px;">持仓 ⇵</th>
                <th onclick="sort('bis_swap_net')" style="width:130px;">BIS SWAP ⇵<br><span style="font-size:10px;color:#666">净流入(+/-)</span></th>
                <th onclick="sort('bis_amm_net')" style="width:130px;">BIS AMM ⇵<br><span style="font-size:10px;color:#666">净流入(+/-)</span></th>
                <th onclick="sort('total_balance')" style="width:130px;">总和 ⇵</th>
                <th onclick="sort('pct')" style="width:90px;">占比 % ⇵</th>
                <th onclick="sort('change')" style="width:130px;">24H 变化 ⇵</th>
                <th style="width:60px;">趋势</th>
            </tr>
        </thead>
        <tbody id="tbody"></tbody>
    </table>

    <div id="modal"><div class="box"><span class="close" onclick="document.getElementById('modal').style.display='none'">&times;</span><canvas id="c"></canvas></div></div>

    <script>
    let rawData = {json_table};
    const chartData = {json_chart};
    let sortCol = 'total_balance';  // 默认按总和排序
    let sortDesc = true;

    // 分页配置
    let currentPage = 1;
    let pageSize = 100;
    let filteredAndSortedData = [];  // 缓存过滤和排序后的数据

    function render() {{
        const tbody = document.getElementById('tbody');
        const search = document.getElementById('search').value.toLowerCase();

        // 过滤数据
        filteredAndSortedData = rawData.filter(item =>
            item.key.includes(search) || item.btc.includes(search) || item.note.toLowerCase().includes(search) || item.status.toLowerCase().includes(search)
        );

        document.getElementById('count').innerText = filteredAndSortedData.length;

        // 排序数据（只在排序时执行一次）
        filteredAndSortedData.sort((a, b) => {{
            let valA = a[sortCol];
            let valB = b[sortCol];
            if (typeof valA === 'string') return sortDesc ? valB.localeCompare(valA) : valA.localeCompare(valB);
            return sortDesc ? (valB - valA) : (valA - valB);
        }});

        // 分页
        const totalPages = Math.ceil(filteredAndSortedData.length / pageSize);
        if(currentPage > totalPages) currentPage = Math.max(1, totalPages);
        const startIdx = (currentPage - 1) * pageSize;
        const endIdx = startIdx + pageSize;
        const pageData = filteredAndSortedData.slice(startIdx, endIdx);

        // 更新分页信息
        document.getElementById('pageInfo').innerText = `第 ${{currentPage}} / ${{totalPages || 1}} 页 (共 ${{filteredAndSortedData.length}} 条)`;

        let html = [];
        pageData.forEach(item => {{
            let balStr = item.bal.toLocaleString('en-US', {{maximumFractionDigits: 0}});
            let pctStr = item.pct.toFixed(2) + "%";
            let chgClass = "flat", chgText = "-";
            if(item.change > 0) {{
                chgClass="up";
                chgText = "+" + item.change.toLocaleString('en-US', {{maximumFractionDigits: 0}}) + " ▲";
            }}
            else if(item.change < 0) {{
                chgClass="down";
                chgText = item.change.toLocaleString('en-US', {{maximumFractionDigits: 0}}) + " ▼";
            }}

            // BIS SWAP 净流入 = 转入 - 转出
            let bisSwapNet = item.bis_swap_in - item.bis_swap_out;
            let bisSwapNetStr = "";
            if(bisSwapNet > 0) {{
                bisSwapNetStr = `<span style="color:#4caf50">+${{bisSwapNet.toLocaleString('en-US', {{maximumFractionDigits: 0}})}}</span>`;
            }} else if(bisSwapNet < 0) {{
                bisSwapNetStr = `<span style="color:#f44336">${{bisSwapNet.toLocaleString('en-US', {{maximumFractionDigits: 0}})}}</span>`;
            }} else {{
                bisSwapNetStr = '<span style="color:#666">0</span>';
            }}

            // BIS AMM 净流入 = 转入 - 转出
            let bisAmmNet = item.bis_amm_in - item.bis_amm_out;
            let bisAmmNetStr = "";
            if(bisAmmNet > 0) {{
                bisAmmNetStr = `<span style="color:#4caf50">+${{bisAmmNet.toLocaleString('en-US', {{maximumFractionDigits: 0}})}}</span>`;
            }} else if(bisAmmNet < 0) {{
                bisAmmNetStr = `<span style="color:#f44336">${{bisAmmNet.toLocaleString('en-US', {{maximumFractionDigits: 0}})}}</span>`;
            }} else {{
                bisAmmNetStr = '<span style="color:#666">0</span>';
            }}

            // 总和 = 持仓 + BIS SWAP净额 + BIS AMM净额
            let totalBalanceStr = item.total_balance.toLocaleString('en-US', {{maximumFractionDigits: 0}});

            let tags = "";
            // 已卖完标签
            if(item.status === "SOLD_OUT") tags += "<span class='soldout-tag'>💸 已卖完</span>";
            // 已卖完的流动性提供者标签
            if(item.status === "SOLD_OUT_LP") tags += "<span class='soldout-lp-tag'>💸 已卖完 LP</span>";
            // 已卖完的交易者标签
            if(item.status === "SOLD_OUT_TRADER") tags += "<span class='soldout-trader-tag'>💸 已卖完 交易</span>";
            // 流动性提供者标签
            if(item.status === "LP") tags += "<span class='lp-tag'>💧 LP</span>";
            // 交易者标签
            if(item.status === "TRADER") tags += "<span class='trader-tag'>🔄 交易</span>";
            // 新地址标签
            if(item.status === "NEW") tags += "<span class='new-tag'>🔥 NEW</span>";
            // 回归标签
            if(item.status === "RETURN") tags += "<span class='ret-tag'>♻️ 回归</span>";

            if(item.note) {{
                if(item.note.includes("MINT")) {{
                     let cleanNote = item.note.replace("🎁 [MINT] ", "");
                     tags += "<span class='mint-tag'>MINT</span>";
                     if(cleanNote) tags += "<span class='rem'>" + cleanNote + "</span> ";
                }} else {{
                     tags += "<span class='rem'>" + item.note + "</span> ";
                }}
            }}

            html.push(`
                <tr>
                    <td>#${{item.rank}}</td>
                    <td>${{tags}}<span class="addr-0x">${{item.key}}</span><span class="addr-btc">${{item.btc}}</span></td>
                    <td style="color:#fff;font-weight:bold">${{balStr}}</td>
                    <td>${{bisSwapNetStr}}</td>
                    <td>${{bisAmmNetStr}}</td>
                    <td style="color:#00bcd4;font-weight:bold">${{totalBalanceStr}}</td>
                    <td style="color:#aaa">${{pctStr}}</td>
                    <td class="${{chgClass}}">${{chgText}}</td>
                    <td><button class="btn" onclick="show('${{item.key}}')">📈</button></td>
                </tr>
            `);
        }});
        tbody.innerHTML = html.join('');
    }}

    function changePageSize() {{
        const sizes = [50, 100, 200, 500];
        const currentIdx = sizes.indexOf(pageSize);
        pageSize = sizes[(currentIdx + 1) % sizes.length];
        document.getElementById('pageSizeLabel').innerText = pageSize;
        currentPage = 1;
        render();
    }}

    function prevPage() {{
        if(currentPage > 1) {{
            currentPage--;
            render();
        }}
    }}

    function nextPage() {{
        const totalPages = Math.ceil(filteredAndSortedData.length / pageSize);
        if(currentPage < totalPages) {{
            currentPage++;
            render();
        }}
    }}

    function sort(col) {{
        if(sortCol === col) sortDesc = !sortDesc;
        else {{ sortCol = col; sortDesc = true; }}
        render();
    }}

    let myChart;
    function show(key) {{
        document.getElementById('modal').style.display='block';
        if(myChart) myChart.destroy();
        const pts = chartData[key];
        if(!pts) return;

        // 计算最大值，用于设置Y轴范围
        const maxY = Math.max(...pts.map(p=>p.y));
        const yAxisMax = maxY > 0 ? Math.ceil(maxY * 1.1) : 100;  // 留10%顶部空间

        myChart = new Chart(document.getElementById('c'), {{
            type: 'line',
            data: {{
                labels: pts.map(p=>p.t),
                datasets: [{{
                    label: '总持仓量 (包含BIS)',
                    data: pts.map(p=>p.y),
                    borderColor: '#00bcd4',
                    backgroundColor: 'rgba(0,188,212,0.1)',
                    fill: true,
                    pointRadius: 3,
                    tension: 0.1
                }}]
            }},
            options: {{
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: '地址: '+key + ' - 总持仓趋势 (包含BIS SWAP和BIS AMM)',
                        color:'#fff',
                        font:{{size:14}}
                    }},
                    legend: {{
                        labels: {{
                            color: '#ccc'
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,  // 纵坐标轴从0开始
                        min: 0,
                        max: yAxisMax,     // 根据数据动态调整最大值
                        grid: {{
                            color: '#333'
                        }},
                        ticks: {{
                            color: '#aaa'
                        }},
                        title: {{
                            display: true,
                            text: '代币数量',
                            color: '#888'
                        }}
                    }},
                    x: {{
                        grid: {{
                            color: '#333'
                        }},
                        ticks: {{
                            color: '#aaa',
                            maxTicksLimit: 10
                        }}
                    }}
                }}
            }}
        }});
    }}

    window.onclick = function(e){{if(e.target==document.getElementById('modal'))document.getElementById('modal').style.display='none';}}
    render();
    </script>
    </body></html>
    """

    with open(HTML_FILE, 'w', encoding='utf-8') as f: f.write(html)
    return HTML_FILE

if __name__ == "__main__":
    db = load_db()
    minters_set = fetch_mint_list_deep()
    holders = fetch_data(minters_set, db.keys())

    if holders:
        path = generate_report(holders, db)
        print(f"✅ 报告已生成: {path}")
        # 注意: webbrowser 已移除，适合 GitHub Actions
    else:
        print("❌ 抓取失败。")
