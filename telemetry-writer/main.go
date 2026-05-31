package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
	_ "github.com/lib/pq"
)

// TelemetryPayload matches the Pydantic models in device-sim/src/models.py
type TelemetryPayload struct {
	DeviceID    string      `json:"device_id"`
	Timestamp   int64       `json:"timestamp"`
	Location    Location    `json:"location"`
	Status      string      `json:"status"`
	Destination string      `json:"destination"`
	Metrics     Metrics     `json:"metrics"`
	Diagnostics Diagnostics `json:"diagnostics"`
}

type Location struct {
	X          float64 `json:"x"`
	Y          float64 `json:"y"`
	HeadingDeg float64 `json:"heading_deg"`
}

type Metrics struct {
	BatterySocPct   float64 `json:"battery_soc_pct"`
	PayloadWeightKg float64 `json:"payload_weight_kg"`
	WifiRssiDbm     int     `json:"wifi_rssi_dbm"`
}

type Diagnostics struct {
	ErrorCode        int  `json:"error_code"`
	ObstacleDetected bool `json:"obstacle_detected"`
}

func main() {
	log.Println("Starting Go Telemetry Writer with PostgreSQL integration...")

	// 1. Initialize PostgreSQL connection
	db := initDatabase()
	defer db.Close()

	// 2. Setup Telemetry buffered channel (queue)
	// Holds up to 1000 messages in memory if database inserts experience temporary latency spikes
	telemetryChan := make(chan TelemetryPayload, 1000)
	defer close(telemetryChan)

	// 3. Start a pool of background DB writers (workers)
	// Spawns 5 concurrent worker routines to handle database ingestion independently from MQTT thread
	const numWorkers = 5
	for i := 1; i <= numWorkers; i++ {
		go dbWorker(i, db, telemetryChan)
	}

	// 4. Load configuration from environment variables
	brokerHost := getEnv("MQTT_BROKER_HOST", "localhost")
	brokerPortStr := getEnv("MQTT_BROKER_PORT", "1883")
	topic := getEnv("MQTT_TOPIC", "factory/telemetry")
	clientID := getEnv("MQTT_CLIENT_ID", "telemetry-writer")

	brokerPort, err := strconv.Atoi(brokerPortStr)
	if err != nil {
		log.Fatalf("Invalid MQTT_BROKER_PORT: %v", err)
	}

	brokerURI := fmt.Sprintf("tcp://%s:%d", brokerHost, brokerPort)
	log.Printf("Connecting to MQTT broker at %s", brokerURI)

	// Configure MQTT Client Options
	opts := mqtt.NewClientOptions()
	opts.AddBroker(brokerURI)
	opts.SetClientID(clientID)
	opts.SetCleanSession(true)
	opts.SetAutoReconnect(true)
	opts.SetConnectRetryInterval(5 * time.Second)

	// Message handling callback (strictly non-blocking)
	opts.SetDefaultPublishHandler(func(client mqtt.Client, msg mqtt.Message) {
		log.Printf("MQTT CALLBACK: Received message on topic %s with payload: %s", msg.Topic(), string(msg.Payload()))
		var payload TelemetryPayload
		if err := json.Unmarshal(msg.Payload(), &payload); err != nil {
			log.Printf("Error unmarshalling telemetry payload: %v | Raw: %s", err, string(msg.Payload()))
			return
		}

		// Push payload into the buffered channel non-blocking-ly.
		// If the database is completely locked/down and the buffer fills up,
		// we drop the message to prevent freezing the MQTT thread.
		select {
		case telemetryChan <- payload:
			// Pushed successfully
		default:
			log.Println("WARNING: Telemetry buffer queue is full! Dropping telemetry packet to prevent MQTT blockage.")
		}
	})

	// Establish connection
	client := mqtt.NewClient(opts)
	if token := client.Connect(); token.Wait() && token.Error() != nil {
		log.Fatalf("Error connecting to MQTT Broker: %v", token.Error())
	}
	log.Println("Successfully connected to MQTT Broker!")

	// Subscribe to topic
	log.Printf("Subscribing to topic: %s", topic)
	if token := client.Subscribe(topic, 1, nil); token.Wait() && token.Error() != nil {
		log.Fatalf("Error subscribing to topic: %v", token.Error())
	}
	log.Printf("Successfully subscribed to topic: %s", topic)

	// Keep service running until OS interrupt signal received
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	log.Println("Shutting down Go Telemetry Writer gracefully...")
	client.Disconnect(250)
	log.Println("Disconnected. Goodbye!")
}

// initDatabase establishes a connection pool to PostgreSQL and creates the telemetry table if missing
func initDatabase() *sql.DB {
	host := getEnv("DB_HOST", "postgres")
	if host == "postgres-service" || host == "localhost" {
		log.Printf("Overriding DB_HOST '%s' to 'postgres'", host)
		host = "postgres"
	}
	portStr := getEnv("DB_PORT", "5432")
	user := getEnv("DB_USER", "postgres")
	password := getEnv("DB_PASSWORD", "postgres123")
	dbname := getEnv("DB_NAME", "telemetry")
	sslmode := getEnv("DB_SSLMODE", "disable")

	port, err := strconv.Atoi(portStr)
	if err != nil {
		log.Fatalf("Invalid DB_PORT: %v", err)
	}

	psqlInfo := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=%s connect_timeout=10",
		host, port, user, password, dbname, sslmode)

	log.Printf("Connecting to PostgreSQL at %s:%d...", host, port)

	// Establish a database connection pool
	db, err := sql.Open("postgres", psqlInfo)
	if err != nil {
		log.Fatalf("Error opening database connection pool: %v", err)
	}

	// Set connection pool settings
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)

	// Retry connection until DB is ready
	for i := 1; i <= 6; i++ {
		err = db.Ping()
		if err == nil {
			break
		}
		if i == 6 {
			log.Fatalf("Failed to ping PostgreSQL database after 30 seconds: %v", err)
		}
		log.Printf("Database not ready yet (attempt %d/6), retrying in 5 seconds...", i)
		time.Sleep(5 * time.Second)
	}

	log.Println("Successfully connected to PostgreSQL database!")

	// Create table if it doesn't exist
	schema := `
	CREATE TABLE IF NOT EXISTS telemetry (
		id SERIAL PRIMARY KEY,
		device_id VARCHAR(100) NOT NULL,
		timestamp TIMESTAMPTZ NOT NULL,
		status VARCHAR(50) NOT NULL,
		destination VARCHAR(100) NOT NULL,
		x DOUBLE PRECISION NOT NULL,
		y DOUBLE PRECISION NOT NULL,
		heading_deg DOUBLE PRECISION NOT NULL,
		battery_soc_pct DOUBLE PRECISION NOT NULL,
		payload_weight_kg DOUBLE PRECISION NOT NULL,
		wifi_rssi_dbm INTEGER NOT NULL,
		error_code INTEGER NOT NULL,
		obstacle_detected BOOLEAN NOT NULL,
		created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
	);
	CREATE INDEX IF NOT EXISTS idx_telemetry_device_time ON telemetry (device_id, timestamp DESC);
	`
	_, err = db.Exec(schema)
	if err != nil {
		log.Fatalf("Failed to initialize database schema: %v", err)
	}
	log.Println("Database schema checked & initialized successfully.")

	return db
}

// dbWorker runs indefinitely, consuming telemetry payloads from the channel and saving them to the DB
func dbWorker(workerID int, db *sql.DB, ch <-chan TelemetryPayload) {
	log.Printf("Background DB Writer Worker #%d started.", workerID)

	// Pre-compile the SQL statement for maximum performance
	stmt, err := db.Prepare(`
		INSERT INTO telemetry (
			device_id, timestamp, status, destination, x, y, heading_deg,
			battery_soc_pct, payload_weight_kg, wifi_rssi_dbm,
			error_code, obstacle_detected
		) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
	`)
	if err != nil {
		log.Fatalf("Worker #%d: Failed to prepare insert statement: %v", workerID, err)
	}
	defer stmt.Close()

	for payload := range ch {
		t := time.Unix(payload.Timestamp, 0)

		_, err := stmt.Exec(
			payload.DeviceID,
			t,
			payload.Status,
			payload.Destination,
			payload.Location.X,
			payload.Location.Y,
			payload.Location.HeadingDeg,
			payload.Metrics.BatterySocPct,
			payload.Metrics.PayloadWeightKg,
			payload.Metrics.WifiRssiDbm,
			payload.Diagnostics.ErrorCode,
			payload.Diagnostics.ObstacleDetected,
		)
		if err != nil {
			log.Printf("Worker #%d DB Write Error: %v", workerID, err)
			continue
		}

		log.Printf("Worker #%d persisted telemetry for: %s (Battery: %.1f%%)", workerID, payload.DeviceID, payload.Metrics.BatterySocPct)
	}
}

// Helper to read env variables with defaults
func getEnv(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}
