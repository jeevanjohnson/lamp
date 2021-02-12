from datetime import datetime

base = '\u001b[{}m'

class Style:
    Reset = 0
    Black = 30
    Red = 31
    Green = 32
    Yellow = 33
    Blue = 34
    Magenta = 35
    Cyan = 36
    White = 37

def log(msg: str, color: Style = Style.White) -> None:
    print(f'{base.format(color)}{datetime.now():%H:%M:%S}: {msg}{base.format(Style.White)}')