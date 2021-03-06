# -*- coding: utf-8 -*-
"""RAP Server（beanstalkc version）

@author: HSS
@since: 2014-10-229
@summary: RAP Server

"""
import re
import sys
import json
import threading
import logging
import logging.config

import beanstalkc
import MySQLdb
import yaml
import chardet
import requests
import tldextract

import rap


def get_url_title(post_url):
    """Get url title with utf8 encoding format.

    @param post_url:    帖子地址
    @type post_url:     str

    @return:            帖子标题
    @rtype：            str
    """
    resp = requests.get(post_url)
    title = re.findall('<title>(.*?)</title>', resp.content, re.I)[0]
    result = chardet.detect(title)  
    return title.decode(result['encoding'])


def db_connect():
    """数据库连接

    @return:            connection
    @rtype:             MySQLdb.connections.Connection
    """
    return MySQLdb.connect(CONFIG['db']['ip'],
                           CONFIG['db']['username'],
                           CONFIG['db']['password'],
                           CONFIG['db']['dbname'],
                           charset='utf8')


def get_site_sign(post_url):
    """获取URL特征

    参考https://github.com/john-kurkowski/tldextract
    >>> tldextract.extract('http://forums.bbc.co.uk/') # United Kingdom
    ExtractResult(subdomain='forums', domain='bbc', suffix='co.uk')
    我们关注的site_sign实际上就是domain

    @param post_url:    帖子地址
    @type post_url:     str

    @return:            URL特征
    @rtype:             str
    """

    return tldextract.extract(post_url).domain


def reply(job_body):
    """回复帖子，并将信息记录到数据库中

    @param job_body:    beanstalk获取的内容
    @type job_body:     json
    """

    job_id = job_body['job_id']
    post_url = job_body['post_url']
    src = job_body['src']

    # 获取帖子标题
    if 'url_title' in src:
        # 标题已知则直接使用
        url_title = src['url_title']
    else:
        # 标题未知则立即获取
        try:
            url_title = get_url_title(post_url)
        except:
            url_title = '获取标题失败'
            
    # 连接数据库
    conn = db_connect()
    cursor = conn.cursor()

    # 将beanstalkc队列中获取到的信息记录到数据库中
    # 将初始状态（status）置为 1 --- 正在发送
    count = cursor.execute('update reply_job set '
                           'status = 1, '
                           'url_title = %s, '
                           'update_time = now() '
                           'where job_id = %s', (url_title, job_id))
    # 将 "正在发送" 状态提交
    conn.commit()
    
    # 调用回复函数
    r, log = rap.reply(post_url, src)

    # 判断回复结果状态
    # 2 --- OK
    # 3 --- Error.
    status = 2 if r else 3
    count = cursor.execute('update reply_job set status = %s, error = %s, update_time = now() where job_id = %s',
                   (status, log, job_id))
    # 将 "发送成功" 或 "发送失败" 状态提交
    conn.commit()

    if 'username' not in src:
        # 匿名情况，不需要更新账户信息
        return

    # 更新账户信息
    params = {
        'username': src['username'],
        'is_invalid': 1 if 'Login Error' in log else 0, 
        'site_url': '%' + get_site_sign(post_url) + '%',
    }
    info, log = rap.get_account_info(post_url, {'username': src['username'], 'password': src['password']})
    if info == {}:
        # 获取账户信息未实现或者错误
        count = cursor.execute('update account set is_invalid = %(is_invalid)s where username = %(username)s and site_sign in (select site_sign from site where site_url like %(site_url)s)', params)
    else:
        # 更新账户信息
        params.update(info)
        sql_str = ('update account set '
                   'head_image = %(head_image)s, '
                   'account_score = %(account_score)s, '
                   'account_class = %(account_class)s, '
                   'time_register = %(time_register)s, '
                   'time_last_login = now(), '
                   'login_count = %(login_count)s, '
                   'count_post = %(count_post)s, '
                   'count_reply = %(count_reply)s, '
                   'is_invalid = %(is_invalid)s '
                   'where username = %(username)s and site_sign in '
                   '(select site_sign from site where site_url like %(site_url)s)')
        count = cursor.execute(sql_str, params)

    conn.commit()
    conn.close()


def post(job_body):
    """发表主帖，并将信息记录到数据库中

    @param job_body:    beanstalk获取的内容
    @type job_body:     json
    """

    job_id = job_body['job_id']
    post_url = job_body['post_url']
    src = job_body['src']

    # 连接数据库
    conn = db_connect()
    cursor = conn.cursor()

    # 将beanstalkc队列中获取到的信息记录到数据库中
    # 将初始状态（status）置为 1 --- 正在发送
    count = cursor.execute('update post_job set '
                           'status = 1, '
                           'update_time = now() '
                           'where id = %s', (job_id,))
    # 将 "正在发送" 状态提交
    conn.commit()
    
    # 调用发帖函数
    url, log = rap.post(post_url, src)

    # 判断发帖状态
    # 2 --- OK
    # 3 --- Error.
    status = 2 if url != '' else 3
    count = cursor.execute('update post_job set status = %s, error = %s, update_time = now(), article_url = %s where id = %s',
                   (status, log, url, job_id))
    # 将 "发送成功" 或 "发送失败" 状态提交
    conn.commit()

    # 更新账户信息
    params = {
        'username': src['username'],
        'is_invalid': 1 if 'Login Error' in log else 0, 
        'site_url': '%' + get_site_sign(post_url) + '%',
    }
    info, log = rap.get_account_info(post_url, {'username': src['username'], 'password': src['password']})
    if info == {}:
        # 获取账户信息未实现或者错误
        count = cursor.execute('update account set is_invalid = %(is_invalid)s where username = %(username)s and site_sign in (select site_sign from site where site_url like %(site_url)s)', params)
    else:
        # 更新账户信息
        params.update(info)
        sql_str = ('update account set '
                   'head_image = %(head_image)s, '
                   'account_score = %(account_score)s, '
                   'account_class = %(account_class)s, '
                   'time_register = %(time_register)s, '
                   'time_last_login = now(), '
                   'login_count = %(login_count)s, '
                   'count_post = %(count_post)s, '
                   'count_reply = %(count_reply)s, '
                   'is_invalid = %(is_invalid)s '
                   'where username = %(username)s and site_sign in '
                   '(select site_sign from site where site_url like %(site_url)s)')
        count = cursor.execute(sql_str, params)

    conn.commit()
    conn.close()


def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_dict(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv


def main():
    """Main eventloop."""

    if len(sys.argv) != 2 or sys.argv[1] not in ['in', 'out']:
        logging.critical('Usage: rap_server.py in|out')
        sys.exit(1)

    try:
        # 连接beanstalkc服务器
        bean = beanstalkc.Connection(CONFIG['beanstalk']['ip'],
                                     CONFIG['beanstalk']['port'])
        # 监听rap_server
        queue = 'rap_in' if sys.argv[1] == 'in' else 'rap_out'
        bean.watch(queue)
        bean.ignore('default')
    except:
        logging.critical('Cann\'t connect to beanstalk server')
        return

    while True:
        # 开启守护进程，持续接收信息
        job = bean.reserve()
        try:
            job_body = json.loads(job.body, object_hook=_decode_dict)
            if 'method' not in job_body:
                logging.error('Abort message without method')
            elif job_body['method'] == 'post':
                post(job_body)
            elif job_body['method'] == 'reply':
                reply(job_body)
            else:
                logging.error('Abort message with method = ' + job_body['method'])
        except:
            logging.exception('Exception in queue')
        finally:
            job.delete()


if __name__ == '__main__':
    # Load local configurations.
    CONFIG = yaml.load(open('config.yaml'))
    # Logging config.
    logging.config.dictConfig(CONFIG)

    main()
