"""
Local Lead Finder (Lite Edition) - Google Maps Playwright Scraper
Capped at 10 results. Upgrade to Pro Edition for unlimited leads & email hunting.
"""

import time
import random
import re
import urllib.parse
import threading
from typing import Callable, Optional, List

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

from models import Lead


def clean_field_text(val: str) -> str:
    if not val:
        return ""
    cleaned = re.sub(r"[\ue000-\uf8ff]", "", val)
    lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
    return " ".join(lines).strip()


def clean_phone(val: str) -> str:
    if not val:
        return ""
    cleaned = clean_field_text(val)
    match = re.search(r"(\+?[\d\s\-().]{7,}\d)", cleaned)
    return match.group(1).strip() if match else cleaned


class GoogleMapsScraper:
    def __init__(
        self,
        query: str,
        location: str,
        max_results: int = 10,
        on_lead: Optional[Callable[[Lead], None]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        on_finished: Optional[Callable[[int], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ):
        self.query = query.strip()
        self.location = location.strip()
        # Strictly cap at 10 results in Lite Edition
        self.max_results = min(max(1, max_results), 10)
        self.on_lead = on_lead
        self.on_progress = on_progress
        self.on_status = on_status
        self.on_finished = on_finished
        self.on_error = on_error
        self.stop_event = stop_event or threading.Event()

    def _status(self, msg: str):
        if self.on_status:
            self.on_status(msg)

    def _progress(self, current: int, total: int):
        if self.on_progress:
            self.on_progress(current, total)

    def run(self) -> List[Lead]:
        leads: List[Lead] = []
        full_query = f"{self.query} {self.location}".strip()
        search_url = f"https://www.google.com/maps/search/{urllib.parse.quote_plus(full_query)}?hl=en"

        self._status(f"Starting Lite Scraper (Max: {self.max_results} leads)...")

        with sync_playwright() as p:
            browser = None
            for channel in ["chromium", "msedge", "chrome"]:
                try:
                    browser = p.chromium.launch(headless=True, channel=channel if channel != "chromium" else None)
                    break
                except Exception:
                    continue

            if not browser:
                if self.on_error:
                    self.on_error("Could not launch browser. Please run: playwright install chromium")
                return []

            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            try:
                page.goto(search_url, timeout=30000)
                time.sleep(2)

                # Dismiss consent dialog if present
                for btn_text in ["Accept all", "Reject all", "I agree", "Tümünü kabul et"]:
                    try:
                        btn = page.locator(f"button:has-text('{btn_text}')").first
                        if btn.is_visible(timeout=1500):
                            btn.click()
                            time.sleep(1)
                            break
                    except Exception:
                        pass

                feed_selector = 'div[role="feed"]'
                try:
                    page.wait_for_selector(feed_selector, timeout=12000)
                except PlaywrightTimeoutError:
                    pass

                processed_names = set()

                while len(leads) < self.max_results and not self.stop_event.is_set():
                    cards = page.locator('div[role="article"]').all()
                    if not cards:
                        cards = page.locator('div.Nv2PK').all()

                    new_card_found = False
                    for card in cards:
                        if self.stop_event.is_set() or len(leads) >= self.max_results:
                            break

                        try:
                            aria_label = card.get_attribute("aria-label") or ""
                            if not aria_label:
                                name_el = card.locator(".qBF1Pd, .fontHeadlineSmall").first
                                if name_el.count() > 0:
                                    aria_label = name_el.inner_text().strip()

                            name = clean_field_text(aria_label)
                            if not name or name in processed_names:
                                continue

                            processed_names.add(name)
                            new_card_found = True
                            self._status(f"Extracting [{len(leads)+1}/{self.max_results}]: {name}")

                            # Click card to inspect details
                            card.scroll_into_view_if_needed()
                            card.click()
                            time.sleep(1.2)

                            # Capture Google Maps URL
                            current_url = page.url
                            if "/maps/place/" in current_url:
                                maps_url = current_url
                            else:
                                maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(name + ' ' + self.location)}"

                            # Extract phone
                            phone = ""
                            phone_el = page.locator('button[data-tooltip*="phone"], button[aria-label*="Phone"], button[data-item-id*="phone:tel"]').first
                            if phone_el.count() > 0:
                                phone = clean_phone(phone_el.inner_text())

                            # Extract website
                            website = ""
                            web_el = page.locator('a[data-tooltip*="website"], a[aria-label*="Website"], a[data-item-id="authority"]').first
                            if web_el.count() > 0:
                                raw_href = web_el.get_attribute("href") or ""
                                if "google.com/url" in raw_href:
                                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                                    website = parsed.get("q", [raw_href])[0]
                                else:
                                    website = raw_href

                            # Extract address
                            address = ""
                            addr_el = page.locator('button[data-tooltip*="address"], button[aria-label*="Address"]').first
                            if addr_el.count() > 0:
                                address = clean_field_text(addr_el.inner_text())

                            # Extract rating & reviews
                            rating = None
                            reviews = None
                            rating_el = page.locator('div.F7nice span[aria-hidden="true"]').first
                            if rating_el.count() > 0:
                                try:
                                    rating = float(rating_el.inner_text().replace(",", ".").strip())
                                except ValueError:
                                    pass

                            review_el = page.locator('div.F7nice span:has-text("(")').first
                            if review_el.count() > 0:
                                m = re.search(r"\((\d[\d.,]*)\)", review_el.inner_text())
                                if m:
                                    reviews = int(re.sub(r"[^\d]", "", m.group(1)))

                            lead = Lead(
                                name=name,
                                phone=phone or None,
                                email="Pro Edition Only",
                                website=website or None,
                                rating=rating,
                                review_count=reviews,
                                address=address or None,
                                google_maps_url=maps_url,
                            )

                            leads.append(lead)
                            if self.on_lead:
                                self.on_lead(lead)
                            self._progress(len(leads), self.max_results)

                        except Exception:
                            continue

                    # Scroll feed
                    try:
                        page.locator(feed_selector).evaluate("el => el.scrollBy(0, 1000)")
                        time.sleep(1.5)
                    except Exception:
                        break

                    if not new_card_found and len(cards) > 0:
                        break

            finally:
                context.close()
                browser.close()

        self._status(f"Finished! Extracted {len(leads)} leads (Lite Edition Limit reached).")
        if self.on_finished:
            self.on_finished(len(leads))

        return leads
