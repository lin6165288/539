import streamlit as st
import math
import re
import itertools
import base64
import io
import time

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None

try:
    from PIL import Image
except Exception:
    Image = None

st.set_page_config(
    page_title="539 快速計算器",
    page_icon="🎯",
    layout="wide"
)

# ===== 緊湊手機版樣式 =====
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 0.25rem;
        padding-left: 0.45rem;
        padding-right: 0.45rem;
        max-width: 720px;
    }

    h1 {
        font-size: 1.18rem !important;
        margin-bottom: 0.1rem !important;
    }

    h2, h3 {
        font-size: 0.98rem !important;
        margin-top: 0.35rem !important;
        margin-bottom: 0.25rem !important;
    }

    p {
        margin-bottom: 0.25rem !important;
    }

    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }

    .main-btn button {
        height: 2.6rem !important;
        font-size: 0.95rem !important;
        border-radius: 12px !important;
    }

    .small-btn button {
        height: 2.05rem !important;
        font-size: 0.8rem !important;
        padding: 0 !important;
    }

    .stNumberInput input {
        font-size: 0.95rem;
        height: 2.35rem;
    }

    textarea {
        font-size: 0.88rem !important;
        line-height: 1.35 !important;
    }

    div[data-testid="stMetric"] {
        background-color: #fff7ed;
        padding: 8px;
        border-radius: 12px;
        border: 1px solid #fed7aa;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.78rem;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1rem;
    }

    .selected-box {
        background: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 7px;
        margin-bottom: 5px;
        font-size: 0.84rem;
        min-height: 48px;
    }

    .sticky-photo {
        position: sticky;
        top: 0;
        z-index: 999;
        background: white;
        padding: 4px 0 6px 0;
        border-bottom: 2px solid #f97316;
    }

    .sticky-photo img {
        width: 100%;
        object-fit: contain;
        border-radius: 10px;
        border: 1px solid #ddd;
        background: #fafafa;
    }

    /* 只壓縮號碼選號區，不影響其他按鈕 */
    .st-key-number_pad_area div[data-testid="stVerticalBlock"] {
        gap: 0.05rem !important;
    }

    .st-key-number_pad_area div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0.04rem !important;
    }

    .st-key-number_pad_area div[data-testid="column"] {
        min-width: 0 !important;
        flex: 1 1 0 !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
    }

    .st-key-number_pad_area div[data-testid="stElementContainer"] {
        margin-bottom: 0rem !important;
    }

    .st-key-number_pad_area .num-btn {
        margin-top: -0.22rem !important;
        margin-bottom: -0.22rem !important;
    }

    .st-key-number_pad_area .num-btn button {
        height: 1.55rem !important;
        min-height: 1.55rem !important;
        font-size: 0.66rem !important;
        padding: 0 !important;
        border-radius: 6px !important;
    }

    @media (max-width: 390px) {
        .block-container {
            padding-left: 0.35rem;
            padding-right: 0.35rem;
        }

        .st-key-number_pad_area .num-btn {
            margin-top: -0.28rem !important;
            margin-bottom: -0.28rem !important;
        }

        .st-key-number_pad_area .num-btn button {
            height: 1.45rem !important;
            min-height: 1.45rem !important;
            font-size: 0.6rem !important;
            border-radius: 5px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🎯 539 快速計算器")
st.caption("填 1 區＝一般組合；填 2 區以上＝分區交叉；車＝號碼數 × 倍率 × 38。")


# ===== 基本設定 =====

GROUP_KEYS = ["A區", "B區", "C區", "D區", "E區", "F區", "G區", "H區"]
QUICK_VALUES = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0]


# ===== 工具函式 =====

def combination(n, r):
    if n < r:
        return 0
    return math.comb(n, r)


def format_num(value):
    if abs(value - round(value)) < 1e-7:
        return str(int(round(value)))
    return f"{value:.2f}"


def parse_numbers(text):
    number_matches = re.findall(r"\d{1,2}", text)

    numbers = []
    invalid_numbers = []

    for item in number_matches:
        num = int(item)
        if 1 <= num <= 39:
            numbers.append(num)
        else:
            invalid_numbers.append(num)

    unique_numbers = sorted(set(numbers))
    duplicate_count = len(numbers) - len(unique_numbers)

    return unique_numbers, invalid_numbers, duplicate_count


def normalize_combined_multipliers(line):
    """
    支援倍率簡寫：
    2x0.1 = 二x0.1
    3x0.1 = 三x0.1
    4x0.1 = 四x0.1
    23x0.1 / 二三x0.1 / ==x0.1 = 二x0.1 三x0.1
    234x0.1 / 二三四x0.1 = 二x0.1 三x0.1 四x0.1
    """
    line = line.replace("×", "x").replace("X", "x")

    # 常見手寫：==x0.1、== x 0.1，代表二星和三星
    line = re.sub(
        r"={2,}\s*x\s*(\d+(?:\.\d+)?)",
        r"二x\1 三x\1",
        line
    )

    mapping = {
        "二": "二",
        "三": "三",
        "四": "四",
        "2": "二",
        "3": "三",
        "4": "四",
    }

    # 先處理 23x0.1、234x0.1、二三x0.1、二三四x0.1
    combined_pattern = r"(?<!\d)([二三四234]{2,3})\s*x\s*(\d+(?:\.\d+)?)"

    def combined_repl(match):
        stars_raw = match.group(1)
        value = match.group(2)

        stars = []
        for ch in stars_raw:
            star = mapping.get(ch)
            if star and star not in stars:
                stars.append(star)

        return " ".join(f"{star}x{value}" for star in stars)

    line = re.sub(combined_pattern, combined_repl, line)

    # 再處理單一數字倍率 2x0.1、3x0.1、4x0.1
    single_pattern = r"(?<!\d)([234])\s*x\s*(\d+(?:\.\d+)?)"

    def single_repl(match):
        star = mapping.get(match.group(1))
        value = match.group(2)
        return f"{star}x{value}"

    line = re.sub(single_pattern, single_repl, line)

    return line


def cross_group_count(groups, star):
    if len(groups) < star:
        return 0

    total = 0

    for selected_groups in itertools.combinations(groups, star):
        for ticket in itertools.product(*selected_groups):
            if len(ticket) == len(set(ticket)):
                total += 1

    return total


def group_display(groups):
    if not groups:
        return ""

    return " × ".join("、".join(f"{num:02d}" for num in group) for group in groups)


def selected_to_text(nums):
    return " ".join(f"{num:02d}" for num in sorted(nums))


def get_filled_group_texts():
    group_texts = []

    for group_key in GROUP_KEYS:
        text = selected_to_text(st.session_state[group_key])
        if text:
            group_texts.append(text)

    return group_texts


def infer_line_from_groups(two_m, three_m, four_m, car_m):
    group_texts = get_filled_group_texts()

    if len(group_texts) == 1:
        return f"{group_texts[0]} 二x{two_m:g} 三x{three_m:g} 四x{four_m:g} 車x{car_m:g}"

    return f"{' | '.join(group_texts)} 二x{two_m:g} 三x{three_m:g} 四x{four_m:g} 車x{car_m:g}"


def parse_multiplier(line, star_patterns):
    pattern = r"(" + "|".join(star_patterns) + r")\s*[xX×]\s*(\d+(\.\d+)?)"
    match = re.search(pattern, line)

    if match:
        multiplier = float(match.group(2))
        line = line.replace(match.group(0), "")
        return multiplier, line

    return 0.0, line


def normalize_cross_group_separator(line):
    """
    AI 不一定會乖乖輸出 |，有時會保留 x / × 當作分區交叉分隔。
    在倍率被移除之後，剩下的 x / × 幾乎都可以視為分區分隔符。
    """
    line = line.replace("×", " x ").replace("X", " x ")

    # 把獨立的 x 視為分區交叉分隔符
    line = re.sub(r"\s+x\s+", " | ", line)

    # 清理多餘空白
    line = re.sub(r"\s*\|\s*", " | ", line)
    line = re.sub(r"\s+", " ", line).strip()

    return line


def parse_line(line):
    original_line = line
    line = normalize_combined_multipliers(line)

    two_multiplier, line = parse_multiplier(line, ["二", "2"])
    three_multiplier, line = parse_multiplier(line, ["三", "3"])
    four_multiplier, line = parse_multiplier(line, ["四", "4"])
    car_multiplier, line = parse_multiplier(line, ["車"])

    # 倍率移除後，如果還有 x / ×，通常就是分區交叉分隔符
    line = normalize_cross_group_separator(line)

    is_cross_group = "|" in line

    all_invalid_numbers = []
    total_duplicate_count = 0

    if is_cross_group:
        group_texts = [part.strip() for part in line.split("|") if part.strip()]
        groups = []

        for group_text in group_texts:
            numbers, invalid_numbers, duplicate_count = parse_numbers(group_text)

            if numbers:
                groups.append(numbers)

            all_invalid_numbers.extend(invalid_numbers)
            total_duplicate_count += duplicate_count

        all_numbers = sorted(set(num for group in groups for num in group))

        return {
            "original_line": original_line,
            "mode": "分區交叉",
            "groups": groups,
            "numbers": all_numbers,
            "two_multiplier": two_multiplier,
            "three_multiplier": three_multiplier,
            "four_multiplier": four_multiplier,
            "car_multiplier": car_multiplier,
            "invalid_numbers": all_invalid_numbers,
            "duplicate_count": total_duplicate_count
        }

    numbers, invalid_numbers, duplicate_count = parse_numbers(line)

    return {
        "original_line": original_line,
        "mode": "一般組合",
        "groups": [],
        "numbers": numbers,
        "two_multiplier": two_multiplier,
        "three_multiplier": three_multiplier,
        "four_multiplier": four_multiplier,
        "car_multiplier": car_multiplier,
        "invalid_numbers": invalid_numbers,
        "duplicate_count": duplicate_count
    }


def calculate_results(lines, price_2, price_3, price_4, price_car):
    results = []

    total_two_count = 0
    total_three_count = 0
    total_four_count = 0
    total_car_count = 0

    total_two_cost = 0
    total_three_cost = 0
    total_four_cost = 0
    total_car_cost = 0

    for index, line in enumerate(lines, start=1):
        parsed = parse_line(line)

        numbers = parsed["numbers"]
        groups = parsed["groups"]
        mode = parsed["mode"]
        n = len(numbers)

        if mode == "分區交叉":
            two_base = cross_group_count(groups, 2)
            three_base = cross_group_count(groups, 3)
            four_base = cross_group_count(groups, 4)
        else:
            two_base = combination(n, 2)
            three_base = combination(n, 3)
            four_base = combination(n, 4)

        car_base = n * 38

        two_multiplier = parsed["two_multiplier"]
        three_multiplier = parsed["three_multiplier"]
        four_multiplier = parsed["four_multiplier"]
        car_multiplier = parsed["car_multiplier"]

        two_actual = two_base * two_multiplier
        three_actual = three_base * three_multiplier
        four_actual = four_base * four_multiplier
        car_actual = car_base * car_multiplier

        two_cost = two_actual * price_2
        three_cost = three_actual * price_3
        four_cost = four_actual * price_4
        car_cost = car_actual * price_car

        total_two_count += two_actual
        total_three_count += three_actual
        total_four_count += four_actual
        total_car_count += car_actual

        total_two_cost += two_cost
        total_three_cost += three_cost
        total_four_cost += four_cost
        total_car_cost += car_cost

        results.append({
            "區塊": index,
            "模式": mode,
            "原始輸入": parsed["original_line"],
            "分區": group_display(groups),
            "全部號碼": "、".join(f"{num:02d}" for num in numbers),
            "號碼數": n,
            "二星倍率": two_multiplier,
            "三星倍率": three_multiplier,
            "四星倍率": four_multiplier,
            "車倍率": car_multiplier,
            "二星原始支數": two_base,
            "三星原始支數": three_base,
            "四星原始支數": four_base,
            "車原始支數": car_base,
            "二星實際支數": two_actual,
            "三星實際支數": three_actual,
            "四星實際支數": four_actual,
            "車實際支數": car_actual,
            "二星金額": two_cost,
            "三星金額": three_cost,
            "四星金額": four_cost,
            "車金額": car_cost,
            "小計": two_cost + three_cost + four_cost + car_cost,
            "重複號碼數": parsed["duplicate_count"],
            "錯誤號碼": "、".join(str(num) for num in parsed["invalid_numbers"])
        })

    totals = {
        "total_two_count": total_two_count,
        "total_three_count": total_three_count,
        "total_four_count": total_four_count,
        "total_car_count": total_car_count,
        "total_two_cost": total_two_cost,
        "total_three_cost": total_three_cost,
        "total_four_cost": total_four_cost,
        "total_car_cost": total_car_cost,
        "total_cost": total_two_cost + total_three_cost + total_four_cost + total_car_cost
    }

    return results, totals


def clear_all_groups():
    for group_key in GROUP_KEYS:
        st.session_state[group_key] = []


def reset_all_multipliers():
    # 不直接改 number_input 的 session_state，避免 StreamlitAPIException
    st.session_state["need_reset_multipliers"] = True


def find_duplicate_in_other_groups(active_group, num):
    for group_key in GROUP_KEYS:
        if group_key == active_group:
            continue

        if num in st.session_state[group_key]:
            return group_key

    return None


def add_or_remove_number(group_key, num):
    if num in st.session_state[group_key]:
        st.session_state[group_key].remove(num)
        st.session_state["select_warning"] = ""
        return

    duplicate_group = find_duplicate_in_other_groups(group_key, num)

    if duplicate_group:
        st.session_state["select_warning"] = (
            f"⚠️ {num:02d} 已經在 {duplicate_group}，不能再加入 {group_key}。"
        )
        return

    st.session_state[group_key].append(num)
    st.session_state["select_warning"] = ""


def set_multiplier(target_key, value):
    st.session_state[target_key] = value


def render_number_pad(group_key):
    numbers = list(range(1, 40))

    with st.container(key="number_pad_area"):
        for row_start in range(0, 39, 10):
            row_nums = numbers[row_start:row_start + 10]
            cols = st.columns(10, gap="small")

            for i, num in enumerate(row_nums):
                selected = num in st.session_state[group_key]
                label = f"✓{num:02d}" if selected else f"{num:02d}"

                with cols[i]:
                    st.markdown('<div class="num-btn">', unsafe_allow_html=True)

                    st.button(
                        label,
                        key=f"{group_key}_{num}",
                        use_container_width=True,
                        on_click=add_or_remove_number,
                        args=(group_key, num)
                    )

                    st.markdown('</div>', unsafe_allow_html=True)


def render_multiplier_control(label, state_key):
    value = st.number_input(
        label,
        min_value=0.0,
        step=0.05,
        format="%.2f",
        key=state_key
    )

    q1, q2 = st.columns(2, gap="small")

    for idx, quick_value in enumerate(QUICK_VALUES):
        with (q1 if idx % 2 == 0 else q2):
            st.markdown('<div class="small-btn">', unsafe_allow_html=True)

            st.button(
                f"{quick_value:g}",
                key=f"{state_key}_{quick_value}",
                use_container_width=True,
                on_click=set_multiplier,
                args=(state_key, quick_value)
            )

            st.markdown('</div>', unsafe_allow_html=True)

    return value


def manual_line_has_cross_duplicate(line):
    parsed = parse_line(line)

    if parsed["mode"] != "分區交叉":
        return []

    seen = {}
    duplicates = []

    for group_index, group in enumerate(parsed["groups"], start=1):
        for num in group:
            if num in seen:
                duplicates.append((num, seen[num], group_index))
            else:
                seen[num] = group_index

    return duplicates


def cross_group_hit_count(groups, star, winning_set):
    """分區交叉兌獎：選 star 個區，每區取 1 號，全部落在開獎號碼內才算中。"""
    if len(groups) < star:
        return 0

    total = 0

    for selected_groups in itertools.combinations(groups, star):
        for ticket in itertools.product(*selected_groups):
            if len(ticket) == len(set(ticket)) and all(num in winning_set for num in ticket):
                total += 1

    return total


def build_redeem_ticket(ticket_name, line, result_row):
    parsed = parse_line(line)

    return {
        "票名": ticket_name,
        "原始輸入": line,
        "模式": parsed["mode"],
        "groups": parsed["groups"],
        "numbers": parsed["numbers"],
        "二星倍率": parsed["two_multiplier"],
        "三星倍率": parsed["three_multiplier"],
        "四星倍率": parsed["four_multiplier"],
        "車倍率": parsed["car_multiplier"],
        "二星下注支數": result_row["二星實際支數"],
        "三星下注支數": result_row["三星實際支數"],
        "四星下注支數": result_row["四星實際支數"],
        "車下注支數": result_row["車實際支數"],
        "分區顯示": group_display(parsed["groups"]),
        "號碼顯示": "、".join(f"{num:02d}" for num in parsed["numbers"]),
    }


def get_next_redeem_ticket_name():
    """
    兌獎區的「第幾張」是依照每次按下開始計算來編號，
    不是依照同一次計算裡有幾行組別來編號。
    例如：第 1 次開始計算有 1 行 => 第1張
          第 2 次開始計算有 2 行 => 兩行都算第2張
    """
    existing_names = []

    for ticket in st.session_state.get("redeem_tickets", []):
        ticket_name = ticket.get("票名", "")
        if ticket_name and ticket_name not in existing_names:
            existing_names.append(ticket_name)

    return f"第{len(existing_names) + 1}張"


def save_current_calculation_to_redeem(lines, price_2, price_3, price_4, price_car):
    results, _ = calculate_results(lines, price_2, price_3, price_4, price_car)

    # 同一次按下「開始計算」的所有組別，都歸在同一張票名底下
    ticket_name = get_next_redeem_ticket_name()

    for index, line in enumerate(lines):
        ticket = build_redeem_ticket(ticket_name, line, results[index])
        st.session_state["redeem_tickets"].append(ticket)


def parse_winning_numbers(text):
    numbers, invalid_numbers, duplicate_count = parse_numbers(text)
    return numbers, invalid_numbers, duplicate_count


def calculate_redeem_result(ticket, winning_numbers):
    winning_set = set(winning_numbers)
    hit_numbers = sorted(set(ticket["numbers"]) & winning_set)
    hit_count = len(hit_numbers)

    if ticket["模式"] == "分區交叉":
        two_hit_base = cross_group_hit_count(ticket["groups"], 2, winning_set)
        three_hit_base = cross_group_hit_count(ticket["groups"], 3, winning_set)
        four_hit_base = cross_group_hit_count(ticket["groups"], 4, winning_set)
    else:
        two_hit_base = combination(hit_count, 2)
        three_hit_base = combination(hit_count, 3)
        four_hit_base = combination(hit_count, 4)

    # 車的中獎支數：命中號碼數 × 車倍率 × 4
    car_hit_base = hit_count * 4

    two_hit_actual = two_hit_base * ticket["二星倍率"]
    three_hit_actual = three_hit_base * ticket["三星倍率"]
    four_hit_actual = four_hit_base * ticket["四星倍率"]
    car_hit_actual = car_hit_base * ticket["車倍率"]

    return {
        "票名": ticket["票名"],
        "模式": ticket["模式"],
        "命中號碼": "、".join(f"{num:02d}" for num in hit_numbers) if hit_numbers else "無",
        "命中號碼數": hit_count,
        "二星中獎支數": two_hit_actual,
        "三星中獎支數": three_hit_actual,
        "四星中獎支數": four_hit_actual,
        "車中獎支數": car_hit_actual,
        "總中獎支數": two_hit_actual + three_hit_actual + four_hit_actual + car_hit_actual,
        "二星下注支數": ticket["二星下注支數"],
        "三星下注支數": ticket["三星下注支數"],
        "四星下注支數": ticket["四星下注支數"],
        "車下注支數": ticket["車下注支數"],
        "原始輸入": ticket["原始輸入"],
    }


def ticket_sort_key(ticket_name):
    match = re.search(r"第(\d+)張", ticket_name)
    if match:
        return int(match.group(1))
    return 999999


def redeem_ticket_summary_rows():
    """已儲存票券：同一張票的多個區塊合併顯示下注總支數。"""
    summary = {}

    for ticket in st.session_state["redeem_tickets"]:
        name = ticket["票名"]

        if name not in summary:
            summary[name] = {
                "票名": name,
                "包含組數": 0,
                "二星總支數": 0,
                "三星總支數": 0,
                "四星總支數": 0,
                "車總支數": 0,
                "號碼內容": [],
            }

        summary[name]["包含組數"] += 1
        summary[name]["二星總支數"] += ticket["二星下注支數"]
        summary[name]["三星總支數"] += ticket["三星下注支數"]
        summary[name]["四星總支數"] += ticket["四星下注支數"]
        summary[name]["車總支數"] += ticket["車下注支數"]
        summary[name]["號碼內容"].append(ticket["原始輸入"])

    rows = []

    for name in sorted(summary.keys(), key=ticket_sort_key):
        item = summary[name]
        rows.append({
            "票名": item["票名"],
            "包含組數": item["包含組數"],
            "二星總支數": item["二星總支數"],
            "三星總支數": item["三星總支數"],
            "四星總支數": item["四星總支數"],
            "車總支數": item["車總支數"],
            "號碼內容": " / ".join(item["號碼內容"]),
        })

    return rows


def redeem_ticket_detail_rows():
    """保留每一組明細，方便檢查。"""
    rows = []

    for ticket in st.session_state["redeem_tickets"]:
        rows.append({
            "票名": ticket["票名"],
            "模式": ticket["模式"],
            "分區": ticket["分區顯示"],
            "號碼": ticket["號碼顯示"],
            "二星下注支數": ticket["二星下注支數"],
            "三星下注支數": ticket["三星下注支數"],
            "四星下注支數": ticket["四星下注支數"],
            "車下注支數": ticket["車下注支數"],
            "原始輸入": ticket["原始輸入"],
        })

    return rows


def redeem_result_summary_by_ticket(winning_numbers):
    """兌獎結果：同一張票合併顯示各星別下注總支數與中獎總支數。"""
    summary = {}

    for ticket in st.session_state["redeem_tickets"]:
        name = ticket["票名"]
        result = calculate_redeem_result(ticket, winning_numbers)

        if name not in summary:
            summary[name] = {
                "票名": name,
                "包含組數": 0,
                "命中號碼集合": set(),
                "二星總支數": 0,
                "三星總支數": 0,
                "四星總支數": 0,
                "車總支數": 0,
                "二星中獎支數": 0,
                "三星中獎支數": 0,
                "四星中獎支數": 0,
                "車中獎支數": 0,
                "總中獎支數": 0,
            }

        summary[name]["包含組數"] += 1

        for num in set(ticket["numbers"]) & set(winning_numbers):
            summary[name]["命中號碼集合"].add(num)

        summary[name]["二星總支數"] += ticket["二星下注支數"]
        summary[name]["三星總支數"] += ticket["三星下注支數"]
        summary[name]["四星總支數"] += ticket["四星下注支數"]
        summary[name]["車總支數"] += ticket["車下注支數"]

        summary[name]["二星中獎支數"] += result["二星中獎支數"]
        summary[name]["三星中獎支數"] += result["三星中獎支數"]
        summary[name]["四星中獎支數"] += result["四星中獎支數"]
        summary[name]["車中獎支數"] += result["車中獎支數"]
        summary[name]["總中獎支數"] += result["總中獎支數"]

    rows = []

    for name in sorted(summary.keys(), key=ticket_sort_key):
        item = summary[name]
        hit_numbers = sorted(item["命中號碼集合"])
        rows.append({
            "票名": item["票名"],
            "包含組數": item["包含組數"],
            "命中號碼": "、".join(f"{num:02d}" for num in hit_numbers) if hit_numbers else "無",
            "二星總支數": item["二星總支數"],
            "二星中獎支數": item["二星中獎支數"],
            "三星總支數": item["三星總支數"],
            "三星中獎支數": item["三星中獎支數"],
            "四星總支數": item["四星總支數"],
            "四星中獎支數": item["四星中獎支數"],
            "車總支數": item["車總支數"],
            "車中獎支數": item["車中獎支數"],
            "總中獎支數": item["總中獎支數"],
        })

    return rows



# ===== AI 辨識工具 =====

CROP_AREAS = {
    "整張": (0.0, 0.0, 1.0, 1.0),
    "左上": (0.0, 0.0, 0.42, 0.36),
    "上方": (0.28, 0.0, 0.72, 0.36),
    "右上": (0.58, 0.0, 1.0, 0.36),
    "左中": (0.0, 0.28, 0.42, 0.68),
    "中間": (0.28, 0.28, 0.72, 0.68),
    "右中": (0.58, 0.28, 1.0, 0.68),
    "左下": (0.0, 0.60, 0.42, 1.0),
    "下方": (0.25, 0.60, 0.75, 1.0),
    "右下": (0.58, 0.60, 1.0, 1.0),
}


def crop_uploaded_image_bytes(uploaded_file, crop_area_name):
    image_bytes = uploaded_file.getvalue()
    mime_type = uploaded_file.type or "image/jpeg"

    if crop_area_name == "整張" or Image is None:
        return image_bytes, mime_type

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = image.size

    left_r, top_r, right_r, bottom_r = CROP_AREAS.get(crop_area_name, CROP_AREAS["整張"])
    left = int(width * left_r)
    top = int(height * top_r)
    right = int(width * right_r)
    bottom = int(height * bottom_r)

    cropped = image.crop((left, top, right, bottom))

    output = io.BytesIO()
    cropped.save(output, format="JPEG", quality=95)
    return output.getvalue(), "image/jpeg"


def preview_crop_image(uploaded_file, crop_area_name):
    if uploaded_file is None:
        return

    image_bytes, mime_type = crop_uploaded_image_bytes(uploaded_file, crop_area_name)
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    st.markdown(
        f"""
        <div style="background:#f8fafc;border:1px solid #cbd5e1;border-radius:10px;padding:6px;margin-bottom:8px;">
            <div style="font-size:0.82rem;color:#475569;margin-bottom:4px;">AI 實際辨識範圍：{crop_area_name}</div>
            <img style="width:100%;max-height:260px;object-fit:contain;border-radius:8px;" src="data:{mime_type};base64,{image_base64}">
        </div>
        """,
        unsafe_allow_html=True
    )


def is_multiplier_only_line(line):
    temp = normalize_combined_multipliers(line)
    temp = temp.replace("×", "x").replace("X", "x")
    temp = re.sub(r"\s+", " ", temp).strip()

    pattern = r"^(?:(?:二|三|四|車)x\d+(?:\.\d+)?)(?:\s+(?:二|三|四|車)x\d+(?:\.\d+)?)*$"
    return bool(re.fullmatch(pattern, temp))


def clean_ai_output(text):
    text = text.strip()

    # 移除 Markdown code fence
    text = text.replace("```text", "").replace("```", "").strip()

    # Gemini 有時候會把換行輸出成字面上的 \n，先轉回真正換行
    text = text.replace("\\n", "\n")

    cleaned_lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        # 移除 AI 可能輸出的項目符號或編號
        line = re.sub(r"^[\-•*]\s*", "", line)
        line = re.sub(r"^\d+[\.、\)]\s*", "", line)

        # 移除位置標籤，例如：左上 =>、中間：
        line = re.sub(r"^(左上|上方|右上|左中|中間|右中|左下|下方|右下|位置不確定)\s*(=>|:|：)\s*", "", line)

        # 忽略頁面標記，例如 A1 / A2 / A3 / A4 / 539 / 日期
        if re.fullmatch(r"A\s*\d+", line, flags=re.I):
            continue
        if re.fullmatch(r"\d{1,2}\s*/\s*\d{1,2}", line):
            continue
        if re.fullmatch(r"539", line):
            continue

        # 統一分隔符
        line = line.replace("×", "x").replace("X", "x")
        line = re.sub(r"\s+", " ", line)

        # 展開 2x0.1、23x0.1、二三x0.1、==x0.1
        line = normalize_combined_multipliers(line)

        # 如果某一行只有倍率，且前一行已有號碼，則自動接到前一行後面
        if cleaned_lines and is_multiplier_only_line(line):
            cleaned_lines[-1] = (cleaned_lines[-1] + " " + line).strip()
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def recognize_lottery_image_with_gemini(uploaded_file, crop_area_name):
    if genai is None or types is None:
        raise RuntimeError("尚未安裝 google-genai。請確認 requirements.txt 有 google-genai。")

    api_key = st.secrets.get("GEMINI_API_KEY", "")

    if not api_key:
        raise RuntimeError("找不到 GEMINI_API_KEY。請到 Streamlit Secrets 加上 GEMINI_API_KEY。")

    image_bytes, mime_type = crop_uploaded_image_bytes(uploaded_file, crop_area_name)

    client = genai.Client(api_key=api_key)

    prompt = f"""
你正在辨識台灣539手寫彩券草稿。
這個使用者之後上傳的圖片版型幾乎固定，請根據以下規則辨識整張圖片。

請只輸出可供程式解析的文字，不要解釋，不要加編號，不要加位置名稱。

輸出格式只允許下面兩種：
一般組合：
01 02 03 04 05 二x0 三x0 四x0.1 車x0

分區交叉：
08 | 12 24 | 03 15 | 16 23 二x0 三x0 四x0.2 車x0

重要規則：
1. 每一組一行，請輸出真正換行，不要輸出字面上的 \\n。
2. 這些圖片大多是橫式書寫，請優先由上到下逐組辨識；每一橫列或每一個獨立小區塊通常就是一組。
3. 號碼只允許 01～39，請一律輸出兩位數。
4. 請忽略標題或頁面標記，例如：6/20、539、A1、A2、A3、A4。
5. 倍率可能寫成：
   2x0.1 = 二x0.1
   3x0.1 = 三x0.1
   4x0.1 = 四x0.1
   23x0.1 / 二三x0.1 / ==x0.1 = 二x0.1 三x0.1
   234x0.1 / 二三四x0.1 = 二x0.1 三x0.1 四x0.1
6. 如果沒有看到某星別倍率，請補 0，例如：二x0 三x0 四x0 車x0。
7. 如果同一組中出現 x / X / × 分隔不同欄位，通常代表分區交叉，請輸出成 | 分隔，不要省略。
8. 如果同一欄有上下堆疊的號碼，表示它們屬於同一區，要合併在一起。
9. 如果倍率另起一行，請把倍率併回上一組，不要獨立成一行。
10. 如果右側另有一個獨立小區塊，也請視為新的獨立一組。
11. 看不清楚請用 ?，不要猜。

以下是這個使用者常見格式的範例，請盡量照這個邏輯辨識：

範例 A（一般組合）
圖片：03,07,14,21,20,31,35 4x0.5
輸出：
03 07 14 21 20 31 35 二x0 三x0 四x0.5 車x0

範例 B（一般組合，倍率寫成數字）
圖片：15,38,39 = 三x0.5
輸出：
15 38 39 二x0 三x0.5 四x0 車x0

範例 C（分區交叉，上下堆疊同欄）
圖片：
08 x 12 x 03 x 16
   24   15   23
4x0.2
輸出：
08 | 12 24 | 03 15 | 16 23 二x0 三x0 四x0.2 車x0

範例 D（分區交叉，兩排對齊）
圖片：
03   12   35   06
33 x 22 x 39 x 08
4x0.2
輸出：
03 33 | 12 22 | 35 39 | 06 08 二x0 三x0 四x0.2 車x0

範例 E（分區交叉，一列內直接寫）
圖片：14 x 20 39 x 09 28 ==x0.3
輸出：
14 | 20 39 | 09 28 二x0.3 三x0.3 四x0 車x0

範例 F（多個倍率分行寫在同一組下方）
圖片：
08 11 36 38
2x1
3x7
4x0.1
輸出：
08 11 36 38 二x1 三x7 四x0.1 車x0
"""

    last_error = None

    for wait_seconds in [0, 2, 5]:
        if wait_seconds:
            time.sleep(wait_seconds)

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
            )

            result_text = getattr(response, "text", "")

            if not result_text:
                raise RuntimeError("Gemini 沒有回傳文字。")

            return clean_ai_output(result_text)

        except Exception as exc:
            last_error = exc
            error_text = str(exc)

            # 忙線才重試
            if "503" not in error_text and "UNAVAILABLE" not in error_text:
                break

    raise RuntimeError(f"Gemini 辨識失敗：{last_error}")


def validate_ai_draft_lines(lines):
    errors = []

    for line_index, line in enumerate(lines, start=1):
        if "?" in line:
            errors.append(f"第 {line_index} 行含有 ?，請先人工確認。")
            continue

        parsed = parse_line(line)

        if parsed["invalid_numbers"]:
            errors.append(
                f"第 {line_index} 行有錯誤號碼："
                + "、".join(str(num) for num in parsed["invalid_numbers"])
            )

        duplicates = manual_line_has_cross_duplicate(line)

        for num, first_group, second_group in duplicates:
            errors.append(
                f"第 {line_index} 行：{num:02d} 同時出現在第 {first_group} 區與第 {second_group} 區。"
            )

        if len(parsed["numbers"]) == 0:
            errors.append(f"第 {line_index} 行沒有辨識到有效號碼。")

    return errors


def ai_draft_review_rows(text):
    rows = []

    # 保險：如果草稿裡還殘留字面上的 \n，也先轉成真正換行
    text = text.replace("\\n", "\n")

    lines = [
        normalize_combined_multipliers(line.strip())
        for line in text.split("\n")
        if line.strip()
    ]

    for line_index, line in enumerate(lines, start=1):
        parsed = parse_line(line)

        check_items = []

        if "?" in line:
            check_items.append("有?需確認")

        if parsed["invalid_numbers"]:
            check_items.append(
                "錯誤號碼：" + "、".join(str(num) for num in parsed["invalid_numbers"])
            )

        duplicates = manual_line_has_cross_duplicate(line)
        if duplicates:
            check_items.append("跨區重複")

        if len(parsed["numbers"]) == 0:
            check_items.append("未辨識到號碼")

        if not check_items:
            check_items.append("OK")

        rows.append({
            "行": line_index,
            "模式": parsed["mode"],
            "號碼": "、".join(f"{num:02d}" for num in parsed["numbers"]),
            "分區": group_display(parsed["groups"]),
            "二": parsed["two_multiplier"],
            "三": parsed["three_multiplier"],
            "四": parsed["four_multiplier"],
            "車": parsed["car_multiplier"],
            "檢查": "；".join(check_items),
            "草稿原文": line,
        })

    return rows



# ===== Session State =====

if "lines" not in st.session_state:
    st.session_state["lines"] = []

if "calculate_clicked" not in st.session_state:
    st.session_state["calculate_clicked"] = False

if "active_group" not in st.session_state:
    st.session_state["active_group"] = "A區"

if "select_warning" not in st.session_state:
    st.session_state["select_warning"] = ""

if "two_multiplier" not in st.session_state:
    st.session_state["two_multiplier"] = 0.0

if "three_multiplier" not in st.session_state:
    st.session_state["three_multiplier"] = 0.0

if "four_multiplier" not in st.session_state:
    st.session_state["four_multiplier"] = 0.0

if "car_multiplier" not in st.session_state:
    st.session_state["car_multiplier"] = 0.0

if "need_reset_multipliers" not in st.session_state:
    st.session_state["need_reset_multipliers"] = False

if "redeem_tickets" not in st.session_state:
    st.session_state["redeem_tickets"] = []

if "ai_draft_text" not in st.session_state:
    st.session_state["ai_draft_text"] = ""

if "ai_draft_text_editor" not in st.session_state:
    st.session_state["ai_draft_text_editor"] = ""

for key in GROUP_KEYS:
    if key not in st.session_state:
        st.session_state[key] = []


# ===== 照片區 =====

with st.expander("📷 照片參考", expanded=False):
    uploaded_file = st.file_uploader(
        "上傳彩券照片",
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed"
    )

    if uploaded_file is not None:
        photo_size = st.radio(
            "照片大小",
            ["小", "中", "大", "特大", "超大"],
            horizontal=True,
            index=0,
            label_visibility="collapsed"
        )

        height_map = {
            "小": "120px",
            "中": "200px",
            "大": "320px",
            "特大": "520px",
            "超大": "760px"
        }

        image_bytes = uploaded_file.getvalue()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = uploaded_file.type

        st.markdown(
            f"""
            <div class="sticky-photo">
                <img style="max-height: {height_map[photo_size]};" src="data:{mime_type};base64,{image_base64}">
            </div>
            """,
            unsafe_allow_html=True
        )




# ===== AI 辨識區 =====

with st.expander("🤖 AI辨識圖片文字", expanded=False):
    st.caption("AI 只辨識整張圖片並產生草稿；已針對你常見的 A1/A2/A3/A4 橫式手寫格式加強。手動選號模式仍保留。")

    if uploaded_file is None:
        st.info("請先在照片參考區上傳圖片。")
    else:
        st.info("目前設定為辨識整張圖片，並優先針對你常見的橫式手寫格式處理。若 AI 有錯，仍可直接修改下方草稿。")

        if st.button("AI辨識整張圖片", use_container_width=True):
            try:
                with st.spinner("AI辨識中，請稍候..."):
                    ai_text = recognize_lottery_image_with_gemini(uploaded_file, "整張")

                st.session_state["ai_draft_text"] = ai_text
                st.session_state["ai_draft_text_editor"] = ai_text
                st.success("AI辨識完成，請先核對草稿。")
            except Exception as exc:
                st.error(str(exc))

        st.caption("下面這個草稿框可以直接手動編輯、修正，再加入組別。若本來應該是分區交叉，請確認有用 | 分隔各區。")
        ai_draft_text = st.text_area(
            "AI辨識草稿（可直接編輯）",
            key="ai_draft_text_editor",
            value=st.session_state.get("ai_draft_text", ""),
            height=260,
            placeholder="AI辨識結果會出現在這裡，你可以直接修改內容後再加入。"
        )

        # 保險：如果 AI 或手動貼上的內容含有字面上的 \n，轉成真正換行
        ai_draft_text = ai_draft_text.replace("\\n", "\n")
        st.session_state["ai_draft_text"] = ai_draft_text

        if st.session_state["ai_draft_text"].strip():
            st.markdown("#### AI草稿核對表")
            st.caption("先看這張表核對號碼、分區與倍率；需要修改時，直接改上方草稿文字。")
            st.dataframe(
                ai_draft_review_rows(st.session_state["ai_draft_text"]),
                use_container_width=True,
                hide_index=True
            )

        add_ai_col, clear_ai_col = st.columns(2, gap="small")

        with add_ai_col:
            if st.button("把AI草稿加入組別", use_container_width=True):
                draft_lines = [
                    normalize_combined_multipliers(line.strip())
                    for line in st.session_state["ai_draft_text"].split("\n")
                    if line.strip()
                ]

                if not draft_lines:
                    st.warning("AI草稿是空的。")
                else:
                    errors = validate_ai_draft_lines(draft_lines)

                    if errors:
                        st.error("AI草稿有問題，請先修正：")
                        for error in errors:
                            st.write(error)
                    else:
                        st.session_state["lines"].extend(draft_lines)
                        st.session_state["calculate_clicked"] = False
                        st.success("已把 AI 草稿加入組別。")
                        st.rerun()

        with clear_ai_col:
            if st.button("清空AI草稿", use_container_width=True):
                st.session_state["ai_draft_text"] = ""
                st.session_state["ai_draft_text_editor"] = ""
                st.rerun()


# ===== 新增一組 =====

st.subheader("➕ 新增一組")

active_group = st.radio(
    "編輯區",
    GROUP_KEYS,
    horizontal=True,
    key="active_group"
)

st.caption("填 1 區＝一般組合；填 2 區以上＝分區交叉。不同區不可重複同一號碼。")

st.markdown("### 快速選號")
render_number_pad(active_group)

if st.session_state["select_warning"]:
    st.warning(st.session_state["select_warning"])


# ===== 已選號碼 =====

st.markdown("### 已選號碼")

filled_groups = []

for group_name in GROUP_KEYS:
    text = selected_to_text(st.session_state[group_name])
    if text:
        filled_groups.append((group_name, text))

if not filled_groups:
    st.info("目前尚未選擇任何號碼。")
else:
    for group_name, text in filled_groups:
        group_col, clear_col = st.columns([5, 1], gap="small")

        with group_col:
            st.markdown(
                f"""
                <div class="selected-box">
                    <b>{group_name}</b><br>{text}
                </div>
                """,
                unsafe_allow_html=True
            )

        with clear_col:
            st.markdown('<div class="small-btn">', unsafe_allow_html=True)

            if st.button(f"清{group_name[0]}", key=f"clear_{group_name}", use_container_width=True):
                st.session_state[group_name] = []
                st.session_state["select_warning"] = ""
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)


# ===== 倍率 =====

if st.session_state.get("need_reset_multipliers", False):
    st.session_state["two_multiplier"] = 0.0
    st.session_state["three_multiplier"] = 0.0
    st.session_state["four_multiplier"] = 0.0
    st.session_state["car_multiplier"] = 0.0
    st.session_state["need_reset_multipliers"] = False

st.markdown("### 倍率")
st.caption("可手動輸入，也可直接點常用倍率。")

m1, m2, m3, m4 = st.columns(4, gap="small")

with m1:
    two_multiplier = render_multiplier_control("二星", "two_multiplier")

with m2:
    three_multiplier = render_multiplier_control("三星", "three_multiplier")

with m3:
    four_multiplier = render_multiplier_control("四星", "four_multiplier")

with m4:
    car_multiplier = render_multiplier_control("車", "car_multiplier")


# ===== 加入這組 =====

filled_group_texts = get_filled_group_texts()

st.markdown('<div class="main-btn">', unsafe_allow_html=True)
if st.button("加入這組", type="primary", use_container_width=True):
    if len(filled_group_texts) == 0:
        st.warning("至少要選擇一個區的號碼。")
    else:
        new_line = infer_line_from_groups(
            two_multiplier,
            three_multiplier,
            four_multiplier,
            car_multiplier
        )

        st.session_state["lines"].append(new_line)
        st.session_state["calculate_clicked"] = False
        clear_all_groups()
        reset_all_multipliers()
        st.session_state["select_warning"] = ""

        st.success("已加入這組")
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)


# ===== 單價設定 =====

st.subheader("💰 單價")
p1, p2, p3, p4 = st.columns(4, gap="small")

with p1:
    price_2 = st.number_input("二星每支", min_value=0.0, value=72.5, step=0.5)

with p2:
    price_3 = st.number_input("三星每支", min_value=0.0, value=63.5, step=0.5)

with p3:
    price_4 = st.number_input("四星每支", min_value=0.0, value=53.0, step=0.5)

with p4:
    price_car = st.number_input("車每支", min_value=0.0, value=1.0, step=0.5)


# ===== 已加入組別 =====

st.subheader("📝 已加入組別")

current_text = "\n".join(st.session_state["lines"])

edited_text = st.text_area(
    "組別清單",
    value=current_text,
    height=160,
    label_visibility="collapsed",
    placeholder="加入的組別會出現在這裡"
)

st.session_state["lines"] = [
    line.strip()
    for line in edited_text.split("\n")
    if line.strip()
]

b1, b2 = st.columns(2, gap="small")

with b1:
    if st.button("開始計算", type="primary", use_container_width=True):
        manual_errors = []

        if len(st.session_state["lines"]) == 0:
            manual_errors.append("請先加入至少一組號碼。")

        for line_index, line in enumerate(st.session_state["lines"], start=1):
            duplicates = manual_line_has_cross_duplicate(line)

            for num, first_group, second_group in duplicates:
                manual_errors.append(
                    f"第 {line_index} 組：{num:02d} 同時出現在第 {first_group} 區與第 {second_group} 區。"
                )

        if manual_errors:
            st.session_state["calculate_clicked"] = False
            st.error("請先修正以下問題：")
            for error in manual_errors:
                st.write(error)
        else:
            st.session_state["calculate_clicked"] = True
            save_current_calculation_to_redeem(
                st.session_state["lines"],
                price_2,
                price_3,
                price_4,
                price_car
            )
            st.success("已計算，並自動存入兌獎區。")

with b2:
    if st.button("清空全部", use_container_width=True):
        st.session_state["lines"] = []
        st.session_state["calculate_clicked"] = False
        clear_all_groups()
        reset_all_multipliers()
        st.session_state["select_warning"] = ""
        st.rerun()


# ===== 計算結果 =====

if st.session_state["calculate_clicked"]:
    lines = st.session_state["lines"]

    if len(lines) == 0:
        st.warning("請先加入至少一組號碼。")
    else:
        results, totals = calculate_results(lines, price_2, price_3, price_4, price_car)

        st.subheader("📊 總計")

        t1, t2 = st.columns(2, gap="small")

        with t1:
            st.metric("二星總支數", f"{format_num(totals['total_two_count'])} 支")
            st.metric("三星總支數", f"{format_num(totals['total_three_count'])} 支")
            st.metric("四星總支數", f"{format_num(totals['total_four_count'])} 支")
            st.metric("車總支數", f"{format_num(totals['total_car_count'])} 支")

        with t2:
            st.metric("二星金額", f"{format_num(totals['total_two_cost'])} 元")
            st.metric("三星金額", f"{format_num(totals['total_three_cost'])} 元")
            st.metric("四星金額", f"{format_num(totals['total_four_cost'])} 元")
            st.metric("車金額", f"{format_num(totals['total_car_cost'])} 元")

        st.metric("總金額", f"{format_num(totals['total_cost'])} 元")

        st.subheader("📋 詳細結果")
        st.dataframe(results, use_container_width=True, hide_index=True)

        warning_items = [
            item for item in results
            if item["重複號碼數"] > 0 or item["錯誤號碼"]
        ]

        if warning_items:
            st.warning("有些區塊出現重複號碼或錯誤號碼，請檢查詳細結果。")



# ===== 兌獎區 =====

st.subheader("🎁 兌獎區")
st.caption("每按一次『開始計算』會自動存成同一張票；車下注支數＝號碼數×倍率×38，車中獎支數＝命中號碼數×倍率×4。")

if len(st.session_state["redeem_tickets"]) == 0:
    st.info("目前兌獎區還沒有資料。請先按『開始計算』，系統會自動把計算內容存進來。")
else:
    st.markdown("#### 已儲存票券總表")
    st.dataframe(redeem_ticket_summary_rows(), use_container_width=True, hide_index=True)

    with st.expander("查看每一組明細", expanded=False):
        st.dataframe(redeem_ticket_detail_rows(), use_container_width=True, hide_index=True)

    draw_text = st.text_input(
        "輸入當期539開獎號碼",
        placeholder="例如：03 10 24 29 34",
        help="請輸入 5 個不重複的 01～39 號碼，可用空白、逗號、句點分隔。"
    )

    winning_numbers, invalid_numbers, duplicate_count = parse_winning_numbers(draw_text)

    if draw_text.strip():
        if invalid_numbers:
            st.error("開獎號碼只能輸入 01～39。錯誤號碼：" + "、".join(str(num) for num in invalid_numbers))
        elif duplicate_count > 0:
            st.error("開獎號碼不可重複，請重新輸入。")
        elif len(winning_numbers) != 5:
            st.warning(f"目前辨識到 {len(winning_numbers)} 個號碼，請輸入剛好 5 個開獎號碼。")
        else:
            st.success("開獎號碼：" + "、".join(f"{num:02d}" for num in winning_numbers))

            redeem_results = [
                calculate_redeem_result(ticket, winning_numbers)
                for ticket in st.session_state["redeem_tickets"]
            ]

            ticket_summary_results = redeem_result_summary_by_ticket(winning_numbers)

            total_two_hit = sum(item["二星中獎支數"] for item in ticket_summary_results)
            total_three_hit = sum(item["三星中獎支數"] for item in ticket_summary_results)
            total_four_hit = sum(item["四星中獎支數"] for item in ticket_summary_results)
            total_car_hit = sum(item["車中獎支數"] for item in ticket_summary_results)
            total_all_hit = sum(item["總中獎支數"] for item in ticket_summary_results)

            r1, r2 = st.columns(2, gap="small")

            with r1:
                st.metric("二星總中獎支數", f"{format_num(total_two_hit)} 支")
                st.metric("三星總中獎支數", f"{format_num(total_three_hit)} 支")

            with r2:
                st.metric("四星總中獎支數", f"{format_num(total_four_hit)} 支")
                st.metric("車總中獎支數", f"{format_num(total_car_hit)} 支")

            st.metric("全部總中獎支數", f"{format_num(total_all_hit)} 支")

            st.markdown("#### 每張中獎結果總表")
            st.dataframe(ticket_summary_results, use_container_width=True, hide_index=True)

            with st.expander("查看每一組中獎明細", expanded=False):
                st.dataframe(redeem_results, use_container_width=True, hide_index=True)

    clear_redeem_col, _ = st.columns([1, 2], gap="small")
    with clear_redeem_col:
        if st.button("清空兌獎區", use_container_width=True):
            st.session_state["redeem_tickets"] = []
            st.rerun()
