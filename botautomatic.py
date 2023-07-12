# Бро, это тестовая ветка, нахуй ты сюда смотришь?
import vk_api
from datetime import datetime, timedelta
from time import sleep
from random import randint
from webserver import keep_alive
from modules import module_logger
import pickle
import os

# keep_alive()

# token = os.environ['token']
token = 'vk1.a.716sbCFj3cv7pE1ozA6EFqr2Osq6Y3Q6JAPrqkmnLBRxGH0jaNRsLf99svzrUbdO_6YG16Tk_KynPlF3kV1Kc4_aSz_7TFOZQSopNM8xIbyEQgdvNrTob41uScZiBr4KeyEPxQwcmIzgZnCWwuyCb0HseSQkJybd-BNXrFcIbCUE_WvKYvmsKhvr-DNvBK-0-zLvo0NWA9mWFhhPJ3r24A'

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
            if posts['count'] < 1:
                return None
            else:
                if wt == 1:
                    last_post = next((x for x in posts if x['from_id'] == bot_id), None)
                elif wt == 2 or wt == 3:
                    last_post = next((x for x in posts if x['signer_id'] == bot_id), None)
            if count == 1:
                break
            else:
                count -= count
    except Exception as e:
        module_logger.Log(f'Something happened during postwatch in {target_group}\n' + str(e))
        return -1
    return last_post


def check_suggests(_tg: int, time: int):
    # noinspection PyUnusedLocal
    respond = 0
    suggested_posts = vk.wall.get(owner_id=-target_group, filter='suggests')
    if len(suggested_posts['items']) < 1:
        if _tg in time_dict:
            if datetime.now() - time_dict[target_group] >= timedelta(seconds=time):
                module_logger.Log(
                    f'Post in group {target_group} timed for too many days or more. Strange.'
                    f' Posting again to remind of myself')
                return 1
            else:
                return 0
        elif last_pst := get_last_post(_tg) is not None:
            if last_pst != -1:
                if datetime.now() - datetime.fromtimestamp(last_pst['date']) >= timedelta(seconds=time):
                    return 1
                else:
                    return 0
            else:
                return 0
        else:
            return 1
    suggest_time = suggested_posts['items'][0]['date']
    if datetime.now() - datetime.fromtimestamp(suggest_time) >= timedelta(seconds=time):
        module_logger.Log(
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
                target_group, text, image, timer = parse(string)
                text, time_dict = prepare(text)

                group = vk.groups.getById(group_id=target_group, fields='wall')
                wall_type = group[0]['wall']

                if wall_type == 2 or wall_type == 3:
                    should_post = check_suggests(target_group, choose_time(timer))
                    if should_post == 1:
                        post(target_group, text, image)
                elif wall_type == 1:
                    temp_time = choose_time(timer)
                    last_bot_post = get_last_post(target_group)
                    if last_bot_post is None:
                        post(target_group, text, image)
                    elif last_bot_post != -1:
                        # noinspection PyUnresolvedReferences
                        post_time = last_bot_post['date']
                        NIGGER = datetime.fromtimestamp(vk.utils.getServerTime()) - datetime.fromtimestamp(post_time)
                        if datetime.fromtimestamp(post_time) <= datetime.now() - timedelta(seconds=temp_time):
                            post(target_group, text, image)
        vk.account.setOffline()
        # sleep(randint(30, 468))
    except Exception as e:
        module_logger.Log(str(target_group) + ' ' + str(e))
        sleep(60)
