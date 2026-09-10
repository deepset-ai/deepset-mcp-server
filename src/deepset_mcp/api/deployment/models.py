# SPDX-FileCopyrightText: 2025-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from deepset_mcp.api.shared_models import DeepsetUser


class DeploymentMode(StrEnum):
    """Execution mode of a deployment."""

    MANAGED = "MANAGED"
    SERVERLESS = "SERVERLESS"


class DeploymentServiceLevel(StrEnum):
    """Sizing tier of a deployment."""

    PRODUCTION = "PRODUCTION"
    DEVELOPMENT = "DEVELOPMENT"
    CUSTOM = "CUSTOM"


class DeploymentDesiredStatus(StrEnum):
    """Whether a deployment is desired to be served."""

    DEPLOYED = "DEPLOYED"
    UNDEPLOYED = "UNDEPLOYED"


class DeploymentStatus(StrEnum):
    """Observed runtime status of a deployment, reconciled from the operator."""

    UNDEPLOYED = "UNDEPLOYED"
    DEPLOYED = "DEPLOYED"
    DEPLOYMENT_IN_PROGRESS = "DEPLOYMENT_IN_PROGRESS"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
    IDLE = "IDLE"


class DeploymentRevisionStatus(StrEnum):
    """Lifecycle of a single deployment revision."""

    PENDING = "PENDING"
    DEPLOYING = "DEPLOYING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    INACTIVE = "INACTIVE"


class DeploymentSourceType(StrEnum):
    """Where a deployment revision's pipeline configuration came from."""

    PLATFORM_PIPELINE = "PLATFORM_PIPELINE"
    EXTERNAL_PIPELINE = "EXTERNAL_PIPELINE"


class DeploymentRevisionAction(StrEnum):
    """Type of a deployment activity event."""

    REVISION_CREATED = "REVISION_CREATED"
    REVISION_ACTIVATED = "REVISION_ACTIVATED"
    REVISION_DEACTIVATED = "REVISION_DEACTIVATED"


class DeploymentOutputType(StrEnum):
    """Shape of a deployment's pipeline output."""

    GENERATIVE = "generative"
    EXTRACTIVE = "extractive"
    DOCUMENT = "document"
    UNKNOWN = "unknown"
    CHAT = "chat"


class DeploymentStatsGranularity(StrEnum):
    """Bucket width for the deployment stats series."""

    DAY = "DAY"
    HOUR = "HOUR"


class DeploymentRevision(BaseModel):
    """A single revision of a deployment's served pipeline configuration."""

    revision_id: UUID
    "Unique identifier for the revision"
    deployment_id: UUID
    "Identifier of the deployment this revision belongs to"
    source_type: DeploymentSourceType | None = None
    "Where the revision's pipeline configuration came from"
    source_version_id: UUID | None = None
    "Identifier of the source pipeline version, if pushed from a platform pipeline"
    source_pipeline_id: UUID | None = None
    "Identifier of the source pipeline, if pushed from a platform pipeline"
    source_metadata: dict[str, Any] | None = None
    "Additional metadata about the revision's source"
    status: DeploymentRevisionStatus
    "Lifecycle status of the revision"
    config_hash: str
    "Hash of the revision's pipeline configuration"
    haystack_version: str
    "Haystack version the revision was built against"
    comment: str | None = None
    "Optional comment describing the revision"
    created_by_user_id: UUID | None = None
    "Identifier of the user who created the revision"
    created_at: datetime
    "Timestamp when the revision was created"
    updated_at: datetime | None = None
    "Timestamp when the revision was last updated"


class DeploymentRevisionDetail(DeploymentRevision):
    """A single revision including its full pipeline configuration YAML."""

    config_yaml: str
    "YAML configuration served by this revision"
    output_type: DeploymentOutputType | None = None
    "Shape of the revision's pipeline output"


class Deployment(BaseModel):
    """A deployment (AI Gateway) on the Haystack Enterprise Platform."""

    deployment_id: UUID
    "Unique identifier for the deployment"
    name: str
    "Human-readable name of the deployment"
    description: str | None = None
    "Optional description of the deployment"
    group_label: str | None = None
    "Optional label used to group related deployments"
    tags: list[str] = Field(default_factory=list)
    "Tags attached to the deployment"
    organization_id: UUID
    "Identifier of the organization the deployment belongs to"
    workspace_id: UUID | None = None
    "Identifier of the workspace the deployment belongs to"
    origin_pipeline_id: UUID | None = None
    "Identifier of the platform pipeline this deployment was created from, if any"
    pipeline_name: str | None = None
    "Name of the pipeline backing the deployment's active revision"
    output_type: DeploymentOutputType | None = None
    "Shape of the deployment's pipeline output"
    deployment_mode: DeploymentMode
    "Execution mode of the deployment"
    desired_status: DeploymentDesiredStatus
    "Whether the deployment is desired to be served"
    status: DeploymentStatus
    "Observed runtime status of the deployment"
    service_level: DeploymentServiceLevel
    "Sizing tier of the deployment"
    active_revision_id: UUID | None = None
    "Identifier of the currently active revision"
    active_revision: DeploymentRevision | None = None
    "The currently active revision"
    pending_revision_id: UUID | None = None
    "Identifier of a revision that is being rolled out, if any"
    idle_timeout_in_seconds: int
    "Seconds of inactivity before the deployment scales down"
    min_query_replica_count: int
    "Minimum number of query replicas"
    max_query_replica_count: int
    "Maximum number of query replicas"
    max_index_replica_count: int
    "Maximum number of index replicas"
    cpu_request: str | None = None
    "Requested CPU per replica"
    cpu_limit: str | None = None
    "CPU limit per replica"
    memory_request: str | None = None
    "Requested memory per replica"
    memory_limit: str | None = None
    "Memory limit per replica"
    gpu_limit_gigabyte: int | None = None
    "GPU memory limit in gigabytes, if any"
    log_storage_enabled: bool
    "Whether logs are stored for this deployment"
    search_history_enabled: bool
    "Whether search history is stored for this deployment"
    created_by: DeepsetUser | None = None
    "User who created the deployment"
    created_at: datetime
    "Timestamp when the deployment was created"
    updated_at: datetime | None = None
    "Timestamp when the deployment was last updated"


class DeploymentEvent(BaseModel):
    """A single activation or revision lifecycle event for a deployment."""

    event_id: UUID
    "Unique identifier for the event"
    deployment_id: UUID
    "Identifier of the deployment the event belongs to"
    revision_id: UUID | None = None
    "Identifier of the revision the event relates to, if any"
    event_type: DeploymentRevisionAction
    "Type of the event"
    triggered_by: UUID | None = None
    "Identifier of the user who triggered the event, if any"
    created_at: datetime
    "Timestamp when the event occurred"


class MetricPoint(BaseModel):
    """A single timestamped metric value."""

    timestamp: int
    "Unix timestamp in milliseconds"
    value: float
    "Metric value at this timestamp"


class ReplicaMetricSeries(BaseModel):
    """A time series of a metric for a single replica."""

    replica: str
    "Identifier of the replica"
    values: list[MetricPoint]
    "Metric values over time for this replica"


class ReplicaCountPoint(BaseModel):
    """A single timestamped replica count."""

    timestamp: int
    "Unix timestamp in milliseconds"
    count: int
    "Number of replicas at this timestamp"


class DeploymentMetrics(BaseModel):
    """Per-replica CPU/memory usage, resource limits, and replica counts for a deployment."""

    cpu: list[ReplicaMetricSeries]
    "CPU usage per replica over time"
    memory: list[ReplicaMetricSeries]
    "Memory usage per replica over time"
    replicas: list[ReplicaCountPoint]
    "Replica count over time"
    cpu_limit_cores: float | None = None
    "Configured CPU limit in cores"
    memory_limit_bytes: float | None = None
    "Configured memory limit in bytes"


class DeploymentSeriesPoint(BaseModel):
    """One time bucket of run activity for a deployment."""

    bucket_start: datetime
    "Start of the time bucket"
    query_count: int = 0
    "Number of queries in this bucket"
    successful_queries: int = 0
    "Number of successful queries in this bucket"
    failed_queries: int = 0
    "Number of failed queries in this bucket"
    error_rate: float | None = None
    "Fraction of queries that failed in this bucket"
    avg_response_time: float | None = None
    "Average response time in this bucket, in seconds"
    min_inference_time: float | None = None
    "Minimum inference time in this bucket, in seconds"
    max_inference_time: float | None = None
    "Maximum inference time in this bucket, in seconds"


class DeploymentStatistics(BaseModel):
    """Query volume, outcome split and run durations for a deployment over a rolling window."""

    window_days: int
    "Number of days covered by the window"
    granularity: DeploymentStatsGranularity
    "Bucket width used for the series"
    time_zone: str
    "Time zone used to bucket the series"
    total_queries: int = 0
    "Total number of queries in the window"
    successful_queries: int = 0
    "Number of successful queries in the window"
    failed_queries: int = 0
    "Number of failed queries in the window"
    error_rate: float | None = None
    "Fraction of queries that failed in the window"
    avg_response_time: float | None = None
    "Average response time in the window, in seconds"
    min_inference_time: float | None = None
    "Minimum inference time in the window, in seconds"
    max_inference_time: float | None = None
    "Maximum inference time in the window, in seconds"
    series: list[DeploymentSeriesPoint] = Field(default_factory=list)
    "Time-bucketed breakdown of the window"
