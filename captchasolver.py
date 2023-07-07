from twocaptcha import TwoCaptcha


def hcaptcha_solver(sitekey, url):
    api_key = "fc8553a0f9973a08d7d13f83e233dc55"
    solver = TwoCaptcha(api_key)

    response = solver.hcaptcha(sitekey=sitekey, url=url)
    solution = response["code"]

    return solution
