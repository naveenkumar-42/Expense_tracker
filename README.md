# ExpTracker - Personal Finance Management System

## Overview
ExpTracker is a modern, user-friendly desktop application built with Python that helps users manage their personal finances effectively. The application provides an intuitive interface for tracking expenses, monitoring income, and analyzing spending patterns.

## Features

### 1. User Authentication
- Secure login and registration system
- Password validation and security checks
- User session management
- Last login tracking

### 2. Transaction Management
- Add new expenses and income
- Categorize transactions (Food & Dining, Transportation, Housing, Entertainment, Other)
- Add comments/notes to transactions
- View transaction history with sorting capabilities
- Color-coded entries (green for income, red for expenses)

### 3. Financial Analysis
- Real-time balance calculation
- Expense distribution visualization
- Category-wise expense breakdown
- Monthly summary statistics
- Interactive charts and graphs

### 4. Data Management
- Excel/CSV import functionality
- Secure database storage
- Transaction history export
- Data persistence across sessions

### 5. User Interface
- Modern gradient design
- Responsive layout
- User-friendly forms
- Interactive visualizations
- Clean and intuitive navigation

## Technical Requirements

### Prerequisites
```
Python 3.x
MySQL Server
```

### Required Python Packages
```
mysql-connector-python
customtkinter
pillow
matplotlib
pandas
python-dotenv
google-generativeai (optional, for AI insights)
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ExpTracker.git
cd ExpTracker
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Database Setup:
- Install MySQL Server
- Create a database named 'expense_tracker'
- Update database credentials in the code if needed (default):
  ```python
  host="localhost"
  user="root"
  password="Ram@3360"
  port=3306
  ```

4. Optional: AI Features Setup
- Get an API key from Google's Makersuite
- Create a .env file in the project root
- Add your API key:
  ```
  GOOGLE_GEMINI_API_KEY=your_api_key_here
  ```

## Usage

1. Start the application:
```bash
python Expense-Tracker.py
```

2. First-time users:
- Click "NEW USER? CREATE ACCOUNT"
- Fill in the registration form
- Password requirements:
  - Minimum 6 characters
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one number

3. Returning users:
- Enter username and password
- Click "LOGIN"

4. Main Features:
- Add Transaction: Enter amount, type, date, and optional comments
- View History: Check all past transactions
- Charts: Monitor expense distribution and patterns
- Import Data: Upload transactions from Excel/CSV files

## Project Structure

```
ExpTracker/
├── Expense-Tracker.py     # Main application file
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (optional)
├── logs/                 # Application logs
│   └── expense_tracker.log
└── README.md            # Documentation
```

## Database Schema

### userinfo Table
```sql
CREATE TABLE userinfo (
    userid VARCHAR(255) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    user_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL DEFAULT NULL
);
```

### expense Table
```sql
CREATE TABLE expense (
    id INT AUTO_INCREMENT PRIMARY KEY,
    userid VARCHAR(255) NOT NULL,
    date VARCHAR(20) NOT NULL,
    expense_type VARCHAR(255) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (userid) REFERENCES userinfo(userid) ON DELETE CASCADE,
    CHECK (amount > 0)
);
```

## Security Features
- Password validation
- SQL injection prevention
- Error logging
- Session management
- Database connection security

## Error Handling
- Comprehensive error logging
- User-friendly error messages
- Database connection error handling
- Input validation
- Exception handling for critical operations

## Future Enhancements
1. Multi-currency support
2. Budget planning features
3. Bill reminders
4. Financial goals tracking
5. Mobile application integration
6. Data backup and restore
7. Advanced reporting features
8. Categories customization

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Support
For support, please create an issue in the repository or contact the development team.

## Acknowledgments
- CustomTkinter for the modern UI components
- MySQL for reliable data storage
- Matplotlib for visualization capabilities
- Google's Generative AI for intelligent insights
