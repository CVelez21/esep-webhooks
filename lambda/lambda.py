# =============================================================================
# @file        lambda.py
# @brief       GitHub Issues → API Gateway → Lambda → Slack webhook bridge
# @author      Chris Velez-Ramirez
# @date        November 10th, 2025
#
# @overview
#   This AWS Lambda receives a GitHub "issues" webhook via API Gateway.
#   It extracts the issue's HTML URL(issue.html_url), and posts a message to
#   Slack using a webhook URL stored in the Lambda environment variable SLACK_URL.
#
# @parameters (for lambda_handler)
#   event   : Incoming payload. When called via API Gateway (proxy integration),
#             this is typically a dict with "headers" and a JSON-string "body".
#
#   context : Lambda runtime context object (unused, passed through).
#
# @returns
#   dict : API Gateway–compatible response with keys:
#          - statusCode (int)
#          - body (str JSON) containing:
#              message              : "success"
#              issueUrl             : Extracted HTML URL for the created issue
#              connectedToSlack     : True if Slack URL was configured
# =============================================================================

import os                                       # Accessing SLACK_URL from environment variables
import json                                     # Parsing incoming JSON data and building Slack message payloads
from urllib.request import Request, urlopen     # Sending HTTP requests to Slack webhook URL
from urllib.error import URLError, HTTPError    # Handling HTTP errors when sending requests to Slack



def lambda_handler(event, context):

    # -------------------------------------------------------------------------
    # Read the Slack webhook URL from the environment variable
    # -------------------------------------------------------------------------
    slack_url = os.getenv("SLACK_URL")

    # -------------------------------------------------------------------------
    # If no Slack URL is set, log a warning and continue
    # -------------------------------------------------------------------------
    if not slack_url:
        print("[EsepWebhook] SLACK_URL not set in environment variables.")

    # -------------------------------------------------------------------------
    # Extract the body from the event if invoked through API Gateway
    # -------------------------------------------------------------------------
    if isinstance(event, dict) and "body" in event:
        body = event["body"]
    else:
        body = event

    # -------------------------------------------------------------------------
    # Try to parse the incoming body as JSON
    # -------------------------------------------------------------------------
    try:
        payload = json.loads(body)
    except Exception:
        # If not valid JSON, wrap it into a dictionary for safety
        payload = {"raw": body}

    # -------------------------------------------------------------------------
    # Attempt to extract the issue's HTML URL from the GitHub payload
    # -------------------------------------------------------------------------
    issue_url = None

    if "issue" in payload and isinstance(payload["issue"], dict):
        issue_url = payload["issue"].get("html_url")

    # -------------------------------------------------------------------------
    # If an issue URL exists and Slack is configured, send it to Slack
    # -------------------------------------------------------------------------
    if issue_url and slack_url:

        # Create a Slack-formatted message
        message = {"text": f":tada: New GitHub Issue created: {issue_url}"}

        # Convert message to bytes
        data = json.dumps(message).encode("utf-8")

        # Create an HTTPS POST request to the Slack webhook URL
        request = Request(slack_url, data=data, headers={"Content-Type": "application/json"})

        try:
            # Send the message to Slack
            with urlopen(request) as response:
                print(f"[EsepWebhook] Message posted to Slack. Status: {response.status}")
        except HTTPError as e:
            print(f"[EsepWebhook] Slack HTTPError {e.code}: {e.reason}")
        except URLError as e:
            print(f"[EsepWebhook] Slack URLError: {e.reason}")

    elif issue_url:
        # Slack URL missing but issue URL was found
        print("[EsepWebhook] IssueURL detected but SLACK_URL not configured.")

    else:
        # No issue URL found, likely not an "issues" event
        print("[EsepWebhook] No issueURL found in payload.")

    # -------------------------------------------------------------------------
    # Return a success response to API Gateway / GitHub
    # -------------------------------------------------------------------------
    response_body = {
        "message": "success",
        "issueUrl": issue_url,
        'connectedToSlack': bool(slack_url)
    }

    return {
        "statusCode": 200,
        "body": json.dumps(response_body)
    }