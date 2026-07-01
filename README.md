# PayFlow: High-Throughput Event-Driven Microservices

A production-ready, cloud-native financial transactions orchestration backend. This project showcases an asynchronous event-driven system architecture engineered with robust infrastructure isolation, high-concurrency database constraints, and full CI/CD automation pipelines.

## 🏗️ System & DevOps Architecture



### Engineering Design Breakdown
* **Order Service (FastAPI):** High-performance REST interface handling transaction ingest, executing reliable dual-write transactions to Postgres, and emitting state changes to an asynchronous bus.
* **Payment Worker (Python Native):** Concurrency-safe service utilizing advanced Row-Level Locking (`FOR UPDATE SKIP LOCKED`) to securely ingest and process pending payments while eliminating race conditions.
* **Notification Service (Python Native):** Asynchronous subscriber consuming system payloads out of decoupled communication streams.

---

## 🛠️ The DevOps Stack (Production-Grade)

This project completely bypasses manual setups by defining the entire application footprint using standard Infrastructure-as-Code (IaC) and pipeline design practices:

* **Infrastructure as Code:** Complete AWS environment (VPC, Private/Public isolated Subnets, NAT Gateways, Security Groups) fully defined using **Terraform Modules**.
* **Managed Data & Ingest:** Cloud-native **AWS RDS PostgreSQL 16** container database backed by a managed **AWS SQS** asynchronous message bus.
* **Serverless Containerization:** Packaged securely via **Multi-Stage Dockerfiles** dropping root privileges (`USER appuser`) and deployed on **AWS ECS Fargate**.
* **Automated CI/CD:** Orchestrated using **GitHub Actions** workflows to automatically run automated infrastructure checks, compile assets, build Docker layers, and securely distribute tags to **Amazon ECR** on every single `git push`.

---

## 🚀 Local Development Onboarding

### Prerequisites
* Docker & Docker Compose Installed

### Quick Start
1. Clone the repository and boot the ecosystem locally:
   ```bash
   docker compose up -d --build
