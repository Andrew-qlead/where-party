import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from parsers.eventbrite_parser import fetch_events_cyprus as fetch_eventbrite
from parsers.incyprus_parser import fetch_events_incyprus
from parsers.timeout_parser import fetch_events_timeout
from bot.poster import post_new_events

def main():
    print("=== Where Party Cyprus — запуск ===")
    all_events = []

    all_events += fetch_eventbrite()
    all_events += fetch_events_incyprus()
    all_events += fetch_events_timeout()

    print(f"Всего событий собрано: {len(all_events)}")
    post_new_events(all_events)
    print("=== Готово ===")

if __name__ == "__main__":
    main()
