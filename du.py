import functools
import heapq
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer


def xav_cache(max_size=16384, initial_minimum=float('-inf')):
    if not isinstance(max_size, int):
        raise TypeError('Expected max_size to be an integer')

    def decorating_function(user_function):
        not_found_sentinel = object()
        arg_to_val_cache = {}
        values_remembered = []
        current_cache_length = 0
        current_min = initial_minimum
        def wrapped_function(*args, **kwargs):
            nonlocal arg_to_val_cache, values_remembered, current_cache_length, current_min
            # print(f"DBG: cache: {arg_to_val_cache}")
            if kwargs:
                raise Exception("keyword args not supported")
            combined_args = (args,)
            cache_attempt = arg_to_val_cache.get(combined_args, not_found_sentinel)
            if cache_attempt is not not_found_sentinel:
                return cache_attempt
            value = user_function(*args, **kwargs)
            if current_cache_length < max_size:
                # cache isn't full, just put it in regardless
                arg_to_val_cache[combined_args] = value
                heapq.heappush(values_remembered, (value, combined_args))
                current_cache_length += 1
                current_min = values_remembered[0][0]
            elif value > current_min:
                # toss it in the cache, replace the worst one currently
                cache_row_to_be_replaced = heapq.heapreplace(values_remembered, (value, combined_args))
                cache_row_to_be_replaced_val, cache_row_to_be_replaced_arg = cache_row_to_be_replaced
                del arg_to_val_cache[cache_row_to_be_replaced_arg]
                arg_to_val_cache[combined_args] = value
                current_min = values_remembered[0][0]
            return value
        # wrapped_function.lowest_cached_val = lambda: (values_remembered[0], len(arg_to_val_cache))
        return wrapped_function
    return decorating_function

last_report_unix_time = 0

@xav_cache(max_size=(4096 * 8))
def find_folder_size(path):
    global last_report_unix_time
    if time.time() > last_report_unix_time + 1:
        print(f'Examining {path}...')
        last_report_unix_time = time.time()

    total = 0
    num_files = 0
    try:
        with os.scandir(path) as entry_iterator:
            for entry in entry_iterator:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        sizes = find_folder_size(entry.path)
                        num_files += sizes[0]
                        total += sizes[1]
                    elif entry.is_file(follow_symlinks=False):
                        num_files += 1
                        total += entry.stat().st_size
                    else:
                        print(f"Hmmm symlink: {entry.path}")
                except:
                    pass
    except:
        pass
    return num_files, total

BINARY_SIZE_UNIT = 1024
listing_lock = threading.Lock()

@xav_cache(max_size=512)
def get_proportional_listing(path):
    began_listing = time.time()
    if not listing_lock.acquire(blocking=True, timeout=10):
        raise Exception(
            "Could not get lock after 10 seconds. "
            "Have you got multiple tabs of this program open?"
        )
    else:
        try:
            print(f"Proportional listing {path} ...")
            total = 0
            children = []
            with os.scandir(path) as entry_iterator:
                for entry in entry_iterator:
                    if entry.is_dir(follow_symlinks=False):
                        num_files, entry_size = find_folder_size(entry.path)
                        is_folder = True
                    elif entry.is_file(follow_symlinks=False):
                        entry_size = entry.stat().st_size
                        is_folder = False
                        num_files = 1
                    else:
                        print(f"Hmmm got a symlink here... {entry.name}")
                        entry_size = 0 # don't follow, just assume it takes zero size...
                        is_folder = False
                        num_files = 1
                    total += entry_size
                    size_summary_suffix = ""
                    size_summary_value = entry_size

                    if size_summary_value >= BINARY_SIZE_UNIT:
                        size_summary_value /= BINARY_SIZE_UNIT
                        size_summary_suffix = "K"
                    if size_summary_value >= BINARY_SIZE_UNIT:
                        size_summary_value /= BINARY_SIZE_UNIT
                        size_summary_suffix = "M"
                    if size_summary_value >= BINARY_SIZE_UNIT:
                        size_summary_value /= BINARY_SIZE_UNIT
                        size_summary_suffix = "G"
                    if size_summary_value >= BINARY_SIZE_UNIT:
                        size_summary_value /= BINARY_SIZE_UNIT
                        size_summary_suffix = "T" # hmmm terabyte
                    if size_summary_value >= BINARY_SIZE_UNIT:
                        size_summary_value /= BINARY_SIZE_UNIT
                        size_summary_suffix = "P" # hmmm petabyte
                    if size_summary_value >= BINARY_SIZE_UNIT:
                        size_summary_value /= BINARY_SIZE_UNIT
                        size_summary_suffix = "E" # hmmm exabyte

                    size_summary = str(round(size_summary_value, 3)) + " " + size_summary_suffix + "B"

                    children.append((entry_size, os.path.split(entry.path)[1], entry.path, is_folder, size_summary, num_files))
            time_took = str(round(time.time() - began_listing, 3))
            print(f"Done proportional listing of {path}, size is {total}, took {time_took} seconds")
            # print(f"(current lowest in cache: {find_folder_size.lowest_cached_val()})")
            return list(map(lambda child: (child[0] / total, *child[1:]), children))
        finally:
            # can't easily use context manager with timeout for locking :(
            listing_lock.release()

class DUHttpHandle(BaseHTTPRequestHandler):
    def do_GET(self):
        splitted = urllib.parse.unquote(self.path).split("|")
        if self.path == "/":
            with open('du.html', 'rb') as f:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(
                    f.read().replace(
                        b"__FS_ROOT__",
                        os.path.abspath(os.sep).replace("\\", "\\\\").encode('utf-8')
                    )
                )
        elif len(splitted) == 2 and splitted[0] == "/query":
            listing = get_proportional_listing(splitted[1])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(listing).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 NOT FOUND")
    
    def do_POST(self):
        splitted = urllib.parse.unquote(self.path).split("|")
        if len(splitted) == 2 and splitted[0] == "/reveal":
            if os.name == 'nt':
                # note: may return non-zero exit status, because Windows :(
                subprocess.run('explorer /select,"' + splitted[1].replace('"', '') + '"')
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(501) # 501: Not Implemented
                self.end_headers()
                self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 NOT FOUND")

if __name__ == '__main__':
    host = "localhost"
    port = 8080
    with ThreadingHTTPServer((host, port), DUHttpHandle) as httpd:
        sa = httpd.socket.getsockname()
        serve_message = "Serving HTTP on {host} port {port} (http://{host}:{port}/) ..."
        print(serve_message.format(host=sa[0], port=sa[1]))
        try:
            webbrowser.open_new_tab(f"http://{host}:{port}")
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)
