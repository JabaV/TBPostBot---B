import vk_api
from vk_api.exceptions import AuthError
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from datetime import datetime, timedelta

# Логин и пароль пользователя
login = '79314181505'
password = '4Qm9sMCAkzhtcuA'
scope = vk_api.VkUserPermissions.GROUPS + vk_api.VkUserPermissions.NOTIFICATIONS + vk_api.VkUserPermissions.WALL
# Функция-обработчик для двухфакторной аутентификации
def auth_handler():
    code = input("Enter authentication code: ")
    remember_device = True
    return code, remember_device

# Авторизуемся как обычный пользователь
vk_session = vk_api.VkApi(login, password, auth_handler=auth_handler, scope=scope)
try:
    vk_session.auth()
except AuthError as e:
    print(e)

# Получаем объект для работы с API
vk = vk_session.get_api()

# Словарь, в котором хранятся тексты записей для каждой группы
group_posts = {
    172386457: 'Текст записи для первой группы'
}

# Получаем Long Poll сервер для первой группы
group_ids = list(group_posts.keys())
longpoll = VkLongPoll(vk_session)

# Основной цикл бота
while True:
    # Получаем новые события Long Poll API
    events = longpoll.check()

    # Обрабатываем каждое событие
    for event in events:
        # Если это новая запись на стене
        if event.type == VkEventType.WALL_POST_NEW and event.group_id in group_ids:
            # Определяем, какую запись нужно отправить на стену группы
            post_text = group_posts[event.group_id]

            # Отправляем запись на стену группы
            vk.wall.post(owner_id=-event.group_id, message=post_text)

            # Ждем 12 часов
            post_time = datetime.now() + timedelta(hours=12)
            while datetime.now() < post_time:
                pass

# Завершаем сеанс
vk_session.close()