# ETL Migration Workflow Orchestration

The ETL (Extract, Transform, Load) migration workflow orchestration system is a comprehensive framework for managing the migration of test data from Zephyr Scale to qTest. This document explains the workflow orchestration architecture, usage, and configuration.

## Architecture

The workflow orchestration system is built around these key components:

1. **Workflow Orchestrator**: Coordinates the different phases of the migration workflow, manages state, and handles errors and retries.
2. **Workflow CLI**: Provides command-line interfaces for running, monitoring, and managing workflows.
3. **Event System**: Tracks and records events throughout the workflow execution for monitoring and reporting.
4. **Database Integration**: Uses the database factory to connect to either SQLite or PostgreSQL for state persistence.
5. **Validation Framework**: Integrates with the validation system to verify the integrity of migrated data.

## Workflow Phases

The ETL migration workflow consists of four main phases:

1. **Extract**: Fetches data from Zephyr Scale API and stores it in the database
2. **Transform**: Transforms the extracted data to match qTest's data model
3. **Load**: Uploads the transformed data to qTest API
4. **Validate**: Verifies the integrity of the migrated data

Each phase can be run independently or together as part of a complete workflow.

## CLI Commands

The workflow orchestration system provides several CLI commands:

### Run Workflow

```bash
ztoq workflow run --project-key PROJECT_KEY [options]
```

Runs the ETL migration workflow for a project, with options to specify which phases to run, database configuration, and output settings.

### Resume Workflow

```bash
ztoq workflow resume --project-key PROJECT_KEY [options]
```

Resumes an interrupted or failed workflow, picking up from where it left off.

### Check Status

```bash
ztoq workflow status --project-key PROJECT_KEY [options]
```

Displays the current status of a workflow, including progress, entity counts, and any issues.

### Create Report

```bash
ztoq workflow report --project-key PROJECT_KEY --output-file REPORT_PATH [options]
```

Generates a comprehensive report of the workflow execution in JSON, HTML, or text format.

### Validate Migration

```bash
ztoq workflow validate --project-key PROJECT_KEY [options]
```

Runs validation checks on the migrated data, even if the workflow was run without validation.

### Clean Up Workflow Data

```bash
ztoq workflow cleanup --project-key PROJECT_KEY [options]
```

Removes workflow data from the database and attachment storage, allowing for a fresh migration.

## Configuration Options

### Database Configuration

The workflow orchestration system supports both SQLite and PostgreSQL databases:

```bash
# SQLite
--db-type sqlite --db-path /path/to/database.db

# PostgreSQL
--db-type postgresql --host localhost --port 5432 --username postgres --password password --database ztoq
```

### API Configuration

For Zephyr Scale:

```bash
--zephyr-base-url https://api.zephyrscale.com/v2 --zephyr-api-token YOUR_TOKEN
```

For qTest:

```bash
--qtest-base-url https://your-instance.qtestnet.com/api/v3 --qtest-username YOUR_USERNAME --qtest-password YOUR_PASSWORD --qtest-project-id PROJECT_ID
```

### Workflow Options

```bash
--phases extract transform load validate  # Specify phases to run
--batch-size 50                          # Number of items per batch
--max-workers 5                          # Number of concurrent workers
--no-validation                          # Disable validation
--attachments-dir /path/to/attachments   # Directory for attachments
--output-dir /path/to/outputs            # Directory for output files
```

## Recovery and Error Handling

The workflow orchestration system includes robust error handling and recovery:

1. **Checkpointing**: State is saved after each phase and batch, allowing workflows to be resumed from the point of failure.
2. **Batch Processing**: Entities are processed in batches, reducing the impact of errors.
3. **Retry Logic**: Failed operations can be retried with exponential backoff.
4. **Error Recording**: Errors are recorded in the database with detailed context.
5. **Transaction Management**: Database operations use transactions to maintain consistency.

## Monitoring and Reporting

The workflow orchestration system provides several monitoring and reporting features:

1. **Real-time Progress**: Progress bars show real-time status during execution.
2. **Status Command**: The `status` command displays the current state.
3. **Event Logging**: All events are logged to the database and can be viewed.
4. **Comprehensive Reports**: Generate detailed reports in various formats.
5. **Validation Summary**: See validation results with issue counts by severity.

## Example Usage

### Basic Workflow Execution

```bash
ztoq workflow run \
  --project-key PROJ \
  --zephyr-base-url https://api.zephyrscale.com/v2 \
  --zephyr-api-token YOUR_TOKEN \
  --qtest-base-url https://your-instance.qtestnet.com/api/v3 \
  --qtest-username YOUR_USERNAME \
  --qtest-password YOUR_PASSWORD \
  --qtest-project-id 12345 \
  --output-dir /path/to/reports
```

### Resume a Failed Workflow

```bash
ztoq workflow resume \
  --project-key PROJ \
  --zephyr-base-url https://api.zephyrscale.com/v2 \
  --zephyr-api-token YOUR_TOKEN \
  --qtest-base-url https://your-instance.qtestnet.com/api/v3 \
  --qtest-username YOUR_USERNAME \
  --qtest-password YOUR_PASSWORD \
  --qtest-project-id 12345
```

### Generate a Report

```bash
ztoq workflow report \
  --project-key PROJ \
  --output-file migration_report.html \
  --report-format html
```

## Extending the Workflow

The workflow orchestration system is designed to be extensible:

1. **Custom Validation Rules**: Add new validation rules to check specific aspects of the migration.
2. **Additional Phases**: New phases can be added to the workflow for specialized processing.
3. **Alternative Backends**: Support for different database backends can be added.
4. **Integration Points**: The system can be integrated with monitoring, alerting, and other tools.

## Performance Considerations

For large migrations, consider the following:

1. **PostgreSQL**: Use PostgreSQL instead of SQLite for better performance and concurrency.
2. **Batch Size**: Adjust the batch size based on the entity size and API rate limits.
3. **Worker Count**: Increase the number of workers for parallel processing.
4. **Memory Usage**: Monitor memory usage, especially during the transform phase.
5. **Validation**: Consider running validation as a separate step for very large migrations.

## Troubleshooting

Common issues and their solutions:

1. **Connection Errors**: Check API credentials and network connectivity.
2. **Timeout Errors**: Increase timeouts or decrease batch size.
3. **Memory Errors**: Reduce batch size or increase available memory.
4. **Data Integrity Issues**: Check validation reports for details.
5. **Incomplete Migrations**: Use the resume command to continue from the point of failure.
