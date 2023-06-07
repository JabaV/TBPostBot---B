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

# Словарь, в котором хранятся тексты записей для каждой группы
group_posts = {
    219775222: 'Текст записи для первой группы'
}

# Получаем список групп
group_ids = list(group_posts.keys())

# Отправляем запись на стену каждой группы при запуске
for group_id in group_ids:
    post_text = group_posts[group_id]
    vk.wall.post(owner_id=-group_id, message=post_text)

# Основной цикл бота
while True:
    # Для каждой группы проверяем наличие новых записей
    for group_id in group_ids:
        # Получаем последнюю запись на стене группы
        posts = vk.wall.get(owner_id=-group_id, count=1)
        last_post = posts['items'][0] if posts['items'] else None

        # Если это новая запись
        if last_post and last_post['date'] > datetime.now().timestamp() - 12*60*60:
            # Определяем, какую запись нужно отправить на стену группы
            post_text = group_posts[group_id]

            # Отправляем запись на стену группы
            vk.wall.post(owner_id=-group_id, message=post_text)

    # Ждем 12 часов перед следующей проверкой
    sleep(12*60*60)
    vk_session.close()