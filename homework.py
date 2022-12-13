import os
import requests
import sys
import time
import logging
from http import HTTPStatus

import telegram

from dotenv import load_dotenv
from constants import RETRY_PERIOD

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем доступность перменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    return False


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение <{message}>, успешно отправлено!')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """делает запрос к единственному эндпоинту API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            logging.error(
                f'ENDPOINT недоступен. HTTPStatus {response.status_code}'
            )
            raise ValueError(response.json()['code'])
    except Exception as error:
        logging.error(f'Ошибка при запросе к ENDPOINT API: {error}')
        raise Exception(f'Ошибка при запросе к ENDPOINT API: {error}')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    try:
        response['homeworks']
    except KeyError:
        logging.error('Нет ключа homeworks')
        raise KeyError('Нет ключа homeworks')
    if not isinstance(response, dict):
        logging.error('Не тот тип данных в запросе')
        raise TypeError('Не тот тип данных в запросе')
    if not isinstance(response['homeworks'], list):
        logging.error('Не тот тип данных в запросе')
        raise TypeError('Не тот тип данных в запросе')

    return response['homeworks']


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    """
    try:
        homework_name = homework['homework_name']
        verdict = HOMEWORK_VERDICTS[homework['status']]

        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError:
        logging.error('Нет ключа homeworks')
        raise KeyError('Нет ключа homeworks')


def main():
    """Основная логика работы бота."""
    if check_tokens() is False:
        logging.critical('Не пройдена проверка наличия токенов')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    old_message = ''
    timestamp = int(time.time())
    while True:
        try:
            all_homework = get_api_answer(timestamp)
            homework = check_response(all_homework)
            if len(homework) > 0:
                message = parse_status(homework[0])
                if old_message != message:
                    send_message(bot, message)
                    old_message = message
            else:
                message = 'Домашки нет'
                if old_message != message:
                    send_message(bot, message)
                    old_message = message
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            logging.error = f'Сбой в работе программы: {error}'
            message = f'Сбой в работе программы: {error}'
            if old_message != message:
                send_message(bot, message)
                old_message = message
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(handlers=[logging.FileHandler(
        filename="main.log", encoding='utf-8')],
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG)
    main()
