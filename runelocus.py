import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


def test_split_tunnel(log):
    test_url = "https://api.my-ip.io/ip"
    response = requests.get(test_url)
    log.info(response.text)


def vote(driver, wait, log):
    cookies = driver.get_cookies()
    url = driver.current_url
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    url_callback = query_params.get("callback", [None])[0]

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.runelocus.com',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Referer': url,
        'Cookie': '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies]),
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Sec-GPC': '1'
    }

    for count in range(1, 6):
        data = {
            'countanswer': str(count),
            'rf': 'K3M2S1RkdmRick9aM2R4K0RHbzNLUT09',
            'callback': url_callback,
            'ua': 'dnZ6T3RPVzgxMnhqWkx1RnBCWG90N0JobDkwTWZqN3E1M3F3OENXR2gvcmc1ckVKbTF1QVJ'
                  'PeUNyc0tzMmE4eDNoNHQ3M045ZzIvZG1vaGl1Tmp6T3NrV0ZsTkpNSCtxMjJGUFNwY3dGaDQ9',
            'vote': 'Vote now'
        }

        response = requests.post(url, headers=headers, data=data)

        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        vote_result_element = soup.select_one("#vote-process-block")

        if vote_result_element.text == "Thanks, your vote has been recorded!":
            log.info(vote_result_element.text.strip())
            log.info("Voted on RuneLocus successfully!")
            break
        else:
            log.warning(vote_result_element.text.strip())
    else:
        log.error("RuneLocus vote FAILED!")
        log.error("Verify the split tunnel is working correctly.")
        log.error("If the split tunnel is working, it is currently unknown why it would be failing. Maybe a banned IP?")
        raise Exception
