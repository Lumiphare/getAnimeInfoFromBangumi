import os
import time
import requests
import re
import threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor,as_completed

BASE_URL = "https://age.wpcoder.cn"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": BASE_URL
}
lines_idx = 1
lock = threading.Lock()

session = requests.Session()
session.headers.update(HEADERS)

user_input_url = ""

from urllib.parse import urlparse, parse_qs, urlunparse, urlencode


def generate_list_url(page):
    """智能生成分页地址"""
    # 解析基础 URL 结构
    parsed = urlparse(user_input_url)

    # 解析查询参数
    query_dict = parse_qs(parsed.query)

    # 更新页码参数（自动覆盖原有 page 参数）
    query_dict["page"] = [str(page)]  # 保持参数为列表形式

    # 重组 URL 对象
    new_query = urlencode(query_dict, doseq=True)
    new_parsed = parsed._replace(query=new_query)

    return urlunparse(new_parsed)

def sanitize_filename(name):
    """清理文件名中的非法字符"""
    # 保留中文、日文、英文等常见字符
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def get_soup(url):
    try:
        response = session.get(url, timeout=10)
        response.encoding = 'utf-8'  # 强制使用UTF-8解码
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.Timeout:
        print(f"请求超时 {url}")
        return None
    except Exception as e:
        print(f"请求失败 {url}: {str(e)}")
        return None


def safe_download(url, save_folder, filename_prefix):
    """安全的文件下载函数"""
    try:
        # 修复URL协议问题
        full_url = urljoin("https://", url) if url.startswith("//") else url

        # 生成合法文件名
        filename = f"{sanitize_filename(filename_prefix)}.jpg"
        save_path = os.path.join(save_folder, filename)

        if os.path.exists(save_path):
            # print(f"文件已存在: {filename}")
            return

        response = session.get(full_url, stream=True, timeout=10)

        if response.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            # print(f"下载成功: {filename}")
        else:
            print(f"下载失败 {response.status_code}: {full_url}")
    except Exception as e:
        print(f"下载出错: {str(e)}")


def process_character_page(character_url, anime_name, char_name):
    """处理角色详情页面"""
    soup = get_soup(character_url)
    if not soup:
        return

    # 获取角色海报
    if char_poster := soup.select_one('div.infobox div[align="center"] a.cover img'):
        safe_download(
            url=char_poster["src"],
            save_folder=os.path.join(f"posters", anime_name),
            filename_prefix=f"{char_name}"
        )

def process_anime_page(anime_url, needImage):
    # anime_id = anime_url.split("/")[-1]
    soup = get_soup(anime_url)
    if not soup:
        print("请求超时或url错误")
        return

    if chinese_name_li := soup.select_one('#infobox > li:first-of-type'):
        full_text = chinese_name_li.get_text(strip=True)
        prefix = chinese_name_li.find('span', class_='tip').get_text(strip=True)
        anime_name = full_text.replace(prefix, '').strip()
    else:
        print("未找到匹配的<li>标签")
        return

    print(f"\n处理动画: {anime_name}")

    global lines_idx
    line = f"{lines_idx}\t{anime_name}\t"
    local_lines_idx = lines_idx
    with lock:
        lines_idx += 1

    if needImage:
        if main_poster := soup.select_one('div.infobox div[align="center"] a.thickbox.cover'):
            safe_download(
                url=main_poster.get('href'),
                save_folder=f"posters//{anime_name}",
                filename_prefix=f"{anime_name}"
            )

    # 处理前4个角色
    characters = soup.select('ul#browserItemList li.user')[:4]
    with ThreadPoolExecutor(max_workers=2) as executor:
        for idx, char in enumerate(characters, 1):
            if char_link := char.select_one('a.avatar.l[href^="/character/"]'):
                # 正确解码中文名称
                raw_name = char_link.get("title", "")
                char_name = raw_name.split(" / ")[1] if " / " in raw_name and len(
                    raw_name.split(" / ")) > 1 else raw_name
                line += raw_name + '\t'
                # print(f"处理角色 {idx}: {raw_name}")  # 控制台应正确显示中文

                char_url = urljoin(BASE_URL, char_link["href"])
                if needImage:
                    executor.submit(
                        process_character_page,
                        char_url,
                        anime_name,
                        char_name
                    )
                    time.sleep(0.5)

    return local_lines_idx, line

def get_anime_links(nums):
    page = 1
    unique_links = []
    for _ in range((nums - 1) // 24 + 1):
        soup = get_soup(generate_list_url(page))
        if not soup:
            continue

        # 精准选择器 + 去重
        anime_items = soup.select('li.item h3 > a.l[href^="/subject/"]')

        for a in anime_items:
            href = a["href"]
            unique_links.append(href)

        page += 1

    print(f"有效动画链接数: {len(unique_links)}")
    return [urljoin(BASE_URL, href) for href in unique_links][:nums]

def handle_user_input():
    user_input = input("请输入你要获取的动画数量（默认50）： ")
    nums = 50 if user_input == "" else int(user_input)
    global user_input_url
    while True:
        default_url = f"{BASE_URL}/anime/browser/airtime/2024?sort=collects"
        url = input(f"请输入 bangumi 排行榜网址（默认 {default_url}）: ").strip()

        # 处理空输入
        if not url:
            url = default_url

        # 验证域名
        parsed = urlparse(url)
        if parsed.netloc != urlparse(BASE_URL).netloc:
            print(f"请输入 {BASE_URL} 域名下的正确网址")
            continue

        # 处理 page 参数
        query = parse_qs(parsed.query)
        if 'page' not in query:
            # 自动追加 page 参数
            query['page'] = ['1']  # 设置为第一页
            new_query = urlencode(query, doseq=True)
            parsed = parsed._replace(query=new_query)
            user_input_url = urlunparse(parsed)
        else:
            user_input_url = url
        break
    needImage = False if input("是否需要角色和动画海报 (y / n)? 默认y ") == "n" else True

    return nums, needImage

def main():
    nums, needImage = handle_user_input()
    print("开始处理， 正在获取动画列表。。。")
    anime_links = get_anime_links(nums)
    print(f"获取成功，即将处理 {len(anime_links)} 个动画")
    lines = [""] * nums

    with ThreadPoolExecutor(max_workers=10) as executor:  # 调整 max_workers 根据需要
        future_to_url = {executor.submit(process_anime_page, link, needImage): link for link in anime_links}

        for i, future in enumerate(as_completed(future_to_url), 1):
            link = future_to_url[future]
            try:
                result = future.result()
                if result == None:
                    continue
                lines[result[0] - 1] = result[1]
                print(f"\n进度: {i}/{len(anime_links)}")
            except Exception as exc:
                print(f'\n进度: {i}/{len(anime_links)} - 链接 {link} 产生了一个异常: {exc}')

    # 测试示例
    # test_url = "https://age.wpcoder.cn/subject/424883"
    # process_anime_page(test_url)

    output_path = 'output.txt'
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write("序号\t动画名\t角色1\t角色2\t角色3\t角色4\n")  # 写入表头
        for line in lines:
            file.write(line + "\n")  # 写入每一行并换行

if __name__ == "__main__":
    main()