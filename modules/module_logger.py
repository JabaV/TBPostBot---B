import datetime

elog = open("error_log.txt", "a+", encoding='utf-8')
log = open("log.txt", "a+", encoding='utf-8')


def eLog(error):
    elog.write("[" + str(datetime.datetime.now().date()) + ' ' + str(datetime.datetime.now().timetz()) + "] " + str(error) + "\n")
    elog.flush()


def Log(action):
    log.write("[" + str(datetime.datetime.now().date()) + ' ' + str(datetime.datetime.now().timetz()) + "] " + str(action) + "\n")
    log.flush()
