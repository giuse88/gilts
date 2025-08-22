import sqlite3
import csv
from datetime import datetime
from typing import List, Optional, Dict, Any
import os
import glob
import sys
import argparse

class BondDatabase:
    def __init__(self, db_path: str = "bonds.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create the bonds table with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bonds (
                isin TEXT NOT NULL,
                gilt_name TEXT NOT NULL,
                business_date DATE NOT NULL,
                type TEXT,
                coupon REAL,
                maturity DATE,
                clean_price REAL,
                dirty_price REAL,
                yield REAL,
                mod_duration REAL,
                accrued_interest REAL,
                PRIMARY KEY (isin, business_date)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_business_date ON bonds(business_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_maturity ON bonds(maturity)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON bonds(type)")
        
        conn.commit()
        conn.close()
    
    def parse_date(self, date_str: str) -> str:
        """Parse date from M/D/YYYY format to YYYY-MM-DD"""
        if not date_str or date_str.strip() == "":
            return None
        try:
            dt = datetime.strptime(date_str, "%m/%d/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None
    
    def parse_number(self, value: str) -> Optional[float]:
        """Parse numeric value, return None for N/A"""
        if not value or value.strip() in ["N/A", ""]:
            return None
        try:
            return float(value)
        except ValueError:
            return None
    
    def load_csv(self, csv_path: str):
        """Load bond data from CSV file"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        with open(csv_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                cursor.execute("""
                    INSERT OR REPLACE INTO bonds 
                    (isin, gilt_name, business_date, type, coupon, maturity, 
                     clean_price, dirty_price, yield, mod_duration, accrued_interest)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['ISIN'],
                    row['Gilt Name'],
                    self.parse_date(row['Close of Business Date']),
                    row['Type'],
                    self.parse_number(row['Coupon']),
                    self.parse_date(row['Maturity']),
                    self.parse_number(row['Clean Price']),
                    self.parse_number(row['Dirty Price']),
                    self.parse_number(row['Yield']),
                    self.parse_number(row['Mod Duration']),
                    self.parse_number(row['Accrued Interest'])
                ))
        
        conn.commit()
        conn.close()
        print(f"Data loaded from {csv_path}")
    
    def get_bonds_by_date(self, date: str) -> List[Dict[str, Any]]:
        """Get all bonds for a specific date (YYYY-MM-DD format)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM bonds 
            WHERE business_date = ?
            ORDER BY maturity
        """, (date,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_bond_by_isin(self, isin: str) -> Optional[Dict[str, Any]]:
        """Get bond data by ISIN"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM bonds WHERE isin = ?", (isin,))
        result = cursor.fetchone()
        
        conn.close()
        return dict(result) if result else None
    
    def get_yield_history_by_isin(self, isin: str) -> List[Dict[str, Any]]:
        """Get all yield records for a specific ISIN across all dates"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT business_date, yield, clean_price, dirty_price 
            FROM bonds 
            WHERE isin = ?
            ORDER BY business_date
        """, (isin,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total_bonds FROM bonds")
        total_bonds = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT business_date) as unique_dates FROM bonds")
        unique_dates = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(business_date), MAX(business_date) FROM bonds")
        date_range = cursor.fetchone()
        
        cursor.execute("SELECT type, COUNT(*) FROM bonds GROUP BY type")
        bond_types = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_bonds": total_bonds,
            "unique_dates": unique_dates,
            "date_range": {"min": date_range[0], "max": date_range[1]},
            "bond_types": bond_types
        }

    def find_bond_file_for_date(self, date_input: str, downloads_dir: str = "downloads") -> Optional[str]:
        """Find bond CSV file for a given date in the downloads directory"""
        try:
            if len(date_input) == 8 and date_input.isdigit():
                formatted_date = date_input
            else:
                dt = datetime.strptime(date_input, "%Y-%m-%d")
                formatted_date = dt.strftime("%Y%m%d")
        except ValueError:
            try:
                dt = datetime.strptime(date_input, "%m/%d/%Y")
                formatted_date = dt.strftime("%Y%m%d")
            except ValueError:
                print(f"Invalid date format: {date_input}. Use YYYY-MM-DD, MM/DD/YYYY, or YYYYMMDD")
                return None
        
        pattern = os.path.join(downloads_dir, f"Tradeweb_FTSE_ClosePrices_{formatted_date}_*.csv")
        matching_files = glob.glob(pattern)
        
        if matching_files:
            return matching_files[0]
        else:
            print(f"No bond file found for date {date_input} (looking for pattern: {pattern})")
            return None

    def load_bonds_for_date(self, date_input: str, downloads_dir: str = "downloads"):
        """Load bond data for a specific date from downloads directory"""
        csv_file = self.find_bond_file_for_date(date_input, downloads_dir)
        
        if csv_file:
            print(f"Found bond file: {csv_file}")
            self.load_csv(csv_file)
            return True
        return False

def main():
    parser = argparse.ArgumentParser(description="Load bond data for a specific date")
    parser.add_argument("date", help="Date to process (YYYY-MM-DD, MM/DD/YYYY, or YYYYMMDD format)")
    parser.add_argument("--downloads-dir", default="downloads", help="Downloads directory path (default: downloads)")
    parser.add_argument("--db-path", default="bonds.db", help="Database path (default: bonds.db)")
    
    args = parser.parse_args()
    
    db = BondDatabase(args.db_path)
    
    if db.load_bonds_for_date(args.date, args.downloads_dir):
        print("\nDatabase Summary:")
        stats = db.get_summary_stats()
        print(f"Total bonds: {stats['total_bonds']}")
        print(f"Date range: {stats['date_range']['min']} to {stats['date_range']['max']}")
        print(f"Bond types: {stats['bond_types']}")
    else:
        print("Failed to load bond data")
        sys.exit(1)

if __name__ == "__main__":
    main()
