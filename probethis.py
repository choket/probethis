#!/usr/bin/env python3

import requests
import argparse
import sys
import os
import re
import time
import socket
import threading
from colors import *

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


#psmall = ["80", "81", "443", "591", "2082", "2087", "2095", "2096", "3000", "8000", "8001", "8008", "8080", "8083", "8443", "8834", "8888"]
psmall = ["80", "443",  "2082", "2087", "2095", "2096", "8080", "8083", "8443"]
plarge = ["80", "81", "443", "300", "591", "593", "832", "981", "1010", "1311", "2082", "2087", "2095", "2096", "2480", "3000", "3128", "3333", "4243", "4567", "4711", "4712", "4993", "5000", "5104", "5108", "5800", "6543", "7000", "7396", "7474", "8000", "8001", "8008", "8014", "8042", "8069", "8080", "8081", "8088", "8090", "8091", "8118", "8123", "8172", "8222", "8243", "8280", "8281", "8333", "8443", "8500", "8834", "8880", "8888", "8983", "9000", "9043", "9060", "9080", "9090", "9091", "9200", "9443", "9800", "9981", "12443", "16080", "18091", "18092", "20720", "28017"]
domains = []
outputbuffer = []
headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36'}

def print_line(r, ip_addr):
    try:
        status = r.status_code
        url = r.url

        # set redirect value to location header if status code is 3xx
        redirect_value = r.headers['location'] if str(status)[0] == "3" else ''

        title = re.findall(r'<title[^>]*>(.*?)</title>', r.text, re.IGNORECASE)
        title = '' if title == [] else title[0]

        if str(status)[0] == "1":
            status_color = white
        elif str(status)[0] == "2":
            status_color = lgreen
        elif str(status)[0] == "3":
            status_color = lyellow
        elif str(status)[0] == "4":
            status_color = lred
        elif str(status)[0] == "5":
            status_color = lcyan

        
        # Use dark yellow for 404
        outputbuffer.append(url)

        print(url,
              "[{}{}{}]".format(status_color, status, white),
              "[{}{}{}]".format(cyan, redirect_value, white),
              "[{}{}{}]".format(magenta, title, white),
              "[{}]".format(ip_addr),
              flush=True
         )
    except Exception as e:
        print(str(e))
        pass

def extract_domain(url):
    # remove http and https from input to avoid confusion
    if url.startswith('https://'):
        url = url[8:]
    elif url.startswith('http://'):
        url = url[7:]

    url.rstrip("/")

    return url

def work(timeout, ports, is_https):
    while domains != []:
        try:
            domain = domains.pop()
            domain = extract_domain(domain)
            
            if domain == "":
                continue

            try:
                ip = socket.gethostbyname(domain)
            except socket.gaierror:
                pass

            for port in ports:
                resp_http = None
                resp_https = None

                url_http = "http://{}:{}".format(domain, port)
                url_https = "https://{}:{}".format(domain, port)

                # THis doesnt work
                try:
                    resp_https = requests.get(url_https, timeout = timeout, allow_redirects = False,
                                            headers = headers, stream=True, verify=False)
                except requests.ConnectionError:
                    # Only check for http listener if https fails
                    try:
                        resp_http = requests.get(url_http, timeout = timeout, allow_redirects = False,
                                                headers = headers, stream=True)
                    except requests.ConnectionError:
                        pass

                
                if resp_https is not None:
                    print_line(resp_https, ip)
                
                # Print http only if is_https is false, or if there is no https response
                if resp_http and (not is_https or resp_https is None):
                    print_line(resp_http, ip)

        except requests.exceptions.ReadTimeout:
            pass
        except Exception as e:
            raise e
            pass



def main():
    usage = '''
    Example:

    probethis.py -f domains.txt -t 5 -o output.txt
    probethis.py -f domains.txt -p [ 81,8080,3000 | small | large]
    cat domains.txt | probethis.py -s 200,403,401 -o filtered.txt
	'''
    parser = argparse.ArgumentParser(description="Find working domains!", epilog=usage, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-f", help="File with domain list", type=str, action="store")
    parser.add_argument("-t", help="No of threads", type=int, default=5, action="store")
    parser.add_argument("-o", help="Output file name, Saves all status codes by default unless codes specified using -s", type=str, action="store")
    parser.add_argument("-p", help='"Comma seperated list of ports, or "small" or "large" for a predefined list of ports', type=str, action="store", default="small")
    parser.add_argument("--https", help="Prefer HTTPS over http", action="store_true")
    parser.add_argument("--timeout", help="Timeout for requests", type=int, default=5, action="store")
    args = parser.parse_args()
    file = args.f
    threadcount = args.t
    outputfile = args.o
    ports = args.p
    is_https = args.https
    timeout = args.timeout

    if ports == "small":
        ports = psmall
    elif ports == "large":
        ports = plarge
    else:
        ports.replace(" ", "")
        ports = ports.split(",")

    # if pipe input
    if not file:
        for d in sys.stdin:
            domains.append(d.rstrip('\n'))
    # if input file
    else:
        data = open(file, "r").read()
        domains.extend(data.split('\n'))
    

    # thread lists
    tlist = []
    for i in range(threadcount):
        t = threading.Thread(target=work, args=(timeout, ports, is_https))
        t.start()
        tlist.append(t)

    try:
        # keep main thread running
        while True:
            time.sleep(2)
            if domains == []:
                for t in tlist:
                    # if any thread is active
                    if t.is_alive():
                        continue
                # all threads are complete
                break
        if outputfile:
            # write ouput to file if provided
            with open(outputfile, "w") as f:
                f.write("\n".join(d for d in outputbuffer))
            sys.stdout.write(end)

    except KeyboardInterrupt:
        print("Aborted by User")
        if outputfile:
            # write ouput to file if provided
            with open(outputfile, "w") as f:
                f.write("\n".join(d for d in outputbuffer))
        os.kill(os.getpid(), 9)
        sys.stdout.write(end)

if __name__ == '__main__':
    main()
