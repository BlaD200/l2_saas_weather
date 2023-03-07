import asyncio
import platform
import re
from datetime import datetime, timedelta
from time import time
from typing import Iterator

import aiofiles
import aiohttp
import unicodedata
from bs4 import BeautifulSoup, Tag
from fake_useragent import UserAgent


month_date_format = '%B-%#d'
month_article_date_format = '%B %#d'
simple_date_format = '%Y-%m-%d'
year_date_format = f"{month_date_format}-%Y"


def compose_link_for_date(parse_date: datetime) -> str:
    # 24 - initial
    # 25 - https://understandingwar.org/backgrounder/russia-ukraine-warning-update-russian-offensive-campaign-assessment-february-25-2022
    # 26 - https://understandingwar.org/backgrounder/russia-ukraine-warning-update-russian-offensive-campaign-assessment-february-26
    # 27 - https://understandingwar.org/backgrounder/russia-ukraine-warning-update-russian-offensive-campaign-assessment-february-27
    # 28 - https://understandingwar.org/backgrounder/russian-offensive-campaign-assessment-february-28-2022
    base_initial_february_url = \
        'https://understandingwar.org/backgrounder/' \
        'russia-ukraine-warning-update-russian-offensive-campaign-assessment'
    base_url = \
        'https://www.understandingwar.org/backgrounder/' \
        'russian-offensive-campaign-assessment'

    if parse_date == datetime.strptime('2022-02-25', simple_date_format):
        date = parse_date.strftime(year_date_format).lower()
        url = f"{base_initial_february_url}-{date}"
    elif parse_date <= datetime.strptime('2022-02-27', simple_date_format):
        date = parse_date.strftime(month_date_format).lower()
        url = f"{base_initial_february_url}-{date}"
    elif parse_date == datetime.strptime('2022-02-28', simple_date_format):
        date = parse_date.strftime(year_date_format).lower()
        url = f"{base_url}-{date}"
    elif parse_date.year == 2022:
        date = parse_date.strftime(month_date_format).lower()
        url = f"{base_url}-{date}"
    else:
        date = parse_date.strftime(year_date_format).lower()
        url = f"{base_url}-{date}"

    return url


def links_iterator() -> Iterator[tuple[str, datetime]]:
    base_initial_url = \
        'https://understandingwar.org/backgrounder/' \
        'russia-ukraine-warning-update-initial-russian-offensive-campaign-assessment'

    start_date = datetime.strptime('February-24-2022', '%B-%d-%Y')
    end_date = datetime.now()
    delta = timedelta(days=1)

    parse_date = start_date
    while parse_date <= end_date:
        if parse_date == start_date:
            url = base_initial_url
        else:
            url = compose_link_for_date(parse_date)
        yield url, parse_date
        parse_date += delta


async def preprocess_text(tag: Tag, paragraphs: list, date: datetime):
    def remove_references(text):
        text = re.sub("(\\[\d+\\])", '', text).strip()
        return text.replace('&nbsp', '')

    def process_list(list_tag: Tag, level=1):
        for li in list_tag.find_all('li'):
            if li.find('ul'):
                paragraphs.append(f"{'-' * level} {remove_references(li.next.text)}")
                process_list(li.find('ul'), level=2)
            else:
                paragraphs.append(f"{'-' * level} {remove_references(li.text)}")

    text: str = unicodedata.normalize('NFKD', tag.text)
    if (date.strftime(month_article_date_format).lower() in text.lower()
            and (' ET' in text or ' EST' in text)
            and len(text.split('.')) == 1):
        paragraphs.clear()  # if the date was before 'Click here' paragraph or date paragraph
        return
    elif (tag.find('a') or tag.find('br') or tag.find('img')
          or 'Note' in text or 'https' in text or 'Click here to see' in text or not text.strip()):
        return

    if tag.find('li'):
        process_list(tag)
    else:
        paragraphs.append(remove_references(text))


async def parse_text(html: str, date: datetime) -> str:
    paragraphs = []
    soup = BeautifulSoup(html, "html.parser")
    text_div = soup \
        .find('div', {'class': 'field-type-text-with-summary'}) \
        .find('div', {'class': 'field-item even'})
    for tag in text_div.select('p, div, ul')[3:]:  # skip by date
        await preprocess_text(tag, paragraphs, date)
    return '\n'.join(paragraphs)


async def save_to_file(text: str, date: str):
    async with aiofiles.open(f"data/{date}.txt", 'w', encoding='utf-8') as f:
        await f.write(text)


async def fetch_data(url: str, date: datetime, session: aiohttp.ClientSession):
    ua = UserAgent()
    headers = {
        'authority': 'www.understandingwar.org',
        'accept': 'paragraphs/html,application/xhtml+xml,application/xml;',
        'user-agent': ua.random
    }
    string_date = date.strftime(year_date_format).lower()
    print(f"Processing {string_date}")
    response = await session.get(url=url, params='', headers=headers)

    if response.status != 200:
        if response.status == 404:
            print(f"No report for {string_date}")
        elif response.status == 403:
            print(f"Access denied for {string_date}")
        return

    text = await parse_text(await response.text(), date)
    await save_to_file(text, date.strftime(simple_date_format))


async def collect_data():
    tasks = set()
    iterator = links_iterator()
    async with aiohttp.ClientSession() as session:
        for url, date in iterator:
            # await fetch_data(url, date, session)
            task = asyncio.create_task(fetch_data(url, date, session))
            tasks.add(task)
            task.add_done_callback(tasks.discard)
        await asyncio.gather(*tasks)


async def main():
    await collect_data()


if __name__ == '__main__':
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    t0 = time()
    asyncio.run(main())
    print(f"Execution time: {time() - t0} ms")
