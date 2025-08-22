from flask import Flask, render_template, request, jsonify
from bond_data import BondDatabase
from yield_curve import YieldCurve
import sqlite3
from datetime import datetime

app = Flask(__name__)
db = BondDatabase()
yc = YieldCurve()

@app.route('/')
def index():
    """Main page with date selection and bond table"""
    # Get available dates from database
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT business_date FROM bonds ORDER BY business_date DESC")
    available_dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Default to latest date if available
    selected_date = available_dates[0] if available_dates else None
    
    return render_template('index.html', 
                         available_dates=available_dates, 
                         selected_date=selected_date)

@app.route('/api/bonds')
def get_bonds():
    """API endpoint to get bonds for a specific date and type"""
    date = request.args.get('date')
    bond_type = request.args.get('type', 'all')
    if not date:
        return jsonify({'error': 'Date parameter required'}), 400
    
    # Get all bonds for the date
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Base query filters for UK bonds only
    base_query = """
        SELECT * FROM bonds 
        WHERE business_date = ? 
        AND isin LIKE 'GB%'
    """
    
    # Type filter is now required
    if bond_type in ['Bills', 'Conventional', 'Index-linked', 'Strips']:
        base_query += " AND type = ?"
        cursor.execute(base_query + " ORDER BY maturity", (date, bond_type))
    else:
        return jsonify({'error': 'Invalid bond type'}), 400
    
    bonds = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Format data for display
    formatted_bonds = []
    for bond in bonds:
        formatted_bonds.append({
            'isin': bond['isin'],
            'gilt_name': bond['gilt_name'],
            'type': bond['type'],
            'coupon': f"{bond['coupon']:.4f}%" if bond['coupon'] else 'N/A',
            'maturity': bond['maturity'],
            'clean_price': f"£{bond['clean_price']:.1f}" if bond['clean_price'] else 'N/A',
            'dirty_price': f"£{bond['dirty_price']:.1f}" if bond['dirty_price'] else 'N/A',
            'yield': f"{bond['yield']:.1f}%" if bond['yield'] else 'N/A',
            'mod_duration': f"{bond['mod_duration']:.3f}" if bond['mod_duration'] else 'N/A',
            'accrued_interest': f"£{bond['accrued_interest']:.6f}" if bond['accrued_interest'] else 'N/A'
        })
    
    return jsonify(formatted_bonds)

@app.route('/api/bond/<isin>')
def get_bond_details(isin):
    """API endpoint to get details for a specific bond"""
    bond = db.get_bond_by_isin(isin)
    if not bond:
        return jsonify({'error': 'Bond not found'}), 404
    
    return jsonify(bond)

@app.route('/api/yield-curve')
def get_yield_curve():
    """API endpoint to get yield curve for a specific date"""
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'Date parameter required'}), 400
    
    # Try to get existing yield curve
    curve = yc.get_yield_curve(date)
    
    if not curve:
        # Generate yield curve if it doesn't exist
        try:
            curve_data = yc.generate_yield_curve(date)
            if yc.save_yield_curve(curve_data):
                curve = yc.get_yield_curve(date)
            else:
                return jsonify({'error': 'Failed to generate yield curve'}), 500
        except Exception as e:
            return jsonify({'error': f'Unable to generate yield curve: {str(e)}'}), 500
    
    if curve:
        return jsonify({
            'business_date': curve['business_date'],
            'maturities': curve['curve_points']['maturities_years'],
            'yields': curve['curve_points']['yields'],
            'created_at': curve.get('created_at')
        })
    
    return jsonify({'error': 'No yield curve data available'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)