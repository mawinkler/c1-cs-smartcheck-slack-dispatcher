import hmac
import logging
import json
import pprint
import requests
from json import dumps
from os import getenv
from pathlib import Path
from sys import stderr, exit
from flask import Flask, abort, request

# Read all the environment variables
SLACK_WEBHOOK_URL = getenv('SLACK_WEBHOOK_URL')
SLACK_CHANNEL = getenv('SLACK_CHANNEL')
DSSC_URL = "https://" + getenv('DSSC_URL')

logging.basicConfig(stream=stderr, level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_secret(name):
    """Tries to read Docker secret or corresponding environment variable.

    Returns:
        secret (str): Secret value.

    """
    secret_path = Path('/run/secrets/') / name

    try:
        with open(secret_path, 'r') as file_descriptor:
            # Several text editors add trailing newline which may cause troubles.
            # That's why we're trimming secrets' spaces here.
            return file_descriptor.read() \
                    .strip()
    except OSError as err:
        variable_name = name.upper()
        logging.debug(
            'Can\'t obtain secret %s via %s path. Will use %s environment variable.',
            name,
            secret_path,
            variable_name
        )
        return getenv(variable_name)

def handler(event):
    """Composes a Slack message containing brief information about the scan result.

    """
    # Read message
    flag = False
    if 'body' in event:
        jsonBody = json.loads(event['body'])
    else:
        jsonBody = event

    scan_status=jsonBody.get('scan', {}).get('status', {})
    logger.info("Scan status: " + str(scan_status))

    # if scan_status == "completed-with-findings":
    message = jsonBody['scan']['findings']['vulnerabilities']
    logger.info("Message: " + str(message))
    notification_output = "Trend Micro has found "

    # detect vulnerability and render dynamic message output in slack
    if 'high' in message['total']:
        notification_output += str(message['total']['high']) + " high vulnerabilities, "
        flag = True
    if 'medium' in message['total']:
        notification_output += str(message['total']['medium']) + " medium vulnerabilities, "
        flag = True
    if 'low' in message['total']:
        notification_output += str(message['total']['low']) + " Low vulnerabilities "
        flag = True
    if 'unknown' in message['total']:
        notification_output += ", " + str(message['total']['unknown']) + " unknown vulnerabilities "
        flag = True
    if 'negligible' in message['total']:
        notification_output += ", " + str(message['total']['negligible']) + " negligible vulnerabilities "
        flag = True
    if 'defcon1' in message['total']:
        notification_output += ", " + str(message['total']['defcon1']) + " Critical vulnerabilities that requires your immidiate attention to fix. "
        flag = True
    if not flag:
        notification_output += " no vulnerabilities. "

    # Detect malware and render dynamic message output in slack
    if 'malware' in jsonBody['scan']['findings']:
        if int(jsonBody['scan']['findings']['malware']) > 0:
            notification_output += str(jsonBody['scan']['findings']['malware']) + " potential malicious payload "
            flag = True

    # Detect secrets stored in scanned image and render text message output
    if 'contents' in jsonBody['scan']['findings']:
        if 'high' in jsonBody['scan']['findings']['contents']['total']:
            notification_output += str(
                jsonBody['scan']['findings']['contents']['total']['high']) + " high risk content or secrets "
            flag = True
    # Identify PCI-DSS, HIPPA, and NIST compliance violations
    if 'checklists' in jsonBody['scan']['findings']:
        total_violation = 0
        if 'high' in jsonBody['scan']['findings']['checklists']['total']:
            total_violation += int(jsonBody['scan']['findings']['checklists']['total']['high'])

        if 'medium' in jsonBody['scan']['findings']['checklists']['total']:
            total_violation += int(jsonBody['scan']['findings']['checklists']['total']['medium'])

        if 'low' in jsonBody['scan']['findings']['checklists']['total']:
            total_violation += int(jsonBody['scan']['findings']['checklists']['total']['low'])

        if total_violation != 0:
            flag = True
            notification_output += "and, " + str(
                total_violation) + " total compliance checklist violations in PCI-DSS, HIPPA, and NIST"

    if 'registry' in jsonBody['scan']['source']:
        scan_ui_path = DSSC_URL + str(jsonBody['scan']['href']).replace('/api/', '/')
        scan_image_name = str(jsonBody['scan']['source']['registry']) + "/" + str(jsonBody['scan']['source']['repository']) + ":" + str(jsonBody['scan']['source']['tag'])
        notification_output += " in " + scan_image_name + " image scan. For more details log in to DSSC console by visiting " + scan_ui_path
    elif 'url' in jsonBody['scan']['source']:
        malicious_file_path = str(jsonBody['scan']['source']['url']).split("?", 1)[0]
        notification_output += "uploaded from application to AWS S3 bucket. We recommend you to verify uploaded object and delete from S3 bucket. Object Details: " + malicious_file_path
    else:
        notification_output += "Seems like unknown object got scanned that is not covered in this automation. Kindly contact trend micro support to get it fixed."

    if flag:
        # Construct a new slack message
        slack_message = {
            'channel': '#' + SLACK_CHANNEL,
            'text': "%s" % (notification_output),
            "icon_url": "https://aws-code-bucket-tejas.s3.us-east-2.amazonaws.com/Picture1.png"
        }
        # Post message on SLACK_WEBHOOK_URL
        try:
            response = requests.post(SLACK_WEBHOOK_URL, data=json.dumps(slack_message))
            logger.info("Response: %s", response)
            logger.info("Message posted to %s", slack_message['channel'])
        except requests.exceptions.Timeout as e:
            logger.error("Server connection failed: %s", e.reason)
        except requests.exceptions.HTTPError as e:
            logger.error("Request failed: %d %s", e.code, e.reason)


# Get application secret
webhook_secret = get_secret('webhook_secret')
if webhook_secret is None:
    logging.error("Must define WEBHOOK_SECRET")
    exit(1)

# Application
application = Flask(__name__)


@application.route('/', methods=['POST'])
def index():
    """We got called! Verify signature and pass to handler.

    """
    global webhook_secret, responses

    header_signature = request.headers.get('X-Scan-Event-Signature')
    if header_signature is not None:
        # Construct an hmac, abort if it doesn't match
        try:
            sha_name="sha256"
            signature = header_signature
        except:
            logging.info("X-Scan-Event-Signature format is incorrect (%s), aborting", header_signature)
            abort(400)
        data = request.get_data()
        try:
            mac = hmac.new(webhook_secret.encode('utf8'), msg=data, digestmod=sha_name)
        except:
            logging.info("Unsupported X-Scan-Event-Signature type (%s), aborting", header_signature)
            abort(400)
        if not hmac.compare_digest(str(mac.hexdigest()), str(signature)):
            logging.info("Signature did not match (%s and %s), aborting", str(mac.hexdigest()), str(signature))
            abort(403)
    else:
        logging.info("X-Scan-Event-Signature was missing, aborting")
        abort(403)

    data = request.get_data()
    
    # dssc_json=json.loads(data.decode('utf8').replace("'", '"'))
    dssc_json=json.loads(data.decode('utf8'))
    handler(dssc_json)

# Run the application
if __name__ == '__main__':
    logging.info("All systems operational, beginning application loop")
    application.run(debug=False, host='0.0.0.0', port=8000)
