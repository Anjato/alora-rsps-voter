from twocaptcha import TwoCaptcha


api_key = "fc8553a0f9973a08d7d13f83e233dc55"


def hcaptcha_solver(sitekey, url):
    solver = TwoCaptcha(api_key)

    response = solver.hcaptcha(sitekey=sitekey, url=url)
    solution = response["code"]

    return solution


def recaptcha2_solver(sitekey, url):
    solver = TwoCaptcha(api_key)

    response = solver.recaptcha(sitekey=sitekey, url=url)
    solution = response["code"]

    return solution
