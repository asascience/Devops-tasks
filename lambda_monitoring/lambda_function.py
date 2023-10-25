import base64
import boto3
import gzip
import json
import logging
import os
import datetime


from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def logpayload(event):
    logger.setLevel(logging.DEBUG)
    logger.debug(event['awslogs']['data'])
    compressed_payload = base64.b64decode(event['awslogs']['data'])
    uncompressed_payload = gzip.decompress(compressed_payload)
    log_payload = json.loads(uncompressed_payload)
    return log_payload


def error_details(payload):
    error_msg = ""
    log_events = payload['logEvents']
    logger.debug(payload)
    loggroup = payload['logGroup']
    logstream = payload['logStream']
    lambda_func_name = loggroup.split('/')
    logger.debug(f'LogGroup: {loggroup}')
    logger.debug(f'Logstream: {logstream}')
    logger.debug(f'Function name: {lambda_func_name[3]}')
    logger.debug(log_events)
    for log_event in log_events:
        error_msg += log_event['message']
    logger.debug('Message: %s' % error_msg.split("\n"))
    return loggroup, logstream, error_msg, lambda_func_name
    
def wait_for_log_stream_creation(log_group_name, log_stream_name, max_wait_time_seconds=300):
    client = boto3.client('logs')
    start_time = time.time()
    
    while True:
        try:
            # Check if the log stream exists in the log group.
            response = client.describe_log_streams(
                logGroupName=log_group_name,
                logStreamNamePrefix=log_stream_name
            )
            if response['logStreams']:
                return  # Log stream exists, exit the loop
        except client.exceptions.ResourceNotFoundException:
            pass  # Log stream does not exist yet, continue waiting

        # Check if we have exceeded the maximum wait time.
        elapsed_time = time.time() - start_time
        if elapsed_time >= max_wait_time_seconds:
            return  # Exceeded maximum wait time, exit the loop

        # Wait for a short period before checking again.
        time.sleep(5)  # Adjust the sleep interval as needed

def check_message_exists(lambda_func_name,context):
    log_group_name = context.log_group_name
    log_stream_name = context.log_stream_name
    wait_for_log_stream_creation(log_group_name, log_stream_name, max_wait_time_seconds=300)
    try:
        client.describe_log_streams(
            logGroupName=log_group_name,
            logStreamNamePrefix=log_stream_name
        )
    except client.exceptions.ResourceNotFoundException:
        # The log stream doesn't exist, so there are no events to filter.
        return False
    client = boto3.client('logs')
    response = client.filter_log_events(
        logGroupName=log_group_name,
        logStreamNames=[log_stream_name],
        filterPattern=f'"{lambda_func_name}"',
    )
    for event in response['events']:
        timestamp = event['timestamp']
        current_time = datetime.datetime.now()
        montoring_time_span = current_time.timedelta(hours=1)
        log_event_time = datetime.datetime.fromtimestamp(timestamp/1000.0)
        time_difference = current_time - log_event_time
        if time_difference > montoring_time_span:
            return False
    
    return True
    
    
def publish_message(loggroup, logstream, error_msg, lambda_func_name,context):
    sns_arn = os.environ['snsARN']  # Getting the SNS Topic ARN passed in by the environment variables.
    snsclient = boto3.client('sns')
    try:
        #if not check_message_exists(lambda_func_name,context):
        message = ""
        message += "\nLambda error  summary" + "\n\n"
        message += "##########################################################\n"
        message += "# LogGroup Name:- " + str(loggroup) + "\n"
        message += "# LogStream:- " + str(logstream) + "\n"
        message += "# Log Message:- " + "\n"
        message += "# \t\t" + str(error_msg.split("\n")) + "\n"
        message += "##########################################################\n"

        # Sending the notification...
        snsclient.publish(
            TargetArn=sns_arn,
            Subject=f'Execution error for Lambda - {lambda_func_name[3]}',
            Message=message
        )
        #timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #log_message = f"{timestamp} - {lambda_func_name}"
        #log_message = f"{lambda_func_name}"
        #logging.info(log_message)
    except ClientError as e:
        logger.error("An error occured: %s" % e)


def lambda_handler(event, context):
    pload = logpayload(event)
    lgroup, lstream, errmessage, lambdaname = error_details(pload)
    publish_message(lgroup, lstream, errmessage, lambdaname,context)
    
        
        
    