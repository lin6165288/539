import streamlit as st
import math
import re
import itertools
import base64

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

    /* 強制 Streamlit columns 在手機不要直排 */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 0.16rem !important;
    }

    div[data-testid="column"] {
        min-width: 0 !important;
        flex: 1 1 0 !important;
        padding-left: 0.02rem !important;
        padding-right: 0.02rem !important;
    }

    .num-btn button {
        height: 1.75rem !important;
        min-height: 1.75rem !important;
        font-size: 0.68rem !important;
        padding: 0 !important;
        border-radius: 7px !important;
    }

    @media (max-width: 390px) {
        .num-btn button {
            height: 1.65rem !important;
            min-height: 1.65rem !important;
            font-size: 0.64rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🎯 539 快速計算器")
st.caption("照片參考＋快速選號＋自動計算")


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


def line_from_form(a, b, c, d, two_m, three_m, four_m, mode):
    groups_raw = [a.strip(), b.strip(), c.strip(), d.strip()]
    groups_raw = [g for g in groups_raw if g]

    if mode == "一般組合":
        all_text = " ".join(groups_raw)
        return f"{all_text} 二x{two_m:g} 三x{three_m:g} 四x{four_m:g}"

    return f"{' | '.join(groups_raw)} 二x{two_m:g} 三x{three_m:g} 四x{four_m:g}"


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

    two_multiplier, line = parse_multiplier(line, ["二", "2"])
    three_multiplier, line = parse_multiplier(line, ["三", "3"])
    four_multiplier, line = parse_multiplier(line, ["四", "4"])

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
        "invalid_numbers": invalid_numbers,
        "duplicate_count": duplicate_count
    }


def calculate_results(lines, price_2, price_3, price_4):
    results = []

    total_two_count = 0
    total_three_count = 0
    total_four_count = 0

    total_two_cost = 0
    total_three_cost = 0
    total_four_cost = 0

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

        two_multiplier = parsed["two_multiplier"]
        three_multiplier = parsed["three_multiplier"]
        four_multiplier = parsed["four_multiplier"]

        two_actual = two_base * two_multiplier
        three_actual = three_base * three_multiplier
        four_actual = four_base * four_multiplier

        two_cost = two_actual * price_2
        three_cost = three_actual * price_3
        four_cost = four_actual * price_4

        total_two_count += two_actual
        total_three_count += three_actual
        total_four_count += four_actual

        total_two_cost += two_cost
        total_three_cost += three_cost
        total_four_cost += four_cost

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
            "二星原始支數": two_base,
            "三星原始支數": three_base,
            "四星原始支數": four_base,
            "二星實際支數": two_actual,
            "三星實際支數": three_actual,
            "四星實際支數": four_actual,
            "二星金額": two_cost,
            "三星金額": three_cost,
            "四星金額": four_cost,
            "小計": two_cost + three_cost + four_cost,
            "重複號碼數": parsed["duplicate_count"],
            "錯誤號碼": "、".join(str(num) for num in parsed["invalid_numbers"])
        })

    totals = {
        "total_two_count": total_two_count,
        "total_three_count": total_three_count,
        "total_four_count": total_four_count,
        "total_two_cost": total_two_cost,
        "total_three_cost": total_three_cost,
        "total_four_cost": total_four_cost,
        "total_cost": total_two_cost + total_three_cost + total_four_cost
    }

    return results, totals


def add_or_remove_number(group_key, num):
    if num in st.session_state[group_key]:
        st.session_state[group_key].remove(num)
    else:
        st.session_state[group_key].append(num)


def render_number_pad(group_key):
    numbers = list(range(1, 40))

    # 每排 6 顆，手機比較緊湊
    for row_start in range(0, 39, 6):
        row_nums = numbers[row_start:row_start + 6]
        cols = st.columns(6, gap="small")

        for i, num in enumerate(row_nums):
            selected = num in st.session_state[group_key]
            label = f"✓{num:02d}" if selected else f"{num:02d}"

            with cols[i]:
                st.markdown('<div class="num-btn">', unsafe_allow_html=True)

                if st.button(label, key=f"{group_key}_{num}", use_container_width=True):
                    add_or_remove_number(group_key, num)
                    st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)


# ===== Session State =====

if "lines" not in st.session_state:
    st.session_state["lines"] = []

if "calculate_clicked" not in st.session_state:
    st.session_state["calculate_clicked"] = False

if "active_group" not in st.session_state:
    st.session_state["active_group"] = "A區"

for key in ["A區", "B區", "C區", "D區"]:
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
            ["小", "中", "大"],
            horizontal=True,
            index=0,
            label_visibility="collapsed"
        )

        height_map = {
            "小": "120px",
            "中": "180px",
            "大": "260px"
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


# ===== 新增一組 =====

st.subheader("➕ 新增一組")

top1, top2 = st.columns(2, gap="small")

with top1:
    mode = st.radio(
        "模式",
        ["一般組合", "分區交叉"],
        horizontal=True
    )

with top2:
    active_group = st.radio(
        "編輯區",
        ["A區", "B區", "C區", "D區"],
        horizontal=True,
        key="active_group"
    )

st.caption("點號碼可選取 / 再點一次可取消")

st.markdown("### 快速選號")
render_number_pad(active_group)


# ===== 已選號碼 =====

st.markdown("### 已選號碼")

s1, s2 = st.columns(2, gap="small")

with s1:
    for group_name in ["A區", "B區"]:
        text = selected_to_text(st.session_state[group_name])
        if not text:
            text = "尚未選擇"

        st.markdown(
            f"""
            <div class="selected-box">
                <b>{group_name}</b><br>{text}
            </div>
            """,
            unsafe_allow_html=True
        )

with s2:
    for group_name in ["C區", "D區"]:
        text = selected_to_text(st.session_state[group_name])
        if not text:
            text = "尚未選擇"

        st.markdown(
            f"""
            <div class="selected-box">
                <b>{group_name}</b><br>{text}
            </div>
            """,
            unsafe_allow_html=True
        )

c1, c2, c3, c4 = st.columns(4, gap="small")

with c1:
    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
    if st.button("清A", use_container_width=True):
        st.session_state["A區"] = []
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
    if st.button("清B", use_container_width=True):
        st.session_state["B區"] = []
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
    if st.button("清C", use_container_width=True):
        st.session_state["C區"] = []
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="small-btn">', unsafe_allow_html=True)
    if st.button("清D", use_container_width=True):
        st.session_state["D區"] = []
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ===== 倍率 =====

st.markdown("### 倍率")
m1, m2, m3 = st.columns(3, gap="small")

with m1:
    two_multiplier = st.number_input("二星", min_value=0.0, value=0.0, step=0.1, format="%.1f")

with m2:
    three_multiplier = st.number_input("三星", min_value=0.0, value=0.0, step=0.1, format="%.1f")

with m3:
    four_multiplier = st.number_input("四星", min_value=0.0, value=0.0, step=0.1, format="%.1f")


# ===== 加入這組 =====

a_group = selected_to_text(st.session_state["A區"])
b_group = selected_to_text(st.session_state["B區"])
c_group = selected_to_text(st.session_state["C區"])
d_group = selected_to_text(st.session_state["D區"])

st.markdown('<div class="main-btn">', unsafe_allow_html=True)
if st.button("加入這組", type="primary", use_container_width=True):
    if not a_group:
        st.warning("至少要選擇 A區號碼。")
    else:
        new_line = line_from_form(
            a_group,
            b_group,
            c_group,
            d_group,
            two_multiplier,
            three_multiplier,
            four_multiplier,
            mode
        )

        st.session_state["lines"].append(new_line)
        st.session_state["calculate_clicked"] = False
        st.session_state["A區"] = []
        st.session_state["B區"] = []
        st.session_state["C區"] = []
        st.session_state["D區"] = []

        st.success("已加入這組")
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)


# ===== 單價設定 =====

st.subheader("💰 單價")
p1, p2, p3 = st.columns(3, gap="small")

with p1:
    price_2 = st.number_input("二星每支", min_value=0.0, value=10.0, step=1.0)

with p2:
    price_3 = st.number_input("三星每支", min_value=0.0, value=10.0, step=1.0)

with p3:
    price_4 = st.number_input("四星每支", min_value=0.0, value=10.0, step=1.0)


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
        st.session_state["calculate_clicked"] = True

with b2:
    if st.button("清空全部", use_container_width=True):
        st.session_state["lines"] = []
        st.session_state["calculate_clicked"] = False
        st.session_state["A區"] = []
        st.session_state["B區"] = []
        st.session_state["C區"] = []
        st.session_state["D區"] = []
        st.rerun()


# ===== 計算結果 =====

if st.session_state["calculate_clicked"]:
    lines = st.session_state["lines"]

    if len(lines) == 0:
        st.warning("請先加入至少一組號碼。")
    else:
        results, totals = calculate_results(lines, price_2, price_3, price_4)

        st.subheader("📊 總計")

        t1, t2 = st.columns(2, gap="small")

        with t1:
            st.metric("二星總支數", f"{format_num(totals['total_two_count'])} 支")
            st.metric("三星總支數", f"{format_num(totals['total_three_count'])} 支")
            st.metric("四星總支數", f"{format_num(totals['total_four_count'])} 支")

        with t2:
            st.metric("二星金額", f"{format_num(totals['total_two_cost'])} 元")
            st.metric("三星金額", f"{format_num(totals['total_three_cost'])} 元")
            st.metric("四星金額", f"{format_num(totals['total_four_cost'])} 元")

        st.metric("總金額", f"{format_num(totals['total_cost'])} 元")

        st.subheader("📋 詳細結果")
        st.dataframe(results, use_container_width=True, hide_index=True)

        warning_items = [
            item for item in results
            if item["重複號碼數"] > 0 or item["錯誤號碼"]
        ]

        if warning_items:
            st.warning("有些區塊出現重複號碼或錯誤號碼，請檢查詳細結果。")
