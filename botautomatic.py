import vk_api
import random
from datetime import datetime, timedelta
from time import sleep
from random import randint
from webserver import keep_alive
from modules import module_logger
import pickle
import os

keep_alive()
skip = 0
token = os.environ['token']

# время для постинга
wait_time = 60 * 60 * 12

vk_session = vk_api.VkApi(token=token)

vk = vk_session.get_api()

bot_id = vk.users.get()[0]['id']

time_dict = {}

# функция для постинга
def post(_target_group: int, _text: str, _image: int):
    vk.wall.post(owner_id=-_target_group,
                 message=_text,
                 attachments=f'photo{bot_id}_{_image}')


# парсер для строк
def parse(_string: str):
    _timer = None
    _group, _text, _image = _string[:_string.find(':')], \
        _string[_string.find(':') + 1:_string.find('|')], \
        _string[_string.find('|') + 1:]

    if '?' in _string:
        _image = _string[_string.find('|') + 1:_string.find('?')]
        _timer = _string[_string.find('?') + 1:]
        _timer = int(_timer)

    _group = int(_group)
    _image = int(_image.replace('\n', ''))

    return _group, _text, _image, _timer


def prepare(_text: str):
    _time_dict = None
    if _text == '-':
        _text = 'files/text' + str(random.randint(1, 5)) + '.txt'
    with open(_text, 'r', encoding='utf-8') as f:
        # читает рекламный текст для конкретной группы
        _text = f.read()

    with open('files/dumping.pkl', 'rb+') as _p:
        if os.stat('files/dumping.pkl').st_size != 0:
            _time_dict = pickle.load(_p)
    return _text, _time_dict


def get_last_post(_tg: int):
    # noinspection PyShadowingNames
    last_post = None
    try:
        count = 2
        while count:
            wt = vk.groups.getById(group_id=_tg, fields='wall')[0]['wall']
            posts = vk.wall.get(owner_id=-target_group, offset=0 if count == 2 else 100, count=100)['items']
            if len(posts) < 1:
                return None
            else:
                if wt == 1:
                    for x in posts:
                        if x['from_id'] == bot_id:
                            last_post = x
                            break
                elif wt == 2 or wt == 3:
                    for x in posts:
                        if 'signer_id' in x:
                            if x['signer_id'] == bot_id:
                                last_post = x
                                break
            if last_post is None:
                count -= 1
            else:
                count = 0
                return last_post
        return last_post
    except Exception as e:
        module_logger.eLog(f'Something happened during postwatch in {target_group}\n' + str(e))
        return -1


def check_suggests(_tg: int, time: int):
    # noinspection PyUnusedLocal
    suggested_posts = vk.wall.get(owner_id=-target_group, filter='suggests')
    last_pst = get_last_post(_tg)
    if len(suggested_posts['items']) < 1:
        if _tg in time_dict:
            if datetime.now() - time_dict[target_group] >= timedelta(seconds=time):
                module_logger.eLog(
                    f'Post in group {target_group} timed for too many days. Strange.'
                    f' Posting again to remind of myself')
                return 1
            else:
                return 0
        elif last_pst is not None:
            if last_pst != -1:
                if datetime.now() - datetime.fromtimestamp(last_pst['date']) >= timedelta(seconds=time):
                    return 1
                else:
                    return 0
            else:
                return -1
        else:
            if _tg in time_dict:
                if datetime.now() - time_dict[target_group] >= timedelta(seconds=time):
                    return 1
                else:
                    return 0
            else:
                return 1
    suggest_time = suggested_posts['items'][0]['date']
    if datetime.now() - datetime.fromtimestamp(suggest_time) >= timedelta(seconds=time):
        module_logger.eLog(
            f'Post in group {target_group} delayed for 3 days or more. Dead one?'
            f' Posting again to remind of myself')
        return 1
    return 0


def choose_time(_timer):
    if _timer is None:
        return wait_time
    else:
        return _timer


while True:
    try:
        with open('files/groups.txt', 'r', encoding='utf-8') as file:
            while string := file.readline():
                if skip == 1:
                    skip = 0
                    continue
                target_group, text, image, timer = parse(string)
                text, time_dict = prepare(text)
                module_logger.Log(f"Now working with group {target_group}")

                group = vk.groups.getById(group_id=target_group, fields='wall')
                wall_type = group[0]['wall']
                module_logger.Log("Got the wall type")

                if wall_type == 2 or wall_type == 3:
                    should_post = check_suggests(target_group, choose_time(timer))
                    module_logger.Log("Should I post here?")
                    if should_post == 1:
                        module_logger.Log("Definitly yes")
                        vk.account.setOnline()
                        post(target_group, text, image)
                        time_dict[target_group] = datetime.now()
                        module_logger.Log("Posted and saved time")
                        with open('files/dumping.pkl', 'wb+') as p:
                            pickle.dump(time_dict, p)
                    if should_post == -1:
                        module_logger.Log("Absolutly no")
                        vk.account.setOffline()
                        sleep(randint(30, 468))
                        continue
                elif wall_type == 1:
                    temp_time = choose_time(timer)
                    module_logger.Log("Choosed time to post")
                    last_bot_post = get_last_post(target_group)
                    if last_bot_post is None:
                        module_logger.Log("Can't find my post! Posting right now...")
                        vk.account.setOnline()
                        post(target_group, text, image)
                    elif last_bot_post != -1:
                        module_logger.Log("Found a post, but I need another one")
                        # noinspection PyUnresolvedReferences
                        post_time = last_bot_post['date']
                        if datetime.fromtimestamp(post_time) <= datetime.now() - timedelta(seconds=temp_time):
                            vk.account.setOnline()
                            post(target_group, text, image)
                    elif last_bot_post == -1:
                        module_logger.Log("My job here is done")
                        vk.account.setOffline()
                        sleep(randint(30, 468))
                        continue
                vk.account.setOffline()
                module_logger.Log("Sleep for next iteration")
                sleep(randint(30, 468))
    except Exception as e:
        module_logger.eLog(str(target_group) + ' ' + str(e))
        sleep(60)
        skip = 1
