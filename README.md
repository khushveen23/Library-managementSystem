# Library Management System

A web-based library management system built with Flask and MySQL.

## Features

- Book management (add, view, search)
- User authentication
- Book borrowing system
- Review and rating system
- Fine management for late returns
- Admin dashboard

## Prerequisites

- Python 3.8 or higher
- MySQL 5.7 or higher
- pip (Python package manager)

## Setup Instructions

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the root directory with the following content:
```
MYSQL_HOST=localhost
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DB=library_db
SECRET_KEY=your-secret-key-here
```

3. Initialize the database:
```bash
python init_db.py
```

4. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
library/
├── app.py              # Main application file
├── init_db.py          # Database initialization script
├── requirements.txt    # Python dependencies
├── static/            # Static files (CSS, JS)
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── templates/         # HTML templates
    ├── base.html
    ├── index.html
    ├── login.html
    └── books.html
```

## Using the System

1. After running the application, open your web browser and go to `http://localhost:5000`
2. You can browse books without logging in
3. To borrow books or leave reviews, you'll need to log in
4. Use the search function to find specific books
5. Admin users can manage books, users, and handle fines

## Database Structure

The system uses the following tables:
- books: Stores book information
- users: Manages user accounts
- borrowings: Tracks book loans
- book_reviews: Stores user reviews and ratings
- fines: Manages late return penalties
- admin: Stores admin user information

## License

This project is licensed under the MIT License.