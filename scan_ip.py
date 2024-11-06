# -*- coding: utf-8 -*-
import re
from collections import Counter
import logging
import httplib2
from urllib.parse import urlencode
from waf_api import * 
import dns.resolver

 
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

 
DINGTALK_WEBHOOK_URL='https://oapi.dingtalk.com/robot/send?access_token=1234'

 
ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z]{2,}\b'
datetime_pattern = r'\b\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\b'
while_ip_list = ['1.1.1.1','1.1.1.2','1.1.1.3']
while_domain_list = ['a.a.com','a1.a.com','a2.a.com']

DingDingAlter = DingTalkNotifier()

def get_ip_address():
    for domain in while_domain_list:
        try:
   
            answers = dns.resolver.resolve(domain, 'A')
            for rdata in answers:
                ip_address = rdata.address
                while_ip_list.append(ip_address)
                logging.info(f"resolv {domain} success, ip addr: {ip_address}")
                print(f"{domain}  {ip_address}")
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout) as e:
            logging.error(f"resolv {domain} fail: {e}")
            DingDingAlter.send_dingding_alert(f"Error: {e}")
            return f"Error: {e}"

def extract_info(line):
    ip = re.search(ip_pattern, line)
    email = re.search(email_pattern, line)
    datetime = re.search(datetime_pattern, line)
    return {
        'ip': ip.group(0) if ip else None,
        'email': email.group(0) if email else None,
        'datetime': datetime.group(0) if datetime else None
    }

def filter_and_process_log(file_path):
    ip_counter = Counter()

    with open(file_path, 'r') as file:
        for line in file:
            if 'invalid password' in line.lower():
                info = extract_info(line)
                if info['ip']:
                    ip_counter[info['ip']] += 1

    result = []

    if ip_counter:
        get_ip_address()

   
    for ip, count in ip_counter.items():
        if ip not in while_ip_list and count > 4:
            result.append(f"{ip}")
            logging.info(f"attack ip: {ip}, count: {count}")

    return result

if __name__ == "__main__":
    log_file_path = 'audit.log' #logfile
    remoteaddr = filter_and_process_log(log_file_path)
    client = WAFClientFactory.client()
    creator = DefenseRuleCreator(client, remoteaddr)
    creator.create_defense_rules()
    #logging.info(f"attack ip: {remoteaddr}")