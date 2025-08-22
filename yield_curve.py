import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from scipy.interpolate import interp1d
import pandas as pd
import argparse
import sys

class YieldCurve:
    def __init__(self, db_path: str = "bonds.db"):
        self.db_path = db_path
        self.init_yield_curve_table()
    
    def init_yield_curve_table(self):
        """Create the yield_curves table to store generated curves"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS yield_curves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_date DATE NOT NULL,
                maturity_days INTEGER NOT NULL,
                maturity_years REAL NOT NULL,
                yield_rate REAL NOT NULL,
                interpolation_method TEXT DEFAULT 'linear',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(business_date, maturity_days)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_yield_curve_date ON yield_curves(business_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_yield_curve_maturity ON yield_curves(maturity_days)")
        
        conn.commit()
        conn.close()
    
    def calculate_days_to_maturity(self, business_date: str, maturity_date: str) -> int:
        """Calculate days between business date and maturity date"""
        try:
            bdate = datetime.strptime(business_date, "%Y-%m-%d")
            mdate = datetime.strptime(maturity_date, "%Y-%m-%d")
            return (mdate - bdate).days
        except ValueError:
            return None
    
    def get_bond_data_for_curve(self, business_date: str) -> List[Dict[str, Any]]:
        """Get bond data suitable for yield curve construction"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT isin, gilt_name, maturity, yield, clean_price, type
            FROM bonds 
            WHERE business_date = ? 
            AND yield IS NOT NULL 
            AND maturity IS NOT NULL
            AND isin LIKE 'GB%'
            AND type IN ('Bills', 'Conventional')
            ORDER BY maturity
        """, (business_date,))
        
        results = []
        for row in cursor.fetchall():
            bond = dict(row)
            days_to_maturity = self.calculate_days_to_maturity(business_date, bond['maturity'])
            if days_to_maturity and days_to_maturity > 0:
                bond['days_to_maturity'] = days_to_maturity
                bond['years_to_maturity'] = days_to_maturity / 365.25
                results.append(bond)
        
        conn.close()
        return results
    
    def generate_yield_curve(self, business_date: str, interpolation_method: str = 'linear') -> Dict[str, Any]:
        """Generate yield curve for a specific business date"""
        bonds = self.get_bond_data_for_curve(business_date)
        
        if len(bonds) < 2:
            raise ValueError(f"Insufficient bond data for {business_date}. Need at least 2 bonds with valid yields.")
        
        # Extract maturities and yields
        maturities = np.array([bond['years_to_maturity'] for bond in bonds])
        yields = np.array([bond['yield'] for bond in bonds])
        
        # Remove duplicates and sort
        unique_data = {}
        for mat, yld in zip(maturities, yields):
            if mat not in unique_data:
                unique_data[mat] = yld
            else:
                # Average yields for same maturity
                unique_data[mat] = (unique_data[mat] + yld) / 2
        
        sorted_maturities = np.array(sorted(unique_data.keys()))
        sorted_yields = np.array([unique_data[mat] for mat in sorted_maturities])
        
        # Create interpolation function
        if interpolation_method == 'linear':
            interp_func = interp1d(sorted_maturities, sorted_yields, 
                                 kind='linear', bounds_error=False, fill_value='extrapolate')
        elif interpolation_method == 'cubic':
            if len(sorted_maturities) >= 4:
                interp_func = interp1d(sorted_maturities, sorted_yields, 
                                     kind='cubic', bounds_error=False, fill_value='extrapolate')
            else:
                interp_func = interp1d(sorted_maturities, sorted_yields, 
                                     kind='linear', bounds_error=False, fill_value='extrapolate')
        else:
            raise ValueError(f"Unsupported interpolation method: {interpolation_method}")
        
        # Generate standard maturity points (in years)
        standard_maturities = np.array([
            0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 25, 30
        ])
        
        # Filter to only include maturities within our data range
        min_mat, max_mat = sorted_maturities.min(), sorted_maturities.max()
        valid_maturities = standard_maturities[
            (standard_maturities >= min_mat) & (standard_maturities <= max_mat)
        ]
        
        # Interpolate yields for standard maturities
        interpolated_yields = interp_func(valid_maturities)
        
        curve_data = {
            'business_date': business_date,
            'interpolation_method': interpolation_method,
            'raw_data': {
                'maturities': sorted_maturities.tolist(),
                'yields': sorted_yields.tolist(),
                'bond_count': len(bonds)
            },
            'curve_points': {
                'maturities_years': valid_maturities.tolist(),
                'maturities_days': (valid_maturities * 365.25).astype(int).tolist(),
                'yields': interpolated_yields.tolist()
            }
        }
        
        return curve_data
    
    def save_yield_curve(self, curve_data: Dict[str, Any]) -> bool:
        """Save yield curve to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert or replace curve points (preserves historical curves)
            for mat_years, mat_days, yield_rate in zip(
                curve_data['curve_points']['maturities_years'],
                curve_data['curve_points']['maturities_days'],
                curve_data['curve_points']['yields']
            ):
                cursor.execute("""
                    INSERT OR REPLACE INTO yield_curves 
                    (business_date, maturity_days, maturity_years, yield_rate, interpolation_method)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    curve_data['business_date'],
                    mat_days,
                    mat_years,
                    yield_rate,
                    curve_data['interpolation_method']
                ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error saving yield curve: {e}")
            return False
    
    def get_yield_curve(self, business_date: str) -> Optional[Dict[str, Any]]:
        """Retrieve saved yield curve from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT maturity_days, maturity_years, yield_rate, interpolation_method, created_at
            FROM yield_curves 
            WHERE business_date = ?
            ORDER BY maturity_days
        """, (business_date,))
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return None
        
        return {
            'business_date': business_date,
            'interpolation_method': results[0]['interpolation_method'],
            'created_at': results[0]['created_at'],
            'curve_points': {
                'maturities_days': [row['maturity_days'] for row in results],
                'maturities_years': [row['maturity_years'] for row in results],
                'yields': [row['yield_rate'] for row in results]
            }
        }
    
    def get_available_curve_dates(self) -> List[str]:
        """Get list of dates with available yield curves"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT business_date 
            FROM yield_curves 
            ORDER BY business_date DESC
        """)
        
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        return dates

    def check_bond_data_exists(self, business_date: str) -> bool:
        """Check if bond data exists for the specified date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM bonds 
            WHERE business_date = ? 
            AND yield IS NOT NULL 
            AND maturity IS NOT NULL
            AND isin LIKE 'GB%'
            AND type IN ('Bills', 'Conventional')
        """, (business_date,))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def generate_and_save_yield_curve_for_date(self, business_date: str, interpolation_method: str = 'linear') -> bool:
        """Generate and save yield curve for a specific date with proper error handling"""
        # Check if bond data exists
        if not self.check_bond_data_exists(business_date):
            print(f"ERROR: No bond data found in database for date {business_date}")
            print("Please ensure bond data is loaded for this date before generating yield curve.")
            return False
        
        print(f"Generating yield curve for {business_date}")
        
        try:
            # Generate yield curve
            curve_data = self.generate_yield_curve(business_date, interpolation_method)
            
            # Save to database
            if self.save_yield_curve(curve_data):
                print(f"Yield curve saved successfully for {business_date}")
                print(f"Raw data points: {curve_data['raw_data']['bond_count']} bonds")
                print(f"Interpolated points: {len(curve_data['curve_points']['maturities_years'])}")
                print(f"Maturity range: {min(curve_data['curve_points']['maturities_years']):.2f} - {max(curve_data['curve_points']['maturities_years']):.2f} years")
                
                # Display curve points
                print("\nYield Curve Points:")
                for mat_years, yield_rate in zip(curve_data['curve_points']['maturities_years'], 
                                               curve_data['curve_points']['yields']):
                    print(f"  {mat_years:5.2f}Y: {yield_rate:6.3f}%")
                return True
            else:
                print("Failed to save yield curve")
                return False
                
        except ValueError as e:
            print(f"ERROR: {e}")
            return False
        except Exception as e:
            print(f"ERROR: Unexpected error generating yield curve: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Generate yield curve for a specific date")
    parser.add_argument("date", help="Date to generate yield curve for (YYYY-MM-DD format)")
    parser.add_argument("--db-path", default="bonds.db", help="Database path (default: bonds.db)")
    parser.add_argument("--interpolation", default="linear", choices=["linear", "cubic"], 
                       help="Interpolation method (default: linear)")
    
    args = parser.parse_args()
    
    # Validate date format
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Invalid date format '{args.date}'. Please use YYYY-MM-DD format.")
        sys.exit(1)
    
    yc = YieldCurve(args.db_path)
    
    if not yc.generate_and_save_yield_curve_for_date(args.date, args.interpolation):
        sys.exit(1)

if __name__ == "__main__":
    main()