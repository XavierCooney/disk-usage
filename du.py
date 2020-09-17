#!/usr/bin/env python
__author__ = "Xavier Cooney"

import sys
if sys.version_info < (3, 7):
    print("Need at least Python 3.7!")
    input("Press enter to exit... ")
    sys.exit(1)

import functools
import heapq
import json
import os
import shutil
import subprocess
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer

# relatively simplistic exclusion list (must be full path, case insensitive)
EXCLUDE_PATHS = ['/mnt/c', '/proc', '/dev']

def xav_cache(max_size=16384, initial_minimum=float('-inf')):
    """ A tiny priority cache function, pretty nifty """
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
main_scan_num_files = 0
main_scan_num_bytes = 0
main_scan_time = None

@xav_cache(max_size=(4096 * 8))
def find_folder_size(path):
    global last_report_unix_time, main_scan_num_files, main_scan_num_bytes
    if time.time() > last_report_unix_time + 1:
        print(f'Examining {path}...')
        last_report_unix_time = time.time()

    for exclusion in EXCLUDE_PATHS:
        if path.lower().startswith(exclusion.lower()):
            print(f"Skipping '{path}' because of exclusion")
            return 0, 0

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
                        entry_num_bytes = entry.stat().st_size
                        total += entry.stat().st_size
                        if is_first_scan:
                            main_scan_num_files += 1
                            main_scan_num_bytes += entry_num_bytes
                    else:
                        print(f"Hmmm symlink: {entry.path}")
                except:
                    pass
    except:
        pass
    return num_files, total

BINARY_SIZE_UNIT = 1024

def nice_format_byte_amount(byte_amount):
    size_summary_suffix = ""
    size_summary_value = byte_amount

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

    return str(round(size_summary_value, 2)) + " " + size_summary_suffix + "B"

def get_formatted_total_files_discovered():
    global main_scan_num_files
    if main_scan_num_files <= 0 or main_scan_num_files % 1 != 0:
        return str(main_scan_num_files)
    file_amt_reversed = []
    num_files_temp = main_scan_num_files
    while num_files_temp != 0:
        this_group = num_files_temp % 1000
        num_files_temp = num_files_temp // 1000
        if num_files_temp == 0:
            file_amt_reversed.append(str(f'{this_group % 1000}'))
        else:
            file_amt_reversed.append(str(f'{this_group % 1000:03}'))
    return ','.join(reversed(file_amt_reversed))

listing_lock = threading.Lock()
is_first_scan = True

@xav_cache(max_size=512)
def get_proportional_listing(path):
    global is_first_scan, main_scan_time
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
                    size_summary = nice_format_byte_amount(entry_size)

                    children.append((entry_size, os.path.split(entry.path)[1], entry.path, is_folder, size_summary, num_files))
            time_took = str(round(time.time() - began_listing, 3))
            print(f"Done proportional listing of {path}, size is {total}, took {time_took} seconds")
            # print(f"(current lowest in cache: {find_folder_size.lowest_cached_val()})")
            if is_first_scan:
                main_scan_time = time_took
            is_first_scan = False
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

            self.wfile.write(json.dumps({
                'entries': listing,
                'header': f"Primary scan took {main_scan_time} seconds and found "
                          f"{nice_format_byte_amount(main_scan_num_bytes)} across {get_formatted_total_files_discovered()} files. © 2019-2020 Xavier Cooney"
            }).encode('utf-8'))
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
        elif len(splitted) == 1 and splitted[0] == "/main_scan_status":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                f'{nice_format_byte_amount(main_scan_num_bytes)} discovered across {get_formatted_total_files_discovered()} files'.encode('utf-8')
            )
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 NOT FOUND")

if __name__ == '__main__':
    host = "localhost"
    port = 8080
    with ThreadingHTTPServer((host, port), DUHttpHandle) as httpd:
        sa = httpd.socket.getsockname()
        print(f"Waiting on {sa[0]} port {sa[1]} (http://{sa[0]}:{sa[1]}/) ...")
        try:
            webbrowser.open_new_tab(f"http://{host}:{port}")
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)
