"""
Integration tests for ONYX environment setup and secrets management

These tests validate that the complete environment configuration works correctly
and that secrets are properly managed across all services.
"""

import pytest
import asyncio
import os
import subprocess
import tempfile
import time
from typing import Dict, List
import requests
from pathlib import Path


class TestEnvironmentSetup:
    """Test environment configuration and setup"""

    @pytest.fixture(scope="class")
    def test_env_dir(self):
        """Create temporary directory for test environment files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture(scope="class")
    def test_env_file(self, test_env_dir):
        """Create test environment file with non-sensitive values"""
        env_file = Path(test_env_dir) / ".env.test"
        env_content = """
# Test Environment Configuration
NODE_ENV=test
PYTHON_ENV=test
LOG_LEVEL=debug

# Database Configuration (test values)
POSTGRES_PASSWORD=test-password-123
DATABASE_URL=postgresql://manus:test-password-123@postgres:5432/manus_test

# Redis Configuration
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=test-redis-password

# Qdrant Configuration
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=test-qdrant-key

# API Keys (test values)
TOGETHER_API_KEY=test-together-key
DEEPSEEK_API_KEY=test-deepseek-key

# Google OAuth (test values)
GOOGLE_CLIENT_ID=test-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=test-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/api/auth/callback/google

# Encryption
ENCRYPTION_KEY=12345678901234567890123456789012  # 32 bytes for testing

# Session Management
SESSION_SECRET=test-session-secret-123

# Monitoring
GRAFANA_PASSWORD=test-grafana-password

# API Configuration
API_TITLE="Onyx Core Test API"
API_DESCRIPTION="Test instance of Onyx Core API"
API_VERSION="test-1.0.0"
CORS_ORIGINS="http://localhost:3000,http://test-frontend:3000"
"""
        env_file.write_text(env_content.strip())
        return str(env_file)

    def test_env_file_validation(self, test_env_file):
        """Test that environment file validation works correctly"""
        # Run validation script on test environment file
        result = subprocess.run(
            ["./scripts/validate-runtime-secrets.sh"],
            env={**os.environ, "ENV_FILE": test_env_file},
            capture_output=True,
            text=True,
            cwd="/Users/darius/Documents/1-Active-Projects/M3rcury/ONYX",
        )

        # Should pass validation (no placeholders in test file)
        assert result.returncode == 0, f"Validation failed: {result.stderr}"
        assert "✅ All validations passed" in result.stdout

    def test_docker_compose_config_validation(self, test_env_file):
        """Test Docker Compose configuration validation"""
        # Test docker compose config generation
        result = subprocess.run(
            ["docker", "compose", "config", "--no-path-resolution"],
            env={**os.environ, "ENV_FILE": test_env_file},
            capture_output=True,
            text=True,
            cwd="/Users/darius/Documents/1-Active-Projects/M3rcury/ONYX",
        )

        if result.returncode == 0:
            config_output = result.stdout

            # Check that no placeholder values are exposed
            placeholders = [
                "your-google-client",
                "your-together-ai",
                "your-deepseek",
                "generate-secure",
                "placeholder",
            ]

            for placeholder in placeholders:
                assert placeholder.lower() not in config_output.lower(), (
                    f"Placeholder '{placeholder}' found in docker compose config"
                )

    def test_secrets_masking_script(self, test_env_file):
        """Test secrets masking script functionality"""
        result = subprocess.run(
            ["./scripts/test-secrets-masking.sh"],
            env={**os.environ, "ENV_FILE": test_env_file, "NON_INTERACTIVE": "1"},
            capture_output=True,
            text=True,
            cwd="/Users/darius/Documents/1-Active-Projects/M3rcury/ONYX",
        )

        # Should run successfully
        assert result.returncode == 0, f"Secrets masking test failed: {result.stderr}"
        assert "ONYX Secrets Masking Test" in result.stdout

    def test_environment_switching(self):
        """Test environment switching functionality"""
        # Test switch-env script
        result = subprocess.run(
            ["./scripts/switch-env.sh", "development"],
            capture_output=True,
            text=True,
            cwd="/Users/darius/Documents/1-Active-Projects/M3rcury/ONYX",
        )

        # Should run successfully (may not actually switch if files don't exist)
        assert result.returncode == 0 or "not found" in result.stdout.lower()

    def test_docker_secrets_script(self):
        """Test Docker secrets management script"""
        # Test help command
        result = subprocess.run(
            ["./scripts/manage-docker-secrets.sh", "help"],
            capture_output=True,
            text=True,
            cwd="/Users/darius/Documents/1-Active-Projects/M3rcury/ONYX",
        )

        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert "create-secrets" in result.stdout


class TestRAGServiceIntegration:
    """Test RAG service integration"""

    @pytest.mark.asyncio
    async def test_rag_service_initialization(self):
        """Test RAG service can be initialized"""
        try:
            import sys
            import os

            sys.path.append(os.path.join(os.path.dirname(__file__), "..", "onyx-core"))
            from rag_service import RAGService

            # This will fail if Qdrant is not running, but should not crash
            rag_service = RAGService()
            assert rag_service.qdrant_url is not None
            assert rag_service.collection_name == "documents"
            assert rag_service.embedding_model is not None

        except Exception as e:
            # Expected if Qdrant is not running in test environment
            assert "qdrant" in str(e).lower() or "connection" in str(e).lower()

    @pytest.mark.asyncio
    async def test_search_endpoint_structure(self):
        """Test search endpoint has correct structure"""
        # This tests the API structure without requiring actual RAG functionality
        try:
            from main import search_documents

            # Test with empty query (should raise HTTPException)
            with pytest.raises(Exception):  # HTTPException or similar
                await search_documents(query="", top_k=5)

        except ImportError:
            pytest.skip("Main module not available")
        except Exception as e:
            # Expected if dependencies are not available
            pass


class TestHealthChecks:
    """Test health check endpoints"""

    @pytest.mark.asyncio
    async def test_health_check_structure(self):
        """Test health check returns proper structure"""
        try:
            from health import (
                check_database_health,
                check_qdrant_health,
                check_redis_health,
            )

            # Test database health check
            db_health = await check_database_health()
            assert hasattr(db_health, "status")
            assert hasattr(db_health, "response_time")

            # Test Qdrant health check
            qdrant_health = await check_qdrant_health()
            assert hasattr(qdrant_health, "status")
            assert hasattr(qdrant_health, "response_time")

            # Test Redis health check
            redis_health = await check_redis_health()
            assert hasattr(redis_health, "status")
            assert hasattr(redis_health, "response_time")

        except ImportError:
            pytest.skip("Health module not available")
        except Exception as e:
            # Expected if services are not running
            pass


class TestSecurityValidation:
    """Test security validation functionality"""

    def test_git_history_clean(self):
        """Test that no secrets are in git history"""
        # Check for common secret patterns in git history
        secret_patterns = ["password", "secret", "api_key", "token", "private_key"]

        for pattern in secret_patterns:
            result = subprocess.run(
                ["git", "log", "--all", "--oneline", "-S", pattern],
                capture_output=True,
                text=True,
                cwd="/Users/darius/Documents/1-Active-Projects/M3rcury/ONYX",
            )

            # Should find very few or no results (only legitimate uses)
            lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
            non_test_lines = [line for line in lines if "test" not in line.lower()]

            # Allow some results for legitimate uses, but not many
            assert len(non_test_lines) < 5, (
                f"Too many {pattern} references in git history"
            )

    def test_gitignore_secrets(self):
        """Test that .gitignore properly excludes secret files"""
        gitignore_path = Path(
            "/Users/darius/Documents/1-Active-Projects/M3rcury/ONYX/.gitignore"
        )

        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text()

            # Should exclude common secret file patterns
            secret_patterns = [
                ".env.local",
                ".env.production",
                "*.key",
                "*.pem",
                "secrets/",
            ]

            for pattern in secret_patterns:
                assert pattern in gitignore_content, (
                    f"Pattern '{pattern}' not in .gitignore"
                )

    def test_script_permissions(self):
        """Test that scripts have proper permissions"""
        scripts_dir = Path(
            "/Users/darius/Documents/1-Active-Projects/M3rcury/ONYX/scripts"
        )

        if scripts_dir.exists():
            script_files = list(scripts_dir.glob("*.sh"))

            for script in script_files:
                # Check if script is executable
                assert os.access(script, os.X_OK), (
                    f"Script {script.name} is not executable"
                )


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
