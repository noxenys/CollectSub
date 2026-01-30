# -*- coding: utf-8 -*-

import sys

import os

import datetime

from loguru import logger

sub_path = 'sub' #默认存放订阅源的文件夹名称

sub_all_yaml = os.path.join(sub_path, 'sub_all.yaml')

today = datetime.datetime.today()

path_year = os.path.join(sub_path, str(today.year))

path_mon = os.path.join(path_year, str(today.month))

path_yaml = os.path.join(path_mon, f'{today.month}-{today.day}.yaml')

@logger.catch

def pre_check():

    os.makedirs(path_mon, exist_ok=True)

    logger.info('初始化完成')

    return path_yaml

@logger.catch

def get_sub_all():

    return sub_all_yaml

# pre_check()
