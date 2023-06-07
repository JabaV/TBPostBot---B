import vk_api
from datetime import datetime, timedelta
from time import sleep
from random import randint
from webserver import keep_alive
import logging
import traceback
import os

keep_alive()
# Настраиваем логирование
logging.basicConfig(filename='bot.log', level=logging.ERROR)

# Токен
token = os.environ['token']

# Время ожидания между проверками (в секундах)
wait_time = 60 * 60 * 12

# Авторизуемся с помощью токена
vk_session = vk_api.VkApi(token=token)

# Получаем объект для работы с API
vk = vk_session.get_api()

# Получаем идентификатор бота
bot_id = vk.users.get()[0]['id']

def load_groups_from_file(file_name):
    group_posts = {}

    with open(file_name, 'r', encoding='utf-8') as f:
        content = f.read()

    for record in content.split('---'):
        if record.strip() != '':
            parts = record.strip().split(':::', 1)
            if len(parts) == 2:
                group_id, post_info = parts
                post_text, photo_id = post_info.split('|||', 1)
                group_posts[int(group_id)] = (post_text.strip(), photo_id.strip())

    return group_posts

def load_closed_groups_from_file(file_name):
    with open(file_name, 'r', encoding='utf-8') as f:
        content = f.read()

    return [int(group_id.strip()) for group_id in content.split() if group_id.strip() != '']

def load_banned_groups_from_file(file_name):
    with open(file_name, 'r', encoding='utf-8') as f:
        content = f.read()

    return [int(group_id.strip()) for group_id in content.split() if group_id.strip() != '']

def ban_group(file_name, group_id):
    with open(file_name, 'a', encoding='utf-8') as f:
        f.write(f'{group_id}\n')

group_posts = load_groups_from_file('groups.txt')
group_ids = list(group_posts.keys())
closed_group_ids = load_closed_groups_from_file('closed_groups.txt')
banned_group_ids = load_banned_groups_from_file('banned_groups.txt')

while True:
    try:
        for group_id in group_ids:
            if group_id in banned_group_ids:
                continue
            try:
                # Получаем последние 100 записей на стене группы
                posts = vk.wall.get(owner_id=-group_id, count=100)['items']
            except vk_api.exceptions.ApiError as e:
                if e.code == 15:  # Ошибка доступа, возможно, бот заблокирован
                    logging.warning(f'Access denied for group {group_id}, possibly banned')
                    ban_group('banned_groups.txt', group_id)
                    banned_group_ids = load_banned_groups_from_file('banned_groups.txt')
                    continue
                else:
                    raise e

            # Ищем последнюю запись, сделанную ботом
            last_bot_post = None
            for post in posts:
                if post['from_id'] == bot_id and post['text'] == group_posts[group_id][0]:
                    last_bot_post = post
                    break

            if last_bot_post is None:
                # Если бот еще ничего не опубликовал, публикуем первую запись
                post_text, photo_id = group_posts[group_id]
                attachment = f'photo{bot_id}_{photo_id}'
                vk.wall.post(owner_id=-group_id, message=post_text, attachments=attachment)
            else:
                # Иначе проверяем время последней публикации
                post_time = datetime.fromtimestamp(last_bot_post['date'])
                if group_id in closed_group_ids:
                    if timedelta(hours=24) <= datetime.now() - post_time <= timedelta(days=2):
                        post_text, photo_id = group_posts[group_id]
                        attachment = f'photo{bot_id}_{photo_id}'
                        vk.wall.post(owner_id=-group_id, message=post_text, attachments=attachment)
                else:
                    if post_time <= datetime.now() - timedelta(seconds=wait_time):
                        post_text, photo_id = group_posts[group_id]
                        attachment = f'photo{bot_id}_{photo_id}'
                        vk.wall.post(owner_id=-group_id, message=post_text, attachments=attachment)

            # Ожидаем случайное количество времени между отправкой постов
            sleep(randint(60, 1074))

    except Exception as e:
        logging.error(traceback.format_exc())
        sleep(60)  # Если произошла ошибка, подождем минуту перед повторной попыткой

