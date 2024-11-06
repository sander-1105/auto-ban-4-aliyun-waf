# aliyun-waf-auto-ban-ip



## 使用背景

使用了阿里云WAF识别、拦截恶意攻击行为，但当遇到低频暴力破解时，基础版的WAF就无能为力了，希望能自动的向waf添加黑名单IP，进一步保护业务。

添加黑名单时，需要排除部分IP地址，比如公司办公出口公网地址（需要考虑固定IP和动态地址）。



## 脚本使用限制

1. 已创建阿里云WAF实例，已创建两个阿里云子帐号及设置AK/SK并授予不同的权限(参考第7条)
2. 需要手动的在阿里云WAF-->web基础防护-->IP黑名单 中创建好20个防护模板
3. 阿里云每种防护规则只能创建20个规则模板，每个模板可以设置5个规则，每个规则可以设置200个IP；即：可同时设置20X5X200=20000 个IP黑名单
4. 使用WAF API调试工具获取WAF的实例ID和 20个规则模板的ID，参考：
   1. 获取WAF实例ID（DescribeInstance）：https://api.aliyun.com/api/waf-openapi/2021-10-01/DescribeInstance
   2. 获取20个防护模板ID（DescribeDefenseTemplates）： https://api.aliyun.com/api/waf-openapi/2021-10-01/DescribeDefenseTemplates?RegionId=cn-hangzhou  
   3. 记录得到的WAF实例ID和20个防护模板ID以及防护模板名称
5. 需要使用WAF 3.0 API 
6. 需要将规则模板与防护对象相关联（非脚本执行所需必要项，建议调试完成后再设置）

### 脚本使用说明

1. 环境：python3.8，依赖参考 requirements.txt

2. scan_ip.py 主要用于扫描含有攻击行为的记录，使用正则匹配对应的IP、时间并过滤白名单IP （白名单：固定IP或动态IP（使用动态域名）） 

3. get_ip_resolv.py  DDNS脚本，获取执行环境的外网出口IP并解析到指定的域名，供scan_ip.py使用；实现获取动态IP的功能。注：也可以使用网络设备自带的DDNS功能自动同步线路动态地址至DNS中，设备不支持时可使用get_ip_resolv.py  DDNS脚本。

4. waf_api.py 将scan_ip.py 传递的IP按阿里云WAF API的要求插入或更新到WAF IP黑名单防护规则中。

5. 执行时，请在环境中声明（使用export）ALIBABA_CLOUD_ACCESS_KEY_ID 、ALIBABA_CLOUD_ACCESS_KEY_SECRET 

6. 请酌情修改配置如下

   ```python
   #scan_ip.py
   ...
   def filter_and_process_log(file_path):
       ip_counter = Counter()
   
       with open(file_path, 'r') as file:
           for line in file:
               if 'invalid password' in line.lower():  #请视实际情况给出过滤条件
                   info = extract_info(line)
                   if info['ip']:
                       ip_counter[info['ip']] += 1
   
       result = []
       
     ...
   
   log_file_path = 'mail_audit.log' #logfile  
   ....
   
   #waf_api.py
   ...
   TEMPLATE_NUMBERS=[]
   RULE_NAMES = ['ip_black_1', 'ip_black_2', 'ip_black_3', 'ip_black_4', 'ip_black_5']  #此处不建议修改
   INSTANCE_ID='waf_v2_public_cn-abcdefg'
   DINGTALK_WEBHOOK_URL='https://oapi.dingtalk.com/robot/send?access_token=1234'
   ...
    def query(self):
           describe_defense_rules_request = waf_models.DescribeDefenseRulesRequest(
               region_id='cn-hangzhou',
               instance_id=self.InstanceId,  
               query={
                   "templateId": self.templateId,
                   "scene": 'ip_blacklist',
                   "nameLike": 'ip',  #模糊查询；如果修改了RULE_NAMES的值，请一起修改
                   'orderBy':'name',
                   'PageNumber':100,   #请按需要修改大小，在IP黑名单场景中，100条足矣
                   'PageSize':100  #请按需要修改大小，在IP黑名单场景中，100条足矣
               }
           )
    ...
   
   ```

   6. 建议使用conda创建python3.8虚拟环境运行，举例：

      ```bash
      #start.sh
      #!/bin/bash
      
      cd /data/service/aliyun-waf-auto-ban-ip
      
      conda init >/dev/null
      
      export ALIBABA_CLOUD_ACCESS_KEY_SECRET="SK"
      export ALIBABA_CLOUD_ACCESS_KEY_ID="AK"
      
      source /root/miniconda3/bin/activate python-3.8
      
      /root/miniconda3/envs/python-3.8/bin/python3 /data/service/aliyun-waf-auto-ban-ip/scan_ip.py
      ```

      
   7. 阿里云帐号（AK）授权举例：

      ```json
      # dns解析用
      {
          "Version": "1",
          "Statement": [
              {
                  "Action": [
                      "alidns:UpdateDomainRecord",
                      "alidns:DescribeDomainRecords",
                      "alidns:DescribeDomainRecordInfo",
                      "alidns:DescribeSubDomainRecords",
                      "alidns:DescribeSupportLines",
                      "alidns:UpdateDomainRecordRemark",
                      "alidns:UpdateDNSSLBWeight",
                      "alidns:DescribeDNSSLBSubDomains"
                  ],
                  "Resource": "acs:alidns:*:1234567:domain/a.com",
                  "Effect": "Allow"
              }
          ]
      }
      
      # WAF API操作用
      {
          "Version": "1",
          "Statement": [
              {
                  "Effect": "Allow",
                  "Action": [
                      "yundun-waf:CreateDefenseRule",
                      "yundun-waf:DescribeRuleGroupAssociatedTemplates",
                      "yundun-waf:DescribeRuleHitsTopClientIp",
                      "yundun-waf:DescribeRuleHitsTopResource",
                      "yundun-waf:DescribeRuleHitsTopRuleId",
                      "yundun-waf:DescribeRuleHitsTopTuleType",
                      "yundun-waf:DescribeRuleHitsTopUa",
                      "yundun-waf:DescribeRuleHitsTopUrl",
                      "yundun-waf:ModifyDefenseTemplate",
                      "yundun-waf:ModifyDefenseTemplateStatus",
                      "yundun-waf:ModifyDefenseRule",
                      "yundun-waf:ModifyDefenseRuleStatus",
                      "yundun-waf:DescribeDefenseRule",
                      "yundun-waf:DescribeSceneDefenseRules",
                      "yundun-waf:DescribeDefenseRules"
                  ],
                  "Resource": "*"
              },
              {
                  "Effect": "Allow",
                  "Action": [
                      "yundun-waf:DescribeRule",
                      "yundun-waf:DescribeRuleGroups"
                  ],
                  "Resource": "*"
              }
          ]
      }
      
      ```
