# Email Agent Lambda Function

The Email Agent is responsible for distributing weekly newsletter emails to active subscribers. It retrieves subscriber lists from DynamoDB, loads weekly content from S3, formats emails using responsive templates, and sends them via Amazon SES with delivery tracking.

## Architecture

The Email Agent consists of four main components:

### 1. Subscriber Manager (`subscriber_manager.py`)
- Queries DynamoDB for active subscribers
- Filters and validates subscriber data
- Implements batch processing for large subscriber lists
- Provides subscriber statistics

### 2. Email Formatter (`email_formatter.py`)
- Renders responsive HTML email templates
- Generates plain text email fallbacks
- Creates personalized unsubscribe links with secure tokens
- Formats article content for email display

### 3. Email Sender (`email_sender.py`)
- Sends emails via Amazon SES
- Implements SES free tier compliance (200 emails/day limit)
- Handles bounce and complaint notifications
- Tracks delivery status and failures
- Respects rate limits (1 email/second)

### 4. Lambda Handler (`lambda_function.py`)
- Main entry point for Lambda execution
- Orchestrates the email distribution workflow
- Handles SNS notifications for bounces/complaints
- Provides comprehensive logging and error handling

## Features

### Subscriber List Management
- Retrieves only active subscribers from DynamoDB
- Validates email formats and subscriber status
- Filters out subscribers without unsubscribe tokens
- Organizes subscribers into batches (default: 50 per batch)

### Email Template System
- Responsive HTML design that works on mobile and desktop
- Clean, professional layout with proper styling
- Separate sections for Alzheimer's and Parkinson's content
- Article cards with title, source, date, and summary
- Personalized unsubscribe links for each subscriber
- Plain text fallback for email clients without HTML support

### SES Sending with Limits Compliance
- Respects SES free tier daily limit (200 emails/day)
- Implements rate limiting (1 email/second)
- Batch processing with delays between batches
- Automatic quota tracking and enforcement
- Graceful handling when limits are reached

### Delivery Tracking
- Tracks successful sends with SES message IDs
- Records failed sends with error details
- Provides detailed statistics on send results
- Logs all email operations for monitoring

### Bounce and Complaint Handling
- Processes SNS notifications for bounces
- Automatically unsubscribes permanent bounces
- Handles complaint notifications
- Unsubscribes users who mark emails as spam
- Logs all bounce/complaint events

## Environment Variables

The Lambda function requires the following environment variables:

- `CONTENT_BUCKET`: S3 bucket name for newsletter content (default: `alkinson-newsletter-content`)
- `SUBSCRIBERS_TABLE`: DynamoDB table name for subscribers (default: `alkinson-subscribers`)
- `SENDER_EMAIL`: Verified sender email address in SES (default: `newsletter@example.com`)
- `BASE_URL`: Base URL for unsubscribe links (default: `https://your-domain.com`)
- `AWS_REGION`: AWS region (default: `ap-southeast-2`)

## Usage

### Manual Invocation

Invoke the Lambda function to send the current week's newsletter:

```json
{}
```

Or specify a specific week:

```json
{
  "week_id": "2024-week-01"
}
```

### Automatic Invocation

The Email Agent is typically triggered automatically by the Content Agent after weekly content processing is complete.

### SNS Notification Handling

Configure SNS topics for SES bounce and complaint notifications to invoke the `handle_sns_notification` function.

## Response Format

### Successful Execution

```json
{
  "statusCode": 200,
  "body": {
    "message": "Email Agent completed successfully",
    "week_id": "2024-week-01",
    "send_results": {
      "total_subscribers": 150,
      "successful": 148,
      "failed": 2,
      "skipped": 0
    },
    "statistics": {
      "emails_sent_today": 148,
      "daily_limit": 200,
      "remaining_quota": 52,
      "total_errors": 2
    },
    "timestamp": "2024-01-07T10:30:00Z"
  }
}
```

### Error Response

```json
{
  "statusCode": 500,
  "body": {
    "error": "Error message",
    "error_type": "ExceptionType",
    "timestamp": "2024-01-07T10:30:00Z"
  }
}
```

## Dependencies

- `boto3>=1.28.0`: AWS SDK for Python
- `jinja2>=3.1.0`: Template engine for email rendering
- `pydantic>=2.0.0`: Data validation and models
- Shared utilities from `../shared/` package

## Deployment

### Package Lambda Function

```bash
cd alkinson-newsletter/lambda/email_agent
pip install -r requirements.txt -t .
zip -r email_agent.zip .
```

### Deploy via AWS CLI

```bash
aws lambda update-function-code \
  --function-name alkinson-email-agent \
  --zip-file fileb://email_agent.zip
```

### Deploy via CDK

The Email Agent is deployed as part of the CDK infrastructure stack.

## Monitoring

### CloudWatch Logs

All operations are logged to CloudWatch Logs with the following log levels:
- `INFO`: Normal operations, send statistics
- `WARNING`: Non-critical issues (invalid subscribers, rate limits)
- `ERROR`: Failed operations, exceptions

### CloudWatch Metrics

Monitor the following metrics:
- Lambda invocations and errors
- Lambda duration and memory usage
- SES send statistics (via SES console)
- DynamoDB read capacity usage

### Alarms

Set up CloudWatch alarms for:
- Lambda function errors
- SES bounce rate > 5%
- SES complaint rate > 0.1%
- Daily send limit approaching (> 180 emails)

## Testing

### Local Testing

```python
import json
from lambda_function import lambda_handler

# Test event
event = {
    "week_id": "2024-week-01"
}

# Invoke handler
result = lambda_handler(event, None)
print(json.dumps(result, indent=2))
```

### Integration Testing

1. Create test subscribers in DynamoDB
2. Upload test content to S3
3. Invoke Lambda function
4. Verify emails received
5. Test unsubscribe links
6. Verify bounce/complaint handling

## Security Considerations

- Email addresses are validated before sending
- Unsubscribe tokens are securely generated
- All email content is properly escaped
- SES sender email must be verified
- IAM roles follow least privilege principle
- Sensitive data is not logged

## Cost Optimization

- Uses SES free tier (200 emails/day)
- Implements batch processing to minimize Lambda invocations
- Efficient DynamoDB queries with filtering
- Minimal S3 operations (single content fetch per execution)
- Lambda memory optimized at 256 MB

## Troubleshooting

### No Emails Sent

- Check SES sender email is verified
- Verify subscribers exist in DynamoDB with `active` status
- Check weekly content exists in S3
- Review CloudWatch logs for errors

### Emails Not Received

- Check SES sending limits not exceeded
- Verify recipient email addresses are valid
- Check spam folders
- Review SES bounce/complaint notifications

### Rate Limit Errors

- Verify daily limit not exceeded (200 emails/day)
- Check rate limiting is enabled (1 email/second)
- Review send statistics in CloudWatch logs

## Future Enhancements

- Support for email personalization (subscriber name)
- A/B testing for email templates
- Email open and click tracking
- Retry logic for failed sends
- Support for email attachments
- Multi-language support
