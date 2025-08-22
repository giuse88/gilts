# UK Gilts Bond Data Application

## Project Overview
This is a Python Flask web application for managing and visualizing UK Government bond (Gilts) data. The application downloads bond price data from Tradeweb, stores it in a SQLite database, and provides a web interface for viewing bonds and yield curves.

## Architecture

### Core Components

1. **Flask Web Application (`app.py:1-117`)**
   - Main web server with REST API endpoints
   - Routes for bond data and yield curve visualization
   - Dependencies: Flask, sqlite3, datetime

2. **Bond Data Management (`bond_data.py:1-222`)**
   - `BondDatabase` class for SQLite operations
   - CSV data import from Tradeweb downloads
   - Bond filtering and querying capabilities
   - Database schema with proper indexing

3. **Data Download (`download.py:1-810`)**
   - `TradewegGiltDownloader` class using Selenium WebDriver
   - Automated login and data extraction from Tradeweb
   - Alternative scraping methods if download fails
   - Comprehensive error handling and logging

4. **Yield Curve Generation (`yield_curve.py:1-304`)**
   - `YieldCurve` class for curve construction
   - Scipy interpolation (linear/cubic)
   - Standard maturity point generation
   - Curve persistence in database

5. **Web Frontend**
   - HTML template (`templates/index.html:1-94`)
   - CSS styling (`static/style.css:1-313`)
   - JavaScript functionality (`static/script.js:1-268`)
   - Chart.js integration for yield curve visualization

## Database Schema

### bonds table
- `isin`: Primary key (TEXT)
- `gilt_name`: Bond name (TEXT)
- `business_date`: Trade date (DATE)
- `type`: Bond type (Bills, Conventional, Index-linked, Strips)
- `coupon`: Coupon rate (REAL)
- `maturity`: Maturity date (DATE)
- `clean_price`: Clean price (REAL)
- `dirty_price`: Dirty price (REAL)
- `yield`: Yield to maturity (REAL)
- `mod_duration`: Modified duration (REAL)
- `accrued_interest`: Accrued interest (REAL)

### yield_curves table
- `id`: Auto-increment primary key
- `business_date`: Curve date (DATE)
- `maturity_days`: Days to maturity (INTEGER)
- `maturity_years`: Years to maturity (REAL)
- `yield_rate`: Interpolated yield (REAL)
- `interpolation_method`: Method used (TEXT)
- `created_at`: Timestamp (TIMESTAMP)

## API Endpoints

### `/api/bonds`
- **Method**: GET
- **Parameters**: `date` (required), `type` (required: Bills/Conventional/Index-linked/Strips)
- **Returns**: JSON array of bonds for specified date and type
- **Location**: `app.py:28-74`

### `/api/bond/<isin>`
- **Method**: GET
- **Returns**: JSON object with bond details by ISIN
- **Location**: `app.py:76-83`

### `/api/yield-curve`
- **Method**: GET
- **Parameters**: `date` (required)
- **Returns**: JSON object with yield curve data or generates if missing
- **Location**: `app.py:85-114`

## Configuration

### Environment Variables
- `TRADEWEB_USERNAME`: Login credentials for data download
- `TRADEWEB_PASSWORD`: Login credentials for data download

### Run Script (`run.sh:1-11`)
- Automated daily data processing
- Loads bond data for current date
- Optional yield curve generation

## Data Processing Workflow

1. **Download**: `download.py` fetches CSV data from Tradeweb
2. **Import**: `bond_data.py` processes and stores CSV in SQLite
3. **Analysis**: `yield_curve.py` generates interpolated curves
4. **Visualization**: Web interface displays data and charts

## Dependencies

### Python Packages
- Flask: Web framework
- sqlite3: Database operations
- pandas: Data manipulation
- numpy: Numerical operations
- scipy: Scientific interpolation
- selenium: Web automation
- requests: HTTP operations

### Frontend Libraries
- Chart.js: Yield curve visualization
- Modern CSS Grid/Flexbox layout
- Responsive design for mobile devices

## File Structure
```
gilts/
├── app.py                    # Main Flask application
├── bond_data.py             # Database operations
├── download.py              # Data download automation
├── yield_curve.py           # Yield curve generation
├── run.sh                   # Automation script
├── bonds.db                 # SQLite database
├── downloads/               # Downloaded CSV files
│   ├── logs/               # Download logs
│   └── *.csv               # Tradeweb data files
├── static/
│   ├── script.js           # Frontend JavaScript
│   └── style.css           # Styling
└── templates/
    └── index.html          # Main web template
```

## Usage Commands

### Start Web Server
```bash
python app.py
# Runs on http://localhost:5000
```

### Load Bond Data
```bash
python bond_data.py YYYY-MM-DD
```

### Generate Yield Curve
```bash
python yield_curve.py YYYY-MM-DD
```

### Download Fresh Data
```bash
python download.py
```

## Security Considerations
- Credentials stored as environment variables
- SQL injection protection via parameterized queries
- Input validation for date formats
- Selenium stealth mode to avoid detection

## Bond Types Supported
- **Bills**: Short-term government securities
- **Conventional**: Standard fixed-rate bonds
- **Index-linked**: Inflation-protected securities
- **Strips**: Zero-coupon securities

This application provides a comprehensive solution for UK Government bond analysis with automated data collection, robust storage, and intuitive visualization capabilities.