# OpenSearch Sensor Ingestion Pipeline

A CDK-based AWS project for ingesting temperature sensor data, storing it in Amazon S3, and indexing it in Amazon OpenSearch for analytics.

---

## 📦 Features

- REST API endpoint via Amazon API Gateway
- Real-time ingestion with AWS Lambda (Python 3.13)
- Secure storage of raw data in S3 (versioned, encrypted)
- Indexed search and analytics via OpenSearch
- Environment-specific configuration via `.env`
- Modular CDK deployment with support for `local`, `dev`, `sbx`, `uat`, `acpt`, `prod`

---

## 🧱 Architecture

```
Client → API Gateway → Lambda Function
       ↘︎ S3 (raw JSON storage)
       ↘︎ OpenSearch (index for search/analytics)
```

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/your-org/opensearch-sensor-ingest.git
cd opensearch-sensor-ingest
```

### 2. Install dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3. Setup local environment
Create `.env` in the `src/` folder:
```env
ENVIRONMENT=sbx
AWS_PROFILE=sbx-sso
AWS_BUCKET_NAME=data-lake-week2-sbx
AWS_REGION=us-east-1
IPV4_ALLOWED=1.2.3.4/32
```

### 4. Bootstrap & Deploy (CDK)
```bash
cdk bootstrap
cdk deploy OpensearchStack
```

---

## 📂 Project Structure
```
├── app.py                 # CDK App entrypoint
├── opensearch
|   └──opensearch_stack.py # CDK stack definition
└── src/                   # Lambda code and .env
|   ├── .env               # environment variables
|   ├── lambda.py          # Lambda handler logic
|   ├── common.py          # Shared utilities and config loader
|   └── requirements.txt   # lambda layer dependencies
├── requirements-dev.txt   # CDK local development Python dependecies
└── requirements.txt       # CDK deployment Python dependencies
```

---

## 🔧 Environment Support
| ENVIRONMENT | QUALIFIER        |
|-------------|------------------|
| local       | -                |
| dev         | tciedadev        |
| sbx         | tciedasbx0       |
| uat, acpt   | openweather      |
| prod        | tciedaprod       |

---

## 🔐 Security
- API Gateway: CORS enabled, no auth (for now)
- S3: Versioned, encrypted, access controlled by IAM
- OpenSearch: HTTPS, IP-restricted access, IAM-based

---

## 📬 Example Request
```json
POST /sensor
{
  "sensorID": "sensor1",
  "temperature": 25.3
}
```

---

## 📊 Output Sample
- S3 Object: `sensor1-20240420T010203.json`
- OpenSearch Index: `lambda-s3-index/_doc`

---

## 🧼 Lifecycle Rules (S3)
- Expire after 30 days
- Abort multipart uploads after 7 days
- Non-current versions expire after 7 days

---

## 📞 Support
For questions or enhancements, contact: `jerry.liu@example.com`

---

## 📜 License
MIT License © 2025 Jerry Liu

