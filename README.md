# Chat AI CEI (Côte d'Ivoire 2025 Election Query System)

## Overview
Chat AI CEI is an intelligent agent designed to securely query the official 2025 Côte d'Ivoire national election results using Natural Language. Instead of relying on rigid dashboards, users can ask questions in plain French and immediately receive data tables or interactive charts.

## Core Features
1. **Level 1: Natural Language to SQL (NL2SQL)**
   - Automatically translates French questions into optimized DuckDB SQL queries.
   - Built-in guardrails specifically block destructive queries (`DROP`, `DELETE`) and Out-of-Scope questions.
   
2. **Level 2: Fuzzy Matching & RAG Pipeline**
   - Automatically handles typos in political parties, candidate names, or regions (e.g., querying "rhpd" instead of "RHDP", or "Alssane" instead of "KOFFI AKA CHARLES").
   - Implemented via a robust, offline ChromaDB vector store that embeds unique entities and dynamically corrects user prompts prior to SQL generation.

3. **Dynamic Data Visualization**
   - Incorporates an Intent Router that detects when a user asks for visualizations (e.g., "Génère un diagramme circulaire...").
   - Automatically pivots the SQL results into interactive Plotly charts.

4. **Bulletproof Data Ingestion**
   - Contains a custom PDF parsing engine designed to extract tabular data from the official CEI 35-page PDF document.
   - Successfully handles optical character recognition (OCR) anomalies like reversed vertical text and hidden blank columns to ensure 100% data fidelity.

## Technology Stack
- **Vector Database (RAG)**: ChromaDB (Local offline embedding model `all-MiniLM-L6-v2`)
- **Relational Database**: DuckDB (Lightning-fast analytical queries)
- **Web Interface**: Streamlit
- **Data Ingestion**: pdfplumber, Pandas

## Installation & Usage
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up the environment variables:
   Create a `.env` file in the root directory and add your Google API Key:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```
4. Ingest the PDF and build the databases (DuckDB & ChromaDB):
   ```bash
   python src/ingest_pdf.py
   ```
5. Launch the chat interface:
   ```bash
   streamlit run app.py
   ```
6. Run the Test Suite (Optional):
   ```bash
   pytest tests/test_agent.py -v
   ```
