# Browser Extension (Optional Bonus)

1. Load `extension/` as an unpacked extension in Chrome.
2. Open any Reddit thread; click the extension. It scrapes a few on-page comments and calls the backend `/suggest` to display 2 suggestions.
3. Configure backend base URL in `chrome.storage.sync` (optional). Default is `http://127.0.0.1:8000`.
