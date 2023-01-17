import os
import requests
import sys
import time
import logging
from http import HTTPStatus
import re

import telegram

from dotenv import load_dotenv
from constants import RETRY_PERIOD
import exceptions

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
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение <{message}>, успешно отправлено!')

        return True
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """делает запрос к единственному эндпоинту API-сервиса."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != HTTPStatus.OK:
            logging.error(
                f'ENDPOINT недоступен. HTTPStatus {response.status_code}'
            )
            raise exceptions.HttpStatusException(
                f'ENDPOINT недоступен. HTTPStatus {response.status_code}'
            )

        return response.json()
    except Exception as error:
        logging.error(f'Не удалось получить доступ к ENDPOINT: {error}')
        raise exceptions.ENDPOINTConnectError


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error('Не тот тип данных в запросе')
        raise TypeError('Не тот тип данных в запросе')
    try:
        response['homeworks']
    except KeyError:
        logging.error('Нет ключа homeworks')
        raise KeyError('Нет ключа homeworks')
    if not isinstance(response['homeworks'], list):
        logging.error('Не тот тип данных в запросе')
        raise TypeError('Не тот тип данных в запросе')

    return response['homeworks']


def parse_status(homework):
    """Парсит homework извлекая данные для ответа."""
    if homework['status'] not in HOMEWORK_VERDICTS:
        logging.error('Недокументированный статус домашней работы')
        raise exceptions.StatusHomeWorkException
    try:
        homework_name = homework['homework_name']
    except KeyError:
        logging.error('Нет ключа homework_name')
        raise KeyError('Нет ключа homework_name')
    try:
        verdict = HOMEWORK_VERDICTS[homework['status']]
    except KeyError:
        logging.error(f'В словаре нет ключа {homework["status"]}')
        raise KeyError(f'В словаре нет ключа {homework["status"]}')
    try:
        homework_date = homework['date_updated']
        rep = re.compile("[A-Z]")
        date = rep.sub(" ", homework_date)
    except KeyError:
        logging.error('Нет ключа date_updated')
        raise KeyError('Нет ключа date_updated')

    return (f'{date}изменился статус'
            f' проверки работы "{homework_name}". {verdict}')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Не пройдена проверка наличия токенов')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    old_message = ''
    message = ''
    timestamp = int(time.time() - 604800)
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                print(message)
            if old_message != message:
                if send_message(bot, message):
                    old_message = message
                    timestamp = response['current_date']
        except Exception as error:
            logging.error = f'Сбой в работе программы: {error}'
            message = f'Сбой в работе программы: {error}'
            if old_message != message:
                send_message(bot, message)
                old_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(handlers=[logging.FileHandler(
        filename="main.log", encoding='utf-8')],
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG)
    main()
