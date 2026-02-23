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
