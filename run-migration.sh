#!/bin/bash
set -e

# Help text
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
  echo "ZTOQ Migration Runner Script"
  echo ""
  echo "This script simplifies running the Zephyr Scale to qTest migration using Docker Compose."
  echo ""
  echo "Usage:"
  echo "  ./run-migration.sh [COMMAND] [OPTIONS]"
  echo ""
  echo "Commands:"
  echo "  run         Run the migration (default if no command provided)"
  echo "  status      Check migration status"
  echo "  report      Generate a migration report"
  echo "  dashboard   Start a web-based migration monitoring dashboard"
  echo "  setup       Create necessary directories and initialize the database"
  echo "  stop        Stop all containers"
  echo "  clean       Remove containers, networks, and volumes (keeps data)"
  echo "  purge       Remove all containers, networks, volumes, and data"
  echo ""
  echo "Options:"
  echo "  --env-file FILE    Specify an environment file (default: .env)"
  echo "  --batch-size N     Set batch size for migration (default: 50)"
  echo "  --workers N        Set number of parallel workers (default: 5)"
  echo "  --phase PHASE      Set migration phase to run (extract, transform, load, all)"
  echo "  --port N           Set port for dashboard (default: 5000)"
  echo "  --refresh N        Set dashboard refresh interval in seconds (default: 30)"
  echo "  --help, -h         Show this help message"
  echo ""
  echo "Example:"
  echo "  ./run-migration.sh run --env-file ./my-project.env --batch-size 100 --workers 8"
  echo "  ./run-migration.sh dashboard --port 8080 --refresh 15"
  exit 0
fi

# Set default values
COMMAND=${1:-run}
shift 2>/dev/null || true

# Process options
ENV_FILE=".env"
BATCH_SIZE="50"
MAX_WORKERS="5"
PHASE=""
PORT="5000"
REFRESH="30"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --batch-size)
      BATCH_SIZE="$2"
      shift 2
      ;;
    --workers)
      MAX_WORKERS="$2"
      shift 2
      ;;
    --phase)
      PHASE="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --refresh)
      REFRESH="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check for .env file
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: Environment file $ENV_FILE not found."
  echo "Please create an environment file with your Zephyr and qTest credentials."
  echo "Example .env file contents:"
  echo "ZEPHYR_BASE_URL=https://api.zephyrscale.example.com/v2"
  echo "ZEPHYR_API_TOKEN=your-zephyr-token"
  echo "ZEPHYR_PROJECT_KEY=DEMO"
  echo "QTEST_BASE_URL=https://example.qtestnet.com"
  echo "QTEST_USERNAME=your-username"
  echo "QTEST_PASSWORD=your-password"
  echo "QTEST_PROJECT_ID=12345"
  exit 1
fi

# Function to create directories
create_directories() {
  mkdir -p attachments
  mkdir -p migration_data
  mkdir -p reports
  chmod 777 attachments migration_data reports
  echo "Created directories: attachments, migration_data, reports"
}

# Run the requested command
case "$COMMAND" in
  run)
    if [ -n "$PHASE" ]; then
      PHASE_ARG="--phase $PHASE"
    else
      PHASE_ARG=""
    fi
    
    echo "Running migration with batch size $BATCH_SIZE and $MAX_WORKERS workers"
    
    docker-compose -f docker-compose.migration.yml --env-file "$ENV_FILE" run \
      migration migrate run \
      --batch-size "$BATCH_SIZE" \
      --max-workers "$MAX_WORKERS" \
      --attachments-dir /app/attachments $PHASE_ARG
    ;;
    
  status)
    echo "Checking migration status"
    docker-compose -f docker-compose.migration.yml --env-file "$ENV_FILE" run \
      migration-status
    ;;
    
  report)
    echo "Generating migration report"
    docker-compose -f docker-compose.migration.yml --env-file "$ENV_FILE" run \
      migration-report
    echo "Report saved to ./reports/migration-report.html"
    ;;
    
  dashboard)
    echo "Starting migration monitoring dashboard on port $PORT (refresh: $REFRESH seconds)"
    create_directories
    
    # Check if postgres is running
    if ! docker ps | grep -q postgres; then
      echo "Starting PostgreSQL database"
      docker-compose -f docker-compose.dashboard.yml --env-file "$ENV_FILE" up -d postgres
      
      # Wait for PostgreSQL to start
      echo "Waiting for PostgreSQL to start..."
      sleep 5
    fi
    
    # Start the dashboard
    docker-compose -f docker-compose.dashboard.yml --env-file "$ENV_FILE" run -p $PORT:$PORT \
      dashboard python -m ztoq.migration_dashboard \
      --project-key "${ZEPHYR_PROJECT_KEY}" \
      --port "$PORT" \
      --refresh "$REFRESH" \
      --db-type postgresql
    ;;
    
  setup)
    create_directories
    echo "Starting PostgreSQL database"
    docker-compose -f docker-compose.migration.yml --env-file "$ENV_FILE" up -d postgres
    
    # Wait for PostgreSQL to start
    echo "Waiting for PostgreSQL to start..."
    sleep 5
    
    echo "Initializing database schema"
    docker-compose -f docker-compose.migration.yml --env-file "$ENV_FILE" run \
      migration db init --db-type postgresql
    
    echo "Setup complete. You can now run the migration with:"
    echo "./run-migration.sh run"
    ;;
    
  stop)
    echo "Stopping all containers"
    docker-compose -f docker-compose.migration.yml --env-file "$ENV_FILE" stop
    docker-compose -f docker-compose.dashboard.yml --env-file "$ENV_FILE" stop 2>/dev/null || true
    ;;
    
  clean)
    echo "Removing containers and networks (keeping volumes and data)"
    docker-compose -f docker-compose.migration.yml --env-file "$ENV_FILE" down
    docker-compose -f docker-compose.dashboard.yml --env-file "$ENV_FILE" down 2>/dev/null || true
    ;;
    
  purge)
    echo "WARNING: This will remove all containers, networks, volumes, and data."
    read -p "Are you sure you want to continue? (y/N) " confirm
    if [[ "$confirm" == [yY] || "$confirm" == [yY][eE][sS] ]]; then
      echo "Removing all containers, networks, volumes, and data"
      docker-compose -f docker-compose.migration.yml --env-file "$ENV_FILE" down -v
      docker-compose -f docker-compose.dashboard.yml --env-file "$ENV_FILE" down -v 2>/dev/null || true
      rm -rf attachments/* migration_data/* reports/*
      echo "Purge complete."
    else
      echo "Purge cancelled."
    fi
    ;;
    
  *)
    echo "Unknown command: $COMMAND"
    echo "Run './run-migration.sh --help' for usage information."
    exit 1
    ;;
esac