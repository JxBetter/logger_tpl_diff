"""
模板不匹配问题 快速定位脚本

### 脚本位置

    logger@121.43.182.116:/home/logger/wenbo/autocheck.py

### 使用示例：

    python /home/logger/wenbo/autocheck.py 13512345678

### 脚本的原理

1.根据用户提供的手机号，执行下面命令获取发送记录以及记录所在的IP地址，用户uid：

    pssh -h /home/admin/cluster/rest-host -t 1000 -i grep 13512345678 /home/admin/weike-rest/logs/logged-sms-trace.log

2.根据IP地址和uid再执行下面命令获取缓存：

    pssh -H 123.123.123.123 -t 1000 -i curl 'http://127.0.0.1:8105/rest/util/debug/tpl/cache/get?uid=888888888888888888'

3.将第1步获取的发送内容 和 第2步获取的用户模板 依次进行匹配，找出最接近的那个模板。

    匹配原理是判断相等的文本数量，取最多的。

4.剩下的就简单了

by wangwenbo@qipeng.com
2019.03.05
"""

import difflib
import sys
import os
import re
import json
import paramiko
from pyquery import PyQuery

"""
获取用户请求日志，格式为：

[1] 14:14:29 [FAILURE] 192.168.30.12 Exited with error code 1
[2] 14:14:30 [FAILURE] 172.16.10.2 Exited with error code 1
[3] 14:14:30 [FAILURE] 172.16.10.3 Exited with error code 1
[4] 14:14:32 [FAILURE] 192.168.30.14 Exited with error code 1
[5] 14:14:33 [SUCCESS] 192.168.10.14
2019-03-04 09:56:07.524	INFO	20190304	890000000020628152	......
2019-03-04 10:34:29.910	INFO	20190304	890000000020628152	......
[6] 14:14:33 [FAILURE] 192.168.200.21 Exited with error code 1
[7] 14:14:33 [FAILURE] 192.168.200.22 Exited with error code 1
[8] 14:14:38 [SUCCESS] 192.168.10.12
2019-03-04 10:10:32.901	INFO	20190304	890000000020628152	......
[9] 14:14:38 [FAILURE] 192.168.30.46 Exited with error code 1
[10] 14:14:41 [FAILURE] 192.168.30.47 Exited with error code 1
[11] 14:14:44 [FAILURE] 192.168.10.13 Exited with error code 1
[12] 14:14:50 [FAILURE] 192.168.30.13 Exited with error code 1
"""


def getUserLog(ssh, arg):
    sub1 = arg[0]
    sub2 = ''

    isdate = False
    date = ''
    for i in range(1, len(arg)):
        if isdate:
            date = '.' + arg[i] + '.log'
            isdate = False
        elif arg[i] == '-d':
            isdate = True
        else:
            sub2 = sub2 + ' | grep ' + arg[i]

    cmd = "pssh -h /home/admin/cluster/rest-host -t 1000 -i 'grep " + sub1 + " /home/admin/weike-rest/logs/logged-sms-trace.log" + date + sub2 + "'"
    print(cmd)
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        log = stdout.read().decode()
        print(log)
        return log
    except Exception as e:
        print(e)
        return ''


"""
获取用户模板缓存，格式为：

[1] 15:02:39 [SUCCESS] 192.168.10.14
{"success":false,"total":17,"datas":[{"id":2749008,"templateText":"Hello ......
"""


def getUserTplCache(ssh, ip='', uid=''):
    cmd = "pssh -H %s -t 1000 -i curl 'http://127.0.0.1:8105/rest/util/debug/tpl/cache/get?uid=%s'" % (ip, uid)
    print(cmd)
    stdin, stdout, stderr = ssh.exec_command(cmd)
    log = stdout.read().decode()
    print(log)
    return log


# 提取用户发出的请求
def getUserSend(ssh, arg):
    userSend = []
    ip = ''
    uid = ''
    log = getUserLog(ssh, arg)
    if (log != ''):
        lines = log.split("\n")

        for line in lines:
            if (line.find("[SUCCESS]") > -1):
                ip = re.findall(r"(?<![\.\d])(?:\d{1,3}\.){3}\d{1,3}(?![\.\d])", str(line), re.S)[0]
                # print ip
            elif (line.find("[FAILURE]") > -1):
                pass
            else:
                if (line.find("/v1/sms/send.json") > -1):
                    table = line.split("\t")
                    time = str(table[0])
                    uid = str(table[3])
                    detail = str(table[12])
                    print(re.findall(r'code:(.*?),', detail, re.S))
                    if '5' in re.findall(r'code:(.*?),', detail, re.S):
                        userSend.append((time, uid, re.findall(r'text=\[(.*?)\]', detail, re.S)[0],
                                         re.findall(r'mobile=\[(.*?)\]', detail, re.S)[0]))
                elif (line.find("/single_send.json") > -1):

                    table = line.split("\t")
                    time = str(table[0])
                    uid = str(table[3])
                    detail = str(table[12])
                    print(re.findall(r'code.*?:(.*?),', detail, re.S))
                    if '5' in re.findall(r'code.*?:(.*?),', detail, re.S):
                        userSend.append((time, uid, re.findall(r'text=\[(.*?)\]', detail, re.S)[0],
                                         re.findall(r'mobile=\[(.*?)\]', detail, re.S)[0]))
                elif (line.find("/batch_send.json") > -1):
                    table = line.split("\t")
                    time = str(table[0])
                    uid = str(table[3])
                    detail = str(table[12])
                    print(re.findall(r'code.*?:(.*?),', detail, re.S))
                    if '5' in re.findall(r'code.*?:(.*?),', detail, re.S):
                        userSend.append((time, uid, re.findall(r'text=\[(.*?)\]', detail, re.S)[0],
                                         re.findall(r'mobile=\[(.*?)\]', detail, re.S)[0]))

                elif (line.find("/v2/sms/multi_send.json") > -1):
                    table = line.split("\t")
                    time = str(table[0])
                    uid = str(table[3])
                    detail = str(table[12])
                    print(re.findall(r'code.*?:(.*?),', detail, re.S))
                    if '5' in re.findall(r'code.*?:(.*?),', detail, re.S):
                        userSend.append((time, uid, re.findall(r'text=\[(.*?)\]}', detail, re.S)[0],
                                         re.findall(r'mobile=\[(.*?)\]', detail, re.S)[0]))

    return str(ip), str(uid), userSend


# 获取用户的所有模板
def getTemplates(ssh, ip, uid):
    mubanLog = getUserTplCache(ssh, ip, uid)
    res = []

    jsonStr = "{" + (re.findall(r"{(.*?)}Stderr", str(mubanLog), re.S)[0]) + "}"
    muban = json.loads(jsonStr, encoding='utf-8')
    for d in muban['datas']:
        res.append((d['id'], d['templateTextWithSign']))
    return res


# 转码
# def byteify(input, encoding='utf-8'):
#     if isinstance(input, dict):
#         return {byteify(key): byteify(value) for key, value in input.iteritems()}
#     elif isinstance(input, list):
#         return [byteify(element) for element in input]
#     elif isinstance(input, unicode):
#         return input.encode(encoding)
#     else:
#         return input


# 获取匹配的最优模板
def getBestTemplate(userSend, templates):
    mmax = 0
    best = ''
    bestid = ''
    userSend = str(userSend)

    for id, tpl in templates:
        # tpl = byteify(tpl) # unicode -> str

        match = 0
        s = difflib.SequenceMatcher(lambda x: x == " ", userSend, tpl)
        for block in s.get_matching_blocks():
            (a, b, size) = block
            match += size

        if (match > mmax):
            best = tpl
            bestid = id
            mmax = match
    return bestid, best


def show_diff_html(tpls, text):
    d = difflib.HtmlDiff()  # 创建HtmlDiffer()对象
    html = d.make_file(tpls, text) # 采用make_file方法对字符串进行比较
    pq = PyQuery(html)
    tr = str(pq('tbody tr'))
    print('tr', tr)
    index = tr.find('<td class="diff_next">')
    first_tpl = str(tr)[4:index]
    print('first', first_tpl)
    first_tpl = first_tpl.replace(re.findall(r'(<a href="#difflib_chg_to.*__top">t</a>)', first_tpl, re.S)[0], '<span>模版内容</span>')
    second_msg = str(tr)[index:-5]
    second_msg = second_msg.replace(re.findall(r'(<a href="#difflib_chg_to.*__top">t</a>)', second_msg, re.S)[0], '<span>短信内容</span>')
    return first_tpl, second_msg



def ssh_logger():
    private_key_path = '/Users/gujinxin/.ssh/id_rsa'
    key = paramiko.RSAKey.from_private_key_file(private_key_path)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('121.43.182.116', 22, 'logger', key)
    return ssh


def run(uid_mobile, log_time=None):
    s = ssh_logger()
    r = []
    if log_time:
        args = [uid_mobile, '-d', log_time]
    else:
        args = [uid_mobile]
    ip, uid, userSend = getUserSend(s, args)

    if (ip != '' and uid != ''):
        templates = getTemplates(s, ip, uid)
        for time, uid, txt, mobile in userSend:
            id, tpl = getBestTemplate(txt, templates)
            print(tpl, txt)
            try:
                first_tpl, second_msg = show_diff_html(tpl.splitlines(), txt.splitlines())
            except:
                pass
            else:
                r.append(
                    {
                        'time': time,
                        'uid': uid,
                        'mobile': mobile,
                        'tpl_id': id,
                        'tpl_html': first_tpl,
                        'msg_html': second_msg
                    }
                )
    else:
        print("ip=%s, uid=%s, count=%d" % (ip, uid, len(userSend)))
    s.close()
    return r


if __name__ == '__main__':
    run('15705834033')
