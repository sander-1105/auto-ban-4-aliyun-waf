# -*- coding: utf-8 -*-
### 循环template id和rule name，批量创建规则模板
import os
import json
 
from typing import List
 
from datetime import datetime

from alibabacloud_waf_openapi20211001.client import Client as WAFClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_waf_openapi20211001 import models as waf_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient

 
TEMPLATE_NUMBERS = [
    1111,2222,3333
]

RULE_NAMES = ['ip_black_1', 'ip_black_2', 'ip_black_3', 'ip_black_4', 'ip_black_5']
REGION_ID = 'cn-hangzhou'
INSTANCE_ID = 'waf_v2_public_cn-abcdefg'
DEFENSE_SCENE = 'ip_blacklist'

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


class DefenseRuleCreator:
    def __init__(self, client, remoteaddr: List[str]):
        self.client = client
        self.remoteaddr = remoteaddr

    def create_defense_rules(self) -> None:
        
        for template_id in TEMPLATE_NUMBERS:
            rules = []
            for rule_name in RULE_NAMES:
                rules.append({
                    "name": rule_name,
                    "remoteAddr": self.remoteaddr,
                    "action": "block",
                    "status": 1
                })
                
                #print(template_id,rules)
                result = self._execute_rule_creation(template_id, rules)
                if result is not False:
                    print(f'创建防护规则成功, rule_name: {rule_name}, template_id: {result}')
                else:
                    print(f"创建防护规则失败")
                rules = []
                

    def _execute_rule_creation(self, template_id: int, rules: List[dict]) -> bool:
        create_defense_rule_request = waf_models.CreateDefenseRuleRequest(
            region_id=REGION_ID,
            instance_id=INSTANCE_ID,
            template_id=template_id,
            defense_scene=DEFENSE_SCENE,
            rules=json.dumps(rules)
        )
        _runtime = util_models.RuntimeOptions()
        try:
            self.client.create_defense_rule_with_options(create_defense_rule_request, _runtime)
            return create_defense_rule_request.template_id
        except Exception as error:
            pass

        
if __name__ == '__main__':
    remoteaddr = ["1.1.1.3", '1.1.1.4', '1.1.1.5', '1.1.1.6']
    client = WAFClientFactory.client()
    creator = DefenseRuleCreator(client, remoteaddr)
    creator.create_defense_rules()