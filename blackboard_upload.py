#!/usr/bin/env python3

from argparse import ArgumentParser, FileType, Namespace
from datetime import datetime
from time import sleep
from json import load as json_load
from csv import DictReader as csv_dictreader
from collections.abc import Mapping

import requests
from dateutil.parser import parse

LOCAL_TIMEZONE = "Australia/Sydney"

REQUIRED_HEADER_ROWS = ['name', 'start', 'end']

BB_POST_URL = "https://au-lti.bbcollab.com/collab/api/csa/sessions"
BB_DELETE_URL = "https://au-lti.bbcollab.com/collab/api/csa/sessions/{sid}/occurrences/{oid}"


def parse_args() -> Namespace:
    """
    Parse command-line args
    expect 1-3 readable files
    :return: namespace object of command-line args
    """

    parser = ArgumentParser(description="Upload classes to Blackboard Collaborate")

    parser.add_argument("classes_csv", help="csv file containing classes", type=FileType('r'))
    parser.add_argument("config_json", help="json file containing session config", type=FileType('r'), default=None)
    parser.add_argument("-t", "--token", help="Your auth token for BB Collaborate.", type=FileType('r'), default=None)
    parser.add_argument("-d", "--debug", help="Turn on requests debug logging", action='store_true')

    args = parser.parse_args()

    return args


def enable_logging() -> None:
    """
    Enable logging within the `requests` package
    :return: None
    """

    import logging
    import http.client as http_client

    http_client.HTTPConnection.debuglevel = 1

    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def get_authed_session(token: str) -> requests.Session:
    """
    Get an authorised Blackboard Collaborate session for the `requests` package
    :param token: A Blackboard Collaborate login token manually taken from an authed request
    :return: An authorised requests session
    """

    s = requests.Session()
    s.headers.update({'Authorization': f'Bearer {token}'})
    test_request = s.get(BB_POST_URL)

    if not test_request.ok:
        raise ValueError(
            f"Could not connect to BB Collab with given token. {test_request.status_code}: {test_request.reason}"
        )

    return s


def parse_dict(config: dict) -> dict:
    """
    :param config:
    :return:
    """

    if "startTime" in config: config["startTime"] = parse(config["startTime"]).isoformat()
    if "endTime" in config: config["endTime"] = parse(config["endTime"]).isoformat()

    config["occurrenceType"] = "P" if "recurrenceEndType" in config else "S"
    if "recurrenceRule" not in config: config["recurrenceRule"] = {}
    if "recurrenceType" in config:
        config["recurrenceRule"]["recurrenceType"] = config["recurrenceType"]
        if config["recurrenceEndType"] not in ["daily", "weekly", "monthly"]: raise ValueError()
        del config["recurrenceType"]
    if "interval" in config:
        config["recurrenceRule"]["interval"] = int(config["interval"])
        del config["interval"]
    if "recurrenceEndType" in config:
        if config["recurrenceEndType"] not in ["after_occurrences_count", "on_date"]: raise ValueError()
        config["recurrenceRule"]["recurrenceEndType"] = config["recurrenceEndType"]
        del config["recurrenceEndType"]
    if "daysOfTheWeek" in config:
        config["recurrenceRule"]["daysOfTheWeek"] = list(map(str.strip, config["daysOfTheWeek"].strip().split(",")))
        del config["daysOfTheWeek"]
    elif "startTime" in config:
        config["recurrenceRule"]["daysOfTheWeek"] = [parse(config['startTime']).strftime("%A").lower()[:2]]
    if "numberOfOccurrences" in config:
        config["recurrenceRule"]["numberOfOccurrences"] = int(config["numberOfOccurrences"])
        del config["numberOfOccurrences"]
    if "endDate" in config:
        config["recurrenceRule"]["endDate"] = parse(config["endDate"]).isoformat()
        del config["endDate"]

    return config


def bb_json_from_dict(bb_course_config: dict, bb_class_config: dict) -> dict:
    """
    :param bb_course_config:
    :param bb_class_config:
    :return:
    """
    def update(d, u):
        """
        :param d:
        :param u:
        :return:
        """
        for k, v in u.items():
            if isinstance(v, Mapping): d[k] = update(d.get(k, {}), v)
            else: d[k] = v
        return d

    datestamp = datetime.now().isoformat()

    # If `largeSessionEnable` is `True` then `noEndDate` MUST be false and `occurrenceType` MUST be `S`
    # If `noEndDate` is `True` then `occurrenceType` MUST be `S`
    # IF `occurrenceType` is `True` then `noEndDate` MUST be false

    bb_default_config = {
        # Session name {string} (must be provided)
        "name": None,
        #################
        # Event Details #
        #################
        # Guest access [True, False]
        "allowGuest": True,
        # Guest role ["participant", "presenter", "moderator"]
        "guestRole": "participant",
        # timestamp of the start of the *first* session {datetimestamp} (must be provided)
        "startTime": None,
        # timestamp of the end of the *first* session {datetimestamp} (must be provided)
        "endTime": None,
        # hidden, timestamp of when this session was created {datetimestamp} (used for ordering)
        "created": datestamp,
        # hidden, timestamp of when this session was last edited {datetimestamp}
        "modified": datestamp,
        # hidden, timezone for this sessions timestamps {datetimestamp}
        "createdTimezone": LOCAL_TIMEZONE,
        # No end (open session) [True, False]
        "noEndDate": False,
        # Repeat session ["S", "P"] S == single, P == ???
        "occurrenceType": None,
        # Configuration for when `occurrenceType` is `P`, Ignored if `occurrenceType` is `S`
        "recurrenceRule": {
            # Have a session every day or week or month ["daily", "weekly", "monthly"]
            "recurrenceType": "weekly",
            # Have a session every Nth day/week/month [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
            "interval": 1,
            # when to end the recurrence ["after_occurrences_count", "on_date"]
            "recurrenceEndType": None,
            # required if `recurrenceType` is `weekly`
            "daysOfTheWeek": None,
            # end the recurrence after this many sessions, required if `recurrenceEndType` is `after_occurrences_count` {integer}
            "numberOfOccurrences": None,
            # end the recurrence after this date, required if `recurrenceEndType` is `on_date` {datestamp}
            "endDate": None,
        },
        # Early Entry [0, 15, 30, 45, 60]
        "boundaryTime": 15,
        # Description {string}
        "description": "",
        ####################
        # Session Settings #
        ####################
        ### Default Attendee Role ###
        # Default Attendee Role ["participant", "presenter", "moderator"]
        "ltiParticipantRole": "participant",
        ### Recording ###
        # Allow recording downloads [True, False]
        "canDownloadRecording": True,
        # Anonymize chat messages [True, False]
        "anonymizeRecordings": False,
        ### Moderator permissions ###
        # Show profile pictures for moderator only [True, False]
        "showProfile": True,
        ### Participant permissions ###
        # hidden, if False pretend that the next four options are also all False [True, False]
        "participantCanUseTools": True,
        # Share audio [True, False]
        "canShareAudio": True,
        # Share video [True, False]
        "canShareVideo": True,
        # Post chat messages [True, False]
        "canPostMessage": True,
        # Draw on whiteboard and files [True, False]
        "canAnnotateWhiteboard": False,
        ### Enable session telephony ###
        # Allow attendees to join the session using a telephone [True, False]
        "telephonyEnabled": False,
        ### Private Chat ###
        # Participants can chat privately only with moderators [True, False]
        "privateChatRestricted": False,
        # Moderators supervise all private chats [True, False]
        "mustBeSupervised": False,
        ### Large scale session (250+) ###
        # Allow 250+ attendees to join [True, False]
        "largeSessionEnable": False,
        ### Profanity filter ###
        # Hide profanity in chat messages [True, False]
        "profanityFilterEnabled": True,
    }

    bb_session_config = update(update(dict(bb_default_config), parse_dict(bb_course_config)), parse_dict(bb_class_config))

    if "exclude" in bb_session_config:
        del bb_session_config["exclude"]

    if None in bb_session_config.values():
        raise ValueError(
            f"\
Some required filed are empty: \
{', '.join(map(lambda x: x[0], filter(lambda x: x[1] is None, bb_session_config.items())))}"
        )

    return bb_session_config


def create_bb_class(session: requests.Session, bb_course_config: dict, bb_class_config: dict) -> None:
    """
    :param session:
    :param bb_course_config:
    :param bb_class_config:
    :return:
    """

    print(f"Creating Class: {bb_class_config['name']}")
    class_json = bb_json_from_dict(bb_course_config, bb_class_config)

    r = session.post(BB_POST_URL, json=class_json)

    if not r.ok:
        print(r.status_code, r.reason)
        return

    if "guestUrl" in r.json():
        print(r.json()['guestUrl'])


def main() -> int:
    """
    :return:
    """

    args = parse_args()
    if args.debug: enable_logging()
    session = get_authed_session(args.token.read().strip() if args.token else input("BB Collaborate auth token: "))
    config = json_load(args.config_json)
    for bb_class in csv_dictreader(args.classes_csv, dialect="unix"):
        create_bb_class(session, config, bb_class)
        sleep(1)

    return 0


if __name__ == "__main__":
    exit(main())
