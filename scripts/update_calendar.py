import os
from datetime import datetime, timedelta

import pytz
from dotenv import load_dotenv, set_key
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from icalendar import Alarm, Calendar, Event
from lunarcalendar import Converter, DateNotExist, Lunar

# 加载环境变量
load_dotenv()

# 定义 OAuth2.0 范围，只读访问联系人
SCOPES = ['https://www.googleapis.com/auth/contacts.readonly']


def save_to_env(key, value):
    """
    保存数据到 .env 文件中
    :param key: 环境变量的名称
    :param value: 要保存的值
    """
    env_file = os.getenv('ENV_PATH', '.env')
    set_key(env_file, key, value)


def get_credentials():
    """
    获取 Google API 凭据
    :return: 凭据对象，用于后续 API 调用
    """
    creds = None
    refresh_token = os.getenv('GOOGLE_REFRESH_TOKEN')

    if refresh_token:
        # 使用现有的刷新令牌来获取凭据
        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri=os.getenv('GOOGLE_TOKEN_URI'),
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
            scopes=SCOPES
        )

        # 刷新访问令牌
        creds.refresh(Request())

    if not refresh_token or not creds or not creds.valid:
        # 如果没有刷新令牌或者凭据无效，需要用户授权
        flow = InstalledAppFlow.from_client_config({
            'web': {
                'client_id': os.getenv('GOOGLE_CLIENT_ID'),
                'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
                'auth_uri': os.getenv('GOOGLE_AUTH_URI'),
                'token_uri': os.getenv('GOOGLE_TOKEN_URI'),
                'auth_provider_x509_cert_url': os.getenv('GOOGLE_AUTH_PROVIDER_X509_CERT_URL')
            }
        }, SCOPES)

        creds = flow.run_local_server(port=8080)

        # 保存刷新令牌到 .env 文件
        save_to_env('GOOGLE_REFRESH_TOKEN', creds.refresh_token)

    return creds


def has_birthday_or_event(contact):
    """
    检查联系人是否有生日或事件
    :param contact: 联系人信息字典
    :return: 如果联系人有生日或事件，返回 True，否则返回 False
    """
    return ('birthdays' in contact and contact['birthdays']) or ('events' in contact and contact['events'])


def get_connections(service):
    """
    获取联系人信息
    :param service: Google API 服务对象
    :return: 包含生日或事件的联系人列表
    """
    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=1000,
        personFields='names,birthdays,events'
    ).execute()
    return [conn for conn in results.get('connections', []) if has_birthday_or_event(conn)]


def add_gregorian_birthday_event(name, birth_date, year, calendar, birth_year):
    """
    添加公历生日事件到日历
    :param name: 联系人名称
    :param birth_date: 出生日期（datetime 对象）
    :param year: 要添加事件的年份
    :param calendar: 日历对象
    :param birth_year: 出生年份
    """
    event = Event()
    age = year - birth_year if birth_year else None
    if birth_year:
        summary = f'{name}的{age}岁生日🎂'
        description = f'今天是{name}的{age}岁生日！'
    else:
        summary = f'{name}的生日🎂'
        description = f'今天是{name}的生日！'

    event.add('summary', summary)
    event.add('description', description)

    # 设置事件为全天事件，不指定时区
    event.add('dtstart', datetime(year, birth_date.month, birth_date.day).date())
    event.add('dtend', (datetime(year, birth_date.month, birth_date.day) + timedelta(days=1)).date())
    event.add('dtstamp', datetime.now())

    event['uid'] = f'{name}-{year}-{birth_date.month:02d}-{birth_date.day:02d}@finn'

    # 添加提醒时间为当天上午9:00
    alarm = Alarm()
    alarm.add('action', 'DISPLAY')
    alarm.add('description', 'Reminder')
    alarm.add('trigger', timedelta(hours=+9))
    event.add_component(alarm)

    # 将事件添加到日历中
    calendar.add_component(event)


def add_lunar_birthday_event(name, lunar_date, year, calendar, birth_year):
    """
    添加农历生日事件到日历
    :param name: 联系人名称
    :param lunar_date: 农历日期字典，包含年份、月份、日期
    :param year: 要添加事件的年份
    :param calendar: 日历对象
    :param birth_year: 出生年份
    """
    event = Event()
    lunar_year = lunar_date.get('year', birth_year)
    age = year - lunar_year if lunar_year else None

    # 检查并处理农历日期是否有效
    valid_lunar_date = False
    while not valid_lunar_date:
        try:
            lunar = Lunar(year, lunar_date['month'], lunar_date['day'])
            solar = Converter.Lunar2Solar(lunar)
            valid_lunar_date = True
        except DateNotExist:
            # 如果日期不存在，将农历日期提前一天
            lunar_date['day'] -= 1
            if lunar_date['day'] < 1:
                raise ValueError(f"Lunar date adjustment failed for {name}. Please check the data.")

    solar_date = datetime(solar.year, solar.month, solar.day)

    if lunar_year:
        summary = f'{name}的{age}岁农历生日🎂'
        description = f'今天是{name}的{age}岁农历生日！'
    else:
        summary = f'{name}的农历生日🎂'
        description = f'今天是{name}的农历生日！'

    event.add('summary', summary)
    event.add('description', description)

    # 设置事件为全天事件，不指定时区
    event.add('dtstart', solar_date.date())
    event.add('dtend', (solar_date + timedelta(days=1)).date())
    event.add('dtstamp', datetime.now())

    event['uid'] = f'{name}-{year}-{solar_date.month:02d}-{solar_date.day:02d}@finn'

    # 添加提醒时间为当天上午9:00
    alarm = Alarm()
    alarm.add('action', 'DISPLAY')
    alarm.add('description', 'Reminder')
    alarm.add('trigger', timedelta(hours=+9))
    event.add_component(alarm)

    # 将事件添加到日历中
    calendar.add_component(event)


def add_anniversary_event(name, event_date, year, calendar, anniversary_year):
    """
    添加周年纪念日事件到日历
    :param name: 事件名称
    :param event_date: 事件日期（字典，包含月份、日期）
    :param year: 要添加事件的年份
    :param calendar: 日历对象
    :param anniversary_year: 纪念开始年份
    """
    event = Event()
    age = year - anniversary_year if anniversary_year else None
    anniv_date = datetime(year, event_date['month'], event_date['day'])

    cleaned_name = name.strip()

    if anniversary_year:
        summary = f'{cleaned_name}{age}周年纪念日'
        description = f'今天是{cleaned_name}{age}周年纪念日！'
    else:
        summary = f'{cleaned_name}周年纪念日'
        description = f'今天是{cleaned_name}周年纪念日！'

    event.add('summary', summary)
    event.add('description', description)

    # 设置事件为全天事件，不指定时区
    event.add('dtstart', anniv_date.date())
    event.add('dtend', (anniv_date + timedelta(days=1)).date())
    event.add('dtstamp', datetime.now())

    event['uid'] = f'{cleaned_name}-{year}-{event_date["month"]:02d}-{event_date["day"]:02d}@finn'

    # 添加提醒时间为当天上午9:00
    alarm = Alarm()
    alarm.add('action', 'DISPLAY')
    alarm.add('description', 'Reminder')
    alarm.add('trigger', timedelta(hours=+9))
    event.add_component(alarm)

    # 将事件添加到日历中
    calendar.add_component(event)


def create_calendar(data, current_year, years_to_create, timezone):
    """
    创建包含生日和事件的日历
    :param data: 联系人数据列表
    :param current_year: 当前年份
    :param years_to_create: 要生成的年份数量
    :param timezone: 时区对象
    :return: 日历对象，包含所有生日和事件
    """
    cal = Calendar()
    cal.add('prodid', '-//Google Inc//Google Calendar 70.9054//EN')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', '生日快乐')

    for person in data:
        name = person['names'][0]['displayName']
        birth_year = None

        if 'birthdays' in person:
            birthday_info = person['birthdays'][0]['date']
            birth_date = datetime(
                birthday_info['year'] if 'year' in birthday_info else current_year,
                birthday_info['month'],
                birthday_info['day']
            )
            birth_year = birthday_info.get('year')
            for year in range(current_year, current_year + years_to_create):
                add_gregorian_birthday_event(name, birth_date, year, cal, birth_year)

        if 'events' in person:
            for event in person['events']:
                event_description = event.get('type', '').lower()
                if '农历生日' in event_description:
                    lunar_date = event['date']
                    for year in range(current_year, current_year + years_to_create):
                        add_lunar_birthday_event(name, lunar_date, year, cal, birth_year)
                elif '周年纪念日' in event_description:
                    event_name = event_description.split('#')[0]
                    event_date = event['date']
                    anniversary_year = event_date.get('year')
                    for year in range(current_year, current_year + years_to_create):
                        add_anniversary_event(event_name, event_date, year, cal, anniversary_year)

    return cal


def save_calendar(calendar, file_path):
    """
    保存日历到 ICS 文件
    :param calendar: 日历对象
    :param file_path: 要保存的文件路径
    """
    with open(file_path, 'wb') as f:
        f.write(calendar.to_ical())


def main():
    """
    主函数，获取并保存联系人生日和事件
    """
    creds = get_credentials()
    service = build('people', 'v1', credentials=creds)
    connections = get_connections(service)

    current_year = datetime.now().year
    years_to_create = 5
    timezone = pytz.timezone('Asia/Shanghai')
    calendar = create_calendar(connections, current_year, years_to_create, timezone)

    save_calendar(calendar, './birthdays.ics')

    print('日历文件已保存至 ./birthdays.ics')


if __name__ == '__main__':
    main()
