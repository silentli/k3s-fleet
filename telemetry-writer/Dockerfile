# Build Stage
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Copy dependency configs
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY main.go ./

# Build a statically linked, optimized binary for Linux
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o telemetry-writer main.go

# Final Runtime Stage
FROM alpine:3.19

WORKDIR /app

# Copy the statically compiled binary from the builder stage
COPY --from=builder /app/telemetry-writer .

# Run the binary
CMD ["./telemetry-writer"]
