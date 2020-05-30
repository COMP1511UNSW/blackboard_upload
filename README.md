# Blackboard Collaborate Uploader

This is a small utilty to upload a list of classes to Blackboard Collaborate.

## Usage Reference

```
usage: blackboard_generate.py [-h] [-d] classes_csv token

Upload classes to Blackboard Collaborate

positional arguments:
  classes_csv  csv file containing classes
  token        Your auth token for BB Collaborate.

optional arguments:
  -h, --help   show this help message and exit
  -d, --debug  Turn on debug logging

```

Where `classes_csv` is a path to a CSV in the requisite format
(see `examples/classes.csv`), and `token` is the Bearer token
given to you by Blackboard Collaborate.

Note that this script has a shebang line to use cs1511's python3
distribution on CSE systems. We recommend you use the script on 
CSE systems, since that python3 is guaranteed to have the 
correct packages installed.


### Classes CSV

The classes CSV contains the list of classes you want to upload, with the following columns:

 - `name` (string) - the name of the class
 - `start` (datestamp) - the start date/time of the *first* class, in `LOCAL_TIMEZONE`
 (as defined by the global variable in `blackboard_generate.py`, currently "Australia/Sydney" )
 - `end` (datestamp) - the end date/time of the *first* class, in `LOCAL_TIMEZONE`
 (this should be on the same day as `start`).
 - `recurr` (int) - the number of times the class will occur
 
## Instructions

1. Copy the file `examples/session.csv` somewhere, and edit it to contain the relevant detialas
2. Login to BB Collaborate (via Moodle)
3. Open your developer tools (usually, right click on the page, choose "Inspect Element")
4. Go to the "Console" tab of your developer tools
5. Find the message "LaunchParams loaded parameters:", and copy the value of "tokens" (this will be a long base64 string, with some dots in the middle. Copy everything inside the quotes.)
6. Run the script provided in this repo, with the command `./blackboard_generate.py <your_session_csv>.csv <the_token_you_copied>`

## TODO

 - Get the tool to automatically remove flexibility week.
 - More precise control over weeks, for things like public holidays.
