#!/usr/bin/python
# encoding: utf-8

"""
    @Author : noise131
    @Desc   : 微信告警脚本
    @Date   : 2022-07-31 09:56:24
    @Ver    : v1.0
    @PyVer  : 3.10.x
"""

import WechatRobot
import getopt
import sys
import re

def usage_help():
    help = \
    '''
    Usage : 
        MainExecName.py [OPTIONS]

    Opts:
        -a  --atall                   : @全体成员 (仅在消息类型为 text 时生效).
                                        默认值 : False

        -m  --message  <Message>      : 发送的消息内容.
                                        必选参数.

        -n  --atname   <Name>         : @指定群员的微信名. 可以指定多次选项或逗号分隔多个微信名 (仅在消息类型为 text 时生效).
                                        默认值   : None
                                        参数语法 : <name> | <name1,name2,nameN>

        -o  --atmobile <Mobile>       : @指定群成员的手机号. 可以只当多次选项或逗号分隔多个手机号 (仅在消息类型为 text 时生效).
                                        默认值   : None
                                        参数语法 : <mobile> | <mobile1,mobile2,mobileN>

        -t  --msgtype  <MessageType>  : 指定发送的消息类型. 
                                        默认值 : text
                                        可选值 : text | markdown

        -w  --webhook  <WebhookUrl>   : 指定发信机器人的 webhook 地址.
                                        必选参数.
    '''
    print(help)


if __name__ == '__main__':
    # 命令行配置记录字典
    opt_cfg: dict = {
        'at_all': False,
        'at_name_list': [],
        'at_mobile_list': [],
        'message': '',
        'webhook': '',
        'message_type': 'text'
    }
    # 解析命令行参数
    try:
        opts, other_args = getopt.getopt(sys.argv[1:], 'ham:n:o:w:t:', ['help', 'message=', 
                                        'atall', 'atname=', 'atmobile=', 'webhook=', 'msgtype='])
    except getopt.GetoptError as e:
        print('error :', e)
        usage_help()
        sys.exit(1)
    for opt,arg in opts:
        # print(opt, arg)
        # print(type(opt), type(arg))
        # 去除头尾空格, zabbix 传选项参数时会导致参数头部出现一个多余空格，可能会被错误识别
        arg = re.sub(r'^\s*|\s*$', '', arg)
        if opt in ('-h', '--help'):
            usage_help()
            sys.exit(0)
        if opt in ('-a', '--atall'):
            opt_cfg['at_all'] = True
        if opt in ('-m', '--message'):
            opt_cfg['message'] = ''.join([arg])
        if opt in ('-n', '--atname'):
            opt_cfg['at_name_list'].extend(arg.split(','))
            # opt_cfg['at_name_list'].append(arg)
        if opt in ('-o', '--atmobile'):
            opt_cfg['at_mobile_list'].extend(arg.split(','))
            # opt_cfg['at_mobile_list'].append(arg)
        if opt in ('-w', '--webhook'):
            opt_cfg['webhook'] = arg
        if opt in ('-t', '--msgtype'):
            opt_cfg['message_type'] = arg
    if not opt_cfg.get('message'):
        print('-m | --message 参数需要一个非空值')
        sys.exit(1)
    if not opt_cfg.get('webhook'):
        print('error : -w | --webhook 参数需要一个非空值')
        sys.exit(1)
    # print(opt_cfg)
    # 初始化机器人
    robot1 = WechatRobot.WechatRobot(opt_cfg.get('webhook'))
    # 发信
    result = robot1.message_send(
        opt_cfg.get('message'),
        opt_cfg.get('message_type'),
        opt_cfg.get('at_name_list'),
        opt_cfg.get('at_mobile_list'),
        opt_cfg.get('at_all')
    )
    # 检查发信是否成功
    if not result.get('status'):
        print(result.get('msg'))
        # 不成功退出码为 1 并打印具体错误信息
        sys.exit(1)
    print(result.get('msg'))
    # 如果成功退出码为 0 并打印发信信息
    sys.exit(0)
