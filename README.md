# 🚨 Drug Shortage Early-Warning Stack (Public Health Analytics)

An end-to-end data engineering and analytics pipeline that ingests public health data from the openFDA API, stores it in a relational PostgreSQL star schema, processes statistical anomalies in Python, and surfaces supply chain risk profiles inside Power BI.

## 📊 Dashboard Preview
![Dashboard Preview](dashboard_screenshot.png)

## 🛠️ Tech Stack & Architecture
* **Ingestion Layer:** Python (`requests`, `pandas`) interacting with paginated openFDA endpoints.
* **Storage & Modeling:** PostgreSQL Data Warehouse utilizing a specialized relational Star Schema.
* **Analytics Engine:** Python (`SQLAlchemy`, `numpy`) executing rolling statistical Z-Score anomaly detection.
* **BI / Visualization:** Power BI Desktop connected via active imports mapping data infrastructure.

## 🚀 Setup & Execution Instructions

### 1. Clone the Workspace
```bash
git clone [https://github.com/YOUR_USERNAME/drug-shortage-alert.git](https://github.com/YOUR_USERNAME/drug-shortage-alert.git)
cd drug-shortage-alert