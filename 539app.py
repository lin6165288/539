import streamlit as st
import math
import re
import itertools

st.set_page_config(
    page_title="539 快速計算器",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 539 快速計算器")

st.write("""
每一行代表一組號碼。

支援兩種格式：

1. 一般組合：
`01 02 03 11 16 32 35 38 二x0.1 三x0 四x0`

2. 分區交叉：
`02 18 36 06 | 03 04 07 31 二x1 三x0 四x0`

3. 多區交叉：
`07 14 21 36 | 17 20 23 38 | 13 24 27 37 29 二x0.1 三x0.1 四x0`
""")

uploaded_file = st.file_uploader(
    "上傳彩券照片（目前先顯示照片）",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    st.image(uploaded_file, caption="已上傳的照片", use_container_width=True)

col1, col2, col3 = st.columns(3)

with col1:
    price_2 = st.number_input("二星每支金額", min_value=0.0, value=10.0, step=1.0)

with col2:
    price_3 = st.number_input("三星每支金額", min_value=0.0, value=10.0, step=1.0)

with col3:
    price_4 = st.number_input("四星每支金額", min_value=0.0, value=10.0, step=1.0)


default_text = """01 02 03 11 16 32 35 38 二x0.1 三x0 四x0
02 18 36 06 | 03 04 07 31 二x1 三x0 四x0
07 14 21 36 | 17 20 23 38 | 13 24 27 37 29 二x0.1 三x0.1 四x0
01 19 二x4 三x0 四x0"""

if "input_text" not in st.session_state:
    st.session_state["input_text"] = default_text

input_text = st.text_area(
    "輸入號碼",
    key="input_text",
    height=300
)


def combination(n, r):
    if n < r:
        return 0
    return math.comb(n, r)


def format_num(value):
    if abs(value - round(value)) < 0.0000001:
        return str(int(round(value)))
    return f"{value:.2f}"


def parse_multiplier(line, star_patterns):
    pattern = r"(" + "|".join(star_patterns) + r")\s*[xX×]\s*(\d+(\.\d+)?)"
    match = re.search(pattern, line)

    if match:
        multiplier = float(match.group(2))
        line = line.replace(match.group(0), "")
        return multiplier, line

    return 0.0, line


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
    分區交叉計算：
    二星：任選 2 區，各取 1 個號碼，相乘後加總
    三星：任選 3 區，各取 1 個號碼，相乘後加總
    四星：任選 4 區，各取 1 個號碼，相乘後加總
    """
    if len(groups) < star:
        return 0

    total = 0

    for selected_groups in itertools.combinations(groups, star):
        count = 1

        for group in selected_groups:
            count *= len(group)

        total += count

    return total


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

    else:
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


def group_display(groups):
    if not groups:
        return ""

    display_parts = []

    for group in groups:
        display_parts.append("、".join(f"{num:02d}" for num in group))

    return "  ×  ".join(display_parts)


if st.button("開始計算", type="primary"):
    lines = [
        line.strip()
        for line in input_text.split("\n")
        if line.strip()
    ]

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

    total_cost = total_two_cost + total_three_cost + total_four_cost

    st.subheader("總計")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("二星總支數", f"{format_num(total_two_count)} 支")
        st.metric("二星金額", f"{format_num(total_two_cost)} 元")

    with c2:
        st.metric("三星總支數", f"{format_num(total_three_count)} 支")
        st.metric("三星金額", f"{format_num(total_three_cost)} 元")

    with c3:
        st.metric("四星總支數", f"{format_num(total_four_count)} 支")
        st.metric("四星金額", f"{format_num(total_four_cost)} 元")

    with c4:
        st.metric("總金額", f"{format_num(total_cost)} 元")

    st.subheader("詳細結果")
    st.dataframe(results, use_container_width=True)

    warning_items = [
        item for item in results
        if item["重複號碼數"] > 0 or item["錯誤號碼"]
    ]

    if warning_items:
        st.warning("有些區塊出現重複號碼或錯誤號碼，請檢查詳細結果。")
