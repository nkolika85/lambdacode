import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Received event: " + json.dumps(event))
   
    # Extract relevant information from the AWS Config event
    invoking_event = json.loads(event['invokingEvent'])
    account_id = event['accountId']
    region = event['configRuleArn'].split(":")[3]
    resource_type = invoking_event['configurationItem']['resourceType']
    resource_id = invoking_event['configurationItem']['resourceId']
    creation_date = invoking_event['configurationItem']['configurationItemCaptureTime']
    tags = invoking_event['configurationItem'].get('tags', {})
   
    logger.info(f"Account ID: {account_id}, Region: {region}, Resource Type: {resource_type}, Resource ID: {resource_id}, Tags: {tags}, Creation Date: {creation_date}")
   
    # Initialize the compliance status
    compliance_status = 'NON_COMPLIANT'

    # Check for non-compliance
    non_compliant_resources = []
    if not tags or not any(any(domain in value.lower() for domain in ['@yahoo.com', '@gmail.com', '@ymail.com']) for value in tags.values()):
        non_compliant_resources.append({
            'AccountId': account_id,
            'Region': region,
            'ResourceType': resource_type,
            'ResourceId': resource_id,
            'CreationDate': creation_date,
            'ComplianceStatus': compliance_status
        })

    if non_compliant_resources:
        # Send email with non-compliant resources
        smtp_server = 'your_smtp_server_ip'
        smtp_port = 25  # or your SMTP port
        sender_email = 'your_sender_email@example.com'
        receiver_email = 'your_receiver_email@example.com'
        subject = 'Non-compliant AWS Resources Report'
        
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = receiver_email
        message['Subject'] = subject
        
        body = "\n".join([f"{key}: {value}" for key, value in non_compliant_resources[0].items()])
        message.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.sendmail(sender_email, receiver_email, message.as_string())
        
        logger.info("Sent email with non-compliant resources.")
    
    else:
        logger.info("All resources are compliant or no resources to evaluate.")

    # Report evaluation result to AWS Config
    config_client = boto3.client('config')
    evaluations = [{
        'ComplianceResourceType': resource_type,
        'ComplianceResourceId': resource_id,
        'ComplianceType': compliance_status,
        'Annotation': 'Resource is not tagged with a valid email address.',
        'OrderingTimestamp': creation_date  # Use the creation date for OrderingTimestamp
    } for resource in non_compliant_resources]
    response = config_client.put_evaluations(
        Evaluations=evaluations,
        ResultToken=event['resultToken']
    )

    return {"message": "Execution completed"}
