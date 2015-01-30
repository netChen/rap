# -*- coding: utf-8 -*- 

import requests, re, random, logging
from bs4 import BeautifulSoup
from hashlib import md5

import config
from utils import *


def login_wolfax(sess, src):
    host = 'http://bbs.wolfax.com/'
    resp = sess.get(host)
    soup = BeautifulSoup(resp.content)
    form = soup.find('form', attrs={'id': 'lsform'})
    payload = get_datadic(form)
    payload['username'] = src['username']
    payload['password'] = md5(src['password']).hexdigest()

    resp = sess.post(host + form['action'], data=payload)
    soup = BeautifulSoup(resp.content)
    tag = soup.find('div', attrs={'id': 'messagetext'})
    if tag:
        return False
    return True


# Coding: utf8
# Captcha: arithmetic
# Login: required
def reply_wolfax_forum(post_url, src):
    if src['TTL'] == 0:
        raise RAPMaxTryException('captcha')
    logger = RAPLogger(post_url)

    host = get_host(post_url)
    sess = RAPSession(src)

    if not login_wolfax(sess, src):
        logger.error('Login Error')
        return (False, str(logger))
    logger.info('Login OK')

    # Step 2: Load post page
    resp = sess.get(post_url)
    soup = BeautifulSoup(resp.content)
    form = soup.find('form', attrs={'id':'fastpostform'})
    idhash = re.findall('secqaa_(\w*)', str(form))[0]

    # Step 3: Retrieve captcha question and crack
    resp = sess.get(host + 'misc.php',
        params={
            'mod': 'secqaa',
            'action': 'update',
            'idhash': idhash,
        },
        headers={'Referer': post_url})

    # Crack the silly captcha question
    # Server responses are as follows: 
    # '77 + 5 = ?'
    # '26 - 5 = ?'
    # ...
    a, op, b = re.findall("'(\d+) (.) (\d+)", resp.content)[0]
    seccode = int(a) + int(b) if op == '+' else int(a) - int(b)
    logger.info('%s %s %s = %d' % (a, op, b, seccode))

    # Step 4: Submit and check
    payload = get_datadic(form)
    if 'subject' in src:
        payload['subject'] = src['subject']
    payload['secqaahash'] = idhash
    payload['secanswer'] = seccode
    payload['message'] = src['content']

    resp = sess.post(host + form['action'], data=payload)
    soup = BeautifulSoup(resp.content)
    tag = soup.find('div', attrs={'id': 'messagetext'})
    if tag:
        logger.error('Reply Error: ' + tag.find('p').text)
        # Captcha cracking is absolutely right, unless the schema has changed
        # It's not necessary to retry for captcha error
        # But it is necessary now...
        if u'验证问答' in tag.find('p').text:
            src['TTL'] -= 1
            return reply_wolfax_forum(post_url, src)
        return (False, str(logger))
    logger.info('Reply OK')
    return (True, str(logger))


def post_wolfax_forum(post_url, src):
    if src['TTL'] == 0:
        raise RAPMaxTryException('captcha')
    logger = RAPLogger(post_url)

    host = get_host(post_url)
    sess = RAPSession(src)

    if not login_wolfax(sess, src):
        logger.error('Login Error')
        return ('', str(logger))
    logger.info('Login OK')

    # Step 2: Load post page
    resp = sess.get(post_url)
    soup = BeautifulSoup(resp.content)
    form = soup.find('form', attrs={'id':'fastpostform'})
    idhash = re.findall('secqaa_(\w*)', str(form))[0]

    # Step 3: Retrieve captcha question and crack
    resp = sess.get(host + 'misc.php',
        params={
            'mod': 'secqaa',
            'action': 'update',
            'idhash': idhash,
        },
        headers={'Referer': post_url})

    # Crack the silly captcha question
    # Server responses are as follows: 
    # '77 + 5 = ?'
    # '26 - 5 = ?'
    # ...
    a, op, b = re.findall("'(\d+) (.) (\d+)", resp.content)[0]
    seccode = int(a) + int(b) if op == '+' else int(a) - int(b)
    logger.info('%s %s %s = %d' % (a, op, b, seccode))

    # Step 4: Submit and check
    payload = get_datadic(form)
    payload['subject'] = src['subject']
    payload['secqaahash'] = idhash
    payload['secanswer'] = seccode
    payload['message'] = src['content']

    resp = sess.post(host + form['action'], data=payload)
    soup = BeautifulSoup(resp.content)
    tag = soup.find('div', attrs={'id': 'messagetext'})
    if tag:
        logger.error('Post Error: ' + tag.find('p').text)
        # Captcha cracking is absolutely right, unless the schema has changed
        # It's not necessary to retry for captcha error
        # But it is necessary now...
        if u'验证问答' in tag.find('p').text:
            src['TTL'] -= 1
            return post_wolfax_forum(post_url, src)
        return ('', str(logger))
    logger.info('Post OK')
    return (resp.url, str(logger))


def reply_wolfax_blog(post_url, src):
    if src['TTL'] == 0:
        raise RAPMaxTryException('captcha')
    logger = RAPLogger(post_url)

    host = get_host(post_url)
    sess = RAPSession(src)

    if not login_wolfax(sess, src):
        logger.error('Login Error')
        return (False, str(logger))
    logger.info('Login OK')

    # Step 2: Load post page
    resp = sess.get(post_url)
    soup = BeautifulSoup(resp.content)
    uid = re.findall('&id=(\d+)', post_url)[0]
    form = soup.find('form', attrs={'id': 'quickcommentform_' + uid})
    idhash = re.findall('secqaa_(\w*)', str(form))[0]

    # Step 3: Retrieve captcha question and crack
    resp = sess.get(host + 'misc.php',
        params={
            'mod': 'secqaa',
            'action': 'update',
            'idhash': idhash,
        },
        headers={'Referer': post_url})

    # Crack the silly captcha question
    # Server responses are as follows: 
    # '77 + 5 = ?'
    # '26 - 5 = ?'
    # ...
    a, op, b = re.findall("'(\d+) (.) (\d+)", resp.content)[0]
    seccode = int(a) + int(b) if op == '+' else int(a) - int(b)
    logger.info('%s %s %s = %d' % (a, op, b, seccode))

    # Step 4: Submit and check
    payload = get_datadic(form)
    if 'subject' in src:
        payload['subject'] = src['subject']
    payload['secqaahash'] = idhash
    payload['secanswer'] = seccode
    payload['message'] = src['content']

    resp = sess.post(host + form['action'], data=payload)
    soup = BeautifulSoup(resp.content)
    tag = soup.find('div', attrs={'id': 'messagetext'})
    if tag:
        logger.error('Reply Error: ' + tag.find('p').text)
        # Captcha cracking is absolutely right, unless the schema has changed
        # It's not necessary to retry for captcha error
        # But it is necessary now...
        if u'验证问答' in tag.find('p').text:
            src['TTL'] -= 1
            return reply_wolfax_forum(post_url, src)
        return (False, str(logger))
    logger.info('Reply OK')
    return (True, str(logger))


def post_wolfax_blog(post_url, src):
    if src['TTL'] == 0:
        raise RAPMaxTryException('captcha')
    logger = RAPLogger(post_url)

    host = 'http://home.wolfax.com/'
    sess = RAPSession(src)

    if not login_wolfax(sess, src):
        logger.error('Login Error')
        return (False, str(logger))
    logger.info('Login OK')

    resp = sess.get(host + 'home.php?mod=spacecp&ac=blog')
    soup = BeautifulSoup(resp.content)
    form = soup.find('form', attrs={'id': 'ttHtmlEditor'})
    print form
    idhash = re.findall('secqaa_(\w*)', str(form))[0]

    # Step 3: Retrieve captcha question and crack
    resp = sess.get(host + 'misc.php',
        params={
            'mod': 'secqaa',
            'action': 'update',
            'idhash': idhash,
        },
        headers={'Referer': post_url})

    # Crack the silly captcha question
    # Server responses are as follows: 
    # '77 + 5 = ?'
    # '26 - 5 = ?'
    # ...
    a, op, b = re.findall("'(\d+) (.) (\d+)", resp.content)[0]
    seccode = int(a) + int(b) if op == '+' else int(a) - int(b)
    logger.info('%s %s %s = %d' % (a, op, b, seccode))

    # Step 4: Submit and check
    payload = get_datadic(form)
    if 'subject' in src:
        payload['subject'] = src['subject']
    payload['secqaahash'] = idhash
    payload['secanswer'] = seccode
    payload['message'] = src['content']

    resp = sess.post(host + form['action'], data=payload)
    soup = BeautifulSoup(resp.content)
    tag = soup.find('div', attrs={'id': 'messagetext'})
    if tag:
        logger.error('Reply Error: ' + tag.find('p').text)
        # Captcha cracking is absolutely right, unless the schema has changed
        # It's not necessary to retry for captcha error
        # But it is necessary now...
        if u'验证问答' in tag.find('p').text:
            src['TTL'] -= 1
            return reply_wolfax_forum(post_url, src)
        return (False, str(logger))
    logger.info('Reply OK')
    return (True, str(logger))


def get_account_info_wolfax_forum(src):
    logger = RAPLogger('wolfax=>' + src['username'])
    sess = RAPSession(src)

    if not login_wolfax(sess, src):
        logger.error('Login Error')
        return ({}, str(logger))
    logger.info('Login OK')

    resp = sess.get('http://bbs.wolfax.com')
    uid = re.findall('http://home.wolfax.com/s-uid-(\d+)', resp.content)[0]
    resp = sess.get('http://home.wolfax.com/home.php?mod=space&uid=%s&do=profile' % uid)

    head_image = re.findall('avtm"><img src="(.*?)"', resp.content)[0]
    account_score = int(re.findall('积分</em>(\d+)', resp.content)[0])
    account_class = re.findall('用户组.*_blank">(.*?)<', resp.content)[0]
    time_register = re.findall('注册时间</em>(.*?)<', resp.content)[0]
    time_last_login = re.findall('最后访问</em>(.*?)<', resp.content)[0]
    login_count = 0
    count_post = int(re.findall('主题数 (\d+)', resp.content)[0])
    count_reply = int(re.findall('回帖数 (\d+)', resp.content)[0])

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
