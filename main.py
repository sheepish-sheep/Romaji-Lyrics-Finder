from googlesearch import search
import requests
from bs4 import BeautifulSoup
import lyricspy
from pykakasi import kakasi
import tkinter as tk
from tkinter import ttk
import threading
import openai
import os
import time
from datetime import datetime, timedelta
import sys # Added for sys.modules

# Add these global variables at the top after imports
last_api_call = None
api_call_count = 0
MAX_API_CALLS_PER_HOUR = 50  # Adjust as needed
API_COOLDOWN_SECONDS = 2  # Minimum time between calls

def find_lyrics_urls(song_title):
    """Search for lyrics on Lyrical Nonsense website"""
    urls = {}
    
    # Try lyrical-nonsense.com (main source)
    try:
        query = f'site:lyrical-nonsense.com "{song_title}"'
        for url in search(query, num_results=3):
            if "lyrical-nonsense.com" in url:
                urls['lyrical_nonsense'] = url
                break
    except Exception as e:
        print(f"Lyrical Nonsense search error: {e}")
    
    return urls

def get_lyrics_from_lyrical_nonsense(url):
    """Extract lyrics from Lyrical Nonsense website"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Look for the specific lyrics content area
        lyrics_content = None
        
        # Try multiple strategies to find the lyrics
        strategies = [
            # Strategy 1: Look for div with class "lyrics"
            lambda: soup.find("div", class_="lyrics"),
            # Strategy 2: Look for div with id "lyrics"
            lambda: soup.find("div", id="lyrics"),
            # Strategy 3: Look for the main content area
            lambda: soup.find("main") or soup.find("article"),
            # Strategy 4: Look for div containing numbered lyrics
            lambda: find_div_with_numbered_lyrics(soup),
            # Strategy 5: Look for div with specific text patterns
            lambda: find_div_with_lyrics_patterns(soup)
        ]
        
        for strategy in strategies:
            try:
                result = strategy()
                if result:
                    lyrics_content = result
                    break
            except:
                continue
        
        if lyrics_content:
            # Extract only the clean lyrics content
            clean_lyrics = extract_clean_lyrics(lyrics_content)
            if clean_lyrics:
                return clean_lyrics
        
        return None
        
    except Exception as e:
        print(f"Lyrical Nonsense extraction error: {e}")
        return None

def find_div_with_numbered_lyrics(soup):
    """Find div containing numbered lyrics lines"""
    for div in soup.find_all("div"):
        text = div.get_text()
        # Check if this div contains numbered lyrics
        if text.count("1.") > 0 and text.count("2.") > 0 and text.count("3.") > 0:
            # Make sure it's not too long (avoid getting the whole page)
            if 100 < len(text) < 10000:
                return div
    return None

def find_div_with_lyrics_patterns(soup):
    """Find div with lyrics-like patterns"""
    for div in soup.find_all("div"):
        text = div.get_text().lower()
        # Look for lyrics indicators
        if any(pattern in text for pattern in ['lyrics', '歌詞', 'romaji', 'romanized']):
            # Check if it has numbered content
            if any(f"{i}." in text for i in range(1, 11)):
                return div
    return None

def extract_clean_lyrics(content_element):
    """Extract clean lyrics from a content element"""
    if not content_element:
        return None
    
    # Get all text content
    all_text = content_element.get_text("\n", strip=True)
    lines = all_text.split('\n')
    
    # Extract only lyrics lines
    lyrics_lines = []
    current_numbered_line = ""
    current_line_content = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Check if we're entering a lyrics section
        if any(keyword in line.lower() for keyword in ['lyrics', '歌詞', 'romaji', 'romanized']):
            continue
            
        # Check if we're leaving lyrics (hit navigation or other content)
        if any(keyword in line.lower() for keyword in ['favorite', 'view favorites', 'copy link', 'artist:', 'tie-in:', 'status', 'comments', 'transliterated by:', 'join our', 'send me a coffee', 'home', 'artists', 'series', 'reviews', 'support ln', 'about', 'join us', 'submit', 'video', 'related']):
            break
        
        # Check if this line starts with a number (1. to 99.)
        if line and line[0].isdigit() and '.' in line[:3]:
            # If we have a previous numbered line, save it first
            if current_numbered_line and current_line_content:
                full_line = current_numbered_line + " " + " ".join(current_line_content)
                lyrics_lines.append(full_line)
            
            # Start a new numbered line
            current_numbered_line = line
            current_line_content = []
            
        elif current_numbered_line and len(line) < 200 and not line.startswith(('http', 'www', '©', 'copyright')):
            # This is a continuation of the current numbered line
            current_line_content.append(line)
    
    # Don't forget the last numbered line
    if current_numbered_line and current_line_content:
        full_line = current_numbered_line + " " + " ".join(current_line_content)
        lyrics_lines.append(full_line)
    elif current_numbered_line:
        # If there's a numbered line with no content, add it as is
        lyrics_lines.append(current_numbered_line)
    
    # If we didn't find lyrics with the numbered approach, try direct extraction
    if not lyrics_lines:
        current_numbered_line = ""
        current_line_content = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line and line[0].isdigit() and '.' in line[:3]:
                # If we have a previous numbered line, save it first
                if current_numbered_line and current_line_content:
                    full_line = current_numbered_line + " " + " ".join(current_line_content)
                    lyrics_lines.append(full_line)
                
                # Start a new numbered line
                current_numbered_line = line
                current_line_content = []
                
            elif current_numbered_line and len(line) < 200 and not any(keyword in line.lower() for keyword in ['favorite', 'view favorites', 'copy link', 'artist:', 'tie-in:', 'status', 'comments', 'transliterated by:', 'join our', 'send me a coffee', 'home', 'artists', 'series', 'reviews', 'support ln', 'about', 'join us']):
                # This is a continuation of the current numbered line
                current_line_content.append(line)
        
        # Don't forget the last numbered line
        if current_numbered_line and current_line_content:
            full_line = current_numbered_line + " " + " ".join(current_line_content)
            lyrics_lines.append(full_line)
        elif current_numbered_line:
            # If there's a numbered line with no content, add it as is
            lyrics_lines.append(current_numbered_line)
    
    # Return clean lyrics
    if lyrics_lines:
        return '\n'.join(lyrics_lines)
    
    return None

def convert_to_romaji(japanese_text):
    try:
        kakasi_obj = kakasi()
        kakasi_obj.setMode("J", "a")  # Japanese to ascii (romaji)
        kakasi_obj.setMode("K", "a")  # Katakana to ascii (romaji)
        kakasi_obj.setMode("H", "a")  # Hiragana to ascii (romaji)
        conv = kakasi_obj.getConverter()
        return conv.do(japanese_text)
    except Exception as e:
        return f"Failed to convert to romaji: {str(e)}"

def fallback_lyrics(song_title):
    try:
        result = lyricspy.search(song_title)
        if result and len(result) > 0:
            return result[0].lyrics
    except Exception as e:
        print(f"Lyricspy error: {e}")
        return None
    return None

def try_alternative_anime_sources(song_title):
    """Try alternative anime lyrics sources that might be more accessible"""
    alternative_sources = [
        f'site:jpopasia.com "{song_title}" lyrics',
        f'site:musixmatch.com "{song_title}"',
        f'site:lyricstranslate.com "{song_title}"',
        f'site:utaten.com "{song_title}"',
        f'site:petitlyrics.com "{song_title}"'
    ]
    
    for query in alternative_sources:
        try:
            for url in search(query, num_results=2):
                if any(site in url for site in ['jpopasia.com', 'musixmatch.com', 'lyricstranslate.com', 'utaten.com', 'petitlyrics.com']):
                    return f"Found alternative anime lyrics source: {url}\nTry visiting this URL manually to get lyrics."
        except Exception:
            continue
    
    return None

def search_anime_lyrics_backup(song_title):
    """Backup search specifically for anime song lyrics on multiple platforms"""
    backup_sources = [
        # Anime-specific lyrics sites
        f'site:anime-lyrics.com "{song_title}"',
        f'site:animeop.info "{song_title}"',
        f'site:animeworld.com "{song_title}" lyrics',
        f'site:anime-planet.com "{song_title}"',
        f'site:myanimelist.net "{song_title}" lyrics',
        f'site:anidb.net "{song_title}"',
        f'site:animenewsnetwork.com "{song_title}"',
        f'site:crunchyroll.com "{song_title}"',
        f'site:funimation.com "{song_title}"',
        # Japanese music sites
        f'site:uta-net.com "{song_title}"',
        f'site:joysound.com "{song_title}"',
        f'site:dam-ch.com "{song_title}"',
        f'site:music.jp "{song_title}"',
        # International anime communities
        f'site:reddit.com/r/anime "{song_title}" lyrics',
        f'site:reddit.com/r/jpop "{song_title}"',
        f'site:reddit.com/r/anime_lyrics "{song_title}"',
        f'site:discord.gg anime "{song_title}" lyrics',
        # Anime database sites
        f'site:anilist.co "{song_title}"',
        f'site:kitsu.io "{song_title}"',
        f'site:shoboi.jp "{song_title}"',
        f'site:vgmdb.net "{song_title}"'
    ]
    
    found_sources = []
    
    for query in backup_sources:
        try:
            for url in search(query, num_results=1):
                # Extract domain name for cleaner display
                domain = url.split('/')[2] if len(url.split('/')) > 2 else url
                if domain not in [source.split('/')[2] for source in found_sources]:
                    found_sources.append(url)
                    if len(found_sources) >= 5:  # Limit to 5 results
                        break
            if len(found_sources) >= 5:
                break
        except Exception:
            continue
    
    if found_sources:
        result = "🎵 Found anime lyrics backup sources:\n\n"
        for i, url in enumerate(found_sources, 1):
            domain = url.split('/')[2] if len(url.split('/')) > 2 else url
            result += f"{i}. {domain}\n   {url}\n\n"
        result += "💡 Try visiting these sites manually to find lyrics!"
        return result
    
    return None

def search_lyrics_online(song_title):
    """Additional fallback: search for lyrics on other websites"""
    try:
        # Try searching for lyrics on other sites
        search_query = f'"{song_title}" lyrics site:lyrics.com OR site:genius.com OR site:azlyrics.com'
        for url in search(search_query, num_results=3):
            if any(site in url for site in ['lyrics.com', 'genius.com', 'azlyrics.com']):
                return f"Found potential lyrics source: {url}\nTry visiting this URL manually to get lyrics."
        return None
    except Exception as e:
        return None

def verify_romaji_with_chatgpt(japanese_text, romaji_text, api_key):
    global last_api_call, api_call_count
    # Rate limiting checks
    current_time = datetime.now()
    
    # Check hourly limit
    if api_call_count >= MAX_API_CALLS_PER_HOUR:
        return "API rate limit reached (50 calls/hour). Please wait before making more requests."
    
    # Check cooldown between calls
    if last_api_call and (current_time - last_api_call).total_seconds() < API_COOLDOWN_SECONDS:
        return f"Please wait {API_COOLDOWN_SECONDS} seconds between API calls."
    
    try:
        openai.api_key = api_key
        prompt = f"""Please verify if this romaji translation is accurate for the Japanese text:

Japanese: {japanese_text}
Romaji: {romaji_text}

Please:
1. Check if the romaji accurately represents the Japanese pronunciation
2. Provide corrections if needed
3. Give a confidence score (1-10)

Respond in this format:
Accuracy: [score]/10
Corrections: [any corrections or "None if accurate"]
Notes: [brief explanation]"""
        
        # Fixed: Use the correct OpenAI API method
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )

        # Update rate limiting variables
        last_api_call = current_time
        api_call_count += 1

        return response.choices[0].message.content
    except Exception as e:
        return f"ChatGPT verification failed: {str(e)}"

def main():
    root = tk.Tk()
    root.title("Romaji Lyrics Finder")
    root.geometry("800x700")

    # Add a flag to control thread execution
    stop_search = False

    api_label = tk.Label(root, text="OpenAI API Key (optional):", font=("Arial", 10, "bold"))
    api_label.pack(pady=(10,5))
    api_entry = tk.Entry(root, width=50, show="*", font=("Arial", 10))
    api_entry.pack(pady=5)

    # Add separator line
    separator1 = tk.Frame(root, height=2, bg="gray")
    separator1.pack(fill="x", padx=20, pady=10)

    # Fixed: Add scrollbar to text widget
    text_frame = tk.Frame(root)
    text_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
    
    text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 10))
    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    # Make output text widget read-only but copyable
    text_widget.config(state=tk.DISABLED)
    
    # Add line tracking variables
    current_line = 1
    total_lines = 1
    
    # Function to update line display
    def update_line_display():
        line_label.config(text=f"Line {current_line} of {total_lines}")
    
    # Function to move up one line
    def move_up_line():
        nonlocal current_line
        if current_line > 1:
            current_line -= 1
            highlight_current_line()
            update_line_display()
    
    # Function to move down one line
    def move_down_line():
        nonlocal current_line
        if current_line < total_lines:
            current_line += 1
            highlight_current_line()
            update_line_display()
    
    # Function to highlight the current line
    def highlight_current_line():
        text_widget.tag_remove("current_line", "1.0", tk.END)
        text_widget.tag_remove("completed_line", "1.0", tk.END)
        text_widget.tag_remove("upcoming_line", "1.0", tk.END)

         # Highlight completed lines (lines 1 to current_line-1)
        for i in range(1, current_line):
            start_pos = f"{i}.0"
            end_pos = f"{i}.end"
            text_widget.tag_add("completed_line", start_pos, end_pos)

        # Add highlighting to current line
        start_pos = f"{current_line}.0"
        end_pos = f"{current_line}.end"
        text_widget.tag_add("current_line", start_pos, end_pos)
        # Scroll to current line
        text_widget.see(start_pos)
    
    # Function to update total lines count
    def update_total_lines():
        nonlocal total_lines
        text_widget.config(state=tk.NORMAL)
        content = text_widget.get("1.0", tk.END)
        total_lines = len(content.split('\n'))
        text_widget.config(state=tk.DISABLED)
        update_line_display()
    
    # Configure the current line tag
    text_widget.tag_configure("current_line", background="lightblue", relief="raised")
    text_widget.tag_configure("completed_line", background="lightgreen", relief="flat")
    text_widget.tag_configure("upcoming_line", background="white", relief="flat")

    # Add right-click context menu for copy functionality
    def show_context_menu(event):
        try:
            # Enable text widget temporarily for selection
            text_widget.config(state=tk.NORMAL)
            # Select all text
            text_widget.tag_add(tk.SEL, "1.0", tk.END)
            # Copy to clipboard
            text_widget.event_generate("<<Copy>>")
            # Disable text widget again
            text_widget.config(state=tk.DISABLED)
        except:
            pass
    
    # Bind right-click to show context menu
    text_widget.bind("<Button-3>", show_context_menu)
    
    # Add keyboard shortcuts for copy (Ctrl+C)
    def copy_text(event):
        try:
            text_widget.config(state=tk.NORMAL)
            text_widget.event_generate("<<Copy>>")
            text_widget.config(state=tk.DISABLED)
        except:
            pass
        return "break"
    
    text_widget.bind("<Control-c>", copy_text)
    
    # Add keyboard navigation
    def on_key_press(event):
        nonlocal current_line
        if event.keysym == "Up":
            move_up_line()
            return "break"
        elif event.keysym == "Down":
            move_down_line()
            return "break"
        elif event.keysym == "Home":
            current_line = 1
            highlight_current_line()
            update_line_display()
            return "break"
        elif event.keysym == "End":
            current_line = total_lines
            highlight_current_line()
            update_line_display()
            return "break"
    
    text_widget.bind("<Key>", on_key_press)
    
    text_widget.pack(side="left", fill=tk.BOTH, expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Add line counter display below text widget
    line_frame = tk.Frame(text_frame)
    line_frame.pack(fill="x", pady=(5,0))
    
    line_label = tk.Label(line_frame, text="Line 1 of 1", font=("Arial", 9), fg="gray")
    line_label.pack(side="left")
    
    # Add navigation buttons
    nav_frame = tk.Frame(line_frame)
    nav_frame.pack(side="right")
    
    up_button = tk.Button(nav_frame, text="↑", width=3, command=move_up_line, font=("Arial", 10, "bold"))
    up_button.pack(pady=(0,2))
    
    down_button = tk.Button(nav_frame, text="↓", width=3, command=move_down_line, font=("Arial", 10, "bold"))
    down_button.pack(pady=(2,0))
    
    # Add separator line
    separator2 = tk.Frame(root, height=2, bg="gray")
    separator2.pack(fill="x", padx=20, pady=10)

    # Add clear label for song input
    song_label = tk.Label(root, text="Enter Song Title Here:", font=("Arial", 12, "bold"))
    song_label.pack(pady=(10,5))
    
    entry = tk.Entry(root, width=50, font=("Arial", 12))
    entry.pack(pady=10)
    
    # Add right-click context menu for input field
    def show_input_context_menu(event):
        input_menu = tk.Menu(root, tearoff=0)
        input_menu.add_command(label="Cut", command=lambda: entry.event_generate("<<Cut>>"))
        input_menu.add_command(label="Copy", command=lambda: entry.event_generate("<<Copy>>"))
        input_menu.add_command(label="Paste", command=lambda: entry.event_generate("<<Paste>>"))
        input_menu.add_separator()
        input_menu.add_command(label="Select All", command=lambda: entry.select_range(0, tk.END))
        input_menu.tk_popup(event.x_root, event.y_root)
    
    entry.bind("<Button-3>", show_input_context_menu)

    # Button frame for better layout
    button_frame = tk.Frame(root)
    button_frame.pack(pady=15)

    button = tk.Button(button_frame, text="Search", width=15, height=2, font=("Arial", 12, "bold"))
    button.pack(side="left", padx=10)

    # Add kill button
    kill_button = tk.Button(button_frame, text="Kill App", bg="red", fg="white", width=15, height=2, font=("Arial", 12, "bold"), command=root.quit)
    kill_button.pack(side="left", padx=10)

    def search_lyrics():
        nonlocal stop_search
        user_input = entry.get().strip()  # strip input spaces
        if not user_input:
            text_widget.config(state=tk.NORMAL)  # Enable to edit
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, "Please enter a song title.\n")
            text_widget.config(state=tk.DISABLED)  # Disable again
            update_total_lines()  # Update line count
            button.config(state=tk.NORMAL)
            return

        text_widget.config(state=tk.NORMAL)  # Enable to edit
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, f"Searching for: {user_input}\n\n")
        text_widget.config(state=tk.DISABLED)  # Disable again
        update_total_lines()  # Update line count

        # Check if search was stopped
        if stop_search:
            text_widget.config(state=tk.NORMAL)  # Enable to edit
            text_widget.insert(tk.END, "Search was stopped.\n")
            text_widget.config(state=tk.DISABLED)  # Disable again
            update_total_lines()  # Update line count
            button.config(state=tk.NORMAL)
            return

        try:
            urls = find_lyrics_urls(user_input)
        except Exception as e:
            text_widget.config(state=tk.NORMAL)  # Enable to edit
            text_widget.insert(tk.END, f"Error during search: {e}\n")
            text_widget.config(state=tk.DISABLED)  # Disable again
            update_total_lines()  # Update line count
            button.config(state=tk.NORMAL)
            return

        # Check if search was stopped
        if stop_search:
            text_widget.config(state=tk.NORMAL)  # Enable to edit
            text_widget.insert(tk.END, "Search was stopped.\n")
            text_widget.config(state=tk.DISABLED)  # Disable again
            update_total_lines()  # Update line count
            button.config(state=tk.NORMAL)
            return

        # Try Lyrical Nonsense (main source)
        if 'lyrical_nonsense' in urls:
            text_widget.config(state=tk.NORMAL)  # Enable to edit
            text_widget.insert(tk.END, f"Found Lyrical Nonsense URL: {urls['lyrical_nonsense']}\n")
            text_widget.config(state=tk.DISABLED)  # Disable again
            update_total_lines()  # Update line count
            
            try:
                lyrics = get_lyrics_from_lyrical_nonsense(urls['lyrical_nonsense'])
                if lyrics:
                    text_widget.config(state=tk.NORMAL)  # Enable to edit
                    text_widget.insert(tk.END, "\n--- Lyrics from Lyrical Nonsense ---\n\n")
                    text_widget.insert(tk.END, lyrics)
                    
                    # Try to convert to romaji if it's Japanese
                    text_widget.insert(tk.END, "\n\n--- Romaji conversion ---\n\n")
                    try:
                        romaji_result = convert_to_romaji(lyrics)
                        text_widget.insert(tk.END, romaji_result)
                    except Exception as e:
                        text_widget.insert(tk.END, f"Failed to convert lyrics to romaji: {str(e)}")
                    
                    # ChatGPT verification if API key is provided
                    api_key = api_entry.get().strip()
                    if api_key:
                        text_widget.insert(tk.END, "\n\n--- ChatGPT Verification ---\n")
                        text_widget.insert(tk.END, f"API calls this hour: {api_call_count}/{MAX_API_CALLS_PER_HOUR}\n")
                        
                        if api_call_count >= MAX_API_CALLS_PER_HOUR:
                            text_widget.insert(tk.END, "⚠️ Rate limit reached. Please wait before requesting verification.\n")
                        else:
                            text_widget.insert(tk.END, "Verifying romaji accuracy...\n")
                            verification = verify_romaji_with_chatgpt(lyrics, lyrics, api_key)
                            text_widget.insert(tk.END, verification)
                    
                    text_widget.config(state=tk.DISABLED)  # Disable again
                    update_total_lines()  # Update line count
                    button.config(state=tk.NORMAL)
                    return
                else:
                    text_widget.config(state=tk.NORMAL)  # Enable to edit
                    text_widget.insert(tk.END, "No lyrics found on Lyrical Nonsense page.\n")
                    text_widget.config(state=tk.DISABLED)  # Disable again
                    update_total_lines()  # Update line count
            except Exception as e:
                text_widget.config(state=tk.NORMAL)  # Enable to edit
                text_widget.insert(tk.END, f"Failed to get lyrics from Lyrical Nonsense: {e}\n")
                text_widget.config(state=tk.DISABLED)  # Disable again
                update_total_lines()  # Update line count
        else:
            text_widget.config(state=tk.NORMAL)  # Enable to edit
            text_widget.insert(tk.END, "No lyrics URLs found on Lyrical Nonsense.\n")
            text_widget.config(state=tk.DISABLED)  # Disable again
            update_total_lines()  # Update line count

        # Check if search was stopped
        if stop_search:
            text_widget.config(state=tk.NORMAL)  # Enable to edit
            text_widget.insert(tk.END, "Search was stopped.\n")
            text_widget.config(state=tk.DISABLED)  # Disable again
            update_total_lines()  # Update line count
            button.config(state=tk.NORMAL)
            return

        text_widget.config(state=tk.NORMAL)  # Enable to edit
        text_widget.insert(tk.END, "Trying fallback with LyricsPy...\n")
        text_widget.config(state=tk.DISABLED)  # Disable again
        update_total_lines()  # Update line count
        
        fallback = fallback_lyrics(user_input)
        if fallback:
            text_widget.config(state=tk.NORMAL)  # Enable to edit
            text_widget.insert(tk.END, "\n--- Lyrics from LyricsPy (likely Japanese) ---\n\n")
            text_widget.insert(tk.END, fallback)
            text_widget.insert(tk.END, "\n\n--- Romaji conversion ---\n\n")
            try:
                romaji_result = convert_to_romaji(fallback)
                text_widget.insert(tk.END, romaji_result)
            except Exception as e:
                text_widget.insert(tk.END, f"Failed to convert lyrics to romaji: {str(e)}")
            text_widget.config(state=tk.DISABLED)  # Disable again
            update_total_lines()  # Update line count
        else:
            text_widget.config(state=tk.NORMAL)  # Enable to edit
            text_widget.insert(tk.END, "No lyrics found with LyricsPy.\n")
            text_widget.config(state=tk.DISABLED)  # Disable again
            update_total_lines()  # Update line count
            
            # Try alternative anime lyrics sources
            text_widget.insert(tk.END, "\nTrying alternative anime lyrics sources...\n")
            alt_result = try_alternative_anime_sources(user_input)
            if alt_result:
                text_widget.insert(tk.END, alt_result)
            else:
                text_widget.insert(tk.END, "No alternative anime sources found.\n")
            
            # Try comprehensive anime lyrics backup search
            text_widget.insert(tk.END, "\n🔍 Performing comprehensive anime lyrics backup search...\n")
            backup_result = search_anime_lyrics_backup(user_input)
            if backup_result:
                text_widget.insert(tk.END, backup_result)
            else:
                text_widget.insert(tk.END, "No backup anime sources found.\n")
            
            # Try additional online search
            text_widget.insert(tk.END, "\nTrying additional online sources...\n")
            online_result = search_lyrics_online(user_input)
            if online_result:
                text_widget.insert(tk.END, online_result)
            else:
                text_widget.insert(tk.END, "No additional sources found.\n")
                
                # Provide helpful suggestions
                text_widget.insert(tk.END, "\n--- Suggestions ---\n")
                text_widget.insert(tk.END, "• Try searching with different song title variations\n")
                text_widget.insert(tk.END, "• Check if the song exists on lyrical-nonsense.com\n")
                text_widget.insert(tk.END, "• Try searching manually on: lyrical-nonsense.com, genius.com, or azlyrics.com\n")
                text_widget.insert(tk.END, "• Try alternative anime sites: jpopasia.com, utaten.com, petitlyrics.com\n")
                text_widget.insert(tk.END, "• Check anime database sites: myanimelist.net, anilist.co, anidb.net\n")
                text_widget.insert(tk.END, "• Search Japanese music sites: uta-net.com, joysound.com, dam-ch.com\n")
            text_widget.config(state=tk.DISABLED)  # Disable again
            update_total_lines()  # Update line count

        button.config(state=tk.NORMAL)

    def on_click():
        nonlocal stop_search
        stop_search = False  # Reset stop flag
        button.config(state=tk.DISABLED)  # disable button while searching
        threading.Thread(target=search_lyrics, daemon=True).start()

    def stop_search_func():
        nonlocal stop_search
        stop_search = True
        text_widget.insert(tk.END, "\n🛑 Stopping search...\n")
        button.config(state=tk.NORMAL)

    button.config(command=on_click)

    # Add stop button
    stop_button = tk.Button(button_frame, text="Stop Search", bg="orange", width=15, height=2, font=("Arial", 12, "bold"), command=stop_search_func)
    stop_button.pack(side="left", padx=10)

    # Add keyboard shortcut for stopping (Ctrl+C equivalent)
    def on_key_press(event):
        if event.state == 4 and event.keysym == 'c':  # Ctrl+C
            stop_search_func()
    
    root.bind('<Key>', on_key_press)

    root.mainloop()

if __name__ == "__main__":
    main()
