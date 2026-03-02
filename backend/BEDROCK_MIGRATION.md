# AWS Bedrock Migration Guide

## Overview
The system has been migrated from Google Gemini to **AWS Bedrock with Llama 4 Scout 17B** (90B parameter model).

## What Changed

### 1. LLM Provider
- **Before**: Google Gemini via OpenAI-compatible API
- **After**: AWS Bedrock with Meta Llama 3.2 models

### 2. Configuration Changes

#### Environment Variables
Update your `.env` file with these new variables:

```bash
# LLM Configuration
LLM_PROVIDER=bedrock
LLM_MODEL_ID=us.meta.llama3-2-90b-instruct-v1:0

# AWS Credentials (required for Bedrock)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
```

#### Available Llama Models on Bedrock:
- `us.meta.llama3-2-1b-instruct-v1:0` - 1B parameters (fastest)
- `us.meta.llama3-2-3b-instruct-v1:0` - 3B parameters
- `us.meta.llama3-2-11b-instruct-v1:0` - 11B parameters
- `us.meta.llama3-2-90b-instruct-v1:0` - 90B parameters (most capable) ✅ **Recommended**
- `meta.llama3-1-8b-instruct-v1:0` - 8B parameters
- `meta.llama3-1-70b-instruct-v1:0` - 70B parameters

### 3. Code Changes

#### New Files:
- `backend/core/bedrock_client.py` - Bedrock client wrapper with instructor support

#### Modified Files:
- `backend/config/config.py` - Updated LLMSettings for Bedrock
- `backend/agents/legal_agent.py` - Uses BedrockInstructorClient
- `backend/core/memory.py` - Uses BedrockAsyncClient for summarization
- `backend/.env.example` - Updated with Bedrock variables

## Setup Instructions

### 1. Install Dependencies
All required packages are already in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

**Option A: Environment Variables (Recommended for local dev)**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

**Option B: AWS Credentials File**
```bash
# ~/.aws/credentials
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
```

**Option C: IAM Role (For production on EC2/ECS/Lambda)**
No credentials needed - the role provides automatic access.

### 3. Enable Bedrock Model Access

1. Go to AWS Console → Amazon Bedrock
2. Navigate to "Model access" in the left sidebar
3. Request access to **Meta Llama 3.2 models**
4. Wait for approval (usually instant for most regions)

### 4. Update Your .env File
```bash
cp backend/.env.example backend/.env
# Edit .env with your AWS credentials and preferred model
```

### 5. Test the Integration
```bash
cd backend
python test_cli.py
```

## Cost Comparison

### Gemini Pricing:
- Gemini 2.5 Flash: $0.075 per 1M input tokens, $0.30 per 1M output tokens

### Bedrock Llama Pricing (us-east-1):
- Llama 3.2 1B: $0.10 per 1M input tokens, $0.10 per 1M output tokens
- Llama 3.2 3B: $0.15 per 1M input tokens, $0.15 per 1M output tokens
- Llama 3.2 11B: $0.35 per 1M input tokens, $0.35 per 1M output tokens
- Llama 3.2 90B: $2.00 per 1M input tokens, $2.00 per 1M output tokens

**Note**: Pricing varies by region. Check [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) for latest rates.

## Benefits

### Why Bedrock?
1. **Unified AWS Integration** - Same credentials for Textract OCR, S3, and LLM
2. **Better Security** - IAM-based access control, VPC integration
3. **Lower Latency** - Models run in your AWS region
4. **Enterprise Features** - Guardrails, model evaluation, fine-tuning support
5. **Multiple Model Options** - Easy to switch between Llama sizes based on cost/performance needs

### Why Llama 3.2 90B?
- Strong reasoning capabilities for legal document analysis
- Better at following structured output instructions
- Open-source model with known training data
- Excellent multilingual support (Hindi, Tamil, Bengali)

## Rollback Instructions

If you need to revert to Gemini:

1. Set in `.env`:
```bash
LLM_PROVIDER=openai
GEMINI_API_KEY=your_key
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

2. The code still supports OpenAI-compatible APIs as fallback.

## Troubleshooting

### Error: "Model access denied"
- Go to AWS Bedrock console and request model access
- Ensure your IAM user/role has `bedrock:InvokeModel` permission

### Error: "Region not supported"
- Llama models are available in: us-east-1, us-west-2, ap-southeast-1, eu-central-1
- Update `AWS_REGION` in your `.env` file

### Error: "Throttling exception"
- Bedrock has default quotas (tokens/minute)
- Request quota increase in AWS Service Quotas console

### JSON Parsing Errors
- The Bedrock client automatically strips markdown code blocks
- If errors persist, try the smaller Llama 11B model for faster iteration

## Support

For issues related to:
- **AWS Bedrock**: Check AWS Bedrock documentation
- **Model Performance**: Try different Llama model sizes
- **Integration Issues**: Review `backend/core/bedrock_client.py`
