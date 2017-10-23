# -*- coding: utf-8 -*-

import asyncio
import logging

from src.Launcher import Launcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s:  %(message)s')

BROWSER = r'C:\APP\chrome32\chrome-win32\chrome.exe'


async def main():
    URL = 'https://www.jd.com/'
    INPUT_SELECTOR = '#key'
    SUBMIT_SELECTOR = '#search > div > div.form > button'

    SCH_KEY = '洗衣液'

    browser = Launcher.startBrowser(dict(BROWSEPATH=BROWSER))

    await browser.connect()
    page = await browser.createPage()
    await page.goto(URL, startHarRecord=False)
    await page.click(INPUT_SELECTOR)
    await page.types(SCH_KEY)
    await page.click(SUBMIT_SELECTOR, waitForLoadFinish=True)

    # await page.getHar(r'c:\Doc\test22.har')

    Goodslist_SELECTOR = '#J_goodsList > ul > li'
    GoodsName = 'div > div.p-name.p-name-type-2 > a > em'
    GoodsPrice = 'div > div.p-price > strong > i'
    GoodsCommitNum = 'div > div.p-commit > strong'

    result = await page.evalateFromList(Goodslist_SELECTOR,
                                        dict(goodsName=GoodsName, goodsPrice=GoodsPrice, commits=GoodsCommitNum))
    logging.info('result was {}'.format(result))
    # Launcher.killBrowser()


if __name__ == "__main__":
    result = asyncio.get_event_loop().run_until_complete(main())
    logging.info('main done')
