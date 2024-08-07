import os
from datetime import datetime, timedelta

import pytz
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from icalendar import Calendar, Event, Alarm
from lunarcalendar import Converter, Lunar

# 加载环境变量
load_dotenv()

# 定义 OAuth2.0 范围
SCOPES = ['https://www.googleapis.com/auth/contacts.readonly']


def get_credentials():
    """
    获取 Google API 凭据
    """
    creds = None
    token_info = {
        'refresh_token': os.getenv('GOOGLE_REFRESH_TOKEN'),
        'token': os.getenv('GOOGLE_API_TOKEN'),
        'token_uri': os.getenv('GOOGLE_TOKEN_URI'),
        'client_id': os.getenv('GOOGLE_CLIENT_ID'),
        'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
        'scopes': SCOPES
    }
    creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
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
        if os.getenv('SAVE_TOKEN', 'true').lower() in ['true', '1', 'yes']:
            with open('../token.json', 'w') as token:
                token.write(creds.to_json())
    return creds


def has_birthday_or_event(contact):
    """
    检查联系人是否有生日或事件
    """
    return ('birthdays' in contact and contact['birthdays']) or ('events' in contact and contact['events'])


def get_connections(service):
    """
    获取联系人信息
    """
    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=1000,
        personFields='names,birthdays,events'
    ).execute()
    return [conn for conn in results.get('connections', []) if has_birthday_or_event(conn)]


def add_gregorian_birthday_event(name, birth_date, year, calendar, timezone, birth_year):
    """
    添加公历生日事件到日历
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

    localized_date = timezone.localize(datetime(year, birth_date.month, birth_date.day))
    event.add('dtstart', localized_date)
    event.add('dtend', localized_date + timedelta(days=1))
    event.add('dtstamp', timezone.localize(datetime.now()))
    event['uid'] = f'{name}-{year}-{birth_date.month:02d}-{birth_date.day:02d}@finn'

    reminder_time = datetime(year, birth_date.month, birth_date.day, 9, 0, 0)
    localized_reminder_time = timezone.localize(reminder_time)
    reminder_delta = localized_date - localized_reminder_time

    alarm = Alarm()
    alarm.add('action', 'DISPLAY')
    alarm.add('description', 'Reminder')
    alarm.add('trigger', reminder_delta)
    event.add_component(alarm)

    calendar.add_component(event)


def add_lunar_birthday_event(name, lunar_date, year, calendar, timezone, birth_year):
    """
    添加农历生日事件到日历
    """
    event = Event()
    lunar_year = lunar_date.get('year', birth_year)
    age = year - lunar_year if lunar_year else None
    lunar = Lunar(year, lunar_date['month'], lunar_date['day'])
    solar = Converter.Lunar2Solar(lunar)
    solar_date = datetime(solar.year, solar.month, solar.day)

    if lunar_year:
        summary = f'{name}的{age}岁农历生日🎂'
        description = f'今天是{name}的{age}岁农历生日！'
    else:
        summary = f'{name}的农历生日🎂'
        description = f'今天是{name}的农历生日！'

    event.add('summary', summary)
    event.add('description', description)

    localized_date = timezone.localize(solar_date)
    event.add('dtstart', localized_date)
    event.add('dtend', localized_date + timedelta(days=1))
    event.add('dtstamp', timezone.localize(datetime.now()))
    event['uid'] = f'{name}-{year}-{solar_date.month:02d}-{solar_date.day:02d}@finn'

    reminder_time = datetime(year, solar_date.month, solar_date.day, 9, 0, 0)
    localized_reminder_time = timezone.localize(reminder_time)
    reminder_delta = localized_date - localized_reminder_time

    alarm = Alarm()
    alarm.add('action', 'DISPLAY')
    alarm.add('description', 'Reminder')
    alarm.add('trigger', reminder_delta)
    event.add_component(alarm)

    calendar.add_component(event)


def add_anniversary_event(name, event_date, year, calendar, timezone, anniversary_year):
    """
    添加周年纪念日事件到日历
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

    localized_date = timezone.localize(anniv_date)
    event.add('dtstart', localized_date)
    event.add('dtend', localized_date + timedelta(days=1))
    event.add('dtstamp', timezone.localize(datetime.now()))
    event['uid'] = f'{cleaned_name}-{year}-{event_date["month"]:02d}-{event_date["day"]:02d}@finn'

    reminder_time = datetime(year, event_date['month'], event_date['day'], 9, 0, 0)
    localized_reminder_time = timezone.localize(reminder_time)
    reminder_delta = localized_date - localized_reminder_time

    alarm = Alarm()
    alarm.add('action', 'DISPLAY')
    alarm.add('description', 'Reminder')
    alarm.add('trigger', reminder_delta)
    event.add_component(alarm)

    calendar.add_component(event)


def create_calendar(data, current_year, years_to_create, timezone):
    """
    创建包含生日和事件的日历
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
                add_gregorian_birthday_event(name, birth_date, year, cal, timezone, birth_year)

        if 'events' in person:
            for event in person['events']:
                event_description = event.get('type', '').lower()
                if '农历生日' in event_description:
                    lunar_date = event['date']
                    for year in range(current_year, current_year + years_to_create):
                        add_lunar_birthday_event(name, lunar_date, year, cal, timezone, birth_year)
                elif '周年纪念日' in event_description:
                    event_name = event_description.split('#')[0]
                    event_date = event['date']
                    anniversary_year = event_date.get('year')
                    for year in range(current_year, current_year + years_to_create):
                        add_anniversary_event(event_name, event_date, year, cal, timezone, anniversary_year)

    return cal


def save_calendar(calendar, file_path):
    """
    保存日历到 ICS 文件
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

    # 创建日历
    current_year = datetime.now().year
    years_to_create = 5
    timezone = pytz.timezone('Asia/Shanghai')
    calendar = create_calendar(connections, current_year, years_to_create, timezone)

    # 保存日历到 ICS 文件
    save_calendar(calendar, '../birthdays.ics')

    print('')


if __name__ == '__main__':
    main()
