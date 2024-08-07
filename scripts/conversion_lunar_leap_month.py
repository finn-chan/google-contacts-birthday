import json
from collections import defaultdict


def read_lunar_leap_months(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    lunar_leap_data = defaultdict(list)
    month_map = {
        '正月': 1, '二月': 2, '三月': 3, '四月': 4, '五月': 5,
        '六月': 6, '七月': 7, '八月': 8, '九月': 9, '十月': 10,
        '冬月': 11, '腊月': 12
    }

    for line in lines:
        line = line.strip()
        if line:
            entries = line.split('，')
            for entry in entries:
                year_month = entry.split('年 闰')
                year = int(year_month[0].strip())
                leap_month = year_month[1].strip()
                month_number = month_map[leap_month]
                lunar_leap_data[month_number].append(year)

    for month in range(1, 13):
        if month not in lunar_leap_data:
            lunar_leap_data[month] = []

    sorted_lunar_leap_data = {k: sorted(v) for k, v in sorted(lunar_leap_data.items())}

    return sorted_lunar_leap_data


def convert_to_json(data):
    return json.dumps(data, ensure_ascii=False, indent=4)


def save_to_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(data)


if __name__ == "__main__":
    input_file_path = '../data/lunar_leap_month.txt'
    output_file_path = '../data/lunar_leap_month.json'

    lunar_leap_data = read_lunar_leap_months(input_file_path)
    lunar_leap_json = convert_to_json(lunar_leap_data)

    save_to_file(lunar_leap_json, output_file_path)

    all_years = set()
    for years in lunar_leap_data.values():
        all_years.update(years)

    total_years = len(all_years)
    print(f"一共有 {total_years} 个闰月")

    print(f"闰月数据已保存到 {output_file_path}")
