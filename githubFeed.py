import feedparser
import re
from bs4 import BeautifulSoup
import time
import pymysql
import http.client
"""
一个自动解析github订阅消息的脚本，每十分钟解析一次，并把新的内容存入mysql数据库，数据库目前有三个表-事件表、用户表和项目表

2021.6.21 sql语句用的是最原始的字符串拼接，容易被sql注入，不过是内部代码就没有管了
2021.6.25 已解决：解析到新事件"make public"，未将其入库，因为判断事件类型时没判断该类事件-使用missing_events表存储
2021.6.25 备注：存入数据库的事件发生时间是UTC时间，比如"2021-06-25 15:33:41"是指的"2021-06-25T15:33:41Z"
2021.6.25 已解决：解析时有时会遇到报错，feedparser.parse估计使用的是urllib，有时会出问题-目前解决方法就是遇到error就重新解析即可
2021.6.29 更新：把未知类型的事件存入一张新的表missing_events
2021.7.4  更新：修改了sql语句的写法
"""

# 在feedparser.parse遇到报错http.client.IncompleteRead，下方代码为可能的解决方法
http.client.HTTPConnection._http_vsn = 10
http.client.HTTPConnection._http_vsn_str = 'HTTP/1.0'

import os

# 设置代理地址和端口
proxy_address = "http://192.168.32.125"
proxy_port = "7890"

# 设置HTTP代理
os.environ["HTTP_PROXY"] = f"{proxy_address}:{proxy_port}"

# 设置HTTPS代理
os.environ["HTTPS_PROXY"] = f"{proxy_address}:{proxy_port}"

# 正则表达式
pattern = re.compile(r'[\n ]*(.*?)\n')


# 获取当前时间并返回
def get_time():
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    return current_time

db = pymysql.connect(host="127.0.0.1", user="root", password="root", database="rss")
cursor = db.cursor()

# 此处有时报error-IncompleteRead(122967 bytes read, 1854 more expected)，<urlopen error [Errno 2] No such file or directory>，<urlopen error [WinError 10054] 远程主机强迫关闭了一个现有的连接。>
while True:
    try:
        d = feedparser.parse('https://github.com/ourren.private.atom?token=ACOQ5NCUEGTPHZCZ567LFFN6Z32QA')
    except Exception as e:
        print("\nerror:", e)
        print("[{}]发生错误，10秒钟后将重新进行解析".format(get_time()))
        time.sleep(10)
        continue
    break
#print(d)
lEntries = [e.summary for e in d.entries]
lNews = []

# 当前30个事件的发布时间，取得的时间格式为UTC时间，将其转化为"yyyy-MM-dd HH:mm:ss"并保存
published_time = [f.published for f in d.entries]  # UTC时间
pub_time = []  # 转换格式后的时间
for p_time in published_time:
    p_time = p_time.replace("T", " ").replace("Z", "")
    pub_time.append(p_time)

print("\n\n[{}]本轮开始\n".format(get_time()))

# 判断是否有新事件
sql_if_new = 'SELECT * FROM events WHERE date = %s'

index = -1
for p_time in pub_time:
    sql_if_new_params = (p_time,)
    try:
        db.ping(reconnect=True)
        cursor.execute(sql_if_new, sql_if_new_params)
        db.commit()
        results = cursor.fetchall()
        # 如果数据库中不存在该event，则记录index
        if len(results) == 0:
            index = pub_time.index(p_time)
        else:
            break
    except Exception as e:
        print("查询最新事件error：{}".format(e))
        db.rollback()

# 如果没有新事件则等待十分钟，否则对新事件进行解析
if index == -1:
    print("[{}]当前没有新事件".format(get_time()))
    print("\n[{}]本轮结束，等待十分钟\n\n".format(get_time()))
    # time.sleep(600)
    exit(0)
else:
    print("[{}]取得{}个新事件".format(get_time(), index + 1))
    i = 0
    for text in lEntries:
        if i > index:
            break
        lNew = []
        soup = BeautifulSoup(text, features="html.parser")
        aList = soup.find_all(class_='Link--primary')
        divtxt = soup.find('div', 'd-flex').text
        divtxt = pattern.findall(divtxt)
        if len(aList) == 4:
            lNew.extend([e.attrs['href'] for e in soup.find_all(class_='Link--primary')[:3]])
            lNew.extend([divtxt[0], divtxt[2], divtxt[4], divtxt[1] + ' ' + divtxt[3], divtxt[5]])
        else:
            lNew.extend([e.attrs['href'] for e in soup.find_all(class_='Link--primary')[:2]])
            if len(divtxt) == 6:
                lNew.extend([divtxt[0], divtxt[3], divtxt[1] + ' ' + divtxt[2], divtxt[4]])
            else:
                lNew.extend([divtxt[0], divtxt[2], divtxt[1], divtxt[3]])
        try:
            lNew.append(soup.find_all('p')[0].text.strip())  # <p>标签中为项目描述
        except:
            lNew.append("No description")
        lNew.append(pub_time[i])

        lNews.append(lNew)
        i = i + 1

# lNews总共有以下五种类型：0-starred，1-create a repository,2-started following,3-forked from,4-released
# create a repository:[用户github地址，项目地址，用户名，项目名，操作-created a repository，时间，描述-项目描述，事件发布时间]
# started following：[用户github地址，被follow用户的github地址，用户名，被follow用户名，操作-started following，时间，描述-被follow用户的仓库数和follower数，事件发布时间]
# starred：[用户github地址，star的项目地址，用户名，项目名，操作-starred'，日期，描述-项目描述，事件发布时间]
# forked from：[用户github地址，fork的目的地址，fork的源地址，用户名，fork的目的项目，fork的原项目，操作-forked from，时间，描述-项目描述，事件发布时间]
# released:[用户github地址，release的项目地址，用户名，版本号，操作-released，of，描述，事件发布时间]

# 把LNews进行分类（目前只分为五类：1.创建仓库 2.follow别人 3.star项目 4.fork 5.released-发布新版本）
create_a_repository_news = []
started_following_news = []
starred_news = []
forked_from_news = []
released_news = []

# temp用于记录所有成功分类的事件
temp = []
for one_news in lNews:
    # 逐个检查一条news中的字段，将其进行分类
    for content in one_news:
        if content == 'created a' or content == 'create a repository':
            create_a_repository_news.append(one_news)
            temp.append(one_news)
            break
        elif content == 'started following':
            started_following_news.append(one_news)
            temp.append(one_news)
            break
        elif content == 'starred':
            starred_news.append(one_news)
            temp.append(one_news)
            break
        elif content == 'forked from':
            forked_from_news.append(one_news)
            temp.append(one_news)
            break
        elif content == 'released':
            released_news.append(one_news)
            temp.append(one_news)
            break
        else:
            continue

# 检查是否有未分类的事件并将未分类的事件存入missing_events表中
sql_missing = 'insert into missing_events values(NULL,%s)'

for one_news in lNews:
    if one_news not in temp:
        other_events = " ".join(one_news)
        sql_missing_params = (other_events,)
        try:
            # 检查连接是否断开，如果断开就进行重连
            db.ping(reconnect=True)
            # 使用 execute() 执行sql
            cursor.execute(sql_missing, sql_missing_params)
            db.commit()
            print("[{}]有一个未知类型的事件的事件，已存入missing_events表中：".format(get_time()),
                  sql_missing % sql_missing_params)
        except Exception as e:
            print("存入missing_events表error：{}".format(e))
            # 回滚所有更改
            db.rollback()

# 将news存入数据库中的events表,event_type：0-starred，1-create a repository,2-started following,3-forked from,4-released
# events表：[event_id(自增)，event_type，date，usr_github，target_github，repository_description]
sql_insert_events = 'insert into events values(NULL,%s,%s,%s,%s,%s)'

for news in create_a_repository_news:
    if news[6] == '':
        news[6] = 'No description'
    sql_insert_events_params = ('1', news[7], news[0], news[1], news[6].replace("'", ' '))
    try:
        # 检查连接是否断开，如果断开就进行重连
        db.ping(reconnect=True)
        # 使用 execute() 执行sql
        cursor.execute(sql_insert_events, sql_insert_events_params)
        db.commit()
        print("[{}]新事件入库：".format(get_time()), sql_insert_events % sql_insert_events_params)
    except Exception as e:
        print("存入events表error：{}".format(e))
        # 回滚所有更改
        db.rollback()

for news in started_following_news:
    if news[6] == '':
        news[6] = 'No description'
    sql_insert_events_params = ('2', news[7], news[0], news[1], news[6].replace('\n', ' '))
    # sql = "insert into events values(NULL,2,'" + news[7] + "','" + news[0] + "','" + news[
    #     1] + "','" + news[6].replace('\n', ' ') + "')"
    try:
        db.ping(reconnect=True)
        cursor.execute(sql_insert_events, sql_insert_events_params)
        db.commit()
        print("[{}]新事件入库：".format(get_time()), sql_insert_events % sql_insert_events_params)
    except Exception as e:
        print("存入events表error：{}".format(e))
        db.rollback()

for news in starred_news:
    if news[6] == '':
        news[6] = 'No description'
    sql_insert_events_params = ('0', news[7], news[0], news[1], news[6].replace("'", ' '))
    try:
        db.ping(reconnect=True)
        cursor.execute(sql_insert_events, sql_insert_events_params)
        db.commit()
        print("[{}]新事件入库：".format(get_time()), sql_insert_events % sql_insert_events_params)
    except Exception as e:
        print("存入events表error：{}".format(e))
        db.rollback()

for news in forked_from_news:
    if news[8] == '':
        news[8] = 'No description'
    sql_insert_events_params = ('3', news[9], news[0], news[2], news[8].replace("'", ' '))
    try:
        db.ping(reconnect=True)
        cursor.execute(sql_insert_events, sql_insert_events_params)
        db.commit()
        print("[{}]新事件入库：".format(get_time()), sql_insert_events % sql_insert_events_params)
    except Exception as e:
        print("存入events表error：{}".format(e))
        db.rollback()

for news in released_news:
    if news[6] == '':
        news[6] = 'No description'
    sql_insert_events_params = ('4', news[7], news[0], news[1], news[6].replace("'", ' '))
    try:
        db.ping(reconnect=True)
        cursor.execute(sql_insert_events, sql_insert_events_params)
        db.commit()
        print("[{}]新事件入库：".format(get_time()), sql_insert_events % sql_insert_events_params)
    except Exception as e:
        print("存入events表error：{}".format(e))
        db.rollback()

# 存储至users表和repositories表
# 所有涉及到的用户信息：users[[用户名，用户github地址],...]
# 所有涉及到的项目信息：repositories[[项目github地址，项目描述],....]
users = []
repositories = []
for one_news in create_a_repository_news:
    users.append([one_news[2], one_news[0]])
    repositories.append([one_news[1], one_news[6]])

for one_news in started_following_news:
    users.append([one_news[2], one_news[0]])
    users.append([one_news[3], one_news[1]])

for one_news in starred_news:
    users.append([one_news[2], one_news[0]])
    repositories.append([one_news[1], one_news[6]])

for one_news in forked_from_news:
    users.append([one_news[3], one_news[0]])
    repositories.append([one_news[2], one_news[8]])

for one_news in released_news:
    users.append([one_news[2], one_news[0]])
    repositories.append([one_news[1], one_news[6]])

# 对用户信息去重并存入
sql_if_exists_user = 'SELECT * FROM users WHERE user_name = %s'
sql_insert_users = 'insert into users values(%s,%s)'

for _ in users:
    sql_if_exists_user_params = (_[0],)
    try:
        db.ping(reconnect=True)
        cursor.execute(sql_if_exists_user, sql_if_exists_user_params)
        db.commit()
        results = cursor.fetchall()
        # 如果数据库中不存在这个用户，则存入数据库
        if len(results) == 0:
            sql_insert_users_params = (_[0], _[1])
            cursor.execute(sql_insert_users, sql_insert_users_params)
            db.commit()
            print("[{}]新用户入库：".format(get_time()), sql_insert_users % sql_insert_users_params)
    except Exception as e:
        print("存入users表error：{}".format(e))
        db.rollback()

# 对项目信息去重并存入
sql_if_exists_repo = 'SELECT * FROM repositories WHERE repository_github = %s'
sql_insert_repo = 'insert into repositories(repository_github,repository_description) values(%s,%s)'
for _ in repositories:
    sql_if_exists_repo_params = (_[0],)
    sql_insert_repo_params = (_[0], _[1].replace("'", " "))
    try:
        db.ping(reconnect=True)
        cursor.execute(sql_if_exists_repo, sql_if_exists_repo_params)
        db.commit()
        results = cursor.fetchall()
        # 如果数据库中不存在这个项目，则存入数据库
        if len(results) == 0:
            cursor.execute(sql_insert_repo,sql_insert_repo_params)
            db.commit()
            print("[{}]新项目入库：".format(get_time()), sql_insert_repo % sql_insert_repo_params)
    except Exception as e:
        print("存入repositories表error：{}".format(e))
        db.rollback()

print("\n[{}]本轮结束，等待十分钟\n\n".format(get_time()))
