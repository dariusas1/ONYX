"""
Search Configuration Module

This module contains configuration settings for the hybrid search system,
including weights, performance targets, and feature flags.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SearchConfig:
    """Configuration class for search system settings"""

    # Hybrid Search Weights
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3

    # Search Limits
    default_hybrid_limit: int = 5
    semantic_search_limit: int = 10
    keyword_search_limit: int = 10

    # Performance Targets
    total_timeout_ms: int = 200
    semantic_timeout_ms: int = 100
    keyword_timeout_ms: int = 50
    fusion_timeout_ms: int = 20

    # Recency Boosting
    recency_boost_days: int = 30
    recency_boost_factor: float = 1.10

    # Search Quality
    min_semantic_score: float = 0.3
    min_keyword_score: float = 0.1

    # Feature Flags
    enable_hybrid_search: bool = True
    enable_semantic_search: bool = True
    enable_keyword_search: bool = True
    enable_recency_boost: bool = True
    enable_query_classification: bool = True

    # Caching
    enable_search_cache: bool = True
    search_cache_ttl_seconds: int = 300  # 5 minutes
    cache_max_size: int = 1000

    # Database
    postgres_pool_min_size: int = 2
    postgres_pool_max_size: int = 10
    postgres_query_timeout: float = 5.0

    # Monitoring
    enable_performance_tracking: bool = True
    enable_query_logging: bool = True
    slow_query_threshold_ms: int = 500


class SearchConfigManager:
    """Manager for search configuration with environment variable support"""

    def __init__(self):
        """Initialize configuration manager with environment variable defaults"""
        self._config = self._load_config()

    def _load_config(self) -> SearchConfig:
        """Load configuration from environment variables with sensible defaults"""
        return SearchConfig(
            # Hybrid Search Weights
            semantic_weight=float(os.getenv("SEMANTIC_WEIGHT", "0.7")),
            keyword_weight=float(os.getenv("KEYWORD_WEIGHT", "0.3")),

            # Search Limits
            default_hybrid_limit=int(os.getenv("HYBRID_SEARCH_DEFAULT_LIMIT", "5")),
            semantic_search_limit=int(os.getenv("SEMANTIC_SEARCH_LIMIT", "10")),
            keyword_search_limit=int(os.getenv("KEYWORD_SEARCH_LIMIT", "10")),

            # Performance Targets
            total_timeout_ms=int(os.getenv("HYBRID_SEARCH_TIMEOUT_MS", "200")),
            semantic_timeout_ms=int(os.getenv("SEMANTIC_SEARCH_TIMEOUT_MS", "100")),
            keyword_timeout_ms=int(os.getenv("KEYWORD_SEARCH_TIMEOUT_MS", "50")),
            fusion_timeout_ms=int(os.getenv("FUSION_TIMEOUT_MS", "20")),

            # Recency Boosting
            recency_boost_days=int(os.getenv("RECENCY_BOOST_DAYS", "30")),
            recency_boost_factor=float(os.getenv("RECENCY_BOOST_FACTOR", "1.10")),

            # Search Quality
            min_semantic_score=float(os.getenv("MIN_SEMANTIC_SCORE", "0.3")),
            min_keyword_score=float(os.getenv("MIN_KEYWORD_SCORE", "0.1")),

            # Feature Flags
            enable_hybrid_search=os.getenv("ENABLE_HYBRID_SEARCH", "true").lower() == "true",
            enable_semantic_search=os.getenv("ENABLE_SEMANTIC_SEARCH", "true").lower() == "true",
            enable_keyword_search=os.getenv("ENABLE_KEYWORD_SEARCH", "true").lower() == "true",
            enable_recency_boost=os.getenv("ENABLE_RECENCY_BOOST", "true").lower() == "true",
            enable_query_classification=os.getenv("ENABLE_QUERY_CLASSIFICATION", "true").lower() == "true",

            # Caching
            enable_search_cache=os.getenv("ENABLE_SEARCH_CACHE", "true").lower() == "true",
            search_cache_ttl_seconds=int(os.getenv("SEARCH_CACHE_TTL_SECONDS", "300")),
            cache_max_size=int(os.getenv("SEARCH_CACHE_MAX_SIZE", "1000")),

            # Database
            postgres_pool_min_size=int(os.getenv("POSTGRES_POOL_MIN_SIZE", "2")),
            postgres_pool_max_size=int(os.getenv("POSTGRES_POOL_MAX_SIZE", "10")),
            postgres_query_timeout=float(os.getenv("POSTGRES_QUERY_TIMEOUT", "5.0")),

            # Monitoring
            enable_performance_tracking=os.getenv("ENABLE_PERFORMANCE_TRACKING", "true").lower() == "true",
            enable_query_logging=os.getenv("ENABLE_QUERY_LOGGING", "true").lower() == "true",
            slow_query_threshold_ms=int(os.getenv("SLOW_QUERY_THRESHOLD_MS", "500")),
        )

    @property
    def config(self) -> SearchConfig:
        """Get the current search configuration"""
        return self._config

    def update_config(self, **kwargs) -> None:
        """Update configuration values"""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            else:
                raise ValueError(f"Unknown configuration key: {key}")

    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return validation results"""
        issues = []
        warnings = []

        # Validate weights sum to 1.0
        weight_sum = self._config.semantic_weight + self._config.keyword_weight
        if abs(weight_sum - 1.0) > 0.01:
            issues.append(f"Search weights sum to {weight_sum}, should be 1.0")

        # Validate timeouts
        if self._config.total_timeout_ms <= 0:
            issues.append("Total timeout must be positive")
        if (self._config.semantic_timeout_ms + self._config.keyword_timeout_ms) > self._config.total_timeout_ms:
            warnings.append("Individual timeouts may exceed total timeout")

        # Validate recency boost factor
        if self._config.recency_boost_factor <= 1.0:
            warnings.append("Recency boost factor <= 1.0 means no boosting")

        # Validate limits
        if self._config.default_hybrid_limit <= 0:
            issues.append("Default hybrid limit must be positive")
        if self._config.default_hybrid_limit > 20:
            warnings.append("Large result limit may impact performance")

        # Validate score thresholds
        if not (0.0 <= self._config.min_semantic_score <= 1.0):
            issues.append("Semantic score threshold must be between 0.0 and 1.0")
        if not (0.0 <= self._config.min_keyword_score <= 1.0):
            issues.append("Keyword score threshold must be between 0.0 and 1.0")

        # Validate database pool settings
        if self._config.postgres_pool_min_size >= self._config.postgres_pool_max_size:
            issues.append("PostgreSQL pool min size must be less than max size")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }

    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary for API responses"""
        return {
            "weights": {
                "semantic": self._config.semantic_weight,
                "keyword": self._config.keyword_weight,
            },
            "limits": {
                "default_hybrid": self._config.default_hybrid_limit,
                "semantic": self._config.semantic_search_limit,
                "keyword": self._config.keyword_search_limit,
            },
            "performance": {
                "total_timeout_ms": self._config.total_timeout_ms,
                "semantic_timeout_ms": self._config.semantic_timeout_ms,
                "keyword_timeout_ms": self._config.keyword_timeout_ms,
                "fusion_timeout_ms": self._config.fusion_timeout_ms,
            },
            "features": {
                "hybrid_search": self._config.enable_hybrid_search,
                "semantic_search": self._config.enable_semantic_search,
                "keyword_search": self._config.enable_keyword_search,
                "recency_boost": self._config.enable_recency_boost,
                "query_classification": self._config.enable_query_classification,
                "search_cache": self._config.enable_search_cache,
            },
            "recency_boost": {
                "days": self._config.recency_boost_days,
                "factor": self._config.recency_boost_factor,
            },
            "quality": {
                "min_semantic_score": self._config.min_semantic_score,
                "min_keyword_score": self._config.min_keyword_score,
            },
            "monitoring": {
                "performance_tracking": self._config.enable_performance_tracking,
                "query_logging": self._config.enable_query_logging,
                "slow_query_threshold_ms": self._config.slow_query_threshold_ms,
            }
        }

    def log_config(self, logger) -> None:
        """Log current configuration for debugging"""
        config_dict = self.get_config_dict()

        logger.info("=== Search Configuration ===")
        logger.info(f"Weights: Semantic={config_dict['weights']['semantic']}, Keyword={config_dict['weights']['keyword']}")
        logger.info(f"Limits: Default={config_dict['limits']['default_hybrid']}")
        logger.info(f"Performance: Total timeout={config_dict['performance']['total_timeout_ms']}ms")
        logger.info(f"Features: Hybrid={config_dict['features']['hybrid_search']}, Recency boost={config_dict['features']['recency_boost']}")
        logger.info(f"Recency boost: {config_dict['recency_boost']['days']} days, {config_dict['recency_boost']['factor']}x factor")
        logger.info("=============================")


# Global configuration instance
_search_config_manager: Optional[SearchConfigManager] = None


def get_search_config() -> SearchConfigManager:
    """Get the global search configuration manager instance"""
    global _search_config_manager
    if _search_config_manager is None:
        _search_config_manager = SearchConfigManager()
    return _search_config_manager


def get_search_settings() -> SearchConfig:
    """Get search settings as a dataclass"""
    return get_search_config().config


# Environment variable documentation for .env.example
ENVIRONMENT_DOCS = """
# =============================================================================
# Hybrid Search Configuration
# =============================================================================

# Search Weights (should sum to 1.0)
SEMANTIC_WEIGHT=0.7
KEYWORD_WEIGHT=0.3

# Search Limits
HYBRID_SEARCH_DEFAULT_LIMIT=5
SEMANTIC_SEARCH_LIMIT=10
KEYWORD_SEARCH_LIMIT=10

# Performance Targets (milliseconds)
HYBRID_SEARCH_TIMEOUT_MS=200
SEMANTIC_SEARCH_TIMEOUT_MS=100
KEYWORD_SEARCH_TIMEOUT_MS=50
FUSION_TIMEOUT_MS=20

# Recency Boosting
RECENCY_BOOST_DAYS=30
RECENCY_BOOST_FACTOR=1.10

# Search Quality Thresholds
MIN_SEMANTIC_SCORE=0.3
MIN_KEYWORD_SCORE=0.1

# Feature Flags
ENABLE_HYBRID_SEARCH=true
ENABLE_SEMANTIC_SEARCH=true
ENABLE_KEYWORD_SEARCH=true
ENABLE_RECENCY_BOOST=true
ENABLE_QUERY_CLASSIFICATION=true

# Search Caching
ENABLE_SEARCH_CACHE=true
SEARCH_CACHE_TTL_SECONDS=300
SEARCH_CACHE_MAX_SIZE=1000

# Database Connection Pooling
POSTGRES_POOL_MIN_SIZE=2
POSTGRES_POOL_MAX_SIZE=10
POSTGRES_QUERY_TIMEOUT=5.0

# Monitoring and Logging
ENABLE_PERFORMANCE_TRACKING=true
ENABLE_QUERY_LOGGING=true
SLOW_QUERY_THRESHOLD_MS=500
"""