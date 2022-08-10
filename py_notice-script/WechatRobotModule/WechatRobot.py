# encoding: utf-8

"""
    @Author : noise131
    @Desc   : 微信机器人封装
    @Date   : 2022-07-31 09:39:56
    @Ver    : v1.0
    @PyVer  : 3.10.x
"""

import requests
import string
import random
import json
import sys
from datetime import datetime

class WechatRobot:
    __robot_name: str = None
    __robot_id: str = None
    __robot_webhook_url: str = None
    # 存储机器人状态结构体
    # item: str
    #     该响应字典对应的项目
    # status: bool
    #     True  可以发送消息
    #     False 不可发送消息
    # code: int
    #     0  正常状态
    #     1  机器人 webhook 不存在
    #     2  网络异常或 url 不符合规范
    # info: str
    #     机器人当前状态的详细信息
    __robot_status: dict = {}

    def __init__(self, webhook_url: str, robot_name: str = None) -> None:
        self.__robot_id = self.__random_str(10)
        self.__robot_webhook_url = webhook_url
        if not robot_name:
            self.__robot_name = self.__robot_id
        self.__robot_status['item'] = 'RobotStatus'
        self.__robot_valid_check()

    def __robot_valid_check(self) -> bool:
        # 微信无效机器人 webhook 返回码
        incalid_code = 93000
        try:
            response = requests.get(self.__robot_webhook_url)
        except Exception as e:
            self.__robot_status['status'] = False
            self.__robot_status['code'] = 2
            self.__robot_status['info'] = 'Robot Status exception; {}'.format(e)
            return False
        if response.json().get('errcode') == incalid_code:
            self.__robot_status['status'] = False
            self.__robot_status['code'] = 1
            self.__robot_status['info'] = 'Robot Status exception; {}'.format(response.json().get('errmsg'))
            return False
        self.__robot_status['status'] = True
        self.__robot_status['code'] = 0
        self.__robot_status['info'] = 'Robot Status ok; 机器人状态正常'
        return True

    def message_send(self, content: str|list, message_type: str = 'text', mentioned_list: list[str] = [], 
                    mentioned_mobile_list: list = [], at_all: bool = False) -> dict:
        '''
            发送消息操作封装
                返回码 (code) 含义 : 
                    0 : 发送正常
                    1 : 预留
                    2 : request 请求阶段出现异常
                    3 : 消息发送阶段出现异常
        '''
        if type(content) is list:
            if message_type == 'text':
                message_content = '\n'.join(content)
            else:
                message_content = '\n\n'.join(content)
        else:
            message_content = content
        if at_all:
            if not self.__list_search(mentioned_list, '@all') and not self.__list_search(mentioned_mobile_list, '@all'):
                mentioned_list.append('@all')
        # 构造消息 json 数据
        if message_type.lower() == 'text':
            message_data: dict = self.__text_message_send(message_content, mentioned_list, mentioned_mobile_list)
        elif message_type.lower() == 'markdown':
            message_data: dict = self.__markdown_message_send(message_content)
        # print(json.dumps(message_data))
        try:
            response = requests.request(method='POST', url=self.__robot_webhook_url, data=json.dumps(message_data))
            # response = requests.request(method='POST', url=self.__robot_webhook_url, json=message_data)
        except Exception as e:
            return {'item':'MessageSend', 'status': False, 'code': 2, 'msg': 'Message Send exception; {}'.format(e), 'time': datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}
        if response.json().get('errcode') != 0:
            return {'item':'MessageSend', 'status': False, 'code': 3, 'msg': 'Message Send exception; {}'.format(response.json().get('errmsg')), 'time': datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}
        # print(response.content.decode())
        return {'item':'MessageSend', 'status': True, 'code': 0, 'msg': 'Message Send ok; MessageContent: {}'.format(message_content), 'time': datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}

    def __text_message_send(self, content: str|list, mentioned_list: list, 
                            mentioned_mobile_list: list) -> dict:
        '''
            text 文本格式消息 json 数据构造
        '''
        message_data = {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": mentioned_list,
                "mentioned_mobile_list": mentioned_mobile_list
            }
        }
        return message_data

    def __markdown_message_send(self, content: str|list) -> dict:
        """
            markdown 格式消息 json 数据构造
        """
        message_data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        return message_data

    def __random_str(self, lenght: int) -> str:
        """
            生成指定位数的随机字符串\n
                字符换内容包括 : A-Z, a-z, 0-9
        """
        return ''.join(random.sample(''.join([string.ascii_letters, string.digits]), lenght))

    def __list_search(self, search_source_list: list, search_content) -> bool:
        """
            在列表内搜做自定元素
                元素存在返回   : True
                元素不存在返回 : False
        """
        for element in search_source_list:
            if element == search_content:
                return True
        return False

    def get_robot_info(self) -> dict:
        return self.__robot_status

    def get_robot_status(self) -> bool:
        self.__robot_valid_check()
        return self.__robot_status.get('status')



if __name__ == '__main__':
    # 定义机器人 webhook 地址
    webhook_url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxxxxx'
    # 初始化机器人
    robot1 = WechatRobot(webhook_url, 'robot1')
    print(robot1.get_robot_info())
    # text 消息发送
    # 发送消息之前判断机器人是否可用
    if not robot1.get_robot_status():
        print('机器人状态异常 :', robot1.get_robot_info())
        sys.exit(1)
    result = robot1.message_send(['line1', 'line2', 'line3'], 'text', at_all=True)
    if not result.get('status'):
        # 消息发送失败的处理动作
        # print(result.get('msg'))
        print(result)
        sys.exit(1)
    # 消息发送成功的处理动作
    print(result)

    # markdown 消息发送测试
    result = robot1.message_send(
        [
            '# 一级标题',
            '## 二级标题', 
            '### 三级标题', 
            '- 无序列表1', 
            '- 无序列表2', 
            '- 无序列表3', 
            '> 引用1', 
            '> 引用2',
            '> 引用3'
        ], 
        'markdown'
    )
    print(result)
