# Scheduled and CI/CD Migrations

This document explains how to set up and use automated migrations through GitHub Actions.

## Overview

ZTOQ supports automated and scheduled migrations through GitHub Actions workflows. This enables:

- Running migrations on a schedule (e.g., daily, weekly)
- Triggering migrations from CI/CD pipelines
- Automating migration steps for consistent results
- Generating and distributing reports automatically
- Handling multiple projects in sequence

## Workflow Triggers

The scheduled migration workflow can be triggered in multiple ways:

1. **Scheduled Runs**
   - Automatically runs daily at 2:00 AM UTC (configurable)
   - Processes projects specified in `migration-config/projects.txt`

2. **Manual Triggers**
   - Start a migration manually from the GitHub Actions UI
   - Configure all parameters through the workflow interface

3. **Repository Dispatch Events**
   - Trigger migrations programmatically from other workflows or external systems
   - Send configuration parameters as part of the trigger event

4. **Push Events**
   - Optionally trigger migrations when changes are pushed to specific files
   - Set up in the `migration-trigger` branch by default

## Setting Up Scheduled Migrations

### 1. Configure Project List

Create a file called `migration-config/projects.txt` with the list of Zephyr project keys to migrate:

```
# Projects to migrate (one per line)
# Blank lines and comments are ignored
PROJECT1
PROJECT2
PROJECT3
```

For scheduled runs, projects will be processed in order, one at a time.

### 2. Configure GitHub Secrets

Set up the following secrets in your GitHub repository:

#### Required Secrets

| Secret Name | Description |
|-------------|-------------|
| `ZEPHYR_BASE_URL` | Zephyr Scale API base URL |
| `ZEPHYR_API_TOKEN` | Zephyr Scale API token |
| `QTEST_BASE_URL` | qTest API base URL |
| `QTEST_USERNAME` | qTest username |
| `QTEST_PASSWORD` | qTest password |
| `QTEST_PROJECT_ID` | qTest project ID |

#### For Multi-project Support

| Secret Name | Description |
|-------------|-------------|
| `DEFAULT_ZEPHYR_PROJECT_KEY` | Default project if no list is provided |
| `REPO_ACCESS_TOKEN` | GitHub token with workflow trigger permissions |

#### For Notifications

| Secret Name | Description |
|-------------|-------------|
| `SMTP_SERVER` | Email server address |
| `SMTP_PORT` | Email server port |
| `SMTP_USERNAME` | Email account username |
| `SMTP_PASSWORD` | Email account password |
| `NOTIFICATION_EMAIL` | Email address to receive reports |
| `SLACK_WEBHOOK_URL` | Slack webhook URL for notifications |

### 3. Configure Schedule (Optional)

Edit the cron schedule in `.github/workflows/scheduled-migration.yml` to change when migrations run:

```yaml
schedule:
  # Format: minute hour day-of-month month day-of-week
  # This example runs at 2:00 AM UTC daily
  - cron: '0 2 * * *'
```

Common scheduling patterns:

- Daily at 2:00 AM: `0 2 * * *`
- Weekly on Sunday at midnight: `0 0 * * 0`
- Monthly on the 1st at 3:00 AM: `0 3 1 * *`

## Running Migrations Manually

To run a migration manually:

1. Go to the GitHub repository
2. Click on "Actions" tab
3. Select "Scheduled Migration" workflow
4. Click "Run workflow" button
5. Fill in the parameters:
   - **Project Key**: Zephyr project key to migrate
   - **Batch Size**: Number of items per batch (default: 50)
   - **Max Workers**: Number of parallel workers (default: 5)
   - **Send Report**: Whether to send email reports
   - **Phase**: Migration phase to run (extract, transform, load, all)
6. Click "Run workflow" to start the migration

## Migration Reports

The workflow automatically generates comprehensive reports for each migration:

- HTML report with visualizations
- JSON data export
- CSV reports for data analysis

Reports are uploaded as workflow artifacts and can be:
- Downloaded from the GitHub Actions interface
- Sent via email to specified recipients
- Posted to Slack channels

## Custom Triggers

### Repository Dispatch Trigger

You can trigger migrations programmatically from other workflows or external systems using the repository dispatch event:

```bash
curl -X POST \
  https://api.github.com/repos/USERNAME/REPO/dispatches \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -d '{"event_type": "trigger-migration", "client_payload": {"project_key": "PROJECT1", "batch_size": "100", "max_workers": "8", "phase": "all", "send_report": true}}'
```

### Integration with Other Workflows

You can integrate the migration workflow with other CI/CD processes:

```yaml
jobs:
  # Other jobs...

  trigger-migration:
    name: Trigger Migration
    runs-on: ubuntu-latest
    needs: [previous-job]
    if: success()
    steps:
      - name: Trigger migration workflow
        uses: peter-evans/repository-dispatch@v2
        with:
          token: ${{ secrets.REPO_ACCESS_TOKEN }}
          event-type: trigger-migration
          client-payload: '{"project_key": "PROJECT1", "batch_size": "50", "max_workers": "5", "phase": "all", "send_report": true}'
```

## Multi-Project Migrations

For scheduled runs, the workflow supports migrating multiple projects in sequence:

1. Create `migration-config/projects.txt` with project keys (one per line)
2. When scheduled, the workflow processes the first project
3. After completion, it triggers another workflow run for the next project
4. This continues until all projects have been processed

This approach ensures:
- Each project has its own complete workflow run
- Failures in one project don't affect others
- Resources are allocated efficiently
- Reports are generated per project

## Workflow Steps

The migration workflow performs these steps:

1. **Preparation**
   - Sets up the environment and Python dependencies
   - Determines which project to migrate
   - Generates a unique migration ID for tracking

2. **Database Setup**
   - Launches a PostgreSQL database service
   - Initializes the database schema
   - Verifies the database connection

3. **Migration Execution**
   - Runs the specified migration phase
   - Handles API credentials securely
   - Preserves logs for debugging

4. **Reporting**
   - Generates comprehensive reports
   - Uploads reports as workflow artifacts
   - Sends notifications if configured

5. **Multi-Project Handling** *(for scheduled runs)*
   - Checks if there are more projects to process
   - Triggers the next migration if needed

## Monitoring Migrations

You can monitor migrations in several ways:

- **GitHub Actions Dashboard**: Shows workflow status and progress
- **Workflow Artifacts**: Contains logs and reports
- **Email Reports**: Sent after completion if configured
- **Slack Notifications**: Posted during and after runs if configured

## Best Practices

1. **Start Small**
   - Test with small projects before scheduling large migrations
   - Use the `--limit` parameter to process a subset of entities

2. **Optimize Performance**
   - Adjust batch size based on entity complexity
   - Set max workers based on available GitHub runner resources (typically 2 CPUs)

3. **Handle Credentials Securely**
   - Use GitHub Secrets for all sensitive information
   - Never commit credentials to the repository

4. **Monitor Resource Usage**
   - GitHub-hosted runners have resource limits (2-core CPU, 7GB RAM)
   - For very large projects, consider using self-hosted runners

5. **Test Manual Runs First**
   - Before setting up scheduled runs, test with manual triggers
   - Verify all configurations work as expected

## Troubleshooting

### Common Issues

1. **Workflow Timeouts**
   - GitHub Actions has a 6-hour timeout limit
   - For large migrations, break into phases (extract, transform, load)
   - Use smaller batch sizes to process more efficiently

2. **Database Connection Issues**
   - Check database service is running properly
   - Verify credentials and connection parameters
   - Look for PostgreSQL service logs in workflow output

3. **API Rate Limiting**
   - Check for rate limiting errors in the logs
   - Reduce max_workers to decrease concurrent API calls
   - Contact API providers to increase rate limits if needed

4. **Missing Reports**
   - Ensure SMTP credentials are correct
   - Check notification email for spam filters
   - Download reports directly from workflow artifacts

## Examples

### Example Configuration File

Here's an example `migration-config/projects.txt`:

```
# Format: one project key per line
# Lines starting with # are comments

# Active projects
PROJECT1
PROJECT2

# Projects pending migration (uncomment when ready)
# PROJECT3
# PROJECT4
```

### Example Workflow Customization

To customize workflow behavior, you can edit `.github/workflows/scheduled-migration.yml`:

```yaml
# Change schedule to run weekly on Sunday at 1:00 AM
schedule:
  - cron: '0 1 * * 0'

# Add path triggers for specific files
push:
  branches: [ main, develop ]
  paths:
    - 'migration-config/**'
    - 'ztoq/migration.py'
```

### Example Integration with Slack

For better Slack notifications, customize the message format:

```yaml
- name: Send Slack notification
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    fields: repo,message,workflow,job,commit,eventName
    text: |
      *Migration Report - ${{ needs.prepare.outputs.project_key }}*

      *Status:* ${{ needs.run-migration.outputs.status }}
      *Migration ID:* `${{ needs.prepare.outputs.migration_id }}`
      *Completed:* ${{ steps.set-timestamp.outputs.timestamp }}

      *Project Stats:*
      - Test Cases: 250 migrated
      - Test Cycles: 15 migrated
      - Executions: 120 migrated

      [View Full Report](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }})
```
