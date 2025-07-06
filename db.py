# Gerekli modülleri içe aktar
import os  # Ortam değişkenlerini okumak için kullanılır
import sys  # Programı sonlandırmak için kullanılır
import psycopg2 as pgdb  # PostgreSQL veritabanına bağlanmak için psycopg2 modülü
from werkzeug.security import generate_password_hash

# Veritabanı başlatma sırasında çalıştırılacak SQL komutlarını içeren liste
INIT_STATEMENTS = [
    # Kullanıcılar tablosu
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'student')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    
    # Kategoriler tablosu
    """
    CREATE TABLE IF NOT EXISTS categories (
        id SERIAL PRIMARY KEY,
        name VARCHAR(50) UNIQUE NOT NULL
    )
    """,
    
    # Yazarlar tablosu
    """
    CREATE TABLE IF NOT EXISTS authors (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        biography TEXT
    )
    """,
    
    # Kitaplar tablosu
    """
    CREATE TABLE IF NOT EXISTS books (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        isbn VARCHAR(13) UNIQUE,
        category_id INTEGER REFERENCES categories(id),
        author_id INTEGER REFERENCES authors(id),
        quantity INTEGER NOT NULL DEFAULT 1,
        available_quantity INTEGER NOT NULL DEFAULT 1,
        cover_image VARCHAR(255),
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    
    # Ödünç alma tablosu
    """
    CREATE TABLE IF NOT EXISTS borrowings (
        id SERIAL PRIMARY KEY,
        book_id INTEGER REFERENCES books(id),
        user_id INTEGER REFERENCES users(id),
        borrow_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        due_date TIMESTAMP NOT NULL,
        return_date TIMESTAMP,
        status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'returned', 'overdue')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
]

# Örnek veriler
SAMPLE_DATA = [
    # Admin kullanıcısı
    f"""
    INSERT INTO users (username, password, email, role)
    SELECT 'admin', '{generate_password_hash("admin123")}', 'admin@library.com', 'admin'
    WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin')
    """,
    
    # Örnek kategoriler
    """
    INSERT INTO categories (name)
    SELECT unnest(ARRAY['Roman', 'Bilim Kurgu', 'Fantastik', 'Biyografi', 'Tarih', 'Bilim', 'Kişisel Gelişim', 'Çocuk Kitapları'])
    WHERE NOT EXISTS (SELECT 1 FROM categories LIMIT 1)
    """,
    
    # Örnek yazarlar
    """
    INSERT INTO authors (name)
    SELECT unnest(ARRAY['Orhan Pamuk', 'George R.R. Martin', 'J.K. Rowling', 'Stephen King', 
                       'Isaac Asimov', 'Yuval Noah Harari', 'Malcolm Gladwell', 'Paulo Coelho', 
                       'Adam Fawer', 'Albert Camus'])
    WHERE NOT EXISTS (SELECT 1 FROM authors LIMIT 1)
    """,
    
    # Örnek kitaplar
    """
    INSERT INTO books (title, isbn, category_id, author_id, quantity, available_quantity)
    SELECT 
        b.title,
        b.isbn,
        c.id as category_id,
        a.id as author_id,
        b.quantity,
        b.quantity as available_quantity
    FROM (
        VALUES 
            ('Kar', '9789750719387', 'Roman', 'Orhan Pamuk', 5),
            ('Buz ve Ateşin Şarkısı', '9789750719388', 'Fantastik', 'George R.R. Martin', 3),
            ('Harry Potter ve Felsefe Taşı', '9789750719389', 'Fantastik', 'J.K. Rowling', 4),
            ('Olasılıksız', '9789750719390', 'Bilim Kurgu', 'Adam Fawer', 2),
            ('Sapiens', '9789750719391', 'Bilim', 'Yuval Noah Harari', 3),
            ('Outliers', '9789750719392', 'Kişisel Gelişim', 'Malcolm Gladwell', 2),
            ('Simyacı', '9789750719393', 'Roman', 'Paulo Coelho', 4),
            ('Veba', '9789750719394', 'Roman', 'Albert Camus', 3)
    ) AS b(title, isbn, category_name, author_name, quantity)
    JOIN categories c ON c.name = b.category_name
    JOIN authors a ON a.name = b.author_name
    WHERE NOT EXISTS (SELECT 1 FROM books LIMIT 1)
    """
]

def table_exists(cursor, table_name):
    """Belirtilen tablonun var olup olmadığını kontrol eder."""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        );
    """, (table_name,))
    return cursor.fetchone()[0]

def init_db(url):
    """Veritabanını başlatır. Tablolar yoksa oluşturur ve örnek verileri ekler."""
    with pgdb.connect(url) as connection:
        cursor = connection.cursor()
        
        # Tabloları oluştur
        for statement in INIT_STATEMENTS:
            cursor.execute(statement)
        
        # Örnek verileri ekle
        for statement in SAMPLE_DATA:
            cursor.execute(statement)
        
        connection.commit()
        cursor.close()

if __name__ == "__main__":
    url = os.getenv("DATABASE_URL")
    if url is None:
        print("Usage: DATABASE_URL=url python dbinit.py")
        sys.exit(1)
    init_db(url)