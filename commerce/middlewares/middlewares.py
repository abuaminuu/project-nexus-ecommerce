import time
import csv
import os
from datetime import datetime

# Get the absolute path of the current script's folder
base_dir = os.path.dirname(os.path.abspath(__file__))
load_time_file_path = os.path.join(base_dir, 'loadtime.csv')

class LoadTimeMiddleware():
    def __init__(self, get_response: callable):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        end_time = time.time()
        load_time = round((end_time - start_time), 3)

        # send/log to csv for analytics
        request_path = request.get_full_path()
        time_stamps = datetime.now()
        user = request.user
        row = [user, request_path, load_time, time_stamps]

        try:
            with open(load_time_file_path, "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(row)
        except Exception as e:
            print(e)
        
        return response

    
