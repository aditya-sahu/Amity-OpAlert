from apscheduler.schedulers.blocking import BlockingScheduler
import requests
import os

sched = BlockingScheduler()

@sched.scheduled_job('interval',minutes=150)
def timed_job():
    x = requests.get(os.environ.get('CRONJOBURL'))
    print(x)
