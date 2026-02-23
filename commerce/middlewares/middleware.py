import time
import csv
import os
import datetime
from django.http import HttpResponseForbidden


# Get the absolute path of the current script's folder
base_dir = os.path.dirname(os.path.abspath(__file__))
load_time_file_path = os.path.join(base_dir, "loadtime.csv")
response_file_path = os.path.join(base_dir, "responses.csv")

class RequestLoggingMiddleware():
    def __init__(self, get_response: callable):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        end_time = time.time()
        load_time = round((end_time - start_time), 3)

        # send/log to csv for analytics
        request_path = request.get_full_path()
        time_stamps = datetime.datetime.now()
        user = request.user
        row = [user, request_path, request.method, load_time, time_stamps]

        try:
            with open(load_time_file_path, "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(row)
        except Exception as e:
            print(e)

        with open(response_file_path, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(response.text)
        
        return response


class RestrictAccessByTimeMiddleware():
    """
    Docstring for RestrictAccessByTimeMiddleware
    Middleware that restricts access of the app by specified time
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        current_time = datetime.datetime.now().time()

        # restricted hours
        restrict_start = datetime.time(9, 0)
        restrict_end = datetime.time(13, 0)

        # check if current time is within restricted hours
        is_restricted = self.is_time_restricted(current_time, restrict_start, restrict_end)

        # check if the request is for specific endpoint
        if self.is_specific_endpoint(request.path) and is_restricted:
            return HttpResponseForbidden(
                "Access to messaging services is restricted between 9 PM and 6 AM."
                "Please try again during allowed hours."
            )

        # go ahead and continue
        response = self.get_response(request)
        return response
    
    def is_time_restricted(self, current_time, start_time, end_time):
        # check if current time falls within restricted time
        if start_time < end_time:
            # restrict within same day
            return start_time <= current_time <= end_time
        else:
            # restriction spans midnight
            return current_time >= start_time or current_time <= end_time

    def is_specific_endpoint(self, path):
        # check is request path is for specific endpoint
        restricted_paths = [
            "/api/users/",
            "/api/orders/",
        ]        

        # check if path starts with any messaging endpoint
        return any(path.startswith(restricted_path) for restricted_path in restricted_paths)

class RateLimitMiddleware():
    """
    Docstring for RateLimitMiddleware
    limits number of messages a user can send based on IP address
    LIMIT: 5 messages per minute per IP
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # store request count per IP
        self.request_log = {}
        self.limit = 5 # messages
        self.window = 60 # 1 min 

    def __call__(self, request):
        # TODO control for restricted endpoint and requests

        # get ip of client
        ip = self.get_client_ip(request)

        # check if ip rate limited
        if self.is_rate_limited_ip(ip):
            min_timestamp = min(self.request_log[ip])
            max_timestamp = max(self.request_log[ip])
            rem_time = round(self.window - (time.time() - max_timestamp))

            return HttpResponseForbidden(
                f"Rate limit exceeded. your IP is blocked: Maximum {self.limit} messages per {self.window} seconds window."
                f"Please try in {rem_time} secs to send more messages."
            )

        # first time, record the request
        self.record_request(ip)
        response = self.get_response(request)
        return response

    def get_client_ip(self, request):

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR", "0.0.0.0")

        return ip

    def is_specific_endpoint(self, path):
        # check for restricted endpoint
        restricted_paths = ["/api/"]
        return any(path.startswith(restricted_path) for restricted_path in restricted_paths)
    
    def is_rate_limited_ip(self, ip):
        # get current time
        current_time = time.time()

        # set ip if not in log
        if ip not in self.request_log:
            self.request_log[ip] = []

        # remove old timestamps outside window
        window_start = current_time - self.window
        self.request_log[ip] = [timestamp for timestamp in self.request_log[ip] if timestamp > window_start] 

        # check if limit exceeded
        return len(self.request_log[ip]) >= self.limit
    
    def record_request(self, ip):
        # record request timestamp for ip
        current_time = time.time()
        self.request_log[ip].append(current_time)

        # cleanup old IP to prevent memory leak
        self.cleanup_old_entries()

    def cleanup_old_entries(self):
        # removes IP that has not been used for last hour
        current_time = time.time()
        one_hour_ago = current_time - 3600

        ips_to_remove = []
        for ip, timestamps in self.request_log.items():
            # mark for removal if not recent activity
            if not timestamps or max(timestamps) < one_hour_ago:
                ips_to_remove.append(ip)
             
        for ips in ips_to_remove:
            del self.request_log[ips]

