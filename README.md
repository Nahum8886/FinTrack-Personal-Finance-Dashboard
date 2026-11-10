# FinTrack — Personal Finance Dashboard

A full-stack personal finance web application built using **Python, Flask, SQLite, JavaScript and Chart.js**.

I developed FinTrack to strengthen my full-stack development skills by building an application that allows users to manage transactions, monitor spending, set financial goals and understand their finances through interactive visualisations.

The project gave me practical experience working with frontend and backend technologies, databases, authentication, REST APIs and cloud deployment.

### Live Demo

**[Try FinTrack](https://fintrack-personal-finance-dashboard-bgmd.onrender.com)**

**[View Source Code](https://github.com/Nahum8886/FinTrack-Personal-Finance-Dashboard)**

*This is a portfolio demonstration. Please use test information only. Data entered on the live website may be lost when the hosting service restarts or redeploys.*

## Key Features

### User Authentication
- Account registration and login
- Password hashing using Werkzeug
- Signed sessions and CSRF protection
- User-specific financial records

### Transaction Management
- Add and delete income and expense transactions
- Organise transactions by date and category
- Search and filter transaction history
- Export transactions to CSV

### Financial Dashboard
- View income, expenses and overall balance
- Interactive spending charts using Chart.js
- Income and expense comparisons
- Responsive dashboard interface

### Budgeting and Savings
- Set monthly spending budgets
- Track progress towards savings goals
- View financial insights generated using Python

## Technologies Used

| Area | Technologies |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask |
| Database | SQLite |
| Data Visualisation | Chart.js |
| Authentication | Werkzeug, Flask sessions |
| Testing | Python unittest |
| Version Control | Git, GitHub |
| Deployment | Render, Gunicorn |

## Screenshots

Screenshots of the application will be added here to demonstrate the dashboard, transaction management and financial visualisations.

## Running the Project Locally

### Requirements

- Python 3
- Git
- A modern web browser

### Installation

1. Clone the repository:

```bash
git clone https://github.com/Nahum8886/FinTrack-Personal-Finance-Dashboard.git
cd FinTrack-Personal-Finance-Dashboard
```

2. Create a virtual environment:

```powershell
py -m venv .venv
```

3. Install the dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

4. Configure a Flask secret key:

```powershell
$env:SECRET_KEY = (py -c "import secrets; print(secrets.token_hex(32))")
```

5. Start the application:

```powershell
.\.venv\Scripts\python.exe app.py
```

6. Open `http://127.0.0.1:5000` in your browser.

## Running Tests

The project includes automated Python tests.

Run them using:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Security and Limitations

FinTrack includes password hashing, CSRF protection, parameterised SQL queries, user-scoped database access and CSV formula-injection protection.

However, it is a learning and portfolio project rather than a production banking application. It does not currently include features such as multi-factor authentication, password recovery, account rate limiting or automated backups.

The live demonstration uses SQLite on Render's free hosting environment, which does not guarantee persistent storage. Users should not enter real financial information, banking credentials or sensitive personal data.

## What I Learned

Developing FinTrack helped me improve my understanding of:

- Building a full-stack application with Python and JavaScript
- Connecting frontend interfaces to Flask REST APIs
- Designing and managing relational database records
- Implementing account authentication and user-specific data access
- Creating interactive charts and financial visualisations
- Testing, debugging and deploying a web application
- Using Git and GitHub to manage and publish a software project

## Future Improvements

- Persistent PostgreSQL database
- Additional automated tests
- Improved mobile accessibility
- More advanced financial reporting
- Stronger authentication and account security

## About the Developer

Developed by **Nahum Wondimagegne**, a BSc Computer Science student at Brunel University London, as a personal software development project.

[LinkedIn](https://www.linkedin.com/in/nahum-wondimagegne) | [GitHub](https://github.com/Nahum8886)