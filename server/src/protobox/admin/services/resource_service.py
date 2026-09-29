"""Resource service for managing MCP resources."""

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from ..constants import SystemUsers
from ..database.repositories.resource_repository import ResourceRepository
from ..models.knowledge_base import KnowledgeDocument, ProcessingStatus
from ..models.mcp_resource import (
    MCPResourceCreateRequest,
    MCPResourceModel,
    MCPResourceStatsResponse,
    MCPResourceSyncResponse,
    MCPResourceUpdateRequest,
    ResourceAccessControl,
    ResourceSource,
    ResourceSourceType,
    ResourceType,
)
from .base_service import BaseService


class ResourceValidationError(Exception):
    """Raised when resource validation fails."""
    pass


class ResourceService(BaseService):
    """Service for managing MCP resources."""

    def __init__(self):
        """Initialize the resource service."""
        super().__init__()
        self.repository = ResourceRepository()

    async def create_resource(
        self,
        workspace_id: str,
        resource_data: MCPResourceCreateRequest,
        user_id: str
    ) -> MCPResourceModel:
        """Create a new resource.

        Args:
            workspace_id: The workspace ID
            resource_data: The resource creation data
            user_id: The user creating the resource

        Returns:
            The created resource model

        Raises:
            ResourceValidationError: If resource validation fails
            DuplicateKeyError: If resource URI already exists
        """
        # Validate resource data
        self._validate_resource_data(resource_data)

        # Generate content preview if possible
        content_preview = await self._generate_content_preview(resource_data)

        # Calculate size if possible
        size = await self._calculate_resource_size(resource_data)

        # Prepare data with audit fields
        resource_dict = resource_data.model_dump(exclude_none=True)
        resource_dict["workspace_id"] = workspace_id
        resource_dict["content_preview"] = content_preview
        resource_dict["size"] = size

        audit_data = self.add_create_audit_fields(resource_dict, user_id)

        # Create the resource model
        resource = MCPResourceModel(**audit_data)

        # Save to database
        resource_id = await self.repository.create_resource(resource)
        resource.id = resource_id

        return resource

    async def get_resource(self, workspace_id: str, uri: str) -> MCPResourceModel | None:
        """Get a resource by URI.

        Args:
            workspace_id: The workspace ID
            uri: The resource URI

        Returns:
            The resource model or None if not found
        """
        return await self.repository.get_resource_by_uri(workspace_id, uri)

    async def get_resource_by_id(self, resource_id: str) -> MCPResourceModel | None:
        """Get a resource by ID.

        Args:
            resource_id: The resource ID

        Returns:
            The resource model or None if not found
        """
        return await self.repository.get_resource_by_id(resource_id)

    async def list_resources(
        self,
        workspace_id: str,
        resource_type: ResourceType | None = None,
        uri_pattern: str | None = None,
        is_active: bool | None = None,
        is_template: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MCPResourceModel]:
        """List resources for a workspace.

        Args:
            workspace_id: The workspace ID
            resource_type: Optional resource type filter
            uri_pattern: Optional URI pattern filter
            is_active: Optional active status filter
            is_template: Optional template status filter
            skip: Number of resources to skip
            limit: Maximum number of resources to return

        Returns:
            List of resource models
        """
        return await self.repository.get_resources_by_workspace(
            workspace_id=workspace_id,
            resource_type=resource_type,
            uri_pattern=uri_pattern,
            is_active=is_active,
            is_template=is_template,
            skip=skip,
            limit=limit
        )

    async def read_resource_content(self, workspace_id: str, uri: str) -> tuple[str, str]:
        """Read the content of a resource.

        Args:
            workspace_id: The workspace ID
            uri: The resource URI

        Returns:
            Tuple of (content, mime_type)

        Raises:
            ResourceValidationError: If resource not found or not accessible
        """
        # Get the resource
        resource = await self.get_resource(workspace_id, uri)
        if not resource:
            raise ResourceValidationError(f"Resource '{uri}' not found")

        if not resource.is_active:
            raise ResourceValidationError(f"Resource '{uri}' is not active")

        # Track access
        await self.track_access(workspace_id, uri)

        # Read content based on source type
        content = await self._read_content_from_source(resource)

        return content, resource.mime_type

    async def update_resource(
        self,
        workspace_id: str,
        uri: str,
        updates: MCPResourceUpdateRequest,
        user_id: str
    ) -> MCPResourceModel | None:
        """Update a resource.

        Args:
            workspace_id: The workspace ID
            uri: The resource URI
            updates: The updates to apply
            user_id: The user updating the resource

        Returns:
            The updated resource model or None if not found

        Raises:
            ResourceValidationError: If validation fails
        """
        # Get existing resource
        existing_resource = await self.get_resource(workspace_id, uri)
        if not existing_resource:
            return None

        # Validate updates
        update_data = updates.model_dump(exclude_none=True)

        # Add audit fields
        audit_updates = self.add_update_audit_fields(update_data, user_id)

        # Update in database
        return await self.repository.update_resource(existing_resource.id_str, audit_updates)

    async def delete_resource(self, workspace_id: str, uri: str) -> bool:
        """Delete a resource.

        Args:
            workspace_id: The workspace ID
            uri: The resource URI

        Returns:
            True if deleted, False if not found
        """
        return await self.repository.delete_resource_by_uri(workspace_id, uri)

    async def sync_knowledge_base_resources(self, workspace_id: str) -> MCPResourceSyncResponse:
        """Sync knowledge base documents as resources.

        Args:
            workspace_id: The workspace ID

        Returns:
            Sync response with statistics
        """
        start_time = datetime.now(UTC)

        synced_count = 0
        created_count = 0
        updated_count = 0
        deleted_count = 0
        errors = []

        try:
            # Get knowledge base documents for this workspace
            kb_documents = await self._get_knowledge_base_documents(workspace_id)

            # Get existing KB resources
            existing_resources = await self.repository.get_resources_by_source(
                workspace_id,
                ResourceSourceType.KNOWLEDGE_BASE.value,
                ""  # We'll filter by source type in the query
            )

            # Create mapping of existing resources by source ID
            existing_by_source_id = {r.source.id: r for r in existing_resources}

            # Process each KB document
            for doc in kb_documents:
                try:
                    doc_id = str(doc.id)

                    # Skip documents that aren't processed successfully
                    if doc.processing_status != ProcessingStatus.COMPLETED:
                        continue

                    # Generate resource URI
                    uri = f"kb://{self._generate_uri_slug(doc.title)}"

                    # Check if resource already exists
                    if doc_id in existing_by_source_id:
                        # Update existing resource
                        existing_resource = existing_by_source_id[doc_id]
                        updates = {
                            "name": doc.title,
                            "description": doc.description or f"Knowledge base document: {doc.title}",
                            "content_preview": await self._generate_kb_preview(doc),
                            "size": self._estimate_kb_document_size(doc),
                            "updated_by": SystemUsers.SYSTEM,
                            "updated_at": datetime.now(UTC)
                        }

                        await self.repository.update_resource(existing_resource.id_str, updates)
                        updated_count += 1
                    else:
                        # Create new resource
                        resource_data = MCPResourceCreateRequest(
                            workspace_id=workspace_id,
                            uri=uri,
                            name=doc.title,
                            description=doc.description or f"Knowledge base document: {doc.title}",
                            mime_type=self._get_kb_mime_type(doc),
                            resource_type=ResourceType.KNOWLEDGE_BASE,
                            source=ResourceSource(
                                type=ResourceSourceType.KNOWLEDGE_BASE,
                                id=doc_id,
                                metadata={
                                    "document_title": doc.title,
                                    "category": doc.category,
                                    "tags": doc.tags,
                                    "chunk_count": doc.chunk_count,
                                    "processing_status": doc.processing_status.value
                                }
                            ),
                            is_active=True,
                            access_control=ResourceAccessControl(
                                public=False,
                                require_authentication=True
                            )
                        )

                        await self.create_resource(
                            workspace_id=workspace_id,
                            resource_data=resource_data,
                            user_id=SystemUsers.SYSTEM
                        )
                        created_count += 1

                    synced_count += 1

                except Exception as e:
                    errors.append(f"Failed to sync document {doc.title}: {str(e)}")
                    continue

            # Remove resources for deleted KB documents
            current_doc_ids = {str(doc.id) for doc in kb_documents}
            resources_to_delete = [
                r for r in existing_resources
                if r.source.id not in current_doc_ids
            ]

            for resource in resources_to_delete:
                try:
                    await self.repository.delete_resource(resource.id_str)
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"Failed to delete resource {resource.uri}: {str(e)}")

        except Exception as e:
            errors.append(f"Failed to sync knowledge base: {str(e)}")

        duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

        return MCPResourceSyncResponse(
            synced_count=synced_count,
            created_count=created_count,
            updated_count=updated_count,
            deleted_count=deleted_count,
            errors=errors,
            duration_ms=duration_ms
        )

    def validate_uri(self, uri: str) -> bool:
        """Validate URI format.

        Args:
            uri: The URI to validate

        Returns:
            True if valid, False otherwise
        """
        if not uri or len(uri) == 0:
            return False

        # Basic URI validation
        try:
            parsed = urlparse(uri)
            # Must have either scheme or be a valid path
            return bool(parsed.scheme or parsed.path)
        except Exception:
            return False

    def resolve_uri_template(self, template: str, params: dict[str, Any]) -> str:
        """Resolve URI template with parameters (RFC 6570 basic implementation).

        Args:
            template: URI template string
            params: Parameters to substitute

        Returns:
            Resolved URI
        """
        # Basic RFC 6570 implementation for simple variables {var}
        resolved = template

        # Find all variables in template
        variables = re.findall(r'\{(\w+)\}', template)

        for var in variables:
            if var in params:
                value = str(params[var])
                resolved = resolved.replace(f'{{{var}}}', value)

        return resolved

    async def track_access(self, workspace_id: str, uri: str) -> None:
        """Track access to a resource.

        Args:
            workspace_id: The workspace ID
            uri: The resource URI
        """
        resource = await self.get_resource(workspace_id, uri)
        if resource:
            await self.repository.increment_access_count(resource.id_str)

    async def get_resource_stats(self, workspace_id: str) -> MCPResourceStatsResponse:
        """Get resource statistics for a workspace.

        Args:
            workspace_id: The workspace ID

        Returns:
            Resource statistics
        """
        # Get basic stats
        usage_stats = await self.repository.get_usage_stats(workspace_id)

        # Get type counts
        type_counts = await self.repository.get_resource_type_counts(workspace_id)

        # Get MIME type counts
        mime_type_counts = await self.repository.get_mime_type_counts(workspace_id)

        # Get most accessed resources
        most_accessed = await self.repository.get_most_accessed_resources(workspace_id, 5)

        return MCPResourceStatsResponse(
            total_resources=usage_stats.get("total_resources", 0),
            active_resources=usage_stats.get("active_resources", 0),
            by_type=type_counts,
            by_mime_type=mime_type_counts,
            total_size=usage_stats.get("total_size", 0),
            total_accesses=usage_stats.get("total_accesses", 0),
            most_accessed=[
                {
                    "uri": item["uri"],
                    "name": item["name"],
                    "access_count": item["access_count"]
                }
                for item in most_accessed
            ]
        )

    async def count_resources(
        self,
        workspace_id: str,
        resource_type: ResourceType | None = None,
        uri_pattern: str | None = None,
        is_active: bool | None = None,
        is_template: bool | None = None,
    ) -> int:
        """Count resources for a workspace.

        Args:
            workspace_id: The workspace ID
            resource_type: Optional resource type filter
            uri_pattern: Optional URI pattern filter
            is_active: Optional active status filter
            is_template: Optional template status filter

        Returns:
            Number of matching resources
        """
        return await self.repository.count_resources_by_workspace(
            workspace_id=workspace_id,
            resource_type=resource_type,
            uri_pattern=uri_pattern,
            is_active=is_active,
            is_template=is_template
        )

    def _validate_resource_data(self, resource_data: MCPResourceCreateRequest) -> None:
        """Validate resource creation data.

        Args:
            resource_data: The resource data to validate

        Raises:
            ResourceValidationError: If validation fails
        """
        if not self.validate_uri(resource_data.uri):
            raise ResourceValidationError(f"Invalid URI: {resource_data.uri}")

        if resource_data.is_template and not resource_data.uri_template:
            raise ResourceValidationError("Template resources must have uri_template")

        if resource_data.uri_template and not resource_data.is_template:
            raise ResourceValidationError("uri_template can only be set for template resources")

    async def _generate_content_preview(self, resource_data: MCPResourceCreateRequest) -> str:
        """Generate content preview for a resource.

        Args:
            resource_data: The resource creation data

        Returns:
            Content preview string (first 500 chars)
        """
        # For now, use description as preview
        # In a full implementation, this would read actual content
        preview = resource_data.description or ""
        return preview[:500]

    async def _calculate_resource_size(self, resource_data: MCPResourceCreateRequest) -> int:
        """Calculate resource size in bytes.

        Args:
            resource_data: The resource creation data

        Returns:
            Size in bytes
        """
        # For now, estimate based on description length
        # In a full implementation, this would calculate actual content size
        return len(resource_data.description.encode('utf-8'))

    async def _read_content_from_source(self, resource: MCPResourceModel) -> str:
        """Read content from the resource's source.

        Args:
            resource: The resource model

        Returns:
            Resource content

        Raises:
            ResourceValidationError: If content cannot be read
        """
        source_type = resource.source.type
        source_id = resource.source.id

        if source_type == ResourceSourceType.KNOWLEDGE_BASE:
            return await self._read_knowledge_base_content(source_id)
        if source_type == ResourceSourceType.ACTION_DEFINITION:
            return await self._read_action_definition(source_id)
        if source_type == ResourceSourceType.WORKSPACE_SETTING:
            return await self._read_workspace_settings(source_id)
        raise ResourceValidationError(f"Unsupported source type: {source_type}")

    async def _read_knowledge_base_content(self, document_id: str) -> str:
        """Read content from a knowledge base document.

        Args:
            document_id: The document ID

        Returns:
            Document content
        """
        # This would integrate with the knowledge base service
        # For now, return a placeholder
        return f"Content from knowledge base document {document_id}"

    async def _read_action_definition(self, action_id: str) -> str:
        """Read action definition as JSON.

        Args:
            action_id: The action ID

        Returns:
            Action definition as JSON string
        """
        # This would integrate with the action service
        # For now, return a placeholder
        return f'{{"action_id": "{action_id}", "type": "action_definition"}}'

    async def _read_workspace_settings(self, workspace_id: str) -> str:
        """Read workspace settings as JSON.

        Args:
            workspace_id: The workspace ID

        Returns:
            Workspace settings as JSON string
        """
        # This would integrate with the workspace service
        # For now, return a placeholder
        return f'{{"workspace_id": "{workspace_id}", "type": "workspace_settings"}}'

    async def _get_knowledge_base_documents(self, workspace_id: str) -> list[KnowledgeDocument]:
        """Get knowledge base documents for a workspace.

        Args:
            workspace_id: The workspace ID

        Returns:
            List of knowledge base documents
        """
        # This would integrate with the knowledge base service
        # For now, return empty list
        return []

    async def _generate_kb_preview(self, doc: KnowledgeDocument) -> str:
        """Generate preview for a knowledge base document.

        Args:
            doc: The knowledge base document

        Returns:
            Content preview
        """
        # Generate preview from document metadata
        preview = f"# {doc.title}\n\n"
        if doc.description:
            preview += f"{doc.description}\n\n"

        preview += f"Category: {doc.category}\n"
        if doc.tags:
            preview += f"Tags: {', '.join(doc.tags)}\n"

        preview += f"Chunks: {doc.chunk_count}\n"
        preview += f"Status: {doc.processing_status.value}"

        return preview[:500]

    def _estimate_kb_document_size(self, doc: KnowledgeDocument) -> int:
        """Estimate size of a knowledge base document.

        Args:
            doc: The knowledge base document

        Returns:
            Estimated size in bytes
        """
        # Rough estimate based on chunk count
        # Assumes average 500 chars per chunk
        return doc.chunk_count * 500

    def _get_kb_mime_type(self, doc: KnowledgeDocument) -> str:
        """Get MIME type for a knowledge base document.

        Args:
            doc: The knowledge base document

        Returns:
            MIME type string
        """
        # Map based on original file type or default to markdown
        if doc.mime_type:
            return doc.mime_type
        if doc.filename and doc.filename.endswith('.pdf'):
            return 'application/pdf'
        if doc.filename and doc.filename.endswith('.html'):
            return 'text/html'
        return 'text/markdown'

    def _generate_uri_slug(self, title: str) -> str:
        """Generate a URI-safe slug from a title.

        Args:
            title: The title to convert

        Returns:
            URI-safe slug
        """
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')
