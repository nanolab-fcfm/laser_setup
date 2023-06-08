from lib.display import send_telegram_alert
from Scripts.IVg import IVg

def test_telegram_alert():
    send_telegram_alert('Benja', procedure=IVg)

if __name__ == '__main__':
    test_telegram_alert()
