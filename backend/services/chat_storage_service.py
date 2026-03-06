"""
DynamoDB Chat Storage Service
------------------------------
Persists all chat messages to DynamoDB for audit, analytics, and session recovery.
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
import boto3
from botocore.exceptions import ClientError

from config.config import Settings

logging.basicConfig(level=logging.INFO)


class ChatStorageService:
    """Manages chat message persistence in DynamoDB."""
    
    def __init__(self):
        settings = Settings()
        
        # Initialize DynamoDB client
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=settings.llm.aws_region,
            aws_access_key_id=settings.llm.aws_access_key_id,
            aws_secret_access_key=settings.llm.aws_secret_access_key,
        )
        
        # Table name from env or default
        import os
        self.table_name = os.getenv("DYNAMODB_CHAT_TABLE", "sahayak-chat-messages")
        self.table = self.dynamodb.Table(self.table_name)
        
        logging.info(f"✅ ChatStorageService initialized with table: {self.table_name}")
    
    async def save_message(
        self,
        session_id: str,
        role: str,  # 'user' or 'assistant'
        content: str,
        agent_type: Optional[str] = None,
        metadata: Optional[Dict] = None,
        user_id: Optional[str] = None,  # User email/phone for session grouping
    ) -> bool:
        """
        Save a single chat message to DynamoDB.
        
        Args:
            session_id: Unique session identifier
            role: 'user' or 'assistant'
            content: Message text
            agent_type: Active agent when message was sent (optional)
            metadata: Additional metadata (progress_status, error_message, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            
            item = {
                'session_id': session_id,
                'timestamp': timestamp,
                'role': role,
                'content': content,
            }
            
            if agent_type:
                item['agent_type'] = agent_type
            
            if metadata:
                item['metadata'] = metadata
            
            if user_id:
                item['user_id'] = user_id
            
            self.table.put_item(Item=item)
            logging.info(f"💾 Saved {role} message for session {session_id}")
            return True
            
        except ClientError as e:
            logging.error(f"❌ DynamoDB write error: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            logging.error(f"❌ Unexpected error saving message: {str(e)}")
            return False
    
    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Retrieve chat history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve (default 50)
        
        Returns:
            List of message dicts sorted by timestamp ascending (oldest first)
        """
        try:
            response = self.table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('session_id').eq(session_id),
                Limit=limit,
                ScanIndexForward=True,  # Sort ascending by timestamp
            )
            
            messages = response.get('Items', [])
            logging.info(f"📖 Retrieved {len(messages)} messages for session {session_id}")
            return messages
            
        except ClientError as e:
            logging.error(f"❌ DynamoDB read error: {e.response['Error']['Message']}")
            return []
        except Exception as e:
            logging.error(f"❌ Unexpected error retrieving history: {str(e)}")
            return []
    
    async def delete_session_history(self, session_id: str) -> bool:
        """
        Delete all messages for a session (for panic wipe).
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if successful
        """
        try:
            # Query all messages for the session
            response = self.table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('session_id').eq(session_id),
            )
            
            # Batch delete
            with self.table.batch_writer() as batch:
                for item in response.get('Items', []):
                    batch.delete_item(
                        Key={
                            'session_id': item['session_id'],
                            'timestamp': item['timestamp'],
                        }
                    )
            
            logging.info(f"🗑️  Deleted chat history for session {session_id}")
            return True
            
        except ClientError as e:
            logging.error(f"❌ DynamoDB delete error: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            logging.error(f"❌ Unexpected error deleting history: {str(e)}")
            return False
    
    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict]:
        """
        List all sessions for a user with preview of last message.
        
        Args:
            user_id: User identifier (email or phone)
            limit: Maximum number of sessions to return
        
        Returns:
            List of session summaries with last message preview
        """
        try:
            # Use GSI to query by user_id (requires GSI setup)
            # For now, we'll scan (not ideal for production but works for MVP)
            response = self.table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('user_id').eq(user_id),
                Limit=limit * 10,  # Get more to account for multiple messages per session
            )
            
            # Group messages by session_id and get last message for each
            sessions_map = {}
            for item in response.get('Items', []):
                sid = item['session_id']
                if sid not in sessions_map:
                    sessions_map[sid] = {
                        'session_id': sid,
                        'last_message': item['content'][:100],
                        'last_timestamp': item['timestamp'],
                        'message_count': 1,
                    }
                else:
                    sessions_map[sid]['message_count'] += 1
                    # Keep the most recent message
                    if item['timestamp'] > sessions_map[sid]['last_timestamp']:
                        sessions_map[sid]['last_message'] = item['content'][:100]
                        sessions_map[sid]['last_timestamp'] = item['timestamp']
            
            # Convert to list and sort by last activity
            sessions = sorted(
                sessions_map.values(),
                key=lambda x: x['last_timestamp'],
                reverse=True
            )[:limit]
            
            logging.info(f"📋 Listed {len(sessions)} sessions for user {user_id}")
            return sessions
            
        except ClientError as e:
            logging.error(f"❌ DynamoDB scan error: {e.response['Error']['Message']}")
            return []
        except Exception as e:
            logging.error(f"❌ Unexpected error listing sessions: {str(e)}")
            return []
    
    def create_table_if_not_exists(self):
        """
        Create the DynamoDB table if it doesn't exist.
        Use this during initial setup or deployment.
        
        Table Schema:
        - Partition Key: session_id (String)
        - Sort Key: timestamp (String - ISO 8601 format)
        - Attributes: role, content, agent_type, metadata
        """
        try:
            self.table.load()
            logging.info(f"✅ Table {self.table_name} already exists")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logging.info(f"📋 Creating table {self.table_name}...")
                
                table = self.dynamodb.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {'AttributeName': 'session_id', 'KeyType': 'HASH'},  # Partition key
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'},  # Sort key
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'session_id', 'AttributeType': 'S'},
                        {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                    ],
                    BillingMode='PAY_PER_REQUEST',  # On-demand pricing (no capacity planning needed)
                )
                
                # Wait for table to be created
                table.wait_until_exists()
                logging.info(f"✅ Table {self.table_name} created successfully")
                return True
            else:
                logging.error(f"❌ Error checking table: {e.response['Error']['Message']}")
                return False
