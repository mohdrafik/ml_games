# Streamlit Machine Learning Demo App

An interactive, multi-page Streamlit web application designed to demonstrate and visualize various Machine Learning (ML) algorithms in real-time, including Regression, Clustering, and Neural Networks.

---

## 📌 Project Overview

This repository provides a modular, production-ready blueprint for deploying Machine Learning models via Streamlit. It includes synthetic data generation, dynamic evaluation metrics, interactive charting components, and configurations ready for cloud deployment (via Heroku, Railway, etc.).

### Key Features
* **Multi-Page Navigation:** Separate interactive dashboards for individual ML algorithms.
* **Modular UI Components:** Reusable charts, sidebars, and metric cards to keep code DRY.
* **Production Configurations:** Pre-configured deployment files (`Procfile`, `railway.json`, `packages.txt`).

---

## 🏗️ Repository Architecture

Below is the workflow and data flow mapping how the app's components interact with each other:

```mermaid
graph TD
    A[main.py] --> B[pages/]
    B -->|1. Linear Regression| C[Regression Models]
    B -->|2. Polynomial Regression| C
    B -->|3. KMeans Clustering| D[Clustering Models]
    B -->|4. Neural Networks| E[Deep Learning]
    
    F[utils/] -->|Generates Data & Preprocesses| B
    G[components/] -->|Renders UI, Sidebars & Charts| B
    H[models/] -->|Saves & Loads Weights| B
    
    style A fill:#4CAF50,stroke:#333,stroke-width:2px,color:#fff
    style B fill:#2196F3,stroke:#333,stroke-width:2px,color:#fff

```

---

## 📂 Directory Structure & Module Breakdown

| Directory/File | Description | Key Contents / Responsibility |
| --- | --- | --- |
| **`app/`** | Core application root | Houses all application logic, views, and assets. |
| ├── `main.py` | App Entry Point | The main landing page launching the Streamlit server. |
| ├── `pages/` | Algorithm Dashboards | Dedicated UIs for Linear/Poly Regression, KMeans, and NNs. |
| ├── `components/` | Reusable UI Elements | `charts.py` (plotting), `sidebar.py`, and `metrics.py`. |
| ├── `utils/` | Helper Utilities | Synthetic `data_generator.py`, preprocessing, and model loading. |
| ├── `models/` | Model Storage & Logic | Saved weights (`trained_models/`) and training logic scripts. |
| ├── `assets/` | Static Styling | Images, custom CSS overrides, and UI animations. |
| └── `config/` | Application Settings | Global variables, model hyperparameter bounds, and themes. |
| **`requirements.txt`** | Python Dependencies | Standard pip package management file. |
| **`Procfile` / `railway.json**` | Deployment Configs | Orchestration setups for platform hosting (Heroku / Railway). |
| **`packages.txt`** | System Dependencies | Apt-get packages required for Linux environments (e.g., OpenCV, Graphviz). |

---

## 📊 Codebase Distribution Analysis

The following chart illustrates the functional focus of the codebase files within the `app/` ecosystem, showcasing the architectural split between UI logic, ML modeling, and backend utilities:

```text
[Module Type]     [File Count Allocation]
──────────────────────────────────────────────────────────
Pages / Views     ■■■■■■■■■■■■■■■■■■ 4 Files (25%)
Utilities         ■■■■■■■■■■■■■■■■■■ 4 Files (25%)
UI Components     ■■■■■■■■■■■■■ 3 Files (18.75%)
Models / Logic    ■■■■■■■■■■■■■ 2 Files (12.5%)
Configuration     ■■■■■■■■■■■■■ 2 Files (12.5%)
Main Entry        ■■■■ 1 File (6.25%)
──────────────────────────────────────────────────────────
Total Monitored App Components: 16 Files (100%)

```

---

## 🚀 Getting Started

### 1. Prerequisites

Ensure you have Python 3.9+ installed.

### 2. Installation & Setup

Clone the repository, create a virtual environment, and install the required dependencies:

```bash
# Navigate to project root
cd streamlit_ml_demo

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt

```

### 3. Running the App Locally

Launch the application server using the following command:

```bash
streamlit run app/main.py

```