import pymysql

from src.config import *

# 日报查询时间范围：1天前同一时刻
SQL_DAILY = 'SELECT target_github, repository_description, COUNT(event_type) AS nums \
            FROM events \
            WHERE event_type = 0 \
            AND target_github IN (SELECT repository_github FROM repositories WHERE daily_pushed = 0) \
            AND date BETWEEN \
            DATE_SUB(NOW(), INTERVAL 1 DAY) AND \
            NOW() \
            GROUP BY target_github, repository_description \
            ORDER BY nums DESC \
            LIMIT '
# 周报查询时间范围：7天前同一时刻
SQL_WEEKLY = 'SELECT target_github, repository_description, COUNT(event_type) AS nums \
            FROM events \
            WHERE event_type = 0 \
            AND target_github IN (SELECT repository_github FROM repositories WHERE weekly_pushed = 0) \
            AND date BETWEEN \
            DATE_SUB(NOW(), INTERVAL 7 DAY) AND \
            NOW() \
            GROUP BY target_github, repository_description \
            ORDER BY nums DESC \
            LIMIT '

SQL_DAILY_PUSHED = "UPDATE repositories SET daily_pushed = b'1' WHERE repository_github = "
SQL_WEEKLY_PUSHED = "UPDATE repositories SET weekly_pushed = b'1' WHERE repository_github = "

class feedByMysql():
    # 周报接口
    def get_weekly(self,limit):
        # 接口response模板
        res = {
            'status': 0,
            'message': 'OK',
            'data': []
        }
        data = []
        try:
            for record in self.db_search(SQL_WEEKLY + str(limit)):
                data.append({
                    'url': record[0],
                    'description': record[1],
                    'count': record[2]
                })
                # 已推送过的项目进行标记
                self.db_update(SQL_WEEKLY_PUSHED + '"' + record[0] + '"')
            res['data'] = data
        except Exception as e:
            res['status'] = 1
            res['message'] = e.__str__()
        return res

    # 日报接口
    def get_daily(self,limit):
        # 接口response模板
        res = {
            'status': 0,
            'message': 'OK',
            'data': []
        }
        data = []
        try:
            for record in self.db_search(SQL_DAILY + str(limit)):
                data.append({
                    'url': record[0],
                    'description': record[1],
                    'count': record[2]
                })
                # 已推送过的项目进行标记
                self.db_update(SQL_DAILY_PUSHED + '"' + record[0] + '"')
            res['data'] = data
        except Exception as e:
            res['status'] = 1
            res['message'] = e.__str__()
        return res

    def db_update(self,sql):
        '''SQL更新，用于更新标记'''
        db = pymysql.connect(host=MYSQL_ADDR, user=MYSQL_USER, password=MYSQL_PASSWD, database=MYSQL_DATABASE)
        cursor = db.cursor()
        try:
            cursor.execute(sql)
            db.commit()
        except:
            db.rollback()
        db.close()

    def db_search(self,sql):
        '''SQL查询'''
        db = pymysql.connect(host=MYSQL_ADDR, user=MYSQL_USER, password=MYSQL_PASSWD, database=MYSQL_DATABASE)
        cursor = db.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        db.close()

        print(results)
        return results