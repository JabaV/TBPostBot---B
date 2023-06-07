import vk_api
from vk_api.exceptions import AuthError
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from datetime import datetime, timedelta
from time import sleep

# Логин и пароль пользователя
token =  'vk1.a.716sbCFj3cv7pE1ozA6EFqr2Osq6Y3Q6JAPrqkmnLBRxGH0jaNRsLf99svzrUbdO_6YG16Tk_KynPlF3kV1Kc4_aSz_7TFOZQSopNM8xIbyEQgdvNrTob41uScZiBr4KeyEPxQwcmIzgZnCWwuyCb0HseSQkJybd-BNXrFcIbCUE_WvKYvmsKhvr-DNvBK-0-zLvo0NWA9mWFhhPJ3r24A'
tok = str(token)
# Функция-обработчик для двухфакторной аутентификации
def auth_handler():
    code = input("Enter authentication code: ")
    remember_device = True
    return code, remember_device

# Авторизуемся с помощью токена
vk_session = vk_api.VkApi(token=tok)

# Получаем объект для работы с API
vk = vk_session.get_api()

# Получаем идентификатор бота
bot_id = vk.users.get()[0]['id']

group_posts = {
    219775222: 'Бибурат'
}

group_ids = list(group_posts.keys())

# Время ожидания между проверками (в секундах)
wait_time = 60 # для дебага пока 60, должно быть 12 * 60 * 60 для стандартной работы

while True:
    for group_id in group_ids:
        # Получаем последние 100 записей на стене группы
        posts = vk.wall.get(owner_id=-group_id, count=100)['items']

        # Ищем последнюю запись, сделанную ботом
        last_bot_post = None
        for post in posts:
            if post['from_id'] == bot_id and post['text'] == group_posts[group_id]:
                last_bot_post = post
                break

        if last_bot_post is None:
            # Если бот еще ничего не опубликовал, публикуем первую запись
            post_text = group_posts[group_id]
            vk.wall.post(owner_id=-group_id, message=post_text)
        else:
            # Иначе проверяем время последней публикации
            post_time = datetime.fromtimestamp(last_bot_post['date'])
            if post_time <= datetime.now() - timedelta(seconds=wait_time):
                post_text = group_posts[group_id]
                vk.wall.post(owner_id=-group_id, message=post_text)

    sleep(wait_time)