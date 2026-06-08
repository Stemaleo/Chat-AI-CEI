import pdfplumber
import pandas as pd
import duckdb
import os
import re
import chromadb
from dotenv import load_dotenv

def parse_pdf_to_df(pdf_path):
    print(f"Parsing PDF: {pdf_path}")
    all_data = []
    
    # These are the expected columns based on visual inspection
    expected_headers = [
        "REGION", "CIRCONSCRIPTION", "NB BV", "INSCRITS", "VOTANTS", "TAUX DE PART.",
        "BULL. NULS", "SUF. EXPRIMES", "BULL. BLANCS NOMBRE", "BULL. BLANCS %",
        "GROUPEMENTS / PARTIS POLITIQUES", "CANDIDATS / LISTES DE CANDIDATS",
        "SCORES", "%", "ELU"
    ]
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"Processing page {i+1}/{len(pdf.pages)}...")
            
            # Extract tables. Depending on the PDF structure, extract_table() or extract_tables() might be needed
            tables = page.extract_tables()
            if not tables:
                continue
                
            for table in tables:
                for row in table:
                    # Clean up the row: replace newlines inside cells with spaces
                    clean_row = [str(cell).replace('\\n', ' ').strip() if cell else None for cell in row]
                    
                    # Skip header rows (we can identify them if they contain 'CIRCONSCRIPTION' or 'TOTAL')
                    if not clean_row or not any(clean_row):
                        continue
                    if clean_row[1] and 'CIRCONSCRIPTION' in clean_row[1].upper():
                        continue
                    if clean_row[1] and 'TOTAL' in clean_row[1].upper():
                        continue
                        
                    # There is a problem where the columns shift.
                    # The raw table from pdfplumber looks like this:
                    # ['REGI', '', None, '', '', '', 'TAUX DE', 'BULL.', 'SUF.', 'BULL. BLANCS', None, 'GROUPEMENTS / PARTIS', '', '', '', '']
                    # And row values like:
                    # [None, None, None, None, None, None, None, None, None, None, None, 'RHDP', 'KOFFI AKA CHARLES', '9 078', '66,35%', 'ELU(E)']
                    # This means the list size can be 16.
                    
                    # We will only keep the first 15 columns if it's longer than 15
                    # Wait, if we look at the raw row for RHDP:
                    # [None, None, None, None, None, None, None, None, None, None, None, 'RHDP', 'KOFFI AKA CHARLES', '9 078', '66,35%', 'ELU(E)']
                    # It has 16 items! The columns are:
                    # 0: REGION
                    # 1: CIRCONSCRIPTION
                    # 2: None (extra)
                    # 3: NB BV
                    # 4: INSCRITS
                    # 5: VOTANTS
                    # 6: TAUX DE PART.
                    # 7: BULL. NULS
                    # 8: SUF. EXPRIMES
                    # 9: BULL. BLANCS NOMBRE
                    # 10: BULL. BLANCS %
                    # 11: GROUPEMENTS / PARTIS POLITIQUES
                    # 12: CANDIDATS / LISTES DE CANDIDATS
                    # 13: SCORES
                    # 14: %
                    # 15: ELU
                    
                    # Notice how index 2 is completely empty and shifts everything to the right by 1!
                    if len(clean_row) >= 16:
                        # Drop index 2
                        clean_row = clean_row[:2] + clean_row[3:]
                    
                    # Then enforce 15 length
                    if len(clean_row) < 15:
                        clean_row += [None] * (15 - len(clean_row))
                    elif len(clean_row) > 15:
                        clean_row = clean_row[:15]
                        
                    all_data.append(clean_row)
                    
    df = pd.DataFrame(all_data, columns=expected_headers)
    
    print(f"Extracted {len(df)} raw rows.")
    
    # Clean the dataframe (forward fill merged cells like REGION and CIRCONSCRIPTION)
    df['REGION'] = df['REGION'].replace('', pd.NA).ffill()
    
    # The REGION text is vertical and read backwards by pdfplumber with newlines. 
    # Let's fix it by stripping newlines and reversing the string.
    def fix_region(x):
        if not isinstance(x, str):
            return x
        # Remove newlines and reverse the characters
        clean_str = x.replace('\n', '')
        # Some characters might be grouped together (e.g. 'IB'). Reversing the entire string works mostly.
        # But wait, if 'IB' is a single block, reversing the whole string might flip 'IB' to 'BI'.
        # Actually pdfplumber outputs 'N\nA\nJ\nD\nIB\nA\n'D\nE\nM\nO\nN\nO\nT\nU\nA'. 
        # If we split by '\n', reverse the list, and join, it preserves blocks!
        parts = x.split('\n')
        return ''.join(reversed(parts))
        
    df['REGION'] = df['REGION'].apply(fix_region)
    
    df['CIRCONSCRIPTION'] = df['CIRCONSCRIPTION'].replace('', pd.NA).ffill()
    df['NB BV'] = df['NB BV'].replace('', pd.NA).ffill()
    df['INSCRITS'] = df['INSCRITS'].replace('', pd.NA).ffill()
    df['VOTANTS'] = df['VOTANTS'].replace('', pd.NA).ffill()
    df['TAUX DE PART.'] = df['TAUX DE PART.'].replace('', pd.NA).ffill()
    df['BULL. NULS'] = df['BULL. NULS'].replace('', pd.NA).ffill()
    df['SUF. EXPRIMES'] = df['SUF. EXPRIMES'].replace('', pd.NA).ffill()
    
    # Remove rows where the candidate is empty (artifacts from pagination)
    df = df[df['CANDIDATS / LISTES DE CANDIDATS'].notna() & (df['CANDIDATS / LISTES DE CANDIDATS'] != '')]
    
    # Clean numeric columns (remove spaces, e.g. "10 675" -> "10675")
    numeric_cols = ['NB BV', 'INSCRITS', 'VOTANTS', 'BULL. NULS', 'SUF. EXPRIMES', 'BULL. BLANCS NOMBRE', 'SCORES']
    for col in numeric_cols:
        df[col] = df[col].astype(str).str.replace(' ', '').str.replace(r'[^0-9]', '', regex=True)
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    print(f"Final cleaned dataset: {len(df)} rows.")
    return df

def setup_database(df, db_path='elections.duckdb'):
    print(f"Setting up DuckDB at {db_path}...")
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = duckdb.connect(db_path)
    # Register the dataframe and create a table
    conn.execute("CREATE TABLE election_results AS SELECT * FROM df")
    
    # Verify
    count = conn.execute("SELECT COUNT(*) FROM election_results").fetchone()[0]
    print(f"Successfully inserted {count} rows into the DuckDB database.")
    conn.close()

def setup_vector_db(df, persist_dir='./chroma_db'):
    print("Setting up ChromaDB vector store for fuzzy matching...")
    load_dotenv()
    
    # Extract unique entities
    parties = df['GROUPEMENTS / PARTIS POLITIQUES'].dropna().unique().tolist()
    candidates = df['CANDIDATS / LISTES DE CANDIDATS'].dropna().unique().tolist()
    regions = df['REGION'].dropna().unique().tolist()
    
    all_entities = list(set(parties + candidates + regions))
    # Filter out any purely numeric or very short entities just in case
    all_entities = [e for e in all_entities if len(str(e)) > 2]
    
    # Initialize native ChromaDB (it will automatically use the default all-MiniLM-L6-v2 model)
    client = chromadb.PersistentClient(path=persist_dir)
    # Recreate collection to ensure it's fresh
    try:
        client.delete_collection("election_entities")
    except:
        pass
    collection = client.create_collection("election_entities")
    
    ids = [f"entity_{i}" for i in range(len(all_entities))]
    metadatas = [{"source": "pdf_extraction"} for _ in all_entities]
    
    print("Generating embeddings locally using ChromaDB default model...")
    collection.add(
        documents=all_entities,
        metadatas=metadatas,
        ids=ids
    )
    print("ChromaDB vector store setup complete.")

if __name__ == "__main__":
    pdf_file = "EDAN_2025_RESULTAT_NATIONAL_DETAILS.pdf"
    if not os.path.exists(pdf_file):
        print(f"Error: {pdf_file} not found in the current directory.")
    else:
        df = parse_pdf_to_df(pdf_file)
        setup_database(df)
        setup_vector_db(df)
