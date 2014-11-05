# -*- coding: utf-8 -*-
"""凯迪回复模块（凯迪社区）

@author: HSS
@since: 2014-10-20
@summary: 凯迪社区

@var CHARSET: 凯迪社区网页编码
@type CHARSET: str

"""
import re

from bs4 import BeautifulSoup

import utils

CHARSET = 'gb2312'

def login_kdnet(sess, src):
    """ 凯迪社区登录函数

    @param sess:    requests.Session()
    @type sess:     Session

    @param src:        用户名，密码，回复内容，等等。
    @type src:         dict

    @return:           是否登录成功
    @rtype:            bool

    """
    payload = {
        'a':'login',
        'username':src['username'],
        'password':src['password'],
        'last_url':'http://user.kdnet.net/'
    }
    # 发送登录post包
    resp = sess.post('http://user.kdnet.net/user.asp', data=payload)
    # 若指定字样出现在response中，表示登录成功
    if 'msg' in resp.content:
        return False
    return True

def reply_kdnet(post_url, src):
    """ 凯迪社区回复函数

        - Name:     凯迪社区
        - Feature:  club.kdnet.net
        - Captcha:  NO
        - Login:    NO

    @param post_url:   帖子地址
    @type post_url:    str

    @param src:        用户名，密码，回复内容，等等。
    @type src:         dict
    
    @return:           是否回复成功
    @rtype:            bool

    """
    logger = utils.RAPLogger(post_url)
    sess = utils.RAPSession(src)
    resp = sess.get(post_url)

    # 获得回复iframe
    iframe = re.findall('<iframe src=\"(.*?)\"', resp.content)[0]
    resp = sess.get(iframe.decode(CHARSET))
    soup = BeautifulSoup(resp.content)
    # 获得回复form
    form = soup.find('form', attrs={'id': 't_form'})
    # 获得boardid，作为post参数
    boardid = re.findall(r'boardid=(.*\d)', post_url)[0]
    # 构造回复参数
    payload = utils.get_datadic(form)
    payload['UserName'] = src['username']
    payload['password'] = src['password']
    payload['body'] = src['content'].decode('utf8').encode(CHARSET)
    # 回复地址
    reply_url = 'http://upfile1.kdnet.net/do_lu_shuiyin.asp?'\
        + 'action=sre&method=fastreply&BoardID='
    # 发送回复post包
    resp = sess.post(reply_url + boardid, data=payload)
    # 若指定字样出现在response中，表示回复成功
    if u'成功回复'.encode(CHARSET) not in resp.content:
        logger.error(' Reply Error')
        return (False, str(logger))
    logger.info(' Reply OK')
    return (True, str(logger))

def get_account_info_kdnet(src):
    """ 凯迪社区账户信息获取函数

    @param src:        用户名，密码
    @type src:         dict

    @return:           账户信息
    @rtype:            dict
    """
    logger = utils.RAPLogger(src['username'])
    sess = utils.RAPSession(src)

    faild_info = {'Error':'Failed to get account info'}
    # Step 1: 登录
    if not login_kdnet(sess, src):
        logger.error(' Login Error')
        return (faild_info, str(logger))
    logger.info(' Login OK')

    resp = sess.get('http://user.kdnet.net/index.asp')
    head_image = re.findall(r'<img id=\"userface_img_index\" onerror=\"this.src = duf_190_190;\" src=\"(.*?)\"', resp.content)[0]

    acount_score = ''
    acount_class = ''

    content = resp.content.decode(CHARSET).encode('utf8')
    # print content
    time_register = re.findall(r'注册时间：(.*?)<', content)[0]
    time_last_login = re.findall(r'上次登录：(.*?)<', content)[0]
    login_count = re.findall(r'登录次数：(\d*)<', content)[0]

    resp = sess.get('http://user.kdnet.net/posts.asp')
    content = resp.content.decode(CHARSET).encode('utf8')
    if '还未发表内容' in content:
        count_post = 0
    else:
        count_post = re.findall(r'共(\d*)条记录', content)[0]


    resp = sess.get('http://user.kdnet.net/reply.asp')
    content = resp.content.decode(CHARSET).encode('utf8')
    if '还未发表内容' in content:
        count_reply = 0
    else:
        count_reply = re.findall(r'共(\d*)条记录', content)[0]

    acount_info = {
        #########################################
        # 用户名
        'username':src['username'],
        # 密码
        'password':src['password'],
        # 头像图片
        'head_image':head_image,
        #########################################
        # 积分
        'acount_score':acount_score,
        # 等级
        'acount_class':acount_class,
        #########################################
        # 注册时间
        'time_register':time_register,
        # 最近登录时间
        'time_last_login':time_last_login,
        # 登录次数
        'login_count':login_count,
        #########################################
        # 主帖数
        'count_post':count_post,
        # 回复数
        'count_reply':count_reply
        #########################################
    }
    return (acount_info, str(logger))