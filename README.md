# Romaji Lyrics Finder

## Overview
This project is a single-file application that creates a popup interface for scraping romaji (romanized Japanese) lyrics from anime songs. You can also provide your API key to double-check the translation accuracy if you trust my coding skills(which you shouldn't).

## Features
- **Lyrics Search**: Find lyrics from multiple anime music sources
- **Romaji Conversion**: Automatically convert Japanese lyrics to romaji
- **API Integration**: Optional OpenAI API integration for translation verification
- **Comprehensive Backup**: Multiple fallback sources for hard-to-find lyrics
- **User-Friendly Interface**: Simple GUI with keyboard navigation

## How It Works
1. Enter the anime song title you're looking for
2. The app searches multiple lyrics databases
3. Extracts and formats the lyrics with proper numbering
4. Converts Japanese text to romaji pronunciation
5. Optionally verifies accuracy using AI (if API key provided)

## Sources
- **Primary**: Lyrical Nonsense (lyrical-nonsense.com)
- **Fallback**: LyricsPy, multiple anime lyrics sites
- **Backup**: 25+ anime and Japanese music platforms
- **Verification**: OpenAI GPT for romaji accuracy checking

## Requirements
- Python 3.6+
- Required packages listed in `requirements.txt`
- Optional: OpenAI API key for translation verification

## Usage
Run `main.py` to launch the application. Enter a song title and click "Search" to begin finding lyrics.

## Note
This tool is designed for educational and personal use. Please respect copyright and use responsibly.