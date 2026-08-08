"""Runtime patch for the post-login Gemini/Google One offer flow.

This module is imported automatically by Python's site machinery. It patches
only the post-login offer navigation; Google sign-in and Google verification
remain in Google's own UI.
"""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import urljoin

from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By

logger = logging.getLogger("autopixel.offer_flow")


def _offer_urls(driver) -> list[str]:
    """Collect account-specific Google offer URLs visible in the current page."""
    found: list[str] = []
    patterns = (
        r"https?://one\.google\.com/(?:offer|partner-eft-onboard)/[^\"'<>\\s]+",
        r"/offer/[A-Za-z0-9_-]+(?:\?[^\"'<>\\s]+)?",
        r"/partner-eft-onboard/[A-Za-z0-9_-]+(?:\?[^\"'<>\\s]+)?",
    )

    def add(value: str) -> None:
        value = (value or "").strip().rstrip(".,);]")
        if value.startswith("/"):
            value = urljoin("https://one.google.com", value)
        if value.startswith("http") and "one.google.com/" in value:
            if "/offer/" in value or "/partner-eft-onboard/" in value:
                if value not in found:
                    found.append(value)

    try:
        for element in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
            add(element.get_attribute("href") or "")
    except Exception:
        pass

    try:
        source = driver.page_source or ""
        for pattern in patterns:
            for match in re.findall(pattern, source, flags=re.IGNORECASE):
                add(match)
    except Exception:
        pass

    try:
        add(driver.current_url or "")
    except Exception:
        pass

    return found


def _visible_click_by_text(driver, labels: tuple[str, ...]) -> bool:
    """Click a visible Google UI element whose text/aria-label matches."""
    script = """
    const labels = arguments[0].map(x => x.toLowerCase());
    const nodes = document.querySelectorAll('button, a, [role="button"], [role="link"], [role="menuitem"]');
    for (const node of nodes) {
      if (!node || node.offsetParent === null) continue;
      const text = ((node.innerText || '') + ' ' + (node.getAttribute('aria-label') || '')).trim().toLowerCase();
      if (labels.some(label => text.includes(label))) {
        node.click();
        return true;
      }
    }
    return false;
    """
    try:
        return bool(driver.execute_script(script, list(labels)))
    except Exception:
        return False


def _wait_for_offer(driver, timeout: int = 8) -> str | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        urls = _offer_urls(driver)
        if urls:
            return urls[0]
        time.sleep(0.5)
    return None


def _navigate_and_scan(driver, url: str) -> str | None:
    logger.info("Offer flow: opening %s", url)
    try:
        driver.get(url)
    except TimeoutException:
        try:
            driver.execute_script("window.stop();")
        except Exception:
            pass
    time.sleep(3)

    # Consent dialogs, when present.
    _visible_click_by_text(driver, ("accept all", "i agree", "agree"))
    time.sleep(1)

    link = _wait_for_offer(driver, 3)
    if link:
        return link

    # Gemini web flow mirrors the documented in-app fallback:
    # profile -> Upgrade to Gemini Advanced -> eligibility.
    if "gemini.google.com" in (driver.current_url or ""):
        _visible_click_by_text(driver, ("profile", "account", "google account"))
        time.sleep(1)
        _visible_click_by_text(
            driver,
            ("upgrade to gemini advanced", "upgrade to gemini", "gemini advanced"),
        )
        time.sleep(3)

        link = _wait_for_offer(driver, 3)
        if link:
            return link

        # Some current Gemini UIs expose Check eligibility directly.
        _visible_click_by_text(driver, ("check eligibility", "check for offers", "check offer"))
        time.sleep(3)

        link = _wait_for_offer(driver, 3)
        if link:
            return link

        # Start Trial can reveal the final account-specific offer page. Do not
        # click Subscribe or submit payment information.
        _visible_click_by_text(driver, ("start trial", "start your trial"))
        time.sleep(3)
        link = _wait_for_offer(driver, 4)
        if link:
            return link

    return _wait_for_offer(driver, 2)


def patched_navigate_google_one(driver):
    """Post-login Gemini/Google One offer discovery used by AutoPixel."""
    urls = (
        "https://gemini.google.com/",
        "https://one.google.com/about/plans",
        "https://one.google.com/",
    )

    for url in urls:
        try:
            link = _navigate_and_scan(driver, url)
            if link:
                logger.info("Offer flow: account-specific offer found: %s", link)
                return link
        except (TimeoutException, WebDriverException) as exc:
            logger.warning("Offer flow failed on %s: %s", url, exc)
        except Exception as exc:
            logger.warning("Unexpected offer-flow error on %s: %s", url, exc)

    return None


def _patch() -> None:
    try:
        import services.google_automation as google_automation
        google_automation.navigate_google_one = patched_navigate_google_one
        google_automation.check_offer_with_driver = lambda driver: patched_navigate_google_one(driver)
        logger.info("Post-login Gemini offer flow patch loaded")
    except Exception as exc:
        logger.warning("Could not load post-login Gemini offer flow patch: %s", exc)


_patch()
