import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from icalendar import Calendar, Event
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
        "refresh_token": os.getenv('GOOGLE_REFRESH_TOKEN'),
        "token": os.getenv('GOOGLE_API_TOKEN'),
        "token_uri": os.getenv('GOOGLE_TOKEN_URI'),
        "client_id": os.getenv('GOOGLE_CLIENT_ID'),
        "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
        "scopes": SCOPES
    }
    creds = Credentials.from_authorized_user_info(token_info, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config({
                "web": {
                    "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                    "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                    "auth_uri": os.getenv('GOOGLE_AUTH_URI'),
                    "token_uri": os.getenv('GOOGLE_TOKEN_URI'),
                    "auth_provider_x509_cert_url": os.getenv('GOOGLE_AUTH_PROVIDER_X509_CERT_URL')
                }
            }, SCOPES)
            creds = flow.run_local_server(port=8080)
        if os.getenv('SAVE_TOKEN', 'true').lower() in ['true', '1', 'yes']:
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    return creds

def has_birthday(contact):
    """
    检查联系人是否有生日
    """
    return 'birthdays' in contact or any(
        'birthday' in event.get('type', '').lower() for event in contact.get('events', [])
    )

def get_connections(service):
    """
    获取联系人信息
    """
    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=1000,
        personFields='names,birthdays,events'
    ).execute()
    return [conn for conn in results.get('connections', []) if has_birthday(conn)]

def add_event(name, date, year, calendar, timezone, is_lunar=False, birth_year=None):
    """
    添加事件到日历
    """
    event = Event()
    age = year - birth_year if birth_year else None
    if birth_year:
        summary = f"{name}的{'农历' if is_lunar else ''}{age}岁生日🎂"
        description = f"今天是{name}的{'农历' if is_lunar else ''}{age}岁生日！"
    else:
        summary = f"{name}的{'农历' if is_lunar else ''}生日🎂"
        description = f"今天是{name}的{'农历' if is_lunar else ''}生日！"

    event.add('summary', summary)
    event.add('description', description)

    localized_date = timezone.localize(datetime(year, date.month, date.day))
    event.add('dtstart', localized_date)
    event.add('dtend', localized_date + timedelta(days=1))
    event.add('dtstamp', timezone.localize(datetime.now()))
    event['uid'] = f'{name}-{year}-{date.month:02d}-{date.day:02d}@finn'
    calendar.add_component(event)

def create_calendar(data, current_year, years_to_create, timezone):
    """
    创建包含生日事件的日历
    """
    cal = Calendar()
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
                add_event(name, birth_date, year, cal, timezone, birth_year=birth_year)

        if 'events' in person:
            lunar_date = person['events'][0]['date']
            for year in range(current_year, current_year + years_to_create):
                lunar = Lunar(year, lunar_date['month'], lunar_date['day'])
                solar = Converter.Lunar2Solar(lunar)
                solar_date = datetime(solar.year, solar.month, solar.day)
                add_event(name, solar_date, year, cal, timezone, is_lunar=True, birth_year=birth_year)

    return cal

def save_calendar(calendar, file_path):
    """
    保存日历到 ICS 文件
    """
    with open(file_path, 'wb') as f:
        f.write(calendar.to_ical())

def main():
    """
    主函数，获取并保存联系人生日
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
    save_calendar(calendar, 'birthdays.ics')

if __name__ == '__main__':
    main()
