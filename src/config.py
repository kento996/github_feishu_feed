import configparser

CONFIG_BUILD = 'config/config_dev.txt'
CONFIG_DEV = 'config/config_pro.txt'

REDIS_ADDR = ''
REDIS_PORT = ''
REDIS_DATABASE = ''
REDIS_PASSWD = ''

MYSQL_ADDR = '127.0.0.1'
MYSQL_PORT = '3306'
MYSQL_DATABASE = 'rss'
MYSQL_USER = 'root'
MYSQL_PASSWD = 'root'

class Config():
    global REDIS_PASSWD, REDIS_ADDR, REDIS_PORT, REDIS_DATABASE, \
        MYSQL_PORT, MYSQL_USER, MYSQL_DATABASE, MYSQL_PASSWD, MYSQL_ADDR

    def __init__(self,opt:str):
        mode=opt.replace("--","")
        self.config = configparser.ConfigParser()
        try:
            if mode=="build":
                self.config.read(CONFIG_BUILD,encoding="utf-8")
            elif mode=="dev":
                self.config.read(CONFIG_DEV, encoding="utf-8")
            else:
                raise Exception
        except Exception as e:
            raise RuntimeError(f"config find a undefined parse :{e}")


    def get_config(self):
        config={}
        # 读取Redis配置
        REDIS_ADDR = self.config.get("Redis", "addr")
        config.update({"REDIS_ADDR":REDIS_ADDR})
        REDIS_PORT = self.config.get("Redis", "port")
        config.update({"REDIS_PORT":REDIS_PORT})
        REDIS_DATABASE = self.config.get("Redis", "database")
        config.update({"REDIS_DATABASE":REDIS_DATABASE})
        REDIS_PASSWD = self.config.get("Redis", "password")
        config.update({"REDIS_PASSWD":REDIS_PASSWD})
        # 读取MySQL配置
        MYSQL_ADDR = self.config.get("MySQL", "hostname")
        config.update({"MYSQL_ADDR": MYSQL_ADDR})
        MYSQL_PORT = self.config.get("MySQL", "port")
        config.update({"MYSQL_PORT": MYSQL_PORT})
        MYSQL_DATABASE = self.config.get("MySQL", "database")
        config.update({"MYSQL_DATABASE": MYSQL_DATABASE})
        MYSQL_USER = self.config.get("MySQL", "username")
        config.update({"MYSQL_USER": MYSQL_USER})
        MYSQL_PASSWD = self.config.get("MySQL", "password")
        config.update({"MYSQL_PASSWD": MYSQL_PASSWD})

        return config

