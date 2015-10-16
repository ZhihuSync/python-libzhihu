#!/usr/bin/env python
#-*- coding:utf-8 -*-

import libzhihu
from libzhihu.core import Question, People

def test_question():
    token = "35564122"
    q = Question(token=token)
    q.pull()
    q.parse()

def test_people():
    token = "rio"
    p = People(token=token)
    p.pull()
    p.parse()

def test():
    # test_question()
    test_people()

if __name__ == '__main__':
    test()