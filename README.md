# InfraWatch

Linux server monitoring system built with Python.

The project collects system metrics from Linux servers and is designed to provide a centralized way to monitor infrastructure without manually connecting to each server.

## Current Features

* CPU usage monitoring via `/proc/stat`
* Memory usage monitoring via `/proc/meminfo`
* Disk usage monitoring
* Network traffic and speed monitoring via `/proc/net/dev`
* Structured system metrics collection
* Logging with Python `logging`

## Architecture


Linux Server -> Python Agent -> FastAPI -> Redis & MongoDB & ClickHouse

## Tech Stack

* Python
* Linux
* FastAPI
* Redis
* MongoDB
* ClickHouse
* Docker
* Kubernetes

## Project Status

🚧 Work in progress.

The current stage focuses on building the Linux monitoring agent. The next steps include integrating the FastAPI backend, storing metrics, containerization, and deploying the system with Kubernetes.
