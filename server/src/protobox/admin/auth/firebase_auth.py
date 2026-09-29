"""
Firebase token validation for authentication exchange.

This module handles Firebase ID token validation and exchange for custom JWTs.
Firebase is only used for initial authentication - all subsequent operations
use our custom JWTs.
"""

import json
import os
from datetime import datetime
from typing import Any

import firebase_admin
from firebase_admin import auth, credentials
from loguru import logger
from pydantic import BaseModel

from ..config import settings
from .jwt_auth import JWTAuth


class FirebaseUser(BaseModel):
    """Firebase user information extracted from ID token."""

    uid: str
    email: str | None = None
    email_verified: bool = False
    name: str | None = None
    picture: str | None = None
    provider_id: str | None = None


class FirebaseTokenExchangeRequest(BaseModel):
    """Request model for Firebase token exchange."""

    firebase_token: str


class TokenExchangeResponse(BaseModel):
    """Response model for token exchange."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # 1 hour for access token
    user: dict[str, Any]


class FirebaseAuth:
    """
    Firebase ID token validation for authentication exchange.

    This class ONLY validates Firebase tokens during the exchange process.
    All subsequent authentication uses our custom JWTs.
    """

    def __init__(
        self, project_id: str | None = None, verify_exp: bool = True, verify_iat: bool = True
    ):
        self.project_id = project_id or settings.firebase_project_id
        self.verify_exp = verify_exp
        self.verify_iat = verify_iat

        # Check if we're using Firebase emulator
        self.use_emulator = settings.use_firebase_emulator
        self.emulator_host = settings.firebase_auth_emulator_host

        # Initialize Firebase Admin SDK if not already initialized
        if not firebase_admin._apps:
            try:
                # Check if we're using emulator (Firebase Admin SDK auto-detects from env var)
                if os.getenv("FIREBASE_AUTH_EMULATOR_HOST"):
                    logger.info(
                        f"🔥 Using Firebase Auth Emulator at {os.getenv('FIREBASE_AUTH_EMULATOR_HOST')}"
                    )
                    # For emulator, we just need project ID
                    if self.project_id:
                        firebase_admin.initialize_app(options={"projectId": self.project_id})
                    else:
                        firebase_admin.initialize_app()
                    logger.info("Firebase Admin SDK initialized for emulator")
                else:
                    # Production/staging initialization with credentials
                    # Try to use service account credentials from environment
                    service_account_json = settings.firebase_service_account_key
                    if service_account_json:
                        # Replace escaped newlines with actual newlines in private key
                        service_account_json = service_account_json.replace("\\\\n", "\\n")
                        service_account_info = json.loads(service_account_json)
                        cred = credentials.Certificate(service_account_info)
                        firebase_admin.initialize_app(cred)
                        logger.info("Firebase Admin SDK initialized with service account from env")
                    else:
                        # Try to use service account from file
                        service_account_path = settings.firebase_service_account_path
                        if service_account_path and os.path.exists(service_account_path):
                            cred = credentials.Certificate(service_account_path)
                            firebase_admin.initialize_app(cred)
                            logger.info(
                                "Firebase Admin SDK initialized with service account from file"
                            )
                        elif self.project_id:
                            # Initialize with project ID only (will use ADC or fetch public keys)
                            firebase_admin.initialize_app(options={"projectId": self.project_id})
                            logger.info(
                                f"Firebase Admin SDK initialized for project: {self.project_id}"
                            )
                        else:
                            # Try default initialization
                            firebase_admin.initialize_app()
                            logger.info("Firebase Admin SDK initialized with default credentials")
            except Exception as e:
                logger.warning(f"Could not initialize Firebase Admin SDK: {e}")

        if self.use_emulator:
            logger.info(f"Using Firebase Auth Emulator at {self.emulator_host}")
            # Set emulator environment variable for firebase-admin
            os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = self.emulator_host
        elif not self.project_id:
            logger.warning("FIREBASE_PROJECT_ID not set - Firebase auth will not work")

    async def verify_firebase_token(self, token: str) -> FirebaseUser | None:
        """
        Verify a Firebase ID token and extract user information.

        Args:
            token: Firebase ID token

        Returns:
            FirebaseUser if valid, None if invalid
        """
        # Only use Firebase ID token validation - no test tokens

        try:
            # Use firebase-admin SDK to verify the token
            decoded_token = auth.verify_id_token(
                token, check_revoked=False  # Set to True if you want to check for revoked tokens
            )

            # Extract user information from the decoded token
            user = FirebaseUser(
                uid=decoded_token.get("uid"),
                email=decoded_token.get("email"),
                email_verified=decoded_token.get("email_verified", False),
                name=decoded_token.get("name") or decoded_token.get("display_name"),
                picture=decoded_token.get("picture"),
                provider_id=decoded_token.get("firebase", {}).get("sign_in_provider", "password"),
            )

            logger.info(f"Firebase token verified for user: {user.email}")
            return user

        except auth.ExpiredIdTokenError:
            logger.warning("Firebase token has expired")
            return None
        except auth.RevokedIdTokenError:
            logger.warning("Firebase token has been revoked")
            return None
        except auth.InvalidIdTokenError as e:
            logger.warning(f"Invalid Firebase token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying Firebase token: {e}")
            return None

    async def exchange_token(
        self, firebase_token: str, jwt_auth: JWTAuth, db=None
    ) -> TokenExchangeResponse | None:
        """
        Exchange a Firebase ID token for custom JWT tokens.

        Args:
            firebase_token: Firebase ID token
            jwt_auth: JWT auth instance for creating tokens
            db: Database connection (optional, will be fetched if not provided)

        Returns:
            TokenExchangeResponse with access and refresh tokens
        """
        # Always use Firebase token verification
        firebase_user = await self.verify_firebase_token(firebase_token)
        if not firebase_user:
            return None

        # Create or update user in MongoDB
        if db is None:
            from ..database.connection import get_database_connection

            db_conn = get_database_connection()
            db = db_conn.database

        users_collection = db.users

        # Use find_one_and_update for atomic operation

        user_doc = await users_collection.find_one_and_update(
            {"firebase_uid": firebase_user.uid},
            {
                "$set": {
                    "email": firebase_user.email,
                    "displayName": firebase_user.name or (firebase_user.email.split("@")[0] if firebase_user.email else f"user-{firebase_user.uid}"),
                    "email_verified": firebase_user.email_verified,
                    "last_login": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                },
                "$setOnInsert": {
                    "firebase_uid": firebase_user.uid,
                    "created_at": datetime.utcnow(),
                    "workspaces": [],
                    "preferences": {
                        "theme": "light",
                        "language": "en",
                        "timezone": "UTC",
                        "email_notifications": True,
                        "last_workspace_id": None,
                    },
                },
            },
            upsert=True,
            return_document=True,  # Return the document after update
        )

        # Get user's workspaces from the workspaces collection
        workspaces_collection = db.workspaces
        workspace_id = None

        # Check if user has workspaces in their document
        user_workspace_ids = user_doc.get("workspaces", [])

        if user_workspace_ids:
            # User has workspace IDs, get the actual workspace
            # Use the last workspace or first available
            last_workspace_id = user_doc.get("preferences", {}).get("last_workspace_id")

            if last_workspace_id:
                # Try to use the last workspace if it exists
                workspace = await workspaces_collection.find_one({"_id": last_workspace_id})
                if workspace:
                    workspace_id = str(workspace["_id"])

            if not workspace_id and user_workspace_ids:
                # Fall back to first workspace
                first_workspace_id = user_workspace_ids[0]
                workspace = await workspaces_collection.find_one({"_id": first_workspace_id})
                if workspace:
                    workspace_id = str(workspace["_id"])
        else:
            # User has no workspaces, check if they're a member of any workspace
            # IMPORTANT: Use MongoDB user ID to check membership, not Firebase UID
            mongodb_user_id = str(user_doc["_id"])
            workspace = await workspaces_collection.find_one({"members.user_id": mongodb_user_id})

            if workspace:
                workspace_id = str(workspace["_id"])
                # Add workspace to user's list
                await users_collection.update_one(
                    {"firebase_uid": firebase_user.uid},
                    {
                        "$addToSet": {"workspaces": workspace["_id"]},
                        "$set": {"preferences.last_workspace_id": workspace["_id"]},
                    },
                )

        if not workspace_id:
            # Create a new workspace for the user
            from bson import ObjectId

            workspace_object_id = ObjectId()
            # CRITICAL: Use MongoDB user ID as owner_id, NOT Firebase UID
            # Firebase UIDs should only be used at token exchange time
            mongodb_user_id = str(user_doc["_id"])
            new_workspace = {
                "_id": workspace_object_id,
                "workspace_id": str(workspace_object_id),  # Add workspace_id field to avoid null duplicate key error
                "name": f"{firebase_user.name or (firebase_user.email.split('@')[0] if firebase_user.email else f'user-{firebase_user.uid}')}'s Workspace",
                "description": "Default workspace",
                "owner_id": mongodb_user_id,  # Use MongoDB user ID, not Firebase UID
                "members": [
                    {"user_id": mongodb_user_id, "role": "owner", "joined_at": datetime.utcnow()}  # Use MongoDB user ID here too
                ],
                "settings": {},
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            # Insert the workspace
            await workspaces_collection.insert_one(new_workspace)
            workspace_id = str(new_workspace["_id"])

            # Update user with the new workspace
            await users_collection.update_one(
                {"firebase_uid": firebase_user.uid},
                {
                    "$push": {"workspaces": new_workspace["_id"]},
                    "$set": {"preferences.last_workspace_id": new_workspace["_id"]},
                },
            )

        # Create custom tokens with consistent user ID and workspace
        # IMPORTANT: We include both Firebase UID (for backward compatibility) and MongoDB ID (db_id)
        # The JWT validation layer prefers db_id when available (see jwt_auth.py)
        mongodb_user_id = str(user_doc["_id"])
        access_token = jwt_auth.create_access_token(
            uid=firebase_user.uid,  # Keep Firebase UID for backward compatibility
            email=firebase_user.email,
            workspace_id=workspace_id,
            additional_claims={
                "name": firebase_user.name,
                "email_verified": firebase_user.email_verified,
                "provider": "firebase",
                "db_id": mongodb_user_id,  # CRITICAL: MongoDB ID is the primary identifier
            },
        )

        refresh_token = jwt_auth.create_refresh_token(
            uid=firebase_user.uid, email=firebase_user.email, workspace_id=workspace_id
        )

        # Create response
        response = TokenExchangeResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,  # 1 hour
            user={
                "id": mongodb_user_id,  # IMPORTANT: Return MongoDB ID as primary identifier
                "firebase_uid": firebase_user.uid,  # Keep Firebase UID for reference
                "email": firebase_user.email,
                "name": firebase_user.name or user_doc.get("displayName"),
                "email_verified": firebase_user.email_verified,
                "picture": firebase_user.picture,
                "db_id": mongodb_user_id,
            },
        )

        logger.info(f"Token exchange successful for user: {firebase_user.email}")
        return response


# Singleton instance
_firebase_auth_instance: FirebaseAuth | None = None


def get_firebase_auth() -> FirebaseAuth:
    """Get or create Firebase auth instance."""
    global _firebase_auth_instance

    if _firebase_auth_instance is None:
        _firebase_auth_instance = FirebaseAuth()

    return _firebase_auth_instance
