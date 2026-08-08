"""Google sign-in fallback for legitimate Authenticator/TOTP challenges.

This module does not bypass Google's security checks. It only helps Selenium
navigate the normal "Try another way" UI when Google does not expose the
Authenticator option immediately.
"""

from __future__ import annotations

import logging
import time

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

import services.google_automation as google_automation

logger = logging.getLogger(__name__)

_ORIGINAL_RESOLVE = google_automation._resolve_post_password_state


def _click_try_another_way(driver) -> bool:
    """Click Google's normal alternative-verification control if visible."""
    selectors = (
        # Text variants used by Google's current and older sign-in UIs.
        (By.XPATH, "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'try another way')]") ,
        (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'try another way')]") ,
        (By.XPATH, "//*[@role='button' and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'try another way')]") ,
        (By.XPATH, "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'another way')]") ,
        (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'another way')]") ,
        (By.XPATH, "//*[@role='button' and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'another way')]") ,
    )

    for by, selector in selectors:
        try:
            elements = driver.find_elements(by, selector)
            for element in elements:
                try:
                    if not element.is_displayed() or not element.is_enabled():
                        continue
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
                    try:
                        element.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", element)
                    time.sleep(1.5)
                    logger.info("Clicked Google's 'Try another way' control.")
                    return True
                except StaleElementReferenceException:
                    continue
                except Exception as exc:
                    logger.debug("Unable to click alternative verification control: %s", exc)
        except Exception:
            continue
    return False


def _click_authenticator_option(driver) -> bool:
    """Select the normal Google Authenticator/TOTP option when it is shown."""
    selectors = (
        (By.CSS_SELECTOR, '[data-challengetype="6"]'),
        (By.XPATH, "//*[@data-challengetype='6']"),
        (By.XPATH, "//div[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'google authenticator')]") ,
        (By.XPATH, "//div[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'authenticator')]") ,
        (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'authenticator')]") ,
        (By.XPATH, "//*[@role='button' and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'authenticator')]") ,
        (By.XPATH, "//li[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'authenticator')]") ,
    )

    for by, selector in selectors:
        try:
            elements = driver.find_elements(by, selector)
            for element in elements:
                try:
                    if not element.is_displayed() or not element.is_enabled():
                        continue
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
                    try:
                        element.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", element)
                    time.sleep(1.5)
                    if google_automation._is_totp_challenge(driver):
                        logger.info("Google Authenticator/TOTP challenge selected.")
                        return True
                except StaleElementReferenceException:
                    continue
                except Exception as exc:
                    logger.debug("Unable to select Authenticator option: %s", exc)
        except Exception:
            continue
    return False


def _fallback_resolve_post_password_state(driver, email: str) -> str:
    """Use the existing resolver first, then recover through Try another way."""
    try:
        return _ORIGINAL_RESOLVE(driver, email)
    except google_automation.GoogleAutomationError as exc:
        message = str(exc).lower()
        if "no authenticator option found" not in message:
            raise

        logger.warning(
            "Google did not expose Authenticator directly for %s; opening Try another way.",
            email,
        )

        clicked = _click_try_another_way(driver)
        if not clicked:
            raise

        # Google can render the alternative methods asynchronously.
        deadline = time.time() + 8
        while time.time() < deadline:
            if _click_authenticator_option(driver):
                return "needs_totp"
            if google_automation._is_totp_challenge(driver):
                return "needs_totp"
            time.sleep(0.5)

        raise


# Patch only the internal resolver before handlers import it. The public
# start_login API and all existing Telegram flows remain unchanged.
google_automation._resolve_post_password_state = _fallback_resolve_post_password_state
