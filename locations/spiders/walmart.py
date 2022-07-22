# -*- coding: utf-8 -*-
import json
import re
from locations.items import GeojsonPointItem
from scrapy.spiders import SitemapSpider


class WalmartSpider(SitemapSpider):
    name = "walmart"
    item_attributes = {"brand": "Walmart", "brand_wikidata": "Q483551"}
    allowed_domains = ["walmart.com"]
    sitemap_urls = ["https://www.walmart.com/sitemap_store_main.xml"]
    sitemap_rules = [
        (
            r"https://www.walmart.com/store/\d*/.*/details",
            "parse_store",
        ),
    ]
    custom_settings = {
        "DOWNLOAD_DELAY": 0.5,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
    }

    def store_hours(self, store_hours):
        if store_hours.get("operationalHours").get("open24Hours") is True:
            return "24/7"
        elif not store_hours.get("operationalHoursCombined"):
            return None
        else:
            op_hours = store_hours.get("operationalHoursCombined")
            open_hours = []
            for op_hour in op_hours:
                if op_hour.get("dailyHours").get("closed") is True:
                    continue

                if op_hour.get("dailyHours").get("openFullDay") is True:
                    start_hr = "00:00"
                    end_hr = "24:00"
                else:
                    start_hr = op_hour.get("dailyHours").get("startHr")
                    end_hr = op_hour.get("dailyHours").get("endHr")

                start_day = op_hour.get("startDayName")
                end_day = op_hour.get("endDayName")

                if end_day is None:
                    end_day = ""

                hours = start_day + "-" + end_day + " " + start_hr + "-" + end_hr
                open_hours.append(hours)

            hours_combined = "; ".join(open_hours)

            return hours_combined

    def parse_store(self, response):
        script = response.xpath(
            "//script[contains(.,'__WML_REDUX_INITIAL_STATE__ = ')]"
        ).extract_first()

        script_content = re.search(
            r"window.__WML_REDUX_INITIAL_STATE__ = (.*);</script>",
            script,
            flags=re.IGNORECASE | re.DOTALL,
        ).group(1)

        store_data = json.loads(script_content).get("store")
        services = store_data["primaryServices"] + store_data["secondaryServices"]

        yield GeojsonPointItem(
            lat=store_data.get("geoPoint").get("latitude"),
            lon=store_data.get("geoPoint").get("longitude"),
            ref=store_data.get("id"),
            phone=store_data.get("phone"),
            name=store_data.get("displayName"),
            opening_hours=self.store_hours(store_data),
            addr_full=store_data.get("address").get("streetAddress"),
            city=store_data.get("address").get("city"),
            state=store_data.get("address").get("state"),
            postcode=store_data.get("address").get("postalCode"),
            website=store_data.get("detailsPageURL"),
            extras={
                "amenity:fuel": any(
                    s["name"] == "GAS_STATION" and s["active"] for s in services
                ),
                "shop": "department_store"
                if store_data["storeType"]["id"] == 2
                else "supermarket",
            },
        )
