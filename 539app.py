import streamlit as st
import math
import re
import itertools
import base64
import time
from io import BytesIO

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


def parse_line(line):
    original_line = line
    line = expand_combined_star_multipliers(line)

    two_multiplier, line = parse_multiplier(line, ["二", "2"])
    three_multiplier, line = parse_multiplier(line, ["三", "3"])
    four_multiplier, line = parse_multiplier(line, ["四", "4"])
    car_multiplier, line = parse_multiplier(line, ["車"])

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




def expand_combined_star_multipliers(text):
    """
    將「二三x0.1」這種簡寫展開成「二x0.1 三x0.1」。
    例如：
    二三x0.1 => 二x0.1 三x0.1
    二三四x0.2 => 二x0.2 三x0.2 四x0.2
    23x0.1 => 二x0.1 三x0.1
    """
    if not text:
        return ""

    star_map = {
        "二": "二",
        "三": "三",
        "四": "四",
        "2": "二",
        "3": "三",
        "4": "四",
    }

    def repl(match):
        stars_raw = match.group(1)
        value = match.group(2)
        expanded = []

        for ch in stars_raw:
            if ch in star_map:
                star = star_map[ch]
                if star not in expanded:
                    expanded.append(star)

        return " ".join(f"{star}x{value}" for star in expanded)

    # 支援：二三x0.1、二 三x0.1、二、三x0.1、23x0.1、2 3x0.1
    pattern = r"((?:[二三四234][\s、,，]*){2,4})\s*[xX×]\s*(\d+(?:\.\d+)?)"
    return re.sub(pattern, repl, text)

def normalize_ai_draft_text(text):
    """把 AI 回傳整理成 app 可解析的草稿格式。"""
    if not text:
        return ""

    text = text.strip()
    text = text.replace("```text", "").replace("```", "")
    text = text.replace("×", "x").replace("X", "x")
    text = text.replace("，", " ").replace("、", " ").replace(",", " ")
    text = text.replace("；", "\n").replace(";", "\n")
    text = expand_combined_star_multipliers(text)

    cleaned_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


AI_CROP_AREAS = {
    "整張": (0.00, 0.00, 1.00, 1.00),
    "左上": (0.00, 0.00, 0.40, 0.38),
    "上方": (0.25, 0.00, 0.75, 0.38),
    "右上": (0.60, 0.00, 1.00, 0.38),
    "左中": (0.00, 0.28, 0.42, 0.72),
    "中間": (0.25, 0.25, 0.78, 0.75),
    "右中": (0.58, 0.25, 1.00, 0.78),
    "左下": (0.00, 0.62, 0.45, 1.00),
    "下方": (0.20, 0.60, 0.80, 1.00),
    "右下": (0.55, 0.60, 1.00, 1.00),
}


def crop_uploaded_image(uploaded_file, crop_area_name):
    """依照使用者選擇的照片區域裁切，回傳裁切後 bytes 與 mime_type。"""
    try:
        from PIL import Image
    except Exception:
        return uploaded_file.getvalue(), uploaded_file.type or "image/jpeg", "找不到 Pillow，暫時改用整張圖片辨識。"

    image_bytes = uploaded_file.getvalue()
    mime_type = uploaded_file.type or "image/jpeg"

    if crop_area_name not in AI_CROP_AREAS or crop_area_name == "整張":
        return image_bytes, mime_type, ""

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    width, height = image.size
    left_p, top_p, right_p, bottom_p = AI_CROP_AREAS[crop_area_name]

    left = int(width * left_p)
    top = int(height * top_p)
    right = int(width * right_p)
    bottom = int(height * bottom_p)

    cropped = image.crop((left, top, right, bottom))

    output = BytesIO()
    cropped.save(output, format="JPEG", quality=95)
    return output.getvalue(), "image/jpeg", ""


def recognize_lottery_image_with_gemini(image_bytes, mime_type="image/jpeg", crop_area_name="整張"):
    """使用 Gemini API 辨識圖片，輸出可人工核對的文字草稿。"""
    try:
        from google import genai
        from google.genai import types
    except Exception:
        return "", "找不到 google-genai 套件，請確認 requirements.txt 已加入 google-genai，並重新部署。"

    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        api_key = ""

    if not api_key:
        return "", "找不到 GEMINI_API_KEY，請確認 Streamlit Secrets 已設定。"

    prompt = f"""
你正在辨識台灣539手寫彩券草稿。

重要：這次只辨識圖片中的「{crop_area_name}」這一塊，不要推測照片其他區域。
如果這一塊裡有多個彼此分開、上下左右不連續的下注區塊，請分成多行；但最多輸出 5 行。

請只輸出可供程式解析的文字，不要解釋，不要加表格，不要加項目符號。

輸出規則：
1. 每一組一行。
2. 每一行都要先標示你判斷它在照片中的大約位置，格式固定為：位置 => 內容
3. 位置只能使用下列詞之一：左上、上方、中上、右上、左中、中間、右中、左下、下方、右下、位置不確定。
4. 不要使用第1、第2、1、2、①、② 等編號，避免程式誤判成號碼。
5. 號碼一律輸出兩位數，例如 1 要寫成 01。
6. 一般組合格式：
   上方 => 01 02 03 04 05 二x1 三x0 四x0 車x0
7. 分區交叉格式：
   中間 => 01 02 03 | 04 05 06 | 07 08 二x0.1 三x0.1 四x0 車x0
8. 如果看到 X、x、×、括號、三欄排列、或明顯分成多群號碼，請用 | 分隔不同群。不要把直欄與橫排硬混在一起。
9. 如果一個下注區塊旁邊寫的是「二三x0.1」或「==x0.1」，通常代表二星與三星都 x0.1，請輸出成：二x0.1 三x0.1 四x0 車x0。
10. 如果圖片寫「二三四x0.1」，代表「二x0.1 三x0.1 四x0.1」。
11. 如果只看到「=x1」且沒有看到二、三、四，通常先判斷為二x1 三x0 四x0 車x0；如果旁邊有三條等號或寫三，才判斷三星。
12. 如果某個星別沒有看到倍率，請補成 0，例如 二x0 三x0 四x0 車x0。
13. 看不清楚的數字請用 ?，不要猜。
14. 寧可少輸出，也不要把不同下注區塊混在同一行。
15. 不要輸出任何說明文字。
""".strip()

    last_error = ""

    for attempt, wait_seconds in enumerate([0, 2, 5], start=1):
        if wait_seconds:
            time.sleep(wait_seconds)

        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
            )

            ai_text = getattr(response, "text", "") or ""
            ai_text = normalize_ai_draft_text(ai_text)

            if not ai_text:
                return "", "AI 沒有回傳可用文字，請換一張更清楚的照片或重新拍攝。"

            return ai_text, ""

        except Exception as e:
            last_error = str(e)
            if "503" not in last_error and "UNAVAILABLE" not in last_error.upper():
                break

    return "", f"Gemini 辨識失敗：{last_error}"

def ai_draft_lines_have_errors(lines):
    errors = []

    for line_index, line in enumerate(lines, start=1):
        if "?" in line:
            errors.append(f"AI草稿第 {line_index} 行有 ?，代表 AI 看不清楚，請先手動修正。")

        parsed = parse_line(line)

        if parsed["invalid_numbers"]:
            errors.append(
                f"AI草稿第 {line_index} 行有錯誤號碼：" +
                "、".join(str(num) for num in parsed["invalid_numbers"])
            )

        duplicates = manual_line_has_cross_duplicate(line)
        for num, first_group, second_group in duplicates:
            errors.append(
                f"AI草稿第 {line_index} 行：{num:02d} 同時出現在第 {first_group} 區與第 {second_group} 區。"
            )

    return errors


AI_LOCATION_WORDS = [
    "左上", "上方", "中上", "右上",
    "左中", "中間", "右中",
    "左下", "下方", "右下", "位置不確定"
]


def split_ai_location_and_content(line):
    """將 AI 草稿拆成「照片位置」與「可加入組別的內容」。"""
    line = (line or "").strip()
    line = re.sub(r"^[\-\*\s]+", "", line)

    default_location = "位置不確定"

    for separator in ["=>", "＝>", "→", "：", ":"]:
        if separator in line:
            left, right = line.split(separator, 1)
            left = left.strip()
            right = right.strip()

            # 位置欄不能有阿拉伯數字，避免「第1筆」被當成號碼
            if not re.search(r"\d", left):
                for word in AI_LOCATION_WORDS:
                    if word in left:
                        return word, right

    return default_location, line


def build_ai_review_rows(ai_text):
    rows = []

    for raw_line in ai_text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        location, content = split_ai_location_and_content(raw_line)
        rows.append({
            "加入": True,
            "照片位置": location,
            "草稿內容": content,
            "檢查提示": summarize_ai_review_line(content),
        })

    return rows


def summarize_ai_review_line(line):
    if not line.strip():
        return "空白"

    warnings = []

    if "?" in line:
        warnings.append("有?待修正")

    parsed = parse_line(line)

    if parsed["invalid_numbers"]:
        warnings.append("有錯誤號碼")

    duplicates = manual_line_has_cross_duplicate(line)
    if duplicates:
        warnings.append("跨區重複")

    mode = parsed["mode"]
    number_count = len(parsed["numbers"])
    multipliers = (
        f"二{parsed['two_multiplier']:g} "
        f"三{parsed['three_multiplier']:g} "
        f"四{parsed['four_multiplier']:g} "
        f"車{parsed['car_multiplier']:g}"
    )

    if warnings:
        return f"⚠️ {'、'.join(warnings)}｜{mode}｜{number_count}碼｜{multipliers}"

    return f"✅ {mode}｜{number_count}碼｜{multipliers}"


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
    st.caption("建議不要整張辨識。請先選一小塊區域，AI 只產生草稿，你再人工核對後加入。")

    if uploaded_file is None:
        st.info("請先在上方『照片參考』上傳圖片。")
    else:
        st.warning("手寫整張辨識容易把上下左右搞混。建議一次只辨識一小區，例如左上、中間、右下。")

        ai_area = st.selectbox(
            "選擇AI要辨識的照片區域",
            list(AI_CROP_AREAS.keys()),
            index=0,
            help="如果整張照片很複雜，請不要選整張，改選左上、上方、右上等局部區域。"
        )

        cropped_bytes, cropped_mime_type, crop_warning = crop_uploaded_image(uploaded_file, ai_area)

        if crop_warning:
            st.warning(crop_warning)

        with st.expander("預覽AI實際辨識範圍", expanded=True):
            st.image(cropped_bytes, caption=f"AI 只會看這一塊：{ai_area}", use_container_width=True)

        if st.button("AI辨識這個區域", use_container_width=True):
            with st.spinner("AI 辨識中，請稍等... 如果遇到忙線會自動重試。"):
                ai_text, ai_error = recognize_lottery_image_with_gemini(
                    cropped_bytes,
                    cropped_mime_type,
                    ai_area
                )

            if ai_error:
                st.error(ai_error)
            else:
                old_text = st.session_state.get("ai_draft_text", "").strip()
                if old_text:
                    st.session_state["ai_draft_text"] = old_text + "\n" + ai_text
                else:
                    st.session_state["ai_draft_text"] = ai_text
                st.success("AI 已產生草稿，請在下方表格逐筆核對。")
                st.rerun()

    ai_review_rows = build_ai_review_rows(st.session_state.get("ai_draft_text", ""))

    if not ai_review_rows:
        st.info("AI辨識後，草稿會整理成表格出現在這裡。")
    else:
        st.markdown("#### AI核對表")
        st.caption("請主要核對『草稿內容』。不想加入的那筆，把『加入』取消勾選；看錯的地方可以直接在表格內修改。")

        edited_ai_rows = st.data_editor(
            ai_review_rows,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "加入": st.column_config.CheckboxColumn("加入", help="勾選後才會加入組別", default=True),
                "照片位置": st.column_config.TextColumn("照片位置", disabled=True, width="small"),
                "草稿內容": st.column_config.TextColumn(
                    "草稿內容",
                    help="可以直接修改號碼、分區與倍率",
                    width="large"
                ),
                "檢查提示": st.column_config.TextColumn("檢查提示", disabled=True, width="medium"),
            },
            key="ai_review_editor"
        )

        with st.expander("查看 / 編輯原始多行草稿", expanded=False):
            ai_draft_text = st.text_area(
                "原始AI草稿",
                value=st.session_state.get("ai_draft_text", ""),
                height=160,
                label_visibility="collapsed",
                placeholder="AI辨識結果會出現在這裡。"
            )

            update_raw_col, _ = st.columns([1, 2], gap="small")
            with update_raw_col:
                if st.button("更新核對表", use_container_width=True):
                    st.session_state["ai_draft_text"] = ai_draft_text
                    st.rerun()

        add_ai_col, clear_ai_col = st.columns(2, gap="small")

        with add_ai_col:
            if st.button("加入已勾選草稿", use_container_width=True):
                selected_lines = []

                for row in edited_ai_rows:
                    if row.get("加入"):
                        content = str(row.get("草稿內容", "")).strip()
                        if content:
                            selected_lines.append(content)

                if not selected_lines:
                    st.warning("請至少勾選一筆草稿。")
                else:
                    draft_errors = ai_draft_lines_have_errors(selected_lines)

                    if draft_errors:
                        st.error("AI草稿還有問題，請先修正：")
                        for error in draft_errors:
                            st.write(error)
                    else:
                        st.session_state["lines"].extend(selected_lines)
                        st.success("已把勾選的 AI 草稿加入組別，請在『已加入組別』再檢查一次。")
                        st.rerun()

        with clear_ai_col:
            if st.button("清空AI草稿", use_container_width=True):
                st.session_state["ai_draft_text"] = ""
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
