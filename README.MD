# Xavier's Tiny Disk Usage Explorer

It does what it says: explore disk usage. The backend is written in Python (3.7 or higher), and the frontend is written in HTML5.

Please note: this is not intended to have good UI or UX, but rather to server my very specific needs. It deliberately does things in ways which could be improved to save development time.

_Please note that this tool can't account for folders/files which it can't access, so the numbers may be actually larger_

## Using it

 1. Ensure you have Python 3.7. If you don't use Micro$oft Window$, read the section below.

 2. Run du.py

 3. Point your web browser to `http://localhost:8080`

 4. Wait a while. You can open up the console in Python to see as it looks through your filesystem and adds things up

 5. After it loads, you should see the files in your root C: drive.

 6. The entry's heights are proportional to their size relative to the sizes of the folder/s they contain

 7. You can hover your mouse over entries to view further info

 8. Folders are marked with a blue right edge.

 9. You can click on folders to view their contents. Note that on occasion the backend may need to look through your filesystem (if it decides it wants to forget it)

 10. Click on a folder to the left of the currently opened folder to close it

 11. Alt+Click on any entry to reveal it in explorer (Windows only)

## Non-windows

To use on a *NIX system, you'll need to change a few things:

 1. Change the line in `du.html` from `make_listing("C:\\", document.body, 0, 0);` to `make_listing("/", document.body, 0, 0);`

## Testimonials

> "This software immediately helped me identify a plethora of useless and unwanted software/files on my computer, and has helped me free up 10% of my storage (more than 12gb). Highly recommended!"

_[GitHubMadHatter](https://github.com/GitHubMadHatter) - Yash Agarwal_
