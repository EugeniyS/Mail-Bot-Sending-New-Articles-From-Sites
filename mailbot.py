import requests
import os
import os.path
import re
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib, ssl
import time
import imaplib
import email
from email.header import decode_header
import base64
from bs4 import BeautifulSoup

#Получение статей из файла. Каждая статья имеет: заголовок, сслыку, категории, адреса электронной почты, на которые статья была когда-то отправлена
def get_articles_from_file(file_path):
    if not os.path.isfile(file_path):
        return []
    articles_pattern=r'<a href=".*" categories=".*" emails=".*">.*<\/a>'
    article_link_pattern=r'href="(.*)" categories'
    article_title_pattern=r'>(.*)<'
    article_categories_pattern=r'categories="(.*)" emails'
    article_emails_pattern=r'emails="(.*)">'
    f=open(file_path, 'r', encoding="utf-8")
    all_str=f.read()
    f.close()
    all_str=re.findall(articles_pattern,all_str)
    articles=[]
    for str in all_str:
        emails=re.findall(article_emails_pattern,str)[0]
        emails=emails.split(',')
        check=False
        for i in range(0,len(emails)):
            emails[i]=emails[i].strip()
        article={}
        article['title']=re.findall(article_title_pattern,str)[0]
        article['link']=re.findall(article_link_pattern,str)[0]
        categories=re.findall(article_categories_pattern,str)[0]
        categories=categories.split(',')
        for i in range(0,len(categories)):
            categories[i]=categories[i].strip()
        article['categories']=categories
        article['emails']=emails
        articles.append(article)
    return articles

#Проверка статьи на наличие конкретного адреса электронной почты
def check_mail(articles,mail):
    new_articles=[]
    for article in articles:
        for email in article['emails']:
            if mail==email:
                new_articles.append(article)
                break
    return new_articles

#Получение контент из запроса к адресу сайта
def get_info_from_link(link):
    try:
        req=requests.get(link)
    except Exception as exp:
        return False
    return req.content

#Проверка статьи на наличие нужной категории, проверка на повторность статей
def check_item(article,old_articles,categories):
    if categories!=['nocat']:
        check=False
        for category in categories: 
            for article_category in article['categories']:
                if category.lower()==article_category.lower():
                    check=True
            if check:
                break
        if not check:
            return False
    if len(old_articles)==0:
        return True
    for old_article in old_articles:
        if old_article['title']==article['title'] and old_article['link']==article['link']:
            return False
    return True

#Отправка сообщения по почте.
def send_message(send_mail,recepient_mail,smtp_server,port,password,subject,message_type,message):
    try:
        msg = MIMEMultipart()
        msg['From'] = send_mail
        msg['To'] = recepient_mail
        msg['Subject'] = subject
        msg.attach(MIMEText(message, message_type, "utf-8"))
        if port=='465':
            context = ssl.create_default_context()
            server= smtplib.SMTP_SSL(smtp_server, port, context=context)
            server.login(msg['From'], password)
            server.sendmail(msg['From'], msg['To'], msg.as_string())
            server.quit()
        elif port=='587':
            server = smtplib.SMTP(smtp_server,port)
            server.starttls()
            server.login(msg['From'], password)
            server.sendmail(msg['From'], msg['To'], msg.as_string())
            server.quit()
    except Exception as exp:
        return False
    return True

#Добавление новых адресов к существующим статьям или добавление новых статей к существующим
def check_articles(new_articles,old_articles,mail):
    for new_article in new_articles:
        new_article['emails']=[]
        new_article['emails'].append(mail)
        check=False
        article=""
        for i in range(0, len(old_articles)):
            if new_article['title']==old_articles[i]['title'] and new_article['link']==old_articles[i]['link']:
                check=True
                check_mail=False
                for email in old_articles[i]['emails']:
                    if mail==email:
                        check_mail=True
                if not check_mail:
                    old_articles[i]['emails'].append(mail)
                break
        if not check:
            old_articles.append(new_article)
    return old_articles

#Формирование списка тегов со статьями для записи в файл
def form_tegs(articles):
    string=""
    for article in articles:
        string+="<a href=\""+article['link']+"\" categories=\""
        for i in range(0,len(article['categories'])):
            string+=article['categories'][i]
            if i<len(article['categories'])-1:
                string+=', '
        string+="\" emails=\""
        for i in range(0,len(article['emails'])):
            string+=article['emails'][i]
            if i<len(article['emails'])-1:
                string+=', '
        string+="\">"+article['title']+"</a>\n"
    return string 

#Формирование html с ссылками на новые статьи для отправки по почте
def generate_html(articles,links):
    title="Новые посты"
    message="""<html lang="ru">
        <head> 
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8"> 
        <title>"""+title+"""</title>
        <style type="text/css">
	@import 'https://fonts.googleapis.com/css?family=Merriweather';
	div {
  		padding: 20px 0;
  		border-bottom: 2px solid rgba(0,0,0,.05); 
  		text-align: center;
	}
        </style> 
        </head> 

        <body style="margin:0;">
        """
    for link in links:
        main_link=re.findall(r'https?:\/\/(.*)',link['link'])[0]
        main_link=main_link[:main_link.find('/')]
        check=False
        cat=" с тегами: "
        if link['categories']==['nocat']:
            cat=" без тегов!"
        else:
            cat+=', '.join(link['categories']).title()
        mes="""<div class="d3" style="text-align:center"><h1 style="font-family: 'Merriweather', serif;
  		font-size: 30px;
  		letter-spacing: 1px;
  		max-width: 320px;
  		width: 100%;
  		position: relative;
  		display: inline-block;
  		color: #465457;"><span>"""+title+' с '+main_link+cat+"""</span></h1></div>
        """
        for article in articles:
            article_link=re.findall(r'https?:\/\/(.*)',article['link'])[0]
            article_link=article_link[:article_link.find('/')]
            if(article_link==main_link):
                check=True
                string_article="<a href=\""+article['link']+"\" target=\"_blank\" style=\"box-sizing:border-box;color:rgb(51,51,51);text-decoration-line:none;font-family:'Fira Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;font-size:22px;line-height:29px\" rel=\" noopener noreferrer\">"+article['title']+"</a>&nbsp;"
                mes+="""<div style="box-sizing:border-box">
                """+string_article+"""</div>"""
        if check:
            message+=mes
    message+="</body></html>"
    return message

#Получение новых статей
def get_new_articles(links,all_articles,recepient_mail):
    old_articles=check_mail(all_articles,recepient_mail)
    new_articles=[]
    for link in links:
        func=globals()[link['method']]
        articles=func(link,old_articles)
        new_articles.extend(articles)
    return new_articles

#Основная программа получения новых статей
def main_prog(send_mail,password,recepient_mail,links,smtp_server,port,user,file_path):
    for k in range(0,len(links)):
        link=re.findall(r'https?:\/\/(.*)',links[k]['link'])[0]
        link=link[:link.find('/')]
        if link=='habr.com':
            links[k]['categories']=user['habr_categories']
        if link=='vc.ru':
            links[k]['categories']=user['vc_categories']

    all_articles=get_articles_from_file(file_path)

    new_articles=get_new_articles(links,all_articles,recepient_mail)
   
    if len(new_articles)!=0:#Проверка на наличие новых статей
        subject= "Новые посты!"
        message=generate_html(new_articles,links)

        check=False
        for i in range(0,100):
            check=send_message(send_mail,recepient_mail,smtp_server,port,password,subject,'html',message)
            if check:
                break
        if not check:
            print("Send Message Error!\n")
            return False
        
        new_articles=check_articles(new_articles,all_articles,recepient_mail)

        tegs=form_tegs(new_articles)
        file=open(file_path,'w+',encoding='utf-8')#Открытие файла для перезаписи
        file.write(tegs)#Запись статей в файл
        file.close()
        return True
    else: 
        return True
    
#Получение новых статей с сайта habr.com
def get_articles_from_habr(link,old_articles):
    new_articles=[]
    for page in range(1,51):
        soup=False
        for i in range(0,100):
            soup=get_info_from_link(link['link']+str(page))
            if soup:
                soup=BeautifulSoup(soup, features='xml')
                break
        if not soup: 
            print('Connection Error!\n')
            break
        items=soup.findAll('item')
        if  len(items)==0:
            break
        for item in items:
            article={}
            article['title']=item.find('title').text
            article['link']=item.find('guid').text
            categories=item.findAll('category')
            article['categories']=[]
            for category in categories:
                article['categories'].append(category.text)
            if check_item(article,old_articles,link['categories']):
                new_articles.append(article)
    return new_articles

#Получение новых статей с сайта vc.ru
def get_articles_from_vcru(link,old_articles):
    new_articles=[]
    last_id=0
    last_sorting_value=1
    for page in range(1,51):
        soup=False
        for i in range(0,100):
            soup=get_info_from_link(link['link']+'last_sorting_value='+str(last_sorting_value)+'&last_id='+str(last_id))
            if soup:
                soup=json.loads(soup)
                break
        if not soup: 
            print('Connection Error!\n')
            break
        last_id=soup['data']['last_id']
        last_sorting_value=soup['data']['last_sorting_value']
        items_html=soup['data']['items_html']
        items=BeautifulSoup(items_html,'lxml')
        if len(items)==0:
            break
        items=items.find_all('div',class_='feed__item l-island-round')
        for item in items:
            article={}
            article['title']=item.find('div',class_='content-title content-title--short l-island-a')
            if not article['title']:
                continue
            if article['title'].find('span',class_='content-title__last-word'):
                if article['title'].find('span',class_='content-title__last-word').find('a'):
                   article['title'].find('span',class_='content-title__last-word').find('a').decompose()
            article['title']=article['title'].text.strip()
            article['link']=item.find('a',class_='content-link')['href']
            categories=item.find('div',class_='content-header__info')
            article['categories']=[]
            if categories.find('div',class_='content-header-author content-header-author--user content-header__item content-header-author--desktop'):
                article['categories'].append(categories.find('div',class_='content-header-author content-header-author--subsite content-header__item content-header-author--shrink').find('div',class_='content-header-author__name').text.strip())
            if check_item(article,old_articles,link['categories']):
                new_articles.append(article)
    return new_articles

#Получение пользователей из файла. Пользователь имеет: адрес электронной почты, категории, статьи с которыми будут ему присылаться, время, для отправки сообщения через определенный промежуток
def get_users_from_file(file_path):
    if not os.path.isfile(file_path):
        return []
    users_pattern=r'<user habr_categories=".*" vc_categories=".*" time=".*">.*<\/user>'
    habr_categories_pattern=r'habr_categories="(.*)" vc_categories'
    email_pattern=r'>(.*)<'
    vc_categories_pattern=r'vc_categories="(.*)" time'
    time_pattern=r'time="(.*)">'
    f=open(file_path, 'r', encoding="utf-8")
    all_str=f.read()
    f.close()
    all_str=re.findall(users_pattern,all_str)
    users=[]
    for str in all_str:
        user={}
        user['email']=re.findall(email_pattern,str)[0]
        categories=re.findall(habr_categories_pattern,str)[0].split(',')
        for i in range(0,len(categories)):
            categories[i]=categories[i].strip()
        user['habr_categories']=categories
        categories=re.findall(vc_categories_pattern,str)[0].split(',')
        for i in range(0,len(categories)):
            categories[i]=categories[i].strip()
        user['vc_categories']=categories
        user['time']=float(re.findall(time_pattern,str)[0])
        users.append(user)
    return users

#Разделение комманд с электронной почты
def define_commands(element):
    commands=[]
    message=""
    command=''
    for line in element['text']:
        line=line.strip()
        if re.findall(r'<.*@.*\..*>',line)or line.strip()=='--':
            break
        if len(line)!=0 and line[0]=='/' and command!='':
            commands.append(command.strip(' ||'))
            command=''
        if len(line)!=0 and not line.isspace():
            command+=line+' ||'
    if command!='':
        commands.append(command.strip())
    return commands

#Проверка комманд на наличие комманды, правильность ввода, наличие парамметров и выполнение комманд        
def run_command(line,users,email):
    com=re.findall(r'\/\S*',line)[0]
    command=com.lower()
    parametrs=re.findall(r'\/\S* (.*)',line)
    message=''
    check_command=False
    if parametrs!=[] and parametrs!=['']:
        parametrs=parametrs[0]
    else:
        parametrs=''
    match(command):
        case '/help':#Возвращение сообщения со всеми существующими коммандами
            check_command=True
            message='Комманды:\n/subscribe - оформить подписку!\n/unsubscribe - отменить подписку!\n/list - теги, выбранные пользователем!\n/addtag - добавить тег!\nПример:\n/addtag\nhabr.com #DIY\n\n/deletetag - удалить тег!\nПример:\n/deletetag\nhabr.com #DIY\n\n/clear - очистить категории!\nПример:\n/clear all(или habr.com или vc.ru)'
        case '/subscribe':#Оформление подписки пользователем на рассылку
            check_command=True
            check=False
            for i in range(0,len(users)):
                if users[i]['email']==email:
                    check=True
                    message='У вас имеется подписка!'
                    break
            if not check:
                message='Подписка оформлена!'
                users.append({
                    'email':email,
                    'habr_categories':['nocat'],
                    'vc_categories':['nocat'],
                    'time':time.perf_counter()
                })
        case '/unsubscribe':#Отмена подписки пользователем на рассылку
            check_command=True
            check=False
            for i in range(0,len(users)):
                if users[i]['email']==email:
                    check=True
                    message='Подписка отменена!'
                    users.pop(i)
                    break
            if not check:
                message='Вы не имеете подписку!'
        case '/list':#Возвращение сообщения с выбранными пользователем категориями
            check_command=True
            check=False
            for i in range(0,len(users)):
                if users[i]['email']==email:
                    check=True
                    info=''
                    if users[i]['habr_categories']==['']:
                        info='Отсутствуют'
                    elif users[i]['habr_categories']==['nocat']:
                        info='Без категорий!'
                    else:
                        info=', '.join(users[i]['habr_categories'])
                    message='Ваши теги habr.com: \n'+info
                    if users[i]['vc_categories']==['']:
                        info='Отсутствуют'
                    elif users[i]['vc_categories']==['nocat']:
                        info='Без категорий!'
                    else:
                        info=', '.join(users[i]['vc_categories'])
                    message+='\nВаши теги vc.ru: \n'+info
                    break
            if not check:
                message='Вы не имеете подписку!'
        case '/addtag':#Добавление категории для отправки пользователю
            check_command=True
            message='Выполнение /addtag:'
            if parametrs!='':
                check=False
                parametrs=parametrs.strip('||').split(' ||')
                for i in range(0,len(users)):
                        if users[i]['email']==email:
                            check=True
                            break
                if not check:
                    users.append({
                        'email':email,
                        'habr_categories':[''],
                        'vc_categories':[''],
                        'time':time.perf_counter()
                    })
                for parametr in parametrs:
                    parametr=parametr.split(' ',1)
                    if len(parametr[1])==0:
                        message+='\nНе введено название тега!'
                        continue
                    s=parametr[0]
                    site=s.lower()
                    category=parametr[1].strip()
                    category=category.split()
                    if category[0][0]=='<'and category[0][-1]=='>':
                        category.pop(0)
                    category=' '.join(category)
                    if site=='habr.com':
                        key='habr_categories'
                    elif site=='vc.ru':
                        key='vc_categories'
                    else:
                        message+='\nСайт "'+s+'" не существует!'
                        continue
                    if category[0]!='#':
                        message+='\nНазвание тега вводится через решетку: #название тега! : '+category
                        continue
                    for i in range(0,len(users)):
                        if users[i]['email']==email:
                            if users[i][key]==['']:
                                users[i][key]=[]
                            if category[1:]=='nocat'or users[i][key]==['nocat']:
                                users[i][key]=[]
                                users[i][key].append(category[1:])
                            else:
                                check_cat=False
                                for k in range(0,len(users[i][key])):
                                    if users[i][key][k].strip()==category[1:].lower():
                                        check_cat=True
                                if not check_cat:
                                    users[i][key].append(category[1:])
                            users[i]['time']=time.perf_counter()
                            message+='\nТег "'+category[1:]+'" добавлен в теги сайта "'+s+'"!'
            else:
                message='Не введены парамметры комманды /addtag\nПример:\n/addtag habr.com #DIY!'
        case '/deletetag':#Удаление категории. Статья с категорией не будет отправляться пользователю
            check_command=True
            message='Выполнение /deletetag:'
            if parametrs!='':
                check=False
                parametrs=parametrs.strip('||').split(' ||')
                for i in range(0,len(users)):
                        if users[i]['email']==email:
                            check=True
                            break
                if not check:
                    users.append({
                        'email':email,
                        'habr_categories':[''],
                        'vc_categories':[''],
                        'time':time.perf_counter()
                    })
                for parametr in parametrs:
                    parametr=parametr.split(' ',1)
                    if len(parametr[1])==0:
                        message+='\nНе введено название тега!'
                        continue
                    s=parametr[0]
                    site=s.lower()
                    category=parametr[1].strip()
                    category=category.split()
                    if category[0][0]=='<'and category[0][-1]=='>':
                        category.pop(0)
                    category=' '.join(category)
                    if site=='habr.com':
                        key='habr_categories'
                    elif site=='vc.ru':
                        key='vc_categories'
                    else:
                        message+='\nСайт "'+s+'" не существует!'
                        continue
                    if category[0]!='#':
                        message+='\nНазвание тега вводится через решетку: #название тега! : '+category
                        continue
                    for i in range(0,len(users)):
                        if users[i]['email']==email:
                            for k in range(0,len(users[i][key])):
                                if users[i][key][k].strip()==category[1:].lower():
                                    users[i][key].pop(k)
                                    if users[i][key]==[]:
                                        users[i][key]=['']
                                    break
                            users[i]['time']=time.perf_counter()
                            message+='\nТег "'+category[1:]+'" удален из тегов сайта "'+s+'"!'
            else:
                message='Не введены парамметры комманды /deletetag\nПример:\n/deletetag habr.com #DIY!'
        case '/clear':#Очистка категорий
            check_command=True
            parametrs=parametrs.split()
            if parametrs[0][0]=='<'and parametrs[0][-1]=='>':
                parametrs=parametrs[1]
            else:
                parametrs=parametrs[0]
            print(parametrs)
            par=parametrs
            check=False
            for i in range(0,len(users)):
                if users[i]['email']==email:
                    check=True
                    parametrs=parametrs.lower()
                    if parametrs=='all':
                        users[i]['habr_categories']=[]
                        users[i]['vc_categories']=[]
                    elif parametrs=='habr.com':
                        users[i]['habr_categories']=[]
                    elif parametrs=='vc.ru':
                        users[i]['vc_categories']=[]
                    else:
                        message='Сайт "'+par+'" отсутствует!'
                        break
                    users[i]['time']=time.perf_counter()
                    message='Теги сайта "'+par+'" очищены!'
            if not check:
                users.append({
                    'email':email,
                    'habr_categories':[''],
                    'vc_categories':[''],
                    'time':time.perf_counter()
                })
                message='Теги сайта "'+par+'" очищены!'
    if not check_command:
        message='Комманда '+com+' не найдена!'
    return message

#Получение сообщений с почты
def get_message_from_email(send_mail,password,imap_server):
    imap = imaplib.IMAP4_SSL(imap_server)
    imap.login(send_mail, password)
    imap.select("INBOX")
    result,data=imap.search(None, "UNSEEN")
    list=[]
    if result=='OK':
        ids=data[0]
        id_list=ids.split()
        for id in id_list:
            result, message = imap.fetch(id, '(RFC822)')
            if result=='OK':
                message = email.message_from_bytes(message[0][1])
                element={}
                element['email']=decode_header(message["From"])[1][0].decode().strip().lstrip('<').rstrip('>')
                element['text']=None
                for part in message.walk():
                    if part.get_content_maintype() == 'text' and part.get_content_subtype() == 'plain':
                       text=part.get_payload(decode=True).decode('utf-8')
                       element['text']=text.split('\r\n')
                if element['text']!=None:
                    list.append(element)   
    return list

#Сохранение списка тегов с информацией о пользователях в файл
def save_users_in_file(file_path,users):
    text=''
    for user in users:
        text+='<user habr_categories="'+', '.join(user['habr_categories']).lower().strip()+'" vc_categories="'+', '.join(user['vc_categories']).lower().strip()+'" time="'+str(user['time'])+'">'+user['email']+'</user>\n'
    file=open(file_path,'w+',encoding='utf-8')
    file.write(text)
    file.close()

#Основная программа
def main():
    file_path_users="C:\\Users\\User\\Desktop\\users.txt"#Ссылка на файл с пользователями
    file_path_articles='C:\\Users\\User\Desktop\\articles.txt'#Ссылка на файл с статьями

    smtp_server='smtp.xxxx.xx'#Адрес smtp сервера почты, с которой отправляются сообщения
    port='465' #Порт smtp сервера почты, с которой отправляются сообщения
    imap_server = "imap.xxxx.xx" #Адрес imap сервера почты, с которой отправляются сообщения и получаются сообщения от пользователя

    send_mail='xxxxxx@xxxx.xxx'#Адрес электронной почты, с которой отправляются сообщения и получаются сообщения от пользователя
    password = 'xxxxxxxxx'#Пароль от электронной почты
    links=[
        {
            'link':'https://habr.com/ru/rss/all/page',#Ссылка на сайт для получения статей
            'categories':[''],#Список категорий для получения статей с определенной категорией
            'method':'get_articles_from_habr'#Название функции для обработки полученных данных с сайта
        },
        {
            'link':'https://vc.ru/new/all/more?',#Ссылка на сайта для получения статей
            'categories':[''],#Список категорий для получения статей с определенной категорией
            'method':'get_articles_from_vcru'#Название функции для обработки полученных данных с сайта
        }
    ]
    users=get_users_from_file(file_path_users)
    for i in range(0,len(users)):
        users[i]['time']=time.perf_counter()
    save_users_in_file(file_path_users,users)
    while True:
        users=get_users_from_file(file_path_users)
        list=get_message_from_email(send_mail,password,imap_server)
        if list:#Проверка на наличие новых сообщений на почте
            for element in list:
                message=''
                commands=define_commands(element)
                for command in commands:
                    message+=run_command(command,users,element['email'])+'\n\n'
                save_users_in_file(file_path_users,users)
                send_message(send_mail,element['email'],smtp_server,port,password,'Выполнение комманд!','plain',message)
                for user in users:
                    if user['email']==element['email']:
                        check=False
                        i=0
                        while not check and i !=100:
                            check=main_prog(send_mail,password,user['email'],links,smtp_server,port,user,file_path_articles)#Запуск основной программы получения новых статей после выполнения комманд от пользователя
                            i+=1
                        if not check:
                            print("Programm cant be running!\n")
                            os._exit(0)
                        break
        for j in range(0,len(users)):
            if time.perf_counter()-users[j]['time']>=7200:#Проверка времени. (Отправка статей каждые два часа)
                check=False
                i=0
                while not check and i !=100:
                    check=main_prog(send_mail,password,users[j]['email'],links,smtp_server,port,users[j],file_path_articles)
                    i+=1
                if not check:
                    print("Programm cant be running!\n")
                    os._exit(0)
                users[j]['time']=time.perf_counter()#Обнуление времени после выполнение поиска новых статей
                save_users_in_file(file_path_users,users)
        
main()