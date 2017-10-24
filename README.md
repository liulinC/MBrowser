MBrowser is a python version puppeteer(JS), implemented by asyncio and  PyEventEmitter developed in anpther repo of mine

it's only for study, since only some API implemented, not all features implemented


here is an example for your use:

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


details pls reference test.py under Test.



