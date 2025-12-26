import pandas as pd
import glob
import os

data_dir = os.path.join(os.getcwd(), 'joe_data')
files = glob.glob(os.path.join(data_dir, "*.xlsx"))

if not files:
    print(f"No files found in {data_dir}")
else:
    first_file = files[0]
    print(f"Reading {first_file}...")
    try:
        df = pd.read_excel(first_file)
        
        with open('xls_schema.txt', 'w', encoding='utf-8') as f:
            f.write("Columns:\n")
            for col in df.columns:
                f.write(f"- {col}\n")
            
            f.write("\nFirst row sample:\n")
            for k, v in df.iloc[0].to_dict().items():
                f.write(f"{k}: {v}\n")
            
            f.write(f"\nTotal columns: {len(df.columns)}\n")
            
        print("Schema saved to xls_schema.txt")
        
    except Exception as e:
        print(f"Error reading file: {e}")
