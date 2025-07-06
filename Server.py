from flask import Flask, redirect, url_for, render_template, request, flash, session, jsonify
from db import init_db
import os
from psycopg2 import extensions
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
import requests
import urllib.request
import json

extensions.register_type(extensions.UNICODE)
extensions.register_type(extensions.UNICODEARRAY)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Session için güvenli bir secret key

# Veritabanı bağlantı URL'sini düzelt
os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_zbV7u9EDjQnI@ep-mute-meadow-a4z9e04k.us-east-1.aws.neon.tech/neondb?sslmode=require"
init_db(os.environ.get("DATABASE_URL"))

# Dosya yükleme için gerekli ayarlar
UPLOAD_FOLDER = 'static/uploads/covers'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Dosya uzantısı kontrolü
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Login gerekli decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bu sayfayı görüntülemek için giriş yapmalısınız.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin gerekli decorator'ı
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash('Bu sayfaya erişim yetkiniz yok.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    recent_books = []
    if session.get('user_id'):
        with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT b.id, b.title, b.cover_image, a.name as author_name
                    FROM books b
                    LEFT JOIN authors a ON b.author_id = a.id
                    ORDER BY b.created_at DESC
                    LIMIT 4
                """)
                books_data = cur.fetchall()
                
                # Sonuçları dictionary formatına dönüştür
                recent_books = [{
                    'id': book[0],
                    'title': book[1],
                    'cover_image': book[2],
                    'author_name': book[3]
                } for book in books_data]
    
    return render_template('index.html', recent_books=recent_books)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, password, role FROM users WHERE username = %s", (username,))
                user = cur.fetchone()
                
                if user and check_password_hash(user[2], password):
                    session['user_id'] = user[0]
                    session['username'] = user[1]
                    session['role'] = user[3]
                    flash('Başarıyla giriş yaptınız!', 'success')
                    return redirect(url_for('index'))
                
                flash('Geçersiz kullanıcı adı veya şifre!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Başarıyla çıkış yaptınız!', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                try:
                    hashed_password = generate_password_hash(password)
                    cur.execute(
                        "INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, 'student')",
                        (username, hashed_password, email)
                    )
                    conn.commit()
                    flash('Kayıt başarılı! Şimdi giriş yapabilirsiniz.', 'success')
                    return redirect(url_for('login'))
                except psycopg2.IntegrityError:
                    flash('Bu kullanıcı adı veya email zaten kullanımda!', 'error')
    
    return render_template('register.html')

# Kitap yönetimi route'ları
@app.route('/books')
@login_required
def books():
    search_query = request.args.get('search', '')
    category_id = request.args.get('category', '')
    
    with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            # Kategorileri al
            cur.execute("SELECT id, name FROM categories ORDER BY name")
            categories_data = cur.fetchall()
            categories = [{'id': cat[0], 'name': cat[1]} for cat in categories_data]
            
            # Kitapları al
            query = """
                SELECT b.id, b.title, b.isbn, b.quantity, b.available_quantity,
                       b.cover_image, c.name as category, a.name as author
                FROM books b
                LEFT JOIN categories c ON b.category_id = c.id
                LEFT JOIN authors a ON b.author_id = a.id
                WHERE 1=1
            """
            params = []
            
            if search_query:
                query += " AND (b.title ILIKE %s OR a.name ILIKE %s)"
                params.extend([f'%{search_query}%', f'%{search_query}%'])
            
            if category_id:
                query += " AND b.category_id = %s"
                params.append(category_id)
            
            query += " ORDER BY b.title"
            cur.execute(query, params)
            books_data = cur.fetchall()
            
            # Sonuçları dictionary formatına dönüştür
            books = [{
                'id': book[0],
                'title': book[1],
                'isbn': book[2],
                'quantity': book[3],
                'available_quantity': book[4],
                'cover_image': book[5],
                'category': book[6],
                'author': book[7]
            } for book in books_data]
    
    return render_template('books.html', books=books, categories=categories,
                         search_query=search_query, selected_category=category_id)

@app.route('/books/search', methods=['GET'])
@login_required
@admin_required
def search_books():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    api_key = 'AIzaSyDLAfqlMCELB2UZMDoe1TLYGWXK3PGLcA4'
    url = f'https://www.googleapis.com/books/v1/volumes?q={query}&key={api_key}'
    
    try:
        response = requests.get(url)
        data = response.json()
        
        books = []
        if 'items' in data:
            for item in data['items']:
                volume_info = item['volumeInfo']
                
                # ISBN numarasını bul
                isbn = ''
                if 'industryIdentifiers' in volume_info:
                    for identifier in volume_info['industryIdentifiers']:
                        if identifier['type'] == 'ISBN_13':
                            isbn = identifier['identifier']
                            break
                        elif identifier['type'] == 'ISBN_10':
                            isbn = identifier['identifier']
                
                book = {
                    'title': volume_info.get('title', ''),
                    'authors': volume_info.get('authors', ['Bilinmeyen Yazar']),
                    'isbn': isbn,
                    'description': volume_info.get('description', ''),
                    'cover_image': volume_info.get('imageLinks', {}).get('thumbnail', ''),
                    'categories': volume_info.get('categories', ['Genel'])
                }
                books.append(book)
        
        return json.dumps(books)
    except Exception as e:
        return json.dumps({'error': str(e)}), 500

@app.route('/books/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        isbn = request.form['isbn']
        category_id = request.form['category_id']
        author_name = request.form['author']
        quantity = request.form['quantity']
        description = request.form['description']
        cover_url = request.form.get('cover_url', '')
        
        with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                try:
                    # Önce yazarı ekle veya var olan yazarı bul
                    cur.execute("SELECT id FROM authors WHERE name = %s", (author_name,))
                    author = cur.fetchone()
                    if not author:
                        cur.execute("INSERT INTO authors (name) VALUES (%s) RETURNING id", (author_name,))
                        author_id = cur.fetchone()[0]
                    else:
                        author_id = author[0]
                    
                    # Kapak resmi indirme ve kaydetme
                    cover_image = None
                    if cover_url:
                        try:
                            # Benzersiz dosya adı oluştur
                            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(title)}.jpg"
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            
                            # Resmi indir ve kaydet
                            urllib.request.urlretrieve(cover_url, filepath)
                            cover_image = filename
                        except Exception as e:
                            flash(f'Kapak resmi indirilirken hata oluştu: {str(e)}', 'error')
                    
                    # Kitabı ekle
                    cur.execute("""
                        INSERT INTO books (title, isbn, category_id, author_id, quantity, 
                                        available_quantity, description, cover_image)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (title, isbn, category_id, author_id, quantity, quantity, 
                          description, cover_image))
                    
                    conn.commit()
                    flash('Kitap başarıyla eklendi!', 'success')
                    return redirect(url_for('books'))
                except psycopg2.IntegrityError:
                    flash('Bu ISBN numarası zaten kullanımda!', 'error')
                except Exception as e:
                    flash(f'Bir hata oluştu: {str(e)}', 'error')
    
    with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM categories ORDER BY name")
            categories = cur.fetchall()
    
    return render_template('add_book.html', categories=categories)

@app.route('/books/<int:book_id>')
@login_required
def book_detail(book_id):
    with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            # Kitap detaylarını al
            cur.execute("""
                SELECT b.*, a.name as author_name, c.name as category_name,
                       (SELECT COUNT(*) FROM borrowings WHERE book_id = b.id) as total_borrows
                FROM books b
                LEFT JOIN authors a ON b.author_id = a.id
                LEFT JOIN categories c ON b.category_id = c.id
                WHERE b.id = %s
            """, (book_id,))
            book_data = cur.fetchone()
            
            if not book_data:
                flash('Kitap bulunamadı!', 'error')
                return redirect(url_for('books'))
            
            # Kitap verilerini dictionary formatına dönüştür
            book = {
                'id': book_data[0],
                'title': book_data[1],
                'isbn': book_data[2],
                'category_id': book_data[3],
                'author_id': book_data[4],
                'quantity': book_data[5],
                'available_quantity': book_data[6],
                'cover_image': book_data[7],
                'description': book_data[8],
                'created_at': book_data[9],
                'author_name': book_data[10],
                'category_name': book_data[11],
                'total_borrows': book_data[12]
            }
            
            # Kitabın ödünç alma geçmişini al
            cur.execute("""
                SELECT br.borrow_date, br.return_date, br.status,
                       u.username, u.role
                FROM borrowings br
                JOIN users u ON br.user_id = u.id
                WHERE br.book_id = %s
                ORDER BY br.borrow_date DESC
            """, (book_id,))
            borrow_history = cur.fetchall()
    
    return render_template('book_detail.html', book=book, borrow_history=borrow_history)

@app.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_book(book_id):
    with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            if request.method == 'POST':
                title = request.form['title']
                isbn = request.form['isbn']
                category_id = request.form['category_id']
                author_name = request.form['author']
                quantity = request.form['quantity']
                description = request.form['description']
                
                try:
                    # Yazarı güncelle veya ekle
                    cur.execute("SELECT id FROM authors WHERE name = %s", (author_name,))
                    author = cur.fetchone()
                    if not author:
                        cur.execute("INSERT INTO authors (name) VALUES (%s) RETURNING id", (author_name,))
                        author_id = cur.fetchone()[0]
                    else:
                        author_id = author[0]
                    
                    # Kapak resmi yükleme
                    cover_image = None
                    if 'cover_image' in request.files:
                        file = request.files['cover_image']
                        if file and allowed_file(file.filename):
                            filename = secure_filename(file.filename)
                            # Benzersiz dosya adı oluştur
                            filename = f"{book_id}_{filename}"
                            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                            cover_image = filename
                    
                    # Kitabı güncelle
                    if cover_image:
                        cur.execute("""
                            UPDATE books 
                            SET title = %s, isbn = %s, category_id = %s, author_id = %s, 
                                quantity = %s, available_quantity = %s, description = %s,
                                cover_image = %s
                            WHERE id = %s
                        """, (title, isbn, category_id, author_id, quantity, quantity, 
                              description, cover_image, book_id))
                    else:
                        cur.execute("""
                            UPDATE books 
                            SET title = %s, isbn = %s, category_id = %s, author_id = %s, 
                                quantity = %s, available_quantity = %s, description = %s
                            WHERE id = %s
                        """, (title, isbn, category_id, author_id, quantity, quantity, 
                              description, book_id))
                    
                    conn.commit()
                    flash('Kitap başarıyla güncellendi!', 'success')
                    return redirect(url_for('book_detail', book_id=book_id))
                except psycopg2.IntegrityError:
                    flash('Bu ISBN numarası başka bir kitap tarafından kullanılıyor!', 'error')
            
            # Kitap bilgilerini al
            cur.execute("""
                SELECT b.*, a.name as author_name, c.name as category_name
                FROM books b
                LEFT JOIN authors a ON b.author_id = a.id
                LEFT JOIN categories c ON b.category_id = c.id
                WHERE b.id = %s
            """, (book_id,))
            book_data = cur.fetchone()
            
            if not book_data:
                flash('Kitap bulunamadı!', 'error')
                return redirect(url_for('books'))
            
            # Kitap verilerini dictionary formatına dönüştür
            book = {
                'id': book_data[0],
                'title': book_data[1],
                'isbn': book_data[2],
                'category_id': book_data[3],
                'author_id': book_data[4],
                'quantity': book_data[5],
                'available_quantity': book_data[6],
                'cover_image': book_data[7],
                'description': book_data[8],
                'created_at': book_data[9],
                'author_name': book_data[10],
                'category_name': book_data[11]
            }
            
            # Kategorileri al
            cur.execute("SELECT id, name FROM categories ORDER BY name")
            categories = cur.fetchall()
    
    return render_template('edit_book.html', book=book, categories=categories)

@app.route('/books/<int:book_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_book(book_id):
    with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("DELETE FROM books WHERE id = %s", (book_id,))
                conn.commit()
                flash('Kitap başarıyla silindi!', 'success')
            except Exception as e:
                flash(f'Kitap silinirken bir hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('books'))

# Ödünç alma sistemi route'ları
@app.route('/books/<int:book_id>/borrow', methods=['POST'])
@login_required
def borrow_book(book_id):
    # Admin kullanıcıları ödünç alma işlemi yapamaz
    if session.get('role') == 'admin':
        flash('Admin kullanıcıları kitap ödünç alamaz!', 'error')
        return redirect(url_for('books'))

    with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            try:
                # Kitabın müsait olup olmadığını kontrol et
                cur.execute("""
                    SELECT available_quantity, title 
                    FROM books 
                    WHERE id = %s
                """, (book_id,))
                book = cur.fetchone()
                
                if not book or book[0] <= 0:
                    flash('Bu kitap şu anda müsait değil!', 'error')
                    return redirect(url_for('books'))
                
                # Kullanıcının aktif ödünç alma sayısını kontrol et
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM borrowings 
                    WHERE user_id = %s AND status = 'active'
                """, (session['user_id'],))
                active_borrows = cur.fetchone()[0]
                
                if active_borrows >= 3:
                    flash('En fazla 3 kitap ödünç alabilirsiniz!', 'error')
                    return redirect(url_for('books'))
                
                # Ödünç alma kaydı oluştur
                due_date = datetime.now() + timedelta(days=14)  # 2 hafta
                cur.execute("""
                    INSERT INTO borrowings (book_id, user_id, due_date, status)
                    VALUES (%s, %s, %s, 'active')
                """, (book_id, session['user_id'], due_date))
                
                # Kitabın müsait sayısını güncelle
                cur.execute("""
                    UPDATE books 
                    SET available_quantity = available_quantity - 1 
                    WHERE id = %s
                """, (book_id,))
                
                conn.commit()
                flash(f'{book[1]} kitabı başarıyla ödünç alındı!', 'success')
            except Exception as e:
                flash(f'Bir hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('my_borrows'))

@app.route('/my-borrows')
@login_required
def my_borrows():
    with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT br.id, b.title, br.borrow_date, br.due_date, br.status,
                       CASE 
                           WHEN br.status = 'active' AND br.due_date < CURRENT_TIMESTAMP 
                           THEN CURRENT_TIMESTAMP - br.due_date
                           ELSE NULL
                       END as delay_days
                FROM borrowings br
                JOIN books b ON br.book_id = b.id
                WHERE br.user_id = %s
                ORDER BY br.borrow_date DESC
            """, (session['user_id'],))
            borrows = cur.fetchall()
    
    return render_template('my_borrows.html', borrows=borrows)

@app.route('/borrows/<int:borrow_id>/return', methods=['POST'])
@login_required
def return_book(borrow_id):
    with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            try:
                # Önce ödünç alma kaydının var olup olmadığını kontrol et
                cur.execute("""
                    SELECT br.id, br.book_id, br.status, b.title
                    FROM borrowings br
                    JOIN books b ON br.book_id = b.id
                    WHERE br.id = %s AND br.user_id = %s
                """, (borrow_id, session['user_id']))
                borrow = cur.fetchone()
                
                if not borrow:
                    flash('Ödünç alma kaydı bulunamadı!', 'error')
                    return redirect(url_for('my_borrows'))
                
                if borrow[2] != 'active':
                    flash('Bu kitap zaten iade edilmiş!', 'error')
                    return redirect(url_for('my_borrows'))
                
                # Ödünç alma kaydını güncelle
                cur.execute("""
                    UPDATE borrowings 
                    SET return_date = CURRENT_TIMESTAMP,
                        status = CASE 
                            WHEN due_date < CURRENT_TIMESTAMP THEN 'overdue'
                            ELSE 'returned'
                        END
                    WHERE id = %s AND user_id = %s
                """, (borrow_id, session['user_id']))
                
                # Kitabın müsait sayısını güncelle
                cur.execute("""
                    UPDATE books 
                    SET available_quantity = available_quantity + 1 
                    WHERE id = %s
                """, (borrow[1],))
                
                conn.commit()
                flash(f'{borrow[3]} kitabı başarıyla iade edildi!', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Bir hata oluştu: {str(e)}', 'error')
    
    return redirect(url_for('my_borrows'))

# Raporlama ve istatistikler
@app.route('/reports')
@login_required
@admin_required
def reports():
    with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            # En çok okunan kitaplar
            cur.execute("""
                SELECT b.title, COUNT(*) as borrow_count
                FROM borrowings br
                JOIN books b ON br.book_id = b.id
                GROUP BY b.id, b.title
                ORDER BY borrow_count DESC
                LIMIT 5
            """)
            popular_books = cur.fetchall()
            
            # Aktif ödünç almalar
            cur.execute("""
                SELECT b.title, u.username, br.borrow_date, br.due_date,
                       CASE 
                           WHEN br.due_date < CURRENT_TIMESTAMP 
                           THEN CURRENT_TIMESTAMP - br.due_date
                           ELSE NULL
                       END as delay_days
                FROM borrowings br
                JOIN books b ON br.book_id = b.id
                JOIN users u ON br.user_id = u.id
                WHERE br.status = 'active'
                ORDER BY br.due_date
            """)
            active_borrows = cur.fetchall()
            
            # Gecikmiş iadeler
            cur.execute("""
                SELECT b.title, u.username, br.borrow_date, br.due_date,
                       CURRENT_TIMESTAMP - br.due_date as delay_days
                FROM borrowings br
                JOIN books b ON br.book_id = b.id
                JOIN users u ON br.user_id = u.id
                WHERE br.status = 'active' AND br.due_date < CURRENT_TIMESTAMP
                ORDER BY br.due_date
            """)
            overdue_borrows = cur.fetchall()
    
    return render_template('reports.html', 
                         popular_books=popular_books,
                         active_borrows=active_borrows,
                         overdue_borrows=overdue_borrows)

# Kullanıcı profil yönetimi
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        email = request.form['email']
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        
        with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
            with conn.cursor() as cur:
                try:
                    # Mevcut şifreyi kontrol et
                    cur.execute("""
                        SELECT password 
                        FROM users 
                        WHERE id = %s
                    """, (session['user_id'],))
                    user = cur.fetchone()
                    
                    if not user or not check_password_hash(user[0], current_password):
                        flash('Mevcut şifre yanlış!', 'error')
                        return redirect(url_for('profile'))
                    
                    # Profili güncelle
                    if new_password:
                        hashed_password = generate_password_hash(new_password)
                        cur.execute("""
                            UPDATE users 
                            SET email = %s, password = %s 
                            WHERE id = %s
                        """, (email, hashed_password, session['user_id']))
                    else:
                        cur.execute("""
                            UPDATE users 
                            SET email = %s 
                            WHERE id = %s
                        """, (email, session['user_id']))
                    
                    conn.commit()
                    flash('Profil başarıyla güncellendi!', 'success')
                    return redirect(url_for('profile'))
                except psycopg2.IntegrityError:
                    flash('Bu email adresi zaten kullanımda!', 'error')
                    return redirect(url_for('profile'))
                except Exception as e:
                    flash(f'Bir hata oluştu: {str(e)}', 'error')
                    return redirect(url_for('profile'))
    
    with psycopg2.connect(os.environ.get("DATABASE_URL")) as conn:
        with conn.cursor() as cur:
            # Kullanıcı bilgilerini al
            cur.execute("""
                SELECT username, email, role 
                FROM users 
                WHERE id = %s
            """, (session['user_id'],))
            user_data = cur.fetchone()
            
            # Kullanıcı verilerini dictionary formatına dönüştür
            user = {
                'username': user_data[0],
                'email': user_data[1],
                'role': user_data[2]
            }
            
            # Eğer kullanıcı admin değilse, ödünç alma istatistiklerini al
            if session.get('role') != 'admin':
                cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE status = 'active') as active_borrows,
                        COUNT(*) FILTER (WHERE status = 'returned') as returned_borrows,
                        COUNT(*) FILTER (WHERE status = 'overdue') as overdue_borrows
                    FROM borrowings 
                    WHERE user_id = %s
                """, (session['user_id'],))
                stats = cur.fetchone()
                active_borrows = stats[0]
                returned_borrows = stats[1]
                overdue_borrows = stats[2]
            else:
                active_borrows = returned_borrows = overdue_borrows = 0
    
    return render_template('profile.html', 
                         user=user,
                         active_borrows=active_borrows,
                         returned_borrows=returned_borrows,
                         overdue_borrows=overdue_borrows)

if __name__ == "__main__":
    app.run(debug=True)
  