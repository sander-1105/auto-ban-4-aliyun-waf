# -*- coding: utf-8 -*-
import os
import json
import re
import requests
from typing import List
import random
import logging
from datetime import datetime

from alibabacloud_waf_openapi20211001.client import Client as WAFClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_waf_openapi20211001 import models as waf_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient

random.seed(os.urandom(32))

# 配置日志记录器
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TEMPLATE_NUMBERS = [
    1111, 2222, 3333, 4444, 5555
]

RULE_NAMES = ['ip_black_1', 'ip_black_2', 'ip_black_3', 'ip_black_4', 'ip_black_5']
REGION_ID = 'cn-hangzhou'
INSTANCE_ID = 'waf_v2_public_cn-abcdefg'
DEFENSE_SCENE = 'ip_blacklist'
DINGTALK_WEBHOOK_URL='https://oapi.dingtalk.com/robot/send?access_token=1234'
#DINGTALK_WEBHOOK_URL=''

class DingTalkNotifier:
    @staticmethod
    def send_message(message):
        message = 'mail' + message 
        data = {
            "msgtype": "text",
            "text": {"content": message}
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(DINGTALK_WEBHOOK_URL, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        logging.info(f"钉钉消息发送详情: {response.json()}")


class WAFClientFactory:

    _client = None
    @staticmethod
    def client() -> WAFClient:
        if WAFClientFactory._client is not None:
            return WAFClientFactory._client
        
        config = open_api_models.Config(
            access_key_id=os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'],
            access_key_secret=os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'],
            endpoint='wafopenapi.cn-hangzhou.aliyuncs.com'
        )
        WAFClientFactory._client = WAFClient(config)
        return WAFClientFactory._client


class QueryDefenseRuleId:
    def __init__(self, templateId):
        self.client = WAFClientFactory.client()
        self.InstanceId = str(INSTANCE_ID)
        self.templateId = templateId
        
    def query(self):
        describe_defense_rules_request = waf_models.DescribeDefenseRulesRequest(
            region_id='cn-hangzhou',
            instance_id=self.InstanceId,  
            query={
                "templateId": self.templateId,
                "scene": DEFENSE_SCENE,
                "nameLike": 'ip',
                'orderBy':'name',
                'PageNumber':100,
                'PageSize':100
            }
        )

        #{"templateId": 175432, "scene": 'ip_blacklist',"nameLike": 'ip','orderBy':'name'}  
        runtime = util_models.RuntimeOptions()
        try:
            response = self.client.describe_defense_rules_with_options(describe_defense_rules_request, runtime)
       
            rule_name_id = {}
            t_id = {}
            items=[]

            if response.body.rules:       
                for item in response.body.rules:
                    if item.rule_name in RULE_NAMES:
                        items.append(item)
            if items: 
                _item=random.choice(items)
                rule_name_id[_item.rule_name] = _item.rule_id
                t_id['template_id'] = _item.template_id
                
                logging.info(f"查询防护规则成功, rule_name and rule id: {rule_name_id}, template id: {t_id}")
            
                return rule_name_id, t_id
            else:
                logging.error(f"查询防护规则失败，数据样本: {response.body.rules[0]}")
                return False

        except Exception as error:
            error_message = getattr(error, 'message', str(error))
            error_data = getattr(error, 'data', {})
            logging.error(f"查询防护规则失败: {error_message}, {error_data.get('Recommend')}")
            DingTalkNotifier.send_message(f"查询防护规则失败: {error_message}, {error_data.get('Recommend')}") 
            return False


class ModifyDefenseRule:
    def __init__(self):
        self.client = WAFClientFactory.client()
        
    def modify_defense_rules(self, rule_name: str, rule_id: int, remoteaddr: List[str], TemplateId: int):
        self.remoteaddr = remoteaddr
        self.TemplateId = TemplateId
        self.rule_id = rule_id
        self.rule_name = rule_name

        rules = [{
            "id": self.rule_id,
            "name": self.rule_name,
            "remoteAddr": self.remoteaddr,
            "action": "block",
            "status": 1
        }]
        #print(rules)
        _modify_defense_rule_request = waf_models.ModifyDefenseRuleRequest(
            region_id='cn-hangzhou',
            instance_id=INSTANCE_ID,
            template_id=TemplateId,
            defense_scene='ip_blacklist',
            rules=str(rules)
        )
        _runtime = util_models.RuntimeOptions()

        try:
            response = self.client.modify_defense_rule_with_options(_modify_defense_rule_request, _runtime)
            logging.info(f"修改防护规则成功: {response.body}")
            return response
            
        except Exception as error:
            error_message = getattr(error, 'message', str(error))
            error_data = getattr(error, 'data', {})
            logging.error(f"修改防护规则失败: {error_message}, {error_data.get('Recommend')}")
            DingTalkNotifier.send_message(f"修改防护规则失败: {error_message}, {error_data.get('Recommend')}")
            return False

    def create_update_rules(self, remoteaddr):
        self.template_id = random.choice(TEMPLATE_NUMBERS)
        print(f'random choice tmpelate id: {self.template_id}')
        query_instance = QueryDefenseRuleId(self.template_id)
        self.remoteaddr = remoteaddr
        
        rule_name_id_list, new_template_id_dict = query_instance.query()
        self.template_id = new_template_id_dict['template_id']

        if rule_name_id_list: 
            for k,v in  rule_name_id_list.items():
                rule_name = k
                rule_id = v
        else:
            logging.warning("在更新时，未获取到有效的规则ID")
            DingTalkNotifier.send_message("在更新时，未获取到有效的规则ID")
            return False

        try:
            data = self.modify_defense_rules(rule_name, rule_id, self.remoteaddr, self.template_id)

            if data.status_code and data.status_code == 200:
                logging.info(f"更新防护规则成功, rule id: {rule_id}, template id: {self.template_id}")
                return data.status_code
            else:
                logging.error("更新防护规则失败, rule id: {rule_id}, template id: {new_template_id}")
                DingTalkNotifier.send_message(f"更新防护规则失败, rule id: {rule_id}, template id: {self.template_id}")
                return False
            
        except Exception as error:
            error_message = getattr(error, 'message', str(error))
            error_data = getattr(error, 'data', {})
            logging.error(f"更新防护规则失败: {error_message}, {error_data.get('Recommend')},rule id: {rule_id}, template id: {self.template_id}")
            DingTalkNotifier.send_message(f"更新防护规则失败: {error_message}, {error_data.get('Recommend')},rule id: {rule_id}, template id: {self.template_id}")
            return False


class DefenseRuleCreator:
    def __init__(self, client, remoteaddr: List[str]):
        self.client = client
        self.remoteaddr = remoteaddr

    def create_defense_rules(self) -> None:
        template_id_index = 0
        rule_name_index = 0
        rules = []

        for i in range(0, len(self.remoteaddr), 200):
            chunk = self.remoteaddr[i:i + 200]
            if len(rules) >= 5:
                template_id_index += 1
                rule_name_index = 0
                rules = []

            rule_name = RULE_NAMES[rule_name_index]
            rule_name_index += 1

            rules.append({
                "name": rule_name,
                "remoteAddr": chunk,
                "action": "block",
                "status": 1
            })

            result = self._execute_rule_creation(template_id_index, rules, chunk)
            if result is not False:
                logging.info(f'创建防护规则成功, rule_name: {rule_name}, template_id: {result}')
            else:
                logging.error(f"创建防护规则失败")
                

    def _execute_rule_creation(self, template_id_index: int, rules: List[dict],  remoteaddr) -> bool:
        create_defense_rule_request = waf_models.CreateDefenseRuleRequest(
            region_id=REGION_ID,
            instance_id=INSTANCE_ID,
            template_id=TEMPLATE_NUMBERS[template_id_index % len(TEMPLATE_NUMBERS)],
            defense_scene=DEFENSE_SCENE,
            rules=json.dumps(rules)
        )
        _runtime = util_models.RuntimeOptions()
        try:
            self.client.create_defense_rule_with_options(create_defense_rule_request, _runtime)
            return create_defense_rule_request.template_id
        except Exception as error:
            #update
            update_rules = ModifyDefenseRule()
            status_code = update_rules.create_update_rules(remoteaddr)

            if status_code == 200:
                logging.info('更新防护规则成功')
                return create_defense_rule_request.template_id
            else:
                error_message = getattr(error, 'message', str(error))
                error_data = getattr(error, 'data', {})
                logging.error(f"创建防护规则失败: {error_message}, {error_data.get('Recommend')}")
                return False

        
if __name__ == '__main__':
    remoteaddr = ["1.1.1.3", '1.1.1.4', '1.1.1.5', '1.1.1.6']
    client = WAFClientFactory.client()
    creator = DefenseRuleCreator(client, remoteaddr)
    creator.create_defense_rules()