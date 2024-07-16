import os
from datetime import datetime
import getopt
import json
import sys
import copy
import requests

import redis as Redis

from src.feed import *


## 飞书api
WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/6b145d96-b3e1-4542-8e07-6ba92c38d932"

## 项目内容示例模板
repo_templete =  {
            "tag": "div",
            "text": {
                "content": "**西湖**，位于浙江省杭州市西湖区龙井路1号，杭州市区西部，景区总面积49平方千米，汇水面积为21.22平方千米，湖面面积为6.38平方千米。",
                "tag": "lark_md",
                "href": {
                         "urlVal": {
                             "url": "https://www.baidu.com",
                         }
                     }

            }
        }

## 分割线模板
line_templete =  {
        "tag": "hr"
      }

## 备注模板
note_templete =  {
        "tag": "note",
        "elements": [
          {
            "tag": "plain_text",
            "content": "Notes"
          }
        ]
      }

## payload模板
payload = {
    "msg_type": "interactive",
    "card": {
        "config": {
            "wide_screen_mode": True,
            "enable_forward": False
        },
        # "elements": element_list,
        "header": {
            "title": {
                "content": "安全相关热门开源项目周报🔥",
                "tag": "plain_text"
            }
        }
    }
}
class FeishuWebHookApi():
    def send_msg(self,payload):
        try:
            res=requests.request("post",
                                 url=WEBHOOK,
                                 data=json.dumps(payload),
                                 headers={'Content-Type': 'application/json'})
        except Exception as e:
            raise RuntimeError(f"FeishuWebHookApi's send_msg fina an error:{e}")

def getFeedReportInformation(config):
    redis=Redis.StrictRedis(host= config["REDIS_ADDR"],
                                       port=config["REDIS_PORT"],
                                       db=config["REDIS_DATABASE"],
                                       decode_responses=True)
    # 获取时间，写在备注中
    year = datetime.now().isocalendar()[0]
    week = datetime.now().isocalendar()[1] - 1
    weekday = datetime.now().isocalendar()[2]
    # 每年第一周需特殊处理
    if week == 0:
        week = 52
        year -= 1
    # 周一推周报，其余推日报
    if weekday == 1:
        redis.incr('PushTime4GitHub')
        times = redis.get('PushTime4GitHub')
        note_templete['elements'][0]['content'] = str(year) + "年第" + str(week) + "周"
        payload['card']['header']['title']['content'] = "[开源周报]-安全热门开源项目第" + str(times) + "期🔥"
        return feedByMysql().get_weekly(50)['data']
    else:
        note_templete['elements'][0]['content'] = datetime.now().strftime('%Y-%m-%d')
        payload['card']['header']['title']['content'] = "[开源日报]-安全热门开源项目🔥"
        return feedByMysql().get_weekly(20)['data']

def setFeedReport(data_list):
    element_list = [line_templete]

    if len(data_list) == 0:  # 无新增项目
        repo_templete['text']['content'] = '无新增项目'
        element_list.append(copy.deepcopy(repo_templete))
    else:
        for i in data_list:
            # 取项目名称
            repo_name = os.path.basename(i['url'])
            # 取项目地址
            repo_url = i['url']
            # 取项目描述
            repo_desc = i['description']
            # 生成项目描述
            repo_templete['text']['content'] = '**[' + repo_name + ']($urlVal)**:' + repo_desc
            # 生成跳转链接
            repo_templete['text']['href']['urlVal']['url'] = repo_url
            element_list.append(copy.deepcopy(repo_templete))
            # 加入分割线
            element_list.append(line_templete)
            # print(element_list)
        # 加入备注
    element_list.append(note_templete)
    # 主体合入信息包
    payload['card']['elements'] = element_list

if __name__ == '__main__':
    opts,args=getopt.getopt(sys.argv[1:],'',["dev","build"])
    for opt_key,opt_value in opts:
        try:
            if opt_key=='--build':
                config = Config(opt_key).get_config()
                break
            elif opt_key=='--dev':
                config = Config(opt_key).get_config()
                break
            else:
                raise Exception
        except Exception as e:
            raise RuntimeError(f"parase is error:{e}")

    data_list=getFeedReportInformation(config=config)
    setFeedReport(data_list=data_list)
    res=FeishuWebHookApi().send_msg(payload=payload)
    print(res)




