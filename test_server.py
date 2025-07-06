import pytest
from unittest.mock import patch, MagicMock
from Server import app
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import psycopg2

@pytest.fixture
def client():#Test istemcisi oluşturma
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_db(): # Mock veritabanı bağlantısı
    with patch('psycopg2.connect') as mock:
        mock_cr = MagicMock()
        mock.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cr
        yield mock_cr

def test_login_success(client, mock_db):
    # Mock kullanıcı verisi - gerçek hash'lenmiş şifre kullan
    hashed_password = generate_password_hash('test_password')
    mock_user = (1, 'test_user', hashed_password, 'student')
    mock_db.fetchone.return_value = mock_user

    
    test_data = {
        'username': 'test_user',
        'password': 'test_password'
    }

   
    response = client.post('/login', data=test_data, follow_redirects=True)

    
    assert response.status_code == 200  
    
    mock_db.execute.assert_any_call('SELECT id, username, password, role FROM users WHERE username = %s', ('test_user',))

def test_login_failure(client, mock_db):

    mock_db.fetchone.return_value = None
    test_data = {
        'username': 'wrong_user',
        'password': 'wrong_password'
    }
    response = client.post('/login', data=test_data)
    assert response.status_code == 200 
    mock_db.execute.assert_called_once()

def test_register_success(client, mock_db):
    
    mock_db.fetchone.return_value = None  

    
    test_data = {
        'username': 'new_user',
        'password': 'new_password',
        'email': 'new@example.com'
    }

   
    response = client.post('/register', data=test_data, follow_redirects=True)

    
    assert response.status_code == 200 
    mock_db.execute.assert_called()

def test_register_duplicate_username(client, mock_db):
    
    mock_db.execute.side_effect = psycopg2.IntegrityError("duplicate key value violates unique constraint")

   
    test_data = {
        'username': 'existing_user',
        'password': 'password',
        'email': 'test@example.com'
    }

   
    response = client.post('/register', data=test_data)

   
    assert response.status_code == 200  # Hata durumunda sayfada kalır
    mock_db.execute.assert_called()

def test_add_book_success(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['role'] = 'admin'

    
    mock_db.fetchone.return_value = (1,)  
    mock_db.fetchall.return_value = [(1, 'Roman')]  

   
    test_data = {
        'title': 'Test Book',
        'isbn': '1234567890123',
        'author': 'Test Author',
        'category_id': '1',
        'quantity': '5',
        'description': 'Test Description'
    }

    
    response = client.post('/books/add', data=test_data)

    
    assert response.status_code == 302  
    mock_db.execute.assert_called()

def test_borrow_book_success(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 2
        session['role'] = 'student'

   
    mock_db.fetchone.return_value = (1, 'Test Book')  

    
    mock_db.fetchone.side_effect = [(1, 'Test Book'), (0,)]  

   
    response = client.post('/books/1/borrow')

    
    assert response.status_code == 302  
    mock_db.execute.assert_called()

def test_return_book_success(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 2
        session['role'] = 'student'

    
    mock_db.fetchone.return_value = (1, 1, 'active', 'Test Book')

    
    response = client.post('/borrows/1/return')

   
    assert response.status_code == 302  
    mock_db.execute.assert_called()

def test_search_books(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['role'] = 'admin'

   
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'items': [{
            'volumeInfo': {
                'title': 'Test Book',
                'authors': ['Test Author'],
                'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': '1234567890123'}],
                'description': 'Test Description',
                'imageLinks': {'thumbnail': 'http://example.com/cover.jpg'},
                'categories': ['Test Category']
            }
        }]
    }

    with patch('requests.get', return_value=mock_response):
        # Kitap arama isteği gönder
        response = client.get('/books/search?q=test')

       
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) > 0

def test_profile_update(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['role'] = 'student'

    
    mock_db.fetchone.return_value = ('hashed_password',)  # Mevcut şifre

   
    test_data = {
        'email': 'updated@example.com',
        'current_password': 'current_password',
        'new_password': 'new_password'
    }

   
    response = client.post('/profile', data=test_data)

   
    assert response.status_code == 302 
    mock_db.execute.assert_called()

def test_index_page(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 1
    
    mock_db.fetchall.return_value = [
        (1, 'Test Book', 'cover.jpg', 'Test Author')
    ]
    
    response = client.get('/')
    assert response.status_code == 200

def test_logout(client):
    
    with client.session_transaction() as session:
        session['user_id'] = 1
    
    response = client.get('/logout')
    assert response.status_code == 302  

def test_books_page(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 1
    
    
    mock_db.fetchall.side_effect = [
        [(1, 'Roman')], 
        [(1, 'Test Book', '1234567890123', 5, 3, 'cover.jpg', 'Roman', 'Test Author')]  
    ]
    
    response = client.get('/books')
    assert response.status_code == 200

def test_book_detail(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 1
    
    
    mock_db.fetchone.return_value = (
        1, 'Test Book', '1234567890123', 1, 1, 5, 3, 'cover.jpg', 'Test Description',
        datetime.now(), 'Test Author', 'Roman', 2
    )
    mock_db.fetchall.return_value = [
        (datetime.now(), None, 'active', 'test_user', 'student')
    ]
    
    response = client.get('/books/1')
    assert response.status_code == 200

def test_edit_book(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['role'] = 'admin'
    
    
    mock_db.fetchone.return_value = (
        1, 'Test Book', '1234567890123', 1, 1, 5, 3, 'cover.jpg', 'Test Description',
        datetime.now(), 'Test Author', 'Roman'
    )
    mock_db.fetchall.return_value = [(1, 'Roman')]
    
    response = client.get('/books/1/edit')
    assert response.status_code == 200

def test_delete_book(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['role'] = 'admin'
    
    response = client.post('/books/1/delete')
    assert response.status_code == 302  

def test_my_borrows(client, mock_db):
   
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['role'] = 'student'
    
    
    mock_db.fetchall.return_value = [
        (1, 'Test Book', datetime.now(), datetime.now() + timedelta(days=14), 'active', None)
    ]
    
    response = client.get('/my-borrows')
    assert response.status_code == 200

def test_reports_page(client, mock_db):
   
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['role'] = 'admin'
    
    # Mock rapor verileri
    mock_db.fetchall.side_effect = [
        [('Test Book', 5)], 
        [('Test Book', 'test_user', datetime.now(), datetime.now() + timedelta(days=14), None)],  
        [('Test Book', 'test_user', datetime.now(), datetime.now() - timedelta(days=1), timedelta(days=1))] 
    ]
    
    response = client.get('/reports')
    assert response.status_code == 200

def test_profile_page(client, mock_db):
    # Mock kullanıcı oturumu
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['role'] = 'student'
    
   
    mock_db.fetchone.side_effect = [
        ('test_user', 'test@example.com', 'student'),  
        (2, 3, 1) 
    ]
    
    response = client.get('/profile')
    assert response.status_code == 200

def test_profile_update_duplicate_email(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 1
        session['role'] = 'student'
    
    # Mock kullanıcı verisi
    hashed_password = generate_password_hash('current_password')
    mock_db.fetchone.side_effect = [
        (hashed_password,),  # Şifre kontrolü için
        ('AbdulSamet', 'Sametsaba84@gmail.com', 'student'),  
        (2, 3, 1) 
    ]
    
   
    def execute_side_effect(*args, **kwargs):
        query = args[0].strip()
        
       
        if query.startswith('SELECT'):
            return None
            
      
        if query.startswith('UPDATE'):
            raise psycopg2.IntegrityError("duplicate key value violates unique constraint")
            
        return None
    
    mock_db.execute.side_effect = execute_side_effect
    
    test_data = {
        'email': 'existing@example.com',
        'current_password': 'current_password',
        'new_password': 'new_password'
    }
    
    response = client.post('/profile', data=test_data, follow_redirects=True)
    assert response.status_code == 200
    # Hata mesajının gösterildiğini kontrol et
    assert b'Bu email adresi zaten kullan' in response.data

def test_borrow_book_limit_exceeded(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 2
        session['role'] = 'student'
    
    # kitap ve aktif ödünç alma sayısı
    mock_db.fetchone.side_effect = [
        (1, 'Test Book'), 
        (3,)  # Maksimum ödünç alma sayısına ulaşılmış
    ]
    
    response = client.post('/books/1/borrow')
    assert response.status_code == 302 

def test_borrow_book_not_available(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 2
        session['role'] = 'student'
    
    # müsait olmayan kitap
    mock_db.fetchone.return_value = (0, 'Test Book')
    
    response = client.post('/books/1/borrow')
    assert response.status_code == 302  

def test_return_book_not_found(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 2
        session['role'] = 'student'
    
    # ödünç alma kaydı bulunamadı
    mock_db.fetchone.return_value = None
    
    response = client.post('/borrows/999/return')
    assert response.status_code == 302  

def test_return_book_already_returned(client, mock_db):
    
    with client.session_transaction() as session:
        session['user_id'] = 2
        session['role'] = 'student'
    
    # zaten iade edilmiş kitap
    mock_db.fetchone.return_value = (1, 1, 'returned', 'Test Book')
    
    response = client.post('/borrows/1/return')
    assert response.status_code == 302 