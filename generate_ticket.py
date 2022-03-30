from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from pony.orm import desc

from models import Registration, db_session

TEMPLATE_PATH = 'files/ticket_base.png'
IMAGE_PATH = 'files/aviaticket_example.png'

SECTION_FONT_PATH = 'files/Verdanab.ttf'
SECTION_FONT_SIZE = 14
DATA_FONT_PATH = 'files/Verdana.ttf'
DATA_FONT_SIZE = 14

BLACK = (0, 0, 0, 255)
SECTION_OFFSETS = ((35, 100), (35, 160), (35, 240), (35, 300), (300, 100))
DATA_OFFSETS = ((35, 120), (35, 180), (35, 260), (35, 320), (300, 120))

SECTIONS_TO_DRAW = (
    'Имя пассажира:',
    'Рейс:',
    'Количество мест:',
    'Телефон для подтверждения:',
    'Перевозчик:'
)


async def draw_ticket(user_id):

    # Отрисовка билета по данным из БД
    with db_session:
        sql_data = Registration.select(
            lambda registration: registration.user_id == user_id
        ).order_by(desc(Registration.id))[:1]
        ticket_data = (sql_data[0].username, sql_data[0].chosen_flight,
                       sql_data[0].sits, sql_data[0].phone_number, 'SKILLBOX-AIRLINES')

    img = Image.open(TEMPLATE_PATH).convert('RGBA')
    section_font = ImageFont.truetype(SECTION_FONT_PATH, SECTION_FONT_SIZE)
    data_font = ImageFont.truetype(DATA_FONT_PATH, DATA_FONT_SIZE)
    draw = ImageDraw.Draw(img)

    for offset, text in zip(SECTION_OFFSETS, SECTIONS_TO_DRAW):
        draw.text(xy=offset, text=text, fill=BLACK, font=section_font)

    for offset, text in zip(DATA_OFFSETS, ticket_data):
        draw.text(xy=offset, text=str(text), fill=BLACK, font=data_font)

    temp_file = BytesIO()
    img.save(temp_file, 'png')
    temp_file.seek(0)
    return temp_file
