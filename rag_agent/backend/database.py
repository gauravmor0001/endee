import sqlite3
import bcrypt
import uuid
from datetime import datetime
import json
import os

class UserDatabase:
    def __init__(self, db_path=None):
        if db_path is None:
            # This automatically finds the 'data/users.db' folder next to this file
            self.db_path = os.path.join(os.path.dirname(__file__), "data", "users.db")
        else:
            self.db_path = db_path
            
        # Create the 'data' folder if it doesn't exist yet
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.init_database()
    
    def init_database(self):
        conn=sqlite3.connect(self.db_path)
        cursor=conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                messages TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        conn.commit()
        conn.close()

    def create_user(self,username,password):
        try:
            conn=sqlite3.connect(self.db_path)
            cursor=conn.cursor()

            cursor.execute("SELECT id FROM users WHERE username= ?",(username,))
            if cursor.fetchone(): #check we something is returned
                conn.close()
                return False, "Username already exists", None
            
            user_id=str(uuid.uuid4())

            password_hash=bcrypt.hashpw(password.encode('utf-8'),bcrypt.gensalt())
            # password.encode convert string into bytes,bcrypt needs bytes

            cursor.execute('''
                INSERT INTO users (id, username, password_hash, created_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, password_hash, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()

            print(f"✅ User created: {username} (ID: {user_id})")
            return True, "User created successfully", user_id
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return False, f"Error: {str(e)}", None
            
    def verify_user(self, username, password):
        """..."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find user by username
            cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            
            conn.close()
            
            if not result:
                return False, "Invalid username or password", None
            
            user_id, stored_hash = result

            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                print(f"✅ User logged in: {username}")
                return True, "Login successful", user_id
            else:
                return False, "Invalid username or password", None
            
        except Exception as e:
            print(f"❌ Error fetching user: {e}")
            return None
        
    def get_user_by_id(self, user_id):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                return result[0]
            return None
            
        except Exception as e:
            print(f"❌ Error fetching user: {e}")
            return None
        
    def create_conversation(self, user_id, title="New Chat"):
        try:
            conn=sqlite3.connect(self.db_path)
            cursor=conn.cursor()

            conv_id=str(uuid.uuid4())
            now=datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO conversations(id, user_id,title,created_At,updated_At,messages)
                VALUES(?,?,?,?,?,?)
            ''',(conv_id,user_id,title,now,now,json.dumps([])))
            
            conn.commit()
            conn.close()

            return conv_id
        except Exception as e:
            print(f"❌ Error creating conversation: {e}")
            return None
        
    
    def get_conversations(self, user_id):
        """Get all conversations for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE user_id = ?
                ORDER BY updated_at DESC
            ''', (user_id,))
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    "id": row[0],
                    "title": row[1],
                    "created_at": row[2],
                    "updated_at": row[3]
                })
            
            conn.close()
            return conversations
        except Exception as e:
            print(f"❌ Error fetching conversation: {e}")
            return None
    def get_conversation(self, conv_id, user_id):
        """Get a specific conversation with messages"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, created_at, updated_at, messages
                FROM conversations
                WHERE id = ? AND user_id = ?
            ''', (conv_id, user_id))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    "id": result[0],
                    "title": result[1],
                    "created_at": result[2],
                    "updated_at": result[3],
                    "messages": json.loads(result[4])
                }
            return None
            
        except Exception as e:
            print(f"❌ Error fetching conversation: {e}")
            return None
        
    def add_message_to_conversation(self, conv_id, user_id, user_msg, bot_msg):
        """Add a message pair to a conversation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current messages
            cursor.execute('SELECT messages, title FROM conversations WHERE id = ? AND user_id = ?', 
                         (conv_id, user_id))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return False
            
            messages = json.loads(result[0])
            current_title = result[1]
            
            # Add new messages
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": bot_msg})
            
            # Auto-generate title from first message if still "New Chat"
            new_title = current_title
            if current_title == "New Chat" and len(messages) == 2:
                # Use first 50 chars of user's first message as title
                new_title = user_msg[:50] + ("..." if len(user_msg) > 50 else "")
            
            # Update conversation
            cursor.execute('''
                UPDATE conversations
                SET messages = ?, updated_at = ?, title = ?
                WHERE id = ? AND user_id = ?
            ''', (json.dumps(messages), datetime.now().isoformat(), new_title, conv_id, user_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error adding message: {e}")
            return False
    
    def delete_conversation(self, conv_id, user_id):
        """Delete a conversation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM conversations WHERE id = ? AND user_id = ?', 
                         (conv_id, user_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error deleting conversation: {e}")
            return False
            