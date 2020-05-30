#!/web/cs1511/bin/python3
import argparse
from datetime import datetime
import time
import pandas as pd
from pandas.api.types import is_numeric_dtype
import requests
import pathlib

DEFAULT_WEEKS = 10

LOCAL_TIMEZONE = "Australia/Sydney"

HEADER_ROWS = ['name', 'start', 'end', 'recurr']

BB_POST_URL = "https://au-lti.bbcollab.com/collab/api/csa/sessions"

def enable_logging():
    import logging

    import http.client as http_client
    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

def parse_args():
    def is_valid_file(parser, arg):
        arg = pathlib.Path(arg)
        if not arg.exists():
            parser.error("The file %s does not exist!" % str(arg))
        else:
            return arg

    parser = argparse.ArgumentParser(description="Upload classes to Blackboard Collaborate")
    parser.add_argument("classes_csv", help="csv file containing classes",
                        type=lambda x: is_valid_file(parser, x))
    parser.add_argument("token", help="Your auth token for BB Collaborate.")
    parser.add_argument("-d", "--debug", help="Turn on debug logging", action='store_true')
    args = parser.parse_args()

    return args

def parse_classes(classes_csv):
    df = pd.read_csv(classes_csv)
    if list(df) != HEADER_ROWS:
        raise ValueError(f"File {classes_csv} did not have the headers: {HEADER_ROWS}")

    # This doesn't deal with UTC
    for col in ['start', 'end']:
        df[col] = pd.to_datetime(df[col])
        print(df[col])
        df[col] = df[col].dt.tz_localize(LOCAL_TIMEZONE)

    if not is_numeric_dtype(df['recurr']):
        raise ValueError("Recurr column must be numeric.")

    return df.to_dict('records')

def get_authed_session(token):
    s = requests.Session()
    s.headers.update({'Authorization': f'Bearer {token}'})

    test_request = s.get("https://au-lti.bbcollab.com/collab/ui/scheduler/session")
    if not test_request.ok:
        raise ValueError("Could not connect to BB Collab with given token.")

    return s

def bb_json_from_dict(bb_class):
    datestamp = datetime.now().isoformat()
    day_of_week = bb_class['start'].strftime("%A").lower()[:2]

    return {
        "startTime":bb_class['start'].isoformat(),
        "endTime":bb_class['end'].isoformat(),
        "created":datestamp,
        "modified":datestamp,
        "canDownloadRecording":False,
        "showProfile":False,
        "canShareAudio":True,
        "canShareVideo":True,
        "canPostMessage":True,
        "canAnnotateWhiteboard":True,
        "allowGuest":False,
        "canEnableLargeSession":False,
        "telephonyEnabled":True,
        "mustBeSupervised":False,
        "ltiParticipantRole":"participant",
        "boundaryTime":15,
        "guestRole":"participant",
        "participantCanUseTools":True,
        "createdTimezone": LOCAL_TIMEZONE,
        "occurrenceType":"P",
        "recurrenceRule":{
            "recurrenceType":"weekly",
            "interval":1,
            "recurrenceEndType":"after_occurrences_count",
            "numberOfOccurrences":10,
            "daysOfTheWeek":[day_of_week],
            "endDate":None
        },
        "noEndDate":False,
        "name": bb_class['name']
    }

def create_bb_class(bb_class, session):
    class_json = bb_json_from_dict(bb_class)
    session.post(BB_POST_URL, json=class_json)

def main():
    args = parse_args()
    if args.debug:
        enable_logging()
    classes = parse_classes(args.classes_csv)
    session = get_authed_session(args.token)
    for bb_class in classes:
        create_bb_class(bb_class, session)
        if args.debug:
            return

if __name__ == "__main__":
    main()
