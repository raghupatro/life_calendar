import datetime
import calendar
import argparse
import sys
import os
import math

import cairo


# A1 standard international paper size
DOC_WIDTH = 1683   # 594mm / 23 3/8 inches
DOC_HEIGHT = 2383  # 841mm / 33 1/8 inches

DOC_NAME = "life_calendar.pdf"

KEY_NEWYEAR_DESC = "First week of the new year"
KEY_BIRTHDAY_DESC = "Week of your birthday"

XAXIS_DESC = "Weeks of the year"
YAXIS_DESC = "Years of your life"

FONT = "Libre Baskerville"

MONO_FONT = "Courier Prime"
BIGFONT_SIZE = 40
SMALLFONT_SIZE = 16
TINYFONT_SIZE = 14

MAX_TITLE_SIZE = 30
DEFAULT_TITLE = "LIFE CALENDAR"

Y_MARGIN = 144
BOX_MARGIN = 6

MIN_AGE = 80
MAX_AGE = 100


BOX_LINE_WIDTH = 3
NUM_COLUMNS = 52

BIRTHDAY_COLOUR = (0.5, 0.5, 0.5)
NEWYEAR_COLOUR = (0.8, 0.8, 0.8)
DARKENED_COLOUR_DELTA = (-0.4, -0.4, -0.4)

ARROW_HEAD_LENGTH = 36
ARROW_HEAD_WIDTH = 8

# Color variables
FONT_COLOR = (0x1E / 255.0, 0x03 / 255.0, 0x42 / 255.0)  # Deep purple
BACKGROUND_COLOR = (0xFF / 255.0, 0xFA / 255.0, 0xE6 / 255.0)  # Creamy yellow

BOX_BORDER_COLOR = (0x00 / 255.0, 0x23 / 255.0, 0x79 / 255.0)  # Dark blue
BIRTHDAY_COLOUR = (0xFF / 255.0, 0x5F / 255.0, 0x00 / 255.0)  # Bright orange
NEWYEAR_COLOUR = (0xFF / 255.0, 0x9F / 255.0, 0x66 / 255.0)  # Soft orange
DARKENED_COLOUR_DELTA = (0x0E / 255.0, 0x46 / 255.0, 0xA3 / 255.0)  # Navy Blue
# DARKENED_COLOUR_DELTA = (0x12 / 255.0, 0x14 / 255.0, 0x81 / 255.0)  # Navy Blue

ARROW_HEAD_LENGTH = 36
ARROW_HEAD_WIDTH = 8


def parse_date(date):
    formats = ['%d/%m/%Y', '%d-%m-%Y']

    for f in formats:
        try:
            ret = datetime.datetime.strptime(date.strip(), f)
        except ValueError:
            continue
        else:
            return ret

    raise ValueError("Incorrect date format: must be dd-mm-yyyy or dd/mm/yyyy")


def draw_square(ctx, pos_x, pos_y, box_size, fillcolour=(1, 1, 1)):
    """
    Draws a square at pos_x, pos_y with slightly rounded corners.
    """
    radius = 2  # Small radius for minimal rounding
    ctx.set_line_width(BOX_LINE_WIDTH)
    ctx.set_source_rgb(*BOX_BORDER_COLOR)
    
    # Begin path
    ctx.new_path()
    ctx.arc(pos_x + radius, pos_y + radius, radius, math.pi, 3 * math.pi / 2)
    ctx.arc(pos_x + box_size - radius, pos_y + radius, radius, 3 * math.pi / 2, 0)
    ctx.arc(pos_x + box_size - radius, pos_y + box_size - radius, radius, 0, math.pi / 2)
    ctx.arc(pos_x + radius, pos_y + box_size - radius, radius, math.pi / 2, math.pi)
    
    ctx.close_path()
    ctx.stroke_preserve()
    ctx.set_source_rgb(*fillcolour)
    ctx.fill()



def text_size(ctx, text):
    _, _, width, height, _, _ = ctx.text_extents(text)
    return width, height


def back_up_to_monday(date):
    while date.weekday() != 0:
        date -= datetime.timedelta(days=1)
    return date


def is_future(now, date):
    return now < date


def is_current_week(now, month, day):
    end = now + datetime.timedelta(weeks=1)
    ret = []

    for year in [now.year, now.year + 1]:
        try:
            date = datetime.datetime(year, month, day)
        except ValueError as e:
            if (month == 2) and (day == 29):
                # Handle edge case for birthday being on leap year day
                date = datetime.datetime(year, month, day - 1)
            else:
                raise e

        ret.append(now <= date < end)

    return True in ret


def parse_darken_until_date(date):
    if date == 'today':
        today = datetime.date.today()
        until_date = datetime.datetime(today.year, today.month, today.day)
    else:
        until_date = parse_date(date)

    return back_up_to_monday(until_date)


def get_darkened_fill(fill):
    return tuple(map(sum, zip(fill, DARKENED_COLOUR_DELTA)))


def draw_row(ctx, pos_y, birthdate, date, box_size, x_margin, darken_until_date):
    """
    Draws a row of 52 squares, starting at pos_y
    """

    pos_x = x_margin

    for i in range(NUM_COLUMNS):
        fill = BACKGROUND_COLOR

        if is_current_week(date, birthdate.month, birthdate.day):
            fill = BIRTHDAY_COLOUR
        elif is_current_week(date, 1, 1):
            fill = NEWYEAR_COLOUR

        if darken_until_date and is_future(date, darken_until_date):
            # fill = get_darkened_fill(fill) # helps to get an effect of overlap of two colors
            fill = DARKENED_COLOUR_DELTA

        draw_square(ctx, pos_x, pos_y, box_size, fillcolour=fill)
        pos_x += box_size + BOX_MARGIN
        date += datetime.timedelta(weeks=1)


def draw_key_item(ctx, pos_x, pos_y, desc, box_size, colour):
    draw_square(ctx, pos_x, pos_y, box_size, fillcolour=colour)
    pos_x += box_size + (box_size / 2)

    ctx.set_source_rgb(*FONT_COLOR)
    w, h = text_size(ctx, desc)
    ctx.move_to(pos_x, pos_y + (box_size / 2) + (h / 2))
    ctx.show_text(desc)

    return pos_x + w + (box_size * 2)


def draw_grid(ctx, date, birthdate, age, darken_until_date):
    """
    Draws the whole grid of 52x90 squares
    """
    num_rows = age
    box_size = ((DOC_HEIGHT - (Y_MARGIN + 36)) / num_rows) - BOX_MARGIN
    x_margin = (DOC_WIDTH - ((box_size + BOX_MARGIN) * NUM_COLUMNS)) / 2

    start_date = date
    pos_x = x_margin / 4
    pos_y = pos_x
    
    # Draw the key for box colours
    ctx.set_font_size(TINYFONT_SIZE)
    ctx.set_source_rgb(*FONT_COLOR)
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_NORMAL)

    pos_x = draw_key_item(ctx, pos_x, pos_y, KEY_BIRTHDAY_DESC, box_size, BIRTHDAY_COLOUR)
    draw_key_item(ctx, pos_x, pos_y, KEY_NEWYEAR_DESC, box_size, NEWYEAR_COLOUR)

    # draw week numbers above top row
    ctx.set_font_size(TINYFONT_SIZE)
    ctx.set_source_rgb(*FONT_COLOR)
    ctx.select_font_face(MONO_FONT, cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_NORMAL)

    pos_x = x_margin
    pos_y = Y_MARGIN
    for i in range(NUM_COLUMNS):
        ctx.set_source_rgb(*FONT_COLOR)
        text = f"{i + 1:02}"
        w, h = text_size(ctx, text)
        ctx.move_to(pos_x + (box_size / 2) - (w / 2), pos_y - box_size)
        ctx.show_text(text)
        pos_x += box_size + BOX_MARGIN

    ctx.set_font_size(TINYFONT_SIZE)
    ctx.select_font_face(MONO_FONT, cairo.FONT_SLANT_ITALIC,
        cairo.FONT_WEIGHT_NORMAL)

    for i in range(num_rows):
        # Generate string for current date
        ctx.set_source_rgb(*FONT_COLOR)
        date_str = date.strftime('%d %b, %Y')
        w, h = text_size(ctx, date_str)

        # Draw it in front of the current row
        ctx.move_to(x_margin - w - box_size,
            pos_y + ((box_size / 2) + (h / 2)))
        ctx.show_text(date_str)

        # Draw the current row
        draw_row(ctx, pos_y, birthdate, date, box_size, x_margin, darken_until_date)

        # Increment y position and current date by 1 row/year
        pos_y += box_size + BOX_MARGIN
        date += datetime.timedelta(weeks=52)

    return x_margin

def gen_calendar(birthdate, title, age, filename, darken_until_date, sidebar_text=None,
                 subtitle_text=None):
    if len(title) > MAX_TITLE_SIZE:
        raise ValueError("Title can't be longer than %d characters"
            % MAX_TITLE_SIZE)

    age = int(age)
    if (age < MIN_AGE) or (age > MAX_AGE):
        raise ValueError("Invalid age, must be between %d and %d" % (MIN_AGE, MAX_AGE))

    # Fill background with BACKGROUND_COLOR
    surface = cairo.PDFSurface (filename, DOC_WIDTH, DOC_HEIGHT)
    ctx = cairo.Context(surface)

    ctx.set_source_rgb(*BACKGROUND_COLOR)
    ctx.rectangle(0, 0, DOC_WIDTH, DOC_HEIGHT)
    ctx.fill()

    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD)
    ctx.set_source_rgb(*FONT_COLOR)
    ctx.set_font_size(BIGFONT_SIZE)
    w, h = text_size(ctx, title)
    ctx.move_to((DOC_WIDTH / 2) - (w / 2), (Y_MARGIN / 2) - (h / 2))
    ctx.show_text(title)

    if subtitle_text is not None:
        ctx.set_source_rgb(0.7, 0.7, 0.7)
        ctx.set_font_size(SMALLFONT_SIZE)
        w, h = text_size(ctx, subtitle_text)
        ctx.move_to((DOC_WIDTH / 2) - (w / 2), (Y_MARGIN / 2) - (h / 2) + 15)
        ctx.show_text(subtitle_text)

    date = back_up_to_monday(birthdate)

    # Draw 52x90 grid of squares
    x_margin = draw_grid(ctx, date, birthdate, age, darken_until_date)

    if sidebar_text is not None:
        # Draw text on sidebar
        w, h = text_size(ctx, sidebar_text)
        ctx.move_to((DOC_WIDTH - x_margin) + 20, Y_MARGIN + w + 100)
        ctx.set_font_size(SMALLFONT_SIZE)
        ctx.set_source_rgb(0.7, 0.7, 0.7)
        ctx.rotate(-90 * math.pi / 180)
        ctx.show_text(sidebar_text)

    ctx.show_page()


def main():
    parser = argparse.ArgumentParser(description='\nGenerate a personalized "Life '
                                     ' Calendar", inspired by the calendar with the same name from the '
                                     'waitbutwhy.com store')

    parser.add_argument(type=parse_date, dest='date', help='starting date; your birthday,'
                        'in either yyyy/mm/dd or dd/mm/yyyy format (dashes \'-\' may also be used in '
                        'place of slashes \'/\')')

    parser.add_argument('-f', '--filename', type=str, dest='filename',
                        help='output filename', default=DOC_NAME)

    parser.add_argument('-t', '--title', type=str, dest='title',
                        help='Calendar title text (default is "%s")' % DEFAULT_TITLE,
                        default=DEFAULT_TITLE)

    parser.add_argument('-s', '--sidebar-text', type=str, dest='sidebar_text',
                        help='Text to show along the right side of grid (default is no sidebar text)',
                        default=None)

    parser.add_argument('-b', '--subtitle-text', type=str, dest='subtitle_text',
                        help='Text to show under the calendar title (default is no subtitle text)',
                        default=None)

    parser.add_argument('-a', '--age', type=int, dest='age', choices=range(MIN_AGE, MAX_AGE + 1),
                        metavar='[%s-%s]' % (MIN_AGE, MAX_AGE),
                        help=('Number of rows to generate, representing years of life'),
                        default=90)

    parser.add_argument('-d', '--darken-until', type=parse_darken_until_date, dest='darken_until_date',
                         nargs='?', const='today', help='Darken until date. '
                        '(defaults to today if argument is not given)')

    args = parser.parse_args()
    doc_name = '%s.pdf' % (os.path.splitext(args.filename)[0])

    try:
        gen_calendar(args.date, args.title, args.age, doc_name, args.darken_until_date,
                     sidebar_text=args.sidebar_text, subtitle_text=args.subtitle_text)
    except Exception as e:
        print("Error: %s" % e)
        return

    print('Created %s' % doc_name)

if __name__ == "__main__":
    main()