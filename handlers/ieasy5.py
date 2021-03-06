# -*- coding: utf-8 -*- 
"""加拿大加易模块

@author: HSS
@since: 2014-11-30
@summary: 加拿大加易中文网

"""
import requests, re, random, logging
from bs4 import BeautifulSoup

import config
from utils import *


def login_ieasy5(sess, src):
    """ 加易登录函数

    @param sess:    requests.Session()
    @type sess:     Session

    @param src:        用户名，密码，回复内容，等等。
    @type src:         dict

    @return:           是否登录成功
    @rtype:            bool

    """
    host = 'http://ieasy5.com/bbs/'
    resp = sess.get('http://ieasy5.com/bbs/thread.php?fid=3')
    soup = BeautifulSoup(resp.content)
    form = soup.find('form', attrs={'name': 'login_FORM'})

    payload = get_datadic(form, 'gbk')
    payload['pwuser'] = src['username'].decode('utf8').encode('gbk')
    payload['pwpwd'] = src['password'].decode('utf8').encode('gbk')
    # 发送登录post包
    resp = sess.post(host+form['action'], data=payload)
    # 若指定字样出现在response中，表示登录成功
    if u'您已经顺利登录' not in resp.content.decode('gbk'):
        return False
    return True


# Coding: gb2312
# Captcha: required
# Login: not required
def reply_ieasy5_news(post_url, src):
    if src['TTL'] == 0:
        raise RAPMaxTryException('captcha')
    logger = RAPLogger(post_url)

    host = get_host(post_url)
    s = RAPSession(src)

    # Step 1: Load post page
    r = s.get(post_url)
    soup = BeautifulSoup(r.content)
    form_url = host + soup.find('iframe', attrs={'id': 'o'})['src']

    # Step 2: Get real form html
    r = s.get(form_url)
    soup = BeautifulSoup(r.content)

    # Step 3: Retrieve captcha and crack
    r = s.get(host + 'e/ShowKey?v=pl' + str(random.random()),
        headers={
            'Accept': config.accept_image,
            'Referer': post_url,
        })
    seccode = crack_captcha(r.content)

    # Step 4: Submit and check
    form = soup.find('form', attrs={'name': 'saypl'})
    payload = get_datadic(form, 'gb2312')
    if 'nickname' in src:
        payload['username'] = src['nickname'].decode('utf8').encode('gb2312')
    payload['saytext'] = src['content'].decode('utf8').encode('gb2312')
    payload['key'] = seccode

    r = s.post(host + 'e/enews/index.php', data=payload)
    soup = BeautifulSoup(r.content)
    tag = soup.find('span', attrs={'class': 'rred'})
    if u'评论成功' not in tag.text:
        logger.error('Reply Error: ' + tag.text)
        if u'验证码' in tag.text:
            # Captcha error, retry
            src['TTL'] -= 1
            return reply_ieasy5_news(post_url, src)
        return (False, str(logger))
    logger.info('Reply OK')
    return (True, str(logger))


# Coding: gbk
# Captcha: not required
# Login: required
def reply_ieasy5_forum(post_url, src):
    logger = RAPLogger(post_url)
    host = 'http://ieasy5.com/bbs/'
    sess = RAPSession(src)

    if not login_ieasy5(sess, src):
        logger.error('Login Error')
        return (False, str(logger))
    logger.info('Login OK')

    # Step 2: Load post page
    resp = sess.get(post_url)
    soup = BeautifulSoup(resp.content)
    form = soup.find('form', attrs={'id': 'anchor'})

    # Step 3: Submit
    payload = get_datadic(form, 'gbk')
    if 'subject' in src:
        payload['atc_title'] = src['subject'].decode('utf8').encode('gbk')
    payload['atc_content'] = src['content'].decode('utf8').encode('gbk')

    resp = sess.post(host + form['action'], data=payload)
    soup = BeautifulSoup(resp.content)
    tag = soup.find('div', attrs={'class': 'cc'})
    if u'跳转' not in tag.find('a').text:
        logger.error('Reply Error')
        return (False, str(logger))
    logger.info('Reply OK')
    return (True, str(logger))


def post_ieasy5_forum(post_url, src):
    """加拿大加易论坛发主贴模块

    @author: HSS
    @since: 2015-1-24

    @param sess:    requests.Session()
    @type sess:     Session

    @param post_url:   板块地址 http://ieasy5.com/bbs/thread.php?fid=3
    @type post_url:    str

    @param src:        用户名，密码，标题，帖子内容等等。
    @type src:         dict

    @return:           是否发帖成功
    @rtype:            bool

    """
    host = 'http://ieasy5.com/bbs/'
    logger = RAPLogger(post_url)
    sess = RAPSession(src)
    # Step 1: 登录
    if not login_ieasy5(sess, src):
        logger.error(' Login Error')
        return ('', str(logger))
    logger.info(' Login OK')

    fid = re.findall(r'fid=(\d*)', post_url)[0]
    resp = sess.get('http://ieasy5.com/bbs/post.php?fid='+fid)
    soup = BeautifulSoup(resp.content)
    form = soup.find('form', attrs={'id': 'mainForm'})

    _hexie = re.findall(r'document\.FORM\._hexie\.value.*=.*\'(.*?)\'',resp.content)[0]
    payload = get_datadic(form)
    payload['atc_title'] = src['subject'].decode('utf8').encode('gbk','ignore')
    payload['atc_content'] = src['content'].decode('utf8').encode('gbk','ignore')
    payload['step'] = '2'
    payload['pid'] = ''
    payload['action'] = 'new'
    payload['fid'] = fid
    payload['tid'] = '0'
    payload['article'] = '0'
    payload['special'] = '0'
    payload['_hexie'] = _hexie
    payload['atc_hide'] = '0'

    payload['atc_requireenhide'] = '0'
    payload['atc_anonymous'] = '0'
    payload['atc_requiresell'] = '0'
    payload['atc_convert'] = '0'
    payload['atc_newrp'] = '0'
    payload['attachment_1'] = ''
    payload['atc_desc1'] = ''
    payload['atc_credittype'] = 'money'
    payload['att_special1']= '0'
    payload['att_ctype1'] = 'money'
    payload['atc_needrvrc1']= '0'
    # print payload
    resp = sess.post(host + form['action'], data=payload)
    soup = BeautifulSoup(resp.content)
    tag = soup.find('div', attrs={'class': 'cc'})
    if u'跳转' not in tag.find('a').text:
        logger.error('Post Error')
        return ('', str(logger))
    logger.info('Post OK')
    url = host + tag.find('a')['href']
    return (url, str(logger))


def get_account_info_ieasy5_forum(src):
    logger = RAPLogger('ieasy5=>' + src['username'])
    sess = RAPSession(src)

    # Step 1: 登录
    if not login_ieasy5(sess, src):
        logger.error(' Login Error')
        return ({}, str(logger))
    logger.info(' Login OK')

    resp = sess.get('http://www.ieasy5.com/bbs/')
    uid = re.findall("winduid = '(\d+)'", resp.content)[0]
    head_image = 'http://www.ieasy5.com/bbs/' + re.findall('><i><img src="(.*?)"', resp.content)[0]
    account_class = re.findall(u'等级: (.*?)<'.encode('gbk'), resp.content)[0].decode('gbk').encode('utf8')
    count_post = int(re.findall(u'帖子: (\d+)'.encode('gbk'), resp.content)[0])
    # 威望 代替 回复
    count_reply = int(re.findall(u'威望: (\d+)'.encode('gbk'), resp.content)[0])
    # 铜币 代替 登录次数
    login_count = int(re.findall(u'铜币: (\d+)'.encode('gbk'), resp.content)[0])

    resp = sess.get('http://www.ieasy5.com/bbs/u.php?a=info&uid=' + uid)
    account_score = int(re.findall(u'总积分：</span><span class="s2 b">(\d+)'.encode('gbk'), resp.content)[0])
    time_register = re.findall(u'注册时间.*?(\d.*?)<'.encode('gbk'), resp.content, re.S)[0]
    time_last_login = re.findall(u'最后登录.*?(\d.*?)<'.encode('gbk'), resp.content, re.S)[0]

    account_info = {
        #########################################
        # 用户名
        'username':src['username'],
        # 密码
        'password':src['password'],
        # 头像图片
        'head_image':head_image,
        #########################################
        # 积分
        'account_score':account_score,
        # 等级
        'account_class':account_class,
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
    logger.info('Get account info OK')
    return (account_info, str(logger))
    