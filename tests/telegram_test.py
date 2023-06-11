from lib.display import send_telegram_alert

def test_telegram_alert():
    send_telegram_alert('Hello World!')

if __name__ == '__main__':
    test_telegram_alert()
