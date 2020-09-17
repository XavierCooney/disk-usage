# Xavier's Tiny Disk Usage Explorer

It does what it says: explore disk usage. The backend is written in Python (3.7 or higher), and the frontend is written in HTML5.

_Please note that this tool can't account for folders/files which it can't access, so the numbers may be actually larger. Furthermore, it only counts the size of the files themselves, and not filesystem metadata_

## Using it

 1. Ensure you have Python 3.7

 2. Run `du.py`

 3. Point your web browser to `http://localhost:8080` (should also open automatically)

 4. Wait for the program to process all of your filesystem. You should see live statistics update on the loading screen as the program works

 5. After it is done, you should see the files in your root `C:` drive (or `/` for *nix)

 6. The entry's heights are proportional to their size relative to the sizes of the folder(s) they contain

 7. You can hover your mouse over entries to view further info

 8. Folders are marked with a blue right edge

 9. You can click on folders to view their contents. Note that on occasion the backend may need to look through your filesystem again (if it decided it wanted to forget it previously)

 10. Click on a folder to the left of the currently opened folder to close it

 11. Alt+Click on any entry to reveal it in explorer (Windows only)

 12. Alter the `EXCLUDE_PATHS` list in `du.py` to exclude folders as wanted

## Testimonials

> "This software immediately helped me identify a plethora of useless and unwanted software/files on my computer, and has helped me free up 10% of my storage (more than 12gb). Highly recommended!"

_[GitHubMadHatter](https://github.com/GitHubMadHatter) - Yash Agarwal_

## Screenshot

![A screenshot of the software](screenshot.png?raw=true "Optional Title")
