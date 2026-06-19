import streamlit as st
import math
import re
import itertools

st.set_page_config(
    page_title="539 快速計算器",
    page_icon="🎯",
    layout="wide"
)

# ===== 手機版樣式 =====
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 900px;
    }

    .stButton > button {
        width: 100%;
        height: 3rem;
        font-size: 1.05rem;
        border-radius: 12px;
        font-weight: 600;
    }

    .stTextInput input {
        font-size: 1.05rem;
        height: 3rem;
    }

    .stNumberInput input {
        font-size: 1.05rem;
        height: 3rem;
    }

    textarea {
        font-size: 1rem !important;
        line-height: 1.5 !important;
    }

    div[data-testid="stMetric"] {
        background-color: #fff7ed;
        padding: 12px;
        border-radius: 14px;
        border: 1px solid #fed7aa;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.9rem;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.25rem;
    }

    @media (max-width: 768px) {
        h1 {
            font-size: 1.55rem !important;
        }

        h2, h3 {
            font-size: 1.15rem !important;
        }

        .stRadio > div {
            gap: 0.5rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🎯 539 快速計算器")
st.caption("上傳照片當參考，手動輸入分區與倍率，系統自動計算支數與金額。")


# ===== 工具函式 =====

def combination(n, r):
    if n < r:
        return 0
    return math.comb(n, r)


def format_num(value):
    if abs(value - round(value)) < 0.0000001:
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
    """
    分區交叉計算，且同一支內同號要排除。

    二星：任選 2 區，各取 1 個號碼
    三星：任選 3 區，各取 1 個號碼
    四星：任選 4 區，各取 1 個號碼

    若同一支裡出現重複號碼，該支不計算。
    """
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

    display_parts = []
    for group in groups:
        display_parts.append("、".join(f"{num:02d}" for num in group))

    return "  ×  ".join(display_parts)


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


# ===== Session State =====

if "lines" not in st.session_state:
    st.session_state["lines"] = []

if "calculate_clicked" not in st.session_state:
    st.session_state["calculate_clicked"] = False


# ===== 照片區 =====

with st.expander("📷 照片參考", expanded=True):
    uploaded_file = st.file_uploader(
        "上傳彩券照片",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file is not None:
        st.image(uploaded_file, caption="已上傳的照片", use_container_width=True)


# ===== 新增一組 =====

st.subheader("➕ 新增一組")

with st.form("add_group_form", clear_on_submit=True):
    mode = st.radio(
        "計算模式",
        ["一般組合", "分區交叉"],
        horizontal=True
    )

    st.caption("一般組合：全部號碼一起算。分區交叉：A區 × B區 × C區，且同號自動排除。")

    a_group = st.text_input("A區號碼", placeholder="例如：02 18 36 06")
    b_group = st.text_input("B區號碼", placeholder="例如：03 04 07 31")
    c_group = st.text_input("C區號碼", placeholder="例如：13 24 27 37 29")
    d_group = st.text_input("D區號碼", placeholder="可空白")

    m1, m2, m3 = st.columns(3)

    with m1:
        two_multiplier = st.number_input(
            "二星",
            min_value=0.0,
            value=0.0,
            step=0.1,
            format="%.1f"
        )

    with m2:
        three_multiplier = st.number_input(
            "三星",
            min_value=0.0,
            value=0.0,
            step=0.1,
            format="%.1f"
        )

    with m3:
        four_multiplier = st.number_input(
            "四星",
            min_value=0.0,
            value=0.0,
            step=0.1,
            format="%.1f"
        )

    submitted = st.form_submit_button("加入這組")

    if submitted:
        if not a_group.strip():
            st.warning("至少要輸入 A區號碼。")
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
            st.success("已加入這組。")


# ===== 單價設定 =====

st.divider()
st.subheader("💰 單價設定")

p1, p2, p3 = st.columns(3)

with p1:
    price_2 = st.number_input(
        "二星每支金額",
        min_value=0.0,
        value=10.0,
        step=1.0
    )

with p2:
    price_3 = st.number_input(
        "三星每支金額",
        min_value=0.0,
        value=10.0,
        step=1.0
    )

with p3:
    price_4 = st.number_input(
        "四星每支金額",
        min_value=0.0,
        value=10.0,
        step=1.0
    )


# ===== 已加入組別 =====

st.divider()
st.subheader("📝 目前已加入的組別")

if len(st.session_state["lines"]) == 0:
    st.info("目前還沒有加入任何組別。")
else:
    st.caption("可以直接在下面修改文字。分區交叉用 | 分隔。")

current_text = "\n".join(st.session_state["lines"])

edited_text = st.text_area(
    "組別清單",
    value=current_text,
    height=240,
    placeholder="加入的組別會出現在這裡"
)

st.session_state["lines"] = [
    line.strip()
    for line in edited_text.split("\n")
    if line.strip()
]

btn_col1, btn_col2 = st.columns(2)

with btn_col1:
    if st.button("開始計算", type="primary"):
        st.session_state["calculate_clicked"] = True

with btn_col2:
    if st.button("清空全部"):
        st.session_state["lines"] = []
        st.session_state["calculate_clicked"] = False
        st.rerun()


# ===== 計算結果 =====

if st.session_state["calculate_clicked"]:
    lines = st.session_state["lines"]

    if len(lines) == 0:
        st.warning("請先加入至少一組號碼。")
    else:
        results, totals = calculate_results(lines, price_2, price_3, price_4)

        st.divider()
        st.subheader("📊 總計")

        c1, c2 = st.columns(2)

        with c1:
            st.metric("二星總支數", f"{format_num(totals['total_two_count'])} 支")
            st.metric("三星總支數", f"{format_num(totals['total_three_count'])} 支")
            st.metric("四星總支數", f"{format_num(totals['total_four_count'])} 支")

        with c2:
            st.metric("二星金額", f"{format_num(totals['total_two_cost'])} 元")
            st.metric("三星金額", f"{format_num(totals['total_three_cost'])} 元")
            st.metric("四星金額", f"{format_num(totals['total_four_cost'])} 元")

        st.metric("總金額", f"{format_num(totals['total_cost'])} 元")

        st.subheader("📋 詳細結果")

        st.dataframe(
            results,
            use_container_width=True,
            hide_index=True
        )

        warning_items = [
            item for item in results
            if item["重複號碼數"] > 0 or item["錯誤號碼"]
        ]

        if warning_items:
            st.warning("有些區塊出現重複號碼或錯誤號碼，請檢查詳細結果。")
