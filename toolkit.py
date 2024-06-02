##!/usr/bin/env python
# coding=utf-8
"""
    @File           : toolkit.py
    @Version        : 1.0.0
    @Date           : 2024-05-28
    @Author         : Jin
    @Description    : 工具包
"""


import yaml


def read_yaml_config():
    with open(file="config.yaml", encoding="utf8") as f:
        config = yaml.load(stream=f, Loader=yaml.FullLoader)
    return config


CONFIG = read_yaml_config()

if __name__ == "__main__":
    print(CONFIG)
