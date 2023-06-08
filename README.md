# Почтовый Бот на Python 3
## Бот умеет:

1. Получать статьи с сайтов и обрабатывать их (получать заголовок, ссылки, категории).
2. Проверять на новизну статьи.
3. Определять статьи определенной категории.
4. Отправлять новые статьи на почту пользователя.
5. Выполнять комманды, присланные на почту, от пользователя и отправлять отчет об их выполнении.

## Для использования почтового бота нужно:

1. Скачать [Python 3](https://www.python.org/downloads/) с официального сайта
2. Установить библиотеки: requests, bs4, lxml.
3. Скачать файл [mailbot.py](https://github.com/EugeniyS/Mail-Bot-Sending-New-Articles-From-Sites/blob/main/mailbot.py).
4. В файле [mailbot.py](https://github.com/EugeniyS/Mail-Bot-Sending-New-Articles-From-Sites/blob/main/mailbot.py) в функции main() изменить: 
    - сслыку на файл с статьями (file_path_articles)
    - ссылку на файл с пользователями (file_path_users)
    - почту отправителя (send_mail)
    - пароль от почты отправителя (password)
    - ссылку на smtp (smtp_server) и imap (imap_server) сервер
    - порт smtp (port).
5. Запустить скрипт [mailbot.py](https://github.com/EugeniyS/Mail-Bot-Sending-New-Articles-From-Sites/blob/main/mailbot.py).
6. С почты получателя отправить письмо с коммандой /help, для получения всех комманд бота.
7. Подписаться на рассылку с помощью комманды /subscribe или /addtag.
