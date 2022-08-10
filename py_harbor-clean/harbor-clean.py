#!/usr/bin/python3
# encoding: utf-8

"""
    @Author : noise131
    @Desc   : 指定条件删除 harbor 镜像版本, harbor api 版本 v2
    @Date   : 2021-03-13 22:34:08
    @Ver    : v1.0
    @PyVer  : 3.10.x (3.10.5)
    @Github : https://github.com/noise131
"""

import datetime
import requests
import re
import sys
import json
import getopt
import urllib.parse
from prettytable import PrettyTable
from requests.auth import HTTPBasicAuth

harbor_base_api_url: str = None
harbor_auth: HTTPBasicAuth = None
header = {
    'accept': 'application/json'
    # 'authorization': 'Basic YWRtaW46aGFyYm9yLjEyMw=='
}

def usage_help():
    help = \
    '''
    Usage:
        MainExecName.py [OPTIONS]

    Opts:
        -H  --help           : 获取使用帮助

        -h  --host   <host>  : harbor 的 IP 地址或域名

        -p  --port   <port>  : harbor 的端口.
                               默认值 : 80

        -u  --user   <user>  : 指定 harbor 的认证用户

        -P  --password <pwd> : 指定 harbor 认证用户的密码

        -c --scheme <scheme> : 访问 harbor 所使用的协议. 
                               默认值 : http
                               可选值 : http | https

        -m  --mode   <mode>  : 指定删除工件的匹配模式 (以工件的哪种时间作为删除比较依据)
                               默认值 : push
                               可选值 : pull | push | create

        -d  --day    <day>   : 指定与匹配模式多少天之前的工件会被删除
                               默认值 : 30
                               
        -s  --simulation     : 模拟运行, 不会真正删除数据 (配合表格输出使用)

        -t  --table  <table> : 指定表格的输出模式
                               默认值 : del
                               可选值 :
                                   none   : 不输出表格
                                   del    : 输出被删除工件的表格
                                   retain : 输出保留工件的表格
                                   all    : 输出所有表格
        -n  --neverpull      : 删除 pull 时间为 0001-01-01T00:00:00 的工件 (删除从未拉取过的工件, 默认不会删除)

        -e --eproject <project> : 清理工件时排除指定项目，多个项目使用逗号分隔 (逗号与项目名之间不要有空格)

    Example:
        ]# python3 ./harbor-clean.py -h 10.0.0.109 -m pull -d 60 -s -t del -u admin -P "harbor.123"
    '''
    print(help)

def repo_name_handle(repo_respone_data: list) -> dict:
    '''
        处理项目名和仓库名分离, 在获取所有仓库后\n
        返回字典数据结构 : 
            {
                'project': 项目名 (str),
                'repo': [仓库名1, 仓库名2, ...] (list)
            }
    '''
    # repo_list: list[dict] = []
    repo_dict: dict = {}
    for repo in repo_respone_data:
        project_repo_name: str = repo.get('name')
        if project_repo_name:
            name_list: list = project_repo_name.split('/')
            if not repo_dict.get(name_list[0]):
                repo_dict[name_list[0]] = []
            repo_dict[name_list[0]].append(name_list[1])
            # repo_list.append({'project': name_list[0], 'repo': name_list[1]})
    # print(repo_dict)
    return repo_dict
    ...

def del_artifacts(project_name: str, repo_name: str, artifacts_digest: str) -> dict:
    '''
        根据 digest 删除指定工件 (tag | 镜像版本)
    '''
    # 将镜像 ID 转化为 url 编码 (镜像 ID 总包含 : 符号, 需要转换，不转换也可以正常删除，转换是为了兼容以后的版本)
    artifacts_digest_urlcode = urllib.parse.quote(artifacts_digest)
    api_uri = '/projects/{}/repositories/{}/artifacts/{}'.format(project_name, repo_name, artifacts_digest_urlcode)
    try:
        r = requests.delete(url=''.join([harbor_base_api_url, api_uri]), headers=header, auth=harbor_auth)
    except Exception as e:
        return {'status': False, 'code': 1, 'msg': '{}'.format(e), 'kind': 'Delete Artifacts', 'carry': {'digest': artifacts_digest}}
    if not r.status_code == 200:
        msg = r.json().get('errors')[0].get('message')
        return {'status': False, 'code': 2, 'msg': msg, 'kind': 'Delete Artifacts', 'carry': {'digest': artifacts_digest}}
    return {'status': True, 'code': 0, 'msg': 'ok', 'kind': 'Delete Artifacts', 'carry': {'digest': artifacts_digest}}

def artifacts_handle(project_name: str, repo_name: str, del_condition: str, day_before: int,
                    simulation: bool, never_pull: bool, ex_project: list) -> dict:
    '''
        获取一个 repo 下的所有版本 (工件) 的信息并对工件做出相应处理
    '''
    api_uri = '/projects/{}/repositories/{}/artifacts'.format(project_name, repo_name)
    try:
        r = requests.get(url=''.join([harbor_base_api_url, api_uri]), headers=header, auth=harbor_auth)
    except Exception as e:
        return {'status': False, 'code': 1, 'msg': '{}'.format(e), 'kind': 'Artifacts Handle', 'carry': None}
    if not r.status_code == 200:
        msg = r.json().get('errors')[0].get('message')
        return {'status': False, 'code': 2, 'msg': msg, 'kind': 'Artifacts Handle', 'carry': None}
    # artifacts_info_list: list = []
    del_artifacts_info_list: list = []
    retain_artifacts_info_list: list = []
    date_before = datetime.datetime.now() - datetime.timedelta(day_before)
    artifacts: dict = {}
    for artifacts in r.json():
        artifacts_tags = artifacts.get('tags')
        if artifacts_tags:
            artifacts_tags_list: list = []
            for tags in artifacts_tags:
                artifacts_tags_list.append(tags.get('name'))
        else:
            artifacts_tags_list = []
        artifacts_info_dict: dict = {
            'project': project_name,
            'repo': repo_name,
            'digest': artifacts.get('digest'),
            'create_time': re.sub(r'\..*$', '', artifacts.get('extra_attrs').get('created')),
            'pull_time': re.sub(r'\..*$', '', artifacts.get('pull_time')),
            'push_time': re.sub(r'\..*$', '', artifacts.get('push_time')),
            'tag': artifacts_tags_list,
            'type': artifacts.get('type')
        }
        artifacts_time = datetime.datetime.strptime(artifacts_info_dict.get(del_condition), r'%Y-%m-%dT%H:%M:%S')
        if artifacts_time < date_before and artifacts_info_dict.get('project') not in ex_project:
            if artifacts_time == datetime.datetime.strptime('0001-01-01T00:00:00', r'%Y-%m-%dT%H:%M:%S') and not never_pull:
                retain_artifacts_info_list.append(artifacts_info_dict)
                continue
            if not simulation:
                del_result = del_artifacts(artifacts_info_dict.get('project'), artifacts_info_dict.get('repo'), artifacts_info_dict.get('digest'))
                if not del_result.get('status'):
                    print('工件删除失败 : {}'.format(json.dumps(del_result)))
                    sys.exit(1)
            # 添加已删除的工件信息到已删除列表
            del_artifacts_info_list.append(artifacts_info_dict)
            continue
        retain_artifacts_info_list.append(artifacts_info_dict)
    # print(json.dumps(del_artifacts_info_list))
    return {'status': True, 'code': 0, 'msg': 'ok', 'kind': 'Artifacts Handle', 'carry': {'del_list': del_artifacts_info_list, 'retain_list': retain_artifacts_info_list}}
        # 将一个仓库中的所有工件信息汇总到一个数组并返回，作为接口时使用
        # artifacts_info_list.append(artifacts_info_dict)
    # print(del_artifacts_info_list)
    # 返回存储仓库中所有工件信息的列表，作为接口时使用
    # return artifacts_info_list
    # print(artifacts_info_list)

def table_stdout(table_data: list) -> None:
    table = PrettyTable(['Project', 'Repo', 'Tag', 'Digest', 'Kind', 'Create Time', 'Push Time', 'Pull Time'])
    row: dict = {}
    for row in table_data:
        table.add_row([
            row.get('project'),
            row.get('repo'),
            ', '.join(row.get('tag')),
            row.get('digest')[0:17],
            row.get('type'),
            row.get('create_time'),
            row.get('push_time'),
            row.get('pull_time')
        ])
    print(table)

if __name__ == '__main__':
    # 配置字典
    config_map = {
        'host': '',
        'port': '80',
        'user': '',
        'password': '',
        'scheme': 'http',
        'mode': 'push',
        'day': 30,
        'simulation': False,
        'table': 'del',
        'never': False,
        'ex_project': [],
    }
    # 解析命令行参数
    try:
        opts, other_args = getopt.getopt(sys.argv[1:], 'Hsh:p:u:P:c:m:d:t:ne:', ['help', 'simulation', 'host=',
                                        'port=', 'user=', 'password=', 'scheme=', 'mode=', 'day=', 'table=', 'neverpull', 'eproject='])
    except getopt.GetoptError as e:
        print('参数获取失败 : {}'.format(e))
        sys.exit(1)
    # print(other_args)
    for opt,arg in opts:
        # print(opt, arg)
        # print(type(opt), type(arg))
        # 去除参数的头尾空格
        arg = re.sub(r'^\s*|\s*$', '', arg)
        match opt:
            case '-H' | '--help':
                usage_help()
                sys.exit(1)
            case '-h' | '--host':
                config_map['host'] = arg
            case '-p' | '--port':
                config_map['port'] = arg
            case '-u' | '--user':
                config_map['user'] = arg
            case '-P' | '--password':
                config_map['password'] = arg
            case '-c' | '--scheme':
                config_map['scheme'] = arg
            case '-m' | '--mode':
                config_map['mode'] = arg
            case '-d' | '--day':
                try:
                    config_map['day'] = int(arg)
                except Exception as e:
                    print('\"{}\" 选项获取参数值 \"{}\" 出现异常 : \"{}\"'.format(opt, arg, str(e)))
                    sys.exit(1)
            case '-s' | '--simulation':
                config_map['simulation'] = True
            case '-t' | '--table':
                config_map['table'] = arg
            case '-n' | '--neverpull':
                config_map['never'] = True
            case '-e' | '--eproject':
                config_map['ex_project'] = arg.split(',')
            case _:
                print('选项 {} 未定义'.format(opt))
                sys.exit(1)
    # print(json.dumps(config_map))
    harbor_base_api_url = '{}://{}:{}/api/v2.0'.format(
                                                    config_map.get('scheme'),
                                                    config_map.get('host'),
                                                    config_map.get('port')
                                                )
    harbor_auth = HTTPBasicAuth(config_map.get('user'), config_map.get('password'))
    # print(harbor_auth.username, harbor_auth.password)
    match config_map.get('mode'):
        case 'pull':
            condition = 'pull_time'
        case 'push':
            condition = 'push_time'
        case 'create':
            condition = 'create_time'
        case _:
            print('匹配模式 {} 未定义'.format(config_map.get('mode')))
            sys.exit(1)
    # harbor 主操作块
    get_repo_api_uri = '/repositories'
    try:
        r = requests.get(url=''.join([harbor_base_api_url, get_repo_api_uri]), headers=header, auth=harbor_auth)
    except Exception as e:
        print('访问 Harbor 时发生错误 : {}'.format(e))
        sys.exit(1)
    if r.status_code != 200:
        print('Harbor 响应异常 : {}'.format(r.json().get('errors')[0].get('message')))
    repo_result = repo_name_handle(r.json())
    if not repo_result:
        print('获取到的仓库信息为空, 请检查 harbor 地址及认证信息是否正确 !')
        sys.exit(1)
    del_artifacts_info_list: list = []
    retain_artifacts_info_list: list = []
    for project, repo_list in repo_result.items():
        for repo in repo_list:
            r = artifacts_handle(project, repo, condition, config_map.get('day'), config_map.get('simulation'), config_map.get('never'), config_map.get('ex_project'))
            if r.get('carry').get('del_list'):
                del_artifacts_info_list.extend(r.get('carry').get('del_list'))
            if r.get('carry').get('retain_list'):
                retain_artifacts_info_list.extend(r.get('carry').get('retain_list'))
    # print(json.dumps(del_artifacts_info_list))
    # print(json.dumps(retain_artifacts_info_list))
    match config_map.get('table'):
        case 'del':
            print('\n删除的工件 :')
            table_stdout(del_artifacts_info_list)
        case 'retain':
            print('\n保留的工件 :')
            table_stdout(retain_artifacts_info_list)
        case 'all':
            print('\n删除的工件 :')
            table_stdout(del_artifacts_info_list)
            print('\n保留的工件 :')
            table_stdout(retain_artifacts_info_list)
    print('\n工件清理完成 ! (simulation : {})\n'.format(str(config_map.get('simulation'))))
