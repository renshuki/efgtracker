#!/usr/bin/env python3
"""Check Epic Games Store for new free games and update tracking data."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

API_URL = (
    "https://store-site-backend-static.ak.epicgames.com"
    "/freeGamesPromotions?locale=en-US&country=US&allowCountries=US"
)
STORE_BASE_URL = "https://store.epicgames.com/p"
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "free_games.json"


def fetch_free_games():
    """Fetch current free games from the Epic Games Store API."""
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    elements = resp.json()["data"]["Catalog"]["searchStore"]["elements"]

    free_games = []
    for game in elements:
        promotions = game.get("promotions")
        if not promotions:
            continue
        promo_offers = promotions.get("promotionalOffers") or []
        for offer_group in promo_offers:
            for offer in offer_group.get("promotionalOffers", []):
                if offer.get("discountSetting", {}).get("discountPercentage") == 0:
                    free_games.append(_parse_game(game, offer))
                    break

    return free_games


def _parse_game(game, offer):
    """Extract relevant fields from a game element."""
    # Build store URL from mappings
    # Prefer productSlug because pageSlug mappings are absent for some offers.
    slug = (game.get("productSlug") or "").strip("/")
    for mapping in game.get("catalogNs", {}).get("mappings", []):
        if slug:
            break
        if mapping.get("pageSlug"):
            slug = mapping["pageSlug"].strip("/")
            break
    if not slug:
        for mapping in game.get("offerMappings", []):
            if mapping.get("pageSlug"):
                slug = mapping["pageSlug"].strip("/")
                break

    store_url = f"{STORE_BASE_URL}/{slug}" if slug else ""

    # Get wide image for issue display
    image_url = ""
    for img in game.get("keyImages", []):
        if img.get("type") == "OfferImageWide":
            image_url = img["url"]
            break
    if not image_url:
        for img in game.get("keyImages", []):
            if img.get("type") == "Thumbnail":
                image_url = img["url"]
                break

    price_info = game.get("price", {}).get("totalPrice", {})
    fmt = price_info.get("fmtPrice", {})

    return {
        "id": game["id"],
        "title": game.get("title", "Unknown"),
        "description": game.get("description", ""),
        "original_price": fmt.get("originalPrice", "N/A"),
        "start_date": offer.get("startDate", ""),
        "end_date": offer.get("endDate", ""),
        "store_url": store_url,
        "image_url": image_url,
        "seller": game.get("seller", {}).get("name", "Unknown"),
    }


def load_data():
    """Load existing tracked games data."""
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"games": {}, "last_checked": ""}


def save_data(data):
    """Save tracked games data."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def format_issue_body(new_games):
    """Format the GitHub Issue body as markdown."""
    lines = []
    for game in new_games:
        end_date = game["end_date"]
        if end_date:
            try:
                dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                end_date = dt.strftime("%B %d, %Y at %H:%M UTC")
            except ValueError:
                pass

        lines.append(f"## {game['title']}")
        if game["image_url"]:
            lines.append(f"![{game['title']}]({game['image_url']})")
        lines.append("")
        lines.append(f"> {game['description']}")
        lines.append("")
        lines.append(f"- **Original Price:** {game['original_price']}")
        lines.append(f"- **Publisher:** {game['seller']}")
        lines.append(f"- **Free Until:** {end_date}")
        if game["store_url"]:
            lines.append(f"- **Claim Here:** {game['store_url']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    print("Fetching free games from Epic Games Store...")
    current_free = fetch_free_games()
    print(f"Found {len(current_free)} free game(s)")

    data = load_data()
    existing_ids = set(data["games"].keys())

    new_games = [g for g in current_free if g["id"] not in existing_ids]
    print(f"New games: {len(new_games)}")

    if not new_games:
        print("No new free games found.")
        # Write outputs for GitHub Actions
        gh_output = os.environ.get("GITHUB_OUTPUT")
        if gh_output:
            with open(gh_output, "a") as f:
                f.write("has_new_games=false\n")
        return

    # Update data
    for game in new_games:
        data["games"][game["id"]] = {k: v for k, v in game.items() if k != "id"}

    data["last_checked"] = datetime.now(timezone.utc).isoformat()
    save_data(data)

    # Print new games
    for game in new_games:
        print(f"  - {game['title']} (was {game['original_price']}, free until {game['end_date']})")

    # Write outputs for GitHub Actions
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        issue_title = f"New Free Games on Epic Games Store — {today}"
        issue_body = format_issue_body(new_games)

        with open(gh_output, "a") as f:
            f.write("has_new_games=true\n")
            f.write(f"issue_title={issue_title}\n")
            # Use delimiter for multiline body
            f.write("issue_body<<EOF\n")
            f.write(issue_body)
            f.write("\nEOF\n")


if __name__ == "__main__":
    main()
