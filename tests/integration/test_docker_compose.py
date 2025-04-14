"""Integration tests for Docker Compose configuration for migration."""
import os
import io
import pytest
import re
from pathlib import Path
import yaml

# Mark all tests in this module as docker integration tests
pytestmark = [pytest.mark.integration, pytest.mark.docker]


class TestDockerComposeConfiguration:
    """Test suite for Docker Compose configuration validation."""

    @pytest.fixture
    def docker_compose_file(self):
        """Load the Docker Compose file for testing."""
        compose_path = Path(__file__).parent.parent.parent / "docker-compose.migration.yml"
        assert compose_path.exists(), f"Docker Compose file not found at {compose_path}"

        with open(compose_path, 'r') as f:
            compose_data = yaml.safe_load(f)

        return compose_data

    def test_compose_version(self, docker_compose_file):
        """Test that the Docker Compose file uses a valid version."""
        assert 'version' in docker_compose_file, "Docker Compose file should specify a version"
        assert docker_compose_file['version'] in ['3.8', '3.9', '3.7'], "Version should be 3.7 or higher"

    def test_required_services(self, docker_compose_file):
        """Test that all required services are defined in the Docker Compose file."""
        required_services = [
            'migration',
                'migration-status',
                'migration-report',
                'postgres',
                'pgadmin'
        ]

        assert 'services' in docker_compose_file, "Docker Compose file should define services"
        services = docker_compose_file['services']

        for service in required_services:
            assert service in services, f"Required service '{service}' not found in Docker Compose file"

    def test_migration_service_configuration(self, docker_compose_file):
        """Test the migration service configuration."""
        migration = docker_compose_file['services']['migration']

        # Check build context and dockerfile
        assert 'build' in migration, "migration service should have build configuration"
        assert 'context' in migration['build'], "build should specify context"
        assert 'dockerfile' in migration['build'], "build should specify dockerfile"

        # Check volumes
        assert 'volumes' in migration, "migration service should have volumes configured"
        volume_paths = [v.split(':')[0] for v in migration['volumes']]
        assert './attachments' in volume_paths, "migration should mount attachments directory"
        assert './migration_data' in volume_paths, "migration should mount migration_data directory"

        # Check environment variables
        assert 'environment' in migration, "migration service should have environment variables"
        env_vars = migration['environment']
        db_vars = [v for v in env_vars if v.startswith('ZTOQ_DB_')]
        assert len(db_vars) >= 5, "migration should have database configuration environment variables"

        zephyr_vars = [v for v in env_vars if v.startswith('ZEPHYR_')]
        assert len(zephyr_vars) >= 3, "migration should have Zephyr API environment variables"

        qtest_vars = [v for v in env_vars if v.startswith('QTEST_')]
        assert len(qtest_vars) >= 3, "migration should have qTest API environment variables"

        # Check command
        assert 'command' in migration, "migration service should have a command defined"
        command_str = ' '.join(migration['command'])
        assert 'migrate run' in command_str, "command should run the migration"
        assert '--batch-size' in command_str, "command should specify batch size"
        assert '--max-workers' in command_str, "command should specify max workers"

    def test_postgres_service_configuration(self, docker_compose_file):
        """Test the PostgreSQL service configuration."""
        postgres = docker_compose_file['services']['postgres']

        # Check image
        assert 'image' in postgres, "postgres service should specify an image"
        assert postgres['image'].startswith('postgres:'), "postgres image should be a postgres image"

        # Check volumes
        assert 'volumes' in postgres, "postgres service should have volume for data persistence"

        # Check environment variables
        assert 'environment' in postgres, "postgres service should have environment variables"
        env_vars = postgres['environment']
        required_vars = ['POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB']
        for var in required_vars:
            assert any(v.startswith(f"{var}=") for v in env_vars), f"postgres should have {var} environment variable"

    def test_volumes_definition(self, docker_compose_file):
        """Test that all required volumes are defined."""
        assert 'volumes' in docker_compose_file, "Docker Compose file should define volumes"
        volumes = docker_compose_file['volumes']
        assert 'postgres_data' in volumes, "postgres_data volume should be defined"

    def test_service_dependencies(self, docker_compose_file):
        """Test that service dependencies are correctly configured."""
        services = docker_compose_file['services']

        # Migration services should depend on postgres
        migration_services = ['migration', 'migration-status', 'migration-report']
        for service_name in migration_services:
            service = services[service_name]
            assert 'depends_on' in service, f"{service_name} should have dependencies defined"
            assert 'postgres' in service['depends_on'], f"{service_name} should depend on postgres"

        # pgadmin should depend on postgres
        pgadmin = services['pgadmin']
        assert 'depends_on' in pgadmin, "pgadmin should have dependencies defined"
        assert 'postgres' in pgadmin['depends_on'], "pgadmin should depend on postgres"

    def test_migration_report_configuration(self, docker_compose_file):
        """Test the migration report service configuration."""
        report_service = docker_compose_file['services']['migration-report']

        # Check build configuration
        assert 'build' in report_service, "migration-report service should have build configuration"
        assert 'dockerfile' in report_service['build'], "build should specify dockerfile"
        assert report_service['build']['dockerfile'] == 'Dockerfile.migration-report', "Should use specialized Dockerfile"

        # Check volumes
        assert 'volumes' in report_service, "migration-report service should have volumes"
        volume_paths = [v.split(':')[0] for v in report_service['volumes']]
        assert './reports' in volume_paths, "migration-report should mount reports directory"

        # Check command
        assert 'command' in report_service, "migration-report service should have a command"
        command_str = ' '.join(report_service['command'])
        assert 'migration_report' in command_str, "command should run the migration report module"
        assert '--output-format' in command_str, "command should specify output format"
        assert '--output-file' in command_str, "command should specify output file"
