##!/usr/bin/env python
# coding=utf-8
"""
    @File           : main.py
    @Version        : 1.0.0
    @Date           : 2024-05-28
    @Author         : Jin
    @Description    : 主程序
"""

import json
import re
import requests
from toolkit import CONFIG
from string import Template
from pathlib import Path


def get_tx_local_barrage_data() -> list:
    """读取本地腾讯json弹幕数据，掉使用

    Returns:
        list: tx弹幕数据
    """
    with open(file="FeHelper1270.json", encoding="utf8") as f:
        tx_barrage_data = json.load(fp=f)
    return tx_barrage_data["barrage_list"]


def create_ass_file(file_name: str = "tmp.ass") -> str:
    """通过ass字幕模板创建ass文件

    Args:
        file_name (str, optional): 字幕文件名字. Defaults to "tmp.ass".

    Returns:
        str: 字幕文件名字
    """
    # file_name = "xx1270-8.ass"
    with open(file="ass_template.ass", encoding="utf8") as f:
        file_data = f.read()
    with open(file=file_name, mode="w", encoding="utf8") as f:
        f.write(file_data)
    return file_name


def format_time(ms: int) -> str:
    """格式化时间

    Args:
        ms (int): 毫秒

    Returns:
        str: 格式化后的时间：0:00:23.97
    """
    # 毫秒整除 得出 小时
    format_h = ms // 3600000
    # 毫秒求余 得出 剩余时间 ms
    ms = ms % 3600000
    # 毫秒整除 得出 分钟
    format_m = ms // 60000
    # 毫秒求余 得出 剩余时间 ms
    ms = ms % 60000
    # 毫秒整除 得出 秒
    format_s = ms // 1000
    # 毫秒求余 得出 剩余时间 ms 再整除 10 保留 2位数
    format_ms = ms % 1000 // 10
    # {format_h:02d}：宽度不足的时候使用 0 填充 ，宽度是 2 整数
    return f"{format_h}:{format_m:02d}:{format_s:02d}.{format_ms}"


def write_ass_data_v2(barrage_links_data: list, file_name: str) -> None:
    """写入ass字幕数据

    Args:
        barrage_links_data (list): 视频弹幕链接信息 [{"url": 弹幕链接, "barrage_requests_max_time": 链接请求的最大时长time_offect}]
        file_name (str): 文件名字
    """
    # 弹幕轨道时间信息
    barrage_line_time_offect_info: dict = {
        i: {
            "tx_time_offect": -1,
            "now_time_offect": 0,
        }
        for i in range(CONFIG["barrage_line_num"])
    }
    # 计算每个弹幕轨道的 y 位置
    barrage_line_start_y: dict = {
        i: (CONFIG["barrage_height_from_top"] + i *
            (CONFIG["barrage_line_height"] + CONFIG["barrage_line_interval"]))
        for i in range(CONFIG["barrage_line_num"])
    }
    # print(barrage_line_time_offect_info)
    # ass字幕行模板
    subtitle_line_template = Template(CONFIG["subtitle_line_template"])
    # 当前轨道
    barrage_line_num_now = 0
    # 创建ass字幕文件
    file_name = create_ass_file(file_name=file_name)
    # TODO 优化下方代码结构？
    with open(file=file_name, mode="a+", encoding="utf8") as f:
        # % 进度条 初始化
        barrage_total_nums = len(barrage_links_data)
        barrage_deal_index = 0
        # 左对齐 4 位宽度 不换行 最大 100% 刚好是4个宽度
        print(f'{barrage_deal_index/barrage_total_nums:<4.0%}', end="")
        # 通过生成器 get_tx_barrage_datas 去请求 弹幕数据
        # TODO 弹幕数据为空的时候可能存在bug
        for tx_barrage_data_dict, barrage_requests_max_time in get_tx_barrage_datas(
                barrage_links_data=barrage_links_data):
            for tx_barrage_data in tx_barrage_data_dict['barrage_list']:
                # 字符串转为整形
                tx_barrage_data["time_offset"] = int(
                    tx_barrage_data["time_offset"])

                # 开始时间大于弹幕的最大时间，进入下一次迭代
                if barrage_line_time_offect_info[barrage_line_num_now][
                        "now_time_offect"] > barrage_requests_max_time:
                    # print("跳过：超过最大时间")
                    continue

                # 如果开启过滤广告位置弹幕，执行下方代码
                if CONFIG["tx_ad_filter"]["status"]:
                    continue_flag = False
                    for ad_start_time, ad_end_time, _ in CONFIG[
                            "tx_ad_filter"]["ad_times"]:
                        if tx_barrage_data[
                                "time_offset"] >= ad_start_time and tx_barrage_data[
                                    "time_offset"] <= ad_end_time:
                            continue_flag = True
                    # 广告位置的弹幕跳过，进行下一次循环
                    if continue_flag:
                        # print(f'跳过：广告位置: {tx_barrage_data["time_offset"]}')
                        continue
                    # 不是广告位置弹幕，如果前面已经跳过了广告，弹幕的实际时间需要修正
                    ad_duration_total_time = 0  # 已播放广告时间 毫秒
                    for _, ad_end_time, ad_duration_time in CONFIG[
                            "tx_ad_filter"]["ad_times"]:
                        if tx_barrage_data["time_offset"] > ad_end_time:
                            ad_duration_total_time += ad_duration_time
                    # 修正没有广告的时间
                    tx_barrage_data["time_offset"] -= ad_duration_total_time

                # 每个弹幕轨道同样的时间只拿一条数据，出现重复数据的时候进入下一次迭代，这里由于同样的时间拿了一条数据更新了now_time_offect，所以同样的时间time_offset会小于新的now_time_offect
                if tx_barrage_data[
                        "time_offset"] < barrage_line_time_offect_info[
                            barrage_line_num_now]["now_time_offect"]:
                    # print("跳过：当前时间轨道已存在数据")
                    continue

                # 弹幕开始时间
                barrage_start_time_ms = tx_barrage_data["time_offset"]
                # 弹幕结束时间
                barrage_end_time_ms = tx_barrage_data["time_offset"] + CONFIG[
                    "barrage_duration_time"]
                # 更新下一次 弹幕轨道 时间信息
                barrage_line_time_offect_info[barrage_line_num_now][
                    "tx_time_offect"] = tx_barrage_data["time_offset"]
                barrage_line_time_offect_info[barrage_line_num_now][
                    "now_time_offect"] = tx_barrage_data[
                        "time_offset"] + CONFIG["barrage_delay_time"]
                # 字幕模板使用数据格式化
                subtitle_line_data = {
                    "barrage_start_time": format_time(barrage_start_time_ms),
                    "barrage_end_time": format_time(barrage_end_time_ms),
                    "barrage_start_y":
                    barrage_line_start_y[barrage_line_num_now],
                    "barrage_content": tx_barrage_data["content"]
                }
                # 更新字幕模板
                subtitle_line = subtitle_line_template.substitute(
                    subtitle_line_data)
                # 写入文件
                f.write(subtitle_line)
                # 追加换行
                f.write("\n")
                # 改变弹幕轨道
                barrage_line_num_now += 1
                # 达到弹幕最大轨道的时候 重置 为 第一条弹幕轨道 （使用0开始计数）
                if barrage_line_num_now == CONFIG["barrage_line_num"]:
                    barrage_line_num_now = 0
            # 进度条修改，使用退格键 \b 删除 4个宽度 最大 100% 刚好是4个宽度
            barrage_deal_index += 1
            print("\b" * 4 + f'{barrage_deal_index/barrage_total_nums:<4.0%}',
                  end="")
    # 换行
    print("")


def get_tx_video_debug_info() -> None:
    """调式用，把腾讯视频链接请求信息写到本地
    """
    # url = "https://v.qq.com/x/cover/mzc002006ldp6dl/w4100lzpu3h.html"  # 电影 第二十一条
    # url = "https://v.qq.com/x/cover/mzc002002kqssyu/u4100vc3n8u.html"  # 剧集 庆余年 后面集数
    url = "https://v.qq.com/x/cover/mzc00200as5tv65/n4100z9tmaf.html"  # 综艺 五哈
    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    res = requests.get(url=url, headers=headers)
    if res.status_code != 200:
        return
    # pat = re.compile(pattern=rf'"vid":"{vid}","lid":.*?,"duration":(\d+?),')
    # match_obj = pat.search(res.text)
    with open(file="tmp_show.html", mode="w", encoding="utf8") as f:
        f.write(res.text)
    # if match_obj:
    #     # print(match_obj.groups())
    #     video_long_time_senonds = int(match_obj.group(1))
    #     print("视频时长提取成功")
    #     return video_long_time_senonds


def get_tx_video_info(tx_video_play_link: str,
                      write_flag: bool = False) -> dict | None:
    """解析腾讯播放链接，获取相关 电影 剧集 综艺 所有 播放信息

    Args:
        tx_video_play_link (str): 腾讯视频播放链接
        write_flag (bool, optional): 是否把信息写到本地tmp_tx_video_info.json中. Defaults to False.

    Returns:
        dict | None: 电影 剧集 综艺 所有 播放信息（id是vid）
        {
            "u4100vc3n8u": {
                "title": "31",
                "fullTitle": "庆余年第二季 第31集",
                "vid": "u4100vc3n8u",
                "duration": 2815,
                "play_link": "https://v.qq.com/x/cover/mzc002002kqssyu/u4100vc3n8u.html"
            }
        }
    """
    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    res = requests.get(url=tx_video_play_link, headers=headers)
    if res.status_code != 200:
        return

    # 视频信息匹配正则
    pat = re.compile(
        pattern=
        r'"title":"(.{,20}?)","vid":"(\w+?)","lid":.*?,"duration":(\d+?),"playTitle":".+?","fullTitle":"(.+?)",'
    )

    # 提取视频链接url路径
    video_play_url_tmp = ""
    url_match_obj = re.match(pattern=r'(https://v.qq.com.+/)\w+?.html',
                             string=tx_video_play_link)
    if url_match_obj:
        video_play_url_tmp = url_match_obj.group(1)

    video_info_dict: dict = {}
    for title, vid, duration, fullTitle in pat.findall(res.text):
        duration = int(duration)
        # 有重复数据的时候 去重
        if vid in video_info_dict:
            continue
        # 过滤指定内容
        if CONFIG["tx_video_filter"]["status"]:
            # 过滤标题含指定内容的视频 如 预告
            if CONFIG["tx_video_filter"]["title_filter"] in fullTitle:
                continue
            # 过滤时长小于 指定 秒数 的视频
            if duration < CONFIG["tx_video_filter"]["time_filter"]:
                continue
        video_info_dict[vid] = {
            "title": title,
            "fullTitle": fullTitle,
            "vid": vid,
            "duration": duration,
            "play_link": f'{video_play_url_tmp}{vid}.html'
        }
    # 写入本地文件
    if write_flag:
        with open("tmp_tx_video_info.json", mode="w", encoding="utf8") as f:
            json.dump(obj=video_info_dict, fp=f, ensure_ascii=False)
    return video_info_dict


def generate_barrage_links_data(vid: str,
                                video_long_time_senonds: int) -> list:
    """根据视频时长 生成切割后的弹幕的链接

    Args:
        vid (str): 视频id
        video_long_time_senonds (int): 视频时长 单位 秒

    Returns:
        list: [{"url": 弹幕链接, "barrage_requests_max_time": 链接请求的最大时长time_offect}]
    """
    # 秒转毫秒
    video_long_time_ms = video_long_time_senonds * 1000
    barrage_links = []
    start_time_offect = 0
    # tx弹幕接口切割偏移数量
    offect = 30000
    while start_time_offect < video_long_time_ms:
        url = f"https://dm.video.qq.com/barrage/segment/{vid}/t/v1/{start_time_offect}/{start_time_offect + offect}"
        start_time_offect += offect
        # 添加这个弹幕链接的最大时间
        barrage_links.append({
            "url": url,
            "barrage_requests_max_time": start_time_offect
        })
    return barrage_links


def get_tx_barrage_datas(barrage_links_data: list) -> list | None:
    """通过链接请求视频弹幕数据，这是一个生成器，避免一次全部请求完所有数据导致内存过大

    Args:
        barrage_links_data (list): 视频弹幕链接信息, [{"url": 弹幕链接, "barrage_requests_max_time": 链接请求的最大时长time_offect}]

    Returns:
        list | None: [接口响应的弹幕数据, barrage_requests_max_time 链接请求的最大时长time_offect]

    Yields:
        Iterator[list | None]: [接口响应的弹幕数据, barrage_requests_max_time 链接请求的最大时长time_offect]
    """
    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    for barrage_link_data in barrage_links_data:
        res = requests.get(url=barrage_link_data["url"], headers=headers)
        # print(barrage_link_data["url"])
        if res.status_code == 200:
            # print("弹幕数据获取成功")
            yield [res.json(), barrage_link_data["barrage_requests_max_time"]]


def generate_menu_option_list(tx_video_info: dict) -> list:
    """打印可下载视频选项列表，并返回对应列表数据

    Args:
        tx_video_info (dict): 电影 剧集 综艺 所有 播放信息（id是vid）
        {
            "u4100vc3n8u": {
                "title": "31",
                "fullTitle": "庆余年第二季 第31集",
                "vid": "u4100vc3n8u",
                "duration": 2815,
                "play_link": "https://v.qq.com/x/cover/mzc002002kqssyu/u4100vc3n8u.html"
            }
        }
    Returns:
        list: 所有视频信息列表
        [
            {'title': '33',
            'fullTitle': '庆余年第二季 第33集',
            'vid': 'l4100k56pve',
            'duration': 2795,
            'play_link': 'https://v.qq.com/x/cover/mzc002002kqssyu/l4100k56pve.html'}
        ]
    """
    index = 0
    video_info_option_list: list = []

    print("=" * 30)
    print("选项id\t视频标题\t视频时长(分钟)")
    print("-" * 30)
    for video_info in tx_video_info.values():
        print(
            f'{index}\t{video_info["fullTitle"]}\t{video_info["duration"]/60:.2f} min'
        )
        video_info_option_list.append(video_info)
        index += 1
    print("=" * 30 + "\n")
    return video_info_option_list


def generate_ass_file(tx_video_info: dict, ass_data_floder: str) -> None:
    """生成ass字幕文件

    Args:
        tx_video_info (dict): 视频信息
        ass_data_floder (str): 字幕文件存储文件夹
        {
            'title': '33',
            'fullTitle': '庆余年第二季 第33集',
            'vid': 'l4100k56pve',
            'duration': 2795,
            'play_link': 'https://v.qq.com/x/cover/mzc002002kqssyu/l4100k56pve.html'
        }
    """

    # 字幕文件名
    file_name = f'{ass_data_floder}{tx_video_info["fullTitle"]}.ass'
    # 生成视频链接信息
    barrage_links_data = generate_barrage_links_data(
        vid=tx_video_info["vid"],
        video_long_time_senonds=tx_video_info["duration"])
    # 生成ass字幕文件
    write_ass_data_v2(barrage_links_data=barrage_links_data,
                      file_name=file_name)


def main() -> None:
    url = input("请输入腾讯视频播放链接:\n")
    # 校验视频链接
    if not re.match(pattern=r'https://v.qq.com.+/\w+?.html$', string=url):
        print("I001: 腾讯视频播放链接有误，请检查！")
        return
    tx_video_info_dict: dict = get_tx_video_info(tx_video_play_link=url,
                                                 write_flag=False)
    if not tx_video_info_dict:
        print("I002: 没有获取到相关腾讯视频信息，请检查！")

    video_info_option_list: list = generate_menu_option_list(
        tx_video_info=tx_video_info_dict)
    select_options = input("请输入要下载的视频[选项id] (多个选项使用 空格 隔开, 如:1 2):\n")
    # 校验用户输入的选项
    verify_select_options = []  # 校验之后的选项
    for option_id in select_options.split():
        try:
            option_id = int(option_id)
            video_info_option_list[option_id]
            verify_select_options.append(option_id)
        except (ValueError, IndexError):
            print(f'W001: {option_id} 选项有误, 不处理')
    # 字幕文件存储相对路径
    ass_data_floder = "./AssData/"
    # 文件夹不存在创建文件夹
    p = Path(ass_data_floder)
    if not p.exists():
        p.mkdir()
    # 开始下载对应视频字幕
    for option_id in verify_select_options:
        print(f'开始下载弹幕: {video_info_option_list[option_id]["fullTitle"]}')
        generate_ass_file(tx_video_info=video_info_option_list[option_id],
                          ass_data_floder=ass_data_floder)


if __name__ == "__main__":
    # url = "https://v.qq.com/x/cover/mzc002006ldp6dl/w4100lzpu3h.html"  # 电影 第二十一条
    # url = "https://v.qq.com/x/cover/mzc002002kqssyu/u4100vc3n8u.html"  # 剧集 庆余年 后面集数
    # url = "https://v.qq.com/x/cover/mzc00200as5tv65/n4100z9tmaf.html"  # 综艺 五哈
    # a = get_tx_video_info(tx_video_play_link=url, write_flag=False)
    # b = generate_menu_option_list(a)
    # print(b)
    main()
