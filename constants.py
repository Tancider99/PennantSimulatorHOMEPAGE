# -*- coding: utf-8 -*-
"""
定数定義ファイル
"""

# 画面設定（デフォルト値）
DEFAULT_SCREEN_WIDTH = 1600
DEFAULT_SCREEN_HEIGHT = 1000

# 実際の画面サイズ（動的に変更可能）
SCREEN_WIDTH = DEFAULT_SCREEN_WIDTH
SCREEN_HEIGHT = DEFAULT_SCREEN_HEIGHT

# 画面サイズオプション
SCREEN_RESOLUTIONS = [
    (1280, 720, "HD"),
    (1600, 900, "HD+"),
    (1600, 1000, "標準"),
    (1920, 1080, "Full HD"),
    (2560, 1440, "QHD")
]

def set_screen_size(width: int, height: int):
    """画面サイズを動的に変更"""
    global SCREEN_WIDTH, SCREEN_HEIGHT
    SCREEN_WIDTH = width
    SCREEN_HEIGHT = height

def get_screen_size():
    """現在の画面サイズを取得"""
    return (SCREEN_WIDTH, SCREEN_HEIGHT)

# カラー定義
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_GRAY = (30, 30, 35)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
BLUE = (70, 130, 220)
DARK_BLUE = (30, 60, 140)
GREEN = (50, 200, 100)
DARK_GREEN = (30, 120, 60)
RED = (220, 80, 80)
DARK_RED = (140, 30, 30)
GOLD = (255, 215, 0)
ORANGE = (255, 150, 50)
PURPLE = (160, 100, 200)
CYAN = (100, 200, 220)
NAVY = (20, 30, 50)
DARK_NAVY = (10, 15, 25)

# 外国人選手名
FOREIGN_SURNAMES = [
    "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin",
    "Thompson", "Garcia", "Martinez", "Rodriguez", "Lee", "Walker", "Hall", "Allen",
    "Young", "King", "Wright", "Lopez", "Hill", "Scott", "Green", "Adams", "Baker",
    "Gonzalez", "Nelson", "Carter", "Mitchell", "Perez", "Roberts", "Turner", "Phillips",
    "Campbell", "Parker", "Evans", "Edwards", "Collins", "Stewart", "Sanchez", "Morris"
]

FOREIGN_FIRSTNAMES = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
    "Thomas", "Charles", "Daniel", "Matthew", "Anthony", "Donald", "Mark", "Paul",
    "Steven", "Andrew", "Kenneth", "Joshua", "Kevin", "Brian", "George", "Edward",
    "Ronald", "Timothy", "Jason", "Jeffrey", "Ryan", "Jacob", "Nicholas", "Eric",
    "Tyler", "Austin", "Brandon", "Justin", "Aaron", "Adam", "Nathan", "Zachary",
    "Dylan", "Christian", "Kyle", "Jose", "Juan", "Carlos", "Luis", "Miguel"
]

# 日本人選手名（架空）
JAPANESE_SURNAMES = [
    "青山", "赤井", "秋元", "浅野", "天野", "荒木", "有馬", "安藤", "飯田", "池上",
    "石橋", "磯野", "市川", "岩崎", "上田", "内山", "榎本", "遠藤", "大石", "大川",
    "大野", "岡崎", "奥田", "小野寺", "海老原", "江藤", "太田", "小笠原", "尾崎", "葛西",
    "片桐", "金子", "神山", "川上", "菊池", "北村", "木下", "国分", "熊谷", "倉田",
    "黒田", "桑原", "小池", "河野", "越智", "小松", "坂井", "桜井", "佐久間", "笹本",
    "篠原", "柴田", "島田", "白石", "杉山", "関根", "瀬戸", "高木", "滝沢", "竹内"
]

JAPANESE_FIRSTNAMES = [
    "翔太", "大輝", "健太", "拓海", "颯太", "悠斗", "蓮", "陽翔", "大和", "翼",
    "海斗", "樹", "蒼", "湊", "陸", "駿", "匠", "凌", "航", "颯",
    "悠", "隼人", "優", "誠", "健", "翔", "大樹", "智也", "勇気", "拓也",
    "陽太", "勇人", "亮太", "将太", "龍馬", "雄大", "慎太郎", "圭介", "修平", "康平"
]
