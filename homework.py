import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    filename='~/main.log',
    format='%(funcName)s, %(lineno)s, %(levelname)s, %(message)s',
    encoding='UTF-8',
    filemode='w'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('my_logger.log',
                              encoding='UTF-8',
                              maxBytes=50000000,
                              backupCount=5
                              )
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(funcName)s, %(lineno)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение в чат')
    except Exception('Ошибка отправки сообщения'):
        logger.error('Ошибка отправки сообщения')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=params
                                         )
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise Exception(f'Ошибка при запросе к основному API: {error}')
    if homework_statuses.status_code != HTTPStatus.OK:
        status_code = homework_statuses.status_code
        logging.error(f'Ошибка {status_code}')
        raise Exception(f'Ошибка {status_code}')
    try:
        return homework_statuses.json()
    except ValueError:
        logger.error('Ошибка парсинга ответа из формата json')
        raise ValueError('Ошибка парсинга ответа из формата json')


def check_response(response):
    """Проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API.
    Ответ приведен к типам данных Python.
    Если ответ API соответствует ожиданиям, то функция должна вернуть
    список домашних работ (он может бытьnи пустым), доступный в ответе
    API по ключу 'homeworks'
    """
    if type(response) is not dict:
        raise TypeError
    try:
        list_works = response['homeworks']
    except KeyError:
        logger.error
        raise KeyError
    try:
        homework = list_works[0]
    except IndexError:
        logger.error
        raise IndexError
    return homework


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает всего один элемент из списка домашних
    работ. В случае успеха, функция возвращает подготовленную для отправки в
    Telegram строку, содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception(f'Неизвестный статус работы: {homework_status}')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка токенов."""
    var = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for i in var:
        if i is None:
            logger.error(f'Отсутствует переменная {i}')
            return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    flag = ''
    if not check_tokens():
        logger.critical
        raise Exception
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            message = parse_status(check_response(response))
            if message != flag:
                send_message(bot, message)
                flag = message
            time.sleep(RETRY_TIME)
        except Exception as error:
            logger.error(error)
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
