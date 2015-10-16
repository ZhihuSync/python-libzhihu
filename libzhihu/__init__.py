#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os
from core import Question, People


def sync(path=""):
    pass

def update():
    pass

def init():
	# 初始化 数据目录
	env = os.environ
	home_path = os.path.join(env['HOME'], ".zhihu")
	if not os.path.exists( home_path ) or not os.path.isdir(home_path):
		os.mkdir(home_path)


if __name__ == '__main__':
	init()