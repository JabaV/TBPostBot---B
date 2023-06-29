import vk_api
from datetime import datetime, timedelta
from time import sleep
from random import randint
from webserver import keep_alive
from modules import module_logger
import os

keep_alive()

token = os.environ['token']

# время для постинга
wait_time = 60 * 60 * 12

vk_session = vk_api.VkApi(token=token)

vk = vk_session.get_api()

bot_id = vk.users.get()[0]['id']

# функция для постинга


def post(_target_group: int, _text: str, _image: int):
    vk.wall.post(owner_id=-_target_group,
                 message=_text,
                 attachments=f'photo{bot_id}_{_image}')


# парсер для строк
def parse(_string: str):
    _group, _text, _image = string[:string.find(':')], \
        string[string.find(':')+1:string.find('|')], \
        string[string.find('|')+1:]
    _group = int(_group)
    _image = _image.replace('\n', '')
    _image = int(_image)
    return _group, _text, _image


# цикл
while True:
    try:
        # открывает файл
        with open('files/groups.txt', 'r', encoding='utf-8') as file:
            # цикл построчно его читает
            while string := file.readline():
                # парсит строку
                target_group, text, image = parse(string)
                # пытаемся получить последние 100 постов
                try:
                    posts = vk.wall.get(owner_id=-target_group, count=100)['items']
                    # обработка ошибки если забанили
                except Exception as e:
                    if e.code == 15:
                        module_logger.Log(
                            f'Possibly banned in group with id {target_group}.\n'
                            f'Consider deleting this group from list')
                        continue # скипает группу в которой забанили

                with open(text, 'r', encoding='utf-8') as f:
                    # читает рекламный текст для конкретной группы
                    text = f.read()

                # смотрим время
                last_bot_post = None
                for poster in posts:
                    if poster['from_id'] == bot_id and poster['text'] == text:
                        last_bot_post = poster
                        break
                if last_bot_post is None:
                    post(target_group, text, image)
                else:
                    group = vk.groups.getById(group_id=target_group, fields='wall')
                    wall_type = group[0]['wall']
                    post_time = datetime.fromtimestamp(last_bot_post['date'])
                    # если есть предложка, то постим по-другому
                    if wall_type == 2:
                        if timedelta(hours=24) <= datetime.now() - post_time <= timedelta(days=2):
                            post(target_group, text, image)
                    # если стена открыта, то постим часто
                    elif wall_type == 1:
                        if post_time <= datetime.now() - timedelta(seconds=wait_time):
                            post(target_group, text, image)
                    else:
                        module_logger.Log(f'Cannot post in group {target_group}.' +
                                          ' Please delete it from list')
                # спим
                sleep(randint(60, 1074))

    except Exception as e:
        module_logger.Log(e)
        sleep(60)
