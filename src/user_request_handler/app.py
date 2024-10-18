# src/user_request_handler/app.py

import json
from common import utils

def lambda_handler(event, context):
    """
    Main Lambda handler function.
    Routes requests based on HTTP method and path.
    """
    # Extract HTTP method and path from the event
    http_method = event.get('httpMethod')
    path = event.get('path')

    if http_method == 'POST' and path == '/submitanewrequest':
        return utils.submit_new_request(event, context)
    elif http_method == 'GET' and path == '/listrequests':
        return utils.list_requests(event)
    elif http_method == 'DELETE' and path == '/deletearequest':
        return utils.delete_request(event)
    elif http_method == 'PUT' and path == '/update':
        return utils.update_request(event)
    else:
        return utils.respond(404, {'message': 'Not Found'})
