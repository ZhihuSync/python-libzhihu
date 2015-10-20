#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Build-in / Std
import os, sys, time, platform, random
import re, json, cookielib

# requirements
import requests, termcolor, html2text
import requests_cache
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

cookies = os.path.join(os.path.join( os.environ['HOME'], '.zhihu'), "cookies")
cache_db = os.path.join(os.path.join( os.environ['HOME'], '.zhihu'), "cache.db")

# requests_cache.install_cache( cache_db )

requests = requests.Session()
requests.cookies = cookielib.LWPCookieJar( cookies )
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
        """
            Tips:
                用户编号 直接 搜索 data-id 可以查看到，但是无法查看到当前登陆用户的 id 
                解决办法采用没有 登陆 session 的连接去请求个人页面。

                view-source:http://www.zhihu.com/people/raymond-wang

                <button 
                    data-follow="m:button" 
                    data-id="cfd6c460ccfe5e87a75a5410bbf0ae65" 
                    class="zg-btn zg-btn-follow zm-rich-follow-btn">
                        关注
                </button>
        """
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
    def search(keywords=""):
        url = "http://www.zhihu.com/r/search"
        # q=%E4%BD%A0%E5%A5%BD&range=&type=question&offset=10
        offset = 0

        has_next = True

        peoples = []

        while has_next:
            params = {"q": keywords, "type": "people", "offset": offset}

            Logging.info(u"正在下载用户搜索结果: %s" % json.dumps(params) )

            r = requests.get(url, params=params)
            if r.status_code != 200:
                raise IOError(u"network error.")
            try:
                """
                JSON Format:
                    {
                        "htmls": [
                            "<li></li>"
                        ],
                        "paging": {
                            "next": "/r/search?q=%E4%BD%A0%E5%A5%BD&range=&type=question&offset=20"  # 为空则代表没有后续数据
                        }
                    }

                HTML DOM:
                    <li class="item item-card user-card clearfix">
                        <div class="left content">
                            <a href="/people/ai-ji-50-13" class="avatar-link left">
                                <img src="https://pic1.zhimg.com/7df3fdfd64e07a4761ec5266978887a0_m.jpg" alt="埃及" class="avatar 50">
                            </a>
                            <div class="body">
                                <div class="line">
                                    <a href="/people/ai-ji-50-13" class="name-link" data-highlight>埃及</a>
                                    <i class="icon icon-profile-female" title="她"></i>
                                </div>
                                <div class="line"></div>
                            </div>
                        </div>
                        <div class="extra">
                            <div class="grid clearfix">
                                <a href="/people/ai-ji-50-13/answers" class="col"><strong>0</strong><span>回答</span></a>
                                <a href="/people/ai-ji-50-13/posts" class="col"><strong>0</strong><span>文章</span></a>
                                <a href="/people/ai-ji-50-13/followers" class="col"><strong>0</strong><span>关注者</span></a>
                            </div>
                            <button 
                                data-follow="m:button" 
                                class="zg-right zg-btn zg-btn-follow" 
                                data-id="beb3486a012acc5c9d07134aeb9be6de">
                                    关注
                            </button>
                        </div>
                    </li>
                """
                body = json.loads(r.content)
                items = body['htmls']
                for q in items:
                    try:
                        DOM = BeautifulSoup(q, 'html.parser')
                        name = re.sub("<.*?>", "", re.sub("^\n+|\n+$", "", DOM.find("div", class_="content").find("a", class_="name-link").get_text()) )
                        id = DOM.find("button")['data-id']
                        token = DOM.find("div", class_="content").find("a", class_="name-link")['href'].split("/")[-1]

                        peoples.append( {"id": id, "token": token, "name": name} )

                    except Exception as e:
                        Logging.error(u"DOM解析失败")
                        Logging.debug(e)
                if body['paging']['next'] == "" or body['paging']['next'] == None:
                    has_next = False

                offset += len(items)

            except Exception as e:
                Logging.error(u"数据解析失败")
                Logging.debug(e)

        return peoples

    def export(self):
        pass



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
                Logging.error(u"HTTP CODE 不为 200.")
                Logging.debug(r.content)
                # raise IOError("network error.")
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

        """
            <div id="zh-question-detail" class="zm-item-rich-text" data-resourceid="6778410" data-action="/question/detail">
        """
        id = int(el['data-resourceid'])  # 问题资源编号, 区别于Token
        self.id = id

        """
            提问者信息 在 问题日志(http://www.zhihu.com/question/36428260/log) 里面可以查看（如果不是匿名提问的话）
        """
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

        # DEBUG
        for atoken in answers:
            A = Answer(question_token=self.token, answer_token=atoken)
            A.pull()
            A.parse()
    @staticmethod
    def search(keywords=""):
        url = "http://www.zhihu.com/r/search"
        # q=%E4%BD%A0%E5%A5%BD&range=&type=question&offset=10
        offset = 0

        has_next = True

        questions = []

        while has_next:
            params = {"q": keywords, "range": "", "type": "question", "offset": offset}

            Logging.info(u"正在下载问答搜索结果: %s" % json.dumps(params) )

            r = requests.get(url, params=params)
            if r.status_code != 200:
                raise IOError(u"network error.")
            try:
                """
                JSON Format:
                    {
                        "htmls": [
                            "<li></li>"
                        ],
                        "paging": {
                            "next": "/r/search?q=%E4%BD%A0%E5%A5%BD&range=&type=question&offset=20"  # 为空则代表没有后续数据
                        }
                    }

                HTML DOM:
                    <li class="item clearfix">
                        <div class="title">
                            <a target="_blank" href="/question/31516118" class="question-link">异地恋 <em>你好</em>？</a>
                        </div>
                        <div class="content">
                            <meta itemprop="question-id" content="4805722">
                            <meta itemprop="question-url-token" content="31516118">
                            <div class="actions">
                                <a href="#" class="action-item" data-follow="q:link" data-id="4805722">
                                    <i class="z-icon-follow"></i>
                                    关注问题
                                </a>
                                <span class="zg-bull">•</span>
                                <a href="/question/31516118/followers" class="action-item">1 人关注</a>
                                <span class="zg-bull">•</span>
                                <a href="/question/31516118" class="action-item">0 个回答</a>
                            </div>
                        </div>
                    </li>"
                """
                body = json.loads(r.content)
                items = body['htmls']
                for q in items:
                    # question_token = re.compile(r"\/question\/(\d+)\"|\'", re.DOTALL).findall(q)[0]
                    try:
                        DOM = BeautifulSoup(q, 'html.parser')
                        title = re.sub("<.*?>", "", re.sub("^\n+|\n+$", "", DOM.find("div", class_="title").find("a").get_text()) )
                        id = DOM.find("meta", itemprop="question-id")['content']
                        token = DOM.find("meta", itemprop="question-url-token")['content']

                        questions.append( {"id": id, "token": token, "title": title} )

                    except Exception as e:
                        Logging.error(u"DOM解析失败")
                        Logging.debug(e)
                if body['paging']['next'] == "" or body['paging']['next'] == None:
                    has_next = False

                offset += len(items)

            except Exception as e:
                Logging.error(u"数据解析失败")
                Logging.debug(e)

        return questions

class Answer:
    """
        答案
    """
    def __init__(self, question_token=None, answer_token=None):
        self.question_token = str(question_token)
        self.answer_token = str(answer_token)
        self.html = ""
    def pull(self):
        url = "http://www.zhihu.com/question/%s/answer/%s" %( self.question_token, self.answer_token )
        res = requests.get(url)
        if res.status_code in [302, 301]:
            raise IOError("network error.")
        elif res.status_code != 200:
            raise IOError("unknow err.or.")
        else:
            # res.content | res.text 
            self.html = res.content
    def sync(self):
        pass
    def _fetch_voters(self, aid):
        # 获取该答案的赞同人员，反对人员名单则不显示
        url = "http://www.zhihu.com/answer/%s/voters_profile" %(str(aid))
        # total=627&offset=10&follows=VzkPlUR84mpoyZY53UYio7cCnUgG
        # Note: follows 代码携带在上次的请求响应数据里面
        """
            {
                "paging": {
                    "total": 628, 
                    "next": ""   # 如果为空 则代表没有下一页, 否则应该返回的是这样的 URI: /answer/22511343/voters_profile?total=628&offset=620&follows=7r8vFgMT1QmkVDoPV6FZX4ac-NFP
                }, 
                "code": 0, 
                "payload": [
                    ""
                    <div class="zm-profile-card clearfix no-hovercard"> 
                        <div class="zg-right"> 
                            <button data-follow="m:button" data-id="7b2882fdb3b60897b593664361e852fb" class="zg-btn zg-btn-follow zm-rich-follow-btn small nth-0">关注她</button> 
                        </div> 
                        <a title="段NaN" data-tip="p$t$duannan" class="zm-item-link-avatar" target="_blank" href="/people/duannan"> 
                            <img src="https://pic2.zhimg.com/f32c7f335_m.jpg" class="zm-item-img-avatar"> 
                        </a> 
                        <div class="body"> 
                            <div class="author ellipsis"> 
                                <a data-tip="p$t$duannan" href="http://www.zhihu.com/people/duannan" target="_blank" class="zg-link" title="段NaN">段NaN</a> 
                                <span class="bio hidden-phone">早起特困户@.@</span> 
                            </div> 
                            <ul class="status"> 
                                <li><span>31 赞同</span></li> 
                                <li><span>6 感谢</span></li> 
                                <li class="hidden-phone">
                                    <a href="/people/duannan/asks" target="_blank">0 提问</a>
                                </li> 
                                <li class="hidden-phone">
                                    <a href="/people/duannan/answers" target="_blank">8 回答</a>
                                </li> 
                            </ul> 
                        </div> 
                    </div>
                    ""
                ], 
                "success": true
            }
        """
        has_next = True
        Logging.info(u"获取答案的赞同人员列表")
        
        users = []
        
        while has_next:
            r = requests.get(url)
            Logging.info(u"请求页面: %s" % url)

            if r.status_code != 200:
                raise IOError(u"network error.")
            try:
                body = json.loads(r.content)
                assert body['code'] == 0

            except Exception as e:
                Logging.error(u"数据格式错误")
                Logging.debug(e)
            for p in body['payload']:
                # print p
                # sys.exit()
                people_token = re.compile(r"\/people\/(\S+)\"|\'", re.DOTALL).findall(p)[0]
                try:
                    people_id = re.compile(r"data-id=.(\w+).", re.DOTALL).findall(p)[0]
                except Exception as e:
                    Logging.error(u"解析 作者编号出错！")
                    Logging.debug(e)
                    # Logging.debug(p)
                    people_id = ""

                users.append({"token": people_token, "id": people_id})
            if body['paging']['next'] == "":
                has_next = False
            else:
                url = "http://www.zhihu.com" + body['paging']['next']
        return users

    def _fetch_comments(self, aid):
        # 获取该答案的评论
        url = "http://www.zhihu.com/node/AnswerCommentBoxV2"
        params = {"answer_id": aid, "load_all": True}

        Logging.info(u"获取答案评论")
        Logging.info(url)
        Logging.info(json.dumps(params))

        r = requests.get(url, params={"params": json.dumps(params)})

        if r.status_code != 200:
            raise IOError(u"network error")

        soup = BeautifulSoup(r.content, 'html.parser')
        # DOM = soup.find("div", class_="zm-comment-list")
        elems = soup.find_all("div", class_="zm-item-comment")
        """
        <div class="zm-comment-list">
            <div class="zm-item-comment" data-id="98953481">
                <a class="zg-anchor-hidden" name="comment-98953481"></a>
                <a title="赵健" data-tip="p$t$zhao-jian-65" class="zm-item-link-avatar" href="/people/zhao-jian-65">
                    <img src="https://pic2.zhimg.com/9f4c3e0b5_s.jpg" class="zm-item-img-avatar">
                </a>
                <div class="zm-comment-content-wrap">
                    <div class="zm-comment-hd">
                        <a data-tip="p$t$zhao-jian-65" href="http://www.zhihu.com/people/zhao-jian-65" class="zg-link" title="赵健">赵健</a>
                    </div>
                    <div class="zm-comment-content">
                        我只知道运输都是抓幼崽，没想到看起来这么的。。。。。残忍
                    </div>
                    <div class="zm-comment-ft">
                        <span class="date">2015-10-15</span>
                        <a href="#" class="reply zm-comment-op-link" name="reply_comment">
                            <i class="zg-icon zg-icon-comment-reply"></i>回复
                        </a>
                        <a href="#" class="like zm-comment-op-link " name="like_comment">
                            <i class="zg-icon zg-icon-comment-like"></i>赞
                        </a>
                        <span class="like-num  nil" data-tip="s$r$0 人觉得这个很赞">
                            <em>0</em> <span>赞</span>
                        </span>
                        <a href="#" 
                            name="report" 
                            class="report zm-comment-op-link needsfocus goog-inline-block goog-menu-button" 
                            role="button" aria-expanded="false" tabindex="0" aria-haspopup="true" 
                            style="-webkit-user-select: none;">
                                <div class="goog-inline-block goog-menu-button-outer-box">
                                    <div class="goog-inline-block goog-menu-button-inner-box">
                                        <div class="goog-inline-block goog-menu-button-caption">
                                            <i class="zg-icon z-icon-no-help"></i>举报
                                        </div>
                                        <div class="goog-inline-block goog-menu-button-dropdown">&nbsp;</div>
                                    </div>
                                </div>
                        </a>
                    </div>
                </div>
            </div>
        </div>
        """
        if elems == None: elems = []

        comments = []

        for elem in elems:
            comment_id = elem['data-id']
            author_token = elem.find("div", class_="zm-comment-hd").find("a", class_="zg-link")['href'].split("/")[-1]
            author_name = elem.find("div", class_="zm-comment-hd").find("a", class_="zg-link")['title']

            content = elem.find("div", class_="zm-comment-content").get_text()
            content = re.sub("^\n+|\n+$", "", content)

            comments.append(  {"id": comment_id, "people":{"token": author_token, "name": author_name}, "content": content } )
        return comments

    def parse(self):
        DOM = BeautifulSoup(self.html, 'html.parser')
        elem = DOM.find("div", class_="zh-question-answer-wrapper").find("div", class_="zm-item-answer")
        """
            <div tabindex="-1" 
                class="zm-item-answer" itemscope="" itemtype="http://schema.org/Answer" 
                data-aid="22511343" 
                data-qtoken="31272454" 
                data-author="Jess" 
                data-atoken="67732326" 
                data-collapsed="0" 
                data-created="1444820403" 
                data-deleted="0" 
                data-helpful="1" 
                data-isowner="0" 
                data-copyable="1">
                    <a class="zg-anchor-hidden" name="answer-22511343"></a>
                    ......
            </div>
        """
        aid = elem['data-aid']
        ctime = int(elem['data-created'])
        try:
            el = elem.find("h3", class_="zm-item-answer-author-wrap")
            if re.sub("^\n+|\n+$", "", el.get_text() ) == u"匿名用户":
                author_token = u"匿名用户"
            else:
                author_token = el.find("a", class_="zm-item-link-avatar")['href'].split("/")[-1]
        except Exception as e:
            Logging.error(u"解析作者 TOKEN 出错")
            Logging.debug(e)
            Logging.debug(elem.find("div", class_="answer-head"))
            author_token = ""
            """
                解析出错，应该是 匿名用户的原因.
                <div class="answer-head">
                    <div class="zm-item-answer-author-info">
                        <a class="collapse meta-item zg-right" href="javascript:;" name="collapse"><i class="z-icon-fold"></i>收起</a>
                        <h3 class="zm-item-answer-author-wrap">匿名用户</h3>
                    </div>
                    <div class="zm-item-vote-info " data-votecount="1">
                        <span class="voters">
                            <span class="user-block">
                                <a 
                                    class="zg-link" 
                                    data-tip="p$t$hao-lu-ba-80" 
                                    href="http://www.zhihu.com/people/hao-lu-ba-80" 
                                    title="郝绿坝">
                                        郝绿坝
                                </a>
                            </span>
                        </span>
                        <span>赞同</span>
                    </div>
                </div>

            """

        # voters_num = int(elem.find("div", class_="zm-votebar").find("button", class_="up").find("span", class_="count").string)
        voters = self._fetch_voters(aid)

        content = elem.find("div", class_="zm-item-rich-text")

        comments = self._fetch_comments(aid)


        print u"问题Token: %s" %self.question_token
        print u"答案Token: %s (ID: %s ) " % (self.answer_token, str(aid))
        print u"作者Token: %s" % author_token
        print u"回答时间: %d " % ctime
        print u"赞同人员: \n\t", voters
        print u"答案正文: \n\t", content
        print u"答案评论: \n\t", comments

    @staticmethod
    def search(keywords):
        return []

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
    def newest(self):
        # 动态, 热门排序 | 时间排序

        # 时间排序
        url = "http://www.zhihu.com/topic/%s/newest" % ( self.token )
        """
            HTTP POST:
                start:0
                offset:1445013770.0
                _xsrf:f11a7023d52d5a0ec95914ecff30885f
            Note:

                offset 数据携带在 请求回应结果中的 HTML DOM 中。

                <div 
                    class="feed-item feed-item-hook  folding combine" 
                    itemprop="question" 
                    itemscope="" 
                    itemtype="http://schema.org/Question" 
                    data-score="1445021798.0">

                    ......
                </div>
        """

        # 热门排序
        url = "http://www.zhihu.com/topic/19550374/hot"
        """
            HTTP POST:
                start:0
                offset:2435.88125526
                _xsrf:f11a7023d52d5a0ec95914ecff30885f
            offset 数据在 响应 DOM 属性中

            <div 
                class="feed-item feed-item-hook question-item" 
                itemprop="question" 
                itemscope="" 
                itemtype="http://schema.org/Question" 
                data-score="2435.63387728" 
                data-type="q">

                ......
            </div>
        """

    def top_answers(self):
        # 精华
        pass
    def questions(self):
        # 全部问题
        pass
    def parser(self, html):
        pass
    def export(self, format="rst"):
        pass
    @staticmethod
    def search(keywords=""):
        url = "http://www.zhihu.com/r/search"
        # q=%E4%BD%A0%E5%A5%BD&range=&type=topic&offset=10
        offset = 0

        has_next = True

        topics = []

        while has_next:
            params = {"q": keywords, "type": "topic", "offset": offset}

            Logging.info(u"正在下载话题搜索结果: %s" % json.dumps(params) )

            r = requests.get(url, params=params)
            if r.status_code != 200:
                raise IOError(u"network error.")
            try:
                """
                JSON Format:
                    {
                        "htmls": [
                            "<li></li>"
                        ],
                        "paging": {
                            "next": "/r/search?q=%E4%BD%A0%E5%A5%BD&range=&type=topic&offset=20"  # 为空则代表没有后续数据
                        }
                    }

                HTML DOM:
                    <li class="item clearfix">
                        <a href="/topic/20025392" class="avatar-link hidden-phone">
                            <img src="http://pic1.zhimg.com/e82bab09c_m.jpg" alt="你知道 X 多努力么" class="avatar 50">
                        </a>
                        <div class="content">
                            <div class="name">
                                <a href="/topic/20025392" class="name-link" data-highlight>你知道 X 多努力么</a>
                            </div>
                            <div class="desc"></div>
                            <div class="meta">
                                <button data-follow="t:button" class="zg-right zg-btn zg-btn-follow" data-id="160564">关注</button>
                                <a class="questions" href="/topic/20025392/questions">
                                    <i class="icon icon-bubble"></i>
                                    6 个问题
                                </a>
                                <a class="followers" href="/topic/20025392/followers"><i class="icon icon-avatar"></i>1 个关注</a>
                            </div>
                        </div>
                    </li>"
                """
                body = json.loads(r.content)
                items = body['htmls']
                for q in items:
                    try:
                        DOM = BeautifulSoup(q, 'html.parser')
                        name = re.sub("<.*?>", "", re.sub("^\n+|\n+$", "", DOM.find("div", class_="content").find("a", class_="name-link").get_text()) )
                        id = DOM.find("button")['data-id']
                        token = DOM.find("div", class_="content").find("a", class_="name-link")['href'].split("/")[-1]

                        topics.append( {"id": id, "token": token, "name": name} )

                    except Exception as e:
                        Logging.error(u"DOM解析失败")
                        Logging.debug(e)
                if body['paging']['next'] == "" or body['paging']['next'] == None:
                    has_next = False

                offset += len(items)

            except Exception as e:
                Logging.error(u"数据解析失败")
                Logging.debug(e)

        return topics

class Collection:
    """
        收藏
    """
    def __init__(self, token=None):
        self.token = token
        self.html  = ""
    def pull(self):
        url = "http://www.zhihu.com/collection/%s" % self.token
        res = requests.get(url)
        if res.status_code in [302, 301]:
            raise IOError("network error.")
        elif res.status_code != 200:
            raise IOError("unknow err.or.")
        else:
            # res.content | res.text 
            self.html = res.content

    def sync(self):
        pass
    def _fetch_all_questions(self):

        def fetch(page):
            url = "http://www.zhihu.com/collection/%s" % self.token
            res = requests.get(url, params={"page": page})

            Logging.info(u"正在下载第%s页收藏数据 ..." % str(page) )

            if res.status_code in [302, 301]:
                raise IOError("network error.")
            elif res.status_code != 200:
                raise IOError("unknow err.or.")
            else:
                # res.content | res.text 
                return res.content

        def parse(html):
            

            DOM = BeautifulSoup(html, 'html.parser')
            elems = DOM.find("div", id="zh-list-answer-wrap").find_all("div", class_="zm-item")

            for elem in elems:
                try:
                    this_is_one_answer = False
                    _qid = elem.find("div", class_="zm-item-rich-text")['data-resourceid']
                    try:
                        _elem = elem.find("h2", class_="zm-item-title").contents[0]
                        _title = re.sub("^\n+|\n+$", "", _elem.string ) 
                        _qtoken = _elem['href'].split("/")[-1]
                    except:
                        this_is_one_answer = True
                        Logging.warn(u"这是问题的子答案")
                    try:
                        

                        _elem2 = elem.find("div", class_="zm-item-answer")
                        _aid = _elem2['data-aid']
                        _atoken = _elem2['data-atoken']
                        _ctime = _elem2['data-created']
                        """
                            BUG:
                                下面的写入步骤存在 BUG, 主要是 DOM 的信息不规范引起的，需要分析后修正。

                        """
                        if this_is_one_answer:
                            items[_qid]['answers'].append( { "token": _atoken, "id": _aid, "ctime": _ctime } )
                        else:
                            items[_qid] = {"token": _qtoken, "id": _qid, "title": _title, "answers": [{ "token": _atoken, "id": _aid, "ctime": _ctime }] }
                    except Exception as e:
                        Logging.error(u"严重异常")
                        Logging.debug(e)
                        Logging.debug(_elem2)
                except Exception as e:
                    Logging.error(u"解析错误")
                    Logging.debug(e)
                    Logging.debug(elem)
            """
                border-pager
                <span><a href="?page=30">下一页</a></span>
                <span class="zg-gray-normal">下一页</span>
            """
            pages = DOM.find("div", class_="border-pager").find("div", class_="zm-invite-pager").find_all("span")
            next_el = pages[-1].find("a")
            if next_el:
                next_page = next_el['href'].split("=")[-1]
            else:
                next_page = 0

            return next_page

        html = self.html
        items = {}

        while True:
            np = parse(html)
            # questions += ques
            if np == 0:
                break
            else:
                html = fetch(np)
        return items.values()

    def parse(self):
        DOM = BeautifulSoup(self.html, 'html.parser')
        
        questions = self._fetch_all_questions()

        for q in questions:
            print "Title: %s \t Token: %s " % ( q['title'], str(q['token']) )

        # print questions



class RoundTable:
    """
        圆桌
    """
    def __init__(self, token=None):
        self.token = token
    def pull(self):
        url = "http://www.zhihu.com/roundtable/%s" % ( self.token )
        res = requests.get(url)
        if res.status_code in [302, 301]:
            raise IOError("network error.")
        elif res.status_code != 200:
            raise IOError("unknow err.or.")
        else:
            # res.content | res.text 
            self.html = res.content
    def sync(self):
        pass
    def parse(self):
        pass

class Explore:
    """
        发现新话题
    """
    def __init__(self):
        self.html = ""

    def pull(self):
        url = "http://www.zhihu.com/explore"
        res = requests.get(url)
        if res.status_code in [302, 301]:
            raise IOError("network error.")
        elif res.status_code != 200:
            raise IOError("unknow err.or.")
        else:
            # res.content | res.text 
            self.html = res.content
    def _fetch_questions(self):
        # 下载推荐问题列表
        url = "http://www.zhihu.com/node/ExploreAnswerListV2"
        offset = 0
    
        has_next = True
        questions = []

        while has_next:
            params = {"offset": offset,"type":"day"}
            
            Logging.info(u"正在下载推荐问题列表: %s" % json.dumps(params) )

            r = requests.get(url, params={"params": json.dumps(params)})
            if r.status_code != 200:
                raise IOError(u"network error.")
            try:
                DOM = BeautifulSoup(r.content, 'html.parser')
                items = DOM.find_all("div", class_="explore-feed")
                if items == None or len(items) == 0:
                    items = []
                    has_next = False
                for q in items:
                    try:
                        qlink = q.find("a", class_="question_link")['href']
                        qtoken = re.compile(r"\/question\/(\d+)\/", re.DOTALL).findall( qlink )[0]

                        questions.append( qtoken )

                    except Exception as e:
                        Logging.error(u"问题解析失败")
                        Logging.debug(e)
                        Logging.debug(q)
            except Exception as e:
                Logging.error(u"推荐问题列表解析失败")
                Logging.debug(e)
                Logging.debug(r.content)
                items = []
                has_next = False
            offset += len(items)
        return questions

    def _fetch_hot_favlists(self):
        # 热门收藏
        url = "http://www.zhihu.com/node/ExploreHotFavlistsInnerV2"
        offset = 0
            
        favs = []

        while True:
            """
                NOTE: 这个可以无限 请求下去，需要考虑限制条件。暂且不启用该功能。
            """
            if offset == 10:
                Logging.warn(u"收藏列表目前最多只换十批数据！")
                break
            params = {"offset": offset}

            Logging.info(u"下载热门收藏列表: %s" % json.dumps(params) )

            r = requests.get(url, params={"params": json.dumps(params) })
            if r.status_code != 200:
                Logging.warn(u"状态码不为200")
                Logging.warn(r.content)
                r.content = ""
            try:
                DOM = BeautifulSoup(r.content, "html.parser")
                items = DOM.find_all("li")
                if items == None or len(items) == 0: items = []
                for c in items:
                    """
                        <li>
                            <div class="content">
                                <a href="/collection/20320737" target="_blank">科普&amp;归纳</a>
                                <div class="meta">
                                    <span>273 人关注</span>
                                    <span class="zg-bull">&bull;</span>
                                    <span>76 个回答</span>
                                </div>
                            </div>
                        </li>
                    """
                    _el = c.find("div", class_="content").find("a")
                    _token = _el['href'].split("/")[-1]
                    _name = re.sub("^\n+|\n+$", "", _el.string)

                    favs.append( {"token": _token, "name": _name} )

            except Exception as e:
                Logging.error(u"热门收藏列表解析失败")
                Logging.debug(e)
                Logging.debug(r.content)

            offset += 1

        return favs
    def _fetch_topics(self):
        # 话题广场 － 发现新话题
        url = "http://www.zhihu.com/topics"


    def parse(self):

        DOM = BeautifulSoup(self.html, 'html.parser')
        # 热门问题
        questions = self._fetch_questions()
        
        sidebar = DOM.find("div", class_="zu-main-sidebar")

        # 热门圆桌
        roundtables = []
        roundtables_elems = sidebar.find("ul", class_="hot-roundtables").find_all("li")
        for el in roundtables_elems:
            """
                <li class="clearfix">
                    <a target="_blank" class="avatar-link" href="/roundtable/nobelprize2015">
                        <img src="https://pic1.zhimg.com/89b894a0aa0c5549f4d6699077b5e608_m.png" alt="Path" class="avatar 40" />
                    </a>
                    <div class="content">
                        <a href="/roundtable/nobelprize2015" target="_blank" data-tip="r$b$nobelprize2015">诺贝尔奖巡礼</a>
                        <div class="meta">
                            <span>4673 人关注</span>
                            <span class="zg-bull">•</span>
                            <span>52 个问题</span>
                        </div>
                    </div>
                </li>
            """
            _el = el.find("div", class_="content").find("a")
            _token = _el['href'].split("/")[-1]
            _name = re.sub("^\n+|\n+$", "", _el.string)
            
            roundtables.append( {"token": _token, "name": _name} )

        # 热门话题
        topics = []
        topics_elems = sidebar.find("ul", class_="hot-topics").find_all("li")
        for el in topics_elems:
            """
                <li class="clearfix">
                    <a target="_blank" class="avatar-link" href="/topic/19555662" data-tip="t$b$19555662">
                        <img src="https://pic3.zhimg.com/9780e0f8dbcfd240f76d22916b59bd36_m.png" alt="创业融资" class="avatar 40">
                    </a>
                    <div class="content">
                        <a href="/topic/19555662" target="_blank" data-tip="t$b$19555662">创业融资</a>
                        <div class="meta">
                            <span>31986 人关注</span>
                        </div>
                    </div>
                    <div class="bottom">
                        <a class="question_link" target="_blank" href="/question/36423536">
                            投资人投资初创公司的投资方式有哪几种？实际中都是根据什么原则去选择的？
                        </a>
                    </div>
                </li>
            """
            _el = el.find("div", class_="content").find("a")
            _token = _el['href'].split("/")[-1]
            _name = re.sub("^\n+|\n+$", "", _el.string)
            
            topics.append( {"token": _token, "name": _name} )

        # 热门收藏
        hot_collections = self._fetch_hot_favlists()

        
        print questions
        print roundtables
        print topics
        print hot_collections

    def export(self, result=[], format="rst"):
        pass





class Search:
    """
        搜索接口
            人 | 问题 | 话题

    """
    def __init__(self):
        pass
    @staticmethod
    def people(keywords=None, limit=-1):
        return People.search(keywords=keywords)
    @staticmethod
    def question(keywords=None, limit=-1):
        return Question.search(keywords=keywords)
    @staticmethod
    def topic(keywords=None, limit=-1):
        return Topic.search(keywords=keywords)

class Inbox:
    def __init__(self):
        self.inbox = []
        self.html = ""
    def pull(self):
        url = "http://www.zhihu.com/inbox"
        res = requests.get(url)
        if res.status_code in [302, 301]:
            raise IOError("network error.")
        elif res.status_code != 200:
            raise IOError("unknow err.or.")
        else:
            # res.content | res.text 
            self.html = res.content
    def sync(self):
        pass
    def parse(self, html):
        pass
    def export(self, format="rst"):
        pass

class Message:
    def __init__(self, token=None):
        self.token = token
    def pull(self):
        url = ""
        res = requests.get(url)
        if res.status_code in [302, 301]:
            raise IOError("network error.")
        elif res.status_code != 200:
            raise IOError("unknow err.or.")
        else:
            # res.content | res.text 
            self.html = res.content
    def sync(self):
        pass
    def parse(self):
        pass
    def export(self, format="rst"):
        pass
    @staticmethod
    def search(keywords):
        return Search.people(keywords)


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
    # token = "35564122"
    token = "31272454"
    token = "31272454"
    q = Question(token=token)
    q.pull()
    q.parse()

def test_people():
    token = "rio"
    p = People(token=token)
    p.pull()
    p.parse()

def test_explore():
    e = Explore()
    e.pull()
    e.parse()

def test_search():
    questions = Search.question(keywords="埃及")
    for p in questions:
        print "id: %s\t token: %s\t title: %s" % ( p['id'], p['token'], p['title'] )

    peoples = Search.people(keywords="埃及")
    for p in peoples:
        print "id: %s\t token: %s\t name: %s" % ( p['id'], p['token'], p['name'] )

    topics = Search.topic(keywords="埃及")
    for p in topics:
        print "id: %s\t token: %s\t name: %s" % ( p['id'], p['token'], p['name'] )
def test_collection():
    token = "20432495"
    c = Collection(token=token)
    c.pull()
    c.parse()

def test():
    # test_question()
    # test_people()
    # test_explore()
    # test_search()
    test_collection()

if __name__ == '__main__':
    test()
