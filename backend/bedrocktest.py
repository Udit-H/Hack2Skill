import boto3
import json
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

# 1. Force load the .env file from the current directory
load_dotenv()

# 2. Verify the keys are actually loaded before starting
if not os.getenv("AWS_ACCESS_KEY_ID"):
    print("❌ ERROR: Could not find AWS_ACCESS_KEY_ID in environment variables!")
else:
    # 3. Explicitly pass them to the client if the automatic search fails
    client = boto3.client(
        "bedrock-runtime",
        region_name="us-east-1",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )

# Initialize the Bedrock Runtime client
# It will automatically use the credentials in your .env or local AWS config
client = boto3.client("bedrock-runtime", region_name="us-east-1")

# The specific Inference Profile ID from your error message
MODEL_ID = "us.meta.llama3-2-90b-instruct-v1:0"

def test_connection():
    print(f"🚀 Testing connection to {MODEL_ID}...")
    
    messages = [{
        "role": "user",
        "content": [{"text": "Is the Sahayak_Dev user authorized to use Llama 3.2?"}]
    }]

    try:
        # Using the Converse API (Standard for 2026)
        response = client.converse(
            modelId=MODEL_ID,
            messages=messages,
            inferenceConfig={"maxTokens": 100, "temperature": 0.5}
        )
        
        output_text = response["output"]["message"]["content"][0]["text"]
        print("✅ SUCCESS! Response from Llama:")
        print(f"---\n{output_text}\n---")

    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ FAILED: {error_code}")
        print(f"Message: {e.response['Error']['Message']}")
        
        if error_code == 'AccessDeniedException':
            print("\n💡 TIP: Your IAM policy change might still be propagating. Wait 60 seconds and try again.")
        elif error_code == 'SubscriptionRequiredException':
            print("\n💡 TIP: You need to add the 'Marketplace' permissions I mentioned in the previous turn.")

if __name__ == "__main__":
    test_connection()