from twocaptcha import TwoCaptcha
from twocaptcha.solver import TimeoutException


api_key = "fc8553a0f9973a08d7d13f83e233dc55"


def hcaptcha_solver(sitekey, url, log):
    solver = TwoCaptcha(api_key)

    try:
        response = solver.hcaptcha(sitekey=sitekey, url=url)
    except TimeoutException:
        log.warning("2captcha request timed out. Trying again!")
        return False

    solution = response["code"]

    return solution


def recaptcha2_solver(sitekey, url, log):
    solver = TwoCaptcha(api_key)

    try:
        response = solver.recaptcha(sitekey=sitekey, url=url)
    except TimeoutException:
        log.warning("2captcha request timed out. Trying again!")
        return False

    solution = response["code"]

    return solution
