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
from datetime import date
from email.header import decode_header
import base64
from bs4 import BeautifulSoup

def check_date_today(d):
    if d==str(date.today()):
        return True
    else:
        return False

#Получение статей из файла. Каждая статья имеет: заголовок, сслыку, категории, адреса электронной почты, на которые статья была когда-то отправлена
def get_articles_from_file(file_path):
    if not os.path.isfile(file_path):
        return []
    articles_pattern=r'<a href=".*" categories=".*" pubDate=".*" emails=".*">.*<\/a>'
    article_link_pattern=r'href="(.*)" categories'
    article_title_pattern=r'>(.*)<'
    article_categories_pattern=r'categories="(.*)" pubDate'
    article_emails_pattern=r'emails="(.*)">'
    article_pubDate_pattern=r'pubDate="(.*)" emails'
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
        article['pubDate']=re.findall(article_pubDate_pattern,str)[0]
        if not check_date_today(article['pubDate']):
            continue
        categories=re.findall(article_categories_pattern,str)
        if categories!=['']:
            categories=categories[0]
            categories=categories.split(',')
            for i in range(0,len(categories)):
                categories[i]=categories[i].strip()
        else:
            categories=['none']
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
    if not check_date_today(article['pubDate']) or categories==['']:
        return False
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
            string+=article['categories'][i].lower().strip()
            if i<len(article['categories'])-1:
                string+=', '
        string+="\" pubDate=\""+article['pubDate']
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
        links[k]['categories']=user[links[k]['name']+'_categories']
        if links[k]['categories']==['']:
            links[k]['categories']=['none']
    all_articles=get_articles_from_file(file_path)

    new_articles=get_new_articles(links,all_articles,recepient_mail)
   
    if len(new_articles)!=0:                            #Проверка на наличие новых статей
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
        file=open(file_path,'w+',encoding='utf-8')      #Открытие файла для перезаписи
        file.write(tegs)                                #Запись статей в файл
        file.close()
        return True
    else: 
        return True
    
def main_prog_start(send_mail,password,recepient_mail,links,smtp_server,port,user,file_path):
    check=False
    i=0
    while not check and i !=100:
        check=main_prog(send_mail,password,recepient_mail,links,smtp_server,port,user,file_path)#Запуск основной программы получения новых статей после выполнения комманд от пользователя
        i+=1
    if not check:
        print("Programm cant be running!\n")
        os._exit(0)
    return time.perf_counter()

def convert_date(date):
    if len(date.split())>1:
        date=date.split()
    else:
        date=date.split('.')
    number=date[0]
    month=date[1]
    year=date[2]
    match(month):
        case 'Jan':month='01'
        case 'Feb':month='02'
        case 'Mar':month='03'
        case 'Apr':month='04'
        case 'May':month='05'
        case 'Jun':month='06'
        case 'Jul':month='07'
        case 'Aug':month='08'
        case 'Sep':month='09'
        case 'Oct':month='10'
        case 'Nov':month='11'
        case 'Dec':month='12'
    return year+'-'+month+'-'+number

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
        check=False
        for item in items:
            article={}
            article['title']=item.find('title').text
            article['link']=item.find('guid').text
            article['pubDate']=item.find('pubDate').text
            article['pubDate']=re.findall(r'\S*, (.*) \S*:\S*:\S*',article['pubDate'])[0]
            article['pubDate']=convert_date(article['pubDate'])
            if not check_date_today(article['pubDate']):
                check=True
                break
            categories=item.findAll('category')
            article['categories']=[]
            for category in categories:
                article['categories'].append(category.text)
            if check_item(article,old_articles,link['categories']):
                new_articles.append(article)
        if check:
            break
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
        check=False
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
            article['pubDate']=item.find('time',class_='time')['title']
            article['pubDate']=re.findall(r'(\S*) \S* \S*',article['pubDate'])[0]
            article['pubDate']=convert_date(article['pubDate'])
            if not check_date_today(article['pubDate']):
                check=True
                break
            categories=item.find('div',class_='content-header__info')
            article['categories']=[]
            if categories.find('div',class_='content-header-author content-header-author--user content-header__item content-header-author--desktop'):
                article['categories'].append(categories.find('div',class_='content-header-author content-header-author--subsite content-header__item content-header-author--shrink').find('div',class_='content-header-author__name').text.strip())
            if check_item(article,old_articles,link['categories']):
                new_articles.append(article)
        if check:
            break
    return new_articles

#Получение пользователей из файла. Пользователь имеет: адрес электронной почты, категории, статьи с которыми будут ему присылаться, время, для отправки сообщения через определенный промежуток
def get_users_from_file(file_path,links):
    if not os.path.isfile(file_path):
        return []
    users_pattern=r'<user .* time=".*">.*<\/user>'
    categories_pattern=r'<user (.*) time=".*">.*<\/user>'
    email_pattern=r'>(.*)<'
    time_pattern=r'time="(.*)">'
    f=open(file_path, 'r', encoding="utf-8")
    all_str=f.read()
    f.close()
    all_str=re.findall(users_pattern,all_str)
    users=[]
    for str in all_str:
        user={}
        user['email']=re.findall(email_pattern,str)[0]
        categories=re.findall(categories_pattern,str)[0]
        cat=categories
        categories=[]
        counter=0
        category=''
        while cat:
            counter+=1
            category+=cat[:cat.find('"')]+'"'
            cat=cat[cat.find('"')+1:] 
            if counter==2:
                counter=0
                categories.append(category.strip())
                category=''
        for category in categories:
            category_name=re.findall(r'(\S*)=".*"',category)
            category_name=category_name[0]
            category=re.findall(r'\S*="(.*)"',category)
            for link in links:
                if (link['name']+'_categories')==category_name:
                    if category!=['']:
                        category=category[0]
                        category=category.split(',')
                        for i in range(0,len(category)):
                            category[i]=category[i].strip()
                    user[category_name]=category
                    break 
        user['time']=float(re.findall(time_pattern,str)[0])
        users.append(user)
    return users

#Сохранение списка тегов с информацией о пользователях в файл
def save_users_in_file(file_path,users):
    text=''
    for user in users:
        text+='<user '
        for key in user.keys():
            if '_categories' in key:
                text+=key+'="'
                for i in range(0,len(user[key])):
                    text+=user[key][i].lower().strip()
                    if i<len(user[key])-1:
                        text+=', '
                text+='" '
        text+='time="'+str(user['time'])+'">'+user['email']+'</user>\n'
    file=open(file_path,'w+',encoding='utf-8')
    file.write(text)
    file.close()

#Разделение комманд с электронной почты
def define_commands(element):
    commands=[]
    message=""
    command=[]
    for line in element['text']:
        line=line.strip()
        if re.findall(r'<.*@.*\..*>',line)or line.strip()=='--':
            break
        if len(line)!=0 and line[0]=='/' and command!=[]:
            commands.append(command)
            command=[]
        if len(line)!=0 and not line.isspace():
            command.append(line)
    if command!=[]:
        commands.append(command)
    return commands


#Проверка комманд на наличие комманды, правильность ввода, наличие парамметров и выполнение комманд        
def run_command(line,users,email,links):
    command=re.findall(r'\/\S*',line[0])[0].lower()
    message=''
    check_command=False
    match(command):
        case '/help':                           #Возвращение сообщения со всеми существующими коммандами
            check_command=True
            message='Комманды:\n/list - теги, выбранные пользователем!\n/addtag - добавить тег!\nПример:\n/addtag\nhabr.com #DIY\n\n/deletetag - удалить тег!\nПример:\n/deletetag\nhabr.com #DIY\n\n/clear - очистить категории!\nПример:\n/clear all(или habr.com или vc.ru)'
        case '/list':                           #Возвращение сообщения с выбранными пользователем категориями
            check_command=True
            check=False
            for i in range(0,len(users)):
                if users[i]['email']==email:
                    check=True
                    info=''
                    for key in users[i].keys():
                        if '_categories'in key:
                            if users[i][key+'_categories']==['']:
                                info='Отсутствуют!'
                            elif users[i][key+'_categories']==['nocat']:
                                info='Без категорий!'
                            else:
                                info=', '.join(users[i][key+'_categories'])
                            message='Ваши теги '+key[:key.find('_categories')]+': \n'+info
                    break
            if not check:
                message='Вы не имеете подписку!'
        case '/addtag':                         #Добавление категории для отправки пользователю
            check_command=True
            message='Выполнение /addtag:'
            line[0]=re.findall(r'\/\S* (.*)',line[0])
            if line[0]!=[] and line[0]!=['']:
                line[0]=line[0][0]
            else:
                line[0]=''
            if len(line)>1 or line[0]!='':
                check=False
                parametrs=line
                for i in range(0,len(users)):
                    if users[i]['email']==email:
                        check=True
                        break
                if not check:
                    user={
                        'email':email,
                        'time':time.perf_counter()
                    }
                    for link in links:
                        user[link['name']+'_categories']=['']
                    users.append(user)
                for parametr in parametrs:
                    parametr=parametr.split(' ',1)
                    if len(parametr[1])==0:
                        message+='\nНе введено название тега!'
                        continue
                    site=parametr[0].lower()
                    category=parametr[1].strip()
                    category=category.split()
                    if category[0][0]=='<'and category[0][-1]=='>':
                        category.pop(0)
                    category=' '.join(category)
                    check_site_link=False
                    key=''
                    for link in links:
                        site_link=re.findall(r'https?:\/\/(.*)',link['link'])[0]
                        site_link=site_link[:site_link.find('/')].strip()
                        if site==site_link:
                            key=link['name']+'_categories'
                            check_site_link=True
                            break
                    if not check_site_link:
                        message+='\nСайт "'+site+'" не существует!'
                        continue
                    if category[0]!='#':
                        message+='\nНазвание тега вводится через решетку: #название тега! : '+category
                        continue
                    for i in range(0,len(users)):
                        if users[i]['email']==email:
                            if users[i][key]==['']:
                                users[i][key]=[]
                            check_cat=False
                            for k in range(0,len(users[i][key])):
                                if users[i][key][k].strip()==category[1:].lower():
                                    check_cat=True
                            if not check_cat:
                                users[i][key].append(category[1:])
                            users[i]['time']=time.perf_counter()
                            message+='\nТег "'+category[1:]+'" добавлен в теги сайта "'+site+'"!'
                            break
            else:
                message='Не введены парамметры комманды /addtag\nПример:\n/addtag habr.com #DIY!'
        case '/deletetag':                      #Удаление категории. Статья с категорией не будет отправляться пользователю
            check_command=True
            message='Выполнение /deletetag:'
            line[0]=re.findall(r'\/\S* (.*)',line[0])
            if line[0]!=[] and line[0]!=['']:
                line[0]=line[0][0]
            else:
                line[0]=''
            if len(line)>1 or line[0]!='':
                check=False
                parametrs=line
                for i in range(0,len(users)):
                    if users[i]['email']==email:
                        check=True
                        break
                if not check:
                    message+='Отсутствует подписка!'
                else:
                    for parametr in parametrs:
                        parametr=parametr.split(' ',1)
                        if len(parametr[1])==0:
                            message+='\nНе введено название тега!'
                            continue
                        site=parametr[0].lower()
                        category=parametr[1].strip()
                        category=category.split()
                        if category[0][0]=='<'and category[0][-1]=='>':
                            category.pop(0)
                        category=' '.join(category)
                        check_site_link=False
                        key=''
                        for link in links:
                            site_link=re.findall(r'https?:\/\/(.*)',link['link'])[0]
                            site_link=site_link[:site_link.find('/')].strip()
                            if site==site_link:
                                key=link['name']+'_categories'
                                check_site_link=True
                                break
                        if not check_site_link:
                            message+='\nСайт "'+site+'" не существует!'
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
                                message+='\nТег "'+category[1:]+'" удален из тегов сайта "'+site+'"!'
                            break
            else:
                message='Не введены парамметры комманды /deletetag\nПример:\n/deletetag habr.com #DIY!'
        case '/clear':                          #Очистка категорий
            check_command=True
            line[0]=re.findall(r'\/\S* (.*)',line[0])
            if line[0]!=[] and line[0]!=['']:
                line[0]=line[0][0]
                parametrs=line[0].split()
                if parametrs[0][0]=='<'and parametrs[0][-1]=='>':
                    parametrs=parametrs[1]
                else:
                    parametrs=parametrs[0]
                check=False
                for i in range(0,len(users)):
                    if users[i]['email']==email:
                        check=True
                        parametrs=parametrs.lower()
                        if parametrs=='all':
                            for link in links:
                                users[i][link['name']+'_categories']=['']
                            message='Теги всех сайтов очищены!'
                        else:
                            check_site_link=False
                            key=''
                            for link in links:
                                site_link=re.findall(r'https?:\/\/(.*)',link['link'])[0]
                                site_link=site_link[:site_link.find('/')].strip()
                                if parametrs==site_link:
                                    key=link['name']+'_categories'
                                    check_site_link=True
                            if not check_site_link:
                                message='Сайт "'+parametrs+'" отсутствует!'
                                break
                            users[i][key]=[''] 
                            message='Теги сайта "'+parametrs+'" очищены!'
                        users[i]['time']=time.perf_counter()
                        break
                if not check:
                    message='Отсутствует подписка!'
            else: 
                message='Отсутствуют параметры комманды /clear!'
    if not check_command:
        message='Комманда '+command+' не найдена!'
    return message

#Получение сообщений с почты
def get_message_from_email(send_mail,password,imap_server):
    list=[]
    try:
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
    except Exception as exp:
        return []
    return list

#Основная программа
def main():
    file_path_users="C:\\Users\\User\\Desktop\\users.txt"       #Ссылка на файл с пользователями
    file_path_articles='C:\\Users\\User\Desktop\\articles.txt'  #Ссылка на файл с статьями

    smtp_server='smtp.xxx.xxx'                                  #Адрес smtp сервера почты, с которой отправляются сообщения
    port='465'                                                  #Порт smtp сервера почты, с которой отправляются сообщения
    imap_server = "imap.xxx.xxx"                                #Адрес imap сервера почты, с которой отправляются сообщения и получаются сообщения от пользователя

    send_mail='xxxxxx@xxxx.xxx'                                 #Адрес электронной почты, с которой отправляются сообщения и получаются сообщения от пользователя
    password = 'xxxxxxxxx'                                      #Пароль от электронной почты
    links=[
        {
            'name':'habr',
            'link':'https://habr.com/ru/rss/all/page',          #Ссылка на сайт для получения статей
            'categories':[''],                                  #Список категорий для получения статей с определенной категорией
            'method':'get_articles_from_habr'                   #Название функции для обработки полученных данных с сайта
        },
        {   
            'name':'vc',
            'link':'https://vc.ru/new/all/more?',               #Ссылка на сайта для получения статей
            'categories':[''],                                  #Список категорий для получения статей с определенной категорией
            'method':'get_articles_from_vcru'                   #Название функции для обработки полученных данных с сайта
        }
    ]

    users=get_users_from_file(file_path_users,links)
    for i in range(0,len(users)):
        users[i]['time']=main_prog_start(send_mail,password,users[i]['email'],links,smtp_server,port,users[i],file_path_articles)
    save_users_in_file(file_path_users,users)
    while True:
        users=get_users_from_file(file_path_users,links)
        list=get_message_from_email(send_mail,password,imap_server)
        if list:#Проверка на наличие новых сообщений на почте
            for element in list:
                message=''
                commands=define_commands(element)
                for command in commands:
                    message+=run_command(command,users,element['email'],links)+'\n\n'
                save_users_in_file(file_path_users,users)
                check=False
                for i in range(0,100):
                    check=send_message(send_mail,element['email'],smtp_server,port,password,'Выполнение комманд!','plain',message)
                    if check:
                        break
                if not check:
                    print("Send Message Error!\n")
                    return False
                users=get_users_from_file(file_path_users,links)
                for i in range(0,len(users)):
                    if users[i]['email']==element['email']:
                        users[i]['time']=main_prog_start(send_mail,password,users[i]['email'],links,smtp_server,port,users[i],file_path_articles)
                        break
        for j in range(0,len(users)):
            if time.perf_counter()-users[j]['time']>=7200:         #Проверка времени. (Отправка статей каждые два часа)
                users[j]['time']=main_prog_start(send_mail,password,users[j]['email'],links,smtp_server,port,users[j],file_path_articles)
                save_users_in_file(file_path_users,users)
        
main()
