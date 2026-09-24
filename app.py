from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json  # Add this at the top with other imports

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Initialize MySQL
mysql = MySQL(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_data, is_admin=False):
        if is_admin:
            # Admin user
            self.id = f"admin_{user_data[0]}"  # Prefix admin IDs to distinguish them
            self.admin_id = user_data[1]
            self.is_admin = True
        else:
            # Student user
            self.id = user_data[0]  # Keep original ID for database operations
            self.user_id = user_data[0]  # Add user_id for easier access
            self.name = user_data[1]
            self.email = user_data[2]
            self.is_admin = False

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    
    # Check if it's an admin ID
    if str(user_id).startswith('admin_'):
        real_id = user_id.split('admin_')[1]
        cur.execute('SELECT * FROM admin WHERE id = %s', (real_id,))
        user_data = cur.fetchone()
        cur.close()
        if user_data:
            return User(user_data, is_admin=True)
    
    # If not admin, treat as regular user
    else:
        cur.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user_data = cur.fetchone()
        cur.close()
        if user_data:
            return User(user_data, is_admin=False)
    
    return None

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect appropriately
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        # Only check users table for student login
        cur.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
        user_data = cur.fetchone()
        cur.close()
        
        if user_data:
            user = User(user_data, is_admin=False)
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('student_dashboard'))
        
        flash('Invalid email or password!', 'error')
    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    # If user is already logged in, redirect appropriately
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        admin_id = request.form['admin_id']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        # Only check admin table
        cur.execute('SELECT * FROM admin WHERE admin_id = %s AND password = %s', (admin_id, password))
        admin_data = cur.fetchone()
        cur.close()
        
        if admin_data:
            user = User(admin_data, is_admin=True)
            login_user(user)
            flash('Logged in successfully as administrator!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        flash('Invalid admin credentials!', 'error')
    return render_template('admin_login.html')

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.is_admin:
        flash('Access denied. This page is for students only.', 'error')
        return redirect(url_for('admin_dashboard'))
    return render_template('student_dashboard.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/books')
def books():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM books')
    books = cur.fetchall()
    cur.close()
    return render_template('books.html', books=books)

@app.route('/borrow/<int:book_id>', methods=['POST'])
@login_required
def borrow_book(book_id):
    if current_user.is_admin:
        flash('Admins cannot borrow books!', 'error')
        return redirect(url_for('books'))

    cur = mysql.connection.cursor()
    
    # Check if book is available
    cur.execute('SELECT available_quantity FROM books WHERE id = %s', (book_id,))
    book = cur.fetchone()
    
    if not book or book[0] <= 0:
        flash('Book is not available for borrowing!', 'error')
        return redirect(url_for('books'))
    
    # Check if user already has this book borrowed
    cur.execute('SELECT * FROM borrowings WHERE user_id = %s AND book_id = %s AND status = "borrowed"',
                (current_user.id, book_id))
    existing_borrow = cur.fetchone()
    
    if existing_borrow:
        flash('You have already borrowed this book!', 'error')
        return redirect(url_for('books'))
    
    try:
        # Update book quantity
        cur.execute('UPDATE books SET available_quantity = available_quantity - 1 WHERE id = %s', (book_id,))
        
        # Create borrowing record
        borrow_date = datetime.now()
        due_date = borrow_date + timedelta(days=14)  # 2 weeks borrowing period
        
        cur.execute('''
            INSERT INTO borrowings (user_id, book_id, borrow_date, due_date, status)
            VALUES (%s, %s, %s, %s, "borrowed")
        ''', (current_user.id, book_id, borrow_date, due_date))
        
        mysql.connection.commit()
        flash('Book borrowed successfully! Due date: ' + due_date.strftime('%Y-%m-%d'), 'success')
    except Exception as e:
        print(f"Error in borrow_book: {str(e)}")  # For debugging
        mysql.connection.rollback()
        flash('Error borrowing book!', 'error')
    finally:
        cur.close()
    
    return redirect(url_for('books'))

@app.route('/return/<int:borrowing_id>', methods=['POST'])
@login_required
def return_book(borrowing_id):
    if current_user.is_admin:
        flash('Admins cannot return books!', 'error')
        return redirect(url_for('admin_dashboard'))

    cur = mysql.connection.cursor()
    try:
        # First get the borrowing record and check if it can be returned
        cur.execute('''
            SELECT b.*, bk.title, f.status as fine_status
            FROM borrowings b
            JOIN books bk ON b.book_id = bk.id 
            LEFT JOIN fines f ON b.id = f.borrowing_id
            WHERE b.id = %s AND b.user_id = %s 
            AND b.status IN ('borrowed', 'overdue')
        ''', (borrowing_id, current_user.id))
        
        borrowing = cur.fetchone()
        
        if not borrowing:
            flash('Invalid return request or book already returned!', 'error')
            return redirect(url_for('my_borrowings'))
        
        # If book is overdue, check if fine is paid
        if borrowing[6] == 'overdue':  # status is at index 6
            if not borrowing[-1] or borrowing[-1] not in ['paid', 'waived']:
                flash('Please pay the fine before returning the book!', 'error')
                return redirect(url_for('my_borrowings'))
        
        # Update the borrowing status to pending_return
        cur.execute('''
            UPDATE borrowings 
            SET status = 'pending_return'
            WHERE id = %s AND user_id = %s
        ''', (borrowing_id, current_user.id))
        
        mysql.connection.commit()
        flash('Return request submitted! Waiting for admin approval.', 'success')
        
    except Exception as e:
        print(f"Error in return_book: {str(e)}")  # For debugging
        mysql.connection.rollback()
        flash('Error submitting return request. Please try again.', 'error')
    finally:
        cur.close()
    
    return redirect(url_for('my_borrowings'))

@app.route('/reviews/<int:book_id>', methods=['GET', 'POST'])
@login_required
def book_reviews(book_id):
    if current_user.is_admin:
        flash('Admins cannot post reviews!', 'error')
        return redirect(url_for('books'))

    cur = mysql.connection.cursor()
    
    if request.method == 'POST':
        rating = request.form.get('rating')
        review_text = request.form.get('review')
        
        if not rating or not (1 <= int(rating) <= 5):
            flash('Please provide a valid rating (1-5)!', 'error')
        else:
            try:
                cur.execute('''
                    INSERT INTO book_reviews (book_id, user_id, rating, review)
                    VALUES (%s, %s, %s, %s)
                ''', (book_id, current_user.id, rating, review_text))
                mysql.connection.commit()
                flash('Review submitted successfully!', 'success')
            except Exception as e:
                print(f"Error in book_reviews: {str(e)}")  # For debugging
                mysql.connection.rollback()
                flash('Error submitting review!', 'error')
    
    # Get book details
    cur.execute('SELECT * FROM books WHERE id = %s', (book_id,))
    book = cur.fetchone()
    
    # Get all reviews for the book
    cur.execute('''
        SELECT r.*, u.name 
        FROM book_reviews r 
        JOIN users u ON r.user_id = u.id 
        WHERE r.book_id = %s
        ORDER BY r.created_at DESC
    ''', (book_id,))
    reviews = cur.fetchall()
    
    cur.close()
    return render_template('reviews.html', book=book, reviews=reviews)

@app.route('/my-borrowings')
@login_required
def my_borrowings():
    if current_user.is_admin:
        flash('Admins cannot have borrowings!', 'error')
        return redirect(url_for('admin_dashboard'))

    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT 
            b.id,
            bk.title,
            bk.author,
            b.borrow_date,
            b.due_date,
            b.status,
            CASE 
                WHEN b.status = 'overdue' THEN f.status
                ELSE NULL
            END as fine_status
        FROM borrowings b 
        JOIN books bk ON b.book_id = bk.id 
        LEFT JOIN fines f ON b.id = f.borrowing_id
        WHERE b.user_id = %s 
        ORDER BY b.borrow_date DESC
    ''', (current_user.id,))
    borrowings = cur.fetchall()
    cur.close()
    return render_template('my_borrowings.html', borrowings=borrowings)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('student_dashboard'))
    
    cur = mysql.connection.cursor()
    # Get admin dashboard data
    cur.execute('SELECT COUNT(*) FROM books')
    total_books = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM users')
    total_users = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM borrowings WHERE status = "borrowed"')
    active_borrowings = cur.fetchone()[0]
    
    cur.execute('SELECT COUNT(*) FROM fines WHERE status = "pending"')
    pending_fines = cur.fetchone()[0]
    
    cur.close()
    
    return render_template('admin_dashboard.html',
                         total_books=total_books,
                         total_users=total_users,
                         active_borrowings=active_borrowings,
                         pending_fines=pending_fines)

@app.route('/admin/fines')
@login_required
def manage_fines():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('student_dashboard'))
    
    cur = mysql.connection.cursor()
    # Get all fines with user and book details
    cur.execute('''
        SELECT 
            f.id,
            f.amount,
            f.status,
            f.due_date,
            u.name as user_name,
            u.email as user_email,
            b.title as book_title,
            br.borrow_date,
            br.due_date as book_due_date,
            br.return_date,
            br.id as borrowing_id
        FROM fines f
        JOIN borrowings br ON f.borrowing_id = br.id
        JOIN users u ON br.user_id = u.id
        JOIN books b ON br.book_id = b.id
        ORDER BY f.due_date ASC
    ''')
    fines = cur.fetchall()
    cur.close()
    
    return render_template('admin/fines.html', fines=fines)

@app.route('/admin/fines/update/<int:fine_id>', methods=['POST'])
@login_required
def update_fine_status(fine_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('manage_fines'))
    
    status = request.form.get('status')
    payment_method = request.form.get('payment_method')
    
    if status not in ['paid', 'waived']:
        flash('Invalid status!', 'error')
        return redirect(url_for('manage_fines'))
    
    cur = mysql.connection.cursor()
    try:
        # First check if the fine exists and is pending
        cur.execute('SELECT borrowing_id, status FROM fines WHERE id = %s', (fine_id,))
        fine = cur.fetchone()
        
        if not fine:
            flash('Fine not found!', 'error')
            return redirect(url_for('manage_fines'))
            
        if fine[1] != 'pending':
            flash('This fine has already been processed!', 'error')
            return redirect(url_for('manage_fines'))
        
        # Update only the fine status
        update_query = '''
            UPDATE fines 
            SET status = %s,
                payment_method = %s,
                paid_date = CURRENT_TIMESTAMP
            WHERE id = %s
        '''
        
        if status == 'waived':
            payment_method = None
        
        cur.execute(update_query, (status, payment_method, fine_id))
        mysql.connection.commit()
        flash(f'Fine has been marked as {status}!', 'success')
        
    except Exception as e:
        print(f"Error in update_fine_status: {str(e)}")
        mysql.connection.rollback()
        flash('Error updating fine status!', 'error')
    finally:
        cur.close()
    
    return redirect(url_for('manage_fines'))

@app.route('/my-fines')
@login_required
def my_fines():
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT 
            f.id,
            f.amount,
            f.status,
            f.due_date,
            b.title as book_title,
            br.borrow_date,
            br.due_date as book_due_date,
            br.return_date,
            f.payment_method,
            f.paid_date
        FROM fines f
        JOIN borrowings br ON f.borrowing_id = br.id
        JOIN books b ON br.book_id = b.id
        WHERE br.user_id = %s
        ORDER BY f.due_date ASC
    ''', (current_user.id,))
    fines = cur.fetchall()
    
    # Calculate total pending fines
    total_pending = sum(fine[1] for fine in fines if fine[2] == 'pending')
    
    cur.close()
    return render_template('my_fines.html', fines=fines, total_pending=total_pending)

@app.route('/admin/returns')
@login_required
def manage_returns():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('student_dashboard'))
    
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT 
            b.id,
            b.borrow_date,
            b.due_date,
            b.status,
            bk.title,
            bk.author,
            u.name as user_name,
            u.email as user_email,
            bk.id as book_id
        FROM borrowings b
        JOIN books bk ON b.book_id = bk.id
        JOIN users u ON b.user_id = u.id
        WHERE b.status = 'pending_return'
        ORDER BY b.borrow_date DESC
    ''')
    pending_returns = cur.fetchall()
    cur.close()
    
    return render_template('admin/returns.html', pending_returns=pending_returns)

@app.route('/admin/returns/confirm/<int:borrowing_id>', methods=['POST'])
@login_required
def confirm_return(borrowing_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('manage_returns'))
    
    cur = mysql.connection.cursor()
    try:
        # Get borrowing and book details
        cur.execute('''
            SELECT 
                b.id as borrowing_id,
                b.status,
                bk.id as book_id,
                bk.title,
                bk.available_quantity
            FROM borrowings b
            JOIN books bk ON b.book_id = bk.id
            WHERE b.id = %s AND b.status = 'pending_return'
        ''', (borrowing_id,))
        
        borrowing = cur.fetchone()
        
        if not borrowing:
            flash('Invalid return request!', 'error')
            return redirect(url_for('manage_returns'))
        
        # Start transaction
        cur.execute("START TRANSACTION")
        
        # Update book quantity
        cur.execute('''
            UPDATE books 
            SET available_quantity = available_quantity + 1
            WHERE id = %s
        ''', (borrowing[2],))  # book_id is at index 2
        
        # Update borrowing status
        cur.execute('''
            UPDATE borrowings 
            SET status = 'returned',
                return_date = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (borrowing_id,))
        
        cur.execute("COMMIT")
        flash(f'Return confirmed for "{borrowing[3]}"!', 'success')  # title is at index 3
        
    except Exception as e:
        cur.execute("ROLLBACK")
        print(f"Error in confirm_return: {str(e)}")  # For debugging
        flash('Error confirming return!', 'error')
    finally:
        cur.close()
    
    return redirect(url_for('manage_returns'))

@app.route('/admin/books', methods=['GET', 'POST'])
@login_required
def manage_books():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        # Handle adding new book
        isbn = request.form.get('isbn')
        title = request.form.get('title')
        author = request.form.get('author')
        publisher = request.form.get('publisher')
        publication_year = request.form.get('publication_year')
        genre = request.form.get('genre')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        
        cur = mysql.connection.cursor()
        try:
            # Check if ISBN already exists
            cur.execute('SELECT id FROM books WHERE isbn = %s', (isbn,))
            if cur.fetchone():
                flash('A book with this ISBN already exists!', 'error')
            else:
                cur.execute('''
                    INSERT INTO books (
                        isbn, title, author, publisher, 
                        publication_year, genre, quantity, 
                        available_quantity, price
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    isbn, title, author, publisher,
                    publication_year, genre, quantity,
                    quantity, price  # initially available = total quantity
                ))
                mysql.connection.commit()
                flash('Book added successfully!', 'success')
        except Exception as e:
            print(f"Error adding book: {str(e)}")
            mysql.connection.rollback()
            flash('Error adding book!', 'error')
        finally:
            cur.close()
            return redirect('/admin/books')
    
    # Get all books for display
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT 
            id, isbn, title, author, publisher,
            publication_year, genre, quantity,
            available_quantity, price
        FROM books
        ORDER BY title
    ''')
    books = cur.fetchall()
    cur.close()
    
    return render_template('admin/manage_books.html', books=books)

@app.route('/admin/books/delete/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('student_dashboard'))
    
    cur = mysql.connection.cursor()
    try:
        # Start transaction
        cur.execute("START TRANSACTION")
        
        # Check if book has any active borrowings
        cur.execute('''
            SELECT COUNT(*) 
            FROM borrowings 
            WHERE book_id = %s AND status IN ('borrowed', 'overdue', 'pending_return')
        ''', (book_id,))
        active_borrowings = cur.fetchone()[0]
        
        if active_borrowings > 0:
            flash('Cannot delete book: there are active borrowings!', 'error')
            cur.execute("ROLLBACK")
            return redirect('/admin/books')
        
        # Get book title for confirmation message
        cur.execute('SELECT title FROM books WHERE id = %s', (book_id,))
        book_data = cur.fetchone()
        
        if not book_data:
            flash('Book not found!', 'error')
            cur.execute("ROLLBACK")
            return redirect('/admin/books')
            
        book_title = book_data[0]
        
        # Delete related records first
        # Delete fines related to this book's borrowings
        cur.execute('''
            DELETE f FROM fines f
            JOIN borrowings b ON f.borrowing_id = b.id
            WHERE b.book_id = %s
        ''', (book_id,))
        
        # Delete book reviews
        cur.execute('DELETE FROM book_reviews WHERE book_id = %s', (book_id,))
        
        # Delete borrowing records
        cur.execute('DELETE FROM borrowings WHERE book_id = %s', (book_id,))
        
        # Finally, delete the book
        cur.execute('DELETE FROM books WHERE id = %s', (book_id,))
        
        # Commit all changes
        cur.execute("COMMIT")
        flash(f'Book "{book_title}" has been deleted successfully.', 'success')
        
    except Exception as e:
        print(f"Error deleting book: {str(e)}")  # For debugging
        cur.execute("ROLLBACK")
        flash('Error deleting book! Please try again.', 'error')
    finally:
        cur.close()
    
    return redirect('/admin/books')

@app.route('/admin/books/update_quantity/<int:book_id>', methods=['POST'])
@login_required
def update_book_quantity(book_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('student_dashboard'))
    
    action = request.form.get('action')
    if action not in ['increase', 'decrease']:
        flash('Invalid action!', 'error')
        return redirect('/admin/books')
    
    cur = mysql.connection.cursor()
    try:
        # Get current quantities
        cur.execute('''
            SELECT quantity, available_quantity, title 
            FROM books 
            WHERE id = %s
        ''', (book_id,))
        book_data = cur.fetchone()
        
        if not book_data:
            flash('Book not found!', 'error')
            return redirect('/admin/books')
            
        current_quantity = book_data[0]
        current_available = book_data[1]
        book_title = book_data[2]
        
        if action == 'decrease':
            if current_quantity <= 0:
                flash('Cannot decrease quantity: already at minimum!', 'error')
                return redirect('/admin/books')
            
            # Calculate new quantities
            new_quantity = current_quantity - 1
            new_available = current_available - 1
            
            # If this is the last available book
            if new_quantity == 0:
                flash(f'This is the last copy of "{book_title}". Please use the Delete button to remove it completely.', 'warning')
                return redirect('/admin/books')
            
            # Update quantities if not the last book
            cur.execute('''
                UPDATE books 
                SET quantity = %s, available_quantity = %s
                WHERE id = %s
            ''', (new_quantity, new_available, book_id))
            flash(f'Successfully decreased quantity for "{book_title}"', 'success')
            
        else:  # action == 'increase'
            # Update quantities for increase
            new_quantity = current_quantity + 1
            new_available = current_available + 1
            
            cur.execute('''
                UPDATE books 
                SET quantity = %s, available_quantity = %s
                WHERE id = %s
            ''', (new_quantity, new_available, book_id))
            flash(f'Successfully increased quantity for "{book_title}"', 'success')
        
        mysql.connection.commit()
        
    except Exception as e:
        print(f"Error updating quantity: {str(e)}")
        mysql.connection.rollback()
        flash('Error updating book quantity!', 'error')
    finally:
        cur.close()
    
    return redirect('/admin/books')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    
    signup_type = request.args.get('type', 'user')
    cur = mysql.connection.cursor()
    
    try:
        if signup_type == 'user':
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']  # In production, hash this password
            
            # Check if email already exists
            cur.execute('SELECT id FROM users WHERE email = %s', (email,))
            if cur.fetchone():
                flash('Email already registered!', 'danger')
                return redirect(url_for('signup'))
            
            # Insert new user
            cur.execute('''
                INSERT INTO users (name, email, password)
                VALUES (%s, %s, %s)
            ''', (name, email, password))
            
            mysql.connection.commit()
            flash('User registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        elif signup_type == 'admin':
            admin_id = request.form['admin_id']
            password = request.form['password']
            
            # Check if admin_id already exists
            cur.execute('SELECT id FROM admin WHERE admin_id = %s', (admin_id,))
            if cur.fetchone():
                flash('Admin ID already exists!', 'danger')
                return redirect(url_for('signup'))
            
            # Insert new admin
            cur.execute('''
                INSERT INTO admin (admin_id, password)
                VALUES (%s, %s)
            ''', (admin_id, password))
            
            mysql.connection.commit()
            flash('Admin registration successful! Please login through admin login.', 'success')
            return redirect(url_for('admin_login'))
        
    except Exception as e:
        mysql.connection.rollback()
        flash('Error during registration!', 'danger')
        return redirect(url_for('signup'))
    finally:
        cur.close()

if __name__ == '__main__':
    app.run(debug=True) 