# Migration Guide

This guide covers how to use the ZTOQ tool to migrate test data from Zephyr Scale to qTest.

## Overview

The migration process follows an ETL (Extract, Transform, Load) workflow:

1. **Extract**: Data is extracted from Zephyr Scale and stored in a database
2. **Transform**: Extracted data is transformed into qTest-compatible format
3. **Load**: Transformed data is loaded into qTest

The process is designed to be:
- **Restartable**: You can resume from where you left off if something fails
- **Configurable**: Control batch sizes, parallelism, and which phases to run
- **Traceable**: Monitor progress and see detailed statistics

## Prerequisites

Before starting a migration, ensure you have:

1. A working Zephyr Scale instance with API access
   - Base URL (e.g., `https://api.adaptavist.io/tm4j/v2`)
   - API token

2. A qTest instance with API access
   - Base URL (e.g., `https://yourcompany.qtestnet.com`)
   - Username and password
   - Project ID (integer)

3. A database for storing intermediate data
   - SQLite (simplest option)
   - PostgreSQL (better for large migrations)

## Running a Migration

You can run migrations using either the CLI directly or Docker Compose for a containerized approach.

### Basic Migration Command

The simplest way to run a migration is:

```bash
# Using SQLite database
ztoq migrate run \
  --zephyr-base-url "https://api.adaptavist.io/tm4j/v2" \
  --zephyr-api-token "your-zephyr-token" \
  --zephyr-project-key "DEMO" \
  --qtest-base-url "https://yourcompany.qtestnet.com" \
  --qtest-username "your-username" \
  --qtest-password "your-password" \
  --qtest-project-id 12345 \
  --db-type sqlite \
  --db-path "./migration.db"
```

### Using PostgreSQL

For larger migrations, PostgreSQL is recommended:

```bash
ztoq migrate run \
  --zephyr-base-url "https://api.adaptavist.io/tm4j/v2" \
  --zephyr-api-token "your-zephyr-token" \
  --zephyr-project-key "DEMO" \
  --qtest-base-url "https://yourcompany.qtestnet.com" \
  --qtest-username "your-username" \
  --qtest-password "your-password" \
  --qtest-project-id 12345 \
  --db-type postgresql \
  --host "localhost" \
  --port 5432 \
  --username "postgres" \
  --password "your-pg-password" \
  --database "ztoq_migration"
```

### Performance Tuning

You can adjust batch size and parallelism for better performance:

```bash
ztoq migrate run \
  # ... other options
  --batch-size 100 \
  --max-workers 10
```

### Running Specific Phases

You can run specific phases of the migration:

```bash
# Only extract data from Zephyr
ztoq migrate run \
  # ... other options
  --phase extract

# Only transform already extracted data
ztoq migrate run \
  # ... other options
  --phase transform

# Only load already transformed data into qTest
ztoq migrate run \
  # ... other options
  --phase load
```

### Handling Attachments

To include attachments in the migration:

```bash
ztoq migrate run \
  # ... other options
  --attachments-dir "./attachments"
```

## Monitoring Migration Status

Check the status of an ongoing or completed migration:

```bash
# For SQLite
ztoq migrate status \
  --db-type sqlite \
  --db-path "./migration.db" \
  --project-key "DEMO"

# For PostgreSQL
ztoq migrate status \
  --db-type postgresql \
  --host "localhost" \
  --port 5432 \
  --username "postgres" \
  --password "your-pg-password" \
  --database "ztoq_migration" \
  --project-key "DEMO"
```

## Database Management

Initialize or update the migration database schema:

```bash
# Initialize SQLite database
ztoq db init \
  --db-type sqlite \
  --db-path "./migration.db"

# Initialize PostgreSQL database
ztoq db init \
  --db-type postgresql \
  --host "localhost" \
  --port 5432 \
  --username "postgres" \
  --password "your-pg-password" \
  --database "ztoq_migration"
```

View database statistics:

```bash
ztoq db stats \
  --db-type sqlite \
  --db-path "./migration.db" \
  --project-key "DEMO"
```

## Troubleshooting

### Common Issues

1. **API Connection Failures**
   - Verify your Zephyr and qTest API credentials
   - Check network connectivity

2. **Database Errors**
   - Ensure the database exists and is accessible
   - Make sure the schema is initialized with `ztoq db init`

3. **Migration Failures**
   - Check the error message with `ztoq migrate status`
   - Fix the issue and resume the migration

4. **Performance Issues**
   - Increase batch size for faster processing
   - Increase max_workers for more parallelism
   - Use PostgreSQL for large migrations

### Logs

Enable debug logs for more detailed information:

```bash
export ZTOQ_LOG_LEVEL=DEBUG
ztoq migrate run # ... options
```

## Best Practices

1. **Test on a Small Project First**
   - Run a migration on a small project before attempting large ones

2. **Use Dry Run Mode**
   - Test migrations without actually writing to qTest

3. **Database Backups**
   - Back up your migration database regularly

4. **Phased Approach**
   - Consider running each phase separately for large migrations

5. **Monitor Resources**
   - Watch CPU, memory, and disk usage during migrations

## Using Docker for Migration

For a containerized approach that simplifies dependency management and provides better isolation, you can use Docker Compose to run migrations.

### Setup

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/yourusername/ztoq.git
   cd ztoq
   ```

2. Copy the example environment file and update it with your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your Zephyr and qTest credentials
   ```

3. Make the migration script executable:
   ```bash
   chmod +x run-migration.sh
   ```

4. Run the setup command to create the necessary directories and initialize the database:
   ```bash
   ./run-migration.sh setup
   ```

### Running Migration with Docker

The `run-migration.sh` script provides a convenient interface for running migrations:

```bash
# Run a full migration
./run-migration.sh run

# Run only the extraction phase
./run-migration.sh run --phase extract

# Customize batch size and worker count
./run-migration.sh run --batch-size 100 --workers 8

# Use a different environment file
./run-migration.sh run --env-file ./prod.env
```

### Monitoring and Reporting

ZTOQ provides comprehensive monitoring and reporting tools for migrations:

#### Real-time Dashboard

Start a web-based real-time monitoring dashboard:

```bash
./run-migration.sh dashboard
```

This launches an interactive dashboard on port 5000 (default) showing:
- Overall migration progress
- Entity counts and status
- Batch processing statistics
- Visual charts and graphs
- Recent activity log

You can customize the dashboard:
```bash
# Change port and refresh interval
./run-migration.sh dashboard --port 8080 --refresh 15
```

Access the dashboard in your browser at `http://localhost:5000` (or your custom port).

#### Migration Status

For a quick status check via the command line:

```bash
./run-migration.sh status
```

#### Detailed Reports

Generate comprehensive migration reports in multiple formats:

```bash
# Generate HTML report with visualizations
./run-migration.sh report
```

The report includes:
- Migration state summary
- Entity counts and completion percentages
- Batch processing statistics
- Timing information
- Failure details
- Data visualizations

Reports are saved to the `./reports` directory.

### Cleaning Up

```bash
# Stop all containers
./run-migration.sh stop

# Remove containers while keeping data
./run-migration.sh clean

# Remove everything including data
./run-migration.sh purge
```

### Docker Compose Configuration

The migration Docker setup includes:

1. A migration service for running the ETL process
2. A migration-status service for checking migration status
3. A migration-report service for generating detailed reports
4. A PostgreSQL database for storing migration data
5. A pgAdmin interface for database management

Advanced users can modify the `docker-compose.migration.yml` file directly for more customization.

## Next Steps

After completing a migration:

1. Verify data in qTest
2. Run validation scripts
3. Update references in other systems
4. Document the migration in your project records
5. Archive the migration database for future reference