from googleapiclient.discovery import build
from datetime import datetime, timedelta

class CalendarAPI:
    """Google Calendar API との通信を担当するクラス"""

    def __init__(self, creds):
        self.service = build('calendar', 'v3', credentials=creds)

    def get_calendar_list(self):
        """利用可能なカレンダーの一覧を取得"""
        calendar_list = self.service.calendarList().list().execute()
        return calendar_list.get('items', [])

    def get_events(self, calendar_ids=['primary'], time_min=None, time_max=None):
        """指定した期間の予定を複数のカレンダーから取得"""
        if not time_min:
            time_min = datetime.utcnow().isoformat() + 'Z'
        
        all_events = []
        for cal_id in calendar_ids:
            try:
                events_result = self.service.events().list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                items = events_result.get('items', [])
                
                # どのカレンダーの予定かを識別できるようにプロパティを追加
                for item in items:
                    item['calendarId'] = cal_id
                all_events.extend(items)
            except Exception as e:
                # 権限がないカレンダーなどはスキップ
                print(f"Failed to fetch {cal_id}: {e}")
                
        # 取得した全予定を開始時間でソート
        def get_start_time(ev):
            start = ev['start'].get('dateTime', ev['start'].get('date'))
            return start
            
        return sorted(all_events, key=get_start_time)

    def create_event(self, calendar_id, summary, start_time, end_time, description=None, is_all_day=False, time_zone='Asia/Tokyo'):
        """新しい予定を作成"""
        event = {
            'summary': summary,
            'description': description or '',
        }
        
        if is_all_day:
            event['start'] = {'date': start_time.strftime('%Y-%m-%d')}
            event['end'] = {'date': end_time.strftime('%Y-%m-%d')}
        else:
            event['start'] = {
                'dateTime': start_time.isoformat(),
                'timeZone': time_zone,
            }
            event['end'] = {
                'dateTime': end_time.isoformat(),
                'timeZone': time_zone,
            }

        return self.service.events().insert(calendarId=calendar_id, body=event).execute()

    def update_event(self, calendar_id, event_id, **kwargs):
        """既存の予定を更新"""
        event = self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        # タイムゾーン等の入れ子構造を安全に更新するための特別処理
        if 'start' in kwargs:
            event['start'] = kwargs['start']
        if 'end' in kwargs:
            event['end'] = kwargs['end']
        
        for key, value in kwargs.items():
            if key not in ('start', 'end'):
                event[key] = value
                
        return self.service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()

    def delete_event(self, calendar_id, event_id):
        """予定を削除"""
        return self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
