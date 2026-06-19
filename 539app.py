import streamlit as st
import math
import re

st.set_page_config(
    page_title="539 快速計算器",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 539 快速計算器")

st.write("每一行代表一區號碼，可以在最後加倍率，例如：`01 02 03 11 16 32 35 38 *0.1`")

col1, col2, col3 = st.columns(3)

with col1:
    price_2 = st.number_input("二星每組金額", min_value=0.0, value=10.0, step=1.0)

with col2:
    price_3 = st.number_input("三星每組金額", min_value=0.0, value=10.0, step=1.0)

with col3:
    price_4 = st.number_input("四星每組金額", min_value=0.0, value=10.0, step=1.0)


default_text = """01 02 03 11 16 32 35 38 *0.1
02 18 36 06 03 04 07 31 *1
05 14 27 06 19 26 38 *0.5"""

input_text = st.text_area(
    "輸入號碼",
    value=default_text,
    height=220
)


def combination(n, r):
    if n < r:
        return 0
    return math.comb(n, r)


def parse_line(line):
    two_multiplier = 0.0
    three_multiplier = 0.0
    four_multiplier = 0.0

    # 找二星倍率，例如：二x0.1、2x0.1、二X1、2×1
    two_match = re.search(r"(二|2)\s*[xX×]\s*(\d+(\.\d+)?)", line)
    if two_match:
        two_multiplier = float(two_match.group(2))
        line = line.replace(two_match.group(0), "")

    # 找三星倍率，例如：三x1、3x1
    three_match = re.search(r"(三|3)\s*[xX×]\s*(\d+(\.\d+)?)", line)
    if three_match:
        three_multiplier = float(three_match.group(2))
        line = line.replace(three_match.group(0), "")

    # 找四星倍率，例如：四x0.5、4x0.5
    four_match = re.search(r"(四|4)\s*[xX×]\s*(\d+(\.\d+)?)", line)
    if four_match:
        four_multiplier = float(four_match.group(2))
        line = line.replace(four_match.group(0), "")

    # 剩下的數字才當作號碼
    number_matches = re.findall(r"\d{1,2}", line)

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

    return {
        "numbers": unique_numbers,
        "two_multiplier": two_multiplier,
        "three_multiplier": three_multiplier,
        "four_multiplier": four_multiplier,
        "invalid_numbers": invalid_numbers,
        "duplicate_count": duplicate_count
    }

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
        two_multiplier = parsed["two_multiplier"]
        three_multiplier = parsed["three_multiplier"]
        four_multiplier = parsed["four_multiplier"]


        n = len(numbers)

        two_base = combination(n, 2)
        three_base = combination(n, 3)
        four_base = combination(n, 4)

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
            "號碼": "、".join(f"{num:02d}" for num in numbers),
            "號碼數": n,
            "二星倍率": two_multiplier,
            "三星倍率": three_multiplier,
            "四星倍率": four_multiplier,
            "二星組數": two_actual,
            "三星組數": three_actual,
            "四星組數": four_actual,
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
        st.metric("二星總組數", f"{total_two_count:g}")
        st.metric("二星金額", f"{total_two_cost:g} 元")

    with c2:
        st.metric("三星總組數", f"{total_three_count:g}")
        st.metric("三星金額", f"{total_three_cost:g} 元")

    with c3:
        st.metric("四星總組數", f"{total_four_count:g}")
        st.metric("四星金額", f"{total_four_cost:g} 元")

    with c4:
        st.metric("總金額", f"{total_cost:g} 元")

    st.subheader("詳細結果")
    st.dataframe(results, use_container_width=True)

    warning_items = [
        item for item in results
        if item["重複號碼數"] > 0 or item["錯誤號碼"]
    ]

    if warning_items:
        st.warning("有些區塊出現重複號碼或錯誤號碼，請檢查詳細結果。")
