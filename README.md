# Epic Free Games Tracker

Automatically tracks free games on the [Epic Games Store](https://store.epicgames.com/en-US/free-games) and creates a GitHub Issue whenever new free games are available.

## How it works

A GitHub Actions workflow runs daily and queries the Epic Games Store API for current free game promotions. When new games are detected, it:

1. Updates `data/free_games.json` with the new game details
2. Creates a GitHub Issue with game info, images, and direct claim links

## Get notified

To receive notifications when new free games are available:

1. Click the **Watch** button at the top of this repository
2. Select **Custom** > check **Issues** > click **Apply**

You'll get an email each time a new free game is posted.

## Game history

All previously tracked free games are stored in [`data/free_games.json`](data/free_games.json), providing a historical record of every free game offer.
