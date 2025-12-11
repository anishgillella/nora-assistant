# Data Ingestion Pipeline

This folder contains scripts for scraping, processing, and ingesting data into Nora's backend.

## Structure
- `process.py`: Main script for LLM processing and database population.
- `reset.py`: Script for resetting databases and experimental scraping.
- `scrape/`: Stores raw scraped markdown files.
- `data/`: Stores processed JSON data (`browsing_history.json`, `products.json`) served by the API.

## Usage

**Run from the project root:**

### 1. Process Data (LLM + Vector Store)
Extract structured data from scraped files and populate Pinecone/JSON:
```bash
python backend/data_ingestion/process.py
```
Options:
- `--retry`: Only process files that failed or are new.
- `--dry-run`: Preview what would be processed without making LLM calls.

### 2. Reset / Scrape (Experimental)
Clear all data or run fresh scrapes:
```bash
# Wipe all databases (Pinecone, SQLite, JSON)
python backend/data_ingestion/reset.py

# Scrape browsing history & Shopify (no LLM processing)
python backend/data_ingestion/reset.py --scrape
```
