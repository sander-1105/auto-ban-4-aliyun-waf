#!/usr/bin/env python3
# coding=utf-8
# pip3 install aliyun-python-sdk-core-v3

from ipaddress import ip_address
import requests
import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkalidns.request.v20150109 import UpdateDomainRecordRequest


# 需要先获取 aliyun 账号的 AccessKey 信息
client = AcsClient('AK', 'SK', 'default')
domain_name = 'a.com'
DINGTALK_WEBHOOK_URL='https://oapi.dingtalk.com/robot/send?access_token=1234'


def get_record_id(rr):
    sub_domain_name = rr + "." + domain_name
    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('alidns.aliyuncs.com')
    request.set_method('POST')
    request.set_protocol_type('https')  # https | http
    request.set_version('2015-01-09')
    request.set_action_name('DescribeSubDomainRecords')

    request.add_query_param('SubDomain', sub_domain_name)

    response = client.do_action_with_exception(request)
    # python2:  print(response)
    # print(str(response, encoding='utf-8'))
    aaa = str(response, encoding='utf-8')
    bbb = json.loads(aaa)
    # print(bbb['RecordId'])
    recordid = bbb['DomainRecords']["Record"][0]["RecordId"]
    return recordid


def send_message(message):
    message = 'mail' + message 
    data = {
        "msgtype": "text",
        "text": {"content": message}
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(DINGTALK_WEBHOOK_URL, json=data, headers=headers, timeout=10)
    response.raise_for_status()
    print(f"钉钉消息发送成功: {response.json()}")

    
def get_ip_address():
    import subprocess
    import random
    site_list=[
        'https://checkip.amazonaws.com',
        'https://ifconfig.me/ip',
        'https://icanhazip.com',
        'https://ipinfo.io/ip',
        'https://ipecho.net/plain',
        'https://checkipv4.dedyn.io'
        ]
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # 随机选择一个网站
            site = random.choice(site_list)
            # 执行 curl 命令并捕获输出
            result = subprocess.run(['curl', site], capture_output=True, text=True, check=True)
            # 去除结尾的 % 符号（如果有）
            ip_address = result.stdout.strip('%').strip()
            return ip_address
        except subprocess.CalledProcessError as e:
            # 记录错误信息
            error_message = f"Attempt {attempt + 1} failed: {e}"
            print(error_message)
    
   	 # 如果3次尝试都失败，返回错误信息
    send_message(f"Error: Failed to get IP address after 3 attempts,deploy on 1401 internal k8s, pod name like : get-ip-and-resolve-4-MailServer-security. ")
    return None




def update_domain_record(rr, record_id, update_type, address):

    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('alidns.aliyuncs.com')
    request.set_method('POST')
    request.set_protocol_type('https')  # https | http
    request.set_version('2015-01-09')
    request.set_action_name('UpdateDomainRecord')

    request.add_query_param('RecordId', record_id)
    request.add_query_param('RR', rr)
    request.add_query_param('Type', update_type)
    request.add_query_param('Value', address)

    response = client.do_action_with_exception(request)
    # python2:  print(response)
    print(str(response, encoding='utf-8'))


if __name__ == '__main__':

    RR = 'dns Record'
    UPDATE_TYPE = 'A' #A 记录
    ADDRESS = get_ip_address()
    #print(ADDRESS)
    RECORD_ID = get_record_id(RR)
    #print(RECORD_ID)
    if ADDRESS != None:
        update_domain_record(RR, RECORD_ID, UPDATE_TYPE, ADDRESS)


