#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Build-in / Std
import os, sys, time, platform, random
import re, json, cookielib

# requirements
import requests, termcolor, html2text
try:
    from bs4 import BeautifulSoup
except:
    import BeautifulSoup

# module
from auth import islogin
from auth import Logging

"""
    Note:
        1. 身份验证由 `auth.py` 完成。
        2. 身份信息保存在当前目录的 `.cookies` 文件中。
        3. `requests` 对象可以直接使用，身份信息已经自动加载。
"""
requests = requests.Session()
requests.cookies = cookielib.LWPCookieJar('.cookies')
try:
    requests.cookies.load(ignore_discard=True)
except:
    Logging.error(u"你还没有登录知乎哦 ...")
    Logging.info(u"执行 `python auth.py` 即可以完成登录。")
    raise Exception("无权限(403)")


class People:
    """
        people:
            name
            domain
            avatar
            profile
                location
                    name
                sex
                job
                    industry
                    organization
                    job
                education
                    organization
                    major
                SNS
                about
            detail:
                chengjiu
                    agree, thx, favor, share
                zhiyejingli

            questions

            answers

            articles

            favors

            edit

            forces
            follows

    """
    def __init__(self, token=None):
        self.token = token
        self.id    = 0
        self.hash_id = ""
        self.xsrf  = ""
        self.html  = ""
    def pull(self):
        url = "http://www.zhihu.com/people/%s/about" %( self.token )
        r = requests.get(url)
        if r.status_code != 200:
            raise IOError("network error.")
        self.html = r.content
        try:
            self.xsrf = re.compile(r"input\stype.*?name=.\_xsrf.\svalue=.(\w+).", re.DOTALL).findall(self.html)[0]
        except Exception as e:
            Logging.error(u"XSRF值提取失败")
            Logging.debug(e)
    def sync(self):
        pass
    def _fetch_followees(self, total):
        # 获取 该用户关注的人
        # http://www.zhihu.com/people/leng-zhe/followees
        url = "http://www.zhihu.com/node/ProfileFolloweesListV2"
        """
            HTTP POST:
                method:next
                params:{"offset":20,"order_by":"created","hash_id":"06f3b1c891d0d504eea8af883150b497"}
                _xsrf:f11a7023d52d5a0ec95914ecff30885f

            <div class="zm-profile-card zm-profile-section-item zg-clear no-hovercard"> 
                <div class="zg-right"> 
                    <button 
                        data-follow="m:button" 
                        data-id="dfadd95bc7af994cc8933c444cc9327e" 
                        class="zg-btn zg-btn-follow zm-rich-follow-btn small nth-0">
                            关注
                    </button> 
                </div>
                <a title="黄云忠" data-tip="p$t$huangdoc" class="zm-item-link-avatar" href="/people/huangdoc">
                    <img src="https://pic2.zhimg.com/b7dde5a21_m.jpg" class="zm-item-img-avatar">
                </a>
                <div class="zm-list-content-medium">
                    <h2 class="zm-list-content-title">
                        <a data-tip="p$t$huangdoc" href="http://www.zhihu.com/people/huangdoc" class="zg-link" title="黄云忠">黄云忠</a>
                    </h2>
                    <div class="zg-big-gray">风险投资人</div>
                    <div class="details zg-gray"> 
                        <a target="_blank" href="/people/huangdoc/followers" class="zg-link-gray-normal">4846 关注者</a> / 
                        <a target="_blank" href="/people/huangdoc/asks" class="zg-link-gray-normal">17 提问</a> / 
                        <a target="_blank" href="/people/huangdoc/answers" class="zg-link-gray-normal">23 回答</a> / 
                        <a target="_blank" href="/people/huangdoc" class="zg-link-gray-normal">8 赞同</a> 
                    </div> 
                </div> 
            </div>
        """
        offset = 0
        followees = []
        while offset<total:
            params = {"offset": offset, "order_by": "created", "hash_id": self.hash_id}
            data = {"method": "next", "params": json.dumps(params), "_xsrf": self.xsrf }

            Logging.info(u"获取该用户关注者: %s " % json.dumps(data))

            r = requests.post(url, data=data)
            if r.status_code != 200:
                raise IOError("network error.")
            try:
                res = json.loads(r.content)
                if res['r'] == 0 and type(res['msg']) == type([]):
                    result = res['msg']
                else:
                    result = []
            except Exception as e:
                Logging.error(u"数据格式解析失败")
                Logging.debug(e)
                result = []
            for p in result:
                r = re.compile(r"\/people/(\S+)\"|\'", re.DOTALL).findall(p)
                if len(r) > 0:
                    followees.append(r[0])
                else:
                    Logging.warn(u"提取用户token失败")
                    Logging.warn(p)
            offset += len(result)
        return followees

    def _fetch_followers(self, total):
        # 获取 关注该用户的人
        # http://www.zhihu.com/people/leng-zhe/followers
        url = "http://www.zhihu.com/node/ProfileFollowersListV2"
        """
            HTTP POST:
                method:next
                params:{"offset":20,"order_by":"created","hash_id":"06f3b1c891d0d504eea8af883150b497"}
                _xsrf:f11a7023d52d5a0ec95914ecff30885f
            <div class="zm-profile-card zm-profile-section-item zg-clear no-hovercard">
                <div class="zg-right">
                    <button 
                        data-follow="m:button" data-id="0c8c2a7a2bf0e05c9853c9a6377b7455" 
                        class="zg-btn zg-btn-follow zm-rich-follow-btn small nth-0">
                            关注
                    </button>
                </div>
                <a title="andy" data-tip="p$t$andy-49-88" class="zm-item-link-avatar" href="/people/andy-49-88">
                    <img src="https://pic1.zhimg.com/da8e974dc_m.jpg" class="zm-item-img-avatar">
                </a>
                <div class="zm-list-content-medium"> 
                    <h2 class="zm-list-content-title">
                        <a data-tip="p$t$andy-49-88" href="http://www.zhihu.com/people/andy-49-88" class="zg-link" title="andy">andy</a>
                    </h2>
                    <div class="zg-big-gray"></div>
                    <div class="details zg-gray">
                        <a target="_blank" href="/people/andy-49-88/followers" class="zg-link-gray-normal">0 关注者</a> / 
                        <a target="_blank" href="/people/andy-49-88/asks" class="zg-link-gray-normal">0 提问</a> / 
                        <a target="_blank" href="/people/andy-49-88/answers" class="zg-link-gray-normal">0 回答</a> / 
                        <a target="_blank" href="/people/andy-49-88" class="zg-link-gray-normal">0 赞同</a> 
                    </div> 
                </div>
            </div>
        """
        offset = 0
        followers = []
        while offset<total:
            params = {"offset": offset, "order_by": "created", "hash_id": self.hash_id}
            data = {"method": "next", "params": json.dumps(params), "_xsrf": self.xsrf }

            Logging.info(u"获取关注该用户的人: %s " % json.dumps(data))

            r = requests.post(url, data=data)
            if r.status_code != 200:
                raise IOError("network error.")
            try:
                res = json.loads(r.content)
                if res['r'] == 0 and type(res['msg']) == type([]):
                    result = res['msg']
                else:
                    result = []
            except Exception as e:
                Logging.error(u"数据格式解析失败")
                Logging.debug(e)
                result = []
            for p in result:
                r = re.compile(r"\/people/(\S+)\"|\'", re.DOTALL).findall(p)
                if len(r) > 0:
                    followers.append(r[0])
                else:
                    Logging.warn(u"提取用户token失败")
                    Logging.warn(p)
            offset += len(result)
        return followers
    def _fetch_followed_by_columns(self, total):
        # 获取该用户关注的专栏
        # http://www.zhihu.com/people/leng-zhe/columns/followed
        url = "http://www.zhihu.com/node/ProfileFollowedColumnsListV2"
        """
            HTTP POST
                method:next
                params:{"offset":20,"limit":20,"hash_id":"cfd6c460ccfe5e87a75a5410bbf0ae65"}
                _xsrf:f11a7023d52d5a0ec95914ecff30885f
        """
    def _fetch_posts(self, total):
        # 获取该用户的专栏文章
        pass
    def _fetch_topics(self, total):
        # 获取该用户关注的话题
        url = "http://www.zhihu.com/people/%s/topics" % (self.token)
        """
            HTTP POST:
                start:0
                offset:20
                _xsrf:f11a7023d52d5a0ec95914ecff30885f
        """

    def _fetch_asks(self, total):
        # 获取该用户的提问
        # total: 总页数
        url = "http://www.zhihu.com/people/%s/asks" % (self.token)
        params = {"page": 1}
        """
            HTTP GET(page):
                分页

        """
    def _fetch_answers(self, total):
        # 获取该用户的 回答列表
        # 该接口采取的是分页方式, total: 总页数
        url = "http://www.zhihu.com/people/%s/answers" %(self.token)
        params = {"page": 1}
        "HTTP GET"

    def _fetch_collections(self, total):
        # 获取该用户的收藏列表
        # total: 总页数
        url = "http://www.zhihu.com/people/%s/collections" % (self.token)
        params = {"page": 1}
        """
            HTTP GET
        """
        
    def _fetch_logs(self, total):
        # 获取该用户 参与的 公共编辑
        pass
    def parse(self):
        DOM = BeautifulSoup(self.html, 'html.parser')
        el = DOM.find("div", class_="zm-profile-header")
        elem = el.find("div", class_="title-section")
        # Name, Bio ( 一句话介绍自己？ )
        name = elem.find("a", class_="name").get_text()
        name = re.sub("^\n+|\n+$", "", name)
        bio = elem.find("span", class_="bio").get_text()
        bio = re.sub("^\n+|\n+$", "", bio)
        # SNS Info ( Weibo | QQ | ... )
        sns = {"weibo": ""}
        wb_el = el.find("div", class_="top").find("div", class_="weibo-wrap")
        try:
            sns['weibo'] = wb_el.find("a", class_="zm-profile-header-user-weibo")['href']
        except:
            pass
        # avatar
        avatar = el.find("div", class_="body").find("img", class_="avatar")['src']
        # descp
        descp = el.find("div", class_="body").find("span", class_="description").find("span", class_="content").get_text()
        descp = re.sub("^\n+|\n+$", "", descp)

        # Hash ID
        try:
            self.hash_id = DOM.find("div", class_="zm-profile-header-op-btns").find("button")['data-id']
        except:
            self.hash_id = ""


        f_el = DOM.find("div", class_="zm-profile-side-following").find_all("strong")
        if len(f_el) < 2:
            followees_num = 0
            followers_num = 0
        else:
            # 该用户关注的人 followees
            followees_num = int(f_el[0].string.replace("\n", ""))
            followees = self._fetch_followees(followees_num)
            # 关注该用户的人 followers
            followers_num = int(f_el[1].string.replace("\n", ""))
            followers = self._fetch_followers(followers_num)

        print followers
        # 关注的专栏

        # 关注的话题

        el = DOM.find("div", class_="zm-profile-section-list")
        # 成就 ( 赞同数, 感谢 )
        reputation = {"agree": 0, "thanks": 0, "favors": 0, "share": 0}
        elems = el.find("div", class_="zm-profile-details-reputation").find_all("strong")
        if len(elems) == 4:
            reputation['agree'] = int(elems[0].string)
            reputation['thanks'] = int(elems[1].string)
            reputation['favors'] = int(elems[2].string)
            reputation['share'] = int(elems[3].string)
        else:
            Logging.error(u"用户个人成就信息解析失败")
            Logging.debug(elems)
        "次要信息, 待完善 ..."
        # 职业经历

        # 居住信息

        # 教育经历



    @staticmethod
    def search(keywords):
        return Search.people(keywords)
    def export(self):
        pass

class Inbox:
    def __init__(self):
        self.inbox = []
        self.pull()
    def pull(self):
        url = "http://www.zhihu.com/inbox"

    def sync(self):
        pass
    def parser(self, html):
        pass
    def export(self, format="rst"):
        pass

class Message:
    def __init__(self, token=None):
        self.token = token
    def pull(self):
        pass
    def sync(self):
        pass
    def parser(self):
        pass
    def export(self, format="rst"):
        pass
    @staticmethod
    def search(keywords):
        return Search.people(keywords)


class Explore:
    """
        发现新话题
    """
    def __init__(self):
        self.answers = []
        self.questions = []
    @staticmethod
    def pull(period="day", offset=0, size=10, limit=1):
        result = []
        if type(period) != type("") or period not in ["day", "week"]: return result
        if type(offset) != type(1) or type(size) != type(1) or type(limit) != type(1):
            return result

        if limit < 1: return result
        elif int(limit) == 1:
            # url = "http://www.zhihu.com/explore"
            url = "http://www.zhihu.com/node/ExploreAnswerListV2"
            params = {"params": json.dumps({"offset": offset,"type": period}) }
            res = requests.get(url, params=params)
            # parse ...
            return [res]
        else:
            for i in range(limit):
                map(lambda r: result.append(r), Explore.pull(period=period, offset=offset+1, size=size, limit=1) )
            return result

    @staticmethod
    def render(result):
        pass
    @staticmethod
    def export(result=[], format="rst"):
        pass


class Topic:
    """
        话题

    """
    def __init__(self, token=None):
        self.token = str(token)
    def pull(self):
        url = "http://www.zhihu.com/topic/%s" % self.token

    def sync(self):
        pass
    def parser(self, html):
        pass
    def export(self, format="rst"):
        pass
    @staticmethod
    def search(keywords):
        return Search.topic(keywords)

class Question:
    """
        问题
    """
    def __init__(self, token=None):
        self.token = str(token)
        self.id = 0
        self.xsrf  = "" 
        self.html  = "" 
    def pull(self):
        if self.token == None:
            raise ValueError("token required.")
        url = "http://www.zhihu.com/question/%s" % self.token
        res = requests.get(url)
        if res.status_code in [302, 301]:
            raise IOError("network error.")
        elif res.status_code != 200:
            raise IOError("unknow err.or.")
        else:
            # res.content | res.text 
            self.html = res.content
            r = re.compile(r"input\stype.*?name=.\_xsrf.\svalue=.(\w+).", re.DOTALL).findall(self.html)
            if len(r)>0:
                self.xsrf = r[0]
            else:
                # error.
                pass
    def sync(self):
        pass
    def _fetch_followers(self):
        # return True
        url = "http://www.zhihu.com/question/%s/followers" % self.token
        offset = 0
        xsrf   = ""

        followers_num = 0

        res = requests.get(url)
        if res.status_code in [302, 301]:
            raise IOError("network error.")
        elif res.status_code != 200:
            raise IOError("unknow error.")
        else:
            # res.content | res.text 
            html = res.content
            r = re.compile(r"input\stype.*?name=.\_xsrf.\svalue=.(\w+).", re.DOTALL).findall(html)
            xsrf = r[0]
            followers_num = int(re.compile(r"\/question\/%s\/followers.*?strong\>(\d+)\<"%(self.token), re.DOTALL).findall(html)[0])

        followers = []
        while offset<followers_num:
            data = {"start": 0, "offset": offset, "_xsrf": xsrf}
            
            Logging.info(u"获取问题关注者: %s " % json.dumps(data))

            r = requests.post(url, data=data)
            if r.status_code == 200:
                try:
                    result = json.loads(r.content)
                    if result['r'] == 0 and type(result['msg']) == type([]) and result['msg'][0]>0 and len(result['msg'][1]) > 0:
                        offset += int(result['msg'][0])
                        DOM = result['msg'][1]
                        try:
                            try:
                                soup = BeautifulSoup(DOM, 'html.parser')
                                cards = soup.find_all("div", class_="zm-profile-card")
                            except Exception as e:
                                print u"BeautifulSoup 初始化 失败."
                                print e
                                cards = []
                            for card in cards:
                                # {"name": "", "token": "", "descp": "", "avatar": ""}
                                try:
                                    el = card.find("a", class_="zg-link")
                                    if el != None:
                                        name = el['title']
                                        token = el['href'].split("/")[-1]

                                        el = card.find("a", class_="zm-item-link-avatar")
                                        avatar = el.find("img")['src']
                                        descp = card.find("div", class_="zg-big-gray").string
                                        followers.append({"name": name, "token": token, "descp": descp, "avatar": avatar })
                                except Exception as e:
                                    print u"BeautifulSoup 查找 HTML Node 失败"
                                    print e
                        except Exception as e:
                            print u"该页解析异常"
                            print e
                            import time
                            time.sleep(3)
                    else:
                        # 应该需要终止 循环
                        print u"数据格式错误"
                        print result
                        break
                except Exception as e:
                    print u"该页初始化数据失败"
                    print e
                    break
            else:
                raise IOError("network error.")
        return followers
    def _fetch_answers(self, total):
        # 获取所有的 问题答案
        url = "http://www.zhihu.com/node/QuestionAnswerListV2"
        """
            method:next
            params:{"url_token":35112858,"pagesize":50,"offset":50}
            _xsrf:f11a7023d52d5a0ec95914ecff30885f
        """
        # size: 50 (max: 100)
        size = 100
        offset = 0

        # 返回 答案 的 token, 而不是内容，完整的答案内容需要调用 Answer 类去获取
        # /question/35112858/answer/63250622
        answers = []
        while offset<total:    
            params = {"url_token": self.token, "pagesize": size, "offset": offset}
            data = {"method": "next", "_xsrf": self.xsrf, "params": json.dumps(params) }
            
            Logging.info(u"获取答案页: %s " % json.dumps(data))

            r = requests.post(url, data=data)
            if r.status_code != 200:
                raise IOError("network error.")
            try:
                res = json.loads(r.content)
                if res['r'] != 0 or type(res['msg']) != type([]): raise ValueError(u"数据格式无效")
                result = res['msg']
            except Exception as e:
                print e
                result = []
            for dom in result:
                """
                <div tabindex="-1" class="zm-item-answer " itemscope itemtype="http://schema.org/Answer" data-aid="20714326" data-atoken="63250622" data-collapsed="0" data-created="1441961912" data-deleted="0" data-helpful="1" data-isowner="0" data-copyable="1" > 
                    <a class="zg-anchor-hidden" name="answer-20714326"></a> 
                    <div class="zm-votebar">
                        <button class="up "> <i class="icon vote-arrow"></i> <span class="label">赞同</span> <span class="count">0</span> </button> 
                        <button class="down "> <i class="icon vote-arrow"></i> <span class="label">反对</span> </button> 
                    </div>
                    <div class="answer-head"> 
                        <div class="zm-item-answer-author-info"> 
                            <h3 class="zm-item-answer-author-wrap"> 
                                <a data-tip="p$t$hao-jun-sao-xiao-fang" class="zm-item-link-avatar" href="/people/hao-jun-sao-xiao-fang"> 
                                    <img src="https://pic1.zhimg.com/da8e974dc_s.jpg" class="zm-list-avatar" data-source="https://pic1.zhimg.com/da8e974dc_s.jpg" /> 
                                </a>
                                <a data-tip="p$t$hao-jun-sao-xiao-fang" href="/people/hao-jun-sao-xiao-fang">好军嫂小方</a>，<strong title="门窗阳光房、封阳台" class="zu-question-my-bio">门窗阳光房、封阳台</strong> 
                            </h3>
                            <a href="javascript:;" name="collapse" class="collapse meta-item zg-right">
                            <i class="z-icon-fold"></i>收起</a> 
                        </div>
                        <div class="zm-item-vote-info empty" data-votecount="0"> </div> 
                    </div>
                    <div class="zm-item-rich-text" data-resourceid="6251824" data-action="/answer/content">
                        <div class="zm-editable-content clearfix">  美味，问题答案 内容区</div> 
                    </div> 
                    <a class="zg-anchor-hidden ac" name="20714326-comment"></a> 
                    <div class="zm-item-meta zm-item-comment-el answer-actions clearfix"> 
                        <div class="zm-meta-panel"> 
                            <span class="answer-date-link-wrap"> 
                                <a class="answer-date-link meta-item" target="_blank" href="/question/35112858/answer/63250622">发布于 2015-09-11</a> 
                            </span>
                            <a href="#" name="addcomment" class=" meta-item toggle-comment"> 
                            <i class="z-icon-comment"></i>添加评论</a> <a href="#" class="meta-item zu-autohide" name="thanks" data-thanked="false">
                            <i class="z-icon-thank"></i>感谢</a> <a href="#" class="meta-item zu-autohide" name="share"> 
                            <i class="z-icon-share"></i>分享</a> <a href="#" class="meta-item zu-autohide" name="favo"> 
                            <i class="z-icon-collect"></i>收藏</a> 
                            <span class="zg-bull zu-autohide">&bull;</span> <a href="#" name="nohelp" class="meta-item zu-autohide">没有帮助</a>
                             <span class="zg-bull zu-autohide">&bull;</span> <a href="#" name="report" class="meta-item zu-autohide">举报</a> 
                             <span class="zg-bull">&bull;</span> <a href="/terms#sec-licence-1" target="_blank" class="meta-item copyright"> 作者保留权利 </a> 
                        </div> 
                    </div> 
                </div>

                """
                soup = BeautifulSoup(dom, "html.parser")
                el = soup.find("div", class_="zm-item-answer")
                try:
                    answers.append(el['data-atoken'])
                except Exception as e:
                    print e
            offset += len(result)
        # answer tokens
        return answers
    def _fetch_comments(self):
        # 获取该问题的评论
        url = "http://www.zhihu.com/node/QuestionCommentBoxV2"
        # 注意，这里的 question id 并非 是 question token.
        params = {"params": json.dumps({"question_id": self.id})}
        r = requests.get(url, params=params)
        if r.status_code != 200:
            return []
        """
            http response:
            <div class="zm-comment-box" data-count="2">
                <i class="icon icon-spike zm-comment-bubble"></i>
                <a class="zg-anchor-hidden" name="comment-0"></a>
                <div class="zm-comment-list">
                    <div class="zm-item-comment" data-id="90669446">
                        <a class="zg-anchor-hidden" name="comment-90669446"></a>
                        <a title="薯薯薯薯条"
                            data-tip="p$t$xia-mu-de-cha-wan"
                            class="zm-item-link-avatar"
                            href="/people/xia-mu-de-cha-wan">
                                <img src="https://pic3.zhimg.com/98a00c51721216c0c61b74be7338c20a_s.jpg" class="zm-item-img-avatar">
                        </a>
                        <div class="zm-comment-content-wrap">
                            <div class="zm-comment-hd">
                                <a data-tip="p$t$xia-mu-de-cha-wan" href="http://www.zhihu.com/people/xia-mu-de-cha-wan" class="zg-link" title="薯薯薯薯条">薯薯薯薯条</a>

                            </div>
                            <div class="zm-comment-content">
                            ( •̀∀•́ )坐等看故事
                            </div>
                            <div class="zm-comment-ft">
                                <span class="date">2015-08-20</span>
                                <a href="#" class="reply zm-comment-op-link" name="reply_comment">
                                <i class="zg-icon zg-icon-comment-reply"></i>回复</a>
                                <a href="#" class="like zm-comment-op-link " name="like_comment">
                                <i class="zg-icon zg-icon-comment-like"></i>赞</a>
                                <span class="like-num  nil" data-tip="s$r$0 人觉得这个很赞">
                                <em>0</em> <span>赞</span></span>


                                <a href="#" name="report" class="report zm-comment-op-link needsfocus">
                                <i class="zg-icon z-icon-no-help"></i>举报</a>
                            </div>
                        </div>
                    </div>
                <!-- comment list end -->
                </div>
            </div>

        """
        soup = BeautifulSoup(r.content, "html.parser")
        elems = soup.find_all("div", class_="zm-item-comment")

        comments = []
        for elem in elems:
            # comment id
            el = elem.find("a", class_="zm-item-link-avatar")
            id = int(elem['data-id'])

            people = {
                "token": el['href'].split("/")[-1],
                "avatar": el.find('img')['src'],
                "name": elem.find("div", class_="zm-comment-hd").find("a")['title']
            }
            utime = elem.find("span", class_="date").string
            content = elem.find("div", class_="zm-comment-content").get_text()
            if content == None:
                Logging.error(u"问题评论解析失败")
                Logging.debug(elem)
            else:
                content = re.sub("^\n+|\n+$", "", content)
                comments.append({"id": id, "people": people, "content": content, "utime": utime})
        
        return comments

    def _fetch_logs(self):
        # 获取该问题的修改日志
        url = "http://www.zhihu.com/question/%s/log" % self.token

    def parse(self):
        DOM = BeautifulSoup(self.html, 'html.parser')

        # 问题标题
        title = DOM.find("h2", class_="zm-item-title").get_text()
        title = re.sub("^\n+|\n+$", "", title)
        
        # 问题主体
        el = DOM.find("div", id="zh-question-detail")

        id = int(el['data-resourceid'])  # 问题资源编号, 区别于Token
        self.id = id
        content = el.find("div", class_="zm-editable-content").get_text()
        content = re.sub("^\n+|\n+$", "", content)

        # 问题关注者
        followers = self._fetch_followers()

        # 答案数量        
        try:
            el = DOM.find("h3", id="zh-question-answer-num")
            answers_num = int(el["data-num"])
        except:
            answers_num = 0
        # 答案 token 列表
        answers = self._fetch_answers(answers_num)

        # 问题 状态, 关注该问题的人员列表、相关问题、被浏览次数、相关话题关注者人数
        sections = DOM.find_all("div", class_="zm-side-section")
        if len(sections) == 3:
            elems = sections[-1].find_all("div", class_="zg-gray-normal")
            # 最后更新时间, 2015-10-02 | 23:35
            utime_string = elems[0].find("span", class_="time").string
            elems = elems[1].find_all("strong")
            # 被浏览次数
            visit_times = int(elems[0].string)
            # 相关话题关注者人数
            RT_for_CN = int(elems[1].string)
            
        else:
            utime_string = ""
            visit_times = 0
            RT_for_CN = 0
        # 问题所属 话题列表
        topics = []
        elems = DOM.find_all("a", class_="zm-item-tag")
        if elems == None: elems = []
        for el in elems:
            try:
                topics.append({"id": el['data-topicid'], "token": el['data-token'], "name": el.contents[0].string.replace("\n", "") })
            except:
                Logging.error(u"话题解析失败")
                Logging.debug(el)
        # 获取该 问题的评论
        comments = self._fetch_comments()

        print u"title: %s" % title
        print u"content: %s" % content
        print u"topics: "
        _print = []
        map(lambda topic: _print.append("%s(%s), " %(topic['name'], topic['token'])), topics)
        print "\t%s" % ", ".join(_print)

        print u"followers: "
        _print = []
        map(lambda topic: _print.append("%s(%s), " %(topic['name'], topic['token'])), followers)
        print "\t%s" % ", ".join(_print)

        print u"答案列表(%d):" %(len(answers))
        print u"\t ", answers

        print u"问题评论:"
        for comment in comments:
            print u"\t %s\t%s\t%s" % (comment['utime'], comment['people']['name'], comment['content'])

        print u"问题状态:"
        print u"\t浏览次数: %d" % visit_times
        print u"\t相关话题关注者人数: %d" % RT_for_CN
        print u"\t最后修改时间: %s" % utime_string
    @staticmethod
    def search(keywords):
        return Search.question(keywords)

class Answer:
    """
        答案
    """
    def __init__(self, question_token=None, answer_token=None):
        self.question_token = question_token
        self.answer_token = answer_token
    def pull(self):
        pass
    def sync(self):
        pass
    @classmethod
    def parser(self, html):
        DOM = BeautifulSoup(html)

    @staticmethod
    def search(keywords):
        return []


class Search:
    """
        搜索接口
            人 | 问题 | 话题

    """
    def __init__(self):
        pass
    @staticmethod
    def people(keywords=None, offset=0, size=10, limit=1):
        """
            offset: 起始偏移量
            size: 10 (不能修改)
            limit: 最多向下几页
        """
        result = []
        if type(keywords) != type(""): return result
        if int(limit) < 1: return result
        elif int(limit) == 1:
            url = "http://www.zhihu.com/r/search"
            res = requests.get(url, params={"q": keywords, "type": "people", "offset": 0})
            # parse ...
            def parse_result():
                pass


            return [res]
        else:
            for i in range(int(limit)):
                map(lambda r: result.append(r), Search.people(keywords=keywords, offset=offset+i, limit=1 ) )
            return result
    @staticmethod
    def question(keywords=None, offset=0, size=10, page=1):
        """
            offset: 起始偏移量
            size: 10 (不能修改)
            page: 页数
        """
        size = 10
        result = []
        if type(keywords) != type(""): return result
        if int(page) < 1: return result
        elif int(page) == 1:
            url = "http://www.zhihu.com/r/search"
            res = requests.get(url, params={"q": keywords, "type": "question", "offset": 0})
            # parse ...

            return [res]
        else:
            for i in range(int(page)):
                map(lambda r: result.append(r), Search.question(keywords=keywords, offset=page*size+offset, page=1 ) )
            return result
    @staticmethod
    def topic(keywords=None, offset=0, size=10, limit=1):
        """
            Note: 
                对于话题的搜索，似乎没有 offset, size 以及 limit 条件，按道理，这种 结构树应该是一次性返回的。
                所以参数 offset, size 以及 limit 暂不起作用。
        """
        result = []
        if type(keywords) != type(""): return result
        url = "http://www.zhihu.com/r/search"
        res = requests.get(url, params={"q": keywords, "type": "topic"})
        # parse ...
        return [res]

"""
    WARNING: 
        前方高能，人类止步！
"""
class Siri:
    def __init__(self, url="", response="total"):
        """
            response: simple | normal | good | perfect
        """
        self.url = url
        print u" \U0001f604   用我吧，你会发现我比Cortana更聪明 \U0001f604 "
    def think(self):
        if self.is_url() != True:
            print u"也许你应该去问问Siri :)) "
            return False
    def is_url(self):
        result = {}
        re.match(r"http\:\:\/\/www\.zhihu\.")
    def is_question(self):
        pass
    def is_topic(self):
        pass
    def is_answer(self):
        pass


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
    # test()
    pass
