import sys
import os
import functools
import shutil
import heapq
import json
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.parse
import functools


def custom_cache(max_size = 16384, initial_minimum = float('-inf')):
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
                print(f"HIT")
                return cache_attempt
            print(f"MISS")            
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
        return wrapped_function
    return decorating_function

@custom_cache(max_size = 2048 * 8)
def find_folder_size(path):
    print(f"Checking {path} ...")
    total = 0
    try:
        with os.scandir(path) as entry_iterator:
            for entry in entry_iterator:
                try:
                    if entry.is_dir(follow_symlinks = False):
                        total += find_folder_size(entry.path)
                    elif entry.is_file(follow_symlinks = False):
                        total += entry.stat().st_size
                except:
                    pass
    except:
        pass
    print(f"{path} is size {total}")
    return total

BINARY_SIZE_UNIT = 1024

@custom_cache(max_size = 512)
def get_proportional_listing(path):
    print(f"Proportional listing {path} ...")
    total = 0
    children = []
    with os.scandir(path) as entry_iterator:
        for entry in entry_iterator:
            if entry.is_dir(follow_symlinks = False):
                entry_size = find_folder_size(entry.path)
                is_folder = True
            elif entry.is_file(follow_symlinks = False):
                entry_size =  entry.stat().st_size
                is_folder = False
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
            
            children.append((entry_size, os.path.split(entry.path)[1], entry.path, is_folder, size_summary))
    return list(map(lambda child: (child[0] / total, *child[1:]), children))

class DUHttpHandle(BaseHTTPRequestHandler):
    def do_GET(self):
        splitted = urllib.parse.unquote(self.path).split("|")
        if self.path == "/":
            with open('du.html', 'rb') as f:
                self.send_response(200)
                self.end_headers()
                shutil.copyfileobj(f, self.wfile)
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
            # TODO make this work
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 NOT FOUND")

"""

@custom_cache(max_size = 16)
def test(x):
    result = x * 2 + 1
    print(f"test({x}) = {result}")
    return result

assert test(0) == 1
assert test(0) == 1
assert test(1) == 3
assert test(1) == 3
assert test(2) == 5
assert test(2) == 5
assert test(3) == 7
assert test(3) == 7
assert test(4) == 9
assert test(4) == 9
assert test(5) == 11
assert test(5) == 11
assert test(6) == 13
assert test(6) == 13
assert test(7) == 15
assert test(7) == 15

assert test(0) == 1
assert test(0) == 1
assert test(1) == 3
assert test(1) == 3
assert test(2) == 5
assert test(2) == 5
assert test(3) == 7
assert test(3) == 7
assert test(4) == 9
assert test(4) == 9
assert test(5) == 11
assert test(5) == 11
assert test(6) == 13
assert test(6) == 13
assert test(7) == 15
assert test(7) == 15
"""


if __name__ == '__main__':
    host = "localhost"
    port = 8080
    with ThreadingHTTPServer((host, port), DUHttpHandle) as httpd:
        sa = httpd.socket.getsockname()
        serve_message = "Serving HTTP on {host} port {port} (http://{host}:{port}/) ..."
        print(serve_message.format(host=sa[0], port=sa[1]))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)