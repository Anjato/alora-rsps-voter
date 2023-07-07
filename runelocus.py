import time
from PIL import Image
import io
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select


def vote(driver, wait):

    vote_wait_timer = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#timer-message")))

    while True:
        try:
            is_visible = vote_wait_timer.is_displayed()
            is_active = vote_wait_timer.is_enabled()

            if is_visible and is_active:
                print("Waiting for captcha to load...")
            else:
                print("RuneLocus captcha loaded!")
                break

        except NoSuchElementException as e:
            print(f"Element could not be found!")
            print(e)
            break

        time.sleep(0.5)

    captcha_image_element = "#captchaimg"
    answer_element = "#answer > select"
    vote_button_element = "#vote"

    captcha_image = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, captcha_image_element)))
    answer = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, answer_element)))
    vote_button = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, vote_button_element)))

    # Screenshot image because URL being used generates a random image
    screenshot = captcha_image.screenshot_as_png

    image = Image.open(io.BytesIO(screenshot))
    image.show()

    # Select correct dropdown menu choice
    select = Select(answer)

    user_input = input("How many runescape objects are in the image?")

    try:
        select.select_by_value(user_input)
    except Exception as e:
        print(e)

    # Click the vote button
    vote_button.click()

    vote_result_element = "#vote-process-block:first-child"
    vote_result = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, vote_result_element)))

    if vote_result.text == "Thanks, your vote has been recorded!":
        print("Voted on RuneLocus successfully!")
    else:
        print(vote_result.text)
        driver.back()
        vote(driver, wait)
